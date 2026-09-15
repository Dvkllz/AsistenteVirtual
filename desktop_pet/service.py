"""Text service independent from Qt; no credentials or network needed for demo."""

import os
from contextlib import nullcontext
from pathlib import Path

import openai

MAX_QUESTION_CHARS = 800
MAX_OUTPUT_TOKENS = 120
DEFAULT_MODEL = "gpt-4.1-mini"
LOCAL_ENV_PATH = Path(__file__).resolve().parent.parent / ".env.local"
SYSTEM_PROMPT = (
    "Eres una pequeña mascota virtual de escritorio. Responde en español salvo que "
    "te pidan otro idioma. Eres un gato siamés: útil, directo y casi siempre "
    "sarcástico. Añade normalmente una pulla breve, ingeniosa y amistosa sobre "
    "tu pereza felina o las costumbres de quien te habla, sin insultos ni crueldad. "
    "Dirígete de tú, sin vocativos ni apodos: nunca llames al usuario "
    "'humano', 'humana', 'humanos', 'humanas' ni 'mortal'. "
    "El sarcasmo está en la observación ingeniosa, no en cómo llamas a la persona. "
    "Ante angustia, emergencias o temas sensibles, deja el sarcasmo y responde "
    "con empatía. No sacrifiques la precisión por una broma. "
    "Responde en una o dos frases, con un máximo de 45 "
    "palabras. Usa texto plano, sin Markdown. No inventes capacidades: solo puedes "
    "responder texto, no ver la pantalla ni controlar el equipo."
)


class PetServiceError(Exception):
    """A safe, user-facing error, never a raw API error or credential."""


def _local_env_value(name: str) -> str:
    try:
        lines = LOCAL_ENV_PATH.read_text(encoding="utf-8-sig").splitlines()
    except (FileNotFoundError, OSError):
        return ""
    for line in lines:
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            return value.strip().strip('"').strip("'")
    return ""


def config_value(name: str) -> str:
    if name in os.environ:
        return os.environ[name].strip()
    return _local_env_value(name)


def has_openai_key() -> bool:
    key = config_value("OPENAI_API_KEY")
    return key.startswith("sk-") and len(key) >= 40


class ApiSession:
    """One lazy connection pool per window, shared by serialized voice/text jobs."""
    def __init__(self):
        self._client = None
        self._key = ""

    def get(self, key):
        if self._client is None or key != self._key:
            self.close()
            self._client = openai.OpenAI(api_key=key, timeout=20.0, max_retries=0)
            self._key = key
        return self._client

    def close(self):
        client, self._client, self._key = self._client, None, ""
        if client is not None:
            client.close()


def _stream_response(client, parameters, on_partial):
    text, final = "", None
    with client.responses.create(**parameters, stream=True) as events:
        for event in events:
            if event.type in ("response.output_text.delta", "response.refusal.delta"):
                text += event.delta
                on_partial(text)
            elif event.type in ("response.completed", "response.incomplete"):
                final = event.response
            elif event.type in ("response.failed", "error"):
                raise PetServiceError("OpenAI no pudo terminar la respuesta. Puedes intentarlo de nuevo.")
    if final is None:
        raise PetServiceError("La respuesta se interrumpió. No se reintentará automáticamente.")
    return final, text


def answer_question(question: str, *, live: bool = False, on_partial=None, session=None) -> str:
    question = question.strip()
    if not question:
        raise PetServiceError("Primero escribe algo. Aún no leo mentes.")
    if len(question) > MAX_QUESTION_CHARS:
        raise PetServiceError(f"Máximo {MAX_QUESTION_CHARS} caracteres por pregunta.")
    if not live:
        return "Respuesta de prueba: estoy listo para ayudarte. Mi talento para fingir que pienso es impecable."

    key = config_value("OPENAI_API_KEY")
    if not key:
        raise PetServiceError("Falta OPENAI_API_KEY. Configúrala y reinicia, o abre el modo de prueba.")
    model = config_value("OPENAI_MODEL") or DEFAULT_MODEL
    try:
        # No automatic retries: each submitted question makes at most one attempt.
        connection = (nullcontext(session.get(key)) if session is not None
                      else openai.OpenAI(api_key=key, timeout=20.0, max_retries=0))
        streamed_text = ""
        with connection as client:
            parameters = dict(
                model=model,
                instructions=SYSTEM_PROMPT,
                input=question,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                store=False,
            )
            if on_partial is not None:
                response, streamed_text = _stream_response(client, parameters, on_partial)
            else:
                response = client.responses.create(**parameters)
        text = (response.output_text or streamed_text).strip()
        if not text:
            raise PetServiceError("No llegó una respuesta de texto. Puedes intentarlo de nuevo.")
        if response.status == "incomplete":
            text += "\n[Respuesta limitada para ahorrar tokens.]"
        return text
    except openai.AuthenticationError:
        raise PetServiceError("La clave de OpenAI no es válida. Revísala y reinicia.") from None
    except openai.RateLimitError:
        raise PetServiceError("OpenAI indica un límite de uso o saldo insuficiente. Revisa tu cuenta.") from None
    except openai.APITimeoutError:
        raise PetServiceError("OpenAI tardó demasiado. Puedes volver a intentarlo.") from None
    except openai.APIConnectionError:
        raise PetServiceError("No pude conectar con OpenAI. Revisa tu conexión.") from None
    except openai.APIStatusError:
        raise PetServiceError("OpenAI rechazó la solicitud. Revisa el modelo y el acceso de tu cuenta.") from None
