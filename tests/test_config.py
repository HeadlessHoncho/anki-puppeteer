from pathlib import Path

from anki_puppeteer.config import Settings, load_settings, write_settings


def test_toml_overrides(tmp_path: Path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        """
[gate]
max_burst_seconds = 2.5

[anki]
url = "http://127.0.0.1:9999"

[commands]
show = ["show", "show answer"]
""",
        encoding="utf-8",
    )
    settings = load_settings(cfg)
    assert settings.max_burst_seconds == 2.5
    assert settings.anki_url == "http://127.0.0.1:9999"
    assert "show answer" in settings.phrases["show"]
    assert settings.phrases["good"] == ("good",)


def test_stt_toml(tmp_path: Path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        """
[stt]
cli = "C:/tools/whisper/whisper-cli.exe"
model = "D:/models/ggml-tiny.en.bin"

[models]
silero = "C:/cache/silero_vad.onnx"
""",
        encoding="utf-8",
    )
    settings = load_settings(cfg)
    assert settings.whisper_cli == Path("C:/tools/whisper/whisper-cli.exe")
    assert settings.whisper_model == Path("D:/models/ggml-tiny.en.bin")
    assert settings.silero_path == Path("C:/cache/silero_vad.onnx")


def test_write_settings_roundtrip(tmp_path: Path):
    settings = Settings()
    settings.whisper_cli = tmp_path / "whisper" / "whisper-cli.exe"
    settings.whisper_model = tmp_path / "ggml-tiny.en.bin"
    settings.silero_path = tmp_path / "silero_vad.onnx"
    settings.vad_threshold = 0.4
    dest = tmp_path / "config.toml"
    write_settings(settings, dest)
    loaded = load_settings(dest)
    assert loaded.whisper_cli == settings.whisper_cli
    assert loaded.whisper_model == settings.whisper_model
    assert loaded.silero_path == settings.silero_path
    assert loaded.max_burst_seconds == 1.8
    assert loaded.phrases["undo"] == ("undo",)
