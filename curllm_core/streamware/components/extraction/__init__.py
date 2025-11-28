"""
Extraction Components for Streamware

Atomic functions for data extraction using LLM.
No hardcoded selectors - LLM determines what to extract.

Components:
- selector.py: LLM-based selector discovery
- extractor.py: Data extraction from DOM
- container.py: Dynamic container detection
"""

from .selector import find_selector_llm, find_all_selectors
from .extractor import extract_data, extract_emails, extract_links, extract_products
from .container import (
    detect_containers,
    detect_container_with_llm,
    extract_from_container
)

__all__ = [
    'find_selector_llm', 'find_all_selectors',
    'extract_data', 'extract_emails', 'extract_links', 'extract_products',
    'detect_containers', 'detect_container_with_llm', 'extract_from_container'
]
