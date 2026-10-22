import os
import unittest
from unittest.mock import patch

from desktop_pet.service import DOG_PROMPT, SYSTEM_PROMPT, answer_question, system_prompt


class PetDialogueTests(unittest.TestCase):
    def test_passive_lines_are_species_specific_local_and_unique(self):
        from desktop_pet.autonomy import passive_lines, QUIPS, DOG_QUIPS
        self.assertEqual(passive_lines('siamese'), QUIPS)
        self.assertEqual(passive_lines('golden'), DOG_QUIPS)
        self.assertGreaterEqual(len(DOG_QUIPS), 20)
        self.assertEqual(len(DOG_QUIPS), len(set(DOG_QUIPS)))
        self.assertFalse(set(DOG_QUIPS) & set(QUIPS))
        self.assertNotIn('atún', ' '.join(DOG_QUIPS))

    def test_personalities_are_separate_and_unknown_ids_fall_back(self):
        self.assertEqual(system_prompt('siamese'), SYSTEM_PROMPT)
        self.assertEqual(system_prompt('unknown'), SYSTEM_PROMPT)
        self.assertEqual(system_prompt('golden'), DOG_PROMPT)
        self.assertIn('sin sarcasmo', DOG_PROMPT)
        self.assertNotIn('pereza felina', DOG_PROMPT)

    def test_both_local_answers_never_create_client(self):
        with patch('desktop_pet.service.openai.OpenAI') as client:
            cat = answer_question('Hola', pet_id='siamese')
            dog = answer_question('Hola', pet_id='golden')
            self.assertNotEqual(cat, dog)
            self.assertIn('te acompaño', dog)
            client.assert_not_called()

    def test_each_request_sends_selected_personality_without_changing_limits(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'offline-test-only'}), \
                patch('desktop_pet.service.openai.OpenAI') as factory:
            client = factory.return_value.__enter__.return_value
            client.responses.create.return_value.output_text = 'Vamos juntos.'
            client.responses.create.return_value.status = 'completed'
            for pet, prompt in [('golden', DOG_PROMPT), ('siamese', SYSTEM_PROMPT)]:
                self.assertEqual(answer_question('Hola', live=True, pet_id=pet), 'Vamos juntos.')
                arguments = client.responses.create.call_args.kwargs
                self.assertEqual(arguments['instructions'], prompt)
                self.assertEqual(arguments['max_output_tokens'], 120)
                self.assertFalse(arguments['store'])
