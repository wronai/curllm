"""
Price Extraction Functions

Atomic functions for extracting and parsing prices from text.
"""

import re
from typing import Optional, Tuple
import sys
sys.path.insert(0, str(__file__).rsplit('/', 3)[0])

from functions.registry import register_function


@register_function(
    category="extractors",
    description="Extract Polish price (zł/PLN) from text",
    examples=[
        {"input": "1 234,56 zł", "output": 1234.56},
        {"input": "999.99 PLN", "output": 999.99},
        {"input": "od 500 zł", "output": 500.0},
    ],
    tags=["price", "polish", "pln"]
)
def extract_polish_price(text: str) -> Optional[float]:
    """
    Extract Polish price from text.
    
    Handles formats:
    - 1 234,56 zł
    - 999.99 PLN
    - od 500 zł
    
    Args:
        text: Text containing price
        
    Returns:
        Price as float or None if not found
    """
    if not text:
        return None
    
    # Pattern for Polish prices
    patterns = [
        r'(\d+[\d\s]*[,\.]\d{2})\s*(?:zł|PLN|złotych)',
        r'(\d+[\d\s]*)\s*(?:zł|PLN|złotych)',
        r'od\s*(\d+[\d\s]*[,\.]\d{2})\s*(?:zł|PLN)',
        r'od\s*(\d+[\d\s]*)\s*(?:zł|PLN)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1)
            return normalize_price_string(price_str)
    
    return None


@register_function(
    category="extractors",
    description="Extract Euro price from text",
    examples=[
        {"input": "€99.99", "output": 99.99},
        {"input": "1.234,56 EUR", "output": 1234.56},
    ],
    tags=["price", "euro", "eur"]
)
def extract_euro_price(text: str) -> Optional[float]:
    """
    Extract Euro price from text.
    
    Args:
        text: Text containing price
        
    Returns:
        Price as float or None
    """
    if not text:
        return None
    
    patterns = [
        r'€\s*(\d+[\d\s]*[,\.]\d{2})',
        r'(\d+[\d\s]*[,\.]\d{2})\s*(?:€|EUR)',
        r'€\s*(\d+[\d\s]*)',
        r'(\d+[\d\s]*)\s*(?:€|EUR)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1)
            return normalize_price_string(price_str)
    
    return None


@register_function(
    category="extractors",
    description="Extract USD price from text",
    examples=[
        {"input": "$99.99", "output": 99.99},
        {"input": "USD 1,234.56", "output": 1234.56},
    ],
    tags=["price", "usd", "dollar"]
)
def extract_usd_price(text: str) -> Optional[float]:
    """
    Extract USD price from text.
    
    Args:
        text: Text containing price
        
    Returns:
        Price as float or None
    """
    if not text:
        return None
    
    patterns = [
        r'\$\s*(\d+[\d,]*[\.]\d{2})',
        r'(\d+[\d,]*[\.]\d{2})\s*(?:\$|USD)',
        r'\$\s*(\d+[\d,]*)',
        r'(\d+[\d,]*)\s*(?:\$|USD)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1)
            # USD uses comma as thousands separator
            price_str = price_str.replace(',', '')
            return float(price_str)
    
    return None


@register_function(
    category="extractors", 
    description="Extract any price from text, auto-detecting currency",
    examples=[
        {"input": "1 234,56 zł", "output": (1234.56, "PLN")},
        {"input": "$99.99", "output": (99.99, "USD")},
        {"input": "€50", "output": (50.0, "EUR")},
    ],
    tags=["price", "universal"]
)
def extract_any_price(text: str) -> Optional[Tuple[float, str]]:
    """
    Extract price with auto-detected currency.
    
    Args:
        text: Text containing price
        
    Returns:
        Tuple of (price, currency) or None
    """
    if not text:
        return None
    
    # Try each currency
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


@register_function(
    category="extractors",
    description="Normalize price string to float",
    examples=[
        {"input": "1 234,56", "output": 1234.56},
        {"input": "999.99", "output": 999.99},
    ],
    tags=["price", "normalize"]
)
def normalize_price_string(price_str: str) -> Optional[float]:
    """
    Normalize price string to float.
    
    Handles:
    - Spaces as thousands separators
    - Comma or dot as decimal separator
    
    Args:
        price_str: Price string
        
    Returns:
        Price as float or None
    """
    if not price_str:
        return None
    
    try:
        # Remove spaces
        clean = price_str.replace(' ', '').replace('\xa0', '')
        
        # Handle comma as decimal separator (European format)
        if ',' in clean and '.' in clean:
            # Both present - comma is thousands, dot is decimal
            clean = clean.replace(',', '')
        elif ',' in clean:
            # Only comma - it's decimal separator
            clean = clean.replace(',', '.')
        
        return float(clean)
    except (ValueError, TypeError):
        return None


@register_function(
    category="extractors",
    description="Extract price range (from-to)",
    examples=[
        {"input": "100-200 zł", "output": (100.0, 200.0)},
        {"input": "od 50 do 100 PLN", "output": (50.0, 100.0)},
    ],
    tags=["price", "range"]
)
def extract_price_range(text: str) -> Optional[Tuple[float, float]]:
    """
    Extract price range from text.
    
    Args:
        text: Text containing price range
        
    Returns:
        Tuple of (min_price, max_price) or None
    """
    if not text:
        return None
    
    # Pattern: X-Y zł or X - Y zł
    match = re.search(
        r'(\d+[\d\s]*[,\.]?\d*)\s*[-–]\s*(\d+[\d\s]*[,\.]?\d*)\s*(?:zł|PLN|€|EUR|\$|USD)?',
        text,
        re.IGNORECASE
    )
    if match:
        min_p = normalize_price_string(match.group(1))
        max_p = normalize_price_string(match.group(2))
        if min_p is not None and max_p is not None:
            return (min_p, max_p)
    
    # Pattern: od X do Y
    match = re.search(
        r'od\s*(\d+[\d\s]*[,\.]?\d*)\s*(?:do|-)?\s*(\d+[\d\s]*[,\.]?\d*)',
        text,
        re.IGNORECASE
    )
    if match:
        min_p = normalize_price_string(match.group(1))
        max_p = normalize_price_string(match.group(2))
        if min_p is not None and max_p is not None:
            return (min_p, max_p)
    
    return None
