"""Public builds start local; explicitly private builds are preconfigured for OpenAI."""

import argparse
import sys

from PyQt6.QtWidgets import QApplication

from desktop_pet.window import PetWindow
from desktop_pet.paths import embedded_api_key
from desktop_pet import __version__


def main() -> int:
    parser = argparse.ArgumentParser(description="Mascota virtual de escritorio")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--live", action="store_true", help="Usar la API de OpenAI (consume tokens)")
    modes.add_argument("--local", action="store_true", help="Empezar sin llamadas a la API")
    parser.add_argument("--self-test", metavar="INFORME", help=argparse.SUPPRESS)
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Mascota virtual")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("AsistenteVirtual")
    if args.self_test:
        from desktop_pet.portable_check import run
        return run(app, args.self_test)
    window = PetWindow(live=args.live or (not args.local and bool(embedded_api_key())))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
