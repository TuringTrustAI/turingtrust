"""
TuringTrust — Rate Limiter

Simple sliding-window rate limiter (in-memory).
No external dependencies.
"""

import time
from collections import defaultdict
from typing import Optional


class RateLimiter:
    """
    In-memory sliding window rate limiter.

    Args:
        requests_per_minute: Maximum requests allowed per 60-second window.
    """

    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self._requests: dict[str, list[float]] = defaultdict(list)

    def can_proceed(self, key: str = "global") -> bool:
        """Check if the key is within rate limits (does NOT record the request)."""
        now = time.time()
        self._requests[key] = [t for t in self._requests[key] if now - t < 60]
        return len(self._requests[key]) < self.rpm

    def record(self, key: str = "global"):
        """Record that a request was made for the given key."""
        self._requests[key].append(time.time())

    def check_and_record(self, key: str = "global") -> bool:
        """Atomically check and record. Returns True if allowed, False if rate limited."""
        if self.can_proceed(key):
            self.record(key)
            return True
        return False

    def remaining(self, key: str = "global") -> int:
        """Return the number of remaining requests in the current window."""
        now = time.time()
        self._requests[key] = [t for t in self._requests[key] if now - t < 60]
        return max(0, self.rpm - len(self._requests[key]))

    def reset(self, key: Optional[str] = None):
        """Reset rate limit state for a key or all keys."""
        if key:
            self._requests.pop(key, None)
        else:
            self._requests.clear()
