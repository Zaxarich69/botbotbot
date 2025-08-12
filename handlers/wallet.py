from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession

from services.storage import get_user, set_user_wallet
from locales.translations import translations
from config import SUPPORTED_CURRENCIES
from .common import get_currency_keyboard, send_main_menu

router = Router()

class WalletSetup(StatesGroup):
    waiting_for_address = State()

@router.callback_query(F.data == "my_wallet")
async def cb_my_wallet(callback: types.CallbackQuery, session: AsyncSession):
    """Displays the wallet management menu."""
    user = await get_user(session, callback.from_user.id, with_wallets=True)
    lang = user.language_code

    text = "Select a currency to view or update your wallet address:\n\n"
    for currency_code, currency_data in SUPPORTED_CURRENCIES.items():
        wallet = next((w for w in user.wallets if w.currency_code == currency_code), None)
        wallet_address = f"<code>{wallet.address}</code>" if wallet else "Not set"
        text += f"<b>{currency_data['name']}:</b> {wallet_address}\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_currency_keyboard(lang, prefix="wallet")
    )
    await callback.answer()

@router.callback_query(F.data.startswith("wallet_"))
async def cb_select_wallet_currency(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handles currency selection for setting a wallet."""
    currency_code = callback.data.split("_")[1]
    user = await get_user(session, callback.from_user.id)
    lang = user.language_code
    currency_info = SUPPORTED_CURRENCIES.get(currency_code)
    if not currency_info:
        await callback.answer("Unknown currency.", show_alert=True)
        return

    await state.set_state(WalletSetup.waiting_for_address)
    await state.update_data(currency_code=currency_code)

    await callback.message.edit_text(
        translations[lang]["wallet_setup_prompt"].format(currency_name=currency_info['name']),
    )
    await callback.answer()

@router.message(WalletSetup.waiting_for_address, F.text)
async def msg_process_wallet_address(message: types.Message, state: FSMContext, bot: Bot, session: AsyncSession):
    """Processes the wallet address sent by the user."""
    address = message.text.strip()
    data = await state.get_data()
    currency_code = data["currency_code"]

    user = await get_user(session, message.from_user.id, with_wallets=True)
    lang = user.language_code
    currency_info = SUPPORTED_CURRENCIES.get(currency_code)
    if not currency_info:
        await state.clear()
        await message.answer("Unknown currency.")
        return

    # Basic validation
    # A more robust validation should be implemented based on currency rules
    if len(address) < 10:  # Simple check
        await message.answer(
            translations[lang]["invalid_wallet_address"].format(currency_name=currency_info['name'])
        )
        return

    await set_user_wallet(session, user, address, currency_code)
    await session.commit()
    await state.clear()

    await message.answer(
        translations[lang]["wallet_saved"].format(currency_name=currency_info['name'], address=address)
    )

    # Refresh user data to show updated wallet in main menu if needed
    refreshed_user = await get_user(session, message.from_user.id, with_wallets=True)
    await send_main_menu(bot, message.from_user.id, refreshed_user, session)
