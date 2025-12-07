"""
Function: filter_specs

Filter technical specifications from mixed data (remove pricing, stock info).
"""

import re
from typing import Dict, Optional


# Patterns that indicate NON-technical data (to exclude)
EXCLUDE_PATTERNS = [
    r'\d+\s*szt\+?',  # "1 szt+", "10 szt+"
    r'\d+[,\.]\d{2}\s*[Zz]ł',  # Price: "82,95 Zł"
    r'rabat',  # Discount related
    r'cena',  # Price related
    r'koszt',  # Cost related
    r'magazyn',  # Stock related
    r'dostaw',  # Delivery related
    r'ilo[sś][cć]',  # Quantity related
    r'zamów',  # Order related
    r'zapytanie',  # Query/request
    r'próbk[aę]',  # Sample
]

# Patterns that indicate TECHNICAL data (to include)
TECHNICAL_PATTERNS = [
    r'voltage|napięcie|zasilanie',
    r'current|prąd|natężenie',
    r'power|moc',
    r'temperature|temperatura',
    r'pressure|ciśnienie',
    r'frequency|częstotliwość',
    r'resistance|rezystancja|oporność',
    r'capacitance|pojemność',
    r'dimension|wymiar|size|rozmiar',
    r'weight|waga|masa',
    r'accuracy|dokładność|precyzja',
    r'resolution|rozdzielczość',
    r'range|zakres',
    r'output|wyjście',
    r'input|wejście',
    r'interface|interfejs',
    r'protocol|protokół',
    r'sensor|czujnik',
    r'type|typ',
    r'series|seria',
    r'manufacturer|producent',
    r'model|model',
    r'rohs|ce|ul|fcc',
    r'mounting|montaż',
    r'case|obudowa',
    r'port|złącze|connector',
    r'msl|moisture',
]


def is_excluded(key: str, value: str) -> bool:
    """Check if key-value pair should be excluded (non-technical)."""
    text = f"{key} {value}".lower()
    
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False


def is_technical(key: str) -> bool:
    """Check if key looks like a technical specification."""
    key_lower = key.lower()
    
    for pattern in TECHNICAL_PATTERNS:
        if re.search(pattern, key_lower, re.IGNORECASE):
            return True
    
    return False


def filter_specs(data: Dict[str, str], strict: bool = False) -> Dict[str, str]:
    """
    Filter technical specifications from mixed data.
    
    Args:
        data: Dictionary of key-value pairs
        strict: If True, only include items matching technical patterns
                If False, exclude non-technical but keep unknown
                
    Returns:
        Filtered dictionary with only technical specs
    """
    if not data:
        return {}
    
    filtered = {}
    
    for key, value in data.items():
        # Skip excluded patterns (pricing, stock, etc.)
        if is_excluded(key, value):
            continue
        
        if strict:
            # Only include if matches technical pattern
            if is_technical(key):
                filtered[key] = value
        else:
            # Include if not excluded
            filtered[key] = value
    
    return filtered


def categorize_specs(data: Dict[str, str]) -> Dict[str, Dict[str, str]]:
    """
    Categorize specifications into groups.
    
    Args:
        data: Dictionary of key-value pairs
        
    Returns:
        Dictionary with categories: technical, pricing, stock, other
    """
    categories = {
        "technical": {},
        "pricing": {},
        "stock": {},
        "other": {}
    }
    
    for key, value in data.items():
        key_lower = key.lower()
        value_lower = value.lower()
        combined = f"{key_lower} {value_lower}"
        
        # Check for stock first (magazyn keyword is strong indicator)
        if re.search(r'magazyn|dostaw|dostępn', combined):
            categories["stock"][key] = value
        # Check for pricing (szt+, Zł prices)
        elif re.search(r'\d+\s*szt\+|zł|cena|rabat|koszt', combined):
            categories["pricing"][key] = value
        # Check for technical
        elif is_technical(key):
            categories["technical"][key] = value
        else:
            categories["other"][key] = value
    
    return categories


__function_meta__ = {
    "name": "filter_specs",
    "category": "extractors.specs",
    "description": "Filter technical specifications from mixed data",
    "examples": [
        {
            "input": {"Operating Pressure": "-500...500Pa", "1 szt+": "82,95 Zł"},
            "output": {"Operating Pressure": "-500...500Pa"}
        }
    ],
    "tags": ["specs", "filter", "technical"]
}
