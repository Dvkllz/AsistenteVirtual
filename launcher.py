"""Executable entry point; preserve safe diagnostics for pre-UI smoke failures."""
import json
from pathlib import Path
import sys
import traceback


def launch():
    try:
        from main import main
        return main()
    except Exception as error:
        if '--self-test' not in sys.argv:
            raise
        index = sys.argv.index('--self-test')
        if index + 1 >= len(sys.argv):
            return 1
        report = Path(sys.argv[index + 1]).resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        diagnostic = {
            'ok': False, 'frozen': bool(getattr(sys, 'frozen', False)),
            'error_type': type(error).__name__,
            'missing_module': error.name if isinstance(error, ImportError) else None,
            'frames': [{'file': Path(frame.filename).name, 'line': frame.lineno,
                        'function': frame.name} for frame in traceback.extract_tb(error.__traceback__)],
        }
        report.write_text(json.dumps(diagnostic, indent=2), encoding='utf-8')
        return 1


if __name__ == '__main__':
    raise SystemExit(launch())
