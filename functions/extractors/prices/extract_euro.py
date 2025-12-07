"""
Function: extract_euro_price

Extract Euro price (EUR/€) from text.
"""

import re
from typing import Optional
from .normalize import normalize_price_string


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
        r'€\s*(\d+[\d\s\.]*[,\.]\d{2})',
        r'(\d+[\d\s\.]*[,\.]\d{2})\s*(?:€|EUR)',
        r'€\s*(\d+[\d\s\.]*)',
        r'(\d+[\d\s\.]*)\s*(?:€|EUR)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_price_string(match.group(1))
    
    return None


__function_meta__ = {
    "name": "extract_euro_price",
    "category": "extractors.prices",
    "description": "Extract Euro price (EUR/€) from text",
    "examples": [
        {"input": "€99.99", "output": 99.99},
        {"input": "1.234,56 EUR", "output": 1234.56},
    ],
    "tags": ["price", "euro", "eur"]
}
