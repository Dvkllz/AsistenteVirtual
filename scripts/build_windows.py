"""Build a single-file Windows bundle with explicit assets and third-party notices."""
from importlib.metadata import distributions
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def stage_private_key():
    """Extract only the authorized API key; never copy an entire env file."""
    value = os.environ.get('OPENAI_API_KEY', '').strip()
    if not value:
        try:
            lines = (ROOT / '.env.local').read_text(encoding='utf-8-sig').splitlines()
        except (OSError, UnicodeError):
            lines = []
        for line in lines:
            name, separator, candidate = line.partition('=')
            if separator and name.strip() == 'OPENAI_API_KEY':
                value = candidate.strip().strip('"').strip("'")
                break
    if not value.startswith('sk-') or len(value) < 40 or any(c.isspace() for c in value):
        raise SystemExit('No usable existing API key; private build refused.')
    target = ROOT / 'build/private-input/openai.key'
    if target.is_symlink() or not target.resolve().is_relative_to(ROOT.resolve()):
        raise SystemExit('Unsafe private build destination.')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding='utf-8')
    return target


def build_environment():
    """Keep native dependency discovery independent of unrelated installed apps."""
    environment = os.environ.copy()
    windows = Path(os.environ['SystemRoot'])
    environment['PATH'] = os.pathsep.join(map(str, (
        Path(sys.executable).parent, Path(sys.base_prefix), Path(sys.base_prefix) / 'DLLs',
        windows / 'System32', windows)))
    for name in ('PYTHONHOME', 'PYTHONPATH', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH',
                 'QML2_IMPORT_PATH', 'QML_IMPORT_PATH', 'OPENAI_API_KEY', 'PET_PRIVATE_BUILD'):
        environment.pop(name, None)
    return environment


def main():
    parser = argparse.ArgumentParser(description='Build a public or explicitly private Windows executable.')
    parser.add_argument('--private', action='store_true', help='Include the existing API key; NEVER publish this package.')
    args = parser.parse_args()
    if sys.platform != 'win32' or struct.calcsize('P') != 8:
        raise SystemExit('Build on 64-bit Windows using 64-bit Python.')
    # Fail safely if somebody accidentally hardcodes a credential in app source.
    sources = [ROOT / 'main.py', ROOT / 'launcher.py', *sorted((ROOT / 'desktop_pet').glob('*.py'))]
    if any(re.search(rb'sk-(?:proj-)?[A-Za-z0-9_-]{35,}', source.read_bytes()) for source in sources):
        raise SystemExit('Potential embedded credential in application source; build refused.')
    notices = ROOT / 'build/portable-notices'
    notices.mkdir(parents=True, exist_ok=True)
    versions = {}
    for package in distributions():
        name = package.metadata['Name']
        versions[name] = package.version
        # Installed distributions are public dependencies, never user configuration.
        for entry in package.files or []:
            parts = Path(entry).parts
            if not parts or not parts[0].endswith('.dist-info'):
                continue
            if not any(word in str(entry).lower() for word in ('license', 'copying', 'notice')):
                continue
            source = Path(package.locate_file(entry))
            if source.is_file():
                destination = notices / name / Path(*parts[1:])
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.is_file():
        raise SystemExit('Python license was not found; cannot finish notices.')
    shutil.copy2(python_license, notices / 'Python-LICENSE.txt')
    shutil.copy2(ROOT / 'assets/fonts/OFL.txt', notices / 'PixelifySans-OFL.txt')
    version_file = notices / 'versions.json'
    version_text = json.dumps(versions, indent=2)
    if not version_file.exists() or version_file.read_text(encoding='utf-8') != version_text:
        version_file.write_text(version_text, encoding='utf-8')
    # Do not harvest native DLLs from unrelated apps on the developer's PATH.
    # In particular, Poppler's ICU DLL conflicts with Qt's Windows ICU imports.
    output = ROOT / ('dist/privado' if args.private else 'dist')
    executable = 'AsistenteVirtual-Privado.exe' if args.private else 'AsistenteVirtual.exe'
    environment = build_environment()
    environment['PET_PRIVATE_BUILD'] = '1' if args.private else '0'
    staged_key = stage_private_key() if args.private else None
    try:
        subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm',
                        '--workpath', str(ROOT / ('build/windows-private' if args.private else 'build/windows-x64')),
                        '--distpath', str(output), str(ROOT / 'AsistenteVirtual.spec')],
                       cwd=ROOT, env=environment, check=True)
    finally:
        if staged_key is not None:
            # Only remove the exact staging file created above. The original is untouched.
            staged_key.unlink(missing_ok=True)
    target = output / executable
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / 'SHA256.txt').write_text(f'{checksum}  {executable}\n', encoding='ascii')
    documents = ('LEEME-PRIVADO.txt',) if args.private else ('LEEME.txt', 'configuracion.ejemplo.txt')
    for name in documents:
        shutil.copy2(ROOT / 'packaging' / name, output / name)
    archive = output / ('AsistenteVirtual-PRIVADO-Windows-x64.zip' if args.private else 'AsistenteVirtual-Windows-x64.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name in (executable, *documents, 'SHA256.txt'):
            bundle.write(output / name, name)
        for notice in sorted(notices.rglob('*')):
            if notice.is_file():
                bundle.write(notice, 'licencias/' + notice.relative_to(notices).as_posix())
    print(f'EXE: {target} ({target.stat().st_size / 1024**2:.1f} MiB)')
    print(f'ZIP: {archive}')
    print(f'SHA256: {checksum}')


if __name__ == '__main__':
    main()
