import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship, selectinload
from sqlalchemy import BigInteger, Integer, String, Float, ForeignKey, DateTime, select, Boolean, func, UniqueConstraint
from config import DEFAULT_LANGUAGE, DATABASE_URL, PRIZE_USD

log = logging.getLogger(__name__)

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()


# --- Models ---
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str] = mapped_column(String, nullable=True)
    language_code: Mapped[str] = mapped_column(String(4), default=DEFAULT_LANGUAGE)
    wallets: Mapped[list["Wallet"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Wallet(Base):
    __tablename__ = "wallets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    address: Mapped[str] = mapped_column(String(128), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(10), nullable=False)
    user: Mapped["User"] = relationship(back_populates="wallets")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'currency_code', name='_user_currency_uc'),
    )

class LotteryRound(Base):
    __tablename__ = "lottery_rounds"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    winner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    prize_amount: Mapped[float] = mapped_column(Float, default=PRIZE_USD)
    status: Mapped[str] = mapped_column(String, default="active") # active, finished, rolled_over
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="lottery_round", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="lottery_round", cascade="all, delete-orphan")

class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    round_id: Mapped[int] = mapped_column(Integer, ForeignKey("lottery_rounds.id"), index=True)
    user: Mapped["User"] = relationship(back_populates="tickets")
    lottery_round: Mapped["LotteryRound"] = relationship(back_populates="tickets")

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nowpayments_payment_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    round_id: Mapped[int] = mapped_column(Integer, ForeignKey("lottery_rounds.id"))
    amount_usd: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="waiting", index=True) # waiting, confirmed, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    lottery_round: Mapped["LotteryRound"] = relationship(back_populates="payments")


# --- Database Initialization ---
async def init_db():
    """Initializes the database and creates tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database initialized.")

# --- User Management ---
async def get_or_create_user(session: AsyncSession, user_id: int, username: str | None = None) -> User:
    """
    Gets a user from the DB or creates a new one.
    Does NOT commit changes. This is the handler's responsibility.
    """
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalars().first()

    if not user:
        log.info(f"Creating new user with id={user_id}")
        user = User(id=user_id, username=username)
        session.add(user)
    elif user.username != username:
        user.username = username
    return user

async def get_user(session: AsyncSession, user_id: int, with_wallets: bool = False) -> User | None:
    """Gets a user, optionally with their wallets preloaded."""
    stmt = select(User).where(User.id == user_id)
    if with_wallets:
        stmt = stmt.options(selectinload(User.wallets))
    result = await session.execute(stmt)
    return result.scalars().first()

async def set_user_wallet(session: AsyncSession, user: User, address: str, currency_code: str):
    """
    Updates or creates a wallet for the user for a specific currency.
    Does NOT commit changes.
    """
    wallet = next((w for w in user.wallets if w.currency_code.lower() == currency_code.lower()), None)

    if wallet:
        wallet.address = address
    else:
        wallet = Wallet(address=address, currency_code=currency_code.lower(), user_id=user.id)
        session.add(wallet)
        user.wallets.append(wallet) # Add to the user's collection for immediate access

async def get_user_lang(session: AsyncSession, user_id: int) -> str:
    """Gets the user's language code."""
    result = await session.execute(select(User.language_code).where(User.id == user_id))
    lang = result.scalars().first()
    return lang or DEFAULT_LANGUAGE

async def set_user_lang(session: AsyncSession, user_id: int, lang_code: str):
    """Sets the user's language. Does NOT commit."""
    user = await get_or_create_user(session, user_id)
    user.language_code = lang_code

# --- Lottery Round Management ---
async def get_or_create_active_round(session: AsyncSession) -> LotteryRound:
    """Gets the current active lottery round or creates a new one if none exists."""
    stmt = select(LotteryRound).where(LotteryRound.is_active)
    result = await session.execute(stmt)
    active_round = result.scalars().first()

    if not active_round:
        log.info("No active lottery round found. Creating a new one.")
        active_round = LotteryRound(prize_amount=PRIZE_USD)
        session.add(active_round)
        await session.flush() # Flush to get the ID
    return active_round

async def get_active_round(session: AsyncSession) -> LotteryRound | None:
    """Gets the current active lottery round without creating a new one."""
    stmt = select(LotteryRound).where(LotteryRound.is_active)
    result = await session.execute(stmt)
    return result.scalars().first()

async def get_round_total_collected(session: AsyncSession, round_id: int) -> float:
    """Gets the total amount collected in a specific round from confirmed payments."""
    stmt = select(func.sum(Payment.amount_usd)).where(
        Payment.round_id == round_id,
        Payment.status == "confirmed"
    )
    result = await session.execute(stmt)
    total = result.scalar_one_or_none()
    return total or 0.0

async def get_round_participants(session: AsyncSession, round_id: int) -> list[tuple[int, int]]:
    """Gets all participants of a round and their ticket count."""
    stmt = (
        select(Ticket.user_id, func.count(Ticket.id))
        .where(Ticket.round_id == round_id)
        .group_by(Ticket.user_id)
    )
    result = await session.execute(stmt)
    return result.all()

# --- Ticket and Payment Management ---
async def add_tickets_for_payment(session: AsyncSession, user_id: int, round_id: int, ticket_count: int):
    """Adds multiple tickets for a user in a single operation."""
    if ticket_count <= 0:
        return

    tickets = [Ticket(user_id=user_id, round_id=round_id) for _ in range(ticket_count)]
    session.add_all(tickets)
    log.info(f"Added {ticket_count} tickets for user {user_id} in round {round_id}")

async def create_payment_record(session: AsyncSession, payment_id: str, user_id: int, round_id: int, amount_usd: float) -> Payment:
    """Creates a payment record in the DB."""
    payment = Payment(
        nowpayments_payment_id=payment_id,
        user_id=user_id,
        round_id=round_id,
        amount_usd=amount_usd,
        status="waiting"
    )
    session.add(payment)
    await session.flush() # To get payment ID
    return payment

async def update_payment_status(session: AsyncSession, payment_id: str, new_status: str) -> Payment | None:
    """Updates payment status by NOWPayments ID. Does NOT commit."""
    stmt = select(Payment).where(Payment.nowpayments_payment_id == payment_id)
    result = await session.execute(stmt)
    payment = result.scalars().first()
    if payment:
        payment.status = new_status
    return payment

async def find_payment_by_id(session: AsyncSession, payment_id: str) -> Payment | None:
    """Finds a payment by its NOWPayments ID."""
    stmt = select(Payment).where(Payment.nowpayments_payment_id == payment_id)
    result = await session.execute(stmt)
    return result.scalars().first()

async def add_tickets(session: AsyncSession, user_id: int, round_id: int, ticket_count: int):
    """Compatibility wrapper for adding tickets."""
    await add_tickets_for_payment(session, user_id, round_id, ticket_count)

async def get_user_tickets_count(session: AsyncSession, user_id: int, round_id: int) -> int:
    """Counts a user's tickets for a specific round."""
    stmt = select(func.count(Ticket.id)).where(Ticket.user_id == user_id, Ticket.round_id == round_id)
    result = await session.execute(stmt)
    return result.scalar_one()
