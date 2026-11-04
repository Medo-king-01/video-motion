"""Native Fixed Stage runtime and geometry core for Engine P (`stage.py`).

Implements Phase 2A — Fixed Stage under the authoritative VO Clock:
- Pure stateless dynamic content window `win(spec, t) -> {x, y, w, h, r}`
- Bidirectional full-screen <-> framed transitions with deterministic easing
- Strict three-layer compositing order: `UNDER` -> `CONTENT` (clipped to `win(t)`) -> `OVER` (unclipped)
- True supersampled rectangular (`r == 0`) and rounded-corner (`r > 0`) clipping masks
- Locked `brand.json` v2.6 12-color palette (+ `#030303` `ink_shadow`), zero invented branding
- Optional header driven exclusively by `plan/copy.json` + `plan/text-direction.json`
"""
from __future__ import annotations

import functools
import json
import math
import os
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PIL import Image, ImageDraw

try:
    import backgrounds as _backgrounds
except ImportError:  # pragma: no cover
    from . import backgrounds as _backgrounds  # type: ignore

try:
    import captions as _captions
except ImportError:  # pragma: no cover
    from . import captions as _captions  # type: ignore

try:
    import layout_p as _layout_p
except ImportError:  # pragma: no cover
    _layout_p = None  # type: ignore

try:
    from lib import D, fill_rect, paste, text_sprite
except ImportError:  # pragma: no cover
    from .lib import D, fill_rect, paste, text_sprite  # type: ignore

try:
    from render_policy import decorative_time
except ImportError:  # pragma: no cover
    from .render_policy import decorative_time  # type: ignore

try:
    import text_direction as _td
except ImportError:  # pragma: no cover
    from . import text_direction as _td  # type: ignore


# Locked brand.json v2.6 palette (12 colors + 1 derived shade).
PALETTE_HEX: dict[str, str] = {
    "red": "#CB271B",
    "red_bright": "#CB0801",
    "red_deep": "#9F0803",
    "ink": "#0A0A0A",
    "ink_soft": "#71717A",
    "paper": "#F3F2F1",
    "gray_1": "#D8D7D5",
    "gray_2": "#C9C5C2",
    "gray_3": "#BFBAB7",
    "gray_4": "#A3A2A0",
    "salmon": "#D97F68",
    "blush": "#D5AEA6",
    "ink_shadow": "#030303",
}

ROLE_ALIASES: dict[str, str] = {
    "red": "red",
    "red_bright": "red_bright",
    "redBright": "red_bright",
    "red_deep": "red_deep",
    "redDeep": "red_deep",
    "ink": "ink",
    "ink_soft": "ink_soft",
    "inkSoft": "ink_soft",
    "paper": "paper",
    "gray_1": "gray_1",
    "gray1": "gray_1",
    "gray_2": "gray_2",
    "gray2": "gray_2",
    "gray_3": "gray_3",
    "gray3": "gray_3",
    "gray_4": "gray_4",
    "gray4": "gray_4",
    "salmon": "salmon",
    "blush": "blush",
    "ink_shadow": "ink_shadow",
    "inkShadow": "ink_shadow",
}

PALETTE_RGB: dict[str, tuple[int, int, int]] = {
    key: (int(hx[1:3], 16), int(hx[3:5], 16), int(hx[5:7], 16))
    for key, hx in PALETTE_HEX.items()
}

DEFAULT_CANVAS: dict[str, int] = {"w": 1080, "h": 1920, "fps": 30}
DEFAULT_FRAMED_BOX: dict[str, float] = {
    "x": 56.0,
    "y": 224.0,
    "w": 968.0,
    "h": 1096.0,
    "r": 36.0,
}

STAGE_EASES = frozenset({"linear", "cubicOut", "cubicInOut", "quintOut", "quadInOut"})
FORBIDDEN_BRANDING_KEYS = frozenset({
    "logo",
    "channelName",
    "channel_name",
    "seriesName",
    "series_name",
    "watermark",
    "permanentTitle",
    "permanent_title",
})
VALID_TEXT_ROLES = frozenset({"caption", "hook", "title", "body", "keyword", "cta", "label", "number", "ui", "quote", "hud"})
MASK_SUPERSAMPLE = 4


def _short_repr(value: Any, limit: int = 48) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        try:
            if abs(value) > 10**40:
                sign = "-" if value < 0 else ""
                return f"<{sign}int bit_length={value.bit_length()}>"
        except Exception:  # pragma: no cover
            return "<huge int>"
    try:
        text = repr(value)
    except Exception:
        text = f"<{type(value).__name__}>"
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        fval = float(value)
    except OverflowError:
        return False
    return math.isfinite(fval)


def _require_finite(value: Any, label: str = "value") -> float:
    if not _is_finite_number(value):
        raise ValueError(f"{label} must be a finite number (got {_short_repr(value)})")
    return float(value)


def resolve_brand_role(role: Any, label: str = "colorRole") -> str:
    if not isinstance(role, str) or not role.strip():
        raise ValueError(f"{label} must be a non-empty locked brand role string")
    key = role.strip()
    if key.startswith("#") or key.lower().startswith("rgb"):
        raise ValueError(f"{label} must use a locked brand.json role name, not raw color {key!r}")
    canonical = ROLE_ALIASES.get(key)
    if canonical is None:
        raise ValueError(f"{label} {key!r} is not in the locked brand.json v2.6 palette")
    return canonical


def brand_rgb(role: Any, label: str = "colorRole") -> tuple[int, int, int]:
    return PALETTE_RGB[resolve_brand_role(role, label)]


def brand_hex(role: Any, label: str = "colorRole") -> str:
    return PALETTE_HEX[resolve_brand_role(role, label)]


def ease_stage(name: str, u: float) -> float:
    if name not in STAGE_EASES:
        raise ValueError(f"Unknown stage ease {name!r}; expected one of {sorted(STAGE_EASES)}")
    p = 0.0 if u <= 0.0 else 1.0 if u >= 1.0 else float(u)
    if p == 0.0 or p == 1.0 or name == "linear":
        return p
    if name == "cubicOut":
        inv = 1.0 - p
        return 1.0 - inv * inv * inv
    if name == "quintOut":
        inv = 1.0 - p
        return 1.0 - inv * inv * inv * inv * inv
    if name == "quadInOut":
        return 2.0 * p * p if p < 0.5 else 1.0 - ((-2.0 * p + 2.0) ** 2) / 2.0
    # cubicInOut
    return 4.0 * p * p * p if p < 0.5 else 1.0 - ((-2.0 * p + 2.0) ** 3) / 2.0


def _resolve_canvas(canvas: dict[str, Any] | None) -> dict[str, int]:
    if canvas is None:
        return dict(DEFAULT_CANVAS)
    if not isinstance(canvas, dict):
        raise ValueError("canvas must be an object with w, h, and optional fps")
    w = _require_finite(canvas.get("w", DEFAULT_CANVAS["w"]), "canvas.w")
    h = _require_finite(canvas.get("h", DEFAULT_CANVAS["h"]), "canvas.h")
    fps = _require_finite(canvas.get("fps", DEFAULT_CANVAS["fps"]), "canvas.fps")
    if w <= 0 or h <= 0 or fps <= 0 or int(w) != w or int(h) != h or int(fps) != fps:
        raise ValueError("canvas.w, canvas.h, and canvas.fps must be positive integers")
    return {"w": int(w), "h": int(h), "fps": int(fps)}


def fullscreen_box(canvas: dict[str, Any] | None = None) -> dict[str, float]:
    c = _resolve_canvas(canvas)
    return {"x": 0.0, "y": 0.0, "w": float(c["w"]), "h": float(c["h"]), "r": 0.0}


