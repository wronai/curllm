"""Tests for retry module."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio

from curllm_core.retry import (
    retry_network,
    NetworkError,
    ExtractionError,
    RetryExhaustedError,
    RetryContext,
    execute_with_retry,
)


class TestRetryDecorator:
    """Test the retry_network decorator."""
    
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Function succeeds on first try - no retries needed."""
        call_count = 0
        
        @retry_network(max_attempts=3, initial_delay=0.01)
        async def succeeds():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await succeeds()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_success_after_retry(self):
        """Function fails once, then succeeds."""
        call_count = 0
        
        @retry_network(max_attempts=3, initial_delay=0.01)
        async def fails_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("First attempt failed")
            return "success"
        
        result = await fails_once()
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        """Function keeps failing - exhausts all retries."""
        call_count = 0
        
        @retry_network(max_attempts=3, initial_delay=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise NetworkError("Always fails")
        
        with pytest.raises(RetryExhaustedError):
            await always_fails()
        
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Non-retryable exceptions are raised immediately."""
        call_count = 0
        
        @retry_network(max_attempts=3, initial_delay=0.01)
        async def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")
        
        with pytest.raises(ValueError):
            await raises_value_error()
        
        assert call_count == 1


class TestRetryContext:
    """Test the RetryContext manager."""
    
    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """Success on first attempt."""
        attempts = 0
        
        async with RetryContext(max_attempts=3, initial_delay=0.01) as ctx:
            while ctx.should_retry():
                attempts += 1
                ctx.success()
        
        assert attempts == 1
    
    @pytest.mark.asyncio
    async def test_success_after_failures(self):
        """Success after some failures."""
        attempts = 0
        
        async with RetryContext(max_attempts=3, initial_delay=0.01) as ctx:
            while ctx.should_retry():
                attempts += 1
                try:
                    if attempts < 2:
                        raise NetworkError("Fail")
                    ctx.success()
                    break
                except NetworkError as e:
                    await ctx.failed(e)
        
        assert attempts == 2
    
    @pytest.mark.asyncio
    async def test_exhausted(self):
        """All attempts exhausted."""
        attempts = 0
        
        with pytest.raises(RetryExhaustedError):
            async with RetryContext(max_attempts=3, initial_delay=0.01) as ctx:
                while ctx.should_retry():
                    attempts += 1
                    try:
                        raise NetworkError("Always fail")
                    except NetworkError as e:
                        await ctx.failed(e)
        
        assert attempts == 3


class TestExecuteWithRetry:
    """Test the execute_with_retry function."""
    
    @pytest.mark.asyncio
    async def test_success(self):
        """Function executes successfully."""
        async def success_func(x, y):
            return x + y
        
        result = await execute_with_retry(
            success_func, 1, 2,
            max_attempts=3,
            initial_delay=0.01
        )
        assert result == 3
    
    @pytest.mark.asyncio
    async def test_retry_then_success(self):
        """Function retries and then succeeds."""
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Flaky")
            return "ok"
        
        result = await execute_with_retry(
            flaky_func,
            max_attempts=3,
            initial_delay=0.01
        )
        assert result == "ok"
        assert call_count == 2


class TestExceptions:
    """Test custom exception classes."""
    
    def test_network_error(self):
        """NetworkError can be raised and caught."""
        with pytest.raises(NetworkError):
            raise NetworkError("Connection failed")
    
    def test_extraction_error(self):
        """ExtractionError can be raised and caught."""
        with pytest.raises(ExtractionError):
            raise ExtractionError("Failed to extract")
    
    def test_retry_exhausted_error(self):
        """RetryExhaustedError can be raised and caught."""
        with pytest.raises(RetryExhaustedError):
            raise RetryExhaustedError("All retries failed")
