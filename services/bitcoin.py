import os
import re
import time
import asyncio
import logging
from typing import Callable, Optional

import httpx

log = logging.getLogger(__name__)

# Simple in-memory cache to reduce external calls and rate-limit risks
_CACHE_VALUE: Optional[str] = None
_CACHE_TS: float = 0.0
_CACHE_TTL_SEC: int = int(os.getenv("BITCOIN_HASH_CACHE_TTL_SEC", "60"))

# Optional BlockCypher token support (rate limits)
_BLOCKCYPHER_TOKEN: Optional[str] = os.getenv("BLOCKCYPHER_TOKEN")

# User-Agent header to avoid being blocked by some services
_DEFAULT_HEADERS = {
    "User-Agent": os.getenv(
        "HTTP_USER_AGENT",
        "CryptoLuckBot/1.0 (+https://example.com) httpx",
    )
}

# Backward-compatible single-URL env, and preferred multi-URL env (comma-separated)
_SINGLE_URL_ENV = os.getenv("BITCOIN_HASH_API_URL")
_MULTI_URL_ENV = os.getenv("BITCOIN_HASH_API_URLS")

# Default endpoints (ordered by preference)
_DEFAULT_APIS = [
    "https://blockstream.info/api/blocks/tip/hash",
    "https://api.blockcypher.com/v1/btc/main/blocks/latest",
    "https://blockchain.info/latestblock",
]


def _build_api_list() -> list[str]:
    # Prefer multi-URL env; fallback to single; then defaults
    if _MULTI_URL_ENV:
        urls = [u.strip() for u in _MULTI_URL_ENV.split(",") if u.strip()]
        if urls:
            return urls
    if _SINGLE_URL_ENV:
        return [_SINGLE_URL_ENV.strip()]
    return _DEFAULT_APIS


_HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _is_valid_hash(value: Optional[str]) -> bool:
    return bool(value and _HEX64_RE.match(value))


def _normalize_hash(value: str) -> str:
    return value.strip().lower()


def _parse_blockstream(response: httpx.Response) -> Optional[str]:
    # Plain text 64-hex
    text = response.text.strip()
    return text if _is_valid_hash(text) else None


def _parse_blockcypher(response: httpx.Response) -> Optional[str]:
    # JSON format, commonly {"hash": "...", ...}
    data = response.json()
    candidate = data.get("hash") or data.get("block_hash")
    return candidate if _is_valid_hash(candidate) else None


def _parse_blockchain_info(response: httpx.Response) -> Optional[str]:
    # JSON format, commonly {"hash": "...", ...}
    data = response.json()
    candidate = data.get("hash")
    return candidate if _is_valid_hash(candidate) else None


def _pick_parser(url: str) -> Callable[[httpx.Response], Optional[str]]:
    if "blockstream.info" in url:
        return _parse_blockstream
    if "blockcypher.com" in url:
        return _parse_blockcypher
    if "blockchain.info" in url:
        return _parse_blockchain_info
    # Fallback: try plain text 64-hex
    return _parse_blockstream


async def _fetch_with_retries(
    client: httpx.AsyncClient,
    url: str,
    retries: int = 2,
    initial_backoff: float = 0.75,
) -> Optional[str]:
    parser = _pick_parser(url)

    # Add token if calling BlockCypher
    headers = dict(_DEFAULT_HEADERS)
    params = {}
    if "blockcypher.com" in url and _BLOCKCYPHER_TOKEN:
        params["token"] = _BLOCKCYPHER_TOKEN

    attempt = 0
    backoff = initial_backoff
    while attempt <= retries:
        try:
            log.info("Trying to get Bitcoin hash from: %s (attempt %d)", url, attempt + 1)
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

            parsed = parser(response)
            if parsed:
                norm = _normalize_hash(parsed)
                if _is_valid_hash(norm):
                    return norm
                else:
                    log.warning("Parsed hash invalid after normalization from %s", url)
            else:
                log.warning("No valid hash found in response from %s", url)

        except httpx.TimeoutException as e:
            log.warning("Timeout from %s: %s", url, e)
        except httpx.RequestError as e:
            log.warning("Request error from %s: %s", url, e)
        except ValueError as e:
            # e.g., JSON decode error
            log.warning("Parsing error from %s: %s", url, e)
        except Exception as e:
            log.warning("Unexpected error from %s: %s", url, e)

        attempt += 1
        if attempt <= retries:
            await asyncio.sleep(backoff)
            backoff *= 1.6

    return None


async def get_latest_bitcoin_block_hash() -> str | None:
    """
    Получает хеш последнего блока Bitcoin для честного розыгрыша.
    Использует несколько API для надежности, валидацию, ретраи и кэш.
    Источники можно переопределить переменными окружения:
    - BITCOIN_HASH_API_URLS="url1,url2,..."
    - BITCOIN_HASH_API_URL="url"
    Дополнительно:
    - BITCOIN_HASH_CACHE_TTL_SEC (по умолчанию 60)
    - BLOCKCYPHER_TOKEN (для повышения лимитов BlockCypher)
    - HTTP_USER_AGENT (кастомный User-Agent)
    """
    # Cache hit
    global _CACHE_VALUE, _CACHE_TS
    now = time.time()
    if _CACHE_VALUE and (now - _CACHE_TS) < _CACHE_TTL_SEC:
        return _CACHE_VALUE

    apis = _build_api_list()

    # Granular timeouts
    timeout = httpx.Timeout(
        connect=5.0,
        read=10.0,
        write=5.0,
        pool=5.0,
    )

    # Reasonable limits for retries/backoff are implemented per-endpoint
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for api_url in apis:
            result = await _fetch_with_retries(client, api_url, retries=2, initial_backoff=0.75)
            if result:
                _CACHE_VALUE = result
                _CACHE_TS = now
                return result

    log.error("All Bitcoin API endpoints failed!")
    return None
