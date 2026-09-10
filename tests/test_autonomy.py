import unittest
from PyQt6.QtCore import QPoint
from desktop_pet.autonomy import IdleMouse


class IdleMouseTests(unittest.TestCase):
    def test_exact_ten_seconds_and_only_once_until_moved(self):
        mouse = IdleMouse(100, QPoint(10, 20))
        self.assertFalse(mouse.poll(109.999, QPoint(10, 20)))
        self.assertTrue(mouse.poll(110, QPoint(10, 20)))
        self.assertFalse(mouse.poll(130, QPoint(10, 20)))
        self.assertFalse(mouse.poll(131, QPoint(11, 20)))
        self.assertFalse(mouse.poll(140.99, QPoint(11, 20)))
        self.assertTrue(mouse.poll(141, QPoint(11, 20)))

    def test_busy_resets_the_idle_period(self):
        mouse = IdleMouse(0, QPoint(-500, 20))
        self.assertFalse(mouse.poll(20, QPoint(-500, 20), blocked=True))
        self.assertFalse(mouse.poll(29.9, QPoint(-500, 20)))
        self.assertTrue(mouse.poll(30, QPoint(-500, 20)))
