"""
Fallback Chain

Execute multiple strategies with automatic fallback on failure.
"""

import logging
import functools
from typing import Callable, Any, Optional, List, TypeVar, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class FallbackResult:
    """Result of fallback chain execution."""
    
    success: bool
    value: Any = None
    strategy_used: str = ""
    strategies_tried: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)


class FallbackChain:
    """
    Chain of extraction strategies with automatic fallback.
    
    Example:
        chain = FallbackChain()
        chain.add("regex", extract_with_regex)
        chain.add("heuristic", extract_with_heuristic)
        chain.add("llm", extract_with_llm)
        
        result = chain.execute(text)
        print(f"Used strategy: {result.strategy_used}")
    """
    
    def __init__(self, name: str = "chain"):
        self.name = name
        self._strategies: List[tuple] = []  # (name, func, validator)
    
    def add(
        self,
        name: str,
        func: Callable[..., T],
        validator: Callable[[T], bool] = None,
        priority: int = 0
    ) -> "FallbackChain":
        """
        Add a strategy to the chain.
        
        Args:
            name: Strategy name for logging
            func: Function to execute
            validator: Optional function to validate result
            priority: Higher priority = tried first
            
        Returns:
            self for chaining
        """
        self._strategies.append((name, func, validator, priority))
        # Sort by priority (descending)
        self._strategies.sort(key=lambda x: x[3], reverse=True)
        return self
    
    def execute(self, *args, **kwargs) -> FallbackResult:
        """
        Execute strategies until one succeeds.
        
        Args:
            *args: Arguments for strategy functions
            **kwargs: Keyword arguments
            
        Returns:
            FallbackResult with value or errors
        """
        tried = []
        errors = {}
        
        for name, func, validator, _ in self._strategies:
            tried.append(name)
            
            try:
                result = func(*args, **kwargs)
                
                # Check if result is valid
                if result is None:
                    errors[name] = "Returned None"
                    continue
                
                # Apply validator if provided
                if validator:
                    if not validator(result):
                        errors[name] = "Failed validation"
                        continue
                
                # Success!
                logger.debug(f"{self.name}: Strategy '{name}' succeeded")
                return FallbackResult(
                    success=True,
                    value=result,
                    strategy_used=name,
                    strategies_tried=tried,
                )
                
            except Exception as e:
                errors[name] = str(e)
                logger.debug(f"{self.name}: Strategy '{name}' failed: {e}")
        
        # All strategies failed
        logger.warning(f"{self.name}: All {len(tried)} strategies failed")
        return FallbackResult(
            success=False,
            strategies_tried=tried,
            errors=errors,
        )
    
    async def execute_async(self, *args, **kwargs) -> FallbackResult:
        """
        Execute strategies asynchronously.
        
        Same as execute() but supports async strategy functions.
        """
        tried = []
        errors = {}
        
        for name, func, validator, _ in self._strategies:
            tried.append(name)
            
            try:
                # Check if function is async
                if callable(func):
                    import inspect
                    if inspect.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                if result is None:
                    errors[name] = "Returned None"
                    continue
                
                if validator and not validator(result):
                    errors[name] = "Failed validation"
                    continue
                
                return FallbackResult(
                    success=True,
                    value=result,
                    strategy_used=name,
                    strategies_tried=tried,
                )
                
            except Exception as e:
                errors[name] = str(e)
        
        return FallbackResult(
            success=False,
            strategies_tried=tried,
            errors=errors,
        )


def with_fallbacks(*fallback_funcs: Callable, validator: Callable = None):
    """
    Decorator to add fallback functions.
    
    Args:
        *fallback_funcs: Functions to try if main fails
        validator: Optional result validator
        
    Example:
        @with_fallbacks(extract_v2, extract_v3)
        def extract(text):
            return extract_v1(text)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            # Try main function
            try:
                result = func(*args, **kwargs)
                if result is not None:
                    if validator is None or validator(result):
                        return result
            except Exception as e:
                logger.debug(f"{func.__name__} failed: {e}")
            
            # Try fallbacks
            for fallback in fallback_funcs:
                try:
                    result = fallback(*args, **kwargs)
                    if result is not None:
                        if validator is None or validator(result):
                            logger.debug(f"Fallback {fallback.__name__} succeeded")
                            return result
                except Exception as e:
                    logger.debug(f"Fallback {fallback.__name__} failed: {e}")
            
            return None
        
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern - stop trying after too many failures.
    
    Example:
        breaker = CircuitBreaker(max_failures=3, reset_timeout=60)
        
        if breaker.is_open:
            return cached_result
        
        try:
            result = risky_operation()
            breaker.record_success()
            return result
        except Exception:
            breaker.record_failure()
            raise
    """
    
    def __init__(
        self,
        max_failures: int = 5,
        reset_timeout: float = 60.0
    ):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._last_failure_time: Optional[float] = None
        self._state = "closed"  # closed, open, half-open
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (should not try)."""
        if self._state == "open":
            # Check if reset timeout has passed
            import time
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.reset_timeout:
                    self._state = "half-open"
                    return False
            return True
        return False
    
    def record_success(self):
        """Record successful operation."""
        self._failures = 0
        self._state = "closed"
    
    def record_failure(self):
        """Record failed operation."""
        import time
        self._failures += 1
        self._last_failure_time = time.time()
        
        if self._failures >= self.max_failures:
            self._state = "open"
            logger.warning(f"Circuit breaker opened after {self._failures} failures")
    
    def reset(self):
        """Manually reset the circuit breaker."""
        self._failures = 0
        self._state = "closed"
        self._last_failure_time = None
