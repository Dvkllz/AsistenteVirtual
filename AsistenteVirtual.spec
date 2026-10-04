# Build on Windows x64: python scripts/build_windows.py
from pathlib import Path
import os
import sys
from PyInstaller.utils.hooks import copy_metadata

root = Path(SPECPATH)
private_build = os.environ.get('PET_PRIVATE_BUILD') == '1'
datas = []
# Public resource allowlist; only --private explicitly permits a staged key.
patterns = ('assets/placeholder.png', 'assets/siamese/*.png',
            'assets/siamese/animation/*.png', 'assets/audio/*.mp3',
            'assets/fonts/*.ttf', 'assets/fonts/OFL.txt')
for pattern in patterns:
    for source in sorted(root.glob(pattern)):
        datas.append((str(source), str(source.relative_to(root).parent)))
datas += copy_metadata('openai', recursive=True)
datas.append((str(root / 'desktop_pet/windows_focus.ps1'), 'desktop_pet'))
datas.append((str(root / 'build/portable-notices'), 'licenses'))
if private_build:
    private_key = root / 'build/private-input/openai.key'
    if private_key.is_symlink() or not private_key.is_file():
        raise RuntimeError('Missing authorized private build input.')
    datas.append((str(private_key), 'private-config'))

a = Analysis([str(root / 'launcher.py')], pathex=[str(root)], binaries=[], datas=datas,
             hiddenimports=[], hookspath=[], runtime_hooks=[],
             excludes=['tkinter', 'pytest', 'pip', 'PyQt6.QtWebEngineCore'],
             noarchive=False)
for name, source, kind in a.datas:
    if Path(name).name.startswith('.env'):
        raise RuntimeError('Private configuration must never be bundled.')
    if Path(name).name == 'openai.key' and not private_build:
        raise RuntimeError('Private key found in a public build.')
allowed_binary_roots = [Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(),
                        Path(os.environ['SystemRoot']).resolve()]
for name, source, kind in a.binaries:
    if not any(Path(source).resolve().is_relative_to(folder) for folder in allowed_binary_roots):
        raise RuntimeError(f'Unexpected external binary in build: {name}')
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name='AsistenteVirtual-Privado' if private_build else 'AsistenteVirtual',
          debug=False, bootloader_ignore_signals=False,
          strip=False, upx=False, console=False, disable_windowed_traceback=False,
          uac_admin=False)
