"""
Screenshot Component - Page and element screenshots

Atomic operations:
- capture_page: Full page screenshot
- capture_element: Element screenshot
- capture_viewport: Visible viewport screenshot
"""

from .capture import (
    capture_page,
    capture_element,
    capture_viewport,
    get_screenshot_path
)

__all__ = [
    'capture_page',
    'capture_element',
    'capture_viewport',
    'get_screenshot_path'
]
