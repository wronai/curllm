"""
Safety Module

Provides error handling, sanitization, and fallback mechanisms
for robust DOM processing.
"""

from .wrapper import safe_call, safe_extract, with_fallback
from .sanitize import sanitize_text, sanitize_html, normalize_whitespace
from .validate import validate_input, InputValidator
from .fallback import FallbackChain, with_fallbacks

__all__ = [
    'safe_call',
    'safe_extract', 
    'with_fallback',
    'sanitize_text',
    'sanitize_html',
    'normalize_whitespace',
    'validate_input',
    'InputValidator',
    'FallbackChain',
    'with_fallbacks',
]
