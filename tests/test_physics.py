import unittest

from desktop_pet.physics import Body, DragVelocity


class PhysicsTests(unittest.TestCase):
    def test_drop_bounces_then_sleeps_inside_bounds(self):
        body = Body(200, 30, 600, 0)
        bounced = False
        for _ in range(2400):
            previous_vy = body.vy
            body.step(1 / 60, (0, 0, 600, 500))
            bounced |= previous_vy > 0 and body.vy < 0
            self.assertTrue(0 <= body.x <= 600 and 0 <= body.y <= 500)
            if body.sleeping:
                break
        self.assertTrue(bounced)
        self.assertTrue(body.sleeping)
        self.assertEqual(body.y, 500)
        self.assertEqual((body.vx, body.vy), (0, 0))

    def test_wall_and_ceiling_reflect_velocity(self):
        body = Body(598, 2, 900, -800)
        body.step(1 / 60, (0, 0, 600, 500))
        self.assertLess(body.vx, 0)
        self.assertGreater(body.vy, 0)
        self.assertLess(abs(body.vx), 900)

    def test_jump_rises_and_returns_to_floor(self):
        body = Body(100, 500, 0, -650)
        body.step(1 / 60, (0, 0, 600, 500))
        self.assertLess(body.y, 500)
        for _ in range(600):
            body.step(1 / 60, (0, 0, 600, 500))
            if body.sleeping:
                break
        self.assertTrue(body.sleeping)

    def test_stall_is_capped_and_negative_monitor_coordinates_work(self):
        body = Body(-800, -300, -1400, -1400)
        body.step(30, (-1000, -500, -300, 100))
        self.assertTrue(-1000 <= body.x <= -300 and -500 <= body.y <= 100)
        self.assertLess(abs(body.y + 300), 100)

    def test_small_screen_does_not_create_inverted_bounds(self):
        body = Body(100, 100, 100, 100)
        body.step(1 / 60, (0, 0, -100, -100))
        self.assertEqual((body.x, body.y), (0, 0))

    def test_motion_is_consistent_at_30_and_60_fps(self):
        bodies = [Body(200, 10, 200, 0), Body(200, 10, 200, 0)]
        for body, fps in zip(bodies, (30, 60)):
            for _ in range(fps):
                body.step(1 / fps, (0, 0, 1000, 1000))
        self.assertAlmostEqual(bodies[0].x, bodies[1].x, places=5)
        self.assertAlmostEqual(bodies[0].y, bodies[1].y, places=5)

    def test_fling_capped_and_holding_before_release_cancels_throw(self):
        drag = DragVelocity()
        drag.record(0, 0, 0)
        drag.record(0.05, 300, -300)
        self.assertEqual(drag.release(0.06), (1400, -1400))
        self.assertEqual(drag.release(0.3), (0, 0))

    def test_click_without_drag_has_no_fling(self):
        drag = DragVelocity()
        drag.record(0, 10, 10)
        self.assertEqual(drag.release(0.01), (0, 0))
