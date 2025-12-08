"""
DOM module - DOM manipulation and element finding helpers

Classes and functions for working with DOM elements,
finding links, buttons, inputs, and analyzing page structure.
"""

from curllm_core.dom.helpers import (
    LinkInfo,
    ElementInfo,
    extract_all_links,
    find_links_by_text,
    find_links_by_url_pattern,
    find_links_by_location,
    find_links_by_aria,
    find_elements_by_role,
    find_buttons,
    find_inputs,
    find_link_for_goal,
    try_direct_urls,
    find_search_input,
    execute_search,
    analyze_page_type,
    has_content_type,
    # SPA hydration utilities
    wait_for_spa_hydration,
    wait_for_interactive_elements,
    wait_for_navigation_ready,
    ensure_page_ready,
)

__all__ = [
    'LinkInfo',
    'ElementInfo',
    'extract_all_links',
    'find_links_by_text',
    'find_links_by_url_pattern',
    'find_links_by_location',
    'find_links_by_aria',
    'find_elements_by_role',
    'find_buttons',
    'find_inputs',
    'find_link_for_goal',
    'try_direct_urls',
    'find_search_input',
    'execute_search',
    'analyze_page_type',
    'has_content_type',
    # SPA hydration utilities
    'wait_for_spa_hydration',
    'wait_for_interactive_elements',
    'wait_for_navigation_ready',
    'ensure_page_ready',
]
