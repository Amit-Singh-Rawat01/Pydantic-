import time
from datetime import datetime

import redis

from redis_client import redis_client as r


COUNTER_TTL = 7200
_pause_until = 0


def _minute_key(service_name, occurred_at):
    if isinstance(occurred_at, str):
        occurred_at = datetime.fromisoformat(
            occurred_at.replace("Z", "+00:00")
        )
    return f"errors:{service_name}:{occurred_at.strftime('%Y-%m-%dT%H:%M')}"


def count_error(service_name, occurred_at):
    global _pause_until
    if time.time() < _pause_until:
        return
    try:
        key = _minute_key(service_name, occurred_at)
        if r.incr(key) == 1:
            r.expire(key, COUNTER_TTL)
        r.incr("total_errors")
    except Exception as error:
        _pause_until = time.time() + 10
        print(
            "Redis counter failed, 10 sec ke liye band "
            "(Postgres mein data safe hai):",
            error,
        )


def get_total_from_redis():
    """Return the seeded Redis total, or None when it is unavailable."""
    try:
        total, ready = r.mget("total_errors", "total_errors_ready")
    except redis.exceptions.RedisError as error:
        print("Redis read failed, Postgres se gin-ti karenge:", error)
        return None

    if total is None or ready is None:
        return None

    try:
        return int(total)
    except (TypeError, ValueError) as error:
        print("Redis total invalid, Postgres se gin-ti karenge:", error)
        return None
