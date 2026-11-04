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
FPS = 30
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
    global W, H, FPS, MARGIN, CONTENT_Y, CAPTION_Y, HUD_Y, ZONES
    brand_path = Path(__file__).resolve().parents[2] / "brand" / "brand.json"
    if not brand_path.is_file():
        return
    try:
        data = json.loads(brand_path.read_text(encoding="utf-8"))
        canvas = data.get("canvas", {})
        safe = data.get("safe_zone", {})
        W = int(canvas.get("w", W))
        H = int(canvas.get("h", H))
        FPS = int(canvas.get("fps", FPS))
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
    _STATE = {"boxes": [], "meta": None, "layer": None, "stage_win": None}


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


def set_stage_window(win_box: dict[str, Any] | None) -> None:
    if _STATE is None:
        return
    _STATE["stage_win"] = dict(win_box) if isinstance(win_box, dict) else None


def stage_window() -> dict[str, Any] | None:
    if _STATE is None or _STATE.get("stage_win") is None:
        return None
    return dict(_STATE["stage_win"])


@contextlib.contextmanager
def with_stage_layer(layer: str, win_box: dict[str, Any] | None = None):
    if layer not in ("under", "content", "over"):
        raise ValueError(f"Unknown Fixed Stage layer {layer!r}")
    if _STATE is None:
        yield
        return
    prev_layer = _STATE["layer"]
    if win_box is not None:
        _STATE["stage_win"] = dict(win_box)
    _STATE["layer"] = layer
    try:
        yield
    finally:
        _STATE["layer"] = prev_layer


@contextlib.contextmanager
def capture_frame():
    begin_frame()
    try:
        yield
    finally:
        pass


@contextlib.contextmanager
def with_layout(box_id: str | None = None, zone: str | None = None, layer: str | None = None):
    if _STATE is None:
        yield
        return
    prev = _STATE["meta"]
    meta = dict(prev or {})
    if box_id is not None:
        meta["id"] = box_id
    if zone is not None:
        meta["zone"] = zone
    if layer is not None:
        meta["layer"] = layer
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
    layer: str | None = None,
) -> None:
    if _STATE is None or alpha <= 0.01 or box is None or not str(text).strip():
        return
    meta = _STATE["meta"] or {}
    resolved_id = box_id or meta.get("id") or f"text-{len(_STATE['boxes'])}"
    resolved_zone = meta.get("zone") or zone
    resolved_layer = layer or meta.get("layer") or _STATE.get("layer")
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
    if resolved_layer in ("under", "content", "over"):
        item["layer"] = str(resolved_layer)
    for existing in _STATE["boxes"]:
        if (
            existing.get("kind") == "text"
            and existing.get("text") == item["text"]
            and existing.get("layer") == item.get("layer")
            and all(abs(float(existing[k]) - item[k]) < 0.05 for k in ("x", "y", "w", "h"))
        ):
            return
    _STATE["boxes"].append(item)


def protect_box(
    box_id: str,
    box: dict[str, float],
    *,
    kind: str = "face",
    alpha: float = 1.0,
    layer: str | None = None,
    chrome: bool = False,
) -> None:
    if _STATE is None or alpha <= 0.01:
        return
    meta = _STATE["meta"] or {}
    resolved_layer = layer or meta.get("layer") or _STATE.get("layer")
    entry: dict[str, Any] = {
        "id": str(box_id),
        "kind": str(kind),
        "x": round(float(box.get("x", 0.0)), 3) if _is_finite(box.get("x")) else box.get("x"),
        "y": round(float(box.get("y", 0.0)), 3) if _is_finite(box.get("y")) else box.get("y"),
        "w": round(float(box.get("w", 0.0)), 3) if _is_finite(box.get("w")) else box.get("w"),
        "h": round(float(box.get("h", 0.0)), 3) if _is_finite(box.get("h")) else box.get("h"),
    }
    if resolved_layer in ("under", "content", "over"):
        entry["layer"] = str(resolved_layer)
    if chrome:
        entry["chrome"] = True
    _STATE["boxes"].append(entry)


def apply_camera(z: float, tx: float, ty: float) -> None:
    """Update already-drawn scene boxes when `scenes.camera(fr, z, tx, ty)` warps the canvas."""
    if _STATE is None:
        return
    ox = W / 2.0 - z * (W / 2.0) + tx
    oy = H / 2.0 - z * (H / 2.0) + ty
    for box in _STATE["boxes"]:
        if box.get("zone") in ("hud", "caption") or box.get("layer") in ("under", "over"):
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


