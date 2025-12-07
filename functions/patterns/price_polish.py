"""
Pattern: Polish Price (PLN/zł)

Matches Polish price formats like:
- 1 234,56 zł
- 999.99 PLN
- od 500 zł
"""

import re
from typing import Optional, Tuple
from .registry import register_pattern, get_pattern


# Register the pattern
PATTERN = register_pattern(
    name="price.polish",
    pattern=r'(\d+[\d\s]*[,\.]\d{2})\s*(?:zł|PLN|złotych)',
    description="Polish price with decimal (e.g., 1 234,56 zł)",
    examples=[
        {"input": "1 234,56 zł", "expected": "1 234,56"},
        {"input": "999.99 PLN", "expected": "999.99"},
        {"input": "cena: 50,00 złotych", "expected": "50,00"},
    ],
    flags=re.IGNORECASE
)

PATTERN_INTEGER = register_pattern(
    name="price.polish.integer",
    pattern=r'(\d+[\d\s]*)\s*(?:zł|PLN|złotych)',
    description="Polish price without decimal (e.g., 500 zł)",
    examples=[
        {"input": "500 zł", "expected": "500"},
        {"input": "1 000 PLN", "expected": "1 000"},
    ],
    flags=re.IGNORECASE
)

PATTERN_FROM = register_pattern(
    name="price.polish.from",
    pattern=r'od\s*(\d+[\d\s]*[,\.]?\d*)\s*(?:zł|PLN)',
    description="Polish 'from' price (e.g., od 500 zł)",
    examples=[
        {"input": "od 500 zł", "expected": "500"},
        {"input": "od 1 234,56 PLN", "expected": "1 234,56"},
    ],
    flags=re.IGNORECASE
)


def extract(text: str) -> Optional[str]:
    """
    Extract Polish price string from text.
    
    Args:
        text: Text containing price
        
    Returns:
        Price string or None
    """
    if not text:
        return None
    
    # Try patterns in order of specificity
    for pattern_name in ["price.polish", "price.polish.from", "price.polish.integer"]:
        pattern = get_pattern(pattern_name)
        if pattern:
            match = pattern.match(text)
            if match:
                pattern.record_success()
                return match.group(1)
            else:
                pattern.record_failure()
    
    return None


def extract_with_currency(text: str) -> Optional[Tuple[str, str]]:
    """
    Extract price and currency from text.
    
    Returns:
        Tuple of (price_string, currency) or None
    """
    result = extract(text)
    if result:
        return (result, "PLN")
    return None
