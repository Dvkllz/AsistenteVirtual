from pathlib import Path
import unittest
from unittest.mock import patch

from desktop_pet.paths import local_config_path


class PortablePathTests(unittest.TestCase):
    def test_source_uses_project_configuration(self):
        with patch('desktop_pet.paths.sys.frozen', False, create=True):
            self.assertEqual(local_config_path(), Path(__file__).resolve().parent.parent / '.env.local')

    def test_executable_configuration_is_external_even_with_spaces(self):
        executable = Path('dist/Carpeta con espacios/AsistenteVirtual.exe').resolve()
        with patch('desktop_pet.paths.sys.frozen', True, create=True), \
                patch('desktop_pet.paths.sys.executable', str(executable)):
            self.assertEqual(local_config_path(), executable.parent / '.env.local')
