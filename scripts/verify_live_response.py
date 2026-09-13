"""Explicit, one-request text smoke test; never records audio or retries."""
import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication
from desktop_pet.service import answer_question, PetServiceError
from desktop_pet.window import PetWindow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-one-request", action="store_true")
    args = parser.parse_args()
    if not args.confirm_one_request:
        parser.error("A live request costs credits; pass --confirm-one-request explicitly.")
    try:
        reply = answer_question("¿Qué opinas de mi productividad hoy?", live=True)
    except PetServiceError as error:
        print(str(error))
        return 1
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    with TemporaryDirectory() as folder:
        settings = QSettings(str(Path(folder) / "settings.ini"), QSettings.Format.IniFormat)
        for key in ("sound/effects", "sound/purr", "physics/enabled", "autonomy/enabled", "nap/enabled"):
            settings.setValue(key, False)
        window = PetWindow(live=True, settings=settings)
        window.show()
        window.show_response(reply)
        app.processEvents()
        target = Path(__file__).resolve().parent.parent / "artifacts/live-response-preview.png"
        target.parent.mkdir(exist_ok=True)
        saved = window.grab().save(str(target))
        print(json.dumps({"real_requests": 1, "reply": reply, "words": len(reply.split()),
                          "visible_seconds": window.talking_timer.interval() / 1000,
                          "preview_saved": saved}, ensure_ascii=False))
        window.close()
        window.deleteLater()
        app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
