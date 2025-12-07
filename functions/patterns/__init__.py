"""
Adaptive Pattern System

Provides regex patterns that can be modified by LLM when they fail.
Each pattern is stored separately and can be updated at runtime.
"""

from .registry import (
    PatternRegistry,
    get_pattern,
    register_pattern,
    adapt_pattern,
)

__all__ = [
    'PatternRegistry',
    'get_pattern',
    'register_pattern', 
    'adapt_pattern',
]
