"""Token-bucket rate limiting for request admission.

Not thread-safe: the gateway calls it from a single event-loop thread per worker.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(slots=True)
class TokenBucket:
    """Admit up to `capacity` units at once, refilling at `rate` units per second."""

    rate: float
    capacity: int
    clock: Callable[[], float] = time.monotonic
    _tokens: float = field(init=False)
    _updated: float = field(init=False)

    def __post_init__(self) -> None:
        if self.rate <= 0:
            raise ValueError(f"rate must be positive, got {self.rate}")
        if self.capacity <= 0:
            raise ValueError(f"capacity must be positive, got {self.capacity}")
        self._tokens = float(self.capacity)
        self._updated = self.clock()

    @property
    def available(self) -> float:
        self._refill()
        return self._tokens

    def try_acquire(self, units: int = 1) -> bool:
        """Take `units` tokens if all are available; never takes a partial amount."""
        if not 0 < units <= self.capacity:
            raise ValueError(f"units must be in 1..{self.capacity}, got {units}")
        self._refill()
        if self._tokens < units:
            return False
        self._tokens -= units
        return True

    def _refill(self) -> None:
        now = self.clock()
        elapsed = max(0.0, now - self._updated)
        self._tokens = min(float(self.capacity), self._tokens + elapsed * self.rate)
        self._updated = max(self._updated, now)
