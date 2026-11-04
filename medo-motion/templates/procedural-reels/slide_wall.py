"""Phase 2B — deterministic 3D Slide Wall inside a Fixed Stage CONTENT window.

The spec uses absolute VO seconds, stable slide ids, explicit/generated grid placements and
look-at pinhole cameras. Rendering reuses space3d meshes/projection and brand roles; textures
are supplied by the caller so normal directed-text infrastructure remains authoritative.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import layout_p
import motion
import space3d
from stage import brand_hex, clamp_window_box, fullscreen_box, resolve_brand_role

WALL_EASES = {"linear", "cubicInOut", "cubicOut", "quintOut", "sineInOut", "expoInOut"}
_EPS = 1e-9


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _vec(value, size, default):
    if not isinstance(value, (list, tuple)) or len(value) != size or not all(_finite(v) for v in value):
        return list(default)
    return [float(v) for v in value]


def _canvas(raw):
    raw = raw if isinstance(raw, dict) else {}
    return {
        "w": int(raw.get("w", 1080)) if _finite(raw.get("w", 1080)) else 1080,
        "h": int(raw.get("h", 1920)) if _finite(raw.get("h", 1920)) else 1920,
        "fps": float(raw.get("fps", 30)) if _finite(raw.get("fps", 30)) else 30.0,
    }


def _endpoint(raw, slide_ids, errors, where):
    raw = raw if isinstance(raw, dict) else {}
    kind = raw.get("type")
    if kind == "overview":
        return {"type": "overview"}
    if kind == "slide" and raw.get("slide") in slide_ids:
        return {"type": "slide", "slide": raw["slide"]}
    errors.append(f"{where}: expected {{'type':'overview'}} or {{'type':'slide','slide':<known id>}}")
    return {"type": "overview"}


def _endpoint_key(endpoint):
    return "overview" if endpoint["type"] == "overview" else f"slide:{endpoint['slide']}"


def validate_slide_wall_spec(spec: dict, duration: float | None = None) -> list[str]:
    """Return all configuration/timing errors; no renderer is needed to run this gate."""
    errors: list[str] = []
    if not isinstance(spec, dict):
        return ["spec must be an object"]
    if spec.get("version") != 1:
        errors.append("version must be 1")
    if not isinstance(spec.get("id"), str) or not spec.get("id", "").strip():
        errors.append("id must be a non-empty stable string")
    if spec.get("clock", "vo") != "vo":
        errors.append("clock must be 'vo'; timeline values are absolute VO seconds")
    raw_canvas = spec.get("canvas", {})
    if raw_canvas is not None and not isinstance(raw_canvas, dict):
        errors.append("canvas must be an object")
        raw_canvas = {}
    raw_canvas = raw_canvas or {}
    for key, default in (("w", 1080), ("h", 1920), ("fps", 30)):
        if not _finite(raw_canvas.get(key, default)):
            errors.append(f"canvas.{key} must be finite")
    canvas = _canvas(raw_canvas)
    if canvas["w"] <= 0 or canvas["h"] <= 0 or canvas["fps"] <= 0:
        errors.append("canvas w/h/fps must be finite and positive")
    raw_camera = spec.get("camera", {})
    if raw_camera is not None and not isinstance(raw_camera, dict):
        errors.append("camera must be an object")
        raw_camera = {}
    raw_camera = raw_camera or {}
    if not _finite(raw_camera.get("fov", 30)) or not 5 <= float(raw_camera.get("fov", 30)) <= 120:
        errors.append("camera.fov must be finite and within [5,120] degrees")
    if spec.get("viewport") is not None:
        try:
            clamp_window_box(spec["viewport"], canvas, label="viewport")
        except ValueError as exc:
            errors.append(str(exc))

    layout = spec.get("layout", {})
    if not isinstance(layout, dict):
        errors.append("layout must be an object")
        layout = {}
    raw_default_size = layout.get("slideSize", [3.2, 2.0])
    default_size = _vec(raw_default_size, 2, [3.2, 2.0])
    if (not isinstance(raw_default_size, (list, tuple)) or len(raw_default_size) != 2
            or not all(_finite(v) for v in raw_default_size) or any(v <= 0 for v in default_size)):
        errors.append("layout.slideSize must contain two finite positive values")
    raw_gap = layout.get("gap", [0.4, 0.4])
    gap = _vec(raw_gap, 2, [0.4, 0.4])
    if (not isinstance(raw_gap, (list, tuple)) or len(raw_gap) != 2
            or not all(_finite(v) for v in raw_gap) or any(v < 0 for v in gap)):
        errors.append("layout.gap must contain two finite non-negative values")
    depth = layout.get("depth", 0.08)
    if not _finite(depth) or depth <= 0:
        errors.append("layout.depth must be finite and positive")
        depth = 0.08
    if "preventOverlap" in layout and not isinstance(layout["preventOverlap"], bool):
        errors.append("layout.preventOverlap must be boolean")
    columns = layout.get("gridColumns", 3)
    if not isinstance(columns, int) or isinstance(columns, bool) or columns <= 0:
        errors.append("layout.gridColumns must be a positive integer")
        columns = 3
    raw_origin = layout.get("origin", [0, 0, 0])
    origin = _vec(raw_origin, 3, [0, 0, 0])
    if not isinstance(raw_origin, (list, tuple)) or len(raw_origin) != 3 or not all(_finite(v) for v in raw_origin):
        errors.append("layout.origin must contain three finite values")

    try:
        resolve_brand_role(spec.get("backgroundRole", "ink_shadow"), "backgroundRole")
    except ValueError as exc:
        errors.append(str(exc))
    raw_slides = spec.get("slides")
    if not isinstance(raw_slides, list) or not raw_slides:
        errors.append("slides must be a non-empty array")
        raw_slides = []
    if len(raw_slides) > 64:
        errors.append("slides supports at most 64 entries per wall")
    slides, slide_ids = [], set()
    rows = math.ceil(len(raw_slides) / columns) if raw_slides else 0
    for index, raw in enumerate(raw_slides):
        if not isinstance(raw, dict):
            errors.append(f"slides[{index}] must be an object")
            continue
        sid = raw.get("id")
        if not isinstance(sid, str) or not sid.strip():
            errors.append(f"slides[{index}].id must be a non-empty stable string")
            sid = f"invalid-{index}"
        elif sid in slide_ids:
            errors.append(f"duplicate slide id: {sid}")
        slide_ids.add(sid)
        for role_key, default in (("surfaceRole", "paper"), ("edgeRole", "gray_2"), ("accentRole", "red")):
            try:
                resolve_brand_role(raw.get(role_key, default), f"slide {sid}.{role_key}")
            except ValueError as exc:
                errors.append(str(exc))
        raw_size = raw.get("size", default_size)
        size = _vec(raw_size, 2, default_size)
        if (not isinstance(raw_size, (list, tuple)) or len(raw_size) != 2
                or not all(_finite(v) for v in raw_size) or any(v <= 0 for v in size)):
            errors.append(f"slide {sid}: size must contain two finite positive values")
        row, col = divmod(index, columns)
        generated = [
            origin[0] + (col - (columns - 1) / 2) * (default_size[0] + gap[0]),
            origin[1] + ((rows - 1) / 2 - row) * (default_size[1] + gap[1]),
            origin[2],
        ]
        position = _vec(raw.get("position", generated), 3, generated)
        if "position" in raw and position == generated and raw.get("position") != generated:
            # Equality alone cannot identify all bad explicit values, so check the original too.
            original = raw.get("position")
            if not isinstance(original, (list, tuple)) or len(original) != 3 or not all(_finite(v) for v in original):
                errors.append(f"slide {sid}: position must contain three finite values")
        rotation = _vec(raw.get("rotation", [0, 0, 0]), 3, [0, 0, 0])
        if not isinstance(raw.get("rotation", [0, 0, 0]), (list, tuple)) or len(raw.get("rotation", [0, 0, 0])) != 3 or not all(_finite(v) for v in raw.get("rotation", [0, 0, 0])):
            errors.append(f"slide {sid}: rotation must contain three finite radian values")
        slides.append({
            "id": sid, "size": size, "position": position, "rotation": rotation,
            "surfaceRole": raw.get("surfaceRole", "paper"),
            "edgeRole": raw.get("edgeRole", "gray_2"),
            "accentRole": raw.get("accentRole", "red"),
        })

    bounds = layout.get("bounds")
    parsed_bounds = None
    if bounds is not None:
        if not isinstance(bounds, dict):
            errors.append("layout.bounds must be an object with min/max vectors")
        else:
            lo = _vec(bounds.get("min"), 3, [0, 0, 0])
            hi = _vec(bounds.get("max"), 3, [0, 0, 0])
            if (not isinstance(bounds.get("min"), (list, tuple)) or len(bounds.get("min", [])) != 3
                    or not all(_finite(v) for v in bounds.get("min", []))
                    or not isinstance(bounds.get("max"), (list, tuple)) or len(bounds.get("max", [])) != 3
                    or not all(_finite(v) for v in bounds.get("max", []))):
                errors.append("layout.bounds min/max must contain three finite values")
            elif any(lo[i] >= hi[i] for i in range(3)):
                errors.append("layout.bounds min must be strictly below max on every axis")
            else:
                parsed_bounds = (lo, hi)
    if parsed_bounds:
        lo, hi = parsed_bounds
        for slide in slides:
            mesh = _slide_mesh(slide, float(depth))
            if any(any(v[i] < lo[i] - _EPS or v[i] > hi[i] + _EPS for i in range(3)) for v in mesh["verts"]):
                errors.append(f"slide {slide['id']}: transformed slab leaves layout.bounds")
    if layout.get("preventOverlap", True):
        footprints = [_slide_xy_aabb(slide, depth) for slide in slides]
        for i, a in enumerate(slides):
            for j, b in enumerate(slides[i + 1:], start=i + 1):
                # Conservative transformed-slab XY AABBs: rotation and depth are included, and
                # touching edges are allowed. Set preventOverlap=false for intentional stacks.
                aa, bb = footprints[i], footprints[j]
                if (aa[0] < bb[1] - _EPS and bb[0] < aa[1] - _EPS
                        and aa[2] < bb[3] - _EPS and bb[2] < aa[3] - _EPS):
                    errors.append(f"slides {a['id']} and {b['id']} overlap in the required XY separation contract")

    camera = spec.get("camera", {})
    overview = camera.get("overview") if isinstance(camera, dict) else None
    if overview is not None:
        if not isinstance(overview, dict):
            errors.append("camera.overview must be an object")
        else:
            for key, default in (("position", [0, 0, 10]), ("target", [0, 0, 0]), ("up", [0, 1, 0])):
                value = overview.get(key, default)
                if not isinstance(value, (list, tuple)) or len(value) != 3 or not all(_finite(v) for v in value):
                    errors.append(f"camera.overview.{key} must contain three finite values")
            if not _finite(overview.get("roll", 0)):
                errors.append("camera.overview.roll must be finite radians")
            try:
                space3d.look_camera(
                    _vec(overview.get("position", [0, 0, 10]), 3, [0, 0, 10]),
                    _vec(overview.get("target", [0, 0, 0]), 3, [0, 0, 0]),
                    float(spec.get("camera", {}).get("fov", 30)),
                    float(overview.get("roll", 0)), _vec(overview.get("up", [0, 1, 0]), 3, [0, 1, 0]),
                )
            except ValueError as exc:
                errors.append(f"camera.overview: {exc}")

    timeline = spec.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        errors.append("timeline must be a non-empty array")
        timeline = []
    previous_end, previous_key = None, None
    for index, raw in enumerate(timeline):
        where = f"timeline[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{where} must be an object")
            continue
        mode = raw.get("mode")
        if mode not in {"overview", "slide", "move"}:
            errors.append(f"{where}.mode must be overview, slide or move")
            continue
        start, end = raw.get("start"), raw.get("end")
        if not _finite(start) or not _finite(end) or start < 0 or end <= start:
            errors.append(f"{where} requires finite 0 <= start < end")
            continue
        if index == 0 and abs(start) > _EPS:
            errors.append("timeline must start at absolute VO time 0")
        if previous_end is not None:
            if start < previous_end - _EPS:
                errors.append(f"{where} overlaps the preceding segment")
            elif start > previous_end + _EPS:
                errors.append(f"{where} leaves a timing gap after the preceding segment")
        if mode == "move":
            source = _endpoint(raw.get("from"), slide_ids, errors, f"{where}.from")
            target = _endpoint(raw.get("to"), slide_ids, errors, f"{where}.to")
            if _endpoint_key(source) == _endpoint_key(target):
                errors.append(f"{where} must move between two different endpoints")
            ease = raw.get("ease", "cubicInOut")
            if ease not in WALL_EASES:
                errors.append(f"{where}.ease must be one of {sorted(WALL_EASES)}")
            if not _finite(raw.get("lift", 0)) or raw.get("lift", 0) < 0:
                errors.append(f"{where}.lift must be finite and non-negative")
            current_key = _endpoint_key(target)
            if previous_key is not None and _endpoint_key(source) != previous_key:
                errors.append(f"{where}.from must equal the preceding segment endpoint ({previous_key})")
        else:
            if mode == "slide" and raw.get("slide") not in slide_ids:
                errors.append(f"{where}.slide must reference a known slide id")
                current_key = "overview"
            else:
                current_key = "overview" if mode == "overview" else f"slide:{raw['slide']}"
            if previous_key is not None and current_key != previous_key:
                errors.append(f"{where} must start at the preceding segment endpoint ({previous_key})")
        previous_end, previous_key = float(end), current_key
    if duration is not None:
        if not _finite(duration) or duration <= 0:
            errors.append("duration must be finite and positive")
        elif timeline and previous_end is not None and abs(previous_end - float(duration)) > _EPS:
            errors.append(f"timeline end {previous_end} must equal scene/VO duration {duration}")
    return errors


def normalize_slide_wall(spec: dict) -> dict:
    if isinstance(spec, dict) and spec.get("_normalized"):
        return spec
    errors = validate_slide_wall_spec(spec)
    if errors:
        raise ValueError("Invalid slide-wall spec:\n - " + "\n - ".join(errors))
    canvas = _canvas(spec.get("canvas"))
    viewport = spec.get("viewport") or fullscreen_box(canvas)
    viewport = clamp_window_box(viewport, canvas)
    layout = spec.get("layout", {})
    default_size = [float(v) for v in layout.get("slideSize", [3.2, 2.0])]
    gap = [float(v) for v in layout.get("gap", [0.4, 0.4])]
    columns = int(layout.get("gridColumns", 3))
    origin = [float(v) for v in layout.get("origin", [0, 0, 0])]
    rows = math.ceil(len(spec["slides"]) / columns)
    slides = []
    for index, raw in enumerate(spec["slides"]):
        row, col = divmod(index, columns)
        generated = [
            origin[0] + (col - (columns - 1) / 2) * (default_size[0] + gap[0]),
            origin[1] + ((rows - 1) / 2 - row) * (default_size[1] + gap[1]),
            origin[2],
        ]
        slides.append({
            "id": raw["id"],
            "size": [float(v) for v in raw.get("size", default_size)],
            "position": [float(v) for v in raw.get("position", generated)],
            "rotation": [float(v) for v in raw.get("rotation", [0, 0, 0])],
            "surfaceRole": resolve_brand_role(raw.get("surfaceRole", "paper")),
            "edgeRole": resolve_brand_role(raw.get("edgeRole", "gray_2")),
            "accentRole": resolve_brand_role(raw.get("accentRole", "red")),
        })
    slide_by_id = {slide["id"]: slide for slide in slides}
    timeline = []
    for raw in spec["timeline"]:
        segment = {"mode": raw["mode"], "start": float(raw["start"]), "end": float(raw["end"])}
        if raw["mode"] == "move":
            segment.update({
                "from": dict(raw["from"]), "to": dict(raw["to"]),
                "ease": raw.get("ease", "cubicInOut"), "lift": float(raw.get("lift", 0)),
            })
        elif raw["mode"] == "slide":
            segment["slide"] = raw["slide"]
        timeline.append(segment)
    camera_raw = spec.get("camera", {})
    overview = camera_raw.get("overview")
    return {
        "version": 1, "id": spec["id"], "clock": "vo", "_normalized": True,
        "canvas": canvas, "viewport": viewport,
        "backgroundRole": resolve_brand_role(spec.get("backgroundRole", "ink_shadow")),
        "layout": {
            "slideSize": default_size, "gap": gap, "gridColumns": columns, "origin": origin,
            "depth": float(layout.get("depth", 0.08)),
            "preventOverlap": bool(layout.get("preventOverlap", True)),
            "bounds": layout.get("bounds"),
        },
        "slides": slides, "slideById": slide_by_id,
        "camera": {"fov": float(camera_raw.get("fov", 30)), "overview": dict(overview) if overview else None},
        "timeline": timeline,
    }


def load_project_slide_wall(project: str | Path) -> dict | None:
    """Load the optional companion plan with strict JSON parsing (UTF-8, no NaN)."""
    path = Path(project).resolve() / "plan" / "slide-wall.json"
    if not path.is_file():
        return None
    def reject_constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")
    try:
        with path.open(encoding="utf-8") as handle:
            spec = json.load(handle, parse_constant=reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    return normalize_slide_wall(spec)


def _slide_mesh(slide: dict, depth: float):
    w, h = slide["size"]
    rx, ry, rz = slide["rotation"]
    return space3d.transform(space3d.box(w, h, depth), rx=rx, ry=ry, rz=rz, move=slide["position"])


def _slide_xy_aabb(slide: dict, depth: float):
    verts = _slide_mesh(slide, depth)["verts"]
    xs, ys = [v[0] for v in verts], [v[1] for v in verts]
    return min(xs), max(xs), min(ys), max(ys)


def _window(spec, viewport):
    return clamp_window_box(viewport or spec["viewport"], spec["canvas"])


def _overview_state(spec, viewport):
    custom = spec["camera"].get("overview")
    if custom:
        return {
            "position": [float(v) for v in custom.get("position", [0, 0, 10])],
            "target": [float(v) for v in custom.get("target", [0, 0, 0])],
            "up": [float(v) for v in custom.get("up", [0, 1, 0])],
            "roll": float(custom.get("roll", 0)),
        }
    verts = [v for slide in spec["slides"] for v in _slide_mesh(slide, spec["layout"]["depth"])["verts"]]
    lo = [min(v[i] for v in verts) for i in range(3)]
    hi = [max(v[i] for v in verts) for i in range(3)]
    center = [(lo[i] + hi[i]) / 2 for i in range(3)]
    width, height = hi[0] - lo[0], hi[1] - lo[1]
    H, tan_half = spec["canvas"]["h"], math.tan(math.radians(spec["camera"]["fov"]) / 2)
    distance = max(width * H / (2 * viewport["w"] * tan_half), height * H / (2 * viewport["h"] * tan_half))
    distance = distance * 1.15 + max(0.0, center[2] - lo[2]) + spec["layout"]["depth"]
    return {"position": [center[0], center[1], center[2] + distance], "target": center,
            "up": [0.0, 1.0, 0.0], "roll": 0.0}


def _focus_state(spec, slide_id, viewport):
    slide = spec["slideById"][slide_id]
    rotation = slide["rotation"]
    right = space3d.rotate([1, 0, 0], *rotation)
    up = space3d.rotate([0, 1, 0], *rotation)
    normal = space3d.rotate([0, 0, 1], *rotation)
    front_center = [slide["position"][i] + normal[i] * spec["layout"]["depth"] / 2 for i in range(3)]
    w, h = slide["size"]
    W, H = spec["canvas"]["w"], spec["canvas"]["h"]
    tan_half = math.tan(math.radians(spec["camera"]["fov"]) / 2)
    distance = max(w * H / (2 * viewport["w"] * tan_half), h * H / (2 * viewport["h"] * tan_half))
    focal = (H / 2) / tan_half
    vx, vy = viewport["x"] + viewport["w"] / 2, viewport["y"] + viewport["h"] / 2
    position = [
        front_center[i] + normal[i] * distance
        + right[i] * ((W / 2 - vx) * distance / focal)
        + up[i] * ((vy - H / 2) * distance / focal)
        for i in range(3)
    ]
    target = [position[i] - normal[i] * distance for i in range(3)]
    return {"position": position, "target": target, "up": up, "roll": 0.0}


def _endpoint_state(spec, endpoint, viewport):
    return _overview_state(spec, viewport) if endpoint["type"] == "overview" else _focus_state(spec, endpoint["slide"], viewport)


def _segment_at(spec, t):
    for index, segment in enumerate(spec["timeline"]):
        if segment["start"] - _EPS <= t <= segment["end"] + _EPS:
            return index, segment
    return (0, spec["timeline"][0]) if t < spec["timeline"][0]["start"] else (len(spec["timeline"]) - 1, spec["timeline"][-1])


def _camera_quaternion(camera):
    """Unit quaternion for the right-handed camera basis (right, up, back=-forward)."""
    right, up = camera["right"], camera["up"]
    back = [-v for v in camera["fwd"]]
    m00, m01, m02 = right[0], up[0], back[0]
    m10, m11, m12 = right[1], up[1], back[1]
    m20, m21, m22 = right[2], up[2], back[2]
    trace = m00 + m11 + m22
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        q = (s / 4, (m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s)
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2
        q = ((m21 - m12) / s, s / 4, (m01 + m10) / s, (m02 + m20) / s)
    elif m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2
        q = ((m02 - m20) / s, (m01 + m10) / s, s / 4, (m12 + m21) / s)
    else:
        s = math.sqrt(1.0 + m22 - m00 - m11) * 2
        q = ((m10 - m01) / s, (m02 + m20) / s, (m12 + m21) / s, s / 4)
    length = math.sqrt(sum(v * v for v in q))
    return tuple(v / length for v in q)


def _quaternion_slerp(a, b, t):
    """Shortest-arc SLERP; normalized lerp avoids sin(theta) loss when nearly aligned."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    if dot < 0:
        b = tuple(-v for v in b)
        dot = -dot
    dot = max(-1.0, min(1.0, dot))
    if dot > 0.9995:
        q = tuple(x + (y - x) * t for x, y in zip(a, b, strict=True))
    else:
        theta = math.acos(dot)
        sin_theta = math.sin(theta)
        wa, wb = math.sin((1 - t) * theta) / sin_theta, math.sin(t * theta) / sin_theta
        q = tuple(wa * x + wb * y for x, y in zip(a, b, strict=True))
    length = math.sqrt(sum(v * v for v in q))
    return tuple(v / length for v in q)


