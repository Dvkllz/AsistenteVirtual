import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtCore import QObject, QPoint, QSettings, QRect, Qt, pyqtSignal
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from desktop_pet.concentration import (Concentration, FocusBridge, target_point,
    approach_position, paw_offset, smooth_progress, WALK_SECONDS, CONTACT_SECONDS)
from desktop_pet.window import PetWindow


class FakeBridge(QObject):
    message = pyqtSignal(dict)
    failed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.requests = []
        self.starts = self.stops = 0

    def start(self):
        self.starts += 1

    def stop(self):
        self.stops += 1

    def send(self, command, token=None):
        self.requests.append((command, token))


class ConcentrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = TemporaryDirectory()
        settings = QSettings(str(Path(self.temp.name)/'settings.ini'), QSettings.Format.IniFormat)
        for key in ('physics/enabled', 'sound/effects', 'sound/purr', 'nap/enabled', 'autonomy/enabled'):
            settings.setValue(key, False)
        self.w = PetWindow(settings=settings)
        self.w.show()
        self.app.processEvents()
        self.w.concentration.close()
        self.bridge = FakeBridge()
        self.c = self.w.concentration = Concentration(self.w, self.bridge)
        self.guard = patch.object(self.c, '_blocked', return_value=False)
        self.guard.start()
        self.platform = patch('desktop_pet.concentration.sys.platform', 'win32')
        self.platform.start()
        screen = self.w.screen()
        g, d = screen.geometry(), screen.devicePixelRatio()
        self.target = dict(site='instagram.com', token='opaque-token', monitor=screen.name(),
                           x=100*d, y=60*d, left=0, top=0)

    def tearDown(self):
        self.c.close()
        self.w.close()
        self.w.deleteLater()
        self.app.processEvents()
        self.guard.stop()
        self.platform.stop()
        self.temp.cleanup()

    def enable(self):
        self.c.set_enabled(True)
        self.bridge.message.emit({'ready': True})

    def probe(self, target):
        self.c._probe()
        self.bridge.message.emit({'target': target})

    def begin(self):
        self.enable()
        self.probe(self.target)
        self.assertFalse(self.c.active)
        self.probe(self.target)
        self.assertTrue(self.c.active)

    def test_default_off_no_helper(self):
        self.assertFalse(self.c.enabled)
        self.assertFalse(self.w.concentration_action.isChecked())
        self.assertEqual(self.bridge.starts, 0)

    def test_animation_uses_precise_sixteen_ms_timer(self):
        self.assertEqual(self.c.animation.interval(), 16)
        self.assertEqual(self.c.animation.timerType(), Qt.TimerType.PreciseTimer)

    def test_native_overlay_reaches_x_without_top_edge_clamp(self):
        self.target['y'] = 10*self.w.screen().devicePixelRatio()
        self.begin()
        self.c.started -= CONTACT_SECONDS+.01
        self.c._tick()
        self.app.processEvents()
        self.assertEqual(self.c.overlay.pos(), self.c.destination)
        self.assertEqual(self.c.overlay.pos()+paw_offset(self.c.direction),
                         target_point(self.target, self.app.screens()))

    def test_paw_reaches_x_at_top_edge_in_both_directions(self):
        for direction in (-1, 1):
            target = QPoint(600, 10)
            destination = target-paw_offset(direction)
            self.assertLess(destination.y(), 0)
            for elapsed in (CONTACT_SECONDS, CONTACT_SECONDS+1):
                x,y,state,frame = approach_position(QPoint(300,600), destination, direction, elapsed)
                contact = QPoint(round(x),round(y))+paw_offset(direction)
                self.assertEqual(contact, target)
                self.assertEqual((state,frame), ('falling',2))

    def test_walk_to_jump_is_continuous(self):
        origin, destination = QPoint(20,600), QPoint(500,-40)
        before = approach_position(origin,destination,1,WALK_SECONDS-.0001)
        after = approach_position(origin,destination,1,WALK_SECONDS+.0001)
        self.assertLess(abs(before[0]-after[0])+abs(before[1]-after[1]), .001)
        self.assertEqual(smooth_progress(-1), 0)
        self.assertEqual(smooth_progress(2), 1)

    def test_contact_requests_fresh_validation_without_waiting_for_poll(self):
        self.begin()
        self.c.started -= CONTACT_SECONDS+.01
        self.c._tick()
        self.assertEqual(self.bridge.requests[-1], ('probe',None))
        count = len(self.bridge.requests)
        self.c._tick()
        self.assertEqual(len(self.bridge.requests), count)

    def test_background_draft_does_not_block_browser_detection(self):
        self.guard.stop()
        self.w.input.setText('borrador sin enviar')
        with patch.object(self.w, 'isActiveWindow', return_value=False), \
             patch('desktop_pet.concentration.mouse_button_down', return_value=False), \
             patch('desktop_pet.concentration.escape_pressed', return_value=False):
            self.assertFalse(self.c._blocked())
        with patch.object(self.w, 'isActiveWindow', return_value=True):
            self.assertTrue(self.c._blocked())

    def test_detector_failure_reason_is_visible_in_menu(self):
        self.enable()
        self.c._probe()
        self.bridge.message.emit({'target': None, 'reason': 'close_unavailable'})
        self.assertEqual(self.c.reason, 'close_unavailable')
        self.assertIn('la X', self.w.concentration_status_action.toolTip())
        self.c.explain()
        self.assertIn('la X', self.w.bubble.text())

    def test_unknown_reason_never_displays_raw_helper_output(self):
        self.c._status('private arbitrary text')
        self.assertNotIn('private arbitrary text', self.w.concentration_status_action.text())

    def test_two_stable_probes_and_close_only_after_animation(self):
        self.begin()
        self.assertTrue(self.w.character.isHidden())
        self.probe(self.target)
        self.assertNotIn(('close', 'opaque-token'), self.bridge.requests)
        self.c.started -= 3
        self.probe(self.target)
        self.assertEqual(self.bridge.requests[-1], ('close', 'opaque-token'))
        self.c._probe()
        self.assertEqual(sum(r[0] == 'close' for r in self.bridge.requests), 1)
        self.bridge.message.emit({'closed': True})
        self.assertFalse(self.c.active)
        self.assertFalse(self.w.character.isHidden())
        self.assertIn('cuarenta', self.w.bubble.text())

    def test_changed_tab_url_or_position_cancels(self):
        for field, value in [('token', 'new-page'), ('x', self.target['x']+20)]:
            with self.subTest(field=field):
                self.c.cooldown = 0
                self.begin()
                self.probe(dict(self.target, **{field: value}))
                self.assertFalse(self.c.active)
        self.assertFalse(any(r[0] == 'close' for r in self.bridge.requests))

    def test_browser_switched_or_unknown_target_cancels(self):
        self.begin()
        self.probe(None)
        self.assertFalse(self.c.active)
        self.assertFalse(self.w.character.isHidden())

    def test_disable_restores_sprite_and_stops_helper(self):
        self.begin()
        self.c.set_enabled(False)
        self.assertFalse(self.c.active)
        self.assertFalse(self.c.poll.isActive())
        self.assertFalse(self.c.animation.isActive())
        self.assertGreater(self.bridge.stops, 0)

    def test_interaction_interrupts(self):
        self.begin()
        with patch.object(self.c, '_blocked', return_value=True):
            self.c._tick()
        self.assertFalse(self.c.active)

    def test_pending_close_is_interrupted_on_cancel(self):
        self.begin()
        self.c.started -= 3
        self.probe(self.target)
        self.c.cancel()
        self.assertIsNone(self.c.pending)
        self.assertGreater(self.bridge.stops, 0)
        self.bridge.message.emit({'closed': True})
        self.assertFalse(self.w.talking_timer.isActive())

    def test_failure_disables_mode(self):
        self.begin()
        self.bridge.failed.emit()
        self.assertFalse(self.c.enabled)
        self.assertFalse(self.c.active)

    def test_response_cancels_animation(self):
        self.begin()
        self.w.show_response('Respuesta local')
        self.assertFalse(self.c.active)

    def test_invalid_target_rejected(self):
        for changes in ({'site': 'instagram.com.evil.test'}, {'x': float('nan')},
                        {'monitor': 'missing'}, {'token': ''}, {'x': -1e12}):
            self.assertIsNone(target_point(dict(self.target, **changes), QApplication.screens()))

    def test_multimonitor_scaling(self):
        class Screen:
            def name(self): return 'SECOND'
            def geometry(self): return QRect(-1280, 0, 1280, 720)
            def devicePixelRatio(self): return 1.5
        point = target_point(dict(self.target, monitor='SECOND', left=-1920,
                                  top=0, x=-1770, y=150), [Screen()])
        self.assertEqual((point.x(), point.y()), (-1180, 100))

    @unittest.skipUnless(sys.platform == 'win32', 'Windows helper')
    def test_native_bridge_handshake_and_invalid_token(self):
        bridge = FocusBridge(self.w)
        messages, failures = [], []
        bridge.message.connect(messages.append)
        bridge.failed.connect(lambda: failures.append(True))
        try:
            bridge.start()
            end = time.monotonic()+12
            while not messages and not failures and time.monotonic() < end:
                QTest.qWait(20)
            self.assertFalse(failures)
            self.assertEqual(messages, [{'ready': True}])
            bridge.send('close', 'invalid-token-never-probed')
            end = time.monotonic()+4
            while len(messages) < 2 and not failures and time.monotonic() < end:
                QTest.qWait(20)
            self.assertEqual(messages[-1], {'closed': False})
        finally:
            bridge.stop()


