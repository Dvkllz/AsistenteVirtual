import unittest

from desktop_pet.pets import DEFAULT_PET, PETS, get_pet


class PetProfileTests(unittest.TestCase):
    def test_default_remains_original_cat(self):
        self.assertEqual(get_pet().id, 'siamese')
        self.assertFalse(get_pet().friendly)

    def test_unknown_ids_cannot_select_external_assets(self):
        for value in ('removed', '../../private-config', None):
            self.assertEqual(get_pet(value).id, DEFAULT_PET)

    def test_golden_is_a_separate_friendly_profile(self):
        dog = get_pet('golden')
        self.assertTrue(dog.friendly)
        self.assertEqual(dog.species, 'perro')
        self.assertEqual(dog.directory.name, 'golden')
        self.assertEqual(len(PETS), 2)
