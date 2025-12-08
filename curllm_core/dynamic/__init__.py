"""
Dynamic Detection Module - Replace hardcoded values with LLM-based detection

This module provides functions to dynamically find elements, URLs, and patterns
without hardcoded selectors or values.

Usage:
    from curllm_core.dynamic import (
        find_form_fields,
        find_submit_button,
        find_url_for_intent,
        detect_success_message,
        detect_error_message,
    )
"""

from curllm_core.dynamic.selectors import (
    find_form_fields,
    find_submit_button,
    find_input_by_purpose,
    find_clickable_by_intent,
    find_container_by_content,
)

from curllm_core.dynamic.urls import (
    find_url_for_intent,
    find_login_url,
    find_contact_url,
    find_cart_url,
    discover_sitemap_urls,
)

from curllm_core.dynamic.messages import (
    detect_success_message,
    detect_error_message,
    detect_captcha,
    detect_form_validation_error,
)

from curllm_core.dynamic.patterns import (
    detect_price_pattern,
    detect_product_container,
    detect_list_pattern,
    detect_pagination,
)

__all__ = [
    # Selectors
    'find_form_fields',
    'find_submit_button',
    'find_input_by_purpose',
    'find_clickable_by_intent',
    'find_container_by_content',
    # URLs
    'find_url_for_intent',
    'find_login_url',
    'find_contact_url',
    'find_cart_url',
    'discover_sitemap_urls',
    # Messages
    'detect_success_message',
    'detect_error_message',
    'detect_captcha',
    'detect_form_validation_error',
    # Patterns
    'detect_price_pattern',
    'detect_product_container',
    'detect_list_pattern',
    'detect_pagination',
]
