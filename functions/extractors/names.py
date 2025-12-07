"""
Name/Title Extraction Functions

Atomic functions for extracting and cleaning product names and titles.
"""

import re
from typing import Optional
import sys
sys.path.insert(0, str(__file__).rsplit('/', 3)[0])

from functions.registry import register_function


@register_function(
    category="extractors",
    description="Clean product name - remove prices, special chars, normalize whitespace",
    examples=[
        {"input": "iPhone 15 Pro 999 zł", "output": "iPhone 15 Pro"},
        {"input": "  Samsung Galaxy   S24  ", "output": "Samsung Galaxy S24"},
    ],
    tags=["name", "product", "clean"]
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
        r'\d+\s*(?:zł|PLN|€|EUR|\$|USD)',
        r'od\s*\d+[\d\s]*[,\.]?\d*\s*(?:zł|PLN)?',
        r'(?:cena|price)[:\s]*\d+',
    ]
    
    for pattern in price_patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # Remove common suffixes
    suffixes = [
        r'\s*[-–]\s*\d+\s*szt\.?',
        r'\s*\(\d+\s*szt\.?\)',
        r'\s*x\s*\d+',
    ]
    for pattern in suffixes:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # Normalize whitespace
    result = ' '.join(result.split())
    
    # Truncate if needed
    if len(result) > max_length:
        result = result[:max_length].rsplit(' ', 1)[0]
    
    return result.strip() if result.strip() else None


@register_function(
    category="extractors",
    description="Extract product name from HTML-like text with tags",
    examples=[
        {"input": "<h3>iPhone 15</h3>", "output": "iPhone 15"},
        {"input": "Product: Laptop Dell", "output": "Laptop Dell"},
    ],
    tags=["name", "product", "html"]
)
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


@register_function(
    category="extractors",
    description="Extract title from page or article",
    examples=[
        {"input": "Best Laptops 2024 | TechReview", "output": "Best Laptops 2024"},
        {"input": "iPhone 15 Pro Max - Apple (PL)", "output": "iPhone 15 Pro Max"},
    ],
    tags=["title", "article"]
)
def extract_title(text: str, max_length: int = 150) -> Optional[str]:
    """
    Extract clean title from page title string.
    
    Removes common suffixes like site names.
    
    Args:
        text: Page title
        max_length: Maximum length
        
    Returns:
        Cleaned title
    """
    if not text:
        return None
    
    result = text
    
    # Split on common delimiters and take first part
    delimiters = [' | ', ' - ', ' :: ', ' — ', ' » ']
    for delim in delimiters:
        if delim in result:
            parts = result.split(delim)
            # Take longest meaningful part (usually the actual title)
            result = max(parts, key=lambda p: len(p) if len(p) < 100 else 0)
            break
    
    # Remove common suffixes in parentheses
    result = re.sub(r'\s*\([^)]*(?:PL|EN|US|UK|DE)\)\s*$', '', result, flags=re.IGNORECASE)
    
    result = result.strip()
    
    if len(result) > max_length:
        result = result[:max_length].rsplit(' ', 1)[0]
    
    return result if result else None


@register_function(
    category="extractors",
    description="Check if text looks like a valid product name",
    examples=[
        {"input": "iPhone 15 Pro", "output": True},
        {"input": "Login", "output": False},
        {"input": "Zobacz więcej", "output": False},
    ],
    tags=["name", "validation"]
)
def is_valid_product_name(text: str, min_length: int = 3, max_length: int = 200) -> bool:
    """
    Check if text looks like a valid product name.
    
    Args:
        text: Text to check
        min_length: Minimum length
        max_length: Maximum length
        
    Returns:
        True if looks like valid product name
    """
    if not text:
        return False
    
    text = text.strip()
    
    # Length check
    if len(text) < min_length or len(text) > max_length:
        return False
    
    # Invalid patterns - navigation items
    invalid_patterns = [
        r'^(?:login|loguj|zaloguj|register|rejestr)',
        r'^(?:home|strona główna|główna)',
        r'^(?:cart|koszyk|basket)',
        r'^(?:next|prev|poprzedni|następn)',
        r'^(?:more|więcej|zobacz|read)',
        r'^(?:click|kliknij|naciśnij)',
        r'^\d+$',  # Just numbers
        r'^[<>»«→←]+$',  # Just arrows
    ]
    
    for pattern in invalid_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return False
    
    return True


@register_function(
    category="extractors",
    description="Extract brand from product name",
    examples=[
        {"input": "Apple iPhone 15 Pro", "output": "Apple"},
        {"input": "Samsung Galaxy S24", "output": "Samsung"},
        {"input": "Laptop Dell XPS 15", "output": "Dell"},
    ],
    tags=["name", "brand"]
)
def extract_brand(text: str) -> Optional[str]:
    """
    Extract brand name from product name.
    
    Args:
        text: Product name
        
    Returns:
        Brand name or None
    """
    if not text:
        return None
    
    known_brands = [
        'Apple', 'Samsung', 'Dell', 'HP', 'Lenovo', 'Asus', 'Acer',
        'Sony', 'LG', 'Xiaomi', 'Huawei', 'Nokia', 'Motorola',
        'Microsoft', 'Google', 'OnePlus', 'Oppo', 'Vivo', 'Realme',
        'Philips', 'Panasonic', 'Bosch', 'Siemens', 'Electrolux',
        'Nike', 'Adidas', 'Puma', 'Reebok', 'New Balance',
        'Intel', 'AMD', 'NVIDIA', 'Corsair', 'Logitech', 'Razer',
    ]
    
    text_lower = text.lower()
    
    for brand in known_brands:
        if brand.lower() in text_lower:
            return brand
    
    # Try to extract first word if it looks like a brand
    first_word = text.split()[0] if text.split() else None
    if first_word and first_word[0].isupper() and len(first_word) > 2:
        # Check if it's not a generic word
        generic = ['the', 'new', 'best', 'top', 'super', 'ultra', 'pro', 'max']
        if first_word.lower() not in generic:
            return first_word
    
    return None
