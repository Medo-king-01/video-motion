"""Declared delivery profile → renderer canvas, through one explicit document.

Engine P draws in a fixed **design space** (1080×1920) and writes a **device buffer** scaled by
`REEL_SCALE`. A delivery profile therefore maps cleanly: its frame rate becomes `FPS`, and a smaller
9:16 size becomes the device scale (540×960 → 0.5). Anything that is not a uniform scale of the design
space — another aspect ratio, or larger than the master — is refused here, before a single frame.

    REEL_CANVAS=out/canvas.json python3 run_all.py

The document is produced by `tools/profiles.py canvas --profile <id>`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ENV = "REEL_CANVAS"
DESIGN = (1080, 1920)


def load(path: str | Path | None = None) -> dict:
    """Read the override document; anything unreadable is treated as 'no override', never as a guess."""
    raw = path if path is not None else os.environ.get(ENV)
    if not raw:
        return {}
    try:
        data = json.loads(Path(raw).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def env_fps(default: int = 30, path: str | Path | None = None) -> int:
    """The frame rate the renderer should use: the override when valid, otherwise the caller's default."""
    fps = load(path).get("fps", default)
    if isinstance(fps, bool) or not isinstance(fps, int) or fps <= 0:
        return default
    return fps


def size_scale(path: str | Path | None = None, design: tuple[int, int] = DESIGN) -> float:
    """Device scale for the requested size: 1.0 when absent, 0.5 for half, refused otherwise."""
    data = load(path)
    width, height = data.get("w"), data.get("h")
    if isinstance(width, bool) or isinstance(height, bool):
        return 1.0
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        return 1.0
    if (width, height) == design:
        return 1.0
    if width * design[1] != height * design[0]:
        raise SystemExit(f"{ENV}: {width}×{height} is not a uniform scale of {design[0]}×{design[1]} — "
                         "engine P owns one 9:16 design space; only a scaled device buffer is supported")
    if width > design[0]:
        raise SystemExit(f"{ENV}: {width}×{height} is larger than the {design[0]}×{design[1]} design space")
    return width / design[0]


def plan(width: int = DESIGN[0], height: int = DESIGN[1], path: str | Path | None = None) -> dict:
    """Everything the renderer needs: rate, device size, scale and the profile label."""
    scale = size_scale(path, (width, height))
    device = (int(round(width * scale)), int(round(height * scale)))
    data = load(path)
    return {"fps": env_fps(30, path), "design": (width, height), "device": device, "scale": scale,
            "profile": data.get("profile") or "brand", "overridden": bool(data)}


def describe(plan_doc: dict) -> str:
    """One log line: which profile, which rate, and whether a device scale was applied."""
    label = plan_doc["profile"]
    device = plan_doc["device"]
    tail = f"device scale {plan_doc['scale']:g}" if plan_doc["scale"] != 1 else "design size"
    return f"canvas: profile {label} · {device[0]}×{device[1]} · {plan_doc['fps']} fps · {tail}"
