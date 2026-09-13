"""First-run / installer bootstrap: whisper.cpp, Silero VAD, optional model, AnkiConnect."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from anki_puppeteer.addon import install_ankiconnect
from anki_puppeteer.config import (
    Settings,
    load_settings,
    user_config_path,
    write_settings,
)
from anki_puppeteer.models import (
    ensure_silero,
    ensure_whisper_cli,
    ensure_whisper_tiny_en,
    is_ggml_model,
)
from anki_puppeteer.stt import find_whisper_cli, find_whisper_model

log = logging.getLogger("anki_puppeteer")
Progress = Optional[Callable[[str], None]]


def _log(progress: Progress, message: str) -> None:
    if progress:
        progress(message)
    else:
        log.info(message)


def setup_needed(settings: Optional[Settings] = None) -> bool:
    settings = settings or load_settings()
    cli = _resolve_cli(settings)
    model = _resolve_model(settings)
    silero = settings.silero_path
    if silero is None or not Path(silero).is_file():
        from anki_puppeteer.config import cache_dir

        silero = cache_dir() / "silero_vad.onnx"
    return not (
        cli is not None
        and cli.is_file()
        and model is not None
        and model.is_file()
        and Path(silero).is_file()
    )


def _resolve_cli(settings: Settings) -> Optional[Path]:
    if settings.whisper_cli and Path(settings.whisper_cli).is_file():
        return Path(settings.whisper_cli)
    return find_whisper_cli()


def _resolve_model(settings: Settings) -> Optional[Path]:
    if settings.whisper_model and Path(settings.whisper_model).is_file():
        return Path(settings.whisper_model)
    return find_whisper_model()


def run_setup(
    model: Optional[Path] = None,
    install_addon: bool = True,
    progress: Progress = None,
    config_path: Optional[Path] = None,
) -> int:
    """Detect local tools, download anything missing, write config.

    If ``model`` is a ggml-*.bin path, that file is used and tiny.en is not
    downloaded. Speech models are never bundled with the installer.
    """
    dest_cfg = config_path or user_config_path()
    if dest_cfg.is_file():
        settings = load_settings(dest_cfg)
    elif config_path is None:
        settings = load_settings()
    else:
        settings = Settings()

    _log(progress, "Checking speech tools...")
    cli = _resolve_cli(settings)
    if cli is None:
        _log(progress, "whisper-cli not found; downloading whisper.cpp CPU tools (~8 MB)")
        cli = ensure_whisper_cli(progress=progress)
    else:
        _log(progress, f"whisper-cli: {cli}")
    settings.whisper_cli = cli

    _log(progress, "Checking Silero VAD...")
    silero = ensure_silero(settings.silero_path, progress=progress)
    settings.silero_path = silero
    _log(progress, f"Silero VAD: {silero}")

    chosen: Optional[Path] = None
    if model is not None:
        chosen = Path(model)
        if not is_ggml_model(chosen):
            _log(
                progress,
                f"Not a usable Whisper model: {chosen}. Need an existing ggml-*.bin file.",
            )
            return 1
        _log(progress, f"Using existing speech model: {chosen}")
    else:
        chosen = _resolve_model(settings)
        if chosen is not None:
            _log(progress, f"Using existing speech model: {chosen}")
        else:
            _log(progress, "Downloading ggml-tiny.en.bin (~75 MB). This is local STT, not cloud.")
            chosen = ensure_whisper_tiny_en(progress=progress)
    settings.whisper_model = chosen

    written = write_settings(settings, dest_cfg)
    _log(progress, f"Wrote {written}")

    if install_addon:
        try:
            dest = install_ankiconnect(progress=progress)
            _log(progress, f"AnkiConnect add-on: {dest}")
            _log(progress, "Restart Anki if it is already running.")
        except Exception as exc:
            _log(progress, f"AnkiConnect install skipped: {exc}")
            _log(progress, "Install add-on 2055492159 in Anki, or re-run with --install-ankiconnect.")

    _log(progress, "Setup complete.")
    return 0