def _quaternion_rotate(q, v):
    w, x, y, z = q
    t = (2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0]))
    return (
        v[0] + w * t[0] + y * t[2] - z * t[1],
        v[1] + w * t[1] + z * t[0] - x * t[2],
        v[2] + w * t[2] + x * t[1] - y * t[0],
    )


def _interpolate_camera(source, target, progress, fov):
    """Preserve near-aligned legacy moves; SLERP larger orientations independently of position."""
    source_camera = space3d.look_camera(source["position"], source["target"], fov, 0, source["up"])
    target_camera = space3d.look_camera(target["position"], target["target"], fov, 0, target["up"])
    source_q, target_q = _camera_quaternion(source_camera), _camera_quaternion(target_camera)
    delta_roll = math.atan2(math.sin(target["roll"] - source["roll"]), math.cos(target["roll"] - source["roll"]))
    roll = source["roll"] + delta_roll * progress
    if abs(sum(a * b for a, b in zip(source_q, target_q, strict=True))) > 0.9995:
        state = {key: [source[key][i] + (target[key][i] - source[key][i]) * progress for i in range(3)]
                 for key in ("position", "target", "up")}
        return space3d.look_camera(state["position"], state["target"], fov, roll, state["up"])
    q = _quaternion_slerp(source_q, target_q, progress)
    right = _quaternion_rotate(q, (1, 0, 0))
    up = _quaternion_rotate(q, (0, 1, 0))
    back = _quaternion_rotate(q, (0, 0, 1))
    if roll:
        c, s = math.cos(roll), math.sin(roll)
        right, up = (
            tuple(right[i] * c + up[i] * s for i in range(3)),
            tuple(-right[i] * s + up[i] * c for i in range(3)),
        )
    return {
        "pos": tuple(source["position"][i] + (target["position"][i] - source["position"][i]) * progress for i in range(3)),
        "fwd": tuple(-v for v in back), "right": right, "up": up, "fov": math.radians(fov),
        "target": tuple(source["target"][i] + (target["target"][i] - source["target"][i]) * progress for i in range(3)),
        "roll": roll,
    }


