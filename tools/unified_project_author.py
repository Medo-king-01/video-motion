"""Pure project-authoring operations for the experimental unified project subset.

These functions never touch assets on disk. They validate both input and output,
return detached snapshots, and reject conflicts rather than silently dropping data.
"""
from __future__ import annotations

from copy import deepcopy

from unified_project_edit import _checked, _find_clip, _tick


def create_project(project_id, name, profile, timebase, *, duration=0, seed=0):
    """Create a validated, empty 1.0 project with a detached profile."""
    project = {"schemaVersion": "1.0", "id": project_id, "name": name,
               "profile": deepcopy(profile), "timebase": timebase, "duration": duration,
               "seed": seed, "assets": [], "tracks": []}
    _checked(project)
    return project


def _find_track(project, track_id):
    for track in project["tracks"]:
        if track["id"] == track_id:
            return track
    raise ValueError(f"Unknown track: {track_id!r}")


def _position(index, length):
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index <= length:
        raise ValueError("position must be an integer within the insertion range")


def add_track(project, track_id, kind, *, position=None):
    """Insert an enabled, empty track; lower indices are lower visual layers."""
    _checked(project)
    result = deepcopy(project)
    tracks = result["tracks"]
    if position is None:
        position = len(tracks)
    _position(position, len(tracks))
    tracks.insert(position, {"id": track_id, "kind": kind, "enabled": True, "clips": []})
    _checked(result)
    return result


def remove_track(project, track_id):
    """Remove an empty track; callers must explicitly delete its clips first."""
    _checked(project)
    result = deepcopy(project)
    track = _find_track(result, track_id)
    if track["clips"]:
        raise ValueError("Cannot remove a nonempty track")
    result["tracks"].remove(track)
    _checked(result)
    return result


def reorder_track(project, track_id, position):
    """Move a track to its final zero-based position, preserving its contents."""
    _checked(project)
    result = deepcopy(project)
    tracks = result["tracks"]
    track = _find_track(result, track_id)
    _position(position, len(tracks) - 1)
    tracks.remove(track)
    tracks.insert(position, track)
    _checked(result)
    return result


def set_track_enabled(project, track_id, enabled):
    _checked(project)
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    result = deepcopy(project)
    _find_track(result, track_id)["enabled"] = enabled
    _checked(result)
    return result


def add_clip(project, track_id, clip_id, asset_id, start, duration, *, source_in=0):
    """Insert a plain media clip; the project duration is not extended implicitly."""
    _checked(project)
    _tick(start, "start")
    _tick(duration, "duration")
    _tick(source_in, "source_in")
    result = deepcopy(project)
    _find_track(result, track_id)["clips"].append({
        "id": clip_id, "kind": "media", "assetId": asset_id, "start": start,
        "duration": duration, "sourceIn": source_in, "effects": [], "keyframes": [],
    })
    _checked(result)
    return result


def delete_clip(project, clip_id):
    """Delete exactly one clip, without rippling or changing project duration."""
    _checked(project)
    result = deepcopy(project)
    track, index, _ = _find_clip(result, clip_id)
    track["clips"].pop(index)
    _checked(result)
    return result


def set_duration(project, duration):
    """Set explicit project duration; shrinking across clips is rejected."""
    _checked(project)
    _tick(duration, "duration")
    result = deepcopy(project)
    result["duration"] = duration
    _checked(result)
    return result


def remove_asset(project, asset_id):
    """Unregister an unused asset only; never delete the source file."""
    _checked(project)
    result = deepcopy(project)
    asset = next((asset for asset in result["assets"] if asset["id"] == asset_id), None)
    if asset is None:
        raise ValueError(f"Unknown asset: {asset_id!r}")
    if any(clip["assetId"] == asset_id for track in result["tracks"] for clip in track["clips"]):
        raise ValueError("Cannot remove a referenced asset")
    result["assets"].remove(asset)
    _checked(result)
    return result
