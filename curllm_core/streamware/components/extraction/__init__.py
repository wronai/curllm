"""
Extraction Components for Streamware

Atomic functions for data extraction using LLM.
No hardcoded selectors - LLM determines what to extract.
NO REGEX - Pure LLM-based extraction.

Components:
- page_analyzer.py: LLM-based page type detection
- container_finder.py: LLM-based container detection
- field_detector.py: LLM-based field detection
- llm_extractor.py: Main LLM iterative extractor
- selector.py: LLM-based selector discovery (legacy)
- extractor.py: Data extraction from DOM (legacy)
- container.py: Dynamic container detection (legacy)
"""

# New LLM-based atomic functions
from .page_analyzer import analyze_page_type, detect_price_format
from .container_finder import find_product_containers, analyze_container_content
from .field_detector import detect_product_fields, extract_field_value, detect_price_in_container
from .llm_extractor import LLMIterativeExtractor, llm_extract_products
from .llm_patterns import (
    generate_price_pattern,
    generate_product_link_pattern,
    generate_container_selector,
    generate_field_selector,
    generate_extraction_strategy,
    validate_selector
)

# Legacy imports (backward compatibility)
from .selector import find_selector_llm, find_all_selectors
from .extractor import extract_data, extract_emails, extract_links, extract_products
from .container import (
    detect_containers,
    detect_container_with_llm,
    extract_from_container
)

__all__ = [
    # New LLM-based (recommended)
    'LLMIterativeExtractor', 'llm_extract_products',
    'analyze_page_type', 'detect_price_format',
    'find_product_containers', 'analyze_container_content',
    'detect_product_fields', 'extract_field_value', 'detect_price_in_container',
    # LLM Pattern generators (NO REGEX in code)
    'generate_price_pattern', 'generate_product_link_pattern',
    'generate_container_selector', 'generate_field_selector',
    'generate_extraction_strategy', 'validate_selector',
    # Legacy (backward compatibility)
    'find_selector_llm', 'find_all_selectors',
    'extract_data', 'extract_emails', 'extract_links', 'extract_products',
    'detect_containers', 'detect_container_with_llm', 'extract_from_container'
]
