import sys
import unittest
from unittest.mock import patch
from desktop_pet.napping import input_idle_seconds


class InputIdleTests(unittest.TestCase):
    def test_unavailable_platform_fails_closed(self):
        with patch('desktop_pet.napping.sys.platform', 'unsupported'):
            self.assertIsNone(input_idle_seconds())

    @unittest.skipUnless(sys.platform == 'win32', 'Windows session idle API')
    def test_windows_idle_is_available_without_recording_input(self):
        value = input_idle_seconds()
        self.assertIsNotNone(value)
        self.assertGreaterEqual(value, 0)
