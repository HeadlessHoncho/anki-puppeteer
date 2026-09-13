from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from anki_puppeteer import __version__
from anki_puppeteer.addon import install_ankiconnect
from anki_puppeteer.anki import AnkiClient, AnkiConnectError
from anki_puppeteer.audio import list_input_devices, test_mic
from anki_puppeteer.config import cache_dir, load_settings
from anki_puppeteer.launch import start_anki, wait_for_ankiconnect
from anki_puppeteer.loop import build_stt, run
from anki_puppeteer.models import ensure_silero, ensure_vosk
from anki_puppeteer.selftest import run_self_test, run_wav
from anki_puppeteer.setup import run_setup, setup_needed


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _set_console_title() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleTitleW("Anki Puppeteer")
    except Exception:
        pass


def _pause_on_error(code: int) -> int:
    if code == 0 or not _is_frozen():
        return code
    if not sys.stdin or not sys.stdin.isatty():
        return code
    try:
        input("Press Enter to close")
    except EOFError:
        pass
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="anki-puppeteer" if not _is_frozen() else "AnkiPuppeteer",
        description=(
            "Review Anki cards by voice while another app is focused. "
            "Local VAD + short-burst gate + whisper.cpp + exact whitelist + AnkiConnect."
        ),
    )
    parser.add_argument("--config", "-c", type=Path, help="TOML config file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Recognize commands but do not call Anki",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Input device index or name substring (see --list-devices)",
    )
    parser.add_argument(
        "--test-mic",
        action="store_true",
        help="Live level meter so you can see if talking moves the bar",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Ping AnkiConnect and exit",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List microphone devices and exit",
    )
    parser.add_argument(
        "--download-models",
        action="store_true",
        help="Download Silero VAD and Vosk models, then exit",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Detect or install whisper.cpp, Silero VAD, a speech model, and AnkiConnect",
    )
    parser.add_argument(
        "--model",
        type=Path,
        help="Existing local ggml-*.bin to use instead of downloading tiny.en",
    )
    parser.add_argument(
        "--no-anki",
        action="store_true",
        help="Do not start Anki (frozen exe normally opens Anki first)",
    )
    parser.add_argument(
        "--install-ankiconnect",
        action="store_true",
        help="Install the AnkiConnect add-on into Anki's add-ons folder",
    )
    parser.add_argument(
        "--wav",
        type=Path,
        help="Feed a WAV through the same gate/STT/whitelist (no microphone)",
    )
    parser.add_argument(
        "--expect",
        help="With --wav, the command name that should match (show/again/hard/good/easy/undo)",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Synthesize the six commands with Windows TTS and run them through the pipeline",
    )
    parser.add_argument(
        "--stt",
        choices=("auto", "large", "tiny", "vosk"),
        default="auto",
        help="Speech engine. self-test defaults to tiny unless you pass --stt",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Debug logging",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    _set_console_title()

    fmt = logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    log_path = cache_dir() / "listen.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    log = logging.getLogger("anki_puppeteer")

    if args.list_devices:
        print(list_input_devices())
        return 0

    if args.test_mic:
        spec = args.device
        if spec is not None and str(spec).isdigit():
            spec = int(spec)
        return test_mic(spec)

    if args.setup:
        return run_setup(model=args.model, progress=log.info)

    settings = load_settings(args.config)
    if args.dry_run:
        settings.dry_run = True
    if args.device is not None:
        settings.input_device = int(args.device) if str(args.device).isdigit() else args.device
    if args.model is not None:
        settings.whisper_model = args.model

    if args.self_test:
        kind = "tiny" if args.stt == "auto" else args.stt
        return run_self_test(settings, stt_kind=kind)

    if args.wav:
        stt = build_stt(args.stt, settings)
        rec = run_wav(args.wav, settings, stt, expect=args.expect)
        return 0 if rec["ok"] else 1

    if args.download_models:
        ensure_silero(settings.silero_path, progress=log.info)
        ensure_vosk(settings.vosk_path, progress=log.info)
        log.info("models ready")
        return 0

    if args.install_ankiconnect:
        dest = install_ankiconnect(progress=log.info)
        log.info("installed AnkiConnect at %s", dest)
        log.info("Restart Anki if it is already running.")
        return 0

    if args.check:
        client = AnkiClient(url=settings.anki_url, api_key=settings.anki_key)
        try:
            version = client.ping()
        except AnkiConnectError as exc:
            log.error("%s", exc)
            return 2
        log.info("AnkiConnect ok (version %s)", version)
        return 0

    interactive_start = _is_frozen() and argv is None and len(sys.argv) <= 1
    if setup_needed(settings):
        log.info("Speech tools are missing; running first-run setup")
        code = run_setup(model=args.model, progress=log.info)
        if code != 0:
            return _pause_on_error(code)
        settings = load_settings(args.config)
        if args.dry_run:
            settings.dry_run = True
        if args.device is not None:
            settings.input_device = (
                int(args.device) if str(args.device).isdigit() else args.device
            )
        if args.model is not None:
            settings.whisper_model = args.model

    if _is_frozen() and not args.no_anki and not args.dry_run:
        start_anki(progress=log.info)
        ready = wait_for_ankiconnect(
            url=settings.anki_url,
            api_key=settings.anki_key,
            progress=log.info,
        )
        if not ready and interactive_start:
            try:
                input("Start a review in Anki, then press Enter here.")
            except EOFError:
                pass
        log.info("Voice control is on. Say: show, again, hard, good, easy, undo.")
        log.info("Close this window to stop.")

    stt_kind = args.stt
    if _is_frozen() and stt_kind == "auto":
        stt_kind = "tiny"
    return _pause_on_error(run(settings, stt_kind=stt_kind))


if __name__ == "__main__":
    sys.exit(main())
