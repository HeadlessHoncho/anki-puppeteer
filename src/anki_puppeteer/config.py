from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from anki_puppeteer.commands import DEFAULT_PHRASES
from anki_puppeteer.gate import GateConfig

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


_APP_DIR = "anki-puppeteer"
_LEGACY_DIR = "anki-voice-review"


def _windows_local_appdata() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))


def user_config_path() -> Path:
    """Always the per-user config, even if a local config.toml exists in cwd."""
    if os.name == "nt":
        return _windows_local_appdata() / _APP_DIR / "config.toml"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / _APP_DIR / "config.toml"


def default_config_path() -> Path:
    local = Path("config.toml")
    if local.is_file():
        return local
    if os.name == "nt":
        base = _windows_local_appdata()
        new = base / _APP_DIR / "config.toml"
        old = base / _LEGACY_DIR / "config.toml"
        if old.is_file() and not new.is_file():
            return old
        return new
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    new = base / _APP_DIR / "config.toml"
    old = base / _LEGACY_DIR / "config.toml"
    if old.is_file() and not new.is_file():
        return old
    return new


def cache_dir() -> Path:
    if os.name == "nt":
        base = _windows_local_appdata()
    else:
        xdg = os.environ.get("XDG_CACHE_HOME")
        base = Path(xdg) if xdg else Path.home() / ".cache"
    new = base / _APP_DIR
    old = base / _LEGACY_DIR
    if old.is_dir() and not new.exists():
        return old
    return new


def anki_addons_dir() -> Path:
    if os.name == "nt":
        appdata = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        return appdata / "Anki2" / "addons21"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Anki2" / "addons21"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "Anki2" / "addons21"
    return Path.home() / ".local" / "share" / "Anki2" / "addons21"


@dataclass
class Settings:
    sample_rate: int = 16000
    frame_samples: int = 512
    input_device: Optional[int | str] = None
    min_burst_seconds: float = 0.25
    max_burst_seconds: float = 1.8
    end_silence_seconds: float = 0.20
    rearm_silence_seconds: float = 0.50
    speech_pad_seconds: float = 0.30
    vad_threshold: float = 0.4
    anki_url: str = "http://127.0.0.1:8765"
    anki_key: Optional[str] = None
    phrases: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {k: tuple(v) for k, v in DEFAULT_PHRASES.items()}
    )
    dry_run: bool = False
    silero_path: Optional[Path] = None
    vosk_path: Optional[Path] = None
    whisper_cli: Optional[Path] = None
    whisper_model: Optional[Path] = None

    def gate_config(self) -> GateConfig:
        return GateConfig(
            sample_rate=self.sample_rate,
            min_burst_seconds=self.min_burst_seconds,
            max_burst_seconds=self.max_burst_seconds,
            end_silence_seconds=self.end_silence_seconds,
            rearm_silence_seconds=self.rearm_silence_seconds,
            speech_pad_seconds=self.speech_pad_seconds,
        )


def _as_optional_device(value: Any) -> Optional[int | str]:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    text = str(value)
    if text.isdigit():
        return int(text)
    return text


def load_settings(path: Optional[Path] = None) -> Settings:
    settings = Settings()
    cfg_path = path or default_config_path()
    if cfg_path.is_file():
        with cfg_path.open("rb") as fh:
            data = tomllib.load(fh)
        _apply_toml(settings, data)
    env_key = os.environ.get("ANKI_CONNECT_KEY")
    if env_key:
        settings.anki_key = env_key
    env_url = os.environ.get("ANKI_CONNECT_URL")
    if env_url:
        settings.anki_url = env_url
    env_cli = os.environ.get("WHISPER_CLI")
    if env_cli:
        settings.whisper_cli = Path(env_cli)
    env_model = os.environ.get("WHISPER_MODEL")
    if env_model:
        settings.whisper_model = Path(env_model)
    return settings


def _toml_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_settings(settings: Settings, path: Optional[Path] = None) -> Path:
    """Write a complete user config. Used by --setup; overwrites dest."""
    dest = path or user_config_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Anki Puppeteer user config",
        "",
        "[audio]",
    ]
    if settings.input_device is not None:
        if isinstance(settings.input_device, int):
            lines.append(f"device = {settings.input_device}")
        else:
            lines.append(f"device = {_toml_str(str(settings.input_device))}")
    lines.extend(
        [
            "",
            "[gate]",
            f"min_burst_seconds = {settings.min_burst_seconds}",
            f"max_burst_seconds = {settings.max_burst_seconds}",
            f"end_silence_seconds = {settings.end_silence_seconds}",
            f"rearm_silence_seconds = {settings.rearm_silence_seconds}",
            f"speech_pad_seconds = {settings.speech_pad_seconds}",
            "",
            "[vad]",
            f"threshold = {settings.vad_threshold}",
            "",
            "[anki]",
            f"url = {_toml_str(settings.anki_url)}",
        ]
    )
    if settings.anki_key:
        lines.append(f"key = {_toml_str(settings.anki_key)}")
    lines.extend(["", "[stt]"])
    if settings.whisper_cli:
        lines.append(f"cli = {_toml_str(str(settings.whisper_cli))}")
    if settings.whisper_model:
        lines.append(f"model = {_toml_str(str(settings.whisper_model))}")
    lines.extend(["", "[models]"])
    if settings.silero_path:
        lines.append(f"silero = {_toml_str(str(settings.silero_path))}")
    if settings.vosk_path:
        lines.append(f"vosk = {_toml_str(str(settings.vosk_path))}")
    lines.append("")
    lines.append("[commands]")
    for name, variants in settings.phrases.items():
        inner = ", ".join(_toml_str(v) for v in variants)
        lines.append(f"{name} = [{inner}]")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def _apply_toml(settings: Settings, data: dict[str, Any]) -> None:
    audio = data.get("audio") or {}
    if "sample_rate" in audio:
        settings.sample_rate = int(audio["sample_rate"])
    if "device" in audio:
        settings.input_device = _as_optional_device(audio["device"])

    gate = data.get("gate") or {}
    for name in (
        "min_burst_seconds",
        "max_burst_seconds",
        "end_silence_seconds",
        "rearm_silence_seconds",
        "speech_pad_seconds",
    ):
        if name in gate:
            setattr(settings, name, float(gate[name]))

    vad = data.get("vad") or {}
    if "threshold" in vad:
        settings.vad_threshold = float(vad["threshold"])

    anki = data.get("anki") or {}
    if "url" in anki:
        settings.anki_url = str(anki["url"])
    if anki.get("key"):
        settings.anki_key = str(anki["key"])

    models = data.get("models") or {}
    if models.get("silero"):
        settings.silero_path = Path(models["silero"])
    if models.get("vosk"):
        settings.vosk_path = Path(models["vosk"])

    stt = data.get("stt") or {}
    if stt.get("cli"):
        settings.whisper_cli = Path(stt["cli"])
    if stt.get("model"):
        settings.whisper_model = Path(stt["model"])

    commands = data.get("commands")
    if commands:
        phrases: dict[str, tuple[str, ...]] = {
            k: tuple(v) for k, v in DEFAULT_PHRASES.items()
        }
        for name, variants in commands.items():
            if isinstance(variants, str):
                phrases[name] = (variants,)
            else:
                phrases[name] = tuple(str(v) for v in variants)
        settings.phrases = phrases
