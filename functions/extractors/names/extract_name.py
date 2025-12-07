"""
Function: extract_product_name

Extract product name from text that may contain HTML.
"""

import re
from typing import Optional
from .clean_name import clean_product_name


def extract_product_name(text: str) -> Optional[str]:
    """
    Extract product name from text that may contain HTML.
    
    Args:
        text: Text possibly containing HTML
        
    Returns:
        Extracted product name
    """
    if not text:
        return None
    
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', ' ', text)
    
    # Remove common prefixes
    prefixes = ['product:', 'nazwa:', 'name:', 'tytuł:', 'title:']
    for prefix in prefixes:
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix):]
    
    return clean_product_name(clean)


__function_meta__ = {
    "name": "extract_product_name",
    "category": "extractors.names",
    "description": "Extract product name from HTML-like text",
    "examples": [
        {"input": "<h3>iPhone 15</h3>", "output": "iPhone 15"},
        {"input": "Product: Laptop Dell", "output": "Laptop Dell"},
    ],
    "tags": ["name", "product", "html"]
}
