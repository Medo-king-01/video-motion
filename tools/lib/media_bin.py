"""Locate the media binaries once, with one precedence rule for every tool.

Every tool used to repeat the same three-line lookup, with three different answers:
`shutil.which("ffmpeg") or "ffmpeg"` in one place, `os.environ.get("FFMPEG_BIN") or ... or "ffmpeg"`
in another, and `imageio_ffmpeg.get_ffmpeg_exe()` only inside `selftest.py`. That drift is how a
machine ends up "READY" in one tool and "BLOCKED" in another.

Precedence (documented in AGENTS.md §9): an explicit environment override wins, then PATH, then the
static binary that `imageio-ffmpeg` ships. ffprobe has no bundled equivalent, so it falls back to the
repository's installed shim (`tools/bin/ffprobe`, written by `setup.sh`).
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIM = REPO_ROOT / "tools" / "bin" / "ffprobe"


def _first_executable(candidates: list[str | None]) -> str | None:
    for candidate in candidates:
        if not candidate:
            continue
        found = shutil.which(candidate)
        if found:
            return found
        path = Path(candidate)
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None


def _bundled_ffmpeg() -> str | None:
    """The static ffmpeg shipped by imageio-ffmpeg (no system install needed)."""
    try:
        import imageio_ffmpeg  # noqa: PLC0415 - optional dependency, imported only when needed
    except ImportError:
        return None
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - a broken optional package must not crash a CLI
        return None


def ffmpeg(required: bool = False) -> str | None:
    """Path to ffmpeg: `$FFMPEG_BIN`, then PATH, then the bundled static build."""
    found = _first_executable([os.environ.get("FFMPEG_BIN"), "ffmpeg"]) or _bundled_ffmpeg()
    if found is None and required:
        raise FileNotFoundError(
            "ffmpeg not found (set FFMPEG_BIN, put it on PATH, or: bash tools/setup.sh)")
    return found


def ffprobe(required: bool = False) -> str | None:
    """Path to ffprobe: `$FFPROBE_BIN`, then the installed shim, then PATH."""
    found = _first_executable([os.environ.get("FFPROBE_BIN"), str(SHIM), "ffprobe"])
    if found is None and required:
        raise FileNotFoundError(
            "ffprobe not found (FFmpeg ships it; this repo installs a shim: bash tools/setup.sh)")
    return found
