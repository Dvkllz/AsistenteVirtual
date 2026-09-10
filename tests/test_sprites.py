import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication

from desktop_pet.sprites import SPRITE_DIR, SPRITE_STATES, SpriteSet, select_state


class SpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def test_four_distinct_transparent_images(self):
        hashes = set()
        for state in SPRITE_STATES:
            path = SPRITE_DIR / f'{state}.png'
            hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
            image = QImage(str(path))
            self.assertFalse(image.isNull())
            self.assertTrue(image.hasAlphaChannel())
            self.assertEqual((image.width(), image.height()), (512, 512))
            for x, y in ((0, 0), (511, 0), (0, 511), (511, 511)):
                self.assertEqual(image.pixelColor(x, y).alpha(), 0)
            # Real foreground and real transparency, not merely an RGBA container.
            pixels = [image.pixelColor(x, y).alpha()
                      for x in range(0, 512, 8) for y in range(0, 512, 8)]
            self.assertGreater(pixels.count(0), len(pixels) * .25)
            self.assertGreater(pixels.count(255), len(pixels) * .15)
        self.assertEqual(len(hashes), 4)

    def test_cached_sprites_are_compact_and_mirrored(self):
        sprites = SpriteSet()
        self.assertEqual(sprites.missing, [])
        for state in SPRITE_STATES:
            right, left = sprites.pixmap(state), sprites.pixmap(state, -1)
            self.assertLessEqual(right.width(), 117)
            self.assertLessEqual(right.height(), 112)
            self.assertEqual(right.cacheKey(), sprites.pixmap(state).cacheKey())
            self.assertNotEqual(right.cacheKey(), left.cacheKey())
            self.assertEqual(right.size(), left.size())

    def test_missing_sprite_falls_back_safely(self):
        with TemporaryDirectory() as temp:
            sprites = SpriteSet(Path(temp))
        self.assertEqual(sprites.missing, list(SPRITE_STATES))
        self.assertFalse(sprites.pixmap('idle').isNull())

    def test_priority(self):
        flags = dict(dragging=False, airborne=False, speaking=False, walking=False)
        self.assertEqual(select_state(**flags), 'idle')
        flags['walking'] = True
        self.assertEqual(select_state(**flags), 'walking')
        flags['speaking'] = True
        self.assertEqual(select_state(**flags), 'talking')
        flags['airborne'] = True
        self.assertEqual(select_state(**flags), 'falling')
        flags.update(airborne=False, dragging=True)
        self.assertEqual(select_state(**flags), 'falling')
