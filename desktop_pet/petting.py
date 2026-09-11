"""Recognize deliberate horizontal back-and-forth motion, not a single pass."""


class HeadStrokes:
    def __init__(self):
        self.reset()

    def reset(self):
        self.last = None
        self.direction = 0
        self.distance = 0
        self.previous_stroke = False
        self.active = False

    def feed(self, x, y, now):
        if self.last is None or now - self.last[2] > .45:
            self.reset()
            self.last = (x, y, now)
            return False
        dx, dy = x - self.last[0], y - self.last[1]
        self.last = (x, y, now)
        if abs(dy) > abs(dx):
            self.reset()
            return False
        if not dx:
            return False
        direction = 1 if dx > 0 else -1
        if direction != self.direction:
            self.previous_stroke = self.distance >= 6
            self.distance = 0
            self.direction = direction
        self.distance += abs(dx)
        if self.previous_stroke and self.distance >= 6:
            self.active = True
        return self.active
