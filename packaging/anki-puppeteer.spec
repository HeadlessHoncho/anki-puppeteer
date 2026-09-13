# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

spec_dir = Path(SPECPATH)
root = spec_dir.parent
src = root / "src"
icon = root / "assets" / "anki-puppeteer.ico"

datas = []
binaries = []
hiddenimports = collect_submodules("anki_puppeteer")
excludes = [
    "vosk",
    "pytest",
    "tkinter",
    "_tkinter",
    "matplotlib",
    "PIL",
    "numpy.tests",
    "numpy.conftest",
    "onnxruntime.quantization",
    "onnxruntime.transformers",
    "onnxruntime.datasets",
    "onnxruntime.tools",
]

if icon.is_file():
    datas.append((str(icon), "assets"))

# Duplicate onnxruntime DLLs at MEIPASS root so the Windows loader finds them.
try:
    import onnxruntime as _ort

    _capi = Path(_ort.__file__).resolve().parent / "capi"
    for _name in ("onnxruntime.dll", "onnxruntime_providers_shared.dll"):
        _src = _capi / _name
        if _src.is_file():
            binaries.append((str(_src), "."))
except Exception:
    pass

a = Analysis(
    [str(src / "anki_puppeteer" / "__main__.py")],
    pathex=[str(src)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(spec_dir / "rthooks" / "pyi_rth_anki_puppeteer.py")],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)


def _keep_binary(item) -> bool:
    name = Path(item[0]).name.lower()
    if name.startswith("api-ms-win-"):
        return False
    if name in {"ucrtbase.dll", "msvcp140.dll", "msvcp140_1.dll"}:
        return False
    return True


a.binaries = [item for item in a.binaries if _keep_binary(item)]

# App-local MSVC C++ CRT new enough for onnxruntime 1.29 (the copies
# PyInstaller finds first are often 14.27 and DllMain fails).
_sys32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
for _crt in ("msvcp140.dll", "msvcp140_1.dll"):
    _src = _sys32 / _crt
    if _src.is_file():
        a.binaries.append((_crt, str(_src), "BINARY"))

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AnkiPuppeteer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon) if icon.is_file() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AnkiPuppeteer",
)
