"""Redis-backed fixed-window rate limiting with a development fallback."""
from collections import defaultdict
from time import time
from redis import Redis
from redis.exceptions import RedisError
from crtnm.core.config import get_settings


class RateLimiter:
    """Protects high-value endpoints without retaining request bodies or secrets."""

    def __init__(self) -> None:
        self._memory: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
        self._redis: Redis | None = None

    def allow(self, key: str, limit: int | None = None) -> bool:
        """Allow an event only if the caller remains within the current minute window."""
        configured_limit = limit or get_settings().rate_limit_per_minute
        window = int(time() // 60)
        try:
            if self._redis is None:
                self._redis = Redis.from_url(get_settings().redis_url, socket_connect_timeout=0.25, socket_timeout=0.25)
            redis_key = f"crtnm:rate:{window}:{key}"
            count = self._redis.incr(redis_key)
            if count == 1: self._redis.expire(redis_key, 60)
            return count <= configured_limit
        except RedisError:
            count, remembered_window = self._memory[key]
            count = count + 1 if remembered_window == window else 1
            self._memory[key] = (count, window)
            return count <= configured_limit