def safe_envelope(zone: str = "content", *, check_platform_ui: bool = True) -> dict[str, Any]:
    """Return dynamic canvas, FPS, margin, zone bounds, and social HUD rail from the layout contract."""
    if zone not in ZONES:
        raise ValueError(f"Unknown layout zone {zone!r}; expected one of {sorted(ZONES)}")
    rx0, ry0, rx1, ry1 = PLATFORM_RIGHT_RAIL
    return {
        "w": W,
        "h": H,
        "fps": FPS,
        "margin": MARGIN,
        "zone": zone,
        "x": (float(MARGIN), float(W - MARGIN)),
        "y": (float(ZONES[zone][0]), float(ZONES[zone][1])),
        "nothing_important_below_y": float(CAPTION_Y[1]),
        "platform_right_rail": (
            {"x": rx0, "y": ry0, "w": rx1 - rx0, "h": ry1 - ry0}
            if check_platform_ui
            else None
        ),
    }


def _is_stage_fullscreen(win_box: dict[str, Any] | None) -> bool:
    if not isinstance(win_box, dict):
        return True
    if not all(_is_finite(win_box.get(k)) for k in ("x", "y", "w", "h")):
        return True
    r = float(win_box.get("r", 0.0)) if _is_finite(win_box.get("r", 0.0)) else 0.0
    return (
        abs(float(win_box["x"])) <= 1e-4
        and abs(float(win_box["y"])) <= 1e-4
        and abs(float(win_box["w"]) - float(W)) <= 1e-4
        and abs(float(win_box["h"]) - float(H)) <= 1e-4
        and abs(r) <= 1e-4
    )


def _window_corner_clips(box: dict[str, Any], win_box: dict[str, Any], eps: float = 0.5) -> list[str]:
    r = float(win_box.get("r", 0.0)) if _is_finite(win_box.get("r", 0.0)) else 0.0
    if r <= eps:
        return []
    bx0, by0 = float(box["x"]), float(box["y"])
    bx1, by1 = bx0 + float(box["w"]), by0 + float(box["h"])
    wx0, wy0 = float(win_box["x"]), float(win_box["y"])
    wx1, wy1 = wx0 + float(win_box["w"]), wy0 + float(win_box["h"])
    px0, py0 = max(wx0, min(wx1, bx0)), max(wy0, min(wy1, by0))
    px1, py1 = max(wx0, min(wx1, bx1)), max(wy0, min(wy1, by1))
    if px1 <= px0 or py1 <= py0:
        return []
    clipped: list[str] = []
    if px0 < wx0 + r and py0 < wy0 + r and math.hypot((wx0 + r) - px0, (wy0 + r) - py0) > r + eps:
        clipped.append("top-left")
    if px1 > wx1 - r and py0 < wy0 + r and math.hypot(px1 - (wx1 - r), (wy0 + r) - py0) > r + eps:
        clipped.append("top-right")
    if px0 < wx0 + r and py1 > wy1 - r and math.hypot((wx0 + r) - px0, py1 - (wy1 - r)) > r + eps:
        clipped.append("bottom-left")
    if px1 > wx1 - r and py1 > wy1 - r and math.hypot(px1 - (wx1 - r), py1 - (wy1 - r)) > r + eps:
        clipped.append("bottom-right")
    return clipped


def _effective_collision_rect(
    box: dict[str, Any],
    other: dict[str, Any],
    stage_win: dict[str, Any] | None,
    framed_stage: bool,
) -> tuple[float, float, float, float] | None:
    x0, y0 = float(box["x"]), float(box["y"])
    x1, y1 = x0 + float(box["w"]), y0 + float(box["h"])
    if not framed_stage or stage_win is None:
        return x0, y0, x1, y1
    b_layer = box.get("layer") or ("over" if box.get("zone") in ("hud", "caption") else "content")
    o_layer = other.get("layer") or ("over" if other.get("zone") in ("hud", "caption") else "content")
    if b_layer == "content" and o_layer != "content":
        wx0, wy0 = float(stage_win["x"]), float(stage_win["y"])
        wx1, wy1 = wx0 + float(stage_win["w"]), wy0 + float(stage_win["h"])
        cx0, cy0 = max(x0, wx0), max(y0, wy0)
        cx1, cy1 = min(x1, wx1), min(y1, wy1)
        if cx1 <= cx0 or cy1 <= cy0:
            return None
        return cx0, cy0, cx1, cy1
    return x0, y0, x1, y1


