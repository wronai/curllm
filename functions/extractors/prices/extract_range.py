"""
Function: extract_price_range

Extract price range (min-max) from text.
"""

import re
from typing import Optional, Tuple
from .normalize import normalize_price_string


def extract_price_range(text: str) -> Optional[Tuple[float, float]]:
    """
    Extract price range from text.
    
    Matches formats:
    - 100-200 zł
    - 100 - 200 PLN
    - od 50 do 100 zł
    - from 50 to 100
    
    Args:
        text: Text containing price range
        
    Returns:
        Tuple of (min_price, max_price) or None
    """
    if not text:
        return None
    
    # Pattern: X-Y zł (with optional currency)
    patterns = [
        r'(\d+[\d\s]*[,\.]?\d*)\s*[-–—]\s*(\d+[\d\s]*[,\.]?\d*)\s*(?:zł|PLN|€|EUR|\$|USD)?',
        r'od\s*(\d+[\d\s]*[,\.]?\d*)\s*(?:do|-|–)?\s*(\d+[\d\s]*[,\.]?\d*)',
        r'from\s*(\d+[\d\s]*[,\.]?\d*)\s*to\s*(\d+[\d\s]*[,\.]?\d*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            min_p = normalize_price_string(match.group(1))
            max_p = normalize_price_string(match.group(2))
            if min_p is not None and max_p is not None:
                # Ensure min < max
                if min_p > max_p:
                    min_p, max_p = max_p, min_p
                return (min_p, max_p)
    
    return None


__function_meta__ = {
    "name": "extract_price_range",
    "category": "extractors.prices",
    "description": "Extract price range (min-max) from text",
    "examples": [
        {"input": "100-200 zł", "output": (100.0, 200.0)},
        {"input": "od 50 do 100 PLN", "output": (50.0, 100.0)},
    ],
    "tags": ["price", "range", "min-max"]
}
