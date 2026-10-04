import os
from pathlib import Path
import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.build_windows import build_environment, stage_private_key


class BuildEnvironmentTests(unittest.TestCase):
    def test_private_staging_copies_only_key_not_other_configuration(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            fake_key = 'sk-' + 'x' * 45
            (root / '.env.local').write_text('UNRELATED_SECRET=do-not-copy\nOPENAI_API_KEY=' + fake_key,
                                            encoding='utf-8')
            with patch.dict(os.environ, {}, clear=True), patch('scripts.build_windows.ROOT', root):
                staged = stage_private_key()
                self.assertEqual(staged.read_text(), fake_key)
                self.assertEqual(staged, root / 'build/private-input/openai.key')

    def test_private_staging_refuses_missing_key(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True), \
                patch('scripts.build_windows.ROOT', Path(folder)):
            with self.assertRaises(SystemExit):
                stage_private_key()
            self.assertFalse((Path(folder) / 'build').exists())

    def test_no_external_dll_paths_or_credentials_in_build_environment(self):
        with patch.dict(os.environ, {'SystemRoot': 'C:\\Windows', 'PATH': 'C:\\UnrelatedTool',
                                    'PYTHONPATH': 'C:\\UnrelatedTool', 'QT_PLUGIN_PATH': 'C:\\OtherQt',
                                    'OPENAI_API_KEY': 'private-marker'}, clear=True):
            result = build_environment()
            self.assertNotIn('UnrelatedTool', result['PATH'])
            self.assertIn(str(Path(sys.executable).parent), result['PATH'])
            self.assertIn(str(Path('C:/Windows/System32')), result['PATH'])
            for name in ('PYTHONPATH', 'QT_PLUGIN_PATH', 'OPENAI_API_KEY'):
                self.assertNotIn(name, result)
            # Only the child environment changes, never the user's environment.
            self.assertEqual(os.environ['OPENAI_API_KEY'], 'private-marker')