def clamp_radius(r: Any, w: Any, h: Any) -> float:
    rf = _require_finite(r, "r")
    wf = _require_finite(w, "w")
    hf = _require_finite(h, "h")
    if wf <= 0.0 or hf <= 0.0:
        raise ValueError("Window width and height must be strictly positive")
    max_r = min(wf, hf) / 2.0
    if rf <= 0.0:
        return 0.0
    return max_r if rf >= max_r else rf


def clamp_window_box(
    box: Any,
    canvas: dict[str, Any] | None = None,
    *,
    label: str = "box",
    require_inside_canvas: bool = True,
) -> dict[str, float]:
    if not isinstance(box, dict):
        raise ValueError(f"{label} must be an object with x, y, w, h, and optional r")
    c = _resolve_canvas(canvas)
    cw, ch = float(c["w"]), float(c["h"])
    x = _require_finite(box.get("x"), f"{label}.x")
    y = _require_finite(box.get("y"), f"{label}.y")
    w = _require_finite(box.get("w"), f"{label}.w")
    h = _require_finite(box.get("h"), f"{label}.h")
    r_raw = box.get("r", 0.0)
    r = _require_finite(r_raw, f"{label}.r")

    if w <= 0.0 or h <= 0.0:
        raise ValueError(f"{label} width and height must be > 0 (got w={w}, h={h})")

    x1 = x + w
    y1 = y + h
    if not (math.isfinite(x1) and math.isfinite(y1)):
        raise ValueError(f"{label} bounds overflow finite range")

    if require_inside_canvas:
        eps = 1e-6
        if x < -eps or y < -eps or x1 > cw + eps or y1 > ch + eps:
            raise ValueError(
                f"{label} [{x}, {y}, {w}, {h}] exceeds physical canvas [0, 0, {cw:g}, {ch:g}]"
            )
        if abs(x) <= eps:
            x = 0.0
        if abs(y) <= eps:
            y = 0.0
        if abs(x + w - cw) <= eps:
            w = cw - x
        if abs(y + h - ch) <= eps:
            h = ch - y

    clamped_r = clamp_radius(r, w, h)
    return {"x": float(x), "y": float(y), "w": float(w), "h": float(h), "r": float(clamped_r)}


def is_fullscreen_window(
    box: dict[str, Any],
    canvas: dict[str, Any] | None = None,
    *,
    eps: float = 1e-6,
) -> bool:
    c = _resolve_canvas(canvas)
    w_box = clamp_window_box(box, c, require_inside_canvas=False)
    return (
        abs(w_box["x"]) <= eps
        and abs(w_box["y"]) <= eps
        and abs(w_box["w"] - float(c["w"])) <= eps
        and abs(w_box["h"] - float(c["h"])) <= eps
        and abs(w_box["r"]) <= eps
    )


def _boxes_equal(a: dict[str, float], b: dict[str, float], eps: float = 1e-5) -> bool:
    return all(abs(a[k] - b[k]) <= eps for k in ("x", "y", "w", "h", "r"))


def _resolve_endpoint_box(
    endpoint: Any,
    default_framed: dict[str, float],
    full_box: dict[str, float],
    canvas: dict[str, int],
    label: str,
) -> dict[str, float]:
    if endpoint == "fullscreen":
        return dict(full_box)
    if endpoint == "framed":
        return dict(default_framed)
    if isinstance(endpoint, dict):
        return clamp_window_box(endpoint, canvas, label=label)
    raise ValueError(f"{label} must be 'fullscreen', 'framed', or a window box object")


def _validate_anchor(anchor: Any, label: str, errors: list[str]) -> dict[str, Any] | None:
    if anchor is None:
        return None
    if not isinstance(anchor, dict):
        errors.append(f"{label} must be an object with scene and word")
        return None
    scene = anchor.get("scene")
    word = anchor.get("word")
    if isinstance(scene, bool) or not isinstance(scene, int) or scene < 1:
        errors.append(f"{label}.scene must be an integer >= 1")
    if isinstance(word, bool) or not isinstance(word, int) or word < 0:
        errors.append(f"{label}.word must be a non-negative integer word index")
    text = anchor.get("text")
    if text is not None and (not isinstance(text, str) or not text.strip()):
        errors.append(f"{label}.text must be a non-empty string when provided")
    out: dict[str, Any] = {"scene": scene, "word": word}
    if isinstance(text, str) and text.strip():
        out["text"] = text.strip()
    return out


