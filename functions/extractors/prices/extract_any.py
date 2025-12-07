"""
Function: extract_any_price

Extract price from text with auto-detected currency.
"""

from typing import Optional, Tuple
from .extract_polish import extract_polish_price
from .extract_euro import extract_euro_price
from .extract_usd import extract_usd_price
from .normalize import normalize_price_string
import re


def extract_any_price(text: str) -> Optional[Tuple[float, str]]:
    """
    Extract price with auto-detected currency.
    
    Tries multiple currencies in order: PLN, EUR, USD, then generic.
    
    Args:
        text: Text containing price
        
    Returns:
        Tuple of (price, currency) or None
    """
    if not text:
        return None
    
    # Try each currency in order
    pln = extract_polish_price(text)
    if pln is not None:
        return (pln, "PLN")
    
    eur = extract_euro_price(text)
    if eur is not None:
        return (eur, "EUR")
    
    usd = extract_usd_price(text)
    if usd is not None:
        return (usd, "USD")
    
    # Try generic number as fallback
    match = re.search(r'(\d+[\d\s]*[,\.]\d{2})', text)
    if match:
        price = normalize_price_string(match.group(1))
        if price:
            return (price, "UNKNOWN")
    
    return None


__function_meta__ = {
    "name": "extract_any_price",
    "category": "extractors.prices",
    "description": "Extract price with auto-detected currency",
    "examples": [
        {"input": "1 234,56 zł", "output": (1234.56, "PLN")},
        {"input": "$99.99", "output": (99.99, "USD")},
        {"input": "€50", "output": (50.0, "EUR")},
    ],
    "tags": ["price", "universal", "auto-detect"]
}
