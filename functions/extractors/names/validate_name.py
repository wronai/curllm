"""
Function: is_valid_product_name

Validate if text looks like a valid product name.
"""

import re
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3]))

from functions.patterns.registry import register_pattern


# Register invalid patterns (navigation items, etc.)
PATTERN_INVALID_NAV = register_pattern(
    name="name.invalid.navigation",
    pattern=r'^(?:login|loguj|zaloguj|register|rejestr|sign\s*(?:in|up))',
    description="Navigation login/register items",
    examples=[
        {"input": "Login", "invalid": True},
        {"input": "Zaloguj się", "invalid": True},
    ],
    flags=re.IGNORECASE
)

PATTERN_INVALID_HOME = register_pattern(
    name="name.invalid.home",
    pattern=r'^(?:home|strona\s*główna|główna|start|main)',
    description="Home page navigation",
    examples=[
        {"input": "Home", "invalid": True},
        {"input": "Strona główna", "invalid": True},
    ],
    flags=re.IGNORECASE
)

PATTERN_INVALID_ACTION = register_pattern(
    name="name.invalid.action",
    pattern=r'^(?:next|prev|poprzedni|następn|more|więcej|zobacz|read|click|kliknij)',
    description="Action buttons",
    examples=[
        {"input": "Zobacz więcej", "invalid": True},
        {"input": "Next", "invalid": True},
    ],
    flags=re.IGNORECASE
)


def is_valid_product_name(
    text: str, 
    min_length: int = 3, 
    max_length: int = 200
) -> bool:
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
        r'^(?:home|strona\s*główna|główna)',
        r'^(?:cart|koszyk|basket|bag)',
        r'^(?:next|prev|poprzedni|następn)',
        r'^(?:more|więcej|zobacz|read)',
        r'^(?:click|kliknij|naciśnij|tap)',
        r'^(?:submit|wyślij|send)',
        r'^\d+$',  # Just numbers
        r'^[<>»«→←↑↓•·]+$',  # Just arrows/symbols
        r'^(?:menu|nav|header|footer|sidebar)',
    ]
    
    for pattern in invalid_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return False
    
    # Must have at least one letter
    if not re.search(r'[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]', text):
        return False
    
    return True


__function_meta__ = {
    "name": "is_valid_product_name",
    "category": "extractors.names",
    "description": "Check if text is a valid product name",
    "examples": [
        {"input": "iPhone 15 Pro", "output": True},
        {"input": "Login", "output": False},
        {"input": "Zobacz więcej", "output": False},
    ],
    "tags": ["name", "validation", "filter"]
}
