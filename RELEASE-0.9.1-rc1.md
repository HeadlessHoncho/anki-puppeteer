Anki Puppeteer 0.9.1-rc1 — Windows installer.

Speech models are **not** inside the installer or this git repo.

## Installer

[AnkiPuppeteer-0.9.1-rc1-setup.exe](https://github.com/HeadlessHoncho/anki-puppeteer/releases/download/v0.9.1-rc1/AnkiPuppeteer-0.9.1-rc1-setup.exe) (~29 MB). Rebuild locally with `packaging\build.ps1` if you want.

- Per-user (`%LOCALAPPDATA%\Programs\AnkiPuppeteer`), no admin
- Frozen console exe (Python is not required on the target PC)
- Start menu shortcut **Anki Puppeteer** opens Anki if needed, then starts voice control
- Wizard page: download `ggml-tiny.en.bin` (~75 MB) **or** browse to an existing `ggml-*.bin`
- After files are copied, `AnkiPuppeteer.exe --setup` detects missing pieces and downloads:
  - whisper.cpp CPU tools (`whisper-bin-x64.zip` from ggml-org/whisper.cpp `b5130`, same commit as v1.9.4)
  - Silero VAD ONNX
  - `ggml-tiny.en.bin` unless `--model` / the wizard pointed at a local file
  - AnkiConnect add-on 2055492159
- Silent: `/SILENT` or `/SILENT /MODEL="D:\models\ggml-tiny.en.bin"`

Config is written to `%LOCALAPPDATA%\anki-puppeteer\config.toml` (`[stt] cli` / `model`).

## What still works

- Say `show` / `again` / `hard` / `good` / `easy` / `undo` while another app is focused
- Silero VAD on raw audio, short-burst gate, exact six-word whitelist, AnkiConnect

## Source

Python package is `0.9.1rc1`. `anki-puppeteer --setup --model PATH` is the same bootstrap the installer runs.