def validate_stage_spec(spec: Any) -> list[str]:
    """Return a list of validation error messages (empty list == valid)."""
    errors: list[str] = []
    if not isinstance(spec, dict):
        return ["stage spec must be a JSON object"]

    for bad_key in FORBIDDEN_BRANDING_KEYS:
        if bad_key in spec and spec[bad_key] is not None:
            errors.append(f"stage.{bad_key} is forbidden: studio forbids default logos, channel names, and series names")

    version = spec.get("version", 1)
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        errors.append("stage.version must be 1")

    if "enabled" in spec and not isinstance(spec["enabled"], bool):
        errors.append("stage.enabled must be a boolean")

    if "autoWrap" in spec and not isinstance(spec["autoWrap"], bool):
        errors.append("stage.autoWrap must be a boolean")

    stage_id = spec.get("id", "fixed-stage")
    if not isinstance(stage_id, str) or not stage_id.strip():
        errors.append("stage.id must be a non-empty string")

    clock = spec.get("clock", "vo")
    if clock != "vo":
        errors.append("stage.clock must be 'vo' (authoritative VO Clock required)")

    theme = spec.get("theme", "dark")
    if theme not in ("dark", "light"):
        errors.append("stage.theme must be 'dark' or 'light'")

    try:
        canvas = _resolve_canvas(spec.get("canvas"))
    except ValueError as exc:
        errors.append(str(exc))
        return errors

    full_box = fullscreen_box(canvas)
    raw_default_box = spec.get("defaultFramedBox")
    default_framed: dict[str, float]
    if raw_default_box is None:
        if canvas["w"] == 1080 and canvas["h"] == 1920:
            default_framed = dict(DEFAULT_FRAMED_BOX)
        else:
            mx = round(canvas["w"] * (56.0 / 1080.0), 3)
            yt = round(canvas["h"] * (224.0 / 1920.0), 3)
            wh = round(canvas["h"] * (1096.0 / 1920.0), 3)
            default_framed = clamp_window_box(
                {"x": mx, "y": yt, "w": canvas["w"] - 2 * mx, "h": wh, "r": round(min(canvas["w"], canvas["h"]) * 0.033, 3)},
                canvas,
                label="defaultFramedBox",
            )
    else:
        try:
            default_framed = clamp_window_box(raw_default_box, canvas, label="defaultFramedBox")
        except ValueError as exc:
            errors.append(str(exc))
            default_framed = dict(full_box)

    # Validate UNDER config
    under = spec.get("under", {})
    if not isinstance(under, dict):
        errors.append("stage.under must be an object")
    else:
        for bad_key in FORBIDDEN_BRANDING_KEYS:
            if bad_key in under and under[bad_key] is not None:
                errors.append(f"stage.under.{bad_key} is forbidden")
        if "surfaceRole" in under and under["surfaceRole"] is not None:
            try:
                resolve_brand_role(under["surfaceRole"], "under.surfaceRole")
            except ValueError as exc:
                errors.append(str(exc))
        bg = under.get("background")
        if bg is not None:
            if not isinstance(bg, dict):
                errors.append("under.background must be an object")
            else:
                bg_id = bg.get("id", "wash")
                if bg_id not in _backgrounds.BACKGROUND_IDS:
                    errors.append(f"under.background.id {bg_id!r} is not in the locked background catalog")
                bg_theme = bg.get("theme", theme)
                if bg_theme not in ("dark", "light"):
                    errors.append("under.background.theme must be 'dark' or 'light'")
                for param_key in ("density", "angle", "speed"):
                    if param_key in bg and not _is_finite_number(bg[param_key]):
                        errors.append(f"under.background.{param_key} must be a finite number")
        frame_cfg = under.get("frame")
        if frame_cfg is not None:
            if not isinstance(frame_cfg, dict):
                errors.append("under.frame must be an object")
            else:
                if "strokeRole" in frame_cfg and frame_cfg["strokeRole"] is not None:
                    try:
                        resolve_brand_role(frame_cfg["strokeRole"], "under.frame.strokeRole")
                    except ValueError as exc:
                        errors.append(str(exc))
                if "matRole" in frame_cfg and frame_cfg["matRole"] is not None:
                    try:
                        resolve_brand_role(frame_cfg["matRole"], "under.frame.matRole")
                    except ValueError as exc:
                        errors.append(str(exc))
                if "strokeWidth" in frame_cfg:
                    if not _is_finite_number(frame_cfg["strokeWidth"]) or float(frame_cfg["strokeWidth"]) < 0:
                        errors.append("under.frame.strokeWidth must be a finite number >= 0")
                if "matAlpha" in frame_cfg:
                    if not _is_finite_number(frame_cfg["matAlpha"]) or not (0.0 <= float(frame_cfg["matAlpha"]) <= 1.0):
                        errors.append("under.frame.matAlpha must be between 0 and 1")

    # Validate OVER config
    over = spec.get("over", {})
    if not isinstance(over, dict):
        errors.append("stage.over must be an object")
    else:
        for bad_key in FORBIDDEN_BRANDING_KEYS:
            if bad_key in over and over[bad_key] is not None:
                errors.append(f"stage.over.{bad_key} is forbidden")
        pb = over.get("progressBar")
        if pb is not None:
            if not isinstance(pb, dict):
                errors.append("over.progressBar must be an object")
            else:
                for role_key in ("trackRole", "fillRole"):
                    if role_key in pb and pb[role_key] is not None:
                        try:
                            resolve_brand_role(pb[role_key], f"over.progressBar.{role_key}")
                        except ValueError as exc:
                            errors.append(str(exc))
                for num_key in ("y", "height", "marginX", "trackAlpha"):
                    if num_key in pb and not _is_finite_number(pb[num_key]):
                        errors.append(f"over.progressBar.{num_key} must be a finite number")
        hdr = over.get("header")
        if hdr is not None:
            if not isinstance(hdr, dict):
                errors.append("over.header must be an object")
            else:
                for bad_key in FORBIDDEN_BRANDING_KEYS:
                    if bad_key in hdr and hdr[bad_key] is not None:
                        errors.append(f"over.header.{bad_key} is forbidden")
                if "text" in hdr and hdr["text"] is not None:
                    errors.append("over.header.text is forbidden: visible header text must come from plan/copy.json via slots[].copyId")
                slots = hdr.get("slots", [])
                if not isinstance(slots, list):
                    errors.append("over.header.slots must be an array")
                else:
                    parsed_ranges: list[tuple[float, float, str]] = []
                    for idx, slot in enumerate(slots):
                        s_label = f"over.header.slots[{idx}]"
                        if not isinstance(slot, dict):
                            errors.append(f"{s_label} must be an object")
                            continue
                        if "text" in slot and slot["text"] is not None:
                            errors.append(
                                f"{s_label}.text is forbidden: header slots must reference copyId from plan/copy.json, never inline text"
                            )
                        for bad_key in FORBIDDEN_BRANDING_KEYS:
                            if bad_key in slot and slot[bad_key] is not None:
                                errors.append(f"{s_label}.{bad_key} is forbidden")
                        slot_id = slot.get("id")
                        if not isinstance(slot_id, str) or not slot_id.strip():
                            errors.append(f"{s_label}.id must be a non-empty string")
                        copy_id = slot.get("copyId")
                        if not isinstance(copy_id, str) or not copy_id.strip():
                            errors.append(f"{s_label}.copyId must reference an entry in plan/copy.json")
                        scene_num = slot.get("scene")
                        if isinstance(scene_num, bool) or not isinstance(scene_num, int) or scene_num < 1:
                            errors.append(f"{s_label}.scene must be an integer >= 1")
                        role = slot.get("role", "label")
                        if role not in VALID_TEXT_ROLES:
                            errors.append(f"{s_label}.role {role!r} is not a valid text role")
                        s_start = slot.get("start")
                        s_end = slot.get("end")
                        if not (_is_finite_number(s_start) and _is_finite_number(s_end)):
                            errors.append(f"{s_label}.start and .end must be finite numbers")
                        else:
                            fs, fe = float(s_start), float(s_end)
                            if fs < 0.0 or fe <= fs:
                                errors.append(f"{s_label} requires 0 <= start < end")
                            else:
                                parsed_ranges.append((fs, fe, str(slot_id or idx)))
                        for role_key in ("colorRole", "accentRole", "pillRole", "pillBorderRole"):
                            if role_key in slot and slot[role_key] is not None:
                                try:
                                    resolve_brand_role(slot[role_key], f"{s_label}.{role_key}")
                                except ValueError as exc:
                                    errors.append(str(exc))
                        for num_key in ("x", "y", "size", "maxWidth", "pillAlpha"):
                            if num_key in slot and slot[num_key] is not None and not _is_finite_number(slot[num_key]):
                                errors.append(f"{s_label}.{num_key} must be a finite number")
                        _validate_anchor(slot.get("anchor"), f"{s_label}.anchor", errors)
                    parsed_ranges.sort(key=lambda item: item[0])
                    for i in range(1, len(parsed_ranges)):
                        if parsed_ranges[i][0] < parsed_ranges[i - 1][1] - 1e-9:
                            errors.append(
                                f"over.header.slots overlap between {parsed_ranges[i - 1][2]!r} and {parsed_ranges[i][2]!r}"
                            )

    # Validate timeline / mode
    timeline = spec.get("timeline")
    static_mode = spec.get("mode")
    if timeline is None:
        if static_mode is not None and static_mode not in ("fullscreen", "framed"):
            errors.append("stage.mode must be 'fullscreen' or 'framed' when timeline is omitted")
    else:
        if not isinstance(timeline, list) or len(timeline) == 0:
            errors.append("stage.timeline must be a non-empty list of segments")
        else:
            prev_end = -1.0
            prev_end_box: dict[str, float] | None = None
            for idx, seg in enumerate(timeline):
                label = f"timeline[{idx}]"
                if not isinstance(seg, dict):
                    errors.append(f"{label} must be an object")
                    continue
                mode = seg.get("mode")
                if mode not in ("fullscreen", "framed", "transition"):
                    errors.append(f"{label}.mode must be 'fullscreen', 'framed', or 'transition'")
                    continue
                s_raw, e_raw = seg.get("start"), seg.get("end")
                if not (_is_finite_number(s_raw) and _is_finite_number(e_raw)):
                    errors.append(f"{label}.start and .end must be finite numbers")
                    continue
                s_val, e_val = float(s_raw), float(e_raw)
                if s_val < 0.0 or e_val <= s_val:
                    errors.append(f"{label} requires 0 <= start < end (got {s_val}..{e_val})")
                    continue
                if prev_end >= 0.0 and s_val < prev_end - 1e-9:
                    errors.append(f"{label} overlaps previous segment ({s_val} < {prev_end})")
                _validate_anchor(seg.get("anchor"), f"{label}.anchor", errors)

                try:
                    if mode == "fullscreen":
                        seg_from = dict(full_box)
                        seg_to = dict(full_box)
                    elif mode == "framed":
                        box_val = seg.get("box")
                        seg_from = (
                            dict(default_framed)
                            if box_val is None
                            else clamp_window_box(box_val, canvas, label=f"{label}.box")
                        )
                        seg_to = dict(seg_from)
                    else:
                        ease_name = seg.get("ease", "cubicInOut")
                        if ease_name not in STAGE_EASES:
                            errors.append(f"{label}.ease {ease_name!r} must be one of {sorted(STAGE_EASES)}")
                        seg_from = _resolve_endpoint_box(
                            seg.get("from"), default_framed, full_box, canvas, f"{label}.from"
                        )
                        seg_to = _resolve_endpoint_box(
                            seg.get("to"), default_framed, full_box, canvas, f"{label}.to"
                        )
                except ValueError as exc:
                    errors.append(str(exc))
                    prev_end = e_val
                    continue

                if prev_end_box is not None and not _boxes_equal(prev_end_box, seg_from):
                    errors.append(
                        f"{label} starts from a window box that does not match the preceding state (discontinuous jump)"
                    )
                prev_end = e_val
                prev_end_box = seg_to

    return errors


