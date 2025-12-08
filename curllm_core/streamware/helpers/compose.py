from typing import Any, Dict, List, Callable
import functools
from ..flow import flow, Flow
from ..registry import list_components, list_schemes
from ...diagnostics import get_logger


def compose(*functions: Callable) -> Callable:
    """
    Compose multiple functions into a single function
    
    Args:
        *functions: Functions to compose
        
    Returns:
        Composed function
        
    Example:
        f = compose(func1, func2, func3)
        result = f(data)  # Equivalent to func3(func2(func1(data)))
    """
    def composed(data):
        result = data
        for func in functions:
            result = func(result)
        return result
        
    return composed
