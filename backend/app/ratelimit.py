"""A small in-memory fixed-window rate limiter.

Limits are written like "10/minute" or "12/minute;200/day". Memory storage is per process,
which is fine for one uvicorn worker; use a shared store (e.g. Redis) when running several.
"""
import threading
import time

from fastapi import Request

from .errors import RateLimited

_PERIODS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
_lock = threading.Lock()
_hits: dict[str, tuple[float, int]] = {}
enabled = True


def _parse(spec: str) -> list[tuple[int, int]]:
    rules = []
    for part in spec.split(";"):
        part = part.strip().replace(" per ", "/")
        if not part:
            continue
        count, period = part.split("/")
        rules.append((int(count), _PERIODS[period.strip().rstrip("s")]))
    return rules


def hit(key: str, spec: str) -> None:
    """Count one request for `key`; raise 429 when any window in `spec` is exceeded."""
    if not enabled:
        return
    now = time.monotonic()
    with _lock:
        for limit, seconds in _parse(spec):
            bucket = f"{key}|{seconds}"
            start, count = _hits.get(bucket, (now, 0))
            if now - start >= seconds:
                start, count = now, 0
            if count >= limit:
                raise RateLimited()
            _hits[bucket] = (start, count + 1)


def reset() -> None:
    with _lock:
        _hits.clear()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def limit_by_ip(name: str, spec: str):
    """FastAPI dependency factory: rate-limit an endpoint per client IP."""
    def dependency(request: Request):
        hit(f"{name}:{client_ip(request)}", spec)
    return dependency
