"""Start Anki (if needed) and wait for AnkiConnect. Used by the frozen exe."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

from anki_puppeteer.anki import AnkiClient, AnkiConnectError

log = logging.getLogger("anki_puppeteer")
Progress = Optional[Callable[[str], None]]


def _log(progress: Progress, message: str) -> None:
    if progress:
        progress(message)
    else:
        log.info(message)


def find_anki_exe() -> Optional[Path]:
    env = os.environ.get("ANKI_EXE")
    if env and Path(env).is_file():
        return Path(env)
    local = os.environ.get("LOCALAPPDATA", "")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    for candidate in (
        Path(local) / "Programs" / "Anki" / "anki.exe",
        Path(pf) / "Anki" / "anki.exe",
        Path(pf86) / "Anki" / "anki.exe",
    ):
        if candidate.is_file():
            return candidate
    which = shutil.which("anki") or shutil.which("anki.exe")
    if which:
        return Path(which)
    return None


def anki_running() -> bool:
    if os.name != "nt":
        return False
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq anki.exe", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "anki.exe" in (proc.stdout or "").lower()
    except Exception:
        return False


def start_anki(progress: Progress = None) -> Optional[Path]:
    if anki_running():
        _log(progress, "Anki is already open.")
        return find_anki_exe()
    exe = find_anki_exe()
    if exe is None:
        _log(progress, "Could not find Anki (anki.exe). Install Anki, then start a review.")
        return None
    _log(progress, f"Opening Anki ({exe})...")
    subprocess.Popen([str(exe)], cwd=str(exe.parent))
    return exe


def wait_for_ankiconnect(
    url: str = "http://127.0.0.1:8765",
    timeout: float = 45.0,
    api_key: Optional[str] = None,
    progress: Progress = None,
) -> bool:
    client = AnkiClient(url=url, api_key=api_key)
    deadline = time.monotonic() + timeout
    _log(progress, "Waiting for Anki to be ready...")
    while time.monotonic() < deadline:
        try:
            version = client.ping()
            _log(progress, f"Anki is ready (AnkiConnect {version}).")
            return True
        except AnkiConnectError:
            time.sleep(1.0)
        except Exception:
            time.sleep(1.0)
    _log(progress, "Anki is open, but AnkiConnect is not answering yet.")
    _log(progress, "Start a review in Anki, then continue.")
    return False
