import logging
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from services.storage import get_or_create_user, get_user
from locales.translations import translations
from .common import get_language_keyboard, send_main_menu
from config import DEFAULT_LANGUAGE

router = Router()
log = logging.getLogger(__name__)


def _t(lang: str, key: str) -> str:
    """
    Safe translations getter with fallback to default language and empty string as last resort.
    """
    lang_map = translations.get(lang) or translations.get(DEFAULT_LANGUAGE) or {}
    return lang_map.get(key, "")


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, bot: Bot, session: AsyncSession):
    """
    Обработчик команды /start.
    Показывает приветствие и выбор языка для новых пользователей,
    или главное меню для существующих.
    """
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)

    # Простой способ определить нового пользователя.
    # Если язык не менялся и кошельков нет, скорее всего, пользователь новый.
    is_new_user = user.language_code == DEFAULT_LANGUAGE and not user.wallets

    if is_new_user:
        # Коммит выполнять не нужно: его выполнит middleware после успешного завершения хендлера
        try:
            photo = FSInputFile("assets/welcome.png")
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption=_t(user.language_code, "welcome_photo"),
                reply_markup=get_language_keyboard(),
            )
        except Exception:
            # Логируем стек для диагностики и показываем текст вместо фото
            log.exception("Failed to send welcome photo")
            await message.answer(
                text=_t(user.language_code, "welcome_photo"),
                reply_markup=get_language_keyboard(),
            )
    else:
        await send_main_menu(bot, message.chat.id, user, session)


@router.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(callback: types.CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession):
    """Обработчик для кнопки 'Назад в меню'."""
    await state.clear()
    user = await get_user(session, callback.from_user.id)
    if user:
        # callback.message может отсутствовать в некоторых случаях
        msg_id = callback.message.message_id if callback.message else None
        await send_main_menu(bot, callback.from_user.id, user, session, msg_id)
    await callback.answer()
