"""Entry point: local demo by default, opt in to paid requests with --live."""

import argparse
import sys

from PyQt6.QtWidgets import QApplication

from desktop_pet.window import PetWindow


def main() -> int:
    parser = argparse.ArgumentParser(description="Mascota virtual de escritorio")
    parser.add_argument("--live", action="store_true", help="Usar la API de OpenAI (consume tokens)")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Mascota virtual")
    app.setOrganizationName("AsistenteVirtual")
    window = PetWindow(live=args.live)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
