# Python
import os
import logging
import random
from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from aiogram.types import FSInputFile
from aiogram.utils.markdown import hlink

from services.storage import (
    SessionLocal, User, get_active_round,
    get_round_participants, get_round_total_collected,
)
from services.bitcoin import get_latest_bitcoin_block_hash
from locales.translations import translations
from config import ADMIN_ID
from services.payments import now_payments_api

log = logging.getLogger(__name__)


def _get_prize_usd() -> float:
    """Read PRIZE_USD from environment at runtime with validation and default."""
    value = os.getenv("PRIZE_USD", "10.0")
    try:
        return float(value)
    except (TypeError, ValueError):
        log.warning("Invalid PRIZE_USD=%r. Falling back to 10.0", value)
        return 10.0


def _get_announce_channel_id() -> str | None:
    """Read ANNOUNCE_CHANNEL_ID from environment at runtime."""
    cid = os.getenv("ANNOUNCE_CHANNEL_ID", "")
    cid = cid.strip() if isinstance(cid, str) else ""
    return cid or None


async def draw_lottery(bot: Bot):
    log.info("Starting weekly lottery draw...")

    # Read runtime configuration (avoid import-time env access)
    prize_usd = _get_prize_usd()
    announce_channel_id = _get_announce_channel_id()

    # Получаем хеш последнего блока биткоина для честного розыгрыша
    btc_hash = await get_latest_bitcoin_block_hash()
    if not btc_hash:
        log.warning("Could not get Bitcoin block hash. Falling back to system random for this draw.")
        random.seed()
    else:
        log.info(f"Using Bitcoin block hash as seed: {btc_hash}")
        random.seed(btc_hash)

    async with SessionLocal() as session:
        try:
            # Получаем активный раунд
            active_round = await get_active_round(session)
            # Attempt lazy import of optional storage functions to avoid hard import errors
            try:
                from services.storage import finish_round, create_new_round
            except Exception:
                finish_round = None
                create_new_round = None

            if not active_round:
                log.error("No active round found during draw.")
                if create_new_round:
                    await create_new_round(session, prize_usd)
                    await session.commit()
                    log.info("A new round was created because none was active.")
                else:
                    log.warning("create_new_round is unavailable. Skipping round creation.")
                return

            # Проверяем общую сумму в банке
            total_collected = await get_round_total_collected(session, active_round.id)

            if total_collected < prize_usd:
                log.info(
                    "Bank not met. Collected $%.2f, required $%.2f. Rolling over.",
                    total_collected, prize_usd
                )

                # Отправляем уведомление о переносе
                if announce_channel_id:
                    text = translations['en']["rollover_announcement_channel"].format(
                        prize=prize_usd,
                        bank=total_collected
                    )
                    try:
                        photo = FSInputFile('assets/rollover.png')
                        await bot.send_photo(announce_channel_id, photo=photo, caption=text)
                    except Exception as e:
                        log.error(f"Failed to send rollover announcement: {e}")
                        try:
                            await bot.send_message(announce_channel_id, text)
                        except Exception as e2:
                            log.error(f"Failed to send rollover text message: {e2}")

                await session.commit()
                return

            # Получаем участников
            participants = await get_round_participants(session, active_round.id)
            if not participants:
                log.warning("Bank met, but no participants found. Skipping draw.")
                return

            # Честный выбор победителя (взвешенная лотерея)
            winner_id = select_winner(participants)

            # Получаем данные победителя с загрузкой всех кошельков
            winner_res = await session.execute(
                select(User).where(User.id == winner_id).options(selectinload(User.wallets))
            )
            winner = winner_res.scalars().first()

            if not winner:
                log.error(f"Winner with ID {winner_id} not found in database!")
                return

            log.info(f"Winner selected: User ID {winner.id}, Username: {winner.username}")

            # Обрабатываем выплату (автоплатеж через NOWPayments с идемпотентностью)
            await process_winner_payout(
                bot=bot,
                winner=winner,
                btc_hash=btc_hash,
                prize_usd=prize_usd,
                total_collected=total_collected,
                round_id=active_round.id,
            )

            # Объявляем победителя в канале
            await announce_winner(bot, winner, btc_hash, total_collected, announce_channel_id, prize_usd)

            # Завершаем текущий раунд и создаем новый (если функции доступны)
            if finish_round:
                await finish_round(session, active_round.id, winner_id)
            else:
                log.warning("finish_round is unavailable. Skipping finishing the round.")

            if create_new_round:
                await create_new_round(session, prize_usd)
            else:
                log.warning("create_new_round is unavailable. Skipping new round creation.")

            await session.commit()
            log.info("Lottery draw completed successfully.")

        except Exception as e:
            log.error(f"Error during lottery draw: {e}")
            await session.rollback()
            raise


