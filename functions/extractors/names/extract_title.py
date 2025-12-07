"""
Function: extract_title

Extract clean title from page title string.
"""

import re
from typing import Optional


def extract_title(text: str, max_length: int = 150) -> Optional[str]:
    """
    Extract clean title from page title string.
    
    Removes common suffixes like site names after separators.
    
    Args:
        text: Page title
        max_length: Maximum length
        
    Returns:
        Cleaned title
    """
    if not text:
        return None
    
    result = text
    
    # Split on common delimiters and take first meaningful part
    delimiters = [' | ', ' - ', ' :: ', ' — ', ' » ', ' • ']
    
    for delim in delimiters:
        if delim in result:
            parts = result.split(delim)
            # Take longest part under 100 chars (usually the actual title)
            valid_parts = [p for p in parts if len(p.strip()) > 3 and len(p) < 100]
            if valid_parts:
                result = max(valid_parts, key=len)
                break
    
    # Remove common suffixes in parentheses
    result = re.sub(r'\s*\([^)]*(?:PL|EN|US|UK|DE|FR)\)\s*$', '', result, flags=re.IGNORECASE)
    
    # Remove common site name patterns
    result = re.sub(r'\s*[-|]\s*(?:sklep|shop|store|oficjalny)\s*$', '', result, flags=re.IGNORECASE)
    
    result = result.strip()
    
    if len(result) > max_length:
        result = result[:max_length].rsplit(' ', 1)[0]
    
    return result if result else None


__function_meta__ = {
    "name": "extract_title",
    "category": "extractors.names",
    "description": "Extract title from page or article",
    "examples": [
        {"input": "Best Laptops 2024 | TechReview", "output": "Best Laptops 2024"},
        {"input": "iPhone 15 Pro Max - Apple (PL)", "output": "iPhone 15 Pro Max"},
    ],
    "tags": ["title", "article", "page"]
}
