"""Opt-in screen-space layout box capture and audit for engine P.

Mirrors the conservative AABB contract of `templates/render/lib/layout.js` (K):
- `L00`: invalid/missing registered box (including an unmeasured presenter `face_box`) or unknown zone
- `L01`: text ink outside its brand safe zone (`content` y200..1350, `caption` y1350..1500, `hud` y0..200, margin 40px)
- `L02`: two text boxes (or text + `keep` box) overlap by at least `min_overlap` px on both axes
- `L03`: text overlaps a measured presenter `face` box

Inactive during normal rendering (`is_capturing() == False`), so rendered pixels and performance are untouched.
"""
from __future__ import annotations

import contextlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

W, H = 1080, 1920
MARGIN = 40
CONTENT_Y = (200, 1350)
CAPTION_Y = (1350, 1500)
HUD_Y = (0, 200)
ZONES = {
    "content": CONTENT_Y,
    "caption": CAPTION_Y,
    "hud": HUD_Y,
}


def _load_safe_zones() -> None:
    global W, H, MARGIN, CONTENT_Y, CAPTION_Y, HUD_Y, ZONES
    brand_path = Path(__file__).resolve().parents[2] / "brand" / "brand.json"
    if not brand_path.is_file():
        return
    try:
        data = json.loads(brand_path.read_text(encoding="utf-8"))
        canvas = data.get("canvas", {})
        safe = data.get("safe_zone", {})
        W = int(canvas.get("w", W))
        H = int(canvas.get("h", H))
        MARGIN = int(safe.get("margin_px", MARGIN))
        cy = safe.get("content_y", list(CONTENT_Y))
        CONTENT_Y = (int(cy[0]), int(cy[1]))
        below = int(safe.get("nothing_important_below_y", CAPTION_Y[1]))
        CAPTION_Y = (CONTENT_Y[1], below)
        HUD_Y = (0, CONTENT_Y[0])
        ZONES = {"content": CONTENT_Y, "caption": CAPTION_Y, "hud": HUD_Y}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        pass


_load_safe_zones()

_STATE: dict[str, Any] | None = None


def is_capturing() -> bool:
    return _STATE is not None


def begin_frame() -> None:
    global _STATE
    _STATE = {"boxes": [], "meta": None}


def end_frame() -> list[dict[str, Any]]:
    global _STATE
    if _STATE is None:
        return []
    boxes = [dict(b) for b in _STATE["boxes"]]
    _STATE = None
    return boxes


def snapshot() -> list[dict[str, Any]] | None:
    if _STATE is None:
        return None
    return [dict(b) for b in _STATE["boxes"]]


@contextlib.contextmanager
def capture_frame():
    begin_frame()
    try:
        yield
    finally:
        pass


@contextlib.contextmanager
def with_layout(box_id: str | None = None, zone: str | None = None):
    if _STATE is None:
        yield
        return
    prev = _STATE["meta"]
    meta = dict(prev or {})
    if box_id is not None:
        meta["id"] = box_id
    if zone is not None:
        meta["zone"] = zone
    _STATE["meta"] = meta
    try:
        yield
    finally:
        _STATE["meta"] = prev


def _affine_matrix(
    w: float,
    h: float,
    cx: float,
    cy: float,
    scale: float = 1.0,
    rot: float = 0.0,
    anchor: tuple[float, float] = (0.5, 0.5),
    flipx: bool = False,
    sy: float | None = None,
) -> tuple[float, float, float, float, float, float]:
    ax, ay = anchor[0] * w, anchor[1] * h
    sxs = scale * (-1.0 if flipx else 1.0)
    sys_ = scale if sy is None else sy
    c, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    m00, m01 = c * sxs, -sn * sys_
    m10, m11 = sn * sxs, c * sys_
    tx = cx - (m00 * ax + m01 * ay)
    ty = cy - (m10 * ax + m11 * ay)
    return m00, m01, tx, m10, m11, ty


