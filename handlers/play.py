import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from services import payments
from services.storage import get_active_round, get_user, create_payment_record
from locales.translations import translations
from config import SUPPORTED_CURRENCIES
from states import Play
from .common import get_currency_keyboard, get_back_to_menu_keyboard

router = Router()
log = logging.getLogger(__name__)

# QR sending is optional; disabled by default and kept safe (no hard import of qrcode/io)
_QR_AVAILABLE = False

@router.callback_query(F.data == "buy_ticket")
async def cb_buy_ticket(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начало процесса покупки билетов"""
    # Load user with wallets to validate presence of at least one payout wallet
    user = await get_user(session, callback.from_user.id, with_wallets=True)
    if not user:
        await callback.answer("❌ User not found")
        return

    # Проверяем, что у пользователя есть хотя бы один кошелек
    if not user.wallets:
        await callback.answer(
            "❌ Please set up your payout wallet first!",
            show_alert=True
        )
        return

    await state.set_state(Play.choosing_payment_currency)
    await callback.message.edit_text(
        translations[user.language_code]['choose_payment_currency'],
        reply_markup=get_currency_keyboard(user.language_code, prefix="currency")
    )
    await callback.answer()

@router.callback_query(Play.choosing_payment_currency, F.data.startswith("currency_"))
async def process_currency_choice(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработка выбора валюты для оплаты"""
    currency_code = callback.data.split("_", 1)[1]

    if currency_code not in SUPPORTED_CURRENCIES:
        await callback.answer("❌ Invalid currency selected.", show_alert=True)
        return

    await state.clear()

    try:
        user = await get_user(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ User not found")
            return

        lang = user.language_code
        active_round = await get_active_round(session)

        if not active_round:
            await callback.answer("❌ No active lottery round", show_alert=True)
            return

        # Расчет по 0.1$ за билет: минимум/максимум билетов управляются ENV
        from os import getenv
        ticket_price = float(getenv("TICKET_PRICE_USD", "0.1"))
        min_tickets = int(getenv("MIN_TICKETS_PER_PAYMENT", "2"))
        max_tickets = int(getenv("MAX_TICKETS_PER_PAYMENT", "5"))
        min_tickets = max(1, min_tickets)
        max_tickets = max(min_tickets, max_tickets)

        # По умолчанию выставляем минимум билетов (можно расширить UI позже)
        ticket_count = min_tickets
        payment_amount = float(ticket_count) * ticket_price

        # Создаем платеж через NOWPayments API под рассчитанную сумму
        payment_info = await payments.create_payment(
            user.id,
            active_round.id,
            currency_code,
            payment_amount
        )

        if not payment_info:
            await callback.message.edit_text(
                translations[lang]["payment_failed"],
                reply_markup=get_back_to_menu_keyboard(lang)
            )
            await callback.answer()
            return

        # Сохраняем запись о платеже в БД
        await create_payment_record(
            session,
            payment_info['payment_id'],
            user.id,
            active_round.id,
            payment_amount
        )

        # Получаем URL оплаты
        payment_url = payment_info.get("payment_url") or payment_info.get("payment_link") \
                      or payment_info.get("url") or f"https://nowpayments.io/payments/{payment_info.get('payment_id')}"

        # Отправляем ссылку на оплату
        await callback.message.delete()
        link_text = f"💳 Оплатить по ссылке: <a href='{payment_url}'>Перейти к оплате</a>"
        await callback.bot.send_message(callback.from_user.id, link_text, parse_mode="HTML")

        # Опционально: QR-код для адреса (по запросу и если доступна зависимость)
        if _QR_AVAILABLE and payment_info.get("pay_address"):
            try:
                import qrcode  # type: ignore
                import io  # type: ignore
                qr_img = qrcode.make(payment_info["pay_address"])
                buf = io.BytesIO()
                qr_img.save(buf, "PNG")
                buf.seek(0)
                # QR может быть отправлен отдельной кнопкой/командой, если потребуется.
            except Exception as qr_err:
                log.warning(f"QR generation skipped: {qr_err}")

        log.info(f"Payment created for user {user.id}: {payment_info['payment_id']}")
        await callback.answer()

    except Exception as e:
        log.error(f"Error creating payment for user {callback.from_user.id}: {e}")
        await callback.answer("❌ Error creating payment. Please try again.", show_alert=True)
