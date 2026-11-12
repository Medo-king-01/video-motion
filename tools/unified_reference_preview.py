"""Minimal reference frame preview for a deliberately narrow unified-project subset.

Returns raw RGBA bytes, not an export and not a P/K/R/Hybrid adapter. Only trusted
project directories are supported. This is not a sandbox for concurrent writers.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from unified_project_media import _local_file
from unified_render_graph import compile_project

MAX_PIXELS = 4096 * 4096


class PreviewError(ValueError):
    """A diagnosed unsupported or unreadable reference preview input."""

    def __init__(self, code, path, message):
        self.code, self.path, self.message = code, path, message
        super().__init__(f"{code} {path}: {message}")


def _read_image(root, asset, width, height, path):
    # This intentionally supports a canonical P6 subset only, avoiding a general
    # image decoder and ambiguous metadata/color processing in this reference path.
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    limit = len(header) + width * height * 3
    try:
        source = _local_file(root, asset["uri"])
        with source.open("rb") as stream:
            data = stream.read(limit + 1)
    except (OSError, ValueError) as exc:
        raise PreviewError("V03", path, f"cannot open image: {exc}") from exc
    if hashlib.sha256(data).hexdigest() != asset["sha256"]:
        raise PreviewError("V03", path, "image SHA-256 does not match")
    if len(data) != limit or not data.startswith(header):
        raise PreviewError("V04", path, "expected exact-size canonical 8-bit P6 RGB image")
    return data[len(header):]


def _blend(outgoing, incoming, offset, length):
    """Integer crossfade: at `offset` 0 the outgoing picture, at length-1 the incoming one."""
    here, there = length - offset, offset
    return bytes((incoming[i] * there + outgoing[i] * here + length // 2) // length
                 for i in range(len(outgoing)))


def render_frame(project, root, frame_index):
    """Compile and preview one absolute frame as detached, row-major RGBA8 bytes.

    Rejects any enabled audio clips, multiple enabled video tracks, non-image
    clips or effects on enabled tracks. Checks all referenced enabled images,
    including those not visible at this frame. Disabled tracks are ignored.
    RGB bytes are copied without color conversion; gaps are transparent black.
    """
    graph = compile_project(project)
    p = graph["project"]
    if isinstance(frame_index, bool) or not isinstance(frame_index, int) or not 0 <= frame_index < graph["clock"]["frameCount"]:
        raise PreviewError("V01", "$", "frame index outside project")
    width, height = p["profile"]["width"], p["profile"]["height"]
    if width * height > MAX_PIXELS:
        raise PreviewError("V01", "$.profile", "preview pixel limit exceeded")
    enabled_video = [i for i, track in enumerate(p["tracks"]) if track["enabled"] and track["kind"] == "video"]
    if len(enabled_video) > 1:
        raise PreviewError("V02", "$.tracks", "multiple enabled video tracks are not supported")
    assets = {a["id"]: a for a in p["assets"]}
    tick = frame_index * graph["clock"]["frameTicks"]
    active = None
    for ti, track in enumerate(p["tracks"]):
        if not track["enabled"]:
            continue
        pictures = {}
        for ci, clip in enumerate(track["clips"]):
            path = f"$.tracks[{ti}].clips[{ci}]"
            if track["kind"] != "video":
                raise PreviewError("V02", path, "only video-track still images are supported")
            if clip["effects"] or clip["keyframes"]:
                raise PreviewError("V02", path, "effects and keyframes are not supported")
            asset = assets[clip["assetId"]]
            if asset["kind"] != "image":
                raise PreviewError("V02", path, "only still images are supported")
            rgb = _read_image(Path(root), asset, width, height, path + ".assetId")
            pictures[clip["id"]] = rgb
            if clip["start"] <= tick < clip["start"] + clip["duration"]:
                active = rgb
        for tk, transition in enumerate(track.get("transitions") or []):
            path = f"$.tracks[{ti}].transitions[{tk}]"
            clips = {clip["id"]: clip for clip in track["clips"]}
            source, target = clips.get(transition["fromClipId"]), clips.get(transition["toClipId"])
            if source is None or target is None or transition["kind"] != "crossfade":
                raise PreviewError("V05", path, "a crossfade needs two known clips on this track")
            half = transition["duration"] // 2
            start = target["start"] - half
            if start <= tick < start + transition["duration"]:
                offset = tick - start
                active = _blend(pictures[source["id"]], pictures[target["id"]], offset,
                                transition["duration"])
    rgba = bytearray(width * height * 4)
    if active is not None:
        rgba[0::4], rgba[1::4], rgba[2::4] = active[0::3], active[1::3], active[2::3]
        rgba[3::4] = b"\xff" * (width * height)
    return {"width": width, "height": height, "frameIndex": frame_index, "tick": tick,
            "format": "RGBA8", "pixels": bytes(rgba)}