def _transform_rect(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    m: tuple[float, float, float, float, float, float],
) -> dict[str, float]:
    m00, m01, tx, m10, m11, ty = m
    xs = []
    ys = []
    for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        xs.append(m00 * px + m01 * py + tx)
        ys.append(m10 * px + m11 * py + ty)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return {"x": float(min_x), "y": float(min_y), "w": float(max_x - min_x), "h": float(max_y - min_y)}


def sprite_aabb(
    spr: np.ndarray,
    cx: float,
    cy: float,
    *,
    scale: float = 1.0,
    rot: float = 0.0,
    anchor: tuple[float, float] = (0.5, 0.5),
    flipx: bool = False,
    sy: float | None = None,
) -> dict[str, float] | None:
    """Compute tight screen-space ink AABB of an RGBA sprite placed via `lib.paste`."""
    if scale <= 0.003 or spr.ndim != 3 or spr.shape[0] == 0 or spr.shape[1] == 0:
        return None
    h, w = spr.shape[:2]
    if spr.shape[2] >= 4:
        ys, xs = np.where(spr[..., 3] > 2.5)
        if len(xs) == 0:
            return None
        x0, x1 = float(xs.min()), float(xs.max() + 1)
        y0, y1 = float(ys.min()), float(ys.max() + 1)
    else:
        x0, y0, x1, y1 = 0.0, 0.0, float(w), float(h)
    m = _affine_matrix(w, h, cx, cy, scale=scale, rot=rot, anchor=anchor, flipx=flipx, sy=sy)
    return _transform_rect(x0, y0, x1, y1, m)


def subrect_aabb(
    w: float,
    h: float,
    norm_rect: dict[str, float],
    cx: float,
    cy: float,
    *,
    scale: float = 1.0,
    rot: float = 0.0,
    anchor: tuple[float, float] = (0.5, 0.5),
    flipx: bool = False,
    sy: float | None = None,
) -> dict[str, float]:
    """Transform a normalized `[0..1]` sub-rectangle (e.g. measured `face_box`) to screen space."""
    x0 = float(norm_rect["x"]) * w
    y0 = float(norm_rect["y"]) * h
    x1 = x0 + float(norm_rect["w"]) * w
    y1 = y0 + float(norm_rect["h"]) * h
    m = _affine_matrix(w, h, cx, cy, scale=scale, rot=rot, anchor=anchor, flipx=flipx, sy=sy)
    return _transform_rect(x0, y0, x1, y1, m)


def record_text(
    text: str,
    box: dict[str, float] | None,
    *,
    box_id: str | None = None,
    zone: str = "content",
    alpha: float = 1.0,
) -> None:
    if _STATE is None or alpha <= 0.01 or box is None or not str(text).strip():
        return
    meta = _STATE["meta"] or {}
    resolved_id = box_id or meta.get("id") or f"text-{len(_STATE['boxes'])}"
    resolved_zone = meta.get("zone") or zone
    item = {
        "id": str(resolved_id),
        "kind": "text",
        "zone": str(resolved_zone),
        "text": str(text),
        "x": round(float(box["x"]), 3),
        "y": round(float(box["y"]), 3),
        "w": round(float(box["w"]), 3),
        "h": round(float(box["h"]), 3),
    }
    for existing in _STATE["boxes"]:
        if (
            existing.get("kind") == "text"
            and existing.get("text") == item["text"]
            and all(abs(float(existing[k]) - item[k]) < 0.05 for k in ("x", "y", "w", "h"))
        ):
            return
    _STATE["boxes"].append(item)


def protect_box(box_id: str, box: dict[str, float], *, kind: str = "face", alpha: float = 1.0) -> None:
    if _STATE is None or alpha <= 0.01:
        return
    _STATE["boxes"].append({
        "id": str(box_id),
        "kind": str(kind),
        "x": round(float(box.get("x", 0.0)), 3) if _is_finite(box.get("x")) else box.get("x"),
        "y": round(float(box.get("y", 0.0)), 3) if _is_finite(box.get("y")) else box.get("y"),
        "w": round(float(box.get("w", 0.0)), 3) if _is_finite(box.get("w")) else box.get("w"),
        "h": round(float(box.get("h", 0.0)), 3) if _is_finite(box.get("h")) else box.get("h"),
    })


