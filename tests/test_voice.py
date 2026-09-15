"""Voice tests use fake devices and HTTP transports, never a real microphone."""
from array import array
import io
import os
import threading
import time
import unittest
import wave
from unittest.mock import MagicMock, patch

import httpx
import openai
from PyQt6.QtCore import QSettings, QTimer
from PyQt6.QtMultimedia import QAudio
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from pathlib import Path
from tempfile import TemporaryDirectory

from desktop_pet.service import PetServiceError
from desktop_pet.voice import Microphone, pcm_to_wav, transcribe_audio, MAX_AUDIO_BYTES
from desktop_pet.window import PetWindow, reading_time_ms


def sample_pcm():
    return array("h", [1000, -1000] * 8000).tobytes()


class VoiceServiceTests(unittest.TestCase):
    def test_wav_and_silence_guard(self):
        payload = pcm_to_wav(sample_pcm(), 16000, 1)
        with wave.open(io.BytesIO(payload), "rb") as audio:
            self.assertEqual(audio.getframerate(), 16000)
            self.assertEqual(audio.getnchannels(), 1)
            self.assertEqual(audio.getnframes(), 16000)
        for pcm in (b"", b"\0" * 32000, b"\0" * 400):
            with self.assertRaises(PetServiceError):
                pcm_to_wav(pcm, 16000, 1)

    def test_demo_empty_oversize_and_missing_key_never_call_api(self):
        with patch("desktop_pet.voice.openai.OpenAI") as client, \
                patch("desktop_pet.voice.config_value", return_value=""):
            for payload, live in ((b"data", False), (b"", True),
                                  (b"x" * (MAX_AUDIO_BYTES + 1), True), (b"data", True)):
                with self.assertRaises(PetServiceError):
                    transcribe_audio(payload, live=live)
            client.assert_not_called()

    def test_real_sdk_with_fake_http_transcribes_once(self):
        requests = []
        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={"text": "Hola, gato."})
        client = openai.OpenAI(api_key="test-only-not-a-key", max_retries=0,
                              http_client=httpx.Client(transport=httpx.MockTransport(respond)))
        with patch("desktop_pet.voice.config_value", return_value="test-only-not-a-key"), \
                patch("desktop_pet.voice.openai.OpenAI", return_value=client) as factory:
            self.assertEqual(transcribe_audio(pcm_to_wav(sample_pcm(), 16000, 1), live=True),
                             "Hola, gato.")
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url.path, "/v1/audio/transcriptions")
        self.assertIn(b"gpt-4o-mini-transcribe", requests[0].content)
        self.assertIn(b"pregunta.wav", requests[0].content)
        self.assertEqual(factory.call_args.kwargs["max_retries"], 0)
        self.assertEqual(factory.call_args.kwargs["timeout"], 20)

    def test_safe_errors_and_no_raw_details(self):
        request = httpx.Request("POST", "https://api.openai.com/v1/audio/transcriptions")
        errors = [
            openai.AuthenticationError("private", response=httpx.Response(401, request=request), body=None),
            openai.RateLimitError("private", response=httpx.Response(429, request=request), body=None),
            openai.APITimeoutError(request=request), openai.APIConnectionError(request=request),
            openai.APIStatusError("private", response=httpx.Response(500, request=request), body=None),
        ]
        for error in errors:
            with patch("desktop_pet.voice.config_value", return_value="fake"), \
                    patch("desktop_pet.voice.openai.OpenAI", side_effect=error):
                with self.assertRaises(PetServiceError) as caught:
                    transcribe_audio(b"data", live=True)
                self.assertNotIn("private", str(caught.exception))

    def test_empty_and_long_transcripts_are_not_submitted(self):
        for text in (" ", "a" * 801):
            with patch("desktop_pet.voice.config_value", return_value="fake"), \
                    patch("desktop_pet.voice.openai.OpenAI") as factory:
                factory.return_value.__enter__.return_value.audio.transcriptions.create.return_value.text = text
                with self.assertRaises(PetServiceError):
                    transcribe_audio(b"data", live=True)

    def test_reading_duration_grows_with_length_and_is_bounded(self):
        self.assertEqual(reading_time_ms("Hola."), 6000)
        self.assertEqual(reading_time_ms("palabra " * 45), 21000)
        self.assertEqual(reading_time_ms("palabra " * 200), 30000)


class MicrophoneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.guard = patch("socket.socket.connect", side_effect=AssertionError("No real network"))
        self.guard.start()
        self.factory = patch("desktop_pet.voice.QAudioSource")
        self.source_factory = self.factory.start()
        self.source = self.source_factory.return_value
        self.source.error.return_value = QAudio.Error.NoError
        self.device_patch = patch("desktop_pet.voice.QMediaDevices.defaultAudioInput")
        self.device = self.device_patch.start().return_value
        self.device.isNull.return_value = False
        self.device.isFormatSupported.return_value = True
        self.mic = Microphone()
        self.captured, self.errors = [], []
        self.mic.captured.connect(self.captured.append)
        self.mic.failed.connect(self.errors.append)

    def tearDown(self):
        self.mic.cancel()
        self.mic.deleteLater()
        self.app.processEvents()
        self.device_patch.stop()
        self.factory.stop()
        self.guard.stop()

    def test_no_device_access_until_explicit_start_and_no_duplicate_start(self):
        self.source_factory.assert_not_called()
        self.mic.start()
        self.mic.start()
        self.source_factory.assert_called_once()
        self.assertEqual(self.mic.limit.interval(), 15000)
        self.assertTrue(self.mic.recording)
        self.assertEqual(self.captured, [])

    def test_stop_produces_wav_and_frees_recording(self):
        self.mic.start()
        self.mic.buffer.write(sample_pcm())
        self.mic.stop()
        self.mic.stop()
        self.assertFalse(self.mic.recording)
        self.assertIsNone(self.mic.buffer)
        self.assertIsNone(self.mic.source)
        self.source.stop.assert_called_once()
        self.assertEqual(len(self.captured), 1)
        self.assertTrue(self.captured[0].startswith(b"RIFF"))

    def test_cancel_never_emits_audio(self):
        self.mic.start()
        self.mic.buffer.write(sample_pcm())
        self.mic.cancel()
        self.assertEqual(self.captured, [])
        self.assertFalse(self.mic.limit.isActive())
        self.assertIsNone(self.mic.buffer)

    def test_timeout_stops_recording(self):
        self.mic.start()
        self.mic.buffer.write(sample_pcm())
        self.mic.limit.start(10)
        QTest.qWait(30)
        self.assertFalse(self.mic.recording)
        self.assertEqual(len(self.captured), 1)

    def test_silence_missing_device_unsupported_format_and_access_error(self):
        self.device.isNull.return_value = True
        self.mic.start()
        self.source_factory.assert_not_called()
        self.device.isNull.return_value = False
        self.device.isFormatSupported.return_value = False
        self.mic.start()
        self.source_factory.assert_not_called()
        self.device.isFormatSupported.return_value = True
        self.mic.start()
        self.mic.buffer.write(b"\0" * 32000)
        self.mic.stop()
        self.source.error.return_value = QAudio.Error.OpenError
        self.mic.start()
        self.assertFalse(self.mic.recording)
        self.assertEqual(self.captured, [])
        self.assertEqual(len(self.errors), 4)


class VoiceWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = TemporaryDirectory()
        settings = QSettings(str(Path(self.temp.name) / "settings.ini"), QSettings.Format.IniFormat)
        for name in ("physics/enabled", "autonomy/enabled", "nap/enabled", "sound/effects", "sound/purr"):
            settings.setValue(name, False)
        self.guards = [
            patch("socket.socket.connect", side_effect=AssertionError("No real network")),
            patch("desktop_pet.voice.QAudioSource", side_effect=AssertionError("No real microphone")),
            patch("desktop_pet.autonomy.QCursor.setPos", side_effect=AssertionError("No cursor writes")),
        ]
        for guard in self.guards:
            guard.start()
        self.window = PetWindow(settings=settings)
        self.window.show()
        self.app.processEvents()

    def wait_until(self, condition):
        deadline = time.monotonic() + 3
        while not condition() and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertTrue(condition())

    def tearDown(self):
        self.wait_until(lambda: self.window.voice_worker is None and self.window.worker is None)
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        for guard in reversed(self.guards):
            guard.stop()
        self.temp.cleanup()

    def test_demo_and_existing_draft_do_not_record(self):
        with patch.object(self.window.microphone, "start") as start:
            self.window.mic_button.click()
            start.assert_not_called()
            self.window.set_mode(True, announce=False)
            self.window.input.setText("Mi borrador")
            with patch("desktop_pet.window.has_openai_key", return_value=True):
                self.window.mic_button.click()
            start.assert_not_called()
            self.assertEqual(self.window.input.text(), "Mi borrador")

    def test_opt_in_recording_controls_and_cancel(self):
        self.window.set_mode(True, announce=False)
        def fake_start():
            self.window.microphone.recording = True
            self.window.microphone.changed.emit(True)
        with patch("desktop_pet.window.has_openai_key", return_value=True), \
                patch.object(self.window.microphone, "start", side_effect=fake_start) as start:
            self.window.mic_button.click()
        start.assert_called_once()
        self.assertTrue(self.window.voice_busy)
        self.assertFalse(self.window.input.isEnabled())
        self.assertFalse(self.window.demo_action.isEnabled())
        self.assertTrue(self.window.mic_button.isEnabled())
        self.assertIn("GRABANDO", self.window.mode.text())
        self.window.cancel_voice.activated.emit()
        self.assertFalse(self.window.voice_busy)
        self.assertTrue(self.window.input.isEnabled())

    def test_transcript_automatically_submits_once_and_ui_keeps_ticking(self):
        self.window.set_mode(True, announce=False)
        gate = threading.Event()
        ticks = []
        timer = QTimer(self.window)
        timer.setInterval(10)
        timer.timeout.connect(lambda: ticks.append(1))
        timer.start()
        def fake_transcribe(audio, live, session):
            self.assertTrue(live)
            gate.wait(1)
            return "¿Qué tal?"
        with patch("desktop_pet.window.transcribe_audio", side_effect=fake_transcribe) as transcribe, \
                patch("desktop_pet.window.answer_question", return_value="Todo bien.") as answer:
            self.window._transcribe(b"fake")
            self.window._transcribe(b"duplicate")
            QTest.qWait(40)
            self.assertTrue(ticks)
            self.assertFalse(self.window.mic_button.isEnabled())
            self.assertFalse(self.window.input.isEnabled())
            gate.set()
            self.wait_until(lambda: self.window.voice_worker is None and self.window.worker is None)
            transcribe.assert_called_once()
            answer.assert_called_once()
            self.assertEqual(answer.call_args.args, ("¿Qué tal?",))
            self.assertIs(answer.call_args.kwargs["session"], transcribe.call_args.kwargs["session"])
        self.assertEqual(self.window.input.text(), "")
        self.assertTrue(self.window.input.isEnabled())
        self.assertEqual(self.window.bubble.text(), "Todo bien.")
        self.assertTrue(self.window.mode.isHidden())

    def test_failed_dictation_does_not_submit_text_or_retry(self):
        self.window.set_mode(True, announce=False)
        with patch("desktop_pet.window.transcribe_audio", side_effect=PetServiceError("No reconocí palabras.")) as transcribe, \
                patch("desktop_pet.window.answer_question") as answer:
            self.window._transcribe(b"fake")
            self.wait_until(lambda: self.window.voice_worker is None)
            transcribe.assert_called_once()
            answer.assert_not_called()
        self.assertIn("No reconocí", self.window.bubble.text())
        self.assertTrue(self.window.mode.isHidden())
        self.assertTrue(self.window.mic_button.isEnabled())

    def test_demo_cannot_send_audio_even_if_capture_signal_is_emitted(self):
        with patch("desktop_pet.window.transcribe_audio") as transcribe:
            self.window.microphone.captured.emit(b"fake")
            self.app.processEvents()
            transcribe.assert_not_called()
            self.assertIsNone(self.window.voice_worker)

    def test_close_waits_for_transcription_and_does_not_display_late_result(self):
        self.window.set_mode(True, announce=False)
        gate = threading.Event()
        def fake_transcribe(*args, **kwargs):
            gate.wait(1)
            return "late"
        with patch("desktop_pet.window.transcribe_audio", side_effect=fake_transcribe):
            self.window._transcribe(b"fake")
            self.window.close()
            self.assertFalse(self.window.isVisible())
            self.assertIsNotNone(self.window.voice_worker)
            gate.set()
            self.wait_until(lambda: self.window.voice_worker is None)
        self.assertNotEqual(self.window.input.text(), "late")

    def test_sleep_and_autonomy_blocked_during_recording(self):
        self.window.microphone.recording = True
        self.window.naps.enabled = True
        self.window.naps.next_allowed = 0
        self.window.setFocus()
        with patch("desktop_pet.napping.input_idle_seconds", return_value=31), \
                patch("desktop_pet.napping.mouse_button_down", return_value=False):
            self.window.naps.tick()
        self.assertFalse(self.window.sleeping)
        self.assertTrue(self.window.autonomy.busy())
        self.window.microphone.cancel()
