# python
import logging
import os
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)


# ------------------------------
# Helpers to read environment variables with parsing and safe fallbacks
# ------------------------------
def getenv_str(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)


def getenv_int(name: str, default: Optional[int] = None) -> Optional[int]:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        log.warning(f"Invalid int for {name}={val!r}. Falling back to default {default!r}.")
        return default


def getenv_float(name: str, default: Optional[float] = None) -> Optional[float]:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        log.warning(f"Invalid float for {name}={val!r}. Falling back to default {default!r}.")
        return default


# ------------------------------
# Core Bot Settings
# ------------------------------
API_TOKEN: Optional[str] = getenv_str("API_TOKEN")
ADMIN_ID: Optional[int] = getenv_int("ADMIN_ID")
ANNOUNCE_CHANNEL_ID: Optional[int] = getenv_int("ANNOUNCE_CHANNEL_ID")

# ------------------------------
# Database Settings
# ------------------------------
DATABASE_URL: str = getenv_str("DATABASE_URL", "sqlite+aiosqlite:///data/cryptoluck.db")  # type: ignore[assignment]

# ------------------------------
# Lottery Settings
# ------------------------------
TICKET_PRICE_USD: float = float(getenv_float("TICKET_PRICE_USD", 0.5))
PRIZE_USD: float = float(getenv_float("PRIZE_USD", 10.0))
MIN_BANK_USD: float = float(getenv_float("MIN_BANK_USD", 10.0))

# ------------------------------
# Payout Settings
# ------------------------------
PAYOUT_CURRENCY_CODE: str = getenv_str("PAYOUT_CURRENCY_CODE", "TRX") or "TRX"
PAYOUT_CURRENCY_NAME: str = getenv_str("PAYOUT_CURRENCY_NAME", "TRON") or "TRON"
PAYOUT_WALLET_VALIDATION_REGEX: str = getenv_str("PAYOUT_WALLET_VALIDATION_REGEX",
                                                 r"^T[A-Za-z1-9]{33}$") or r"^T[A-Za-z1-9]{33}$"

# ------------------------------
# NOWPayments API Settings
# ------------------------------
NOWPAYMENTS_API_KEY: Optional[str] = getenv_str("NOWPAYMENTS_API_KEY")
NOWPAYMENTS_IPN_SECRET: Optional[str] = getenv_str("NOWPAYMENTS_IPN_SECRET")

# ------------------------------
# Webhook Settings
# ------------------------------
SERVER_HOSTNAME: Optional[str] = getenv_str("SERVER_HOSTNAME")
IPN_CALLBACK_URL: Optional[str] = f"https://{SERVER_HOSTNAME}/payments/ipn" if SERVER_HOSTNAME else None

# ------------------------------
# Supported Currencies for Payments
# ------------------------------
MIN_PAYMENT_USD: float = 0.5  # shared minimum across currencies

# A single source of truth for supported currencies
SUPPORTED_CURRENCY_DEFS = [
    ("hbar", "Hedera", "HOME_WALLET_HBAR"),
    ("trx", "TRON", "HOME_WALLET_TRX"),
    ("xrp", "Ripple", "HOME_WALLET_XRP"),
]

SUPPORTED_CURRENCIES: Dict[str, Dict[str, Any]] = {
    code: {
        "code": code,
        "name": name,
        "min_payment_usd": MIN_PAYMENT_USD,
        "home_wallet": getenv_str(wallet_env),
    }
    for code, name, wallet_env in SUPPORTED_CURRENCY_DEFS
}

# ------------------------------
# Language Settings
# ------------------------------
LANGUAGES: list[str] = ["en", "es", "pt", "fr"]
DEFAULT_LANGUAGE: str = "en"

# Exported names for clarity when using "from config import *"
__all__ = [
    "API_TOKEN",
    "ADMIN_ID",
    "ANNOUNCE_CHANNEL_ID",
    "DATABASE_URL",
    "TICKET_PRICE_USD",
    "PRIZE_USD",
    "MIN_BANK_USD",
    "PAYOUT_CURRENCY_CODE",
    "PAYOUT_CURRENCY_NAME",
    "PAYOUT_WALLET_VALIDATION_REGEX",
    "NOWPAYMENTS_API_KEY",
    "NOWPAYMENTS_IPN_SECRET",
    "SERVER_HOSTNAME",
    "IPN_CALLBACK_URL",
    "SUPPORTED_CURRENCIES",
    "LANGUAGES",
    "DEFAULT_LANGUAGE",
]
