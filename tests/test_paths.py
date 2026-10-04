from pathlib import Path
import unittest
from unittest.mock import patch

from desktop_pet.paths import embedded_api_key, local_config_path


class PortablePathTests(unittest.TestCase):
    def test_source_never_reads_embedded_credentials(self):
        with patch('desktop_pet.paths.sys.frozen', False, create=True), \
                patch('desktop_pet.paths.Path.read_text') as read:
            self.assertEqual(embedded_api_key(), '')
            read.assert_not_called()

    def test_private_bundle_key_is_read_only_in_frozen_mode(self):
        with patch('desktop_pet.paths.sys.frozen', True, create=True), \
                patch('desktop_pet.paths.Path.read_text', return_value='private-test-value\n'):
            self.assertEqual(embedded_api_key(), 'private-test-value')

    def test_public_bundle_has_no_embedded_key(self):
        with patch('desktop_pet.paths.sys.frozen', True, create=True), \
                patch('desktop_pet.paths.Path.read_text', side_effect=FileNotFoundError):
            self.assertEqual(embedded_api_key(), '')

    def test_source_uses_project_configuration(self):
        with patch('desktop_pet.paths.sys.frozen', False, create=True):
            self.assertEqual(local_config_path(), Path(__file__).resolve().parent.parent / '.env.local')

    def test_executable_configuration_is_external_even_with_spaces(self):
        executable = Path('dist/Carpeta con espacios/AsistenteVirtual.exe').resolve()
        with patch('desktop_pet.paths.sys.frozen', True, create=True), \
                patch('desktop_pet.paths.sys.executable', str(executable)):
            self.assertEqual(local_config_path(), executable.parent / '.env.local')