def normalize_stage_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a canonical, pure normalized Fixed Stage specification."""
    errors = validate_stage_spec(spec)
    if errors:
        raise ValueError("; ".join(errors))

    canvas = _resolve_canvas(spec.get("canvas"))
    theme = spec.get("theme", "dark")
    full_box = fullscreen_box(canvas)
    raw_default = spec.get("defaultFramedBox")
    if raw_default is not None:
        default_framed = clamp_window_box(raw_default, canvas, label="defaultFramedBox")
    elif canvas["w"] == 1080 and canvas["h"] == 1920:
        default_framed = dict(DEFAULT_FRAMED_BOX)
    else:
        mx = round(canvas["w"] * (56.0 / 1080.0), 3)
        yt = round(canvas["h"] * (224.0 / 1920.0), 3)
        wh = round(canvas["h"] * (1096.0 / 1920.0), 3)
        default_framed = clamp_window_box(
            {"x": mx, "y": yt, "w": canvas["w"] - 2 * mx, "h": wh, "r": round(min(canvas["w"], canvas["h"]) * 0.033, 3)},
            canvas,
        )

    under_raw = spec.get("under") or {}
    bg_raw = under_raw.get("background")
    bg_norm = None
    if bg_raw is not None:
        bg_norm = {
            "id": bg_raw.get("id", "wash"),
            "theme": bg_raw.get("theme", theme),
            "density": float(bg_raw["density"]) if "density" in bg_raw else None,
            "angle": float(bg_raw["angle"]) if "angle" in bg_raw else None,
            "speed": float(bg_raw.get("speed", 1.0)),
        }
    frame_raw = under_raw.get("frame") or {}
    frame_norm = {
        "enabled": bool(frame_raw.get("enabled", True)),
        "strokeRole": resolve_brand_role(
            frame_raw.get("strokeRole", "red" if theme == "dark" else "ink"),
            "under.frame.strokeRole",
        ),
        "strokeWidth": float(frame_raw.get("strokeWidth", 3.0)),
        "matRole": resolve_brand_role(
            frame_raw.get("matRole", "ink_shadow" if theme == "dark" else "gray_1"),
            "under.frame.matRole",
        ),
        "matAlpha": float(frame_raw.get("matAlpha", 0.36)),
    }

    over_raw = spec.get("over") or {}
    pb_raw = over_raw.get("progressBar") or {}
    pb_norm = {
        "enabled": bool(pb_raw.get("enabled", True)),
        "y": float(pb_raw.get("y", 64.0)),
        "height": float(pb_raw.get("height", 6.0)),
        "marginX": float(pb_raw.get("marginX", 60.0)),
        "trackRole": resolve_brand_role(
            pb_raw.get("trackRole", "paper" if theme == "dark" else "ink"),
            "over.progressBar.trackRole",
        ),
        "trackAlpha": float(pb_raw.get("trackAlpha", 0.18)),
        "fillRole": resolve_brand_role(pb_raw.get("fillRole", "red"), "over.progressBar.fillRole"),
    }

    hdr_raw = over_raw.get("header") or {}
    slots_norm: list[dict[str, Any]] = []
    for slot in hdr_raw.get("slots") or []:
        slots_norm.append({
            "id": slot["id"].strip(),
            "scene": int(slot["scene"]),
            "copyId": slot["copyId"].strip(),
            "role": slot.get("role", "label"),
            "start": float(slot["start"]),
            "end": float(slot["end"]),
            "x": float(slot.get("x", canvas["w"] / 2.0)),
            "y": float(slot.get("y", 136.0)),
            "size": float(slot.get("size", 38.0)),
            "maxWidth": float(slot.get("maxWidth", canvas["w"] - 160.0)),
            "colorRole": resolve_brand_role(
                slot.get("colorRole", "paper" if theme == "dark" else "ink"),
                "slot.colorRole",
            ),
            "accentRole": resolve_brand_role(
                slot.get("accentRole", "salmon" if theme == "dark" else "red"),
                "slot.accentRole",
            ),
            "pillRole": (
                resolve_brand_role(slot["pillRole"], "slot.pillRole")
                if slot.get("pillRole")
                else None
            ),
            "pillBorderRole": (
                resolve_brand_role(slot["pillBorderRole"], "slot.pillBorderRole")
                if slot.get("pillBorderRole")
                else None
            ),
            "pillAlpha": float(slot.get("pillAlpha", 0.92)),
            "anchor": dict(slot["anchor"]) if isinstance(slot.get("anchor"), dict) else None,
        })
    slots_norm.sort(key=lambda item: item["start"])
    hdr_norm = {
        "enabled": bool(hdr_raw.get("enabled", bool(slots_norm))),
        "slots": slots_norm,
    }

    cap_raw = over_raw.get("captions") or {}
    cap_norm = {
        "enabled": bool(cap_raw.get("enabled", True)),
        "y": float(cap_raw.get("y", 1455.0)),
    }

    segments: list[dict[str, Any]] = []
    if spec.get("timeline") is None:
        static_mode = spec.get("mode", "framed")
        target_box = dict(full_box) if static_mode == "fullscreen" else dict(default_framed)
        segments.append({
            "mode": static_mode,
            "start": 0.0,
            "end": 1e9,
            "ease": "linear",
            "fromBox": dict(target_box),
            "toBox": dict(target_box),
            "anchor": None,
        })
    else:
        for seg in spec["timeline"]:
            mode = seg["mode"]
            if mode == "fullscreen":
                f_box = dict(full_box)
                t_box = dict(full_box)
                ease_name = "linear"
            elif mode == "framed":
                f_box = (
                    dict(default_framed)
                    if seg.get("box") is None
                    else clamp_window_box(seg["box"], canvas)
                )
                t_box = dict(f_box)
                ease_name = "linear"
            else:
                f_box = _resolve_endpoint_box(seg["from"], default_framed, full_box, canvas, "from")
                t_box = _resolve_endpoint_box(seg["to"], default_framed, full_box, canvas, "to")
                ease_name = seg.get("ease", "cubicInOut")
            segments.append({
                "mode": mode,
                "start": float(seg["start"]),
                "end": float(seg["end"]),
                "ease": ease_name,
                "fromBox": f_box,
                "toBox": t_box,
                "anchor": dict(seg["anchor"]) if isinstance(seg.get("anchor"), dict) else None,
            })

    return {
        "version": 1,
        "enabled": bool(spec.get("enabled", True)),
        "autoWrap": bool(spec.get("autoWrap", True)),
        "id": spec.get("id", "fixed-stage").strip(),
        "clock": "vo",
        "theme": theme,
        "canvas": canvas,
        "fullscreenBox": full_box,
        "defaultFramedBox": default_framed,
        "under": {
            "surfaceRole": resolve_brand_role(
                under_raw.get("surfaceRole", "ink_shadow" if theme == "dark" else "paper"),
                "under.surfaceRole",
            ),
            "background": bg_norm,
            "frame": frame_norm,
        },
        "over": {
            "progressBar": pb_norm,
            "header": hdr_norm,
            "captions": cap_norm,
        },
        "segments": segments,
    }


def _mix_box(a: dict[str, float], b: dict[str, float], p: float, canvas: dict[str, int]) -> dict[str, float]:
    if p <= 0.0:
        return dict(a)
    if p >= 1.0:
        return dict(b)
    q = 1.0 - p
    x = a["x"] * q + b["x"] * p
    y = a["y"] * q + b["y"] * p
    w = a["w"] * q + b["w"] * p
    h = a["h"] * q + b["h"] * p
    r = clamp_radius(a["r"] * q + b["r"] * p, w, h)
    return clamp_window_box({"x": x, "y": y, "w": w, "h": h, "r": r}, canvas)


def _eval_segments(norm: dict[str, Any], t: float) -> tuple[dict[str, float], str, float]:
    segs = norm["segments"]
    canvas = norm["canvas"]
    first = segs[0]
    if t <= first["start"]:
        box = dict(first["fromBox"])
        mode = "fullscreen" if is_fullscreen_window(box, canvas) else "framed"
        return box, mode, 0.0

    for idx, seg in enumerate(segs):
        if idx > 0 and t < seg["start"]:
            held = dict(segs[idx - 1]["toBox"])
            mode = "fullscreen" if is_fullscreen_window(held, canvas) else "framed"
            return held, mode, 1.0
        if seg["start"] <= t <= seg["end"]:
            if seg["mode"] != "transition":
                box = dict(seg["fromBox"])
                return box, seg["mode"], 1.0
            if t <= seg["start"]:
                box = dict(seg["fromBox"])
                mode = "fullscreen" if is_fullscreen_window(box, canvas) else "framed"
                return box, mode, 0.0
            if t >= seg["end"]:
                box = dict(seg["toBox"])
                mode = "fullscreen" if is_fullscreen_window(box, canvas) else "framed"
                return box, mode, 1.0
            raw_u = (t - seg["start"]) / (seg["end"] - seg["start"])
            p = ease_stage(seg["ease"], raw_u)
            box = _mix_box(seg["fromBox"], seg["toBox"], p, canvas)
            return box, "transition", p

    last = segs[-1]
    box = dict(last["toBox"])
    mode = "fullscreen" if is_fullscreen_window(box, canvas) else "framed"
    return box, mode, 1.0


def win(spec: dict[str, Any], t: Any) -> dict[str, float]:
    """Pure stateless Fixed Stage content window `win(t) -> {x, y, w, h, r}`."""
    tf = _require_finite(t, "t")
    norm = spec if spec.get("_normalized") is True else {**normalize_stage_spec(spec), "_normalized": True}
    box, _mode, _prog = _eval_segments(norm, tf)
    return box


def _chrome_opacity(box: dict[str, float], canvas: dict[str, int]) -> float:
    """Smooth 0..1 visibility of stage border chrome (0 in full-screen, 1 when inset >= 24px)."""
    cw, ch = float(canvas["w"]), float(canvas["h"])
    inset = max(box["x"], box["y"], cw - (box["x"] + box["w"]), ch - (box["y"] + box["h"]), box["r"])
    if inset <= 1e-6:
        return 0.0
    if inset >= 24.0:
        return 1.0
    u = inset / 24.0
    return u * u * (3.0 - 2.0 * u)


def active_header_at(norm: dict[str, Any], t: float) -> dict[str, Any] | None:
    hdr = norm["over"]["header"]
    if not hdr["enabled"]:
        return None
    for slot in hdr["slots"]:
        if slot["start"] <= t < slot["end"]:
            return dict(slot)
    return None


def stage_state_at(
    spec: dict[str, Any],
    t: Any,
    *,
    duration: float | None = None,
) -> dict[str, Any]:
    """Pure stateless Fixed Stage evaluation at VO timestamp `t`."""
    tf = _require_finite(t, "t")
    norm = spec if spec.get("_normalized") is True else {**normalize_stage_spec(spec), "_normalized": True}
    box, mode, trans_p = _eval_segments(norm, tf)
    full = is_fullscreen_window(box, norm["canvas"])
    prog_val = 0.0
    if duration is not None:
        df = _require_finite(duration, "duration")
        if df > 0.0:
            prog_val = max(0.0, min(1.0, tf / df))
    return {
        "time": tf,
        "win": box,
        "mode": "fullscreen" if full else mode,
        "isFullscreen": full,
        "transitionProgress": trans_p,
        "chromeOpacity": 0.0 if full else _chrome_opacity(box, norm["canvas"]),
        "activeHeader": active_header_at(norm, tf),
        "progress": prog_val,
    }


def create_stage(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate `spec` once and return pure bound evaluators (`win`, `state_at`, `spec`)."""
    norm = {**normalize_stage_spec(spec), "_normalized": True}
    return {
        "spec": norm,
        "win": lambda t: win(norm, t),
        "state_at": lambda t, duration=None: stage_state_at(norm, t, duration=duration),
    }


