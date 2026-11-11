"""Evaluate the experimental scalar effects contract, without rendering."""
from __future__ import annotations

from fractions import Fraction

from unified_project_edit import _checked, _find_clip, _tick


def effect_value(project, clip_id, effect_id, local_tick):
    """Return an exact Fraction in units of 1/10000, or None for a disabled effect.

    Keyframes are local to the clip. The incoming keyframe chooses interpolation
    from the previous point. A hold holds the previous value until the new point.
    Outside the keyframe range, clamp to the first or last value.
    """
    _checked(project)
    _tick(local_tick, "local_tick")
    _, _, clip = _find_clip(project, clip_id)
    if local_tick > clip["duration"]:
        raise ValueError("local_tick exceeds clip duration")
    effect = next((e for e in clip["effects"] if e["id"] == effect_id), None)
    if effect is None:
        raise ValueError("Unknown effect on clip")
    if not effect["enabled"]:
        return None
    curve = next((c for c in clip["keyframes"] if c["effectId"] == effect_id), None)
    if curve is None:
        return Fraction(effect["params"]["value"], 10000)
    points = curve["points"]
    if local_tick <= points[0]["t"]:
        return Fraction(points[0]["value"], 10000)
    for left, right in zip(points, points[1:], strict=False):
        if local_tick < right["t"]:
            if right["interpolation"] == "hold":
                return Fraction(left["value"], 10000)
            delta = Fraction(local_tick - left["t"], right["t"] - left["t"])
            return (Fraction(left["value"]) + delta * (right["value"] - left["value"])) / 10000
    return Fraction(points[-1]["value"], 10000)
