"""Writable configuration lives beside the executable, never in its extraction folder."""
from pathlib import Path
import sys


def local_config_path() -> Path:
    root = (Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False)
            else Path(__file__).resolve().parent.parent)
    return root / '.env.local'


def embedded_api_key() -> str:
    """Opt-in private builds only. This is extractable, not encryption."""
    if not getattr(sys, 'frozen', False):
        return ''
    path = Path(__file__).resolve().parent.parent / 'private-config/openai.key'
    try:
        return path.read_text(encoding='utf-8').strip()
    except (OSError, UnicodeError):
        return ''
