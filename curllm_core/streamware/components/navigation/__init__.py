"""
Navigation Component - Browser navigation and interaction actions

Atomic operations:
- click: Click on element
- fill: Fill input field
- scroll: Scroll page
- wait: Wait for timeout
- navigate: Go to URL
"""

from .actions import (
    click,
    fill_field,
    scroll_page,
    wait,
    auto_scroll,
    execute_action
)

__all__ = [
    'click',
    'fill_field', 
    'scroll_page',
    'wait',
    'auto_scroll',
    'execute_action'
]
