"""
TuringTrust — Circuit Breaker

Prevents cascading failures by tracking per-provider error rates.
State machine: closed → open → half-open → closed.
"""

import time
from collections import defaultdict


class CircuitBreaker:
    """
    Per-provider circuit breaker.

    States:
        closed    — requests flow normally.
        open      — requests are rejected (provider is down).
        half-open — one test request is allowed to check recovery.

    Args:
        failure_threshold: Number of consecutive failures before opening.
        recovery_timeout:  Seconds to wait before trying half-open.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures: dict[str, int] = defaultdict(int)
        self._last_failure_time: dict[str, float] = {}
        self._state: dict[str, str] = defaultdict(lambda: "closed")

    def can_execute(self, provider: str) -> bool:
        """Check if a request to this provider should be allowed."""
        state = self._state[provider]
        if state == "closed":
            return True
        if state == "open":
            elapsed = time.time() - self._last_failure_time.get(provider, 0)
            if elapsed > self.recovery_timeout:
                self._state[provider] = "half-open"
                return True
            return False
        # half-open — allow one test request
        return True

    def record_success(self, provider: str):
        """Record a successful request — resets failure count."""
        self._failures[provider] = 0
        self._state[provider] = "closed"

    def record_failure(self, provider: str):
        """Record a failed request — may open the circuit."""
        self._failures[provider] += 1
        self._last_failure_time[provider] = time.time()
        if self._failures[provider] >= self.failure_threshold:
            self._state[provider] = "open"

    def get_state(self, provider: str) -> str:
        """Return the current circuit state for a provider."""
        return self._state[provider]

    def get_stats(self) -> dict:
        """Return stats for all tracked providers."""
        providers = set(list(self._failures.keys()) + list(self._state.keys()))
        return {
            p: {"state": self._state[p], "failures": self._failures[p]}
            for p in providers
        }

    def reset(self, provider: str | None = None):
        """Reset circuit breaker state for one or all providers."""
        if provider:
            self._failures.pop(provider, None)
            self._last_failure_time.pop(provider, None)
            self._state.pop(provider, None)
        else:
            self._failures.clear()
            self._last_failure_time.clear()
            self._state.clear()
