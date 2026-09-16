import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from launcher import launch


class LauncherTests(unittest.TestCase):
    def test_failed_import_report_does_not_include_exception_contents(self):
        with TemporaryDirectory() as folder:
            target = Path(folder) / 'report.json'
            with patch('launcher.sys.argv', ['pet.exe', '--self-test', str(target)]), \
                    patch('main.main', side_effect=ModuleNotFoundError('private-data', name='missing_dependency')):
                self.assertEqual(launch(), 1)
            text = target.read_text(encoding='utf-8')
            self.assertNotIn('private-data', text)
            self.assertEqual(json.loads(text)['missing_module'], 'missing_dependency')

    def test_normal_startup_failure_is_not_silently_swallowed(self):
        with patch('launcher.sys.argv', ['pet.exe']), \
                patch('main.main', side_effect=RuntimeError('Failed startup')):
            with self.assertRaises(RuntimeError):
                launch()
