"""Recognize a forgiving back-and-forth stroke, including natural curved turns."""


class HeadStrokes:
    def __init__(self):
        self.reset()

    def reset(self):
        self.last = None
        self.direction = 0
        self.origin = None
        self.extreme = 0
        self.active = False

    def feed(self, x, y, now):
        if (self.last is None or now - self.last[2] >= .8
                or abs(y - self.origin[1]) > 18):
            self.reset()
            self.origin = (x, y)
            self.extreme = x
            self.last = (x, y, now)
            return False
        dx = x - self.last[0]
        if x == self.last[0] and y == self.last[1]:
            return False
        self.last = (x, y, now)
        if self.direction == 0:
            if abs(x - self.origin[0]) >= 6:
                self.direction = 1 if x > self.origin[0] else -1
                self.extreme = x
            return False
        # Measure from the furthest point, not the last individual event.
        # Vertical samples and tiny reverse jitters at the turn are harmless.
        self.extreme = max(self.extreme, x) if self.direction > 0 else min(self.extreme, x)
        if (self.extreme - x) * self.direction >= 6:
            self.active = True
            self.direction *= -1
            self.extreme = x
        return self.active and abs(dx) >= 1
