import logging
from aiogram import types, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from locales.translations import translations
from config import ANNOUNCE_CHANNEL_ID, LANGUAGES, SUPPORTED_CURRENCIES
from services.storage import get_or_create_active_round, get_user_tickets_count, get_round_total_collected, User

log = logging.getLogger(__name__)

MAX_CALLBACK_DATA = 64


def _safe_cb(data: str) -> str:
    """Ensure callback_data does not exceed Telegram's 64-byte limit."""
    return data.encode("utf-8")[:MAX_CALLBACK_DATA].decode("utf-8", errors="ignore")


def _resolve_lang(user: User) -> str:
    """Return a supported language code with fallback to 'en'."""
    code = getattr(user, "language_code", None)
    return code if code in translations else "en"


# --- Keyboards ---

def get_language_keyboard() -> types.InlineKeyboardMarkup:
    """Создает клавиатуру выбора языка."""
    builder = InlineKeyboardBuilder()
    lang_emojis = {"es": "🇪🇸 Español", "en": "🇬🇧 English", "pt": "🇵🇹 Português", "fr": "🇫🇷 Français"}
    for lang in LANGUAGES:
        builder.button(text=lang_emojis.get(lang, lang.upper()), callback_data=_safe_cb(f"lang_{lang}"))
    builder.adjust(2)
    return builder.as_markup()


def get_main_menu_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру главного меню."""
    builder = InlineKeyboardBuilder()
    t = translations.get(lang, translations["en"])
    builder.button(text=t.get("buy_ticket_button", "Buy ticket"), callback_data=_safe_cb("buy_ticket"))
    builder.button(text=t.get("my_wallet_button", "My wallet"), callback_data=_safe_cb("my_wallet"))
    builder.button(text=t.get("language_button", "Language"), callback_data=_safe_cb("select_language"))

    has_channel_button = False
    if isinstance(ANNOUNCE_CHANNEL_ID, str) and ANNOUNCE_CHANNEL_ID.startswith("@"):
        channel_username = ANNOUNCE_CHANNEL_ID.lstrip("@")
        builder.button(text=t.get("channel_button", "Channel"), url=f"https://t.me/{channel_username}")
        has_channel_button = True

    # Adjust layout depending on whether the channel button exists
    if has_channel_button:
        builder.adjust(1, 2, 1)
    else:
        builder.adjust(1, 2)

    return builder.as_markup()


def get_back_to_menu_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой 'Назад в меню'."""
    builder = InlineKeyboardBuilder()
    t = translations.get(lang, translations["en"])
    builder.button(text=t.get("back_to_menu", "Back to menu"), callback_data=_safe_cb("back_to_menu"))
    return builder.as_markup()


def get_currency_keyboard(lang: str, prefix: str) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для выбора валюты с заданным префиксом колбэка."""
    builder = InlineKeyboardBuilder()
    for code, currency_data in SUPPORTED_CURRENCIES.items():
        name = currency_data.get("name", code)
        builder.button(text=name, callback_data=_safe_cb(f"{prefix}_{code}"))
    t = translations.get(lang, translations["en"])
    builder.button(text=t.get("back_to_menu", "Back to menu"), callback_data=_safe_cb("back_to_menu"))
    builder.adjust(1)
    return builder.as_markup()


# --- Menu Sending Logic ---

async def send_main_menu(
    bot: Bot, chat_id: int, user: User, session: AsyncSession, message_id: int | None = None
) -> None:
    """
    Готовит данные и отправляет или редактирует сообщение с главным меню.
    """
    active_round = await get_or_create_active_round(session)
    bank = await get_round_total_collected(session, active_round.id)
    tickets = await get_user_tickets_count(session, user.id, active_round.id)

    # Safe defaults
    bank = bank if bank is not None else 0
    tickets = tickets if tickets is not None else 0

    lang = _resolve_lang(user)
    t = translations.get(lang, translations["en"])
    text_template = t.get("main_menu_text", "Bank: {bank}\nTickets: {tickets}")
    try:
        text = text_template.format(bank=bank, tickets=tickets)
    except Exception as fmt_err:
        log.warning(f"Failed to format main menu text for user {chat_id}: {fmt_err}. Using fallback.")
        text = f"Bank: {bank}\nTickets: {tickets}"

    kb = get_main_menu_keyboard(lang)

    if message_id:
        try:
            await bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
        except TelegramBadRequest as e:
            msg = str(e).lower()
            if "message is not modified" in msg:
                log.debug(f"Menu not modified for user {chat_id}. Ignoring.")
            else:
                log.warning(f"Failed to edit main menu for user {chat_id}: {e}. Sending new message.")
                try:
                    await bot.send_message(chat_id, text, reply_markup=kb)
                except Exception as send_err:
                    log.error(f"Failed to send main menu to user {chat_id}: {send_err}")
    else:
        try:
            await bot.send_message(chat_id, text, reply_markup=kb)
        except Exception as send_err:
            log.error(f"Failed to send main menu to user {chat_id}: {send_err}")
