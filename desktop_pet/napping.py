"""Five-second cat naps after 30s without mouse/keyboard input; no screen capture."""

import ctypes
import sys
import time
from PyQt6.QtCore import QTimer
from desktop_pet.autonomy import mouse_button_down


def input_idle_seconds():
    if sys.platform != "win32":
        return None

    class LastInputInfo(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint32), ("dwTime", ctypes.c_uint32)]

    info = LastInputInfo()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return None
    now = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF
    return ((now - info.dwTime) & 0xFFFFFFFF) / 1000


class CatNaps:
    def __init__(self, window):
        self.window = window
        self.enabled = window.settings.value("nap/enabled", True, type=bool)
        self.next_allowed = time.monotonic() + 30
        self.previous_mode = None
        self.timer = QTimer(window)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.tick)
        self.wake_timer = QTimer(window)
        self.wake_timer.setSingleShot(True)
        self.wake_timer.setInterval(5000)
        self.wake_timer.timeout.connect(self.wake)
        if self.enabled:
            self.timer.start()

    def tick(self):
        w = self.window
        idle = input_idle_seconds()
        if w.sleeping:
            if idle is not None and idle < .75:
                self.wake()
            return
        if (not self.enabled or idle is None or idle < 30 or time.monotonic() < self.next_allowed
                or w._closing or not w.isVisible() or w.worker is not None
                or w.talking_timer.isActive() or w.petting or w._drag_offset is not None
                or w.menu.isVisible() or mouse_button_down()
                or (w.motion_timer.isActive() and w.y() < w._bounds()[3] - 1)
                or (w.autonomy and (w.autonomy.pouncing or w.autonomy.swatting or w.autonomy.carrying))):
            return
        w.sleeping = True
        if w.autonomy:
            w.autonomy.cancel()
        w._cancel_walk()
        w._stop_petting()
        w._stop_motion()
        self.previous_mode = w.mode.text()
        w.mode.setText("DURMIENDO · Zzz")
        w._refresh_sprite()
        self.wake_timer.start()

    def wake(self):
        w = self.window
        if not w.sleeping:
            return
        self.wake_timer.stop()
        w.sleeping = False
        self.next_allowed = time.monotonic() + 30
        if self.previous_mode is not None:
            w.mode.setText(self.previous_mode)
        w._refresh_sprite()
        w._start_motion()

    def close(self):
        self.timer.stop()
        self.wake_timer.stop()
