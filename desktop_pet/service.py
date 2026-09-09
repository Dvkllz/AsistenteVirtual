"""Text service independent from Qt; no credentials or network needed for demo."""

import os
from pathlib import Path
import time

import openai

MAX_QUESTION_CHARS = 800
MAX_OUTPUT_TOKENS = 120
DEFAULT_MODEL = "gpt-4.1-mini"
LOCAL_ENV_PATH = Path(__file__).resolve().parent.parent / ".env.local"
SYSTEM_PROMPT = (
    "Eres una pequeña mascota virtual de escritorio. Responde en español salvo que "
    "te pidan otro idioma. Sé útil, directo y ligeramente sarcástico, con humor "
    "amistoso y sin insultar. Responde en una o dos frases, con un máximo de 45 "
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


def answer_question(question: str, *, live: bool = False) -> str:
    question = question.strip()
    if not question:
        raise PetServiceError("Primero escribe algo. Aún no leo mentes.")
    if len(question) > MAX_QUESTION_CHARS:
        raise PetServiceError(f"Máximo {MAX_QUESTION_CHARS} caracteres por pregunta.")
    if not live:
        time.sleep(0.45)
        return "Respuesta de prueba: estoy listo para ayudarte. Mi talento para fingir que pienso es impecable."

    key = config_value("OPENAI_API_KEY")
    if not key:
        raise PetServiceError("Falta OPENAI_API_KEY. Configúrala y reinicia, o abre el modo de prueba.")
    model = config_value("OPENAI_MODEL") or DEFAULT_MODEL
    try:
        # No automatic retries: each submitted question makes at most one attempt.
        with openai.OpenAI(api_key=key, timeout=20.0, max_retries=0) as client:
            response = client.responses.create(
                model=model,
                instructions=SYSTEM_PROMPT,
                input=question,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                store=False,
            )
        text = response.output_text.strip()
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
