"""Offline frozen-build smoke check. No recording, credentials or real API requests."""
import json
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory
import time

from PyQt6.QtCore import QSettings, Qt, QUrl
from PyQt6.QtGui import QFontInfo
from PyQt6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer

from desktop_pet.paths import embedded_api_key, local_config_path
from desktop_pet.sounds import AUDIO_DIR, FILES
from desktop_pet.purring import PURR_PATH
from desktop_pet.window import PetWindow


def run(app, report_path):
    report = Path(report_path).resolve()
    result = {'ok': False, 'frozen': bool(getattr(sys, 'frozen', False)), 'checks': []}
    previous_connect = socket.socket.connect
    previous_connect_ex = socket.socket.connect_ex
    window = None
    players, outputs = [], []

    def forbid_network(*args, **kwargs):
        raise RuntimeError('Network is disabled during portable verification.')

    def wait_until(predicate, seconds=15):
        deadline = time.monotonic() + seconds
        while not predicate() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.01)
        if not predicate():
            raise RuntimeError('Portable verification timed out.')

    socket.socket.connect = forbid_network
    socket.socket.connect_ex = forbid_network
    app.setQuitOnLastWindowClosed(False)
    try:
        with TemporaryDirectory(prefix='pet-check-') as folder:
            settings = QSettings(str(Path(folder) / 'settings.ini'), QSettings.Format.IniFormat)
            for option in ('physics/enabled', 'sound/effects', 'sound/purr', 'autonomy/enabled',
                           'nap/enabled', 'autonomy/cursor_push', 'autonomy/cursor_carry'):
                settings.setValue(option, False)
            window = PetWindow(settings=settings)
            window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
            window.show()
            app.processEvents()
            assert not window.sprites.missing and not window.sprites.missing_animation
            assert all(not frame.isNull() for frame in window.sprites.frames.values())
            assert QFontInfo(window.input.font()).family() == 'Pixelify Sans'
            window.menu.ensurePolished()
            assert QFontInfo(window.menu.font()).family() == 'Pixelify Sans'
            assert window.height() - window.composer.geometry().bottom() - 1 == 8
            window.input.setText('Hola')
            window.send_button.click()
            wait_until(lambda: window.worker is None)
            assert 'prueba' in window.bubble.text()
            assert window.dialogue_frame.isVisible()
            assert window.microphone.source is None
            result['checks'].extend(['all_sprites', 'pixel_fonts', 'compact_layout', 'local_answer_thread'])
            assert not window.concentration.enabled
            assert not window.concentration_action.isChecked()
            from desktop_pet.concentration import FocusBridge
            bridge = FocusBridge(window)
            focus_messages, focus_failures = [], []
            bridge.message.connect(focus_messages.append)
            bridge.failed.connect(lambda: focus_failures.append(True))
            try:
                bridge.start()
                wait_until(lambda: bool(focus_messages or focus_failures))
                assert not focus_failures and focus_messages == [{'ready': True}]
                # No probe and no real target: this cannot close a browser tab.
                bridge.send('close', 'portable-check-invalid-token')
                wait_until(lambda: len(focus_messages) > 1 or bool(focus_failures))
                assert not focus_failures and focus_messages[-1] == {'closed': False}
                result['checks'].append('concentration_default_off_native_bridge_safe_rejection')
            finally:
                bridge.stop()
            assert Path(__file__).resolve().parent.parent.joinpath('assets/fonts/OFL.txt').is_file()
            if result['frozen']:
                assert local_config_path().parent == Path(sys.executable).resolve().parent
                assert not Path(sys._MEIPASS, '.env.local').exists()
                assert Path(sys._MEIPASS, 'licenses/Python-LICENSE.txt').is_file()
                result['checks'].append('external_config_no_embedded_env')
                private_path = Path(sys._MEIPASS, 'private-config/openai.key')
                result['embedded_key_present'] = private_path.is_file()
                if private_path.is_file():
                    from desktop_pet.service import config_value
                    # Compare only in memory. Reports must never contain the value.
                    key = embedded_api_key()
                    assert key.startswith('sk-') and len(key) >= 40
                    assert config_value('OPENAI_API_KEY') == key
                    del key
                    result['checks'].append('embedded_key_loads_without_external_config')
            # Decode every shipped effect without playing audible sound or recording.
            for path in [*(AUDIO_DIR / file for file in FILES.values()), PURR_PATH]:
                assert path.is_file()
                output = QAudioOutput()
                output.setMuted(True)
                player = QMediaPlayer()
                player.setAudioOutput(output)
                outputs.append(output)
                players.append(player)
                player.setSource(QUrl.fromLocalFile(str(path)))
                player.play()
            wait_until(lambda: all(player.position() > 0 or
                                   player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia
                                   for player in players))
            assert all(player.error() == QMediaPlayer.Error.NoError for player in players)
            for player in players:
                player.stop()
            result['checks'].append('all_mp3_decoders_muted')
            result['microphone_devices_detected'] = len(QMediaDevices.audioInputs())
            result['checks'].append('microphone_enumeration_without_recording')

            # Exercise SDK lazy imports inside the executable using an in-memory transport.
            import httpx
            import openai
            def respond(request):
                if request.url.path.endswith('/audio/transcriptions'):
                    return httpx.Response(200, json={'text': 'Dictado sin red.'})
                return httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=(
                    'event: response.output_text.delta\n'
                    'data: {"type":"response.output_text.delta","delta":"Listo."}\n\n'
                    'data: [DONE]\n\n').encode())
            with openai.OpenAI(api_key='offline-test-not-a-key', max_retries=0,
                              http_client=httpx.Client(transport=httpx.MockTransport(respond),
                                                       trust_env=False)) as client:
                with client.responses.create(model='gpt-4.1-mini', input='Prueba', stream=True) as stream:
                    assert ''.join(event.delta for event in stream) == 'Listo.'
                assert client.audio.transcriptions.create(model='gpt-4o-mini-transcribe',
                    file=('prueba.wav', b'offline-test', 'audio/wav')).text == 'Dictado sin red.'
            result['checks'].append('sdk_stream_and_transcription_mock_transport')
            report.parent.mkdir(parents=True, exist_ok=True)
            assert window.grab().save(str(report.with_suffix('.png')))
            window.close()
            window = None
            result['ok'] = True
    except Exception as error:
        # Never serialize raw exceptions or configuration values into the report.
        result['error_type'] = type(error).__name__
    finally:
        for player in players:
            player.stop()
        if window is not None:
            if window.worker is not None:
                window.worker.wait(5000)
                app.processEvents()
            window.close()
        socket.socket.connect = previous_connect
        socket.socket.connect_ex = previous_connect_ex
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['ok'] else 1
