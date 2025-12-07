"""
Function: extract_polish_price

Extract Polish price (PLN/zł) from text.
Uses adaptive patterns that can be modified by LLM.
"""

from typing import Optional
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parents[3]))

from functions.patterns.registry import get_pattern, adapt_pattern
from functions.extractors.prices.normalize import normalize_price_string


async def extract_polish_price_adaptive(
    text: str,
    llm_client = None
) -> Optional[float]:
    """
    Extract Polish price with adaptive pattern matching.
    
    If pattern fails and LLM client is provided, attempts to adapt the pattern.
    
    Args:
        text: Text containing price
        llm_client: Optional LLM client for pattern adaptation
        
    Returns:
        Price as float or None
    """
    if not text:
        return None
    
    # Try each pattern
    pattern_names = ["price.polish", "price.polish.from", "price.polish.integer"]
    
    for pattern_name in pattern_names:
        pattern = get_pattern(pattern_name)
        if pattern:
            match = pattern.match(text)
            if match:
                pattern.record_success()
                return normalize_price_string(match.group(1))
    
    # All patterns failed - try to adapt if LLM available
    if llm_client and any(c in text.lower() for c in ['zł', 'pln', 'złot']):
        # This looks like it should be a Polish price
        new_pattern = await adapt_pattern(
            "price.polish",
            failed_input=text,
            context="Polish price that wasn't matched by existing patterns",
            llm_client=llm_client
        )
        
        if new_pattern:
            # Retry with adapted pattern
            pattern = get_pattern("price.polish")
            if pattern:
                match = pattern.match(text)
                if match:
                    return normalize_price_string(match.group(1))
    
    return None


def extract_polish_price(text: str) -> Optional[float]:
    """
    Extract Polish price (synchronous version).
    
    Args:
        text: Text containing price
        
    Returns:
        Price as float or None
    """
    if not text:
        return None
    
    import re
    
    # Patterns in order of specificity
    patterns = [
        r'(\d+[\d\s]*[,\.]\d{2})\s*(?:zł|PLN|złotych)',
        r'od\s*(\d+[\d\s]*[,\.]?\d*)\s*(?:zł|PLN)',
        r'(\d+[\d\s]*)\s*(?:zł|PLN|złotych)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_price_string(match.group(1))
    
    return None


# Export for registry
__function_meta__ = {
    "name": "extract_polish_price",
    "category": "extractors.prices",
    "description": "Extract Polish price (PLN/zł) from text",
    "examples": [
        {"input": "1 234,56 zł", "output": 1234.56},
        {"input": "999.99 PLN", "output": 999.99},
        {"input": "od 500 zł", "output": 500.0},
    ],
    "tags": ["price", "polish", "pln", "adaptive"]
}
