"""Save an OpenAI key from the Windows clipboard without printing it."""

import os
from pathlib import Path
import sys

from PyQt6.QtWidgets import QApplication


def main() -> int:
    app = QApplication.instance() or QApplication([])
    key = app.clipboard().text().strip()
    if not key.startswith("sk-") or len(key) < 40 or any(char.isspace() for char in key):
        print("El portapapeles no contiene una clave de OpenAI válida.")
        return 2
    target = Path(__file__).resolve().parent.parent / ".env.local"
    target.write_text(f"OPENAI_API_KEY={key}{os.linesep}", encoding="utf-8")
    print(f"Clave guardada como OPENAI_API_KEY en {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
