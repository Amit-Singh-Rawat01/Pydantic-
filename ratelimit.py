"""Per-service token buckets for collector ingestion."""

import math
import threading
import time

from fastapi.responses import JSONResponse
from prometheus_client import Counter

RATE = 20
BURST = 20
MAX_SERVICES = 50

RATE_LIMITED = Counter(
    "ingest_rate_limited_total",
    "Events rejected because a service exceeded its rate limit",
    ["service"],
)


class TokenBucket:
    """A token bucket for one service."""

    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last = time.monotonic()

    def take(self) -> float:
        """Return 0 when a token is available, otherwise the wait in seconds."""
        now = time.monotonic()
        self.tokens = min(self.burst, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= 1:
            self.tokens -= 1
            return 0.0
        return (1 - self.tokens) / self.rate


class ServiceLimiter:
    """Keep independent buckets for service names, with bounded label cardinality."""

    def __init__(
        self,
        rate: float = RATE,
        burst: int = BURST,
        max_services: int = MAX_SERVICES,
    ):
        self.rate = rate
        self.burst = burst
        self.max_services = max_services
        self.buckets: dict[str, TokenBucket] = {}
        self.lock = threading.Lock()

    def check(self, service: str) -> tuple[str, float]:
        """Return the bucket name and wait; a zero wait means the event may proceed."""
        with self.lock:
            if service not in self.buckets and len(self.buckets) >= self.max_services:
                service = "_other"
            if service not in self.buckets:
                self.buckets[service] = TokenBucket(self.rate, self.burst)
            return service, self.buckets[service].take()


limiter = ServiceLimiter()


def check_rate_limit(service: str) -> JSONResponse | None:
    """Return a 429 response when the service has exhausted its bucket."""
    name, wait = limiter.check(service)
    if wait == 0:
        return None
    RATE_LIMITED.labels(service=name).inc()
    return JSONResponse(
        status_code=429,
        content={"detail": f"rate limit: {name}"},
        headers={"Retry-After": str(max(1, math.ceil(wait)))},
    )


if __name__ == "__main__":
    test = ServiceLimiter(rate=5, burst=10)

    def accepted(service: str, count: int) -> int:
        return sum(test.check(service)[1] == 0 for _ in range(count))

    print("payment, 15 ek saath  ->", accepted("payment", 15), "andar")
    print("auth, 3 ek saath      ->", accepted("auth", 3), "andar")
    time.sleep(1.1)
    print("payment, 1.1 sec baad ->", accepted("payment", 15), "andar")