def audit_layout(
    boxes: Any,
    *,
    min_overlap: float = 2.0,
    check_platform_ui: bool = False,
    stage_win: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Audit one frame's captured boxes against physical frame, safe zones, collisions, and `win(t)`."""
    if not isinstance(boxes, list):
        raise ValueError("Layout capture is missing")
    issues: list[dict[str, Any]] = []
    valid_flags: list[bool] = []
    has_stage_win = (
        isinstance(stage_win, dict)
        and all(_is_finite(stage_win.get(k)) for k in ("x", "y", "w", "h"))
        and float(stage_win["w"]) > 0
        and float(stage_win["h"]) > 0
    )
    framed_stage = has_stage_win and not _is_stage_fullscreen(stage_win)

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

        x, y, w, h = float(box["x"]), float(box["y"]), float(box["w"]), float(box["h"])
        layer = box.get("layer")
        is_chrome = box.get("chrome") is True

        if box["kind"] != "text":
            if layer == "over" and not is_chrome:
                if x < MARGIN or x + w > W - MARGIN or y < 0 or y + h > CAPTION_Y[1]:
                    issues.append({
                        "code": "L01",
                        "ids": [box["id"]],
                        "message": "Foreground overlay escapes safe region",
                    })
                if check_platform_ui:
                    rx0, ry0, rx1, ry1 = PLATFORM_RIGHT_RAIL
                    ox = min(x + w, rx1) - max(x, rx0)
                    oy = min(y + h, ry1) - max(y, ry0)
                    if ox >= min_overlap and oy >= min_overlap:
                        issues.append({
                            "code": "L04",
                            "ids": [box["id"]],
                            "message": "Foreground overlay overlaps social right-rail UI zone (x940..1080 y1100..1500)",
                        })
            continue

        zone = box.get("zone") or "content"
        if zone not in ZONES:
            issues.append({"code": "L00", "ids": [box["id"]], "message": "Unknown text zone"})
            bounds = CONTENT_Y
        else:
            bounds = ZONES[zone]
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

        eff_layer = layer or ("over" if zone in ("hud", "caption") else "content")
        if framed_stage and stage_win is not None and eff_layer == "content":
            wx0, wy0 = float(stage_win["x"]), float(stage_win["y"])
            wx1, wy1 = wx0 + float(stage_win["w"]), wy0 + float(stage_win["h"])
            eps = 0.5
            if x < wx0 - eps or y < wy0 - eps or x + w > wx1 + eps or y + h > wy1 + eps:
                issues.append({
                    "code": "L05",
                    "ids": [box["id"]],
                    "message": "Content ink extends outside Fixed Stage window win(t)",
                })
            clipped_corners = _window_corner_clips(box, stage_win, eps=eps)
            if clipped_corners:
                issues.append({
                    "code": "L06",
                    "ids": [box["id"]],
                    "message": f"Ink clipped by Fixed Stage rounded corner ({', '.join(clipped_corners)})",
                })

    for i in range(len(boxes)):
        if not valid_flags[i]:
            continue
        a = boxes[i]
        if a.get("chrome") is True or a.get("layer") == "under":
            continue
        for j in range(i + 1, len(boxes)):
            if not valid_flags[j]:
                continue
            b = boxes[j]
            if b.get("chrome") is True or b.get("layer") == "under":
                continue
            if a["kind"] != "text" and b["kind"] != "text":
                continue
            ra = _effective_collision_rect(a, b, stage_win, framed_stage)
            rb = _effective_collision_rect(b, a, stage_win, framed_stage)
            if ra is None or rb is None:
                continue
            ox = min(ra[2], rb[2]) - max(ra[0], rb[0])
            oy = min(ra[3], rb[3]) - max(ra[1], rb[1])
            if ox >= min_overlap and oy >= min_overlap:
                code = "L03" if ("face" in (a["kind"], b["kind"])) else "L02"
                issues.append({"code": code, "ids": [a["id"], b["id"]], "message": "Overlapping protected ink/box"})
    return issues
