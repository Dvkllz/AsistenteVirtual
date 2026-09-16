"""Writable configuration lives beside the executable, never in its extraction folder."""
from pathlib import Path
import sys


def local_config_path() -> Path:
    root = (Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False)
            else Path(__file__).resolve().parent.parent)
    return root / '.env.local'
