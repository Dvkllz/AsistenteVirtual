"""Opt-in local tab intervention. The helper invokes a verified tab button only."""
import base64
import json
import math
import os
from pathlib import Path
import sys
import subprocess
import threading
import time

from PyQt6.QtCore import QObject, QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QLabel

from desktop_pet.autonomy import escape_pressed, mouse_button_down
from desktop_pet import RELEASE_LABEL

FOCUS_VERSION = 'Concentración · ' + RELEASE_LABEL
WALK_SECONDS = 1.5
JUMP_SECONDS = 1.15
CONTACT_SECONDS = WALK_SECONDS + JUMP_SECONDS


def smooth_progress(value):
    """Quintic easing: zero velocity and acceleration at both ends."""
    t = max(0.0, min(1.0, value))
    return t*t*t*(t*(t*6-15)+10)


def paw_offset(direction):
    # Front paw in the extended jumping frame, centered in the 152x112 overlay.
    return QPoint(128 if direction > 0 else 24, 60)


def approach_position(origin, destination, direction, elapsed):
    """Smooth run-up and diagonal leap; ends with the front paw on the tab X."""
    available = max(0, direction * (destination.x()-origin.x()))
    runup = min(90.0, available * .3)
    launch_x = destination.x()-direction*runup
    if elapsed < WALK_SECONDS:
        t = smooth_progress(elapsed/WALK_SECONDS)
        return (origin.x()+(launch_x-origin.x())*t, float(origin.y()), 'walking',
                int(max(0.0, elapsed)/.12) % 4)
    t = max(0.0, min(1.0, (elapsed-WALK_SECONDS)/JUMP_SECONDS))
    ease = smooth_progress(t)
    return (launch_x+(destination.x()-launch_x)*ease,
            origin.y()+(destination.y()-origin.y())*ease-20*math.sin(math.pi*t)**2,
            'falling', 1 if t < .08 else 2)
REASONS = {
    'off': 'Desactivado',
    'starting': 'Preparando detector…',
    'ready': 'Detector listo; abre Instagram o TikTok en Chrome/Edge.',
    'unsupported_window': 'Pon Chrome o Edge en primer plano.',
    'address_unavailable': 'No se puede leer la barra de direcciones (sal de pantalla completa).',
    'selected_tab_unavailable': 'El navegador no informa cuál es la pestaña activa.',
    'editing_address': 'Termina de escribir la dirección y pulsa Enter.',
    'address_value_unavailable': 'Windows no permite leer la dirección del navegador.',
    'allowed_site': 'La página actual no es Instagram ni TikTok.',
    'close_unavailable': 'No encuentro la X de la pestaña; comprueba que no esté fijada.',
    'window_changed': 'Cambiaste de ventana; acción cancelada.',
    'close_geometry_unavailable': 'La X de la pestaña no está visible.',
    'monitor_unavailable': 'No se pudo localizar la pantalla del navegador.',
    'accessibility_unavailable': 'No se pudo leer el navegador; prueba a reiniciarlo.',
    'screen_unavailable': 'La pantalla del navegador no coincide con las detectadas.',
    'blocked': 'En pausa mientras interactúas con el gato, escribes o mantienes un botón.',
    'detected': 'Página detectada; voy hacia la X.',
    'failed': 'El detector no respondió. Desactiva y vuelve a activar el modo.',
    'cancelled': 'Acción cancelada.',
    'closed': 'Se solicitó cerrar la pestaña.',
}


