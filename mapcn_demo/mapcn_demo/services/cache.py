"""A time-to-live cache held in the memory of this backend process.

The demo reads public services that ask to be used sparingly, and every
visitor would otherwise repeat the same query. This is deliberately the
simplest thing that works: a dict with expiry times, no eviction, at most a
few dozen keys. It is not shared between backend workers, which is fine for a
demo; a deployment with several of them wants Redis instead.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


class TTLCache:
    """Values that expire after a fixed time."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._entries: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        """Return the value, or None when it is missing or expired."""
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._clock() >= expires_at:
            del self._entries[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_s: float) -> None:
        """Store a value for the next ``ttl_s`` seconds."""
        self._entries[key] = (self._clock() + ttl_s, value)

    def clear(self) -> None:
        self._entries.clear()
