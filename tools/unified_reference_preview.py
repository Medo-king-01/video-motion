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
FONT_ROOT = Path(__file__).resolve().parents[1] / "assets" / "fonts"
SHAPER = Path(__file__).resolve().parents[1] / "medo-motion" / "templates" / "procedural-reels"


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


def font_path(family):
    """Resolve a family name to a bundled TTF, preferring the bold weight."""
    folder = FONT_ROOT / family
    if not folder.is_dir():
        raise PreviewError("V07", f"$.texts.font: unknown family {family!r}")
    candidates = sorted(folder.glob("*.ttf"))
    if not candidates:
        raise PreviewError("V07", f"$.texts.font: {family!r} has no TTF")
    bold = [path for path in candidates if "Bold" in path.name or "Black" in path.name]
    return (bold or candidates)[0]


def _text_sprite(text, opacity):
    """Render one text block as an RGBA Pillow image with alpha scaled by `opacity` (0..10000)."""
    import sys  # noqa: PLC0415

    from PIL import Image  # noqa: PLC0415

    if str(SHAPER) not in sys.path:
        sys.path.insert(0, str(SHAPER))
    import arabic_shape  # noqa: PLC0415

    path = str(font_path(text["font"]))
    rtl = text["direction"] == "rtl"
    width, height = arabic_shape.measure(path, text["value"], text["size"], rtl=rtl)
    sprite = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    color = tuple(int(text["color"][i:i + 2], 16) for i in (1, 3, 5))
    arabic_shape.draw(sprite, (width / 2, height / 2), path, text["value"], text["size"], color,
                      rtl=rtl, anchor="mm")
    if opacity < 10000:
        sprite.putalpha(sprite.getchannel("A").point(lambda value: value * opacity // 10000))
    return sprite


def _blend(outgoing, incoming, offset, length):
    """Integer crossfade: at `offset` 0 the outgoing picture, at length-1 the incoming one."""
    here, there = length - offset, offset
    return bytes((incoming[i] * there + outgoing[i] * here + length // 2) // length
                 for i in range(len(outgoing)))


def _text_layers(project, tick, height, width):
    """Sprites for the text clips visible at `tick`, positioned by their alignment."""
    layers = []
    texts = {text["id"]: text for text in project.get("texts") or []}
    margin = max(8, width // 12)
    for ti, track in enumerate(project["tracks"]):
        if not track["enabled"] or track["kind"] != "text":
            continue
        for ci, clip in enumerate(track["clips"]):
            if not clip["start"] <= tick < clip["start"] + clip["duration"]:
                continue
            if clip["keyframes"]:
                raise PreviewError("V02", f"$.tracks[{ti}].clips[{ci}].keyframes",
                                   "keyframed text is not supported by the reference preview")
            opacity = 10000
            for effect in clip["effects"]:
                if effect["type"] != "opacity":
                    raise PreviewError("V02", f"$.tracks[{ti}].clips[{ci}].effects",
                                       "only opacity is supported on text")
                opacity = effect["params"]["value"]
            text = texts[clip["textId"]]
            sprite = _text_sprite(text, opacity)
            room = width - 2 * margin
            if sprite.width > room:
                # Fit instead of clipping: the declared size is a wish, the canvas is the limit.
                ratio = room / sprite.width
                sprite = sprite.resize((room, max(1, int(round(sprite.height * ratio)))))
            if sprite.height > height - 2 * margin:
                ratio = (height - 2 * margin) / sprite.height
                sprite = sprite.resize((max(1, int(round(sprite.width * ratio))), height - 2 * margin))
            x = {"left": margin, "center": (width - sprite.width) // 2,
                 "right": width - margin - sprite.width}[text["align"]]
            layers.append((sprite, (x, (height - sprite.height) // 2)))
    return layers


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
    enabled_text = [i for i, track in enumerate(p["tracks"]) if track["enabled"] and track["kind"] == "text"]
    if len(enabled_text) > 1:
        raise PreviewError("V02", "$.tracks", "multiple enabled text tracks are not supported")
    assets = {a["id"]: a for a in p["assets"]}
    tick = frame_index * graph["clock"]["frameTicks"]
    active = None
    for ti, track in enumerate(p["tracks"]):
        if not track["enabled"]:
            continue
        pictures = {}
        for ci, clip in enumerate(track["clips"]):
            path = f"$.tracks[{ti}].clips[{ci}]"
            if clip.get("speed") not in (None, {"num": 1, "den": 1}):
                raise PreviewError("V06", path + ".speed", "clip speed is not supported by the reference preview")
            if track["kind"] == "text":
                continue
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
    layers = _text_layers(p, tick, height, width)
    if layers:
        from PIL import Image  # noqa: PLC0415

        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        if active is not None:
            base = Image.new("RGBA", (width, height))
            base.putdata([(active[i], active[i + 1], active[i + 2], 255) for i in range(0, len(active), 3)])
            canvas.alpha_composite(base)
        for sprite, (x, y) in layers:
            canvas.alpha_composite(sprite, (x, y))
        return {"width": width, "height": height, "frameIndex": frame_index, "tick": tick,
                "format": "RGBA8", "pixels": canvas.tobytes(), "texts": len(layers)}
    rgba = bytearray(width * height * 4)
    if active is not None:
        rgba[0::4], rgba[1::4], rgba[2::4] = active[0::3], active[1::3], active[2::3]
        rgba[3::4] = b"\xff" * (width * height)
    return {"width": width, "height": height, "frameIndex": frame_index, "tick": tick,
            "format": "RGBA8", "pixels": bytes(rgba), "texts": 0}
