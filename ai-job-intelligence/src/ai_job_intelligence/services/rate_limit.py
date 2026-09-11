"""Sliding-window rate limiting.

Scope and honesty about it
--------------------------
State lives in this process only. It does not survive a restart and is not
shared between workers, so with N workers the effective limit is N times what
is configured. That is enough to stop credential stuffing and casual abuse of
the public endpoints, and it is not a substitute for a shared store (Redis) or
an edge WAF in a real deployment.

A sliding window is used rather than a fixed one because a fixed window lets an
attacker send a full quota at the end of one window and another immediately at
the start of the next, briefly doubling the intended rate.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    """``limit`` attempts allowed per ``window_seconds``."""

    limit: int
    window_seconds: int


class SlidingWindowLimiter:
    """Track attempts per key and report when a key is over its limit."""

    def __init__(self, rule: Rule, *, max_keys: int = 10_000) -> None:
        self._rule = rule
        self._max_keys = max_keys
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> list[float]:
        cutoff = now - self._rule.window_seconds
        recent = [t for t in self._hits.get(key, []) if t > cutoff]
        if recent:
            self._hits[key] = recent
        else:
            self._hits.pop(key, None)
        return recent

    def check(self, key: str) -> float | None:
        """Seconds until the key is allowed again, or None if it is allowed now.

        Read-only: it does not consume an attempt.
        """
        now = time.monotonic()
        with self._lock:
            recent = self._prune(key, now)
            if len(recent) < self._rule.limit:
                return None
            retry_after = self._rule.window_seconds - (now - recent[0])
            return max(retry_after, 1.0)

    def record(self, key: str) -> None:
        """Count one attempt against the key."""
        now = time.monotonic()
        with self._lock:
            recent = self._prune(key, now)
            recent.append(now)
            self._hits[key] = recent

            # Bound memory: drop the least recently active keys.
            if len(self._hits) > self._max_keys:
                oldest = sorted(self._hits, key=lambda k: self._hits[k][-1])
                for stale in oldest[: len(self._hits) - self._max_keys]:
                    self._hits.pop(stale, None)

    def reset(self, key: str) -> None:
        """Clear a key's history, e.g. after a successful login."""
        with self._lock:
            self._hits.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()
