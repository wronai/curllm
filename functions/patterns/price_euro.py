"""
Pattern: Euro Price (EUR/€)

Matches Euro price formats.
"""

import re
from typing import Optional
from .registry import register_pattern, get_pattern


PATTERN = register_pattern(
    name="price.euro",
    pattern=r'€\s*(\d+[\d\s\.]*[,\.]\d{2})',
    description="Euro price with € symbol",
    examples=[
        {"input": "€99.99", "expected": "99.99"},
        {"input": "€ 1.234,56", "expected": "1.234,56"},
    ],
    flags=re.IGNORECASE
)

PATTERN_SUFFIX = register_pattern(
    name="price.euro.suffix",
    pattern=r'(\d+[\d\s\.]*[,\.]\d{2})\s*(?:€|EUR)',
    description="Euro price with EUR suffix",
    examples=[
        {"input": "99.99 EUR", "expected": "99.99"},
        {"input": "1.234,56€", "expected": "1.234,56"},
    ],
    flags=re.IGNORECASE
)


def extract(text: str) -> Optional[str]:
    """Extract Euro price string from text."""
    if not text:
        return None
    
    for pattern_name in ["price.euro", "price.euro.suffix"]:
        pattern = get_pattern(pattern_name)
        if pattern:
            match = pattern.match(text)
            if match:
                pattern.record_success()
                return match.group(1)
            else:
                pattern.record_failure()
    
    return None
