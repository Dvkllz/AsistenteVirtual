# Build on Windows x64: python scripts/build_windows.py
from pathlib import Path
import os
import sys
from PyInstaller.utils.hooks import copy_metadata

root = Path(SPECPATH)
datas = []
# Allowlist resources. Never collect the project root, configuration, or secrets.
patterns = ('assets/placeholder.png', 'assets/siamese/*.png',
            'assets/siamese/animation/*.png', 'assets/audio/*.mp3',
            'assets/fonts/*.ttf', 'assets/fonts/OFL.txt')
for pattern in patterns:
    for source in sorted(root.glob(pattern)):
        datas.append((str(source), str(source.relative_to(root).parent)))
datas += copy_metadata('openai', recursive=True)
datas.append((str(root / 'build/portable-notices'), 'licenses'))

a = Analysis([str(root / 'launcher.py')], pathex=[str(root)], binaries=[], datas=datas,
             hiddenimports=[], hookspath=[], runtime_hooks=[],
             excludes=['tkinter', 'pytest', 'pip', 'PyQt6.QtWebEngineCore'],
             noarchive=False)
for name, source, kind in a.datas:
    if Path(name).name.startswith('.env'):
        raise RuntimeError('Private configuration must never be bundled.')
allowed_binary_roots = [Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(),
                        Path(os.environ['SystemRoot']).resolve()]
for name, source, kind in a.binaries:
    if not any(Path(source).resolve().is_relative_to(folder) for folder in allowed_binary_roots):
        raise RuntimeError(f'Unexpected external binary in build: {name}')
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name='AsistenteVirtual', debug=False, bootloader_ignore_signals=False,
          strip=False, upx=False, console=False, disable_windowed_traceback=False,
          uac_admin=False)
