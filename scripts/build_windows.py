"""Build a single-file Windows bundle with explicit assets and third-party notices."""
from importlib.metadata import distributions
from pathlib import Path
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


def build_environment():
    """Keep native dependency discovery independent of unrelated installed apps."""
    environment = os.environ.copy()
    windows = Path(os.environ['SystemRoot'])
    environment['PATH'] = os.pathsep.join(map(str, (
        Path(sys.executable).parent, Path(sys.base_prefix), Path(sys.base_prefix) / 'DLLs',
        windows / 'System32', windows)))
    for name in ('PYTHONHOME', 'PYTHONPATH', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH',
                 'QML2_IMPORT_PATH', 'QML_IMPORT_PATH', 'OPENAI_API_KEY'):
        environment.pop(name, None)
    return environment


def main():
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
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm',
                    '--workpath', str(ROOT / 'build/windows-x64'),
                    str(ROOT / 'AsistenteVirtual.spec')], cwd=ROOT, env=build_environment(), check=True)
    target = ROOT / 'dist/AsistenteVirtual.exe'
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    (ROOT / 'dist/SHA256.txt').write_text(f'{checksum}  AsistenteVirtual.exe\n', encoding='ascii')
    for name in ('LEEME.txt', 'configuracion.ejemplo.txt'):
        shutil.copy2(ROOT / 'packaging' / name, ROOT / 'dist' / name)
    archive = ROOT / 'dist/AsistenteVirtual-Windows-x64.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name in ('AsistenteVirtual.exe', 'LEEME.txt', 'configuracion.ejemplo.txt', 'SHA256.txt'):
            bundle.write(ROOT / 'dist' / name, name)
        for notice in sorted(notices.rglob('*')):
            if notice.is_file():
                bundle.write(notice, 'licencias/' + notice.relative_to(notices).as_posix())
    print(f'EXE: {target} ({target.stat().st_size / 1024**2:.1f} MiB)')
    print(f'ZIP: {archive}')
    print(f'SHA256: {checksum}')


if __name__ == '__main__':
    main()
