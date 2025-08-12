import logging
import json
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Request, Header, HTTPException
from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.storage import (
    SessionLocal,
    Payment,
    get_user_lang,
    update_payment_status,
    add_tickets,
    get_active_round,
)
from services.payments import verify_ipn_signature
from locales.translations import translations
from config import TICKET_PRICE_USD

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ipn")
async def handle_nowpayments_ipn(request: Request, x_nowpayments_sig: str | None = Header(default=None)):
    """Обрабатывает IPN уведомления от NOWPayments"""
    try:
        body = await request.body()
        bot: Bot = request.app.state.bot

        # Подпись IPN
        if not verify_ipn_signature(body, x_nowpayments_sig):
            log.warning("Invalid IPN signature received.")
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Безопасный парсинг JSON из уже считанного body
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            log.warning("Failed to parse IPN JSON body.")
            raise HTTPException(status_code=400, detail="Invalid JSON")

        log.info(f"Received valid IPN: {data}")

        # Извлекаем необходимые данные
        payment_id = data.get("payment_id")
        payment_status = (data.get("payment_status") or "").lower()
        price_amount_raw = data.get("price_amount")

        if not all([payment_id, payment_status, price_amount_raw]):
            log.error(f"Missing required IPN data: {data}")
            raise HTTPException(status_code=400, detail="Missing required IPN data")

        # Валидируем сумму
        try:
            price_amount = Decimal(str(price_amount_raw))
        except (InvalidOperation, TypeError, ValueError):
            log.error(f"Invalid price_amount value in IPN: {price_amount_raw!r}")
            raise HTTPException(status_code=400, detail="Invalid price_amount")

        async with SessionLocal() as session:  # type: AsyncSession
            try:
                # Находим платеж в базе данных
                result = await session.execute(
                    select(Payment).where(Payment.nowpayments_payment_id == str(payment_id))
                )
                payment = result.scalars().first()

                if not payment:
                    log.error(f"IPN for unknown payment_id {payment_id} received.")
                    raise HTTPException(status_code=404, detail="Payment not found")

                # Дубликаты
                if payment.status in {"confirmed", "finished"}:
                    log.info(f"Payment {payment_id} already finalized ({payment.status}). Ignoring duplicate IPN.")
                    return {"ok": True}

                # Обновляем статус платежа
                updated = await update_payment_status(session, str(payment_id), payment_status)
                if updated is None:
                    log.error(f"Failed to update status for payment {payment_id} to {payment_status}")
                    raise HTTPException(status_code=500, detail="Failed to update payment status")

                # Если платеж подтвержден, выдаем билеты
                if payment_status in {"confirmed", "finished"}:
                    await process_confirmed_payment(session, bot, updated, price_amount)

                await session.commit()
                log.info(f"Successfully processed IPN for payment {payment_id}")

            except HTTPException:
                await session.rollback()
                raise
            except Exception:
                await session.rollback()
                log.exception(f"Error processing IPN for payment {payment_id}")
                raise

        return {"ok": True}

    except HTTPException:
        # Уже корректно подготовлено для клиента
        raise
    except Exception:
        log.exception("Unexpected error in IPN handler")
        raise HTTPException(status_code=500, detail="Internal server error")


async def process_confirmed_payment(session: AsyncSession, bot: Bot, payment: Payment, price_amount: Decimal):
    """Обрабатывает подтвержденный платеж - выдает билеты и уведомляет пользователя"""
    try:
        # Вычисляем количество билетов
        ticket_price = Decimal(str(TICKET_PRICE_USD))
        if ticket_price <= 0:
            log.error("Invalid TICKET_PRICE_USD configuration (must be > 0)")
            return

        ticket_count = int(price_amount / ticket_price)

        if ticket_count <= 0:
            log.warning(f"Payment {payment.nowpayments_payment_id}: amount too small for tickets")
            return

        # Проверяем, что раунд еще активен и соответствует платежу
        active_round = await get_active_round(session)
        if not active_round or active_round.id != payment.round_id:
            log.error(
                f"Payment {payment.nowpayments_payment_id}: round {payment.round_id} is no longer active "
                f"(active={getattr(active_round, 'id', None)})"
            )
            return

        # Добавляем билеты пользователю
        await add_tickets(session, payment.user_id, payment.round_id, ticket_count)
        log.info(
            f"Added {ticket_count} ticket(s) to user {payment.user_id} "
            f"for payment {payment.nowpayments_payment_id}"
        )

        # Отправляем уведомление пользователю (не критично при сбое)
        await send_payment_confirmation(bot, session, payment.user_id, ticket_count, price_amount)

    except Exception:
        log.exception(f"Error processing confirmed payment {payment.nowpayments_payment_id}")
        raise


async def send_payment_confirmation(bot: Bot, session: AsyncSession, user_id: int, ticket_count: int, amount: Decimal):
    """Отправляет пользователю подтверждение получения платежа"""
    try:
        user_lang = await get_user_lang(session, user_id)

        # Безопасный выбор локализации с запасным вариантом
        lang_map = translations.get(user_lang) or translations.get("en") or next(iter(translations.values()))
        template = lang_map.get("payment_received_notification", "Payment received: {tickets} tickets, ${amount}.")

        notification_text = template.format(
            tickets=ticket_count,
            amount=float(amount),
        )

        await bot.send_message(user_id, notification_text)
        log.info(f"Sent payment confirmation to user {user_id}")

    except Exception:
        log.exception(f"Failed to send payment confirmation to user {user_id}")
        # Не поднимаем исключение, так как это не критично для обработки платежа
