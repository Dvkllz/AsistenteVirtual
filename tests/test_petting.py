import unittest
from desktop_pet.petting import HeadStrokes


class HeadStrokesTests(unittest.TestCase):
    def test_single_pass_jitter_and_stationary_mouse_are_not_strokes(self):
        gesture = HeadStrokes()
        for index, x in enumerate((0, 1, 0, 1, 0, 3, 6, 9, 12, 12)):
            self.assertFalse(gesture.feed(x, 10, index * .01))

    def test_small_movements_accumulate_into_a_return_stroke(self):
        gesture = HeadStrokes()
        values = [gesture.feed(x, 10, i * .01)
                  for i, x in enumerate((0, 2, 4, 6, 8, 6, 4, 2))]
        self.assertEqual(values, [False] * 7 + [True])

    def test_pause_vertical_motion_and_reset_require_fresh_strokes(self):
        gesture = HeadStrokes()
        for x, y, now in ((0, 0, 0), (8, 0, .1), (0, 0, 1), (0, 8, 1.1), (8, 8, 1.2)):
            self.assertFalse(gesture.feed(x, y, now))
        gesture.reset()
        self.assertFalse(gesture.feed(0, 8, 1.3))