def stage_safe_envelope(
    win_box: dict[str, Any],
    *,
    margin: float = 40.0,
    padding: float = 24.0,
    content_y: tuple[float, float] = (200.0, 1350.0),
    canvas: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Safe inner content envelope intersected with `win(t)` and rounded-corner clearance."""
    c = _resolve_canvas(canvas)
    wb = clamp_window_box(win_box, c)
    if is_fullscreen_window(wb, c):
        x0, x1 = float(margin), float(c["w"]) - float(margin)
        y0, y1 = float(content_y[0]), float(content_y[1])
    else:
        # Corner clearance `r * (1 - 1/sqrt(2))` guarantees any box inside [x0..x1]x[y0..y1]
        # clears all four rounded-corner arcs as well as straight window edges.
        corner_inset = wb["r"] * (1.0 - (1.0 / math.sqrt(2.0))) + 8.0
        pad = max(float(padding), corner_inset)
        x0 = max(float(margin), wb["x"] + pad)
        x1 = min(float(c["w"]) - float(margin), wb["x"] + wb["w"] - pad)
        y0 = max(float(content_y[0]), wb["y"] + pad)
        y1 = min(float(content_y[1]), wb["y"] + wb["h"] - pad)
    return {
        "x": (x0, max(x0, x1)),
        "y": (y0, max(y0, y1)),
        "w": max(0.0, x1 - x0),
        "h": max(0.0, y1 - y0),
        "win": wb,
    }


def box_outside_window(
    box: dict[str, Any],
    win_box: dict[str, Any],
    *,
    eps: float = 0.5,
) -> bool:
    """Return True if screen-space AABB `box` extends outside the rectangular bounds of `win_box`."""
    bx0 = float(box["x"])
    by0 = float(box["y"])
    bx1 = bx0 + float(box["w"])
    by1 = by0 + float(box["h"])
    wx0 = float(win_box["x"])
    wy0 = float(win_box["y"])
    wx1 = wx0 + float(win_box["w"])
    wy1 = wy0 + float(win_box["h"])
    return bx0 < wx0 - eps or by0 < wy0 - eps or bx1 > wx1 + eps or by1 > wy1 + eps


def box_clipped_by_window_corners(
    box: dict[str, Any],
    win_box: dict[str, Any],
    *,
    eps: float = 0.5,
) -> list[str]:
    """Return which rounded corners of `win_box` (`r > 0`) clip AABB `box`."""
    r = float(win_box.get("r", 0.0))
    if r <= eps:
        return []
    bx0 = float(box["x"])
    by0 = float(box["y"])
    bx1 = bx0 + float(box["w"])
    by1 = by0 + float(box["h"])
    wx0 = float(win_box["x"])
    wy0 = float(win_box["y"])
    wx1 = wx0 + float(win_box["w"])
    wy1 = wy0 + float(win_box["h"])

    # Clamp test points to the window rectangle so pure L05 overflow is not double-counted
    # unless the point inside the window still enters the exterior corner cutout.
    px0 = max(wx0, min(wx1, bx0))
    py0 = max(wy0, min(wy1, by0))
    px1 = max(wx0, min(wx1, bx1))
    py1 = max(wy0, min(wy1, by1))
    if px1 <= px0 or py1 <= py0:
        return []

    clipped: list[str] = []
    # Top-left corner center (wx0 + r, wy0 + r)
    tl_cx, tl_cy = wx0 + r, wy0 + r
    if px0 < tl_cx and py0 < tl_cy and math.hypot(tl_cx - px0, tl_cy - py0) > r + eps:
        clipped.append("top-left")
    # Top-right corner center (wx1 - r, wy0 + r) — critical for RTL Arabic start glyphs
    tr_cx, tr_cy = wx1 - r, wy0 + r
    if px1 > tr_cx and py0 < tr_cy and math.hypot(px1 - tr_cx, tr_cy - py0) > r + eps:
        clipped.append("top-right")
    # Bottom-left corner center (wx0 + r, wy1 - r) — critical for RTL Arabic end descenders
    bl_cx, bl_cy = wx0 + r, wy1 - r
    if px0 < bl_cx and py1 > bl_cy and math.hypot(bl_cx - px0, py1 - bl_cy) > r + eps:
        clipped.append("bottom-left")
    # Bottom-right corner center (wx1 - r, wy1 - r)
    br_cx, br_cy = wx1 - r, wy1 - r
    if px1 > br_cx and py1 > br_cy and math.hypot(px1 - br_cx, py1 - br_cy) > r + eps:
        clipped.append("bottom-right")
    return clipped


# ---------------- Engine P Rendering & True Clipping Mask ----------------

@functools.lru_cache(maxsize=64)
def _cached_quantized_mask(
    qx: int,
    qy: int,
    qw: int,
    qh: int,
    qr: int,
    canvas_w: int,
    canvas_h: int,
) -> tuple[int, int, int, int, np.ndarray]:
    """Pure quantized (1/4 px) supersampled ROI mask for `win(t)`."""
    ss = MASK_SUPERSAMPLE
    x = qx / float(ss)
    y = qy / float(ss)
    w = qw / float(ss)
    h = qh / float(ss)
    r = qr / float(ss)

    ix0 = max(0, int(math.floor(x)))
    iy0 = max(0, int(math.floor(y)))
    ix1 = min(canvas_w, int(math.ceil(x + w)))
    iy1 = min(canvas_h, int(math.ceil(y + h)))
    rw = ix1 - ix0
    rh = iy1 - iy0
    if rw <= 0 or rh <= 0:
        return ix0, iy0, ix0, iy0, np.zeros((0, 0), dtype=np.float32)

    lx0 = int(round((x - ix0) * ss))
    ly0 = int(round((y - iy0) * ss))
    lx1 = int(round((x + w - ix0) * ss))
    ly1 = int(round((y + h - iy0) * ss))
    hi = Image.new("L", (rw * ss, rh * ss), 0)
    draw = ImageDraw.Draw(hi)
    # Pillow rectangle/rounded_rectangle right/bottom coordinates are inclusive; subtract 1 subpixel.
    rx1 = max(lx0, lx1 - 1)
    ry1 = max(ly0, ly1 - 1)
    if qr <= 0:
        draw.rectangle((lx0, ly0, rx1, ry1), fill=255)
    else:
        draw.rounded_rectangle((lx0, ly0, rx1, ry1), radius=qr, fill=255)
    lo = hi.resize((rw, rh), Image.Resampling.BOX)
    mask = np.asarray(lo, dtype=np.float32) / 255.0

    # Strict exterior corner guard when r > 0: ensure zero alpha outside the rounded arc.
    if r > 0.0:
        yy, xx = np.mgrid[iy0:iy1, ix0:ix1].astype(np.float32)
        px = xx + 0.5
        py = yy + 0.5
        wx0, wy0, wx1, wy1 = x, y, x + w, y + h
        dx = np.maximum(0.0, np.maximum((wx0 + r) - px, px - (wx1 - r)))
        dy = np.maximum(0.0, np.maximum((wy0 + r) - py, py - (wy1 - r)))
        in_corner_quadrant = (dx > 0.0) & (dy > 0.0)
        outside_arc = in_corner_quadrant & (np.hypot(dx, dy) > r + 0.75)
        mask = np.where(outside_arc, 0.0, mask)

    mask.flags.writeable = False
    return ix0, iy0, ix1, iy1, mask


def window_clip_mask(
    win_box: dict[str, Any],
    canvas_w: int = 1080,
    canvas_h: int = 1920,
) -> np.ndarray:
    """Return a full `(canvas_h, canvas_w)` float32 `[0..1]` clipping mask for `win_box`."""
    wb = clamp_window_box(win_box, {"w": canvas_w, "h": canvas_h})
    if is_fullscreen_window(wb, {"w": canvas_w, "h": canvas_h}):
        return np.ones((canvas_h, canvas_w), dtype=np.float32)
    ss = MASK_SUPERSAMPLE
    ix0, iy0, ix1, iy1, roi = _cached_quantized_mask(
        int(round(wb["x"] * ss)),
        int(round(wb["y"] * ss)),
        int(round(wb["w"] * ss)),
        int(round(wb["h"] * ss)),
        int(round(wb["r"] * ss)),
        canvas_w,
        canvas_h,
    )
    out = np.zeros((canvas_h, canvas_w), dtype=np.float32)
    if ix1 > ix0 and iy1 > iy0:
        out[iy0:iy1, ix0:ix1] = roi
    return out


def composite_content_window(
    stage_rgb_f32: np.ndarray,
    content_rgb: np.ndarray,
    win_box: dict[str, Any],
) -> np.ndarray:
    """Composite `content_rgb` onto `stage_rgb_f32` strictly clipped to `win_box`."""
    h, w = stage_rgb_f32.shape[:2]
    wb = clamp_window_box(win_box, {"w": w, "h": h})
    if is_fullscreen_window(wb, {"w": w, "h": h}):
        stage_rgb_f32[:] = content_rgb.astype(np.float32, copy=False)
        return stage_rgb_f32

    ss = MASK_SUPERSAMPLE
    ix0, iy0, ix1, iy1, roi_mask = _cached_quantized_mask(
        int(round(wb["x"] * ss)),
        int(round(wb["y"] * ss)),
        int(round(wb["w"] * ss)),
        int(round(wb["h"] * ss)),
        int(round(wb["r"] * ss)),
        w,
        h,
    )
    if ix1 <= ix0 or iy1 <= iy0:
        return stage_rgb_f32

    m = roi_mask[..., None]
    dst = stage_rgb_f32[iy0:iy1, ix0:ix1]
    src = content_rgb[iy0:iy1, ix0:ix1].astype(np.float32, copy=False)
    dst[:] = dst * (1.0 - m) + src * m
    return stage_rgb_f32


@functools.lru_cache(maxsize=32)
def _frame_border_sprite(
    w_px: int,
    h_px: int,
    r_px: float,
    stroke_rgb: tuple[int, int, int],
    stroke_w: float,
) -> np.ndarray:
    pad = max(4, int(math.ceil(stroke_w * 2)))
    d = D(w_px + pad * 2, h_px + pad * 2)
    box = (pad, pad, pad + w_px, pad + h_px)
    if r_px > 0.25:
        d.rrect(box, r_px, fill=None, outline=stroke_rgb + (255,), width=stroke_w)
    else:
        d.rect(box, fill=None, outline=stroke_rgb + (255,), width=stroke_w)
    return d.done()


@functools.lru_cache(maxsize=64)
def _header_pill_sprite(
    w_px: int,
    h_px: int,
    fill_rgb: tuple[int, int, int],
    border_rgb: tuple[int, int, int] | None,
) -> np.ndarray:
    d = D(w_px, h_px)
    outline = border_rgb + (255,) if border_rgb is not None else None
    d.rrect((2, 2, w_px - 2, h_px - 2), (h_px - 4) / 2.0, fill=fill_rgb + (255,), outline=outline, width=3 if outline else 0)
    return d.done()


def draw_stage_under(
    stage_f32: np.ndarray,
    norm_spec: dict[str, Any],
    t: float,
    *,
    win_box: dict[str, float],
    chrome_opacity: float = 1.0,
    motion_mode: str = "normal",
) -> None:
    """Paint the persistent `UNDER` stage background and optional ambient mat."""
    h, w = stage_f32.shape[:2]
    under = norm_spec["under"]
    bg_cfg = under["background"]
    amb_t = decorative_time(t, motion_mode)
    if bg_cfg is not None:
        bg_u8 = _backgrounds.frame(
            bg_cfg["id"],
            w,
            h,
            amb_t,
            theme=bg_cfg["theme"],
            density=bg_cfg["density"],
            angle=bg_cfg["angle"],
            speed=bg_cfg["speed"],
        )
        stage_f32[:] = bg_u8.astype(np.float32)
    else:
        surf = brand_rgb(under["surfaceRole"])
        stage_f32[:] = np.array(surf, dtype=np.float32)

    frame_cfg = under["frame"]
    if frame_cfg["enabled"] and frame_cfg["matAlpha"] > 0.0 and chrome_opacity > 0.0:
        mat_rgb = brand_rgb(frame_cfg["matRole"])
        alpha = frame_cfg["matAlpha"] * chrome_opacity
        # Subtle shadow/mat halo 10px behind the content window
        mx0 = max(0, int(round(win_box["x"] - 8)))
        my0 = max(0, int(round(win_box["y"] + 10)))
        mx1 = min(w, int(round(win_box["x"] + win_box["w"] + 8)))
        my1 = min(h, int(round(win_box["y"] + win_box["h"] + 14)))
        if mx1 > mx0 and my1 > my0:
            roi = stage_f32[my0:my1, mx0:mx1]
            roi[:] = roi * (1.0 - alpha) + np.array(mat_rgb, dtype=np.float32) * alpha


def draw_stage_frame(
    stage_f32: np.ndarray,
    norm_spec: dict[str, Any],
    win_box: dict[str, float],
    *,
    chrome_opacity: float = 1.0,
) -> None:
    """Draw the crisp outer frame stroke around `win(t)` when framed."""
    frame_cfg = norm_spec["under"]["frame"]
    if not frame_cfg["enabled"] or frame_cfg["strokeWidth"] <= 0.0 or chrome_opacity <= 0.005:
        return
    stroke_rgb = brand_rgb(frame_cfg["strokeRole"])
    w_px = max(2, int(round(win_box["w"])))
    h_px = max(2, int(round(win_box["h"])))
    r_px = round(clamp_radius(win_box["r"], w_px, h_px), 1)
    spr = _frame_border_sprite(w_px, h_px, r_px, stroke_rgb, round(frame_cfg["strokeWidth"], 1))
    cx = win_box["x"] + win_box["w"] / 2.0
    cy = win_box["y"] + win_box["h"] / 2.0
    paste(stage_f32, spr, cx, cy, alpha=chrome_opacity)


def draw_stage_header(
    stage_f32: np.ndarray,
    norm_spec: dict[str, Any],
    state: dict[str, Any],
    *,
    direction: dict[str, Any] | None,
    copy_by_id: dict[str, str] | None,
) -> dict[str, Any] | None:
    """Draw the active `OVER` header slot via `copy_by_id` + `text-direction.json`."""
    slot = state["activeHeader"]
    if slot is None:
        return None
    if not copy_by_id or slot["copyId"] not in copy_by_id:
        raise ValueError(f"Header slot {slot['id']!r} missing copyId {slot['copyId']!r} in copy_by_id")
    text = copy_by_id[slot["copyId"]]
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"Header slot {slot['id']!r} copy text for {slot['copyId']!r} is empty")
    if not direction:
        raise ValueError(f"Header slot {slot['id']!r} requires plan/text-direction.json")

    font_meta = _td.font_for(direction, slot["scene"], slot["role"], slot["copyId"])
    color_rgb = brand_rgb(slot["colorRole"])
    accent_rgb = brand_rgb(slot["accentRole"])
    size_px = int(round(slot["size"]))

    if slot["pillRole"] is not None:
        lines = [ln for ln in text.split("\n") if ln.strip()]
        measured = [
            text_sprite(ln, size_px, color_rgb, True, 0, (3, 3, 3), font_meta["family"], font_meta["weight"])
            for ln in lines
        ]
        max_tw = max((s.shape[1] for s in measured), default=80)
        pill_w = min(int(round(slot["maxWidth"] + 56)), max_tw + 68)
        pill_h = int(round(len(lines) * size_px * 1.35 + 28))
        pill_rgb = brand_rgb(slot["pillRole"])
        border_rgb = brand_rgb(slot["pillBorderRole"]) if slot["pillBorderRole"] else None
        pill_spr = _header_pill_sprite(pill_w, pill_h, pill_rgb, border_rgb)
        paste(stage_f32, pill_spr, slot["x"], slot["y"], alpha=slot["pillAlpha"])

    _captions.draw_directed_text(
        stage_f32,
        text,
        direction=direction,
        scene=slot["scene"],
        role=slot["role"],
        element_id=slot["copyId"],
        t=state["time"],
        start=slot["start"],
        end=slot["end"],
        cx=slot["x"],
        cy=slot["y"],
        size=size_px,
        color=color_rgb,
        accent=accent_rgb,
        theme=norm_spec["theme"],
        rtl=True,
        zone="hud",
    )
    return slot


def draw_stage_progress(
    stage_f32: np.ndarray,
    norm_spec: dict[str, Any],
    progress: float,
) -> None:
    """Draw the `OVER` progress bar using locked brand roles."""
    pb = norm_spec["over"]["progressBar"]
    if not pb["enabled"]:
        return
    w = stage_f32.shape[1]
    x0 = pb["marginX"]
    x1 = w - pb["marginX"]
    y0 = pb["y"]
    y1 = y0 + pb["height"]
    track_rgb = brand_rgb(pb["trackRole"])
    fill_rgb = brand_rgb(pb["fillRole"])
    fill_rect(stage_f32, x0, y0, x1, y1, track_rgb, pb["trackAlpha"])
    p = max(0.0, min(1.0, float(progress)))
    if p > 0.0:
        fill_rect(stage_f32, x0, y0, x0 + (x1 - x0) * p, y1, fill_rgb, 1.0)


def render_fixed_stage(
    spec: dict[str, Any],
    t: float,
    content_fn: Callable[[float, dict[str, Any]], np.ndarray],
    *,
    over_fn: Callable[[np.ndarray, float, dict[str, Any]], None] | None = None,
    under_fn: Callable[[np.ndarray, float, dict[str, Any]], None] | None = None,
    duration: float | None = None,
    direction: dict[str, Any] | None = None,
    copy_by_id: dict[str, str] | None = None,
    words: list[dict[str, Any]] | None = None,
    caption_style: str | None = None,
    motion_mode: str = "normal",
) -> np.ndarray:
    """Render one deterministic Fixed Stage RGB uint8 frame in strict `UNDER -> CONTENT -> OVER` order."""
    norm = spec if spec.get("_normalized") is True else {**normalize_stage_spec(spec), "_normalized": True}
    state = stage_state_at(norm, t, duration=duration)
    cw, ch = norm["canvas"]["w"], norm["canvas"]["h"]
    wb = state["win"]

    capturing = _layout_p is not None and _layout_p.is_capturing()
    if capturing:
        _layout_p.set_stage_window(wb)

    if state["isFullscreen"]:
        if capturing:
            with _layout_p.with_stage_layer("content", wb):
                raw_content = content_fn(state["time"], state)
        else:
            raw_content = content_fn(state["time"], state)
        stage_f32 = raw_content.astype(np.float32, copy=True)
    else:
        stage_f32 = np.zeros((ch, cw, 3), dtype=np.float32)
        if capturing:
            with _layout_p.with_stage_layer("under", wb):
                draw_stage_under(
                    stage_f32,
                    norm,
                    state["time"],
                    win_box=wb,
                    chrome_opacity=state["chromeOpacity"],
                    motion_mode=motion_mode,
                )
                if under_fn is not None:
                    under_fn(stage_f32, state["time"], state)
            with _layout_p.with_stage_layer("content", wb):
                raw_content = content_fn(state["time"], state)
        else:
            draw_stage_under(
                stage_f32,
                norm,
                state["time"],
                win_box=wb,
                chrome_opacity=state["chromeOpacity"],
                motion_mode=motion_mode,
            )
            if under_fn is not None:
                under_fn(stage_f32, state["time"], state)
            raw_content = content_fn(state["time"], state)

        composite_content_window(stage_f32, raw_content, wb)
        draw_stage_frame(stage_f32, norm, wb, chrome_opacity=state["chromeOpacity"])

    # Layer 3: OVER (unclipped by win(t))
    def _paint_over() -> None:
        draw_stage_header(stage_f32, norm, state, direction=direction, copy_by_id=copy_by_id)
        if words and caption_style and norm["over"]["captions"]["enabled"]:
            fg_col = brand_rgb("paper" if norm["theme"] == "dark" else "ink")
            acc_col = brand_rgb("salmon" if norm["theme"] == "dark" else "red")
            _captions.draw_phrase_caption(
                stage_f32,
                state["time"],
                words,
                style=caption_style,
                y=norm["over"]["captions"]["y"],
                color=fg_col,
                accent=acc_col,
                theme=norm["theme"],
            )
        if duration is not None:
            draw_stage_progress(stage_f32, norm, state["progress"])
        if over_fn is not None:
            over_fn(stage_f32, state["time"], state)

    if capturing:
        with _layout_p.with_stage_layer("over", wb):
            _paint_over()
    else:
        _paint_over()

    return np.clip(np.rint(stage_f32), 0, 255).astype(np.uint8)


def is_stage_enabled(spec: Any) -> bool:
    """Return True when `spec` is a valid, active Fixed Stage specification (`enabled !== false`)."""
    if spec is None:
        return False
    errors = validate_stage_spec(spec)
    if errors:
        raise ValueError("; ".join(errors))
    return bool(spec.get("enabled", True))


def _load_strict_json(path: Path) -> Any:
    def _forbid_const(val: str) -> None:
        raise ValueError(f"Non-finite JSON constant {val!r} is forbidden in {path.name}")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_forbid_const)


@functools.lru_cache(maxsize=32)
def _load_project_stage_cached(
    root_str: str,
    sig: tuple[tuple[str, int, int], ...],
) -> dict[str, Any] | None:
    _ = sig
    root = Path(root_str)
    stage_path = root / "plan" / "stage.json"
    if not stage_path.is_file():
        return None
    raw_stage = _load_strict_json(stage_path)
    if not is_stage_enabled(raw_stage):
        return None
    norm_spec = {**normalize_stage_spec(raw_stage), "_normalized": True}

    duration: float | None = None
    scenes_meta: list[dict[str, Any]] = []
    beats_path = root / "plan" / "beats.json"
    if beats_path.is_file():
        beats_doc = _load_strict_json(beats_path)
        if isinstance(beats_doc, dict):
            raw_dur = beats_doc.get("duration")
            if _is_finite_number(raw_dur) and float(raw_dur) > 0.0:
                duration = float(raw_dur)
            if isinstance(beats_doc.get("scenes"), list):
                scenes_meta = [s for s in beats_doc["scenes"] if isinstance(s, dict)]

    copy_by_id: dict[str, str] = {}
    copy_path = root / "plan" / "copy.json"
    if copy_path.is_file():
        copy_doc = _load_strict_json(copy_path)
        if isinstance(copy_doc, dict) and isinstance(copy_doc.get("copy"), list):
            for item in copy_doc["copy"]:
                if isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("text"), str):
                    copy_by_id[item["id"]] = item["text"]

    direction = _td.load(root)

    words: list[dict[str, Any]] = []
    wt_path = root / "plan" / "word-timings.json"
    if wt_path.is_file():
        wt_doc = _load_strict_json(wt_path)
        if isinstance(wt_doc, dict) and isinstance(wt_doc.get("scenes"), list):
            for sc in wt_doc["scenes"]:
                if isinstance(sc, dict) and isinstance(sc.get("words"), list):
                    for w in sc["words"]:
                        if isinstance(w, dict) and _is_finite_number(w.get("start")) and _is_finite_number(w.get("end")):
                            words.append({
                                "text": str(w.get("text", "")),
                                "start": float(w["start"]),
                                "end": float(w["end"]),
                            })

    return {
        "spec": norm_spec,
        "duration": duration,
        "scenes": scenes_meta,
        "copy_by_id": copy_by_id,
        "direction": direction,
        "words": words,
    }


def load_project_stage(
    project_dir: str | os.PathLike[str] | None = None,
    *,
    include_manual: bool = False,
) -> dict[str, Any] | None:
    """Load `<project_dir>/plan/stage.json` + companion plan files when enabled (`enabled !== false`).

    By default (`include_manual=False`), returns `None` when `autoWrap` is `False` so the
    default `scenes.py` runtime skips automatic wrapping while preserving manual scene control.
    """
    root = Path(project_dir or os.environ.get("REEL_DIR") or Path.cwd()).resolve()
    plan_dir = root / "plan"
    stage_path = plan_dir / "stage.json"
    if not stage_path.is_file():
        return None
    tracked = ("stage.json", "beats.json", "copy.json", "text-direction.json", "word-timings.json")
    sig: list[tuple[str, int, int]] = []
    for name in tracked:
        p = plan_dir / name
        if p.is_file():
            st = p.stat()
            sig.append((name, st.st_mtime_ns, st.st_size))
    bundle = _load_project_stage_cached(str(root), tuple(sig))
    if bundle is None:
        return None
    if not include_manual and not bundle["spec"]["autoWrap"]:
        return None
    return bundle

