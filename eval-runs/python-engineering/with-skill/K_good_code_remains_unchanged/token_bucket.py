from collections.abc import Callable
from dataclasses import dataclass, field
import time

@dataclass(slots=True)
class TokenBucket:
    capacity: float
    refill_rate: float
    clock: Callable[[], float] = time.monotonic
    _tokens: float = field(init=False)
    _last_timestamp: float = field(init=False)

    def __post_init__(self) -> None:
        if self.capacity <= 0 or self.refill_rate <= 0:
            raise ValueError('capacity and refill_rate must be positive')
        self._tokens = float(self.capacity)
        self._last_timestamp = self.clock()

    def allow(self, cost: float = 1.0) -> bool:
        if cost <= 0:
            raise ValueError('cost must be positive')
        now = self.clock()
        elapsed = max(0.0, now - self._last_timestamp)
        self._last_timestamp = now
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False
