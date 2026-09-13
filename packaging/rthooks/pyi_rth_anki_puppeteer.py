# Runtime hook: DLL search path for onnxruntime before any package import.
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

if getattr(sys, "frozen", False):
    meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    for extra in (meipass, meipass / "onnxruntime" / "capi", meipass / "numpy.libs"):
        if extra.is_dir():
            try:
                os.add_dll_directory(str(extra))
            except (OSError, AttributeError):
                os.environ["PATH"] = str(extra) + os.pathsep + os.environ.get("PATH", "")
