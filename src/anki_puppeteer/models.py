from __future__ import annotations

import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional

from anki_puppeteer.config import cache_dir
from anki_puppeteer import __version__

SILERO_URL = (
    "https://github.com/snakers4/silero-vad/raw/master/"
    "src/silero_vad/data/silero_vad.onnx"
)
VOSK_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
VOSK_DIRNAME = "vosk-model-small-en-us-0.15"
WHISPER_TINY_EN_URL = (
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin"
)
# Official tagged v1.9.4 has no Windows zip; nightly b5130 is the same commit.
WHISPER_BIN_TAG = "b5130"
WHISPER_BIN_URL = (
    "https://github.com/ggml-org/whisper.cpp/releases/download/"
    f"{WHISPER_BIN_TAG}/whisper-bin-x64.zip"
)

Progress = Optional[Callable[[str], None]]


def _log(progress: Progress, message: str) -> None:
    if progress:
        progress(message)


def _download(url: str, dest: Path, progress: Progress = None, timeout: int = 600) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    _log(progress, f"downloading {url}")
    req = urllib.request.Request(
        url, headers={"User-Agent": f"anki-puppeteer/{__version__}"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        read = 0
        last_pct = -1
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            out.write(chunk)
            read += len(chunk)
            if total and progress:
                pct = min(100, (100 * read) // total)
                if pct != last_pct and pct % 5 == 0:
                    mb = read / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    progress(f"  {pct}% ({mb:.1f}/{total_mb:.1f} MB)")
                    last_pct = pct
    tmp.replace(dest)
    _log(progress, f"saved {dest}")


def ensure_silero(path: Optional[Path] = None, progress: Progress = None) -> Path:
    dest = path or (cache_dir() / "silero_vad.onnx")
    if dest.is_file() and dest.stat().st_size > 1000:
        return dest
    _download(SILERO_URL, dest, progress)
    return dest


def _vosk_ready(dest: Path) -> bool:
    return (dest / "am" / "final.mdl").is_file() or (dest / "conf" / "model.conf").is_file()


def ensure_vosk(path: Optional[Path] = None, progress: Progress = None) -> Path:
    dest = path or (cache_dir() / VOSK_DIRNAME)
    if _vosk_ready(dest):
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    zip_path = dest.parent / f"{VOSK_DIRNAME}.zip"
    if not zip_path.is_file():
        _download(VOSK_URL, zip_path, progress)
    _log(progress, f"extracting {zip_path.name}")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest.parent)
    extracted = dest.parent / VOSK_DIRNAME
    if extracted.resolve() != dest.resolve() and extracted.is_dir():
        if dest.exists():
            shutil.rmtree(dest)
        extracted.rename(dest)
    if not _vosk_ready(dest):
        raise RuntimeError(f"Vosk model missing expected files in {dest}")
    return dest


def ensure_whisper_tiny_en(path: Optional[Path] = None, progress: Progress = None) -> Path:
    dest = path or (cache_dir() / "ggml-tiny.en.bin")
    if dest.is_file() and dest.stat().st_size > 20_000_000:
        return dest
    _download(WHISPER_TINY_EN_URL, dest, progress)
    return dest


def _whisper_cli_ready(cli: Path) -> bool:
    return cli.is_file() and cli.stat().st_size > 10_000


def ensure_whisper_cli(path: Optional[Path] = None, progress: Progress = None) -> Path:
    """Download whisper.cpp CPU Windows x64 tools into the cache if missing."""
    dest = path or (cache_dir() / "whisper" / "whisper-cli.exe")
    dest_dir = dest.parent
    if _whisper_cli_ready(dest):
        return dest
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / f"whisper-bin-x64-{WHISPER_BIN_TAG}.zip"
    if not zip_path.is_file() or zip_path.stat().st_size < 100_000:
        _download(WHISPER_BIN_URL, zip_path, progress)
    tmpdir = Path(tempfile.mkdtemp(prefix="anki-puppeteer-whisper-"))
    try:
        _log(progress, f"extracting {zip_path.name}")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmpdir)
        found = next(tmpdir.rglob("whisper-cli.exe"), None)
        if found is None:
            raise RuntimeError(
                f"whisper-cli.exe missing from {zip_path.name}. "
                f"Download {WHISPER_BIN_URL} and extract it to {dest_dir}"
            )
        src_dir = found.parent
        for item in src_dir.iterdir():
            target = dest_dir / item.name
            if item.is_file():
                shutil.copy2(item, target)
            elif item.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    if not dest.is_file():
        raise RuntimeError(f"whisper-cli.exe was not installed to {dest}")
    return dest


def is_ggml_model(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.stat().st_size < 1_000_000:
        return False
    name = path.name.lower()
    return name.endswith(".bin") or name.endswith(".gguf") or "ggml" in name


def extract_zip_to_temp(url: str, progress: Progress = None) -> Path:
    """Download a zip and extract it to a new temporary directory."""
    tmpdir = Path(tempfile.mkdtemp(prefix="anki-puppeteer-"))
    zip_path = tmpdir / "download.zip"
    _download(url, zip_path, progress)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tmpdir)
    zip_path.unlink(missing_ok=True)
    return tmpdir
