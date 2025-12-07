"""
Safe Function Wrappers

Provides decorators and utilities for safe function execution
with error handling and fallbacks.
"""

import logging
import functools
from typing import Callable, Any, Optional, TypeVar, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class ExtractionResult:
    """Result of a safe extraction with error info."""
    
    success: bool
    value: Any = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    fallback_used: bool = False
    attempts: int = 1


def safe_call(
    func: Callable[..., T],
    *args,
    default: T = None,
    log_errors: bool = True,
    error_prefix: str = "",
    **kwargs
) -> T:
    """
    Safely call a function, returning default on any exception.
    
    Args:
        func: Function to call
        *args: Positional arguments
        default: Default value on error
        log_errors: Whether to log errors
        error_prefix: Prefix for error messages
        **kwargs: Keyword arguments
        
    Returns:
        Function result or default value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            prefix = f"{error_prefix}: " if error_prefix else ""
            logger.warning(f"{prefix}Error in {func.__name__}: {e}")
        return default


def safe_extract(
    func: Callable[..., T],
    *args,
    **kwargs
) -> ExtractionResult:
    """
    Safely execute an extraction function with detailed result.
    
    Args:
        func: Extraction function
        *args: Arguments for function
        **kwargs: Keyword arguments
        
    Returns:
        ExtractionResult with value or error info
    """
    try:
        result = func(*args, **kwargs)
        return ExtractionResult(
            success=True,
            value=result,
        )
    except TypeError as e:
        return ExtractionResult(
            success=False,
            error=str(e),
            error_type="TypeError",
        )
    except ValueError as e:
        return ExtractionResult(
            success=False,
            error=str(e),
            error_type="ValueError",
        )
    except AttributeError as e:
        return ExtractionResult(
            success=False,
            error=str(e),
            error_type="AttributeError",
        )
    except KeyError as e:
        return ExtractionResult(
            success=False,
            error=str(e),
            error_type="KeyError",
        )
    except Exception as e:
        return ExtractionResult(
            success=False,
            error=str(e),
            error_type=type(e).__name__,
        )


def with_fallback(*fallback_funcs: Callable):
    """
    Decorator that tries fallback functions on failure.
    
    Args:
        *fallback_funcs: Functions to try if main function fails
        
    Example:
        @with_fallback(extract_price_v2, extract_price_regex)
        def extract_price(text):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Try main function
            try:
                result = func(*args, **kwargs)
                if result is not None:
                    return result
            except Exception as e:
                logger.debug(f"{func.__name__} failed: {e}")
            
            # Try fallbacks
            for fallback in fallback_funcs:
                try:
                    result = fallback(*args, **kwargs)
                    if result is not None:
                        logger.debug(f"Using fallback: {fallback.__name__}")
                        return result
                except Exception as e:
                    logger.debug(f"Fallback {fallback.__name__} failed: {e}")
            
            return None
        
        return wrapper
    return decorator


def safe_property(default: Any = None):
    """
    Decorator for safe property access that returns default on error.
    
    Example:
        @safe_property(default="")
        def get_text(element):
            return element.textContent.strip()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (AttributeError, TypeError, KeyError):
                return default
        return wrapper
    return decorator


class SafeExtractor:
    """
    Context manager for safe extraction with automatic error handling.
    
    Example:
        with SafeExtractor() as extractor:
            price = extractor.call(extract_price, text)
            name = extractor.call(extract_name, text)
            
        if extractor.has_errors:
            print(extractor.errors)
    """
    
    def __init__(self, stop_on_error: bool = False):
        self.stop_on_error = stop_on_error
        self.results: List[ExtractionResult] = []
        self.errors: List[str] = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> Optional[T]:
        """
        Safely call a function and track result.
        
        Returns:
            Function result or None on error
        """
        result = safe_extract(func, *args, **kwargs)
        self.results.append(result)
        
        if not result.success:
            self.errors.append(f"{func.__name__}: {result.error}")
            if self.stop_on_error:
                raise RuntimeError(result.error)
        
        return result.value
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def success_rate(self) -> float:
        if not self.results:
            return 0.0
        successes = sum(1 for r in self.results if r.success)
        return successes / len(self.results)


def guard_none(func: Callable[..., T]) -> Callable[..., Optional[T]]:
    """
    Decorator that returns None if any argument is None.
    
    Example:
        @guard_none
        def process(text):
            return text.upper()
        
        process(None)  # Returns None instead of raising AttributeError
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Check positional args
        for arg in args:
            if arg is None:
                return None
        
        # Check keyword args
        for value in kwargs.values():
            if value is None:
                return None
        
        return func(*args, **kwargs)
    
    return wrapper
