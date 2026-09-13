from pathlib import Path

from anki_puppeteer.config import load_settings
from anki_puppeteer.models import is_ggml_model
from anki_puppeteer.setup import run_setup, setup_needed
from anki_puppeteer.stt import find_whisper_cli, find_whisper_model


def test_is_ggml_model(tmp_path: Path):
    good = tmp_path / "ggml-tiny.en.bin"
    good.write_bytes(b"x" * 2_000_000)
    assert is_ggml_model(good)
    bad = tmp_path / "notes.txt"
    bad.write_text("nope", encoding="utf-8")
    assert not is_ggml_model(bad)
    missing = tmp_path / "missing.bin"
    assert not is_ggml_model(missing)


def test_find_whisper_cli_cache(tmp_path: Path, monkeypatch):
    exe = tmp_path / "whisper" / "whisper-cli.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"MZ" + b"\0" * 20_000)
    monkeypatch.delenv("WHISPER_CLI", raising=False)
    monkeypatch.setattr("anki_puppeteer.stt.shutil.which", lambda _name: None)
    monkeypatch.setattr("anki_puppeteer.stt.cache_dir", lambda: tmp_path)
    monkeypatch.setattr("anki_puppeteer.stt.Path.home", lambda: tmp_path / "no-home")
    found = find_whisper_cli()
    assert found == exe


def test_find_whisper_model_cache(tmp_path: Path, monkeypatch):
    model = tmp_path / "ggml-tiny.en.bin"
    model.write_bytes(b"x" * 2_000_000)
    monkeypatch.delenv("WHISPER_MODEL", raising=False)
    monkeypatch.setattr("anki_puppeteer.stt.cache_dir", lambda: tmp_path)
    monkeypatch.setattr("anki_puppeteer.stt.Path.home", lambda: tmp_path / "no-home")
    assert find_whisper_model() == model


def test_run_setup_uses_existing_model(tmp_path: Path, monkeypatch):
    cli = tmp_path / "whisper-cli.exe"
    cli.write_bytes(b"MZ" + b"\0" * 20_000)
    model = tmp_path / "ggml-base.en.bin"
    model.write_bytes(b"x" * 2_000_000)
    silero = tmp_path / "silero_vad.onnx"
    silero.write_bytes(b"x" * 2000)
    monkeypatch.setattr("anki_puppeteer.setup.find_whisper_cli", lambda: cli)
    monkeypatch.setattr("anki_puppeteer.setup.find_whisper_model", lambda: None)
    monkeypatch.setattr(
        "anki_puppeteer.setup.ensure_silero",
        lambda path=None, progress=None: silero,
    )
    monkeypatch.setattr(
        "anki_puppeteer.setup.install_ankiconnect",
        lambda progress=None: tmp_path / "addon",
    )
    cfg = tmp_path / "config.toml"
    assert run_setup(model=model, config_path=cfg) == 0
    loaded = load_settings(cfg)
    assert loaded.whisper_cli == cli
    assert loaded.whisper_model == model
    assert loaded.silero_path == silero
    assert not setup_needed(loaded)


def test_run_setup_rejects_bad_model(tmp_path: Path, monkeypatch):
    cli = tmp_path / "whisper-cli.exe"
    cli.write_bytes(b"MZ" + b"\0" * 20_000)
    silero = tmp_path / "silero_vad.onnx"
    silero.write_bytes(b"x" * 2000)
    monkeypatch.setattr("anki_puppeteer.setup.find_whisper_cli", lambda: cli)
    monkeypatch.setattr(
        "anki_puppeteer.setup.ensure_silero",
        lambda path=None, progress=None: silero,
    )
    bad = tmp_path / "readme.txt"
    bad.write_text("hi", encoding="utf-8")
    assert run_setup(model=bad, config_path=tmp_path / "config.toml") == 1