class FocusBridge(QObject):
    message = pyqtSignal(dict)
    failed = pyqtSignal()
    received = pyqtSignal(int, bytes)
    ended = pyqtSignal(int)

    def __init__(self, parent):
        super().__init__(parent)
        self.process = None
        self.generation = 0
        self.received.connect(self._read)
        self.ended.connect(lambda generation: self._fail() if generation == self.generation else None)
        self.deadline = QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.timeout.connect(self._fail)
        self.running = False

    def start(self):
        if self.running:
            return
        self.running = True
        self.generation += 1
        try:
            source = Path(__file__).with_name('windows_focus.ps1').read_text(encoding='utf-8')
            encoded = base64.b64encode(source.encode('utf-16-le')).decode('ascii')
            env = os.environ.copy()
            env.pop('OPENAI_API_KEY', None)
            program = str(Path(os.environ.get('SystemRoot', 'C:/Windows')) /
                          'System32/WindowsPowerShell/v1.0/powershell.exe')
            self.process = subprocess.Popen(
                [program, '-NoLogo', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden',
                 '-EncodedCommand', encoded], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
            threading.Thread(target=self._listen, args=(self.process, self.generation),
                             name='pet-focus-reader', daemon=True).start()
            self.deadline.start(10000)
        except (OSError, UnicodeError):
            self._fail()

    def send(self, command, token=None):
        if not self.running:
            return
        request = {'command': command}
        if token is not None:
            request['token'] = token
        try:
            self.process.stdin.write((json.dumps(request) + '\n').encode('utf-8'))
            self.process.stdin.flush()
            self.deadline.start(3000)
        except (OSError, ValueError):
            self._fail()

    def _listen(self, process, generation):
        try:
            while line := process.stdout.readline(16385):
                self.received.emit(generation, line)
            self.ended.emit(generation)
        except (OSError, ValueError, RuntimeError):
            pass
        finally:
            process.stdout.close()

    def _read(self, generation, line):
        if generation != self.generation or not self.running:
            return
        try:
            if len(line) > 16384:
                raise ValueError()
            result = json.loads(line)
            if not isinstance(result, dict):
                raise ValueError()
        except (ValueError, UnicodeError):
            self._fail()
            return
        self.deadline.stop()
        self.message.emit(result)

    def stop(self):
        self.running = False
        self.generation += 1
        self.deadline.stop()
        process, self.process = self.process, None
        if process is not None:
            try:
                if process.poll() is None:
                    process.kill()  # Only our own helper, never a browser process.
                process.wait(timeout=.5)
            except (OSError, subprocess.TimeoutExpired):
                pass
            try:
                process.stdin.close()
            except OSError:
                pass

    def _fail(self):
        if self.running:
            self.stop()
            self.failed.emit()


def target_point(target, screens):
    """UIA physical coordinates -> Qt logical coordinates, per monitor."""
    try:
        if target['site'] not in ('instagram.com', 'tiktok.com') or not target['token']:
            return None
        for screen in screens:
            if screen.name().casefold() != target['monitor'].casefold():
                continue
            x, y, left, top = (float(target[k]) for k in ('x', 'y', 'left', 'top'))
            if not all(math.isfinite(v) for v in (x, y, left, top)):
                return None
            g, scale = screen.geometry(), screen.devicePixelRatio()
            p = QPoint(g.x() + round((x-left)/scale), g.y() + round((y-top)/scale))
            return p if g.contains(p) else None
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return None
    return None


class Concentration:
    def __init__(self, window, bridge=None):
        self.window = window
        self.enabled = self.active = False
        self.ready = False
        self.pending = None
        self.target = None
        self.seen = None
        self.cooldown = 0.0
        self.reason = 'off'
        self.bridge = bridge or FocusBridge(window)
        self.bridge.message.connect(self._message)
        self.bridge.failed.connect(self._failed)
        self.poll = QTimer(window)
        self.poll.setInterval(650)
        self.poll.timeout.connect(self._probe)
        self.animation = QTimer(window)
        self.animation.setInterval(16)
        self.animation.setTimerType(Qt.TimerType.PreciseTimer)
        self.animation.timeout.connect(self._tick)
        self.overlay = QLabel(window, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                              | Qt.WindowType.WindowStaysOnTopHint
                              | Qt.WindowType.WindowTransparentForInput
                              | Qt.WindowType.WindowDoesNotAcceptFocus)
        for flag in (Qt.WidgetAttribute.WA_TranslucentBackground,
                     Qt.WidgetAttribute.WA_ShowWithoutActivating,
                     Qt.WidgetAttribute.WA_TransparentForMouseEvents):
            self.overlay.setAttribute(flag)
        self.overlay.setFixedSize(152, 112)
        self.overlay.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        self.overlay.hide()
        policy = window.character.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        window.character.setSizePolicy(policy)

    def set_enabled(self, enabled):
        self.enabled = bool(enabled) and sys.platform == 'win32'
        self.cancel()
        if self.enabled:
            self._status('starting')
            self.bridge.start()
            if not self.enabled:
                return
            self.poll.start()
            self.window._show_status('CONCENTRACIÓN · Esc cancela')
        else:
            self.poll.stop()
            self.ready = False
            self.pending = None
            self.bridge.stop()
            self._status('off')

    def _status(self, reason):
        self.reason = reason if reason in REASONS else 'accessibility_unavailable'
        action = getattr(self.window, 'concentration_status_action', None)
        if action:
            label = ('Desactivado' if self.reason == 'off' else
                     'Detectando' if self.reason in ('starting', 'ready', 'allowed_site') else
                     'Página detectada' if self.reason == 'detected' else 'Ver estado')
            action.setText(FOCUS_VERSION + ' · ' + label)
            action.setToolTip(REASONS[self.reason])

    def explain(self):
        # A local message, never an API request. Opening the menu must not erase
        # the last detector result before the user can read it.
        self.window.show_response(FOCUS_VERSION + ': ' + REASONS[self.reason])

    def _blocked(self):
        w = self.window
        return (w._closing or not w.isVisible() or w._drag_offset is not None or w.petting
                or w.sleeping or w.menu.isVisible()
                or (w.isActiveWindow() and (w.input.hasFocus() or bool(w.input.text())))
                or w.worker is not None or w.voice_busy or w.talking_timer.isActive()
                or mouse_button_down() or escape_pressed())

    def _probe(self):
        if not self.enabled or not self.ready or self.pending:
            return
        if self._blocked():
            if not self.window.menu.isVisible():
                self._status('blocked')
            self.cancel()
            return
        if time.monotonic() < self.cooldown:
            return
        self.pending = 'probe'
        self.bridge.send('probe')

    def _message(self, result):
        if not self.enabled:
            return
        if result.get('ready'):
            self.ready = True
            self._status('ready')
            return
        command, self.pending = self.pending, None
        if command == 'close':
            completed = self.active and result.get('closed') is True
            self.cancel()
            self.cooldown = time.monotonic() + 20
            self._status('closed' if completed else 'cancelled')
            if completed:
                self.window.show_response('Te ahorré cuarenta minutos. De nada.')
            return
        target = result.get('target')
        point = target_point(target, QApplication.screens()) if isinstance(target, dict) else None
        if point is None or self._blocked():
            self._status('screen_unavailable' if isinstance(target, dict) and point is None
                         else result.get('reason', 'blocked'))
            self.cancel()
            return
        if self.active:
            if target != self.target:
                self._status('window_changed')
                self.cancel()
            elif time.monotonic() - self.started >= CONTACT_SECONDS:
                # The helper revalidates URL, foreground, tab identity and exact X again.
                self.pending = 'close'
                self.bridge.send('close', self.target['token'])
        elif self.seen == target and time.monotonic() >= self.cooldown:
            self._status('detected')
            self._begin(target, point)
        else:
            self.seen = target

    def _begin(self, target, point):
        w = self.window
        if w.autonomy:
            w.autonomy.cancel()
        w._cancel_walk()
        w._stop_motion()
        self.active = True
        self.target = target
        self.started = time.monotonic()
        self.origin = w.character.mapToGlobal(QPoint(w.character.width()//2-76, 0))
        self.direction = 1 if point.x() >= self.origin.x()+76 else -1
        self.destination = point - paw_offset(self.direction)
        # Allow the ears above the monitor edge: clamping the whole rectangle
        # kept the paw below the X on maximized browsers.
        w.character.hide()
        self.overlay.move(self.origin)
        self._tick()
        self.overlay.show()
        self.animation.start()

    def _tick(self):
        if not self.active:
            return
        if self._blocked():
            self.cancel()
            return
        elapsed = time.monotonic() - self.started
        x, y, state, frame = approach_position(self.origin, self.destination, self.direction, elapsed)
        self.overlay.setPixmap(self.window.sprites.pixmap(state, self.direction, frame))
        self.overlay.move(round(x), round(y))
        self.window.sounds.set_walking(state == 'walking')
        if elapsed >= CONTACT_SECONDS and not self.pending and self.ready:
            # Revalidate at contact rather than hanging at the X until the next poll.
            self.pending = 'probe'
            self.bridge.send('probe')
        if elapsed > 7:
            self.cancel()

    def cancel(self):
        if self.pending == 'close':
            # Interrupt a not-yet-invoked close when the user cancels.
            self.pending = None
            self.ready = False
            self.bridge.stop()
            if self.enabled:
                self.bridge.start()
        self.seen = None
        self.target = None
        if not self.active:
            return
        self.active = False
        self.animation.stop()
        self.overlay.hide()
        self.window.character.show()
        self.window.sounds.set_walking(False)
        self.cooldown = time.monotonic() + 5
        self.window._refresh_sprite()
        self.window._start_motion()

    def _failed(self):
        self.set_enabled(False)
        self.window.concentration_action.setChecked(False)
        self.window._show_status('Concentración no disponible')
        self._status('failed')

    def close(self):
        self.set_enabled(False)