def _camera_at(spec, t, motion_mode, viewport):
    index, segment = _segment_at(spec, t)
    mode = segment["mode"]
    camera = None
    if mode == "overview":
        state = _overview_state(spec, viewport)
        progress = 0.0
    elif mode == "slide":
        state = _focus_state(spec, segment["slide"], viewport)
        progress = 0.0
    else:
        raw = max(0.0, min(1.0, (t - segment["start"]) / (segment["end"] - segment["start"])))
        source = _endpoint_state(spec, segment["from"], viewport)
        target = _endpoint_state(spec, segment["to"], viewport)
        if motion_mode == "reduced":
            state, progress = target, 1.0
        elif raw <= 0:
            state, progress = source, 0.0
        elif raw >= 1:
            state, progress = target, 1.0
        else:
            progress = motion.ease(segment["ease"], raw)
            camera = _interpolate_camera(source, target, progress, spec["camera"]["fov"])
            camera["pos"] = (*camera["pos"][:2], camera["pos"][2] + math.sin(math.pi * raw) * segment["lift"])
    if camera is None:
        camera = space3d.look_camera(state["position"], state["target"], spec["camera"]["fov"], state["roll"], state["up"])
    return camera, index, mode, progress


def slide_wall_state_at(spec: dict, t: float, *, motion_mode: str = "normal", viewport: dict | None = None) -> dict:
    """Pure absolute-time evaluation: camera + sorted projected slides, with no global state."""
    if not _finite(t):
        raise ValueError("slide-wall time must be finite")
    if motion_mode not in {"normal", "reduced"}:
        raise ValueError("motion_mode must be 'normal' or 'reduced'")
    spec = normalize_slide_wall(spec)
    viewport = _window(spec, viewport)
    camera, index, mode, progress = _camera_at(spec, float(t), motion_mode, viewport)
    items = []
    for slide in spec["slides"]:
        mesh = _slide_mesh(slide, spec["layout"]["depth"])
        projected = space3d.project(mesh["verts"], camera, spec["canvas"]["w"], spec["canvas"]["h"])
        front = [projected[i] for i in (3, 2, 1, 0)]  # texture TL, TR, BR, BL
        normal = space3d.face_normal(mesh, mesh["faces"][0])
        to_camera = space3d._sub(camera["pos"], slide["position"])
        visible = (space3d._dot(normal, to_camera) > 0.001
                   and all(math.isfinite(v) for point in front for v in point)
                   and all(point[2] > 0 for point in front))
        depth = space3d.project([slide["position"]], camera, spec["canvas"]["w"], spec["canvas"]["h"])[0][2]
        xs, ys = [p[0] for p in front], [p[1] for p in front]
        items.append({
            "slide": slide, "mesh": mesh, "projected": projected, "front": front,
            "visible": visible, "depth": depth,
            "aabb": {"x": min(xs), "y": min(ys), "w": max(xs) - min(xs), "h": max(ys) - min(ys)} if visible else None,
        })
    items.sort(key=lambda item: item["depth"], reverse=True)
    return {"time": float(t), "camera": camera, "segmentIndex": index, "mode": mode,
            "progress": progress, "viewport": viewport, "slides": items}