def select_winner(participants: list[tuple[int, int]]) -> int:
    """Выбирает победителя с учетом количества билетов (взвешенная лотерея)"""
    total_tickets = sum(ticket_count for _, ticket_count in participants)

    if total_tickets == 0:
        raise ValueError("No tickets found for participants")

    # Генерируем случайное число от 0 до общего количества билетов
    win_index = random.randrange(total_tickets)

    # Находим победителя
    current = 0
    for user_id, ticket_count in participants:
        current += ticket_count
        if win_index < current:
            return user_id

    # Fallback - не должно происходить
    return participants[0][0]


async def process_winner_payout(
    bot: Bot,
    winner: User,
    btc_hash: str,
    prize_usd: float,
    total_collected: float,
    round_id: int,
):
    """Обрабатывает выплату победителю (автоматически через NOWPayments, с фолбэком на ручную) и распределяет остаток."""
    try:
        from config import SUPPORTED_CURRENCIES

        payout_method = (os.getenv("PAYOUT_METHOD") or "nowpayments").strip().lower()
        prize_currency = (os.getenv("PRIZE_PAYOUT_CURRENCY") or "USDTTRC20").strip().upper()
        owner_wallets_csv = os.getenv("OWNER_WALLETS", "")
        owner_wallets = [w.strip() for w in owner_wallets_csv.split(",") if w.strip()]
        owner_currency = (os.getenv("OWNER_PAYOUT_CURRENCY") or prize_currency).strip().upper()

        # Подготовим список доступных кошельков победителя
        available_wallets = []
        for wallet in winner.wallets:
            if wallet.currency_code in SUPPORTED_CURRENCIES:
                currency_info = SUPPORTED_CURRENCIES[wallet.currency_code]
                available_wallets.append({
                    'currency': wallet.currency_code.upper(),
                    'name': currency_info['name'],
                    'address': wallet.address
                })

        # Найдем предпочтительный кошелек для приза
        winner_wallet = next((w for w in available_wallets if w["currency"].upper() == prize_currency), None)
        if not winner_wallet and available_wallets:
            winner_wallet = available_wallets[0]

        # Если автоматические выплаты отключены или нет кошелька — переходим к ручному сценарию
        if payout_method != "nowpayments" or not winner_wallet:
            log.info("Auto payout disabled or no suitable winner wallet found. Switching to manual payout flow.")
            await _notify_manual_payout(bot, winner, prize_usd, available_wallets)
            return

        # Выплата приза победителю (идемпотентность по round_id)
        idemp_win = f"lottery:{round_id}:winner"
        payout_res = await now_payments_api.create_payout_single(
            currency=winner_wallet["currency"],
            amount=float(prize_usd),
            address=winner_wallet["address"],
            idempotency_key=idemp_win
        )

        if payout_res is None:
            log.error("Winner payout failed via NOWPayments. Falling back to manual flow.")
            await _notify_manual_payout(bot, winner, prize_usd, available_wallets)
            return

        # Уведомляем победителя об успешной выплате
        wallets_text = f"• {winner_wallet['name']} ({winner_wallet['currency']}): <code>{winner_wallet['address']}</code>"
        winner_text = (
            f"🎉 Congratulations! You have won <b>${prize_usd:.2f}</b> in the weekly lottery!\n\n"
            f"Your prize has been sent to:\n{wallets_text}"
        )
        try:
            await bot.send_message(winner.id, winner_text)
        except Exception as e:
            log.warning(f"Failed to notify winner about payout: {e}")

        # Распределяем остаток на кошельки организаторов (если есть)
        leftover = max(total_collected - prize_usd, 0.0)
        if leftover > 0 and owner_wallets:
            share = leftover / float(len(owner_wallets))
            # Округляем до центов (если валюта с двумя десятичными)
            share = float(round(share, 2))

            for idx, addr in enumerate(owner_wallets, start=1):
                idemp_owner = f"lottery:{round_id}:owner:{idx}"
                owner_res = await now_payments_api.create_payout_single(
                    currency=owner_currency,
                    amount=share,
                    address=addr,
                    idempotency_key=idemp_owner
                )
                if owner_res is None:
                    log.error(f"Owner payout failed for address {addr} (share {share} {owner_currency}).")

    except Exception as e:
        log.error(f"Error processing winner payout: {e}")
        # Уведомляем админа об ошибке
        error_msg = f"❌ Error processing payout for winner {winner.id}: {e}"
        try:
            await bot.send_message(ADMIN_ID, error_msg)
        except Exception as e2:
            log.error(f"Failed to notify admin about payout error: {e2}")


