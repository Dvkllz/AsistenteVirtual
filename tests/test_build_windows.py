import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from scripts.build_windows import build_environment


class BuildEnvironmentTests(unittest.TestCase):
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
