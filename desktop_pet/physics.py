"""Small deterministic physics model; positions in pixels, time in seconds."""

from collections import deque
from dataclasses import dataclass
import math


@dataclass
class Body:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    sleeping: bool = False

    def step(self, elapsed: float, bounds: tuple[float, float, float, float]) -> None:
        left, top, right, bottom = bounds
        right, bottom = max(left, right), max(top, bottom)
        # Bound long stalls and substep collisions for stable motion at varied FPS.
        remaining = max(0.0, min(elapsed, 0.05))
        while remaining > 1e-9:
            dt = min(remaining, 1 / 120)
            remaining -= dt
            self.vy += 1800 * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            if self.x <= left:
                self.x = left
                self.vx = abs(self.vx) * 0.45
            elif self.x >= right:
                self.x = right
                self.vx = -abs(self.vx) * 0.45
            if self.y <= top:
                self.y = top
                self.vy = abs(self.vy) * 0.35
            if self.y >= bottom:
                self.y = bottom
                self.vy = -self.vy * 0.42 if self.vy > 100 else 0.0
                self.vx *= math.exp(-10 * dt)
            if abs(self.vx) < 8 and self.y == bottom and self.vy == 0:
                self.vx = 0.0
                self.sleeping = True
                break
        self.x = max(left, min(self.x, right))
        self.y = max(top, min(self.y, bottom))


class DragVelocity:
    """Estimate a fling from recent actual movement, not total drag duration."""

    def __init__(self):
        self.samples: deque[tuple[float, float, float]] = deque(maxlen=20)

    def record(self, timestamp: float, x: float, y: float) -> None:
        self.samples.append((timestamp, x, y))
        while len(self.samples) > 2 and timestamp - self.samples[0][0] > 0.12:
            self.samples.popleft()

    def release(self, timestamp: float) -> tuple[float, float]:
        if len(self.samples) < 2 or timestamp - self.samples[-1][0] > 0.12:
            return 0.0, 0.0
        first, last = self.samples[0], self.samples[-1]
        dt = last[0] - first[0]
        if dt < 0.008:
            return 0.0, 0.0
        return tuple(max(-1400.0, min(1400.0, (last[i] - first[i]) / dt)) for i in (1, 2))
