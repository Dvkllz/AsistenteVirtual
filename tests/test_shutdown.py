"""Exercise the real Qt event loop in a separate process, without network."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


class ShutdownTests(unittest.TestCase):
    def test_close_during_answer_exits_process(self):
        source = '''
import time
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from desktop_pet.window import PetWindow
app = QApplication([])
window = PetWindow(responder=lambda q: (time.sleep(0.2), "Listo")[1])
window.show()
window.input.setText("Hola")
window.submit()
QTimer.singleShot(10, window.close)
QTimer.singleShot(3000, lambda: app.exit(9))
raise SystemExit(app.exec())
'''
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
        result = subprocess.run([sys.executable, '-c', source],
                                cwd=Path(__file__).resolve().parent.parent,
                                env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
