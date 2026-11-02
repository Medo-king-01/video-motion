"""Portable Video Motion configuration and executable-path resolution.

New settings use the MEDO_* namespace and .video-motion/config.json.
Read-only compatibility aliases keep older local project settings working.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil

LEGACY_ENV = {
    "MEDO_CONFIG": "KHAAM_CONFIG",
    "MEDO_MODELS": "KHAAM_MODELS",
    "MEDO_SFX_LIBRARY": "KHAAM_SFX_LIBRARY",
    "MEDO_AUDIO_PYTHON": "KHAAM_AUDIO_PYTHON",
    "MEDO_TOOLKIT": "KHAAM_TOOLKIT",
    "MEDO_FFMPEG": "KHAAM_FFMPEG",
    "MEDO_FFPROBE": "KHAAM_FFPROBE",
    "MEDO_CHROMIUM": "KHAAM_CHROMIUM",
    "MEDO_ASSETS_DIR": "KHAAM_ASSETS_DIR",
    "MEDO_CHROMIUM_CACHE": "KHAAM_CHROMIUM_CACHE",
}


def _environment_value(name: str) -> str | None:
    """Prefer the current variable; fall back to the previous local setting name."""
    value = os.environ.get(name)
    if value:
        return value
    legacy_name = LEGACY_ENV.get(name)
    return os.environ.get(legacy_name) if legacy_name else None


def _expand_path(value: str | os.PathLike[str]) -> pathlib.Path:
    return pathlib.Path(os.path.expandvars(str(value))).expanduser()


def _config_path() -> pathlib.Path:
    cwd = pathlib.Path.cwd()
    explicit = os.environ.get("MEDO_CONFIG")
    if explicit:
        return _expand_path(explicit)

    current = cwd / ".video-motion" / "config.json"
    if current.is_file():
        return current

    # Transitional compatibility: read an existing older config, but never create it.
    legacy_explicit = os.environ.get(LEGACY_ENV["MEDO_CONFIG"])
    if legacy_explicit:
        legacy_path = _expand_path(legacy_explicit)
        if legacy_path.is_file():
            return legacy_path

    legacy_local = cwd / ".khaam" / "config.json"
    if legacy_local.is_file():
        return legacy_local
    return current


def config() -> tuple[dict, pathlib.Path]:
    """Read local configuration without creating folders or modifying files."""
    path = _config_path()
    if not path.exists():
        return {}, path.parent.parent
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Video Motion config must be a JSON object")
    return data, path.parent.parent


def resolve(key: str, env: str, default: str | os.PathLike[str] | None = None):
    """Resolve a configured path; relative values are anchored at the config root."""
    data, base = config()
    value = _environment_value(env) or data.get(key) or default
    if value is None:
        return None
    path = _expand_path(value)
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def models_dir() -> pathlib.Path:
    return resolve(
        "models_dir",
        "MEDO_MODELS",
        pathlib.Path.home() / ".cache" / "video-motion" / "models",
    )


def sfx_library() -> pathlib.Path:
    return resolve(
        "sfx_library",
        "MEDO_SFX_LIBRARY",
        pathlib.Path.cwd() / "assets" / "sfx",
    )


def executable(name: str) -> str | None:
    """Resolve a configured executable, then fall back to PATH."""
    env_name = f"MEDO_{name.upper()}"
    data, _ = config()
    override = _environment_value(env_name) or data.get(name)
    if override:
        candidate = resolve(name, env_name)
        if candidate and candidate.is_file():
            return str(candidate)
        return shutil.which(str(override))
    return shutil.which(name)
