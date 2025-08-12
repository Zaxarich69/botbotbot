from aiogram.fsm.state import State, StatesGroup

class WalletSetup(StatesGroup):
    """Состояния для процесса настройки кошелька."""
    waiting_for_address = State()

class Play(StatesGroup):
    """Состояния для процесса покупки билета."""
    choosing_ticket_count = State()
    choosing_payment_currency = State()
