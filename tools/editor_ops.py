#!/usr/bin/env python3
"""Pure editing operations the local editor calls — one place, no HTTP in the logic.

`unified_project_edit` covers the timeline operations (split/trim/move/ripple) and
`unified_project_author` covers structure (tracks, clips, duration). The editor needs a few more
verbs — edit a clip's fields, add a text clip, attach media, put a keyframe on a curve — and this
module is where they live so they can be tested without a browser or a socket.

Every function takes a project, returns a new one and validates the result: an edit that would
produce a project the checker refuses raises `ValueError` with the checker's own message.
"""
from __future__ import annotations

import copy

from unified_project_author import add_clip, add_track, delete_clip, remove_asset, remove_track, set_duration
from unified_project_check import validate
from unified_project_effect_edit import add_effect, remove_curve, remove_effect, replace_effect, set_curve
from unified_project_edit import move_clip, ripple_delete, split_clip, trim_clip

__all__ = [
    "add_asset", "add_clip", "add_effect", "add_keyframe", "add_text", "add_text_clip", "add_track",
    "delete_clip", "move_clip", "remove_asset", "remove_effect", "remove_keyframe",
    "remove_track", "ripple_delete", "set_effect_value", "set_project", "set_text",
    "split_clip", "trim_clip", "update_clip",
]


def _checked(project):
    errors = validate(project)
    if errors:
        raise ValueError("project would be invalid: " + "; ".join(errors))
    return project


def _find_clip(project, clip_id):
    for track_index, track in enumerate(project["tracks"]):
        for clip_index, clip in enumerate(track["clips"]):
            if clip["id"] == clip_id:
                return track_index, clip_index, clip
    raise ValueError(f"unknown clip {clip_id!r}")


def update_clip(project, clip_id, *, start=None, duration=None, source_in=None, speed=None):
    """Change a clip's position, length, source offset or speed in one validated step."""
    result = copy.deepcopy(project)
    _, _, clip = _find_clip(result, clip_id)
    if start is not None:
        clip["start"] = int(start)
    if duration is not None:
        clip["duration"] = int(duration)
    if source_in is not None:
        clip["sourceIn"] = int(source_in)
    if speed is not None:
        num, den = int(speed["num"]), int(speed["den"])
        if num < 1 or den < 1:
            raise ValueError("speed must be positive")
        clip["speed"] = {"num": num, "den": den} if (num, den) != (1, 1) else {"num": 1, "den": 1}
    return _checked(result)


def set_text(project, text_id, **fields):
    """Edit a text block: value, size, colour, alignment, wrapping or word animation."""
    allowed = {"value", "size", "color", "align", "direction", "wrap", "animation", "font"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"unknown text fields: {sorted(unknown)}")
    result = copy.deepcopy(project)
    for text in result.get("texts") or []:
        if text["id"] == text_id:
            for key, value in fields.items():
                if value is None:
                    continue
                if key == "animation" and value == "none":
                    text.pop("animation", None)
                    continue
                text[key] = value
            return _checked(result)
    raise ValueError(f"unknown text {text_id!r}")


def add_text(project, text_id, value, *, font="Cairo", size=64, color="#ffffff", align="center",
             direction="rtl", wrap=True, animation=None):
    """Create a text block. The page calls this before `add_text_clip`: a clip points at a text."""
    if not value or not value.strip():
        raise ValueError("a text block needs a value")
    result = copy.deepcopy(project)
    if any(text["id"] == text_id for text in result.get("texts") or []):
        raise ValueError(f"duplicate text id {text_id!r}")
    text = {"id": text_id, "value": value, "font": font, "size": int(size), "color": color,
            "align": align, "direction": direction, "wrap": bool(wrap)}
    if animation not in (None, "none"):
        text["animation"] = animation
    result.setdefault("texts", []).append(text)
    if result.get("texts") is None:
        result["texts"] = [text]
    return _checked(result)


def add_text_clip(project, track_id, clip_id, text_id, start, duration):
    result = copy.deepcopy(project)
    track = next((track for track in result["tracks"] if track["id"] == track_id), None)
    if track is None:
        raise ValueError(f"unknown track {track_id!r}")
    if track["kind"] != "text":
        raise ValueError("a text clip needs a text track")
    if any(clip["id"] == clip_id for clip in track["clips"]):
        raise ValueError(f"duplicate clip id {clip_id!r}")
    track["clips"].append({"id": clip_id, "kind": "media", "textId": text_id, "start": int(start),
                           "duration": int(duration), "sourceIn": 0, "effects": [], "keyframes": []})
    return _checked(result)


def add_asset(project, asset):
    """Attach a media asset; the caller is responsible for the file already being in the project."""
    result = copy.deepcopy(project)
    if any(existing["id"] == asset["id"] for existing in result["assets"]):
        raise ValueError(f"duplicate asset id {asset['id']!r}")
    result["assets"].append(dict(asset))
    return _checked(result)


def set_project(project, **fields):
    """Rename the project or change its duration; the profile is deliberately immutable here."""
    allowed = {"name", "duration", "seed"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"unknown project fields: {sorted(unknown)}")
    result = copy.deepcopy(project)
    if "duration" in fields and fields["duration"] is not None:
        result = set_duration(result, int(fields["duration"]))
        fields = {key: value for key, value in fields.items() if key != "duration"}
    for key, value in fields.items():
        if value is not None:
            result[key] = value
    return _checked(result)


def set_effect_value(project, clip_id, effect_id, value):
    """Set a constant effect value (0..10000 for opacity, 0..20000 for gain)."""
    result = copy.deepcopy(project)
    _, _, clip = _find_clip(result, clip_id)
    effect = next((effect for effect in clip["effects"] if effect["id"] == effect_id), None)
    if effect is None:
        raise ValueError(f"unknown effect {effect_id!r} on clip {clip_id!r}")
    effect["params"] = dict(effect.get("params") or {}, value=int(value))
    return _checked(result)


def add_keyframe(project, clip_id, effect_id, tick, value, interpolation="linear"):
    """Add or replace a keyframe on an existing curve, creating the curve when needed."""
    result = copy.deepcopy(project)
    _, _, clip = _find_clip(result, clip_id)
    if not any(effect["id"] == effect_id for effect in clip["effects"]):
        raise ValueError(f"unknown effect {effect_id!r} on clip {clip_id!r}")
    curve = next((curve for curve in clip["keyframes"] if curve["effectId"] == effect_id), None)
    points = [] if curve is None else [point for point in curve["points"]]
    points = [point for point in points if point["t"] != int(tick)]
    points.append({"t": int(tick), "value": int(value), "interpolation": interpolation})
    points.sort(key=lambda point: point["t"])
    updated = {"property": "value", "effectId": effect_id, "points": points}
    result = set_curve(result, clip_id, updated)
    return _checked(result)


def remove_keyframe(project, clip_id, effect_id, tick):
    """Drop one keyframe; removing the last one drops the curve entirely."""
    result = copy.deepcopy(project)
    _, _, clip = _find_clip(result, clip_id)
    curve = next((curve for curve in clip["keyframes"] if curve["effectId"] == effect_id), None)
    if curve is None:
        raise ValueError(f"no curve for effect {effect_id!r}")
    points = [point for point in curve["points"] if point["t"] != int(tick)]
    if not points:
        result = remove_curve(result, clip_id, effect_id)
    else:
        result = set_curve(result, clip_id, {"property": "value", "effectId": effect_id, "points": points})
    return _checked(result)
