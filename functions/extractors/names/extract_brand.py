"""
Function: extract_brand

Extract brand name from product name.
"""

import re
from typing import Optional, List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3]))

from functions.patterns.registry import register_pattern


# Known brands pattern (can be extended by LLM)
KNOWN_BRANDS = [
    'Apple', 'Samsung', 'Dell', 'HP', 'Lenovo', 'Asus', 'Acer',
    'Sony', 'LG', 'Xiaomi', 'Huawei', 'Nokia', 'Motorola',
    'Microsoft', 'Google', 'OnePlus', 'Oppo', 'Vivo', 'Realme',
    'Philips', 'Panasonic', 'Bosch', 'Siemens', 'Electrolux',
    'Nike', 'Adidas', 'Puma', 'Reebok', 'New Balance',
    'Intel', 'AMD', 'NVIDIA', 'Corsair', 'Logitech', 'Razer',
    'Canon', 'Nikon', 'Sony', 'Fujifilm', 'Olympus',
    'Toyota', 'Honda', 'BMW', 'Mercedes', 'Audi', 'Volkswagen',
    'IKEA', 'Zara', 'H&M', 'Levis', 'Gucci', 'Prada',
]

# Register pattern for brand at start
PATTERN_BRAND_START = register_pattern(
    name="name.brand.start",
    pattern=r'^([A-Z][a-zA-Z0-9&]+)\s+',
    description="Brand at start of product name",
    examples=[
        {"input": "Samsung Galaxy S24", "match": "Samsung"},
        {"input": "Apple iPhone 15", "match": "Apple"},
    ],
    flags=0
)


def extract_brand(text: str, known_brands: List[str] = None) -> Optional[str]:
    """
    Extract brand name from product name.
    
    Args:
        text: Product name
        known_brands: Optional list of known brands to check
        
    Returns:
        Brand name or None
    """
    if not text:
        return None
    
    brands = known_brands or KNOWN_BRANDS
    text_lower = text.lower()
    
    # Check against known brands
    for brand in brands:
        if brand.lower() in text_lower:
            # Verify it's at word boundary
            pattern = rf'\b{re.escape(brand)}\b'
            if re.search(pattern, text, re.IGNORECASE):
                return brand
    
    # Try to extract first word if it looks like a brand
    words = text.split()
    if not words:
        return None
    
    first_word = words[0]
    
    # Brand heuristics:
    # - Starts with uppercase
    # - Length > 2
    # - Not a generic word
    generic_words = [
        'the', 'new', 'best', 'top', 'super', 'ultra', 'pro', 'max',
        'mini', 'lite', 'plus', 'premium', 'original', 'genuine',
        'official', 'authentic', 'classic', 'modern', 'smart',
        'nowy', 'nowa', 'nowe', 'super', 'mega', 'premium',
    ]
    
    if (first_word[0].isupper() and 
        len(first_word) > 2 and 
        first_word.lower() not in generic_words):
        
        # Additional check: not all caps (probably acronym, not brand)
        if not first_word.isupper() or len(first_word) <= 4:
            return first_word
    
    return None


def add_brand(brand: str):
    """Add a brand to the known brands list."""
    if brand not in KNOWN_BRANDS:
        KNOWN_BRANDS.append(brand)


__function_meta__ = {
    "name": "extract_brand",
    "category": "extractors.names",
    "description": "Extract brand name from product name",
    "examples": [
        {"input": "Apple iPhone 15 Pro", "output": "Apple"},
        {"input": "Samsung Galaxy S24", "output": "Samsung"},
        {"input": "Laptop Dell XPS 15", "output": "Dell"},
    ],
    "tags": ["name", "brand", "manufacturer"]
}
