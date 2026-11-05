"""Phase 2C — deterministic One-Take semantic states inside the existing scene architecture.

The plan uses absolute VO seconds, timestamped camera/element snapshots and optional cursor clicks.
The same pure evaluator drives P/K/R; this module also provides the native OpenCV/Pillow P adapter.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import captions
import layout_p
import motion
from stage import brand_rgb, clamp_window_box, fullscreen_box, resolve_brand_role

ONE_TAKE_EASES = {"linear", "cubicInOut", "cubicOut", "quintOut", "sineInOut", "expoInOut"}
ONE_TAKE_KINDS = {"rect", "circle", "text"}
FONT_ROLES = {"caption", "hook", "title", "body", "keyword", "cta", "label", "number", "ui", "quote", "hud"}
_EPS = 1e-9


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _default_transform():
    return {"x": 0.0, "y": 0.0, "scale": 1.0, "rotation": 0.0, "opacity": 1.0}


def _canvas_of(raw, errors):
    if raw is not None and not isinstance(raw, dict):
        errors.append("canvas must be an object")
    source = raw if isinstance(raw, dict) else {}
    out = {}
    for key, fallback in (("w", 1080), ("h", 1920), ("fps", 30)):
        value = source.get(key, fallback)
        if not _finite(value) or int(value) != value or value <= 0:
            errors.append(f"canvas.{key} must be a positive integer")
        out[key] = int(value) if _finite(value) and int(value) == value and value > 0 else fallback
    return out


def _role_of(value, fallback, label, errors):
    try:
        return resolve_brand_role(value if value is not None else fallback, label)
    except ValueError as exc:
        errors.append(str(exc))
        return fallback


def _transform_of(raw, previous, where, errors):
    if raw is not None and not isinstance(raw, dict):
        errors.append(f"{where} must be an object")
    source = raw if isinstance(raw, dict) else {}
    out = {}
    for key in ("x", "y", "scale", "rotation", "opacity"):
        value = source.get(key, previous[key])
        if not _finite(value):
            errors.append(f"{where}.{key} must be finite")
        out[key] = float(value) if _finite(value) else previous[key]
    if out["scale"] <= 0:
        errors.append(f"{where}.scale must be positive")
        out["scale"] = previous["scale"]
    if not 0 <= out["opacity"] <= 1:
        errors.append(f"{where}.opacity must be within [0,1]")
        out["opacity"] = previous["opacity"]
    return out


def _parse_one_take(input_spec, external_duration=None):
    errors = []
    if not isinstance(input_spec, dict):
        return ["one-take spec must be an object"], None
    if input_spec.get("version") != 1:
        errors.append("version must be 1")
    if not isinstance(input_spec.get("id"), str) or not input_spec.get("id", "").strip():
        errors.append("id must be a non-empty stable string")
    if input_spec.get("clock", "vo") != "vo":
        errors.append("clock must be 'vo'; state and interaction times are absolute VO seconds")
    duration = input_spec.get("duration")
    if not _finite(duration) or duration <= 0:
        errors.append("duration must be finite and positive")
    scene_duration = float(duration) if _finite(duration) and duration > 0 else 1.0
    if external_duration is not None and (not _finite(external_duration) or external_duration <= 0):
        errors.append("external duration must be finite and positive")
    elif external_duration is not None and abs(float(external_duration) - scene_duration) > _EPS:
        errors.append(f"duration {scene_duration} must equal scene/VO duration {external_duration}")
    canvas = _canvas_of(input_spec.get("canvas"), errors)
    background_role = _role_of(input_spec.get("backgroundRole"), "ink_shadow", "backgroundRole", errors)

    raw_elements = input_spec.get("elements") if isinstance(input_spec.get("elements"), list) else []
    if not isinstance(input_spec.get("elements"), list) or not raw_elements:
        errors.append("elements must be a non-empty array")
    if len(raw_elements) > 64:
        errors.append("elements supports at most 64 entries")
    elements, element_ids = [], set()
    for index, raw in enumerate(raw_elements):
        where = f"elements[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{where} must be an object")
            continue
        element_id = raw.get("id")
        if not isinstance(element_id, str) or not element_id.strip():
            errors.append(f"{where}.id must be non-empty")
            element_id = f"invalid-{index}"
        elif element_id in element_ids:
            errors.append(f"duplicate element id: {element_id}")
        element_ids.add(element_id)
        kind = raw.get("kind")
        if kind not in ONE_TAKE_KINDS:
            errors.append(f"element {element_id}: kind must be rect, circle or text")
            kind = "rect"
        w, h = raw.get("w"), raw.get("h")
        if not _finite(w) or w <= 0 or not _finite(h) or h <= 0:
            errors.append(f"element {element_id}: w/h must be finite and positive")
        radius, stroke_width = raw.get("radius", 0), raw.get("strokeWidth", 0)
        if not _finite(radius) or radius < 0:
            errors.append(f"element {element_id}: radius must be finite and non-negative")
        if not _finite(stroke_width) or stroke_width < 0:
            errors.append(f"element {element_id}: strokeWidth must be finite and non-negative")
        element = {
            "id": element_id, "kind": kind,
            "w": float(w) if _finite(w) and w > 0 else 100.0,
            "h": float(h) if _finite(h) and h > 0 else 100.0,
            "radius": float(radius) if _finite(radius) and radius >= 0 else 0.0,
            "role": _role_of(raw.get("role"), "paper", f"element {element_id}.role", errors),
            "accentRole": _role_of(raw.get("accentRole"), "red", f"element {element_id}.accentRole", errors),
            "strokeRole": _role_of(raw.get("strokeRole"), "gray_2", f"element {element_id}.strokeRole", errors),
            "strokeWidth": float(stroke_width) if _finite(stroke_width) and stroke_width >= 0 else 0.0,
        }
        if kind == "text":
            if not isinstance(raw.get("text"), str) or not raw.get("text", "").strip():
                errors.append(f"element {element_id}: text must be a non-empty string")
            font_size, scene, font_role = raw.get("fontSize", 48), raw.get("scene", 1), raw.get("fontRole", "body")
            if not _finite(font_size) or font_size <= 0:
                errors.append(f"element {element_id}: fontSize must be finite and positive")
            if not isinstance(scene, int) or isinstance(scene, bool) or scene <= 0:
                errors.append(f"element {element_id}: scene must be a positive integer")
            if font_role not in FONT_ROLES:
                errors.append(f"element {element_id}: unknown fontRole {font_role}")
            if "rtl" in raw and not isinstance(raw["rtl"], bool):
                errors.append(f"element {element_id}: rtl must be boolean")
            element.update({
                "text": raw.get("text") if isinstance(raw.get("text"), str) else "",
                "fontSize": float(font_size) if _finite(font_size) and font_size > 0 else 48.0,
                "scene": scene if isinstance(scene, int) and not isinstance(scene, bool) and scene > 0 else 1,
                "fontRole": font_role, "rtl": raw.get("rtl", True),
            })
        elements.append(element)

    raw_states = input_spec.get("states") if isinstance(input_spec.get("states"), list) else []
    if not isinstance(input_spec.get("states"), list) or len(raw_states) < 2:
        errors.append("states must contain at least two semantic states")
    if len(raw_states) > 16:
        errors.append("states supports at most 16 entries")
    states, state_ids = [], set()
    previous_transforms = {element["id"]: _default_transform() for element in elements}
    previous_time = -math.inf
    for index, raw in enumerate(raw_states):
        where = f"states[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{where} must be an object")
            continue
        state_id = raw.get("id")
        if not isinstance(state_id, str) or not state_id.strip():
            errors.append(f"{where}.id must be non-empty")
            state_id = f"invalid-{index}"
        elif state_id in state_ids:
            errors.append(f"duplicate state id: {state_id}")
        state_ids.add(state_id)
        at = raw.get("time")
        if not _finite(at):
            errors.append(f"{where}.time must be finite")
        at = float(at) if _finite(at) else previous_time + 1
        if index == 0 and abs(at) > _EPS:
            errors.append("states must start at absolute VO time 0")
        if at <= previous_time + _EPS:
            errors.append(f"{where}.time must be strictly increasing")
        if index == len(raw_states) - 1 and abs(at - scene_duration) > _EPS:
            errors.append(f"last state time {at} must equal duration {scene_duration}")
        previous_time = at
        ease_name = raw.get("ease", "cubicInOut")
        if ease_name not in ONE_TAKE_EASES:
            errors.append(f"{where}.ease must be one of {sorted(ONE_TAKE_EASES)}")
        if not isinstance(raw.get("camera"), dict):
            errors.append(f"{where}.camera must be an object")
        camera_raw = raw.get("camera") if isinstance(raw.get("camera"), dict) else {}
        camera = {}
        for key in ("x", "y", "zoom"):
            value = camera_raw.get(key)
            if not _finite(value):
                errors.append(f"{where}.camera.{key} must be finite")
            camera[key] = float(value) if _finite(value) else 1.0 if key == "zoom" else canvas["w" if key == "x" else "h"] / 2
        if camera["zoom"] <= 0:
            errors.append(f"{where}.camera.zoom must be positive")
            camera["zoom"] = 1.0
        if raw.get("elements") is not None and not isinstance(raw.get("elements"), dict):
            errors.append(f"{where}.elements must be an object")
        patches = raw.get("elements") if isinstance(raw.get("elements"), dict) else {}
        for patch_id in patches:
            if patch_id not in element_ids:
                errors.append(f"{where}.elements references unknown element {patch_id}")
        transforms = {}
        for element in elements:
            transforms[element["id"]] = _transform_of(
                patches.get(element["id"]), previous_transforms.get(element["id"], _default_transform()),
                f"{where}.elements.{element['id']}", errors,
            )
        states.append({"id": state_id, "time": at, "ease": ease_name, "camera": camera, "elements": transforms})
        previous_transforms = transforms

    cursor = None
    if input_spec.get("cursor") is not None:
        raw = input_spec.get("cursor")
        if not isinstance(raw, dict):
            errors.append("cursor must be an object")
        source = raw if isinstance(raw, dict) else {}
        size, opacity = source.get("size", 42), source.get("opacity", 1)
        if not _finite(size) or size <= 0:
            errors.append("cursor.size must be finite and positive")
        if not _finite(opacity) or not 0 <= opacity <= 1:
            errors.append("cursor.opacity must be within [0,1]")
        raw_points = source.get("points") if isinstance(source.get("points"), list) else []
        if not raw_points:
            errors.append("cursor.points must be a non-empty array")
        points, point_time = [], -math.inf
        for index, point in enumerate(raw_points):
            where = f"cursor.points[{index}]"
            if not isinstance(point, dict):
                errors.append(f"{where} must be an object")
                continue
            if not all(_finite(point.get(key)) for key in ("time", "x", "y")):
                errors.append(f"{where} requires finite time/x/y")
                continue
            if not 0 <= point["time"] <= scene_duration:
                errors.append(f"{where}.time must stay inside the scene")
            if point["time"] <= point_time + _EPS:
                errors.append(f"{where}.time must be strictly increasing")
            point_time = float(point["time"])
            ease_name = point.get("ease", "cubicInOut")
            if ease_name not in ONE_TAKE_EASES:
                errors.append(f"{where}.ease is invalid")
            points.append({"time": float(point["time"]), "x": float(point["x"]), "y": float(point["y"]), "ease": ease_name})
        raw_clicks = source.get("clicks") if isinstance(source.get("clicks"), list) else []
        clicks, previous_click_end = [], -math.inf
        for index, click in enumerate(raw_clicks):
            where = f"cursor.clicks[{index}]"
            if not isinstance(click, dict):
                errors.append(f"{where} must be an object")
                continue
            click_duration = click.get("duration", 0.36)
            if not _finite(click.get("time")) or not 0 <= click.get("time", -1) < scene_duration:
                errors.append(f"{where}.time must be finite and inside [0,duration)")
            if not _finite(click_duration) or click_duration <= 0:
                errors.append(f"{where}.duration must be finite and positive")
            if _finite(click.get("time")) and _finite(click_duration) and click["time"] + click_duration > scene_duration + _EPS:
                errors.append(f"{where} must finish inside the scene")
            if _finite(click.get("time")) and click["time"] < previous_click_end - _EPS:
                errors.append("cursor.clicks must be ordered and non-overlapping")
            if _finite(click.get("time")):
                previous_click_end = click["time"] + (click_duration if _finite(click_duration) and click_duration > 0 else 0.36)
                clicks.append({"time": float(click["time"]),
                               "duration": float(click_duration) if _finite(click_duration) and click_duration > 0 else 0.36})
        cursor = {
            "size": float(size) if _finite(size) and size > 0 else 42.0,
            "opacity": min(1.0, max(0.0, float(opacity))) if _finite(opacity) else 1.0,
            "points": points, "clicks": clicks,
        }

    if input_spec.get("viewport") is not None:
        try:
            clamp_window_box(input_spec["viewport"], canvas)
        except ValueError as exc:
            errors.append(str(exc))
    try:
        viewport = clamp_window_box(input_spec.get("viewport") or fullscreen_box(canvas), canvas)
    except ValueError:
        viewport = fullscreen_box(canvas)
    spec = {
        "version": 1, "id": input_spec.get("id"), "clock": "vo", "_normalized": True,
        "duration": scene_duration, "canvas": canvas, "backgroundRole": background_role,
        "elements": elements, "states": states, "cursor": cursor, "viewport": viewport,
    }
    return errors, spec


def validate_one_take_spec(spec: dict, duration: float | None = None) -> list[str]:
    """Return every configuration/timing error without requiring a renderer."""
    return _parse_one_take(spec, duration)[0]


def normalize_one_take(spec: dict) -> dict:
    if isinstance(spec, dict) and spec.get("_normalized"):
        return spec
    errors, normalized = _parse_one_take(spec)
    if errors:
        raise ValueError("Invalid one-take spec:\n - " + "\n - ".join(errors))
    return normalized


def load_project_one_take(project: str | Path) -> dict | None:
    """Load the optional companion plan with strict UTF-8 JSON and no NaN/Infinity."""
    path = Path(project).resolve() / "plan" / "one-take.json"
    if not path.is_file():
        return None
    def reject_constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")
    try:
        with path.open(encoding="utf-8") as handle:
            spec = json.load(handle, parse_constant=reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    return normalize_one_take(spec)


def _point_at(points, time, motion_mode):
    if time <= points[0]["time"]:
        return {"x": points[0]["x"], "y": points[0]["y"]}
    for index in range(len(points) - 1):
        a, b = points[index], points[index + 1]
        if time <= b["time"] + _EPS:
            raw = min(1.0, max(0.0, (time - a["time"]) / (b["time"] - a["time"])))
            progress = 1.0 if motion_mode == "reduced" else motion.ease(b["ease"], raw)
            return {"x": motion.lerp(a["x"], b["x"], progress), "y": motion.lerp(a["y"], b["y"], progress)}
    last = points[-1]
    return {"x": last["x"], "y": last["y"]}


def _screen_point(point, camera, viewport):
    return {
        "x": viewport["x"] + viewport["w"] / 2 + (point["x"] - camera["x"]) * camera["zoom"],
        "y": viewport["y"] + viewport["h"] / 2 + (point["y"] - camera["y"]) * camera["zoom"],
    }


def _aabb_of(element, screen):
    angle = math.radians(screen["rotation"])
    c, s = abs(math.cos(angle)), abs(math.sin(angle))
    w = (element["w"] * c + element["h"] * s) * screen["scale"]
    h = (element["w"] * s + element["h"] * c) * screen["scale"]
    return {"x": screen["x"] - w / 2, "y": screen["y"] - h / 2, "w": w, "h": h}


def one_take_state_at(spec: dict, time: float, *, motion_mode: str = "normal", viewport: dict | None = None) -> dict:
    """Pure absolute-time evaluation; repeated and reverse-order seeks return the same state."""
    if not _finite(time):
        raise ValueError("one-take time must be finite")
    if motion_mode not in {"normal", "reduced"}:
        raise ValueError("motion_mode must be 'normal' or 'reduced'")
    spec = normalize_one_take(spec)
    win = clamp_window_box(viewport or spec["viewport"], spec["canvas"])
    t = min(spec["duration"], max(0.0, float(time)))
    index = len(spec["states"]) - 2
    for i in range(len(spec["states"]) - 1):
        if t <= spec["states"][i + 1]["time"] + _EPS:
            index = i
            break
    source, target = spec["states"][index], spec["states"][index + 1]
    raw_progress = min(1.0, max(0.0, (t - source["time"]) / (target["time"] - source["time"])))
    progress = 1.0 if motion_mode == "reduced" else motion.ease(target["ease"], raw_progress)
    camera = {
        "x": motion.lerp(source["camera"]["x"], target["camera"]["x"], progress),
        "y": motion.lerp(source["camera"]["y"], target["camera"]["y"], progress),
        "zoom": math.exp(motion.lerp(math.log(source["camera"]["zoom"]), math.log(target["camera"]["zoom"]), progress)),
    }
    elements = []
    for element in spec["elements"]:
        a, b = source["elements"][element["id"]], target["elements"][element["id"]]
        transform = {key: motion.lerp(a[key], b[key], progress) for key in ("x", "y", "scale", "rotation", "opacity")}
        point = _screen_point(transform, camera, win)
        screen = {**point, "scale": transform["scale"] * camera["zoom"], "rotation": transform["rotation"]}
        elements.append({**element, **transform, "screen": screen, "aabb": _aabb_of(element, screen)})
    cursor = None
    if spec["cursor"] and spec["cursor"]["points"]:
        point = _point_at(spec["cursor"]["points"], t, motion_mode)
        press, click = False, None
        if motion_mode != "reduced":
            for click_index, event in enumerate(spec["cursor"]["clicks"]):
                if event["time"] <= t < event["time"] + event["duration"]:
                    click_progress = (t - event["time"]) / event["duration"]
                    press = t - event["time"] < min(0.14, event["duration"] / 2)
                    anchor = _point_at(spec["cursor"]["points"], event["time"], "normal")
                    click = {"index": click_index, "progress": click_progress, "opacity": 1 - click_progress,
                             "screen": _screen_point(anchor, camera, win)}
        cursor = {**point, "screen": _screen_point(point, camera, win), "press": press, "click": click}
    return {
        "time": t, "segmentIndex": index, "fromState": source["id"], "toState": target["id"],
        "rawProgress": raw_progress, "progress": progress, "camera": camera, "viewport": win,
        "elements": elements, "cursor": cursor,
    }


def _premultiply(sprite):
    out = sprite.astype(np.float32)
    out[..., :3] *= out[..., 3:4] / 255.0
    return out


def _paste(frame, sprite, cx, cy, scale=1.0, rotation=0.0, opacity=1.0):
    """Composite a premultiplied RGBA sprite around its centre, clipped to this frame's dimensions."""
    if opacity <= 0.003 or scale <= 0.003:
        return
    H, W = frame.shape[:2]
    h, w = sprite.shape[:2]
    c, s = math.cos(math.radians(rotation)), math.sin(math.radians(rotation))
    matrix = np.array([[c * scale, -s * scale, 0], [s * scale, c * scale, 0]], np.float32)
    matrix[0, 2] = cx - (matrix[0, 0] * w / 2 + matrix[0, 1] * h / 2)
    matrix[1, 2] = cy - (matrix[1, 0] * w / 2 + matrix[1, 1] * h / 2)
    points = np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float32)
    dest = points @ matrix[:, :2].T + matrix[:, 2]
    x0, x1 = max(int(dest[:, 0].min()) - 1, 0), min(int(dest[:, 0].max()) + 2, W)
    y0, y1 = max(int(dest[:, 1].min()) - 1, 0), min(int(dest[:, 1].max()) + 2, H)
    if x1 <= x0 or y1 <= y0:
        return
    matrix[0, 2] -= x0
    matrix[1, 2] -= y0
    warped = cv2.warpAffine(sprite, matrix, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    alpha = warped[..., 3:4] / 255.0 * opacity
    roi = frame[y0:y1, x0:x1]
    if roi.shape[2] == 4:
        destination_alpha = roi[..., 3:4] / 255.0
        roi[..., :3] = np.clip(warped[..., :3] * opacity + roi[..., :3] * (1 - alpha), 0, 255)
        roi[..., 3:4] = np.clip((alpha + destination_alpha * (1 - alpha)) * 255.0, 0, 255)
    else:
        roi[:] = np.clip(warped[..., :3] * opacity + roi * (1 - alpha), 0, 255)


def _shape_sprite(element):
    w, h = max(1, math.ceil(element["w"])), max(1, math.ceil(element["h"]))
    image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    fill = brand_rgb(element["role"]) + (255,)
    outline = brand_rgb(element["strokeRole"]) + (255,) if element["strokeWidth"] > 0 else None
    width = max(1, round(element["strokeWidth"])) if outline else 0
    box = (0, 0, w - 1, h - 1)
    if element["kind"] == "circle":
        draw.ellipse(box, fill=fill, outline=outline, width=width)
    else:
        radius = min(element["radius"], w / 2, h / 2)
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    return _premultiply(np.asarray(image))


def _text_sprite(element, direction):
    """Rasterize with the existing directed style/font decisions; One-Take owns only the outer transform."""
    if direction is None:
        raise ValueError(f"element {element['id']}: directed text requires a direction plan")
    w, h = max(1, math.ceil(element["w"])), max(1, math.ceil(element["h"]))
    sprite = np.zeros((h, w, 4), dtype=np.float32)
    style = captions.text_style_for(direction, element["scene"], element["fontRole"], element["id"])
    font = captions.font_for(direction, element["scene"], element["fontRole"], element["id"])
    transform = captions.caption_transform(style, 1.0, 1.0)
    lines = element["text"].split("\n")
    line_height = element["fontSize"] * 1.35
    for index, line in enumerate(lines):
        if not line:
            continue
        image = captions.text_sprite(
            line, int(round(element["fontSize"])), brand_rgb(element["role"]), element["rtl"], 0,
            brand_rgb("ink_shadow"), font["family"], font["weight"],
        )
        x = w / 2 + transform["x"] * element["fontSize"]
        y = h / 2 + (index - (len(lines) - 1) / 2) * line_height + transform["y"] * element["fontSize"]
        _paste(sprite, image, x, y, transform["scale"], transform["rotate"], transform["opacity"])
    return sprite


def _draw_cursor(frame, state, spec):
    cursor = state["cursor"]
    if not cursor or spec["cursor"]["opacity"] <= 0:
        return
    size = spec["cursor"]["size"]
    if cursor["click"]:
        click = cursor["click"]
        progress = click["progress"]
        radius = size * (0.6 + 2.0 * (1 - (1 - progress) ** 3)) * state["camera"]["zoom"]
        ring = Image.new("RGBA", (max(1, math.ceil(radius * 2 + 8)),) * 2, (0, 0, 0, 0))
        draw = ImageDraw.Draw(ring)
        draw.ellipse((4, 4, ring.width - 5, ring.height - 5), outline=brand_rgb("red") + (255,), width=max(2, round(size / 8)))
        _paste(frame, _premultiply(np.asarray(ring)), click["screen"]["x"], click["screen"]["y"],
               opacity=click["opacity"] * spec["cursor"]["opacity"])
    scale = state["camera"]["zoom"] * (0.86 if cursor["press"] else 1.0)
    w, h = max(2, math.ceil(size * 0.78)), max(2, math.ceil(size * 1.25))
    pointer = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
    draw = ImageDraw.Draw(pointer)
    points = [(2, 2), (2, h - 8), (w * 0.38, h * 0.70), (w * 0.60, h - 1),
              (w * 0.80, h - 5), (w * 0.58, h * 0.61), (w - 2, h * 0.60)]
    draw.polygon(points, fill=brand_rgb("paper") + (255,), outline=brand_rgb("ink") + (255,))
    _paste(frame, _premultiply(np.asarray(pointer)), cursor["screen"]["x"] + w * scale / 2,
           cursor["screen"]["y"] + h * scale / 2, scale=scale, opacity=spec["cursor"]["opacity"])


def create_one_take(spec: dict, *, direction=None) -> dict:
    """Pre-render static element faces, then expose pure state and native P render callables."""
    spec = normalize_one_take(spec)
    sprites = {}
    for element in spec["elements"]:
        sprites[element["id"]] = _text_sprite(element, direction) if element["kind"] == "text" else _shape_sprite(element)

    def state_at(t, *, motion_mode="normal", viewport=None):
        return one_take_state_at(spec, t, motion_mode=motion_mode, viewport=viewport)

    def render(t, *, motion_mode="normal", viewport=None):
        state = state_at(t, motion_mode=motion_mode, viewport=viewport)
        W, H = spec["canvas"]["w"], spec["canvas"]["h"]
        frame = np.empty((H, W, 3), dtype=np.float32)
        frame[:, :] = brand_rgb(spec["backgroundRole"])
        for element in state["elements"]:
            screen = element["screen"]
            _paste(frame, sprites[element["id"]], screen["x"], screen["y"],
                   screen["scale"], screen["rotation"], element["opacity"])
            if element["kind"] == "text" and layout_p.is_capturing() and element["opacity"] > 0.01:
                box = element["aabb"]
                win = state["viewport"]
                x0, y0 = max(box["x"], win["x"]), max(box["y"], win["y"])
                x1 = min(box["x"] + box["w"], win["x"] + win["w"])
                y1 = min(box["y"] + box["h"], win["y"] + win["h"])
                if x1 - x0 > 1 and y1 - y0 > 1:
                    layout_p.record_text(element["text"], {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0},
                                         box_id=element["id"], alpha=element["opacity"])
        _draw_cursor(frame, state, spec)
        pixels = np.clip(np.rint(frame), 0, 255).astype(np.uint8)
        win = state["viewport"]
        is_fullscreen = win["x"] == 0 and win["y"] == 0 and win["w"] == W and win["h"] == H
        if not is_fullscreen or win["r"] > 0:
            image = Image.fromarray(pixels)
            mask = Image.new("L", (W, H), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (win["x"], win["y"], win["x"] + win["w"], win["y"] + win["h"]),
                radius=win["r"], fill=255,
            )
            background = Image.new("RGB", (W, H), brand_rgb(spec["backgroundRole"]))
            pixels = np.asarray(Image.composite(image, background, mask)).copy()
        return pixels

    return {"spec": spec, "sprites": sprites, "state_at": state_at, "render": render}