def apply_camera(z: float, tx: float, ty: float) -> None:
    """Update already-drawn scene boxes when `scenes.camera(fr, z, tx, ty)` warps the canvas."""
    if _STATE is None:
        return
    ox = W / 2.0 - z * (W / 2.0) + tx
    oy = H / 2.0 - z * (H / 2.0) + ty
    for box in _STATE["boxes"]:
        if box.get("zone") in ("hud", "caption"):
            continue
        if not all(_is_finite(box.get(k)) for k in ("x", "y", "w", "h")):
            continue
        if float(box["w"]) <= 0 or float(box["h"]) <= 0:
            continue
        box["x"] = round(float(box["x"]) * z + ox, 3)
        box["y"] = round(float(box["y"]) * z + oy, 3)
        box["w"] = round(float(box["w"]) * z, 3)
        box["h"] = round(float(box["h"]) * z, 3)


def _is_finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


PLATFORM_RIGHT_RAIL = (940.0, 1100.0, 1080.0, 1500.0)


def audit_layout(
    boxes: Any,
    *,
    min_overlap: float = 2.0,
    check_platform_ui: bool = False,
) -> list[dict[str, Any]]:
    """Audit one frame's captured boxes against brand safe zones and collision rules."""
    if not isinstance(boxes, list):
        raise ValueError("Layout capture is missing")
    issues: list[dict[str, Any]] = []
    valid_flags: list[bool] = []
    for box in boxes:
        ok = (
            isinstance(box, dict)
            and isinstance(box.get("id"), str)
            and bool(box["id"].strip())
            and box.get("kind") in ("text", "face", "keep")
            and all(_is_finite(box.get(k)) for k in ("x", "y", "w", "h"))
            and float(box["w"]) > 0
            and float(box["h"]) > 0
        )
        valid_flags.append(ok)
        if not ok:
            bid = box.get("id") if isinstance(box, dict) and box.get("id") else "?"
            issues.append({"code": "L00", "ids": [str(bid)], "message": "Invalid registered box"})
            continue
        if box["kind"] != "text":
            continue
        zone = box.get("zone") or "content"
        if zone not in ZONES:
            issues.append({"code": "L00", "ids": [box["id"]], "message": "Unknown text zone"})
            bounds = CONTENT_Y
        else:
            bounds = ZONES[zone]
        x, y, w, h = float(box["x"]), float(box["y"]), float(box["w"]), float(box["h"])
        if x < MARGIN or x + w > W - MARGIN or y < bounds[0] or y + h > bounds[1]:
            issues.append({"code": "L01", "ids": [box["id"]], "message": f"Ink outside {zone} safe zone"})
        if check_platform_ui and zone != "hud":
            rx0, ry0, rx1, ry1 = PLATFORM_RIGHT_RAIL
            ox = min(x + w, rx1) - max(x, rx0)
            oy = min(y + h, ry1) - max(y, ry0)
            if ox >= min_overlap and oy >= min_overlap:
                issues.append({
                    "code": "L04",
                    "ids": [box["id"]],
                    "message": "Ink overlaps social right-rail UI zone (x940..1080 y1100..1500)",
                })

    for i in range(len(boxes)):
        if not valid_flags[i]:
            continue
        a = boxes[i]
        for j in range(i + 1, len(boxes)):
            if not valid_flags[j]:
                continue
            b = boxes[j]
            if a["kind"] != "text" and b["kind"] != "text":
                continue
            ox = min(float(a["x"]) + float(a["w"]), float(b["x"]) + float(b["w"])) - max(float(a["x"]), float(b["x"]))
            oy = min(float(a["y"]) + float(a["h"]), float(b["y"]) + float(b["h"])) - max(float(a["y"]), float(b["y"]))
            if ox >= min_overlap and oy >= min_overlap:
                code = "L03" if ("face" in (a["kind"], b["kind"])) else "L02"
                issues.append({"code": code, "ids": [a["id"], b["id"]], "message": "Overlapping protected ink/box"})
    return issues
