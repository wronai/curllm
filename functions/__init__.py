"""
Functions - Atomic Reusable Operations

Provides small, reusable functions for extraction, validation, and transformation.
Functions can be discovered, loaded, and used across the system.
"""

from .registry import (
    register_function,
    get_function,
    list_functions,
    FunctionInfo,
    FunctionRegistry,
)

__all__ = [
    'register_function',
    'get_function', 
    'list_functions',
    'FunctionInfo',
    'FunctionRegistry',
]
