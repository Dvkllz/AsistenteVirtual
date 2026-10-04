import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from launcher import launch


class LauncherTests(unittest.TestCase):
    def test_private_default_mode_and_explicit_local_override(self):
        from main import main
        for arguments, embedded, expected in (([], '', False), ([], 'private-value', True),
                                              (['--local'], 'private-value', False)):
            with self.subTest(arguments=arguments, expected=expected), \
                    patch('main.sys.argv', ['pet.exe', *arguments]), \
                    patch('main.embedded_api_key', return_value=embedded), \
                    patch('main.QApplication') as app, patch('main.PetWindow') as window:
                app.return_value.exec.return_value = 0
                self.assertEqual(main(), 0)
                window.assert_called_once_with(live=expected)

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
