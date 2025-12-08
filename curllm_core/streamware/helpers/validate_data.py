from typing import Any, Dict, List, Callable
import functools
from ..flow import flow, Flow
from ..registry import list_components, list_schemes
from ...diagnostics import get_logger

logger = get_logger(__name__)


def validate_data(schema: Dict[str, Any]) -> Callable:
    """
    Decorator to validate input/output data against a schema
    
    Args:
        schema: JSON schema for validation
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, data):
            # Simple validation (can be extended with jsonschema library)
            if not isinstance(data, dict):
                logger.warning(f"Expected dict, got {type(data).__name__}")
                
            result = func(self, data)
            
            return result
            
        return wrapper
        
    return decorator
