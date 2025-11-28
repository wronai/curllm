"""
DOM Component - DOM analysis and utilities

Atomic operations:
- analyze: Analyze DOM structure
- query: Query DOM elements
- diff: Compare DOM states
- context: Capture page context
"""

from .analyze import (
    analyze_structure,
    get_depth_stats,
    find_repeating_patterns
)
from .context import (
    capture_context,
    capture_visible_text,
    capture_form_state
)
from .query import (
    query_elements,
    query_text,
    query_attributes
)

__all__ = [
    'analyze_structure',
    'get_depth_stats', 
    'find_repeating_patterns',
    'capture_context',
    'capture_visible_text',
    'capture_form_state',
    'query_elements',
    'query_text',
    'query_attributes'
]
