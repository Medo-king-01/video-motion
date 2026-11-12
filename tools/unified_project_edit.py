"""Pure, atomic edits for the experimental media-only project subset.

These operations return a new project or raise ValueError; they never write files, mutate
input, decode media, or run a renderer. All times are integer project ticks.
"""
from __future__ import annotations

from copy import deepcopy

from unified_project_check import MAX_INT, validate


def _checked(project):
    errors = validate(project)
    if errors:
        raise ValueError("Invalid or unsupported project: " + "; ".join(errors))


def _tick(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_INT:
        raise ValueError(f"{name} must be a nonnegative safe integer tick")


def _find_clip(project, clip_id):
    for track in project["tracks"]:
        for index, clip in enumerate(track["clips"]):
            if clip["id"] == clip_id:
                return track, index, clip
    raise ValueError(f"Unknown clip: {clip_id!r}")


def _source_asset(project, clip):
    """The asset a clip reads, or None for a text clip (which has no source range)."""
    asset_id = clip.get("assetId")
    return None if asset_id is None else _asset(project, asset_id)


def _asset(project, asset_id):
    return next(a for a in project["assets"] if a["id"] == asset_id)


def split_clip(project, clip_id, at, new_id):
    """Split at an absolute project tick; left keeps its ID, right gets new_id."""
    _checked(project)
    _tick(at, "at")
    if not isinstance(new_id, str) or not new_id.strip():
        raise ValueError("new_id must be a nonempty string")
    result = deepcopy(project)
    track, index, clip = _find_clip(result, clip_id)
    offset = at - clip["start"]
    if not 0 < offset < clip["duration"]:
        raise ValueError("split must be strictly inside the clip")
    if clip["effects"] or clip["keyframes"]:
        raise ValueError("split of clips with effects is not supported without an ID and curve mapping")
    right = deepcopy(clip)
    right.update(id=new_id, start=at, duration=clip["duration"] - offset)
    asset = _source_asset(result, clip)
    if asset is not None and asset["kind"] != "image":
        right["sourceIn"] += offset
    clip["duration"] = offset
    track["clips"].insert(index + 1, right)
    _checked(result)
    return result


def trim_clip(project, clip_id, start, end):
    """Trim inward to an absolute half-open interval; extending is not supported."""
    _checked(project)
    _tick(start, "start")
    _tick(end, "end")
    result = deepcopy(project)
    _, _, clip = _find_clip(result, clip_id)
    old_start = clip["start"]
    if not old_start <= start < end <= old_start + clip["duration"]:
        raise ValueError("trim must be a nonempty interval inside the original clip")
    if clip["keyframes"] and (start != old_start or end != old_start + clip["duration"]):
        raise ValueError("trim of animated clips is not supported without curve remapping")
    asset = _source_asset(result, clip)
    if asset is not None and asset["kind"] != "image":
        clip["sourceIn"] += start - old_start
    clip.update(start=start, duration=end - start)
    _checked(result)
    return result


def move_clip(project, clip_id, track_id, start):
    """Move a clip without changing source, length or project duration."""
    _checked(project)
    _tick(start, "start")
    result = deepcopy(project)
    source, index, clip = _find_clip(result, clip_id)
    target = next((track for track in result["tracks"] if track["id"] == track_id), None)
    if target is None:
        raise ValueError(f"Unknown track: {track_id!r}")
    source["clips"].pop(index)
    clip["start"] = start
    target["clips"].append(clip)
    _checked(result)
    return result


def ripple_delete(project, start, end, track_ids):
    """Remove [start,end) on selected tracks and shift their later clips left.

    A clip crossing either boundary is rejected: callers must split it first.
    The explicit project duration and all unselected tracks stay unchanged.
    """
    _checked(project)
    _tick(start, "start")
    _tick(end, "end")
    if not start < end <= project["duration"]:
        raise ValueError("delete interval must be nonempty and within project duration")
    if not isinstance(track_ids, (list, tuple)) or not track_ids or any(
        not isinstance(item, str) for item in track_ids
    ):
        raise ValueError("track_ids must be a nonempty list of track IDs")
    selected = set(track_ids)
    if len(selected) != len(track_ids):
        raise ValueError("track IDs must be unique")
    if not selected <= {track["id"] for track in project["tracks"]}:
        raise ValueError("unknown track ID")
    result = deepcopy(project)
    for track in result["tracks"]:
        if track["id"] not in selected:
            continue
        remaining = []
        for clip in track["clips"]:
            a, b = clip["start"], clip["start"] + clip["duration"]
            if (a < start < b) or (a < end < b):
                raise ValueError(f"clip {clip['id']!r} crosses a deletion boundary; split first")
            if start <= a and b <= end:
                continue
            if a >= end:
                clip["start"] -= end - start
            remaining.append(clip)
        track["clips"] = remaining
    _checked(result)
    return result
