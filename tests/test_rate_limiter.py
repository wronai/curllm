"""Tests for rate_limiter module."""

import pytest
import asyncio
import time

pytestmark = pytest.mark.asyncio

from curllm_core.rate_limiter import (
    RateLimiter,
    AdaptiveRateLimiter,
    get_rate_limiter,
    reset_global_limiter,
)


class TestRateLimiter:
    """Test the RateLimiter class."""
    
    def test_init(self):
        """Test initialization."""
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.rpm == 60
        assert limiter.burst == 5
        assert limiter.default_delay == 0.5
    
    def test_extract_domain_from_url(self):
        """Test domain extraction from URL."""
        limiter = RateLimiter()
        
        assert limiter._extract_domain("https://example.com/path") == "example.com"
        assert limiter._extract_domain("http://sub.example.com:8080/") == "sub.example.com:8080"
        assert limiter._extract_domain("example.com") == "example.com"
    
    @pytest.mark.asyncio
    async def test_first_request_no_wait(self):
        """First request should not wait."""
        limiter = RateLimiter(requests_per_minute=60, default_delay=0)
        
        start = time.time()
        await limiter.acquire("example.com")
        elapsed = time.time() - start
        
        assert elapsed < 0.1
    
    @pytest.mark.asyncio
    async def test_respects_default_delay(self):
        """Consecutive requests should respect default delay."""
        limiter = RateLimiter(requests_per_minute=60, default_delay=0.1)
        
        await limiter.acquire("example.com")
        
        start = time.time()
        await limiter.acquire("example.com")
        elapsed = time.time() - start
        
        assert elapsed >= 0.08  # Allow some timing slack
    
    @pytest.mark.asyncio
    async def test_different_domains_independent(self):
        """Different domains should have independent limits."""
        limiter = RateLimiter(requests_per_minute=60, default_delay=0.1)
        
        await limiter.acquire("example.com")
        
        # Different domain should not wait
        start = time.time()
        await limiter.acquire("other.com")
        elapsed = time.time() - start
        
        assert elapsed < 0.05
    
    def test_get_remaining_capacity(self):
        """Test remaining capacity calculation."""
        limiter = RateLimiter(requests_per_minute=10, burst_allowance=2)
        
        assert limiter.get_remaining_capacity("example.com") == 12  # 10 + 2
        
        # Simulate some requests
        limiter.domain_timestamps["example.com"] = [time.time()] * 5
        assert limiter.get_remaining_capacity("example.com") == 7
    
    def test_get_stats(self):
        """Test stats retrieval."""
        limiter = RateLimiter(requests_per_minute=30, burst_allowance=5)
        
        stats = limiter.get_stats("example.com")
        
        assert stats["domain"] == "example.com"
        assert stats["limit"] == 30
        assert stats["burst"] == 5
        assert stats["remaining"] == 35
    
    def test_reset_specific_domain(self):
        """Test resetting a specific domain."""
        limiter = RateLimiter()
        limiter.domain_timestamps["example.com"] = [time.time()] * 10
        limiter.domain_timestamps["other.com"] = [time.time()] * 5
        
        limiter.reset("example.com")
        
        assert len(limiter.domain_timestamps["example.com"]) == 0
        assert len(limiter.domain_timestamps["other.com"]) == 5
    
    def test_reset_all(self):
        """Test resetting all domains."""
        limiter = RateLimiter()
        limiter.domain_timestamps["example.com"] = [time.time()] * 10
        limiter.domain_timestamps["other.com"] = [time.time()] * 5
        
        limiter.reset()
        
        assert len(limiter.domain_timestamps) == 0


class TestAdaptiveRateLimiter:
    """Test the AdaptiveRateLimiter class."""
    
    def test_init(self):
        """Test initialization."""
        limiter = AdaptiveRateLimiter(requests_per_minute=30)
        assert limiter.initial_rpm == 30
        assert limiter.min_rpm == 5
    
    def test_record_429_reduces_rate(self):
        """429 response should reduce rate limit."""
        limiter = AdaptiveRateLimiter(requests_per_minute=30, backoff_factor=0.5)
        
        limiter.record_error("example.com", status_code=429)
        
        assert limiter.domain_rpm["example.com"] == 15  # 30 * 0.5
    
    def test_repeated_errors_reduce_rate(self):
        """Multiple errors should reduce rate."""
        limiter = AdaptiveRateLimiter(requests_per_minute=30, backoff_factor=0.5)
        
        # Record 3 errors
        limiter.record_error("example.com")
        limiter.record_error("example.com")
        limiter.record_error("example.com")
        
        assert limiter.domain_rpm["example.com"] == 15
    
    def test_success_recovers_rate(self):
        """Consistent success should recover rate."""
        limiter = AdaptiveRateLimiter(
            requests_per_minute=30,
            recovery_factor=2.0
        )
        
        # First reduce rate
        limiter.domain_rpm["example.com"] = 10
        
        # Record 10 successes
        for _ in range(10):
            limiter.record_success("example.com")
        
        # Rate should increase
        assert limiter.domain_rpm["example.com"] > 10
    
    def test_rate_does_not_exceed_initial(self):
        """Rate should not exceed initial value."""
        limiter = AdaptiveRateLimiter(
            requests_per_minute=30,
            recovery_factor=2.0
        )
        
        limiter.domain_rpm["example.com"] = 25
        
        # Record many successes
        for _ in range(20):
            limiter.record_success("example.com")
        
        assert limiter.domain_rpm["example.com"] <= 30


class TestGlobalLimiter:
    """Test global limiter functions."""
    
    def test_get_rate_limiter_singleton(self):
        """get_rate_limiter should return same instance."""
        reset_global_limiter()
        
        limiter1 = get_rate_limiter(requests_per_minute=30)
        limiter2 = get_rate_limiter(requests_per_minute=60)  # Should be ignored
        
        assert limiter1 is limiter2
        assert limiter1.rpm == 30
        
        reset_global_limiter()
    
    def test_reset_global_limiter(self):
        """reset_global_limiter should clear state."""
        limiter = get_rate_limiter()
        limiter.domain_timestamps["example.com"] = [time.time()] * 10
        
        reset_global_limiter()
        
        # Should have no timestamps after reset
        assert len(limiter.domain_timestamps.get("example.com", [])) == 0
