"""Exercise real SDK streaming through an in-memory transport, never the API."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import openai

from desktop_pet.service import ApiSession, PetServiceError, answer_question
from desktop_pet.voice import transcribe_audio


class StreamingServiceTests(unittest.TestCase):
    def response(self, status="completed"):
        return {"id": "resp_test", "object": "response", "created_at": 1,
                "model": "gpt-4.1-mini", "status": status,
                "output": [{"id": "msg_test", "type": "message", "role": "assistant",
                            "status": "completed", "content": [
                                {"type": "output_text", "text": "Hola. Ya era hora.", "annotations": []}]}]}

    def invoke(self, events, on_partial):
        requests = []
        payload = "".join("data: " + json.dumps(event) + "\n\n" for event in events) + "data: [DONE]\n\n"
        def respond(request):
            requests.append(request)
            return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                  content=payload.encode())
        client = openai.OpenAI(api_key="test-only-not-a-key", max_retries=0,
                              http_client=httpx.Client(transport=httpx.MockTransport(respond)))
        with patch("desktop_pet.service.config_value",
                   side_effect=lambda name: "test-only-not-a-key" if name == "OPENAI_API_KEY" else ""), \
                patch("desktop_pet.service.openai.OpenAI", return_value=client):
            result = answer_question("Hola", live=True, on_partial=on_partial)
        return result, requests

    def test_progressive_text_uses_one_request_and_original_spending_limits(self):
        chunks = []
        result, requests = self.invoke([
            {"type": "response.output_text.delta", "delta": "Hola."},
            {"type": "response.output_text.delta", "delta": " Ya era hora."},
            {"type": "response.completed", "response": self.response()},
        ], chunks.append)
        self.assertEqual(chunks, ["Hola.", "Hola. Ya era hora."])
        self.assertEqual(result, chunks[-1])
        self.assertEqual(len(requests), 1)
        body = json.loads(requests[0].content)
        self.assertTrue(body["stream"])
        self.assertFalse(body["store"])
        self.assertEqual(body["max_output_tokens"], 120)
        self.assertEqual(body["model"], "gpt-4.1-mini")

    def test_disconnected_stream_does_not_mistake_partial_text_for_success(self):
        chunks = []
        with self.assertRaisesRegex(PetServiceError, "interrumpió"):
            self.invoke([{"type": "response.output_text.delta", "delta": "Solo un fragmento"}], chunks.append)
        self.assertEqual(chunks, ["Solo un fragmento"])

    def test_stream_errors_never_expose_server_details(self):
        for event in ({"type": "error", "message": "private"},
                      {"type": "response.failed", "response": self.response("failed")}):
            with self.assertRaises(PetServiceError) as caught:
                self.invoke([event], lambda text: None)
            self.assertNotIn("private", str(caught.exception))

    def test_incomplete_stream_keeps_the_cost_limit_notice(self):
        result, requests = self.invoke(
            [{"type": "response.incomplete", "response": self.response("incomplete")}], lambda text: None)
        self.assertIn("limitada para ahorrar", result)
        self.assertEqual(len(requests), 1)

    def test_shared_session_is_lazy_reused_for_voice_and_text_and_closed_once(self):
        session = ApiSession()
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(output_text="Respuesta.", status="completed")
        client.audio.transcriptions.create.return_value = SimpleNamespace(text="Pregunta")
        with patch("desktop_pet.service.openai.OpenAI", return_value=client) as factory, \
                patch("desktop_pet.service.config_value", return_value="test-only-not-a-key"), \
                patch("desktop_pet.voice.config_value", return_value="test-only-not-a-key"):
            factory.assert_not_called()
            self.assertEqual(transcribe_audio(b"fake", live=True, session=session), "Pregunta")
            self.assertEqual(answer_question("Pregunta", live=True, session=session), "Respuesta.")
            factory.assert_called_once()
            client.close.assert_not_called()
            session.close()
            session.close()
            client.close.assert_called_once()

    def test_key_change_replaces_connection_without_logging_credentials(self):
        session = ApiSession()
        first, second = MagicMock(), MagicMock()
        with patch("desktop_pet.service.openai.OpenAI", side_effect=[first, second]) as factory:
            self.assertIs(session.get("fake-a"), first)
            self.assertIs(session.get("fake-a"), first)
            self.assertIs(session.get("fake-b"), second)
        self.assertEqual(factory.call_count, 2)
        first.close.assert_called_once()
        session.close()
        second.close.assert_called_once()
