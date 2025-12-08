from typing import Any, Dict, List, Callable
import functools
from ..flow import flow, Flow
from ..registry import list_components, list_schemes
from ...diagnostics import get_logger

logger = get_logger(__name__)


def retry(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorator to retry component operations
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between attempts in seconds
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed: {e}"
                    )
                    
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
                        
            raise last_exception
            
        return wrapper
        
    return decorator
