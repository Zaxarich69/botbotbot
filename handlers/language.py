import logging
from aiogram import Router, types, F, Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from services.storage import get_or_create_user, set_user_lang
from locales.translations import translations
from .common import get_language_keyboard, send_main_menu

router = Router()
log = logging.getLogger(__name__)

# Build a whitelist of supported language codes (respect DB String(4) constraint)
ALLOWED_LANGS: set[str] = {code for code in translations.keys() if isinstance(code, str) and len(code) <= 4}

def _safe_resolve_lang(code: str | None) -> str:
    """Return a safe language code present in translations, fallback to the first available."""
    if code in ALLOWED_LANGS:
        return code  # type: ignore[arg-type]
    # Fallback to a deterministic default: prefer 'en' if present, otherwise first key
    if "en" in ALLOWED_LANGS:
        return "en"
    return next(iter(ALLOWED_LANGS)) if ALLOWED_LANGS else "en"

@router.callback_query(F.data == "select_language")
async def cb_select_language(callback: types.CallbackQuery, session: AsyncSession):
    """Показать клавиатуру выбора языка."""
    # Answer early to avoid Telegram timeout
    try:
        await callback.answer()
    except Exception as e:
        log.debug("Failed to answer callback early: %s", e)

    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    lang = _safe_resolve_lang(getattr(user, "language_code", None))

    # Guard against missing message or edit issues
    if not callback.message:
        log.warning("No message attached to callback for select_language; cannot edit.")
        return

    try:
        await callback.message.edit_text(
            translations.get(lang, {}).get("choose_language", "Choose your language:"),
            reply_markup=get_language_keyboard()
        )
    except TelegramBadRequest as e:
        # Common case: "message is not modified" or message deleted
        log.debug("Edit select_language message failed: %s", e)
    except Exception as e:
        log.exception("Unexpected error editing select_language message: %s", e)

@router.callback_query(F.data.startswith("lang_"))
async def cb_set_language(callback: types.CallbackQuery, bot: Bot, session: AsyncSession):
    """Установить язык пользователя и показать главное меню."""
    data = callback.data or ""
    # Robust parsing: 'lang_<code>'
    _, _, suffix = data.partition("lang_")
    lang_code = suffix.strip()

    # Validate lang_code strictly
    if not lang_code or lang_code not in ALLOWED_LANGS:
        log.warning("Received invalid language code from callback: %r", lang_code)
        # Answer gracefully with a safe default text
        safe_lang = _safe_resolve_lang(None)
        try:
            await callback.answer(translations.get(safe_lang, {}).get("language_set", "Language updated."))
        except Exception as e:
            log.debug("Failed to answer callback for invalid lang code: %s", e)
        # Still try to show main menu with a safe language
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        # Do not persist invalid code; just render menu
        message_id = callback.message.message_id if callback.message else None
        await send_main_menu(bot, callback.from_user.id, user, session, message_id)
        return

    # Get or create user and persist language change via helper
    user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)

    try:
        # Use centralized helper (middleware will commit)
        await set_user_lang(session, user_id=user.id, lang_code=lang_code)
        # Keep the in-memory user consistent for subsequent rendering
        user.language_code = lang_code
    except Exception as e:
        log.exception("Failed to set user language: %s", e)
        # Inform user with safe fallback
        safe_lang = _safe_resolve_lang(getattr(user, "language_code", None))
        try:
            await callback.answer(translations.get(safe_lang, {}).get("language_set", "Language updated."))
        except Exception as e2:
            log.debug("Failed to answer callback after set_user_lang error: %s", e2)
        message_id = callback.message.message_id if callback.message else None
        await send_main_menu(bot, callback.from_user.id, user, session, message_id)
        return

    # Localized confirmation with safe lookup
    text_ok = translations.get(lang_code, {}).get("language_set", "Language updated.")
    try:
        await callback.answer(text_ok)
    except Exception as e:
        log.debug("Failed to answer callback with confirmation: %s", e)

    # Safely obtain message_id (could be None for inline callbacks)
    message_id = callback.message.message_id if callback.message else None
    await send_main_menu(bot, callback.from_user.id, user, session, message_id)
