import logging
import hmac
import hashlib
import httpx
from typing import Optional, Dict
from config import NOWPAYMENTS_API_KEY, IPN_CALLBACK_URL, SUPPORTED_CURRENCIES, NOWPAYMENTS_IPN_SECRET

API_URL = "https://api.nowpayments.io/v1"
log = logging.getLogger(__name__)


class NowPaymentsAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"x-api-key": self.api_key}

    async def create_payment(self, price_usd: float, pay_currency: str, order_id: str) -> dict | None:
        """
        Creates a payment invoice via NOWPayments API.
        """
        if not self.api_key or self.api_key == "development_default":
            log.error("NOWPayments API key is not set. Cannot create payment.")
            return None

        normalized_currency = pay_currency.upper()
        if normalized_currency not in SUPPORTED_CURRENCIES:
            log.error(f"Unsupported payment currency: {pay_currency}")
            return None

        payload = {
            "price_amount": price_usd,
            "price_currency": "usd",
            "pay_currency": normalized_currency,
            "ipn_callback_url": IPN_CALLBACK_URL,
            "order_id": order_id
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                log.info(f"Creating payment with payload: {payload}")
                response = await client.post(f"{API_URL}/payment", json=payload, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                log.info(f"Successfully created payment {data.get('payment_id')} for order {order_id}")
                return data
            except httpx.HTTPStatusError as e:
                log.error(
                    f"HTTP error creating payment for order {order_id}: "
                    f"{e.response.status_code} - {e.response.text}"
                )
                return None
            except Exception as e:
                log.error(f"An unexpected error occurred while creating payment for order {order_id}: {e}")
                return None

    async def get_payment_status(self, payment_id: str) -> dict | None:
        """
        Gets the status of a payment from NOWPayments.
        """
        if not self.api_key or self.api_key == "development_default":
            log.error("NOWPayments API key is not set. Cannot get payment status.")
            return None

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(f"{API_URL}/payment/{payment_id}", headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                log.error(
                    f"HTTP error getting payment status for {payment_id}: "
                    f"{e.response.status_code} - {e.response.text}"
                )
                return None
            except Exception as e:
                log.error(f"An unexpected error occurred while getting status for payment {payment_id}: {e}")
                return None

    async def create_payout_single(
        self,
        currency: str,
        amount: float,
        address: str,
        idempotency_key: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Creates a single payout from NOWPayments custody balance.
        Requires funds available on NOWPayments account and payouts enabled.
        """
        if not self.api_key or self.api_key == "development_default":
            log.error("NOWPayments API key is not set. Cannot create payout.")
            return None

        currency = currency.upper()
        payload = {
            "currency": currency,
            "amount": float(amount),
            "address": address,
        }

        headers = dict(self.headers)
        # Many APIs support Idempotency-Key; if NP supports, pass it; harmless otherwise.
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                log.info(f"Creating payout: {payload}")
                response = await client.post(f"{API_URL}/payout", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                log.info(f"Payout created successfully: {data}")
                return data
            except httpx.HTTPStatusError as e:
                log.error(
                    f"HTTP error creating payout [{currency} {amount} -> {address}]: "
                    f"{e.response.status_code} - {e.response.text}"
                )
                return None
            except Exception as e:
                log.error(f"Unexpected error creating payout [{currency} {amount} -> {address}]: {e}")
                return None


def verify_ipn_signature(request_body: bytes, signature: str | None) -> bool:
    if not NOWPAYMENTS_IPN_SECRET:
        log.error("NOWPAYMENTS_IPN_SECRET is not set")
        return False
    if not signature:
        log.warning("IPN signature header is missing")
        return False
    expected = hmac.new(NOWPAYMENTS_IPN_SECRET.encode("utf-8"), request_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


# Создаем единый экземпляр API клиента
now_payments_api = NowPaymentsAPI(NOWPAYMENTS_API_KEY)

async def create_payment(user_id: int, round_id: int, currency_code: str, amount_usd: float) -> dict | None:
    """
    Упрощенная обертка над NOWPayments API: создает платеж для пользователя и раунда.
    """
    order_id = f"{user_id}:{round_id}"
    return await now_payments_api.create_payment(
        price_usd=amount_usd,
        pay_currency=currency_code,
        order_id=order_id
    )
