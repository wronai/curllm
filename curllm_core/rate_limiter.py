"""
Rate Limiter for Web Requests

Implements per-domain rate limiting to avoid overloading servers
and getting blocked.

Usage:
    from curllm_core.rate_limiter import RateLimiter, get_rate_limiter
    
    limiter = RateLimiter(requests_per_minute=30)
    await limiter.wait_if_needed("example.com")
    
    # Or use global limiter
    limiter = get_rate_limiter()
    await limiter.acquire("example.com")
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Per-domain rate limiter using sliding window.
    
    Tracks request timestamps per domain and enforces
    a maximum requests-per-minute limit.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 30,
        burst_allowance: int = 5,
        default_delay: float = 0.5
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute per domain
            burst_allowance: Extra requests allowed in burst
            default_delay: Minimum delay between requests (seconds)
        """
        self.rpm = requests_per_minute
        self.burst = burst_allowance
        self.default_delay = default_delay
        self.domain_timestamps: Dict[str, list] = defaultdict(list)
        self.domain_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._last_request_time: Dict[str, float] = {}
    
    def _extract_domain(self, url_or_domain: str) -> str:
        """Extract domain from URL or return as-is if already domain."""
        if url_or_domain.startswith(('http://', 'https://')):
            parsed = urlparse(url_or_domain)
            return parsed.netloc
        return url_or_domain
    
    def _cleanup_old_timestamps(self, domain: str, window_seconds: float = 60.0):
        """Remove timestamps older than the sliding window."""
        now = time.time()
        cutoff = now - window_seconds
        self.domain_timestamps[domain] = [
            ts for ts in self.domain_timestamps[domain]
            if ts > cutoff
        ]
    
    async def acquire(self, url_or_domain: str) -> float:
        """
        Acquire permission to make a request, waiting if necessary.
        
        Args:
            url_or_domain: URL or domain to rate limit
            
        Returns:
            Time waited in seconds
        """
        domain = self._extract_domain(url_or_domain)
        
        async with self.domain_locks[domain]:
            return await self._wait_if_needed_internal(domain)
    
    async def wait_if_needed(self, url_or_domain: str) -> float:
        """
        Wait if rate limit would be exceeded.
        
        Args:
            url_or_domain: URL or domain to check
            
        Returns:
            Time waited in seconds
        """
        return await self.acquire(url_or_domain)
    
    async def _wait_if_needed_internal(self, domain: str) -> float:
        """Internal wait logic (must be called with lock held)."""
        now = time.time()
        waited = 0.0
        
        # Clean up old timestamps
        self._cleanup_old_timestamps(domain)
        
        # Check if we're at the limit
        current_count = len(self.domain_timestamps[domain])
        max_allowed = self.rpm + self.burst
        
        if current_count >= max_allowed:
            # Calculate wait time based on oldest request
            oldest = min(self.domain_timestamps[domain])
            wait_time = oldest + 60.0 - now + 0.1  # +0.1s buffer
            
            if wait_time > 0:
                logger.info(
                    f"Rate limit reached for {domain} ({current_count} requests). "
                    f"Waiting {wait_time:.1f}s..."
                )
                await asyncio.sleep(wait_time)
                waited = wait_time
                now = time.time()
                self._cleanup_old_timestamps(domain)
        
        # Enforce minimum delay between requests
        last_time = self._last_request_time.get(domain, 0)
        time_since_last = now - last_time
        
        if time_since_last < self.default_delay:
            delay = self.default_delay - time_since_last
            await asyncio.sleep(delay)
            waited += delay
            now = time.time()
        
        # Record this request
        self.domain_timestamps[domain].append(now)
        self._last_request_time[domain] = now
        
        if waited > 0:
            logger.debug(f"Rate limiter waited {waited:.2f}s for {domain}")
        
        return waited
    
    def get_remaining_capacity(self, url_or_domain: str) -> int:
        """
        Get remaining request capacity for a domain.
        
        Args:
            url_or_domain: URL or domain to check
            
        Returns:
            Number of requests available before hitting limit
        """
        domain = self._extract_domain(url_or_domain)
        self._cleanup_old_timestamps(domain)
        current = len(self.domain_timestamps[domain])
        return max(0, self.rpm + self.burst - current)
    
    def get_stats(self, url_or_domain: str) -> dict:
        """
        Get rate limiting stats for a domain.
        
        Args:
            url_or_domain: URL or domain to check
            
        Returns:
            Dictionary with stats
        """
        domain = self._extract_domain(url_or_domain)
        self._cleanup_old_timestamps(domain)
        
        current = len(self.domain_timestamps[domain])
        remaining = max(0, self.rpm + self.burst - current)
        
        # Calculate time until next slot opens
        reset_in = 0.0
        if current >= self.rpm + self.burst and self.domain_timestamps[domain]:
            oldest = min(self.domain_timestamps[domain])
            reset_in = max(0, oldest + 60.0 - time.time())
        
        return {
            "domain": domain,
            "requests_in_window": current,
            "limit": self.rpm,
            "burst": self.burst,
            "remaining": remaining,
            "reset_in_seconds": round(reset_in, 1),
        }
    
    def reset(self, url_or_domain: Optional[str] = None):
        """
        Reset rate limiting state.
        
        Args:
            url_or_domain: Specific domain to reset, or None for all
        """
        if url_or_domain:
            domain = self._extract_domain(url_or_domain)
            self.domain_timestamps[domain] = []
            self._last_request_time.pop(domain, None)
            logger.debug(f"Rate limiter reset for {domain}")
        else:
            self.domain_timestamps.clear()
            self._last_request_time.clear()
            logger.debug("Rate limiter reset for all domains")


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate limiter that adapts based on server responses.
    
    Automatically reduces rate when receiving 429 (Too Many Requests)
    or other rate-limiting signals.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 30,
        min_rpm: int = 5,
        backoff_factor: float = 0.5,
        recovery_factor: float = 1.1,
        **kwargs
    ):
        super().__init__(requests_per_minute=requests_per_minute, **kwargs)
        self.initial_rpm = requests_per_minute
        self.min_rpm = min_rpm
        self.backoff_factor = backoff_factor
        self.recovery_factor = recovery_factor
        self.domain_rpm: Dict[str, int] = {}
        self.domain_errors: Dict[str, int] = defaultdict(int)
        self.domain_successes: Dict[str, int] = defaultdict(int)
    
    def record_error(self, url_or_domain: str, status_code: Optional[int] = None):
        """
        Record an error response and potentially reduce rate.
        
        Args:
            url_or_domain: URL or domain
            status_code: HTTP status code (429 triggers immediate backoff)
        """
        domain = self._extract_domain(url_or_domain)
        self.domain_errors[domain] += 1
        
        current_rpm = self.domain_rpm.get(domain, self.initial_rpm)
        
        if status_code == 429:
            # Immediate backoff for rate limit response
            new_rpm = max(self.min_rpm, int(current_rpm * self.backoff_factor))
            logger.warning(
                f"Rate limit hit (429) for {domain}. "
                f"Reducing from {current_rpm} to {new_rpm} RPM"
            )
            self.domain_rpm[domain] = new_rpm
        elif self.domain_errors[domain] >= 3:
            # Gradual backoff for repeated errors
            new_rpm = max(self.min_rpm, int(current_rpm * self.backoff_factor))
            logger.warning(
                f"Multiple errors for {domain}. "
                f"Reducing from {current_rpm} to {new_rpm} RPM"
            )
            self.domain_rpm[domain] = new_rpm
            self.domain_errors[domain] = 0
    
    def record_success(self, url_or_domain: str):
        """
        Record a successful response and potentially increase rate.
        
        Args:
            url_or_domain: URL or domain
        """
        domain = self._extract_domain(url_or_domain)
        self.domain_successes[domain] += 1
        self.domain_errors[domain] = max(0, self.domain_errors[domain] - 1)
        
        # Gradually recover rate after consistent success
        if self.domain_successes[domain] >= 10:
            current_rpm = self.domain_rpm.get(domain, self.initial_rpm)
            if current_rpm < self.initial_rpm:
                new_rpm = min(
                    self.initial_rpm,
                    int(current_rpm * self.recovery_factor)
                )
                logger.info(
                    f"Recovering rate for {domain}: {current_rpm} -> {new_rpm} RPM"
                )
                self.domain_rpm[domain] = new_rpm
            self.domain_successes[domain] = 0


# Global rate limiter instance
_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter(
    requests_per_minute: int = 30,
    adaptive: bool = False
) -> RateLimiter:
    """
    Get or create global rate limiter instance.
    
    Args:
        requests_per_minute: RPM limit (only used on first call)
        adaptive: Use adaptive rate limiter
    
    Returns:
        RateLimiter instance
    """
    global _global_limiter
    
    if _global_limiter is None:
        if adaptive:
            _global_limiter = AdaptiveRateLimiter(
                requests_per_minute=requests_per_minute
            )
        else:
            _global_limiter = RateLimiter(
                requests_per_minute=requests_per_minute
            )
    
    return _global_limiter


def reset_global_limiter():
    """Reset the global rate limiter."""
    global _global_limiter
    if _global_limiter:
        _global_limiter.reset()
