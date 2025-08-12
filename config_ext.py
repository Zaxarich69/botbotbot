# Helper defaults for pricing and currencies
MIN_TICKETS_PER_PAYMENT = 2

# Optional extension map for currencies (можно подключить позже, если потребуется расширение валют)
EXT_SUPPORTED_CURRENCIES = {
    "XRP": {"code": "xrp", "name": "Ripple (XRP)", "min_payment_usd": 0.2},
    "TRX": {"code": "trx", "name": "Tron (TRX)", "min_payment_usd": 0.2},
    "USDTTRC20": {"code": "usdttrc20", "name": "Tether TRC20", "min_payment_usd": 0.2},
    "HBAR": {"code": "hbar", "name": "Hedera Hashgraph (HBAR)", "min_payment_usd": 0.2},
}
