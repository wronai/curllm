"""
Function: normalize_price_string

Normalize price string to float.
"""

from typing import Optional


def normalize_price_string(price_str: str) -> Optional[float]:
    """
    Normalize price string to float.
    
    Handles:
    - Spaces as thousands separators (1 234 -> 1234)
    - Comma as decimal separator (99,99 -> 99.99)
    - Dot as thousands separator in European format (1.234,56 -> 1234.56)
    
    Args:
        price_str: Price string
        
    Returns:
        Price as float or None
    """
    if not price_str:
        return None
    
    try:
        # Remove non-breaking spaces and regular spaces
        clean = price_str.replace(' ', '').replace('\xa0', '')
        
        # Handle European format: 1.234,56
        if ',' in clean and '.' in clean:
            # Dot is thousands, comma is decimal
            if clean.index('.') < clean.index(','):
                clean = clean.replace('.', '').replace(',', '.')
            else:
                # Comma is thousands, dot is decimal (less common)
                clean = clean.replace(',', '')
        elif ',' in clean:
            # Only comma - it's decimal separator
            clean = clean.replace(',', '.')
        
        return float(clean)
    except (ValueError, TypeError):
        return None


# Export for registry
__function_meta__ = {
    "name": "normalize_price_string",
    "category": "extractors.prices",
    "description": "Normalize price string to float",
    "examples": [
        {"input": "1 234,56", "output": 1234.56},
        {"input": "999.99", "output": 999.99},
        {"input": "1.234,56", "output": 1234.56},
    ],
    "tags": ["price", "normalize", "convert"]
}
