import json
import os
import unittest
from unittest.mock import patch

import httpx
import openai

from desktop_pet.service import (
    DEFAULT_MODEL, MAX_OUTPUT_TOKENS, PetServiceError, answer_question,
)


class ServiceTests(unittest.TestCase):
    def test_demo_never_constructs_api_client(self):
        with patch('desktop_pet.service.openai.OpenAI') as client:
            self.assertIn('prueba', answer_question('Hola'))
            client.assert_not_called()

    def test_blank_or_oversized_question_does_not_call_api(self):
        with patch('desktop_pet.service.openai.OpenAI') as client:
            for question in ('  ', 'a' * 801):
                with self.assertRaises(PetServiceError):
                    answer_question(question, live=True)
            client.assert_not_called()

    def test_missing_key_does_not_call_api(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}), patch('desktop_pet.service.openai.OpenAI') as client:
            with self.assertRaisesRegex(PetServiceError, 'Falta OPENAI_API_KEY'):
                answer_question('Hola', live=True)
            client.assert_not_called()

    def test_real_sdk_with_fake_transport_and_spending_limits(self):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={
                'id': 'resp_test', 'object': 'response', 'created_at': 1,
                'model': DEFAULT_MODEL, 'status': 'completed',
                'output': [{'type': 'message', 'id': 'msg_test', 'role': 'assistant',
                            'status': 'completed', 'content': [
                                {'type': 'output_text', 'text': 'Hola, humano.', 'annotations': []}
                            ]}],
            })

        sdk_client = openai.OpenAI(api_key='test-only-not-a-key', max_retries=0,
                                  http_client=httpx.Client(transport=httpx.MockTransport(respond)))
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only-not-a-key', 'OPENAI_MODEL': ''}), \
                patch('desktop_pet.service.openai.OpenAI', return_value=sdk_client) as factory:
            self.assertEqual(answer_question(' Hola ', live=True), 'Hola, humano.')
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url.path, '/v1/responses')
        payload = json.loads(requests[0].content)
        self.assertEqual(payload['input'], 'Hola')
        self.assertEqual(payload['model'], DEFAULT_MODEL)
        self.assertEqual(payload['max_output_tokens'], MAX_OUTPUT_TOKENS)
        self.assertFalse(payload['store'])
        self.assertIn('sarcástico', payload['instructions'])
        self.assertEqual(factory.call_args.kwargs['max_retries'], 0)
        self.assertEqual(factory.call_args.kwargs['timeout'], 20)

    def test_safe_api_errors(self):
        request = httpx.Request('POST', 'https://api.openai.com/v1/responses')
        cases = [
            (openai.AuthenticationError('private-details', response=httpx.Response(401, request=request), body=None), 'clave'),
            (openai.RateLimitError('private-details', response=httpx.Response(429, request=request), body=None), 'límite'),
            (openai.APITimeoutError(request=request), 'tardó'),
            (openai.APIConnectionError(request=request), 'conectar'),
        ]
        for error, message in cases:
            with self.subTest(error=type(error).__name__), \
                    patch.dict(os.environ, {'OPENAI_API_KEY': 'test-only-not-a-key'}), \
                    patch('desktop_pet.service.openai.OpenAI', side_effect=error):
                with self.assertRaisesRegex(PetServiceError, message) as caught:
                    answer_question('Hola', live=True)
                self.assertNotIn('private-details', str(caught.exception))
