"""
Function: extract_usd_price

Extract USD price ($/USD) from text.
"""

import re
from typing import Optional


def extract_usd_price(text: str) -> Optional[float]:
    """
    Extract USD price from text.
    
    USD uses:
    - Comma as thousands separator (1,234)
    - Dot as decimal separator (99.99)
    
    Args:
        text: Text containing price
        
    Returns:
        Price as float or None
    """
    if not text:
        return None
    
    patterns = [
        r'\$\s*(\d+[\d,]*\.?\d*)',
        r'(\d+[\d,]*\.?\d*)\s*(?:\$|USD)',
        r'USD\s*(\d+[\d,]*\.?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1)
            # USD format: comma is thousands separator
            price_str = price_str.replace(',', '')
            try:
                return float(price_str)
            except ValueError:
                continue
    
    return None


__function_meta__ = {
    "name": "extract_usd_price",
    "category": "extractors.prices",
    "description": "Extract USD price ($/USD) from text",
    "examples": [
        {"input": "$99.99", "output": 99.99},
        {"input": "USD 1,234.56", "output": 1234.56},
    ],
    "tags": ["price", "usd", "dollar"]
}