async def _notify_manual_payout(bot: Bot, winner: User, prize_usd: float, available_wallets: list[dict]):
    """Сообщение администратору и победителю для ручной выплаты."""
    try:
        wallets_text = "\n".join([
            f"• {w['name']} ({w['currency']}): <code>{w['address']}</code>"
            for w in available_wallets
        ]) if available_wallets else "No payout wallets on file."

        admin_text = (
            f"‼️ <b>MANUAL PAYOUT REQUIRED</b> ‼️\n\n"
            f"Winner selected!\n\n"
            f"<b>User:</b> {hlink(str(winner.id), f'tg://user?id={winner.id}')} (ID: <code>{winner.id}</code>)\n"
            f"<b>Prize:</b> ${prize_usd:.2f}\n"
            f"<b>Available Wallets:</b>\n{wallets_text}\n\n"
            f"Please send the prize to one of these addresses."
        )
        await bot.send_message(ADMIN_ID, admin_text)

        winner_text = (
            f"🎉 Congratulations! You have won <b>${prize_usd:.2f}</b> in the weekly lottery!\n\n"
            f"Your prize is being processed and will be sent to one of your wallets.\n{wallets_text}"
        )
        await bot.send_message(winner.id, winner_text)
    except Exception as e:
        log.error(f"Error notifying manual payout: {e}")


async def announce_winner(
    bot: Bot,
    winner: User,
    btc_hash: str,
    total_collected: float,
    announce_channel_id: str | None,
    prize_usd: float,
):
    """Объявляет победителя в канале"""
    if not announce_channel_id:
        log.warning("ANNOUNCE_CHANNEL_ID not set, skipping winner announcement")
        return

    try:
        # Скрываем часть ID пользователя для приватности
        user_id_str = str(winner.id)
        obscured_id = user_id_str[:3] + '...' + user_id_str[-3:] if len(user_id_str) > 6 else user_id_str

        channel_text = translations['en']["draw_announcement_channel"].format(
            prize=prize_usd,
            user_id_part=obscured_id,
            btc_hash=btc_hash or "N/A (API failed)",
            total_collected=total_collected
        )

        try:
            photo = FSInputFile('assets/winner.png')
            await bot.send_photo(announce_channel_id, photo=photo, caption=channel_text)
        except Exception as e:
            log.error(f"Failed to send winner photo: {e}")
            # Fallback - отправляем только текст
            await bot.send_message(announce_channel_id, channel_text)

    except Exception as e:
        log.error(f"Error announcing winner: {e}")