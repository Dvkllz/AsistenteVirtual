"""Render the chat style offline; no requests, microphone or desktop capture."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from desktop_pet.window import PetWindow


app = QApplication([])
app.setQuitOnLastWindowClosed(False)
with TemporaryDirectory() as folder:
    settings = QSettings(str(Path(folder) / 'preview.ini'), QSettings.Format.IniFormat)
    for key in ('sound/purr', 'sound/effects', 'physics/enabled', 'autonomy/enabled', 'nap/enabled'):
        settings.setValue(key, False)
    window = PetWindow(settings=settings)
    window.show()
    window.show_response('He revisado tu horario: faltan caricias. Prioridades, por favor.')
    window.input.setText('¿Otra siesta?')
    window.input.setCursorPosition(len(window.input.text()))
    window._composer_focus(True)
    app.processEvents()
    target = Path(__file__).resolve().parent.parent / 'artifacts/chat-pixel-preview.png'
    target.parent.mkdir(parents=True, exist_ok=True)
    window.grab().save(str(target))
    print(target)
    window.close()
    window.deleteLater()
    app.processEvents()