@unittest.skipUnless(sys.platform == 'win32', 'Windows domain parser')
class NativeDomainTests(unittest.TestCase):
    def test_real_chrome_address_label_with_trailing_whitespace(self):
        source = Path('desktop_pet/windows_focus.ps1').read_text(encoding='utf-8')
        labels = ['Barra de direcciones y de búsqueda ', ' Address and search bar ',
                  '\u00a0Barra de direcciones y búsqueda\u00a0',
                  'BARRA DE DIRECCIONES', 'Buscar en esta página', 'Instagram',
                  'fake Address and search bar', '']
        source += '\n@(' + ','.join("'"+label+"'" for label in labels) + ') | ForEach-Object {\n'
        source += '@{address=[PetFocus]::AddressName($_)} | ConvertTo-Json -Compress\n}'
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand',
            base64.b64encode(source.encode('utf-16-le')).decode()], input='', text=True,
            capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0)
        values = [json.loads(line)['address'] for line in result.stdout.splitlines()[1:]]
        self.assertEqual(values, [True]*4 + [False]*4)

    def test_close_names_accept_browser_shortcuts_but_not_unrelated_actions(self):
        source = Path('desktop_pet/windows_focus.ps1').read_text(encoding='utf-8')
        source += "\n@('Close tab (Ctrl+W)', 'Cerrar pestaña (Ctrl+W)', ' Close ', 'Cerrar ventana', 'Close account') | ForEach-Object {\n"
        source += '@{close=[PetFocus]::CloseName($_)} | ConvertTo-Json -Compress\n}'
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand',
            base64.b64encode(source.encode('utf-16-le')).decode()], input='', text=True,
            capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0)
        values = [json.loads(line)['close'] for line in result.stdout.splitlines()[1:]]
        self.assertEqual(values, [True, True, True, False, False])

    def test_exact_hosts_subdomains_and_spoof_rejection(self):
        urls = ['instagram.com', 'https://www.instagram.com/p/123', 'https://m.tiktok.com/',
                'https://www.instagram.com/accounts/login/?next=%2F',
                'https://www.instagram.com/accounts/login/',
                'https://instagram.com.evil.test', 'https://evil.test/instagram.com',
                'https://instagram.com@evil.test', 'https://evil@instagram.com',
                'https://notinstagram.com', 'file://instagram.com', 'instagram.com search']
        source = Path('desktop_pet/windows_focus.ps1').read_text(encoding='utf-8')
        source += '\n@(' + ','.join("'"+u+"'" for u in urls) + ') | ForEach-Object {\n'
        source += '@{site=[PetFocus]::Site($_)} | ConvertTo-Json -Compress\n}'
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand',
            base64.b64encode(source.encode('utf-16-le')).decode()], input='', text=True,
            capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0)
        values = [json.loads(line)['site'] for line in result.stdout.splitlines()[1:]]
        self.assertEqual(values, ['instagram.com', 'instagram.com', 'tiktok.com',
                                  'instagram.com', 'instagram.com'] + [None]*7)
