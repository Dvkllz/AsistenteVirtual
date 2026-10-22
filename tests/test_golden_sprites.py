import os
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication
from desktop_pet.sprites import AtlasSpriteSet, FRAME_FILES, load_pet_sprites


class GoldenSpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.sprites = load_pet_sprites('golden')

    def test_complete_distinct_cached_frames_in_both_directions(self):
        self.assertEqual(len(self.sprites.frames), 24)
        self.assertFalse(self.sprites.missing)
        self.assertFalse(self.sprites.missing_animation)
        for state, names in FRAME_FILES.items():
            images = []
            for frame in range(len(names)):
                right = self.sprites.pixmap(state, 1, frame)
                left = self.sprites.pixmap(state, -1, frame)
                self.assertEqual((right.width(), right.height()), (152, 112))
                self.assertEqual(right.cacheKey(), self.sprites.pixmap(state, 1, frame).cacheKey())
                self.assertEqual(left.toImage(), right.toImage().mirrored(True, False))
                images.append(right.toImage())
            for i, im in enumerate(images):
                self.assertTrue(all(im != other for other in images[i+1:]))

    def test_transparent_margins_and_grounded_baseline(self):
        for state in FRAME_FILES:
            for frame in range(len(FRAME_FILES[state])):
                im = self.sprites.pixmap(state, frame=frame).toImage()
                self.assertTrue(im.hasAlphaChannel())
                for x in range(im.width()):
                    self.assertEqual(im.pixelColor(x, 0).alpha(), 0)
                    self.assertEqual(im.pixelColor(x, 111).alpha(), 0)
                for y in range(im.height()):
                    self.assertEqual(im.pixelColor(0, y).alpha(), 0)
                    self.assertEqual(im.pixelColor(151, y).alpha(), 0)

    def test_missing_atlas_is_explicit_not_a_disguised_cat(self):
        with TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                AtlasSpriteSet(Path(folder))
