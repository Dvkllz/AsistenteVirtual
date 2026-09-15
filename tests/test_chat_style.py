import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from desktop_pet.chat_style import FONT_PATH, pixel_font_family


class ChatStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def test_bundled_font_and_license_are_present(self):
        self.assertTrue(FONT_PATH.is_file())
        self.assertIn('SIL OPEN FONT LICENSE', (FONT_PATH.parent / 'OFL.txt').read_text())
        self.assertEqual(pixel_font_family(), 'Pixelify Sans')

    def test_font_registration_is_cached_and_missing_font_has_fallback(self):
        pixel_font_family.cache_clear()
        try:
            with patch('desktop_pet.chat_style.QFontDatabase.addApplicationFont', return_value=-1) as load:
                self.assertEqual(pixel_font_family(), 'Consolas')
                self.assertEqual(pixel_font_family(), 'Consolas')
                load.assert_called_once()
        finally:
            pixel_font_family.cache_clear()
