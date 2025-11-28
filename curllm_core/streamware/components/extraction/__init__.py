"""
Extraction Components for Streamware

Atomic functions for data extraction using LLM.
No hardcoded selectors - LLM determines what to extract.

Components:
- selector.py: LLM-based selector discovery
- extractor.py: Data extraction from DOM
- validator.py: Validate extracted data
"""

from .selector import find_selector_llm, find_all_selectors
from .extractor import extract_data, extract_emails, extract_links, extract_products

__all__ = [
    'find_selector_llm', 'find_all_selectors',
    'extract_data', 'extract_emails', 'extract_links', 'extract_products'
]
