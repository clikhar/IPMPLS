"""Tests for the local fallback rate-control behavior."""
from crtnm.infrastructure.rate_limiter import RateLimiter
from redis.exceptions import RedisError


def test_memory_fallback_rejects_after_limit(monkeypatch) -> None:
    limiter = RateLimiter()
    class BrokenRedis:
        def incr(self, _: str) -> int: raise RedisError("unavailable")
    limiter._redis = BrokenRedis()  # type: ignore[assignment]
    monkeypatch.setattr("crtnm.infrastructure.rate_limiter.time", lambda: 120.0)
    assert limiter.allow("source", limit=2)
    assert limiter.allow("source", limit=2)
    assert not limiter.allow("source", limit=2)
