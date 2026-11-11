"""Exact time calculations and deterministic snapping for unified projects."""
from __future__ import annotations

from unified_project_edit import _checked, _tick


def frame_ticks(project):
    _checked(project)
    fps = project["profile"]["fps"]
    return project["timebase"] * fps["den"] // fps["num"]


def output_lengths(project):
    """Return frame and audio sample counts, rounded up to cover duration."""
    ft = frame_ticks(project)
    st = project["timebase"] // project["profile"]["sampleRate"]
    duration = project["duration"]
    return (duration + ft - 1) // ft, (duration + st - 1) // st


def snap(project, tick, tolerance, *, playhead=None, exclude_clip_id=None, frames=True):
    """Snap to closest candidate within tolerance; return (tick, kind, id).

    Ties: playhead, clip boundary, frame; then smaller tick and lexicographic ID.
    Frame candidates are limited to the nearest project frames within the project.
    exclude_clip_id prevents a dragged clip snapping to its own old edges.
    """
    _checked(project)
    _tick(tick, "tick")
    _tick(tolerance, "tolerance")
    if tick > project["duration"]:
        raise ValueError("tick is outside project")
    candidates = []
    if playhead is not None:
        _tick(playhead, "playhead")
        if playhead > project["duration"]:
            raise ValueError("playhead is outside project")
        candidates.append((playhead, 0, "playhead", ""))
    for track in project["tracks"]:
        for clip in track["clips"]:
            if clip["id"] != exclude_clip_id:
                candidates.extend(((clip["start"], 1, "clip", clip["id"]),
                                   (clip["start"] + clip["duration"], 1, "clip", clip["id"])))
    if frames:
        ft = frame_ticks(project)
        low = (tick // ft) * ft
        for t in (low, low + ft):
            if t <= project["duration"]:
                candidates.append((t, 2, "frame", ""))
    eligible = [c for c in candidates if abs(c[0] - tick) <= tolerance]
    if not eligible:
        return tick, None, None
    value, _, kind, ident = min(eligible, key=lambda c: (abs(c[0] - tick), c[1], c[0], c[3]))
    return value, kind, ident or None
