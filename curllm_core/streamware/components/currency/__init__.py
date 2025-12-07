"""
Currency Translation Component

Converts prices between currencies for extraction filtering.
Example: "$100" → "~450 zł" for Polish e-commerce sites.
"""

from .translator import (
    CurrencyTranslator,
    convert_price,
    detect_currency,
    normalize_price_filter,
    CURRENCY_SYMBOLS,
    EXCHANGE_RATES,
)

__all__ = [
    "CurrencyTranslator",
    "convert_price",
    "detect_currency",
    "normalize_price_filter",
    "CURRENCY_SYMBOLS",
    "EXCHANGE_RATES",
]
