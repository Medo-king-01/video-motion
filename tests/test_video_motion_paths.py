"""Regression tests for current and transitional local configuration paths."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "medo-motion" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import video_motion_paths as paths  # noqa: E402


def clear_path_environment(monkeypatch):
    names = [
        "MEDO_CONFIG", "MEDO_MODELS", "MEDO_SFX_LIBRARY", "MEDO_AUDIO_PYTHON",
        "MEDO_TOOLKIT", "MEDO_FFMPEG", "MEDO_FFPROBE", "MEDO_CHROMIUM",
        "MEDO_ASSETS_DIR", "MEDO_CHROMIUM_CACHE",
        "KHAAM_CONFIG", "KHAAM_MODELS", "KHAAM_SFX_LIBRARY", "KHAAM_AUDIO_PYTHON",
        "KHAAM_TOOLKIT", "KHAAM_FFMPEG", "KHAAM_FFPROBE", "KHAAM_CHROMIUM",
        "KHAAM_ASSETS_DIR", "KHAAM_CHROMIUM_CACHE",
    ]
    for name in names:
        monkeypatch.delenv(name, raising=False)


def write_config(path: Path, **values):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(values), encoding="utf-8")
    return path.read_bytes()


def test_new_config_location_and_project_relative_resolution(tmp_path, monkeypatch):
    clear_path_environment(monkeypatch)
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / ".video-motion" / "config.json"
    original = write_config(config_file, models_dir="shared/models")

    data, base = paths.config()

    assert data == {"models_dir": "shared/models"}
    assert base == tmp_path
    assert paths.models_dir() == (tmp_path / "shared" / "models").resolve()
    assert config_file.read_bytes() == original


def test_current_environment_name_takes_precedence(tmp_path, monkeypatch):
    clear_path_environment(monkeypatch)
    monkeypatch.chdir(tmp_path)
    write_config(tmp_path / ".video-motion" / "config.json", models_dir="from-config")
    monkeypatch.setenv("KHAAM_MODELS", "from-legacy-env")
    monkeypatch.setenv("MEDO_MODELS", "from-current-env")

    assert paths.models_dir() == (tmp_path / "from-current-env").resolve()


def test_legacy_config_and_environment_are_read_without_migration_writes(tmp_path, monkeypatch):
    clear_path_environment(monkeypatch)
    monkeypatch.chdir(tmp_path)
    legacy_file = tmp_path / ".khaam" / "config.json"
    original = write_config(legacy_file, models_dir="legacy-models")
    monkeypatch.setenv("KHAAM_MODELS", "legacy-env-models")

    data, base = paths.config()

    assert data == {"models_dir": "legacy-models"}
    assert base == tmp_path
    assert paths.models_dir() == (tmp_path / "legacy-env-models").resolve()
    assert legacy_file.read_bytes() == original
    assert not (tmp_path / ".video-motion").exists()


def test_current_config_wins_when_both_layouts_exist(tmp_path, monkeypatch):
    clear_path_environment(monkeypatch)
    monkeypatch.chdir(tmp_path)
    write_config(tmp_path / ".video-motion" / "config.json", models_dir="current-models")
    write_config(tmp_path / ".khaam" / "config.json", models_dir="legacy-models")

    assert paths.models_dir() == (tmp_path / "current-models").resolve()


def test_explicit_current_config_path_is_respected(tmp_path, monkeypatch):
    clear_path_environment(monkeypatch)
    monkeypatch.chdir(tmp_path)
    explicit = tmp_path / "settings" / "renderer.json"
    write_config(explicit, toolkit_dir="vendor/toolkit")
    monkeypatch.setenv("MEDO_CONFIG", str(explicit))

    data, base = paths.config()

    assert data["toolkit_dir"] == "vendor/toolkit"
    assert base == explicit.parent.parent
