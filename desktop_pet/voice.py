"""Opt-in microphone capture in memory; bounded transcription off the GUI thread."""

from array import array
from contextlib import nullcontext
import io
import wave

import openai
from PyQt6.QtCore import QBuffer, QIODevice, QObject, QTimer, pyqtSignal
from PyQt6.QtMultimedia import QAudio, QAudioFormat, QAudioSource, QMediaDevices

from desktop_pet.service import MAX_QUESTION_CHARS, PetServiceError, config_value

MAX_RECORD_SECONDS = 15
MAX_AUDIO_BYTES = 48000 * 2 * 2 * MAX_RECORD_SECONDS + 44
TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"


def pcm_to_wav(pcm, rate, channels):
    frame_size = channels * 2
    pcm = pcm[:len(pcm) // frame_size * frame_size]
    if len(pcm) < rate * frame_size // 3:
        raise PetServiceError("Grabación demasiado corta. Mantén el micro al menos un segundo.")
    samples = array("h", pcm)
    if not samples or sum(value * value for value in samples) / len(samples) < 50 ** 2:
        raise PetServiceError("No se oyó suficiente audio. Acércate al micrófono e inténtalo otra vez.")
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(pcm)
    return output.getvalue()


def transcribe_audio(audio, *, live=False, session=None):
    # Demo mode cannot open a client, even if a key exists.
    if not live:
        raise PetServiceError("Activa OpenAI en el menú para dictar; la transcripción consume créditos.")
    if not audio or len(audio) > MAX_AUDIO_BYTES:
        raise PetServiceError("El audio está vacío o supera los 15 segundos permitidos.")
    key = config_value("OPENAI_API_KEY")
    if not key:
        raise PetServiceError("Falta la clave de OpenAI para transcribir.")
    try:
        connection = (nullcontext(session.get(key)) if session is not None
                      else openai.OpenAI(api_key=key, timeout=20.0, max_retries=0))
        with connection as client:
            result = client.audio.transcriptions.create(
                model=TRANSCRIPTION_MODEL,
                file=("pregunta.wav", audio, "audio/wav"),
                response_format="json",
            )
        text = result.text.strip()
        if not text:
            raise PetServiceError("No reconocí palabras. Puedes escribir la pregunta.")
        if len(text) > MAX_QUESTION_CHARS:
            raise PetServiceError("El dictado supera 800 caracteres. Prueba con una pregunta más corta.")
        return text
    except openai.AuthenticationError:
        raise PetServiceError("OpenAI no acepta la clave configurada.") from None
    except openai.RateLimitError:
        raise PetServiceError("OpenAI indica un límite de uso o saldo insuficiente.") from None
    except openai.APITimeoutError:
        raise PetServiceError("La transcripción tardó demasiado. No se reintentará automáticamente.") from None
    except openai.APIConnectionError:
        raise PetServiceError("No pude conectar para transcribir. Revisa tu conexión.") from None
    except openai.APIStatusError:
        raise PetServiceError("OpenAI rechazó la transcripción. Revisa el acceso al modelo.") from None


class Microphone(QObject):
    """Never constructs an audio input until the user explicitly calls start."""
    changed = pyqtSignal(bool)
    captured = pyqtSignal(bytes)
    failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recording = False
        self.source = None
        self.buffer = None
        self.format = None
        self.limit = QTimer(self)
        self.limit.setSingleShot(True)
        self.limit.setInterval(MAX_RECORD_SECONDS * 1000)
        self.limit.timeout.connect(self.stop)

    def start(self):
        if self.recording:
            return
        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            self.failed.emit("No hay micrófono disponible. Conecta uno y revisa los permisos de Windows.")
            return
        self.format = None
        for channels in (1, 2):
            for rate in (16000, 48000, 44100):
                candidate = QAudioFormat()
                candidate.setSampleRate(rate)
                candidate.setChannelCount(channels)
                candidate.setSampleFormat(QAudioFormat.SampleFormat.Int16)
                if device.isFormatSupported(candidate):
                    self.format = candidate
                    break
            if self.format is not None:
                break
        if self.format is None:
            self.failed.emit("Este micrófono no admite un formato compatible. Prueba otro dispositivo.")
            return
        self.buffer = QBuffer(self)
        self.buffer.open(QIODevice.OpenModeFlag.ReadWrite)
        self.source = QAudioSource(device, self.format, self)
        self.source.stateChanged.connect(self._state_changed)
        self.recording = True
        self.changed.emit(True)
        self.limit.start()
        self.source.start(self.buffer)
        if self.source is not None and self.source.error() != QAudio.Error.NoError:
            self._fail()

    def _state_changed(self, state):
        if (self.recording and self.source is not None
                and state == QAudio.State.StoppedState
                and self.source.error() != QAudio.Error.NoError):
            self._fail()

    def _fail(self):
        self.cancel()
        self.failed.emit("No pude grabar. Revisa el micrófono y los permisos de privacidad de Windows.")

    def _release(self):
        self.recording = False
        self.limit.stop()
        if self.source is not None:
            self.source.stop()
            self.source.deleteLater()
            self.source = None
        pcm = bytes(self.buffer.data()) if self.buffer is not None else b""
        if self.buffer is not None:
            self.buffer.close()
            self.buffer.deleteLater()
            self.buffer = None
        self.changed.emit(False)
        return pcm

    def cancel(self):
        if self.recording or self.source is not None:
            self._release()

    def stop(self):
        if not self.recording:
            return
        pcm = self._release()
        rate, channels = self.format.sampleRate(), self.format.channelCount()
        pcm = pcm[:rate * channels * 2 * MAX_RECORD_SECONDS]
        try:
            audio = pcm_to_wav(pcm, rate, channels)
        except PetServiceError as error:
            self.failed.emit(str(error))
            return
        self.captured.emit(audio)
