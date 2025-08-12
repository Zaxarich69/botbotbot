# python
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import all_handlers_routers
from services.ipn import router as ipn_router
from services.storage import init_db, SessionLocal, get_active_round, get_round_total_collected
from services.scheduler import setup_scheduler
from middlewares.session import DbSessionMiddleware
from config import API_TOKEN, IPN_CALLBACK_URL, NOWPAYMENTS_API_KEY

# ===== Logging =====
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# ===== App constants =====
APP_TITLE = "CryptoLuck Bot"
APP_VERSION = "1.0.0"
DOCS_URL = "/docs"
HEALTH_URL = "/health"
LOCAL_BASE_URL = "http://localhost:8080"

# Development mode flag (env override supported; default True for local dev convenience)
IS_DEV_MODE = os.getenv("DEV_MODE", "true").strip().lower() in {"1", "true", "yes"}


def mode_label() -> str:
    return "development" if IS_DEV_MODE else "production"


def bot_status_label() -> str:
    # In development we do not start the telegram bot
    return "disabled" if IS_DEV_MODE else "running"


async def database_init_with_logging() -> None:
    try:
        await init_db()
        log.info("✅ Database initialized successfully")
    except Exception as e:
        log.error(f"❌ Failed to initialize database: {e}")
        raise


def ensure_valid_token(token: Optional[str]) -> str:
    if not token or token == "development_default":
        raise ValueError(
            "Valid API_TOKEN is required for production mode. "
            "Please get a token from @BotFather in Telegram."
        )
    return token


def _warn_runtime_config() -> None:
    """
    Log warnings for optional but recommended runtime configuration.
    These checks do not fail the app; they help avoid silent misconfiguration.
    """
    if not NOWPAYMENTS_API_KEY:
        log.warning("⚠ NOWPAYMENTS_API_KEY is not set. Payments/IPN may not function.")
    if not IPN_CALLBACK_URL:
        log.warning("⚠ IPN_CALLBACK_URL is not set. IPN callbacks will not be registered.")


async def _shutdown_scheduler_if_any(app: FastAPI) -> None:
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler is None:
        return
    try:
        # APScheduler AsyncIOScheduler.shutdown() is sync; attempt both safely.
        maybe_coro = scheduler.shutdown(wait=False)
        if asyncio.iscoroutine(maybe_coro):
            await maybe_coro
    except Exception as e:
        log.warning(f"Scheduler shutdown warning: {e}")


async def setup_production(app: FastAPI) -> None:
    token = ensure_valid_token(API_TOKEN)
    _warn_runtime_config()

    bot = Bot(token=token, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware for DB session management
    dp.update.middleware(DbSessionMiddleware(session_pool=SessionLocal))

    # Register all handler routers
    for router in all_handlers_routers:
        dp.include_router(router)

    # Initialize database
    await database_init_with_logging()

    # Setup lottery scheduler
    try:
        scheduler = setup_scheduler(bot)
        app.state.scheduler = scheduler
        log.info("✅ Lottery scheduler initialized successfully")
    except Exception as e:
        log.error(f"❌ Failed to setup scheduler: {e}")
        raise

    # Save instances and start polling
    app.state.bot = bot
    app.state.dp = dp

    async def _polling():
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        except asyncio.CancelledError:
            # normal during shutdown
            pass
        except Exception as e:
            log.exception(f"Polling crashed: {e}")
            raise

    app.state.polling_task = asyncio.create_task(_polling(), name="telegram-polling")
    log.info("✅ Bot polling started successfully")


async def shutdown_bot(app: FastAPI) -> None:
    log.info("🛑 Shutting down CryptoLuck Bot application...")

    # Stop polling task
    polling_task: Optional[asyncio.Task] = getattr(app.state, "polling_task", None)
    if polling_task is not None:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass

    # Shutdown scheduler if present
    await _shutdown_scheduler_if_any(app)

    # Close bot session
    bot_instance: Optional[Bot] = getattr(app.state, "bot", None)
    if bot_instance is not None:
        try:
            await bot_instance.session.close()
        except Exception as e:
            log.warning(f"Bot session close warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log.info("🚀 Starting CryptoLuck Bot application...")

    if IS_DEV_MODE:
        log.warning("🔧 Running in DEVELOPMENT MODE - Telegram bot features disabled")
        app.state.bot = None
        app.state.scheduler = None
        await database_init_with_logging()
        log.info(f"🌐 Web interface available at {LOCAL_BASE_URL}")
        log.info(f"📋 API docs available at {LOCAL_BASE_URL}{DOCS_URL}")
        try:
            yield
        finally:
            # nothing to shutdown beyond DB pool in this file
            pass
        return

    # Production mode
    await setup_production(app)
    try:
        yield
    finally:
        await shutdown_bot(app)


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

# IPN router (works in any mode)
app.include_router(ipn_router, prefix="/payments", tags=["Payments"])


@app.get("/")
async def root():
    if IS_DEV_MODE:
        return {
            "message": f"{APP_TITLE} - Development Mode",
            "status": mode_label(),
            "telegram_bot": bot_status_label(),
            "database": "active",
            "docs_url": DOCS_URL,
            "health_url": HEALTH_URL,
        }
    return {
        "message": f"{APP_TITLE} is running!",
        "status": mode_label(),
        "bot": "active",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "mode": mode_label(),
        "bot": bot_status_label(),
    }


@app.get("/status")
async def status():
    """Detailed system status"""
    try:
        async with SessionLocal() as session:
            active_round = await get_active_round(session)
            if active_round:
                total_collected = await get_round_total_collected(session, active_round.id)
                return {
                    "database": "connected",
                    "active_round": {
                        "id": active_round.id,
                        "total_collected": total_collected,
                        "prize_amount": active_round.prize_amount,
                        "status": active_round.status,
                    },
                    "mode": mode_label(),
                }
            else:
                return {
                    "database": "connected",
                    "active_round": None,
                    "mode": mode_label(),
                }
    except Exception as e:
        log.error(f"/status error: {e}")
        return {
            "database": "error",
            "error": "unexpected_error",
            "mode": mode_label(),
        }