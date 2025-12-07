"""
Retry Logic for Network Operations

Provides retry decorators and utilities for handling network failures
with exponential backoff.

Usage:
    from curllm_core.retry import retry_network, navigate_with_retry
    
    @retry_network
    async def fetch_data(url):
        ...
    
    await navigate_with_retry(page, url)
"""

import asyncio
import logging
from functools import wraps
from typing import Callable, Optional, Type, Tuple

logger = logging.getLogger(__name__)


class NetworkError(Exception):
    """Network-related error (timeout, connection refused, etc.)"""
    pass


class ExtractionError(Exception):
    """Error during data extraction"""
    pass


class RetryExhaustedError(Exception):
    """All retry attempts have been exhausted"""
    pass


def retry_network(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        NetworkError,
        TimeoutError,
        ConnectionError,
    ),
):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exceptions that trigger retry
    
    Example:
        @retry_network(max_attempts=3)
        async def fetch_page(url):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Retry exhausted for {func.__name__} after {max_attempts} attempts: {e}"
                        )
                        raise RetryExhaustedError(
                            f"Failed after {max_attempts} attempts: {e}"
                        ) from e
                    
                    delay = min(
                        initial_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


async def navigate_with_retry(
    page,
    url: str,
    timeout: int = 30000,
    wait_until: str = "networkidle",
    max_attempts: int = 3,
) -> bool:
    """
    Navigate to URL with automatic retry on failure.
    
    Args:
        page: Playwright page object
        url: URL to navigate to
        timeout: Navigation timeout in milliseconds
        wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')
        max_attempts: Maximum retry attempts
    
    Returns:
        True if navigation succeeded
    
    Raises:
        NetworkError: If all retry attempts fail
    """
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = await page.goto(
                url,
                timeout=timeout,
                wait_until=wait_until
            )
            
            if response and response.ok:
                logger.debug(f"Navigation to {url} succeeded on attempt {attempt}")
                return True
            elif response:
                logger.warning(f"Navigation returned status {response.status}")
                if response.status >= 500:
                    raise NetworkError(f"Server error: {response.status}")
                return True  # 4xx errors are not retryable
            
            return True
            
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            
            # Determine if error is retryable
            is_retryable = any(keyword in error_msg for keyword in [
                'timeout', 'connection', 'network', 'refused',
                'reset', 'aborted', 'failed to load'
            ])
            
            if not is_retryable:
                logger.error(f"Non-retryable error during navigation: {e}")
                raise NetworkError(f"Navigation failed: {e}") from e
            
            if attempt < max_attempts:
                delay = min(2 ** attempt, 30)
                logger.warning(
                    f"Navigation attempt {attempt}/{max_attempts} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"Navigation failed after {max_attempts} attempts: {e}")
    
    raise NetworkError(f"Navigation to {url} failed after {max_attempts} attempts: {last_error}")


async def execute_with_retry(
    func: Callable,
    *args,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    **kwargs
):
    """
    Execute an async function with retry logic.
    
    Args:
        func: Async function to execute
        *args: Positional arguments for func
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay between retries
        **kwargs: Keyword arguments for func
    
    Returns:
        Result of func
    """
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            
            if attempt < max_attempts:
                delay = initial_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"Attempt {attempt}/{max_attempts} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
    
    raise RetryExhaustedError(f"Failed after {max_attempts} attempts") from last_error


class RetryContext:
    """
    Context manager for retry operations with state tracking.
    
    Usage:
        async with RetryContext(max_attempts=3) as ctx:
            while ctx.should_retry():
                try:
                    result = await risky_operation()
                    ctx.success()
                    break
                except Exception as e:
                    await ctx.failed(e)
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.attempt = 0
        self.last_error: Optional[Exception] = None
        self._succeeded = False
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def should_retry(self) -> bool:
        """Check if another retry attempt should be made."""
        return self.attempt < self.max_attempts and not self._succeeded
    
    def success(self):
        """Mark operation as successful."""
        self._succeeded = True
    
    async def failed(self, error: Exception):
        """
        Record failure and wait before next attempt.
        
        Args:
            error: The exception that occurred
        """
        self.attempt += 1
        self.last_error = error
        
        if self.attempt < self.max_attempts:
            delay = min(
                self.initial_delay * (2 ** (self.attempt - 1)),
                self.max_delay
            )
            logger.warning(
                f"Attempt {self.attempt}/{self.max_attempts} failed: {error}. "
                f"Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)
        else:
            raise RetryExhaustedError(
                f"Failed after {self.max_attempts} attempts"
            ) from error
