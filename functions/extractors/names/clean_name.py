"""
Function: clean_product_name

Clean product name by removing prices and normalizing whitespace.
"""

import re
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3]))

from functions.patterns.registry import register_pattern, get_pattern


# Register patterns for cleaning
PATTERN_PRICE = register_pattern(
    name="name.price_in_text",
    pattern=r'\d+[\d\s]*[,\.]\d{2}\s*(?:zł|PLN|€|EUR|\$|USD|złotych)',
    description="Price embedded in product name",
    examples=[
        {"input": "iPhone 15 Pro 999 zł", "match": "999 zł"},
    ],
    flags=re.IGNORECASE
)

PATTERN_QUANTITY = register_pattern(
    name="name.quantity",
    pattern=r'\s*[-–]\s*\d+\s*szt\.?',
    description="Quantity suffix like '- 10 szt'",
    examples=[
        {"input": "Produkt - 5 szt", "match": "- 5 szt"},
    ],
    flags=re.IGNORECASE
)


def clean_product_name(text: str, max_length: int = 200) -> Optional[str]:
    """
    Clean product name by removing prices and normalizing whitespace.
    
    Args:
        text: Raw product name
        max_length: Maximum length of result
        
    Returns:
        Cleaned product name or None
    """
    if not text:
        return None
    
    result = text
    
    # Remove price patterns
    price_patterns = [
        r'\d+[\d\s]*[,\.]\d{2}\s*(?:zł|PLN|€|EUR|\$|USD|złotych)',
        r'\d+\s*(?:zł|PLN)',
        r'od\s*\d+[\d\s]*[,\.]?\d*\s*(?:zł|PLN)?',
        r'(?:cena|price)[:\s]*\d+',
    ]
    
    for pattern in price_patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # Remove quantity patterns
    quantity_patterns = [
        r'\s*[-–]\s*\d+\s*szt\.?',
        r'\s*\(\d+\s*szt\.?\)',
        r'\s*x\s*\d+\s*$',
    ]
    
    for pattern in quantity_patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # Normalize whitespace
    result = ' '.join(result.split())
    
    # Truncate if needed
    if len(result) > max_length:
        result = result[:max_length].rsplit(' ', 1)[0]
    
    return result.strip() if result.strip() else None


__function_meta__ = {
    "name": "clean_product_name",
    "category": "extractors.names",
    "description": "Clean product name - remove prices, normalize whitespace",
    "examples": [
        {"input": "iPhone 15 Pro 999 zł", "output": "iPhone 15 Pro"},
        {"input": "  Samsung Galaxy   S24  ", "output": "Samsung Galaxy S24"},
    ],
    "tags": ["name", "product", "clean"]
}