def slide_homography(src_w: float, src_h: float, quad) -> list[list[float]]:
    """Map texture pixels (TL,TR,BR,BL) to a projected quad; shared with the R CSS adapter."""
    x0, y0 = float(quad[0][0]), float(quad[0][1])
    x1, y1 = float(quad[1][0]), float(quad[1][1])
    x2, y2 = float(quad[2][0]), float(quad[2][1])
    x3, y3 = float(quad[3][0]), float(quad[3][1])
    dx1, dx2, dx3 = x1 - x2, x3 - x2, x0 - x1 + x2 - x3
    dy1, dy2, dy3 = y1 - y2, y3 - y2, y0 - y1 + y2 - y3
    den = dx1 * dy2 - dx2 * dy1
    g = (dx3 * dy2 - dx2 * dy3) / den if abs(den) > _EPS else 0.0
    h = (dx1 * dy3 - dx3 * dy1) / den if abs(den) > _EPS else 0.0
    a, b, c = x1 - x0 + g * x1, x3 - x0 + h * x3, x0
    d, e, f = y1 - y0 + g * y1, y3 - y0 + h * y3, y0
    return [[a / src_w, b / src_h, c], [d / src_w, e / src_h, f], [g / src_w, h / src_h, 1.0]]


def create_slide_wall(spec: dict, slide_renderer, *, slide_layout=None, texture_width: int = 540) -> dict:
    """Pre-render static slide faces once, then return pure state/render callables.

    `slide_renderer(slide, width, height)` returns an RGBA numpy image. The scene owns all text,
    fonts and brand choices. Optional `slide_layout` returns conservative texture-space text rects
    for projection into the existing screen-space layout audit. This adapter owns wall geometry.
    """
    spec = normalize_slide_wall(spec)
    if not callable(slide_renderer):
        raise TypeError("slide_renderer must be callable")
    if not isinstance(texture_width, int) or texture_width < 32:
        raise ValueError("texture_width must be an integer >= 32")
    textures = {}
    for slide in spec["slides"]:
        height = max(1, int(round(texture_width * slide["size"][1] / slide["size"][0])))
        image = np.asarray(slide_renderer(slide, texture_width, height), dtype=np.uint8)
        if image.ndim != 3 or image.shape[:2] != (height, texture_width) or image.shape[2] != 4:
            raise ValueError(f"slide {slide['id']}: renderer must return RGBA shape ({height},{texture_width},4)")
        textures[slide["id"]] = image.copy()
    layouts = {}
    for slide in spec["slides"]:
        texture = textures[slide["id"]]
        th, tw = texture.shape[:2]
        rects = slide_layout(slide, tw, th) if slide_layout else []
        if not isinstance(rects, (list, tuple)):
            raise ValueError(f"slide {slide['id']}: slide_layout must return an array")
        for rect in rects:
            if (not isinstance(rect, dict) or not isinstance(rect.get("id"), str)
                    or not all(_finite(rect.get(key)) for key in ("x", "y", "w", "h"))
                    or rect["w"] <= 0 or rect["h"] <= 0):
                raise ValueError(f"slide {slide['id']}: invalid conservative text rect")
        layouts[slide["id"]] = [dict(rect) for rect in rects]

    def state_at(t, *, motion_mode="normal", viewport=None):
        return slide_wall_state_at(spec, t, motion_mode=motion_mode, viewport=viewport)

    def render(t, *, motion_mode="normal", viewport=None):
        state = state_at(t, motion_mode=motion_mode, viewport=viewport)
        W, H = spec["canvas"]["w"], spec["canvas"]["h"]
        background = space3d.to_rgb(brand_hex(spec["backgroundRole"]))
        frame = np.empty((H, W, 3), dtype=np.uint8)
        frame[:, :] = background
        for item in state["slides"]:
            if not item["visible"]:
                continue
            slide = item["slide"]
            colors = {role: brand_hex(slide["edgeRole" if role != "front" else "surfaceRole"])
                      for role in ("front", "left", "top", "right", "bottom", "back")}
            pil = Image.fromarray(frame)
            space3d.draw_mesh(ImageDraw.Draw(pil), item["mesh"], state["camera"], W, H,
                              colors=colors, ambient=1.0)
            frame = np.asarray(pil).copy()
            front = item["front"]
            x0 = max(0, int(math.floor(min(p[0] for p in front))) - 1)
            y0 = max(0, int(math.floor(min(p[1] for p in front))) - 1)
            x1 = min(W, int(math.ceil(max(p[0] for p in front))) + 2)
            y1 = min(H, int(math.ceil(max(p[1] for p in front))) + 2)
            if x1 <= x0 or y1 <= y0:
                continue
            texture = textures[slide["id"]]
            th, tw = texture.shape[:2]
            matrix = np.asarray(slide_homography(tw, th, front), dtype=np.float64)
            matrix[0, 2] -= x0
            matrix[1, 2] -= y0
            segment = spec["timeline"][state["segmentIndex"]]
            if state["mode"] == "slide":
                active_ids = {segment["slide"]}
            elif state["mode"] == "move":
                active_ids = {endpoint["slide"] for endpoint in (segment["from"], segment["to"])
                              if endpoint["type"] == "slide"}
            else:
                active_ids = set(spec["slideById"])
            if layout_p.is_capturing() and slide["id"] in active_ids:
                for rect in layouts[slide["id"]]:
                    points = []
                    for px, py in ((rect["x"], rect["y"]), (rect["x"] + rect["w"], rect["y"]),
                                   (rect["x"] + rect["w"], rect["y"] + rect["h"]), (rect["x"], rect["y"] + rect["h"])):
                        # `matrix` is translated into the warp bounding box; add the origin back for QA.
                        denominator = matrix[2, 0] * px + matrix[2, 1] * py + matrix[2, 2]
                        points.append(((matrix[0, 0] * px + matrix[0, 1] * py + matrix[0, 2]) / denominator + x0,
                                       (matrix[1, 0] * px + matrix[1, 1] * py + matrix[1, 2]) / denominator + y0))
                    xs, ys = [point[0] for point in points], [point[1] for point in points]
                    win = state["viewport"]
                    bx0, by0 = max(min(xs), win["x"]), max(min(ys), win["y"])
                    bx1, by1 = min(max(xs), win["x"] + win["w"]), min(max(ys), win["y"] + win["h"])
                    if bx1 - bx0 > 1 and by1 - by0 > 1:
                        layout_p.record_text(
                            str(rect.get("text", rect["id"])),
                            {"x": bx0, "y": by0, "w": bx1 - bx0, "h": by1 - by0},
                            box_id=f"{slide['id']}/{rect['id']}", zone=rect.get("zone", "content"), alpha=1.0,
                        )
            warped = cv2.warpPerspective(texture, matrix, (x1 - x0, y1 - y0),
                                         flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                         borderValue=(0, 0, 0, 0))
            alpha = warped[:, :, 3:4].astype(np.float32) / 255.0
            roi = frame[y0:y1, x0:x1].astype(np.float32)
            frame[y0:y1, x0:x1] = np.clip(
                warped[:, :, :3].astype(np.float32) * alpha + roi * (1.0 - alpha), 0, 255
            ).astype(np.uint8)
        return frame

    return {"spec": spec, "textures": textures, "state_at": state_at, "render": render}
