#!/usr/bin/env python3
"""Reference frame renderer for the unified project: real decode, real composition.

This is the pixel path behind both the editor preview and engine P's export, which is why the
adapter can claim "the exported frame is the previewed frame" by hash.

What it decodes and draws today:

* **stills** — canonical `P6` PPM (exact project size, no scaling) and PNG/JPEG through Pillow,
  always SHA-256 verified against the asset;
* **video** — one frame at the clip's source tick through PyAV (`asset.streams.video` selects the
  stream), scaled to the project size with Pillow's deterministic bilinear filter;
* **speed** — a 2× clip reads its source twice as fast, in integer tick maths;
* **opacity** — constant or keyframed, evaluated with `unified_project_effects`;
* **transitions** — crossfade (integer half-mix) and wipe (left/right/up/down, hard edge);
* **text** — Arabic shaping, optional wrapping, and word-level animation (`fade`, `words-up`,
  `words-fade`).

Nothing here is a sandbox: only trusted project directories are supported.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from unified_project_media import _local_file
from unified_project_effects import effect_value
from unified_render_graph import compile_project

MAX_PIXELS = 4096 * 4096
FONT_ROOT = Path(__file__).resolve().parents[1] / "assets" / "fonts"
SHAPER = Path(__file__).resolve().parents[1] / "medo-motion" / "templates" / "procedural-reels"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"


class PreviewError(ValueError):
    """A diagnosed unsupported or unreadable reference preview input."""

    def __init__(self, code, path, message):
        self.code, self.path, self.message = code, path, message
        super().__init__(f"{code} {path}: {message}")


# ------------------------------------------------------------------ assets
def _read_bytes(root, asset, path):
    try:
        source = _local_file(root, asset["uri"])
        data = source.read_bytes()
    except (OSError, ValueError) as exc:
        raise PreviewError("V03", path, f"cannot open media: {exc}") from exc
    if hashlib.sha256(data).hexdigest() != asset["sha256"]:
        raise PreviewError("V03", path, f"{asset['uri']}: SHA-256 does not match the asset")
    return data


def _read_image(root, asset, width, height, path):
    """RGBA bytes for one still, at exactly the project size."""
    data = _read_bytes(root, asset, path)
    if data.startswith(b"P6"):
        header = f"P6\n{width} {height}\n255\n".encode("ascii")
        if not data.startswith(header) or len(data) != len(header) + width * height * 3:
            raise PreviewError("V04", path, "expected a canonical P6 image at the project size")
        rgb = data[len(header):]
        rgba = bytearray(width * height * 4)
        rgba[0::4], rgba[1::4], rgba[2::4] = rgb[0::3], rgb[1::3], rgb[2::3]
        rgba[3::4] = b"\xff" * (width * height)
        return bytes(rgba)
    if data.startswith(PNG_MAGIC) or data.startswith(JPEG_MAGIC):
        from PIL import Image  # noqa: PLC0415

        try:
            image = Image.open(__import__("io").BytesIO(data)).convert("RGBA")
        except Exception as exc:  # noqa: BLE001 - any decoder failure is the same diagnosis
            raise PreviewError("V04", path, f"cannot decode image: {exc}") from exc
        if image.size != (width, height):
            raise PreviewError("V04", path, f"image is {image.size[0]}×{image.size[1]}, "
                                           f"project is {width}×{height}")
        return image.tobytes()
    raise PreviewError("V04", path, "unsupported still format (P6 PPM, PNG or JPEG)")


def _video_stream_index(asset):
    streams = asset.get("streams") or {}
    return int(streams.get("video", 0))


def _read_video(root, asset, width, height, source_tick, path):
    """RGBA bytes for the frame at `source_tick`, decoded by PyAV and scaled to the project."""
    try:
        import av  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - PyAV ships with the studio
        raise PreviewError("V08", path, "PyAV is required to decode video") from exc
    from PIL import Image  # noqa: PLC0415

    data = _read_bytes(root, asset, path)
    timebase = asset.get("timebase", 240_000)
    seconds = source_tick / timebase
    try:
        with av.open(__import__("io").BytesIO(data)) as container:
            stream = container.streams.video[_video_stream_index(asset)]
            stream.thread_type = "AUTO"
            container.seek(int(seconds / stream.time_base), stream=stream, backward=True)
            chosen = None
            for frame in container.decode(stream):
                moment = float(frame.pts * stream.time_base) if frame.pts is not None else 0.0
                chosen = frame
                if moment >= seconds:
                    break
            if chosen is None:
                raise PreviewError("V08", path, "no decodable video frame")
            image = chosen.to_image().convert("RGBA")
    except PreviewError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PreviewError("V08", path, f"cannot decode video: {exc}") from exc
    if image.size != (width, height):
        image = image.resize((width, height), Image.BILINEAR)
    return image.tobytes()


# ------------------------------------------------------------------ maths
def _source_tick(clip, tick):
    """Where inside the asset a timeline tick reads, honouring clip speed."""
    speed = clip.get("speed") or {"num": 1, "den": 1}
    offset = tick - clip["start"]
    return clip["sourceIn"] + offset * speed["num"] // speed["den"]


def _opacity(project, clip, local_tick):
    """Effective opacity in 0..10000 from the clip's effects and keyframes."""
    value = 10000
    for effect in clip["effects"]:
        if effect["type"] != "opacity" or not effect["enabled"]:
            continue
        if effect["id"] in {curve["effectId"] for curve in clip["keyframes"]}:
            fraction = effect_value(project, clip["id"], effect["id"], local_tick)
            value = value * int(fraction * 10000) // 10000 if fraction is not None else 0
        else:
            value = value * min(10000, effect["params"]["value"]) // 10000
    return max(0, min(10000, value))


def _scale_alpha(pixels, opacity, width, height):
    if opacity >= 10000:
        return pixels
    if opacity <= 0:
        return bytes(width * height * 4)
    table = bytes(value * opacity // 10000 for value in range(256))
    out = bytearray(pixels)
    out[3::4] = bytes(out[3::4]).translate(table)
    return bytes(out)


def _clip_pixels(project, root, clip, tick, width, height, path):
    """RGBA pixels of one clip at `tick`, with its opacity applied."""
    local = tick - clip["start"]
    if clip.get("textId") is not None:
        return None
    asset = next(asset for asset in project["assets"] if asset["id"] == clip["assetId"])
    if asset["kind"] == "image":
        pixels = _read_image(root, asset, width, height, path + ".assetId")
    elif asset["kind"] == "video":
        pixels = _read_video(root, asset, width, height, _source_tick(clip, tick), path + ".assetId")
    else:
        raise PreviewError("V02", path, f"{asset['kind']} assets cannot be drawn on a video track")
    return _scale_alpha(pixels, _opacity(project, clip, local), width, height)


def _blend_crossfade(outgoing, incoming, offset, length):
    """Integer half-mix: at `offset` 0 the outgoing picture, at length-1 the incoming one."""
    here, there = length - offset, offset
    return bytes((incoming[i] * there + outgoing[i] * here + length // 2) // length
                 for i in range(len(outgoing)))


def _blend_wipe(outgoing, incoming, offset, length, direction, width, height):
    """Hard-edge reveal: the incoming picture takes over one line at a time."""
    progress = offset * 1000 // max(1, length - 1)
    out = bytearray(outgoing)
    if direction in ("left", "right"):
        edge = progress * width // 1000
        if direction == "right":
            edge = width - edge
        for y in range(height):
            start = y * width * 4
            if direction == "left":
                out[start:start + edge * 4] = incoming[start:start + edge * 4]
            else:
                out[start + edge * 4:start + width * 4] = incoming[start + edge * 4:start + width * 4]
    else:
        edge = progress * height // 1000
        if direction == "down":
            edge = height - edge
        if direction == "up":
            out[0:edge * width * 4] = incoming[0:edge * width * 4]
        else:
            out[edge * width * 4:] = incoming[edge * width * 4:]
    return bytes(out)


# ------------------------------------------------------------------ text
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


def _shaper():
    if str(SHAPER) not in sys.path:
        sys.path.insert(0, str(SHAPER))
    import arabic_shape  # noqa: PLC0415

    return arabic_shape


def _word_sprite(text, word, color, rtl):
    from PIL import Image  # noqa: PLC0415

    shaper = _shaper()
    path = str(font_path(text["font"]))
    shaper = _shaper()
    width, height = shaper.measure(path, word, text["size"], rtl=rtl)
    sprite = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shaper.draw(sprite, (width / 2, height / 2), path, word, text["size"], color, rtl=rtl, anchor="mm")
    return sprite


def _wrap_words(text, words, max_width):
    """Group words into lines that fit `max_width`, measuring each candidate with the shaper."""
    shaper = _shaper()
    path = str(font_path(text["font"]))
    rtl = text["direction"] == "rtl"
    lines, current = [], []
    for word in words:
        candidate = " ".join(current + [word])
        if current and shaper.measure(path, candidate, text["size"], rtl=rtl)[0] > max_width:
            lines.append(current)
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(current)
    return lines


def _ease(progress, ease):
    if ease == "cubic-out":
        inverse = 1000 - progress
        return 1000 - inverse * inverse * inverse // 1000_000
    return progress


def _text_layers(project, tick, height, width):
    """Sprites for the text clips visible at `tick`, with wrapping and word animation."""
    from PIL import Image  # noqa: PLC0415

    layers = []
    texts = {text["id"]: text for text in project.get("texts") or []}
    margin = max(8, width // 12)
    room = width - 2 * margin
    for ti, track in enumerate(project["tracks"]):
        if not track["enabled"] or track["kind"] != "text":
            continue
        for ci, clip in enumerate(track["clips"]):
            if not clip["start"] <= tick < clip["start"] + clip["duration"]:
                continue
            path = f"$.tracks[{ti}].clips[{ci}]"
            if clip["keyframes"] and not any(effect["type"] == "opacity" for effect in clip["effects"]):
                raise PreviewError("V02", path + ".keyframes", "only opacity can be keyframed on text")
            text = texts[clip["textId"]]
            rtl = text["direction"] == "rtl"
            color = tuple(int(text["color"][i:i + 2], 16) for i in (1, 3, 5))
            words = [word for word in text["value"].split() if word]
            lines = _wrap_words(text, words, room) if text.get("wrap") else [words]
            animation = text.get("animation") or {"kind": "none"}
            stagger = int(animation.get("stagger", 0))
            ease = animation.get("ease", "linear")
            local = tick - clip["start"]
            sprites = []
            flat_index = 0
            for line in lines:
                line_sprites = []
                for word in line:
                    progress = 1000
                    if animation["kind"] != "none" and stagger > 0:
                        start = flat_index * stagger
                        progress = max(0, min(1000, (local - start) * 1000 // stagger))
                        progress = _ease(progress, ease)
                    if progress > 0:
                        sprite = _word_sprite(text, word, color, rtl)
                        if animation["kind"] in ("fade", "words-fade", "words-up"):
                            sprite.putalpha(sprite.getchannel("A").point(
                                lambda value, p=progress: value * p // 1000))
                        rise = 0
                        if animation["kind"] == "words-up":
                            rise = text["size"] * (1000 - progress) // 1000
                        line_sprites.append((sprite, rise))
                    flat_index += 1
                if line_sprites:
                    sprites.append(line_sprites)
            if not sprites:
                continue
            line_height = max(max(sprite.height for sprite, _ in line) for line in sprites)
            block_height = line_height * len(sprites)
            if block_height > height - 2 * margin:
                ratio = (height - 2 * margin) / block_height
                for line in sprites:
                    for index, (sprite, rise) in enumerate(line):
                        line[index] = (sprite.resize((max(1, int(sprite.width * ratio)),
                                                     max(1, int(sprite.height * ratio)))), rise)
                line_height = max(max(sprite.height for sprite, _ in line) for line in sprites)
                block_height = line_height * len(sprites)
            top = (height - block_height) // 2
            for row, line in enumerate(sprites):
                line_width = sum(sprite.width for sprite, _ in line)
                if line_width > room:
                    ratio = room / line_width
                    line = [(sprite.resize((max(1, int(sprite.width * ratio)),
                                            max(1, int(sprite.height * ratio)))), rise)
                            for sprite, rise in line]
                    line_width = sum(sprite.width for sprite, _ in line)
                x = {"left": margin, "center": (width - line_width) // 2,
                     "right": width - margin - line_width}[text["align"]]
                y = top + row * line_height
                ordered = line if not rtl else list(reversed(line))
                for sprite, rise in ordered:
                    layers.append((sprite, (x, y + (line_height - sprite.height) // 2 + rise)))
                    x += sprite.width
            opacity = _opacity(project, clip, local)
            if opacity < 10000:
                scaled = []
                for sprite, position in layers[-sum(len(line) for line in sprites):]:
                    if opacity <= 0:
                        continue
                    faded = sprite.copy()
                    faded.putalpha(faded.getchannel("A").point(
                        lambda value, o=opacity: value * o // 10000))
                    scaled.append((faded, position))
                layers = layers[:-sum(len(line) for line in sprites)] + scaled
    return layers


# ------------------------------------------------------------------ frame
def render_frame(project, root, frame_index):
    """Compile and preview one absolute frame as detached, row-major RGBA8 bytes.

    Rejects an out-of-range index, more than one enabled video track, more than one enabled text
    track, and any clip whose asset cannot be decoded. Disabled tracks are ignored; gaps stay
    transparent.
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
    for index, track in enumerate(p["tracks"]):
        if track["enabled"] and track["kind"] not in ("video", "text"):
            raise PreviewError("V02", f"$.tracks[{index}]",
                               f"only video and text tracks are drawn; {track['kind']} is mixed elsewhere")
    tick = frame_index * graph["clock"]["frameTicks"]
    active = None
    for ti, track in enumerate(p["tracks"]):
        if not track["enabled"] or track["kind"] != "video":
            continue
        pictures = {}
        for ci, clip in enumerate(track["clips"]):
            path = f"$.tracks[{ti}].clips[{ci}]"
            pixels = _clip_pixels(p, Path(root), clip, max(tick, clip["start"]), width, height, path)
            pictures[clip["id"]] = pixels
            if clip["start"] <= tick < clip["start"] + clip["duration"]:
                active = pixels
        for tk, transition in enumerate(track.get("transitions") or []):
            path = f"$.tracks[{ti}].transitions[{tk}]"
            clips = {clip["id"]: clip for clip in track["clips"]}
            source, target = clips.get(transition["fromClipId"]), clips.get(transition["toClipId"])
            if source is None or target is None:
                raise PreviewError("V05", path, "a transition needs two known clips on this track")
            half = transition["duration"] // 2
            start = target["start"] - half
            if start <= tick < start + transition["duration"]:
                offset = tick - start
                if transition["kind"] == "crossfade":
                    active = _blend_crossfade(pictures[source["id"]], pictures[target["id"]],
                                              offset, transition["duration"])
                elif transition["kind"] == "wipe":
                    active = _blend_wipe(pictures[source["id"]], pictures[target["id"]], offset,
                                         transition["duration"], transition.get("direction", "left"),
                                         width, height)
                else:
                    raise PreviewError("V05", path, f"unknown transition {transition['kind']!r}")

    layers = _text_layers(p, tick, height, width)
    if layers:
        from PIL import Image  # noqa: PLC0415

        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        if active is not None:
            canvas.alpha_composite(Image.frombytes("RGBA", (width, height), active))
        for sprite, (x, y) in layers:
            canvas.alpha_composite(sprite, (x, y))
        return {"width": width, "height": height, "frameIndex": frame_index, "tick": tick,
                "format": "RGBA8", "pixels": canvas.tobytes(), "texts": len(layers)}
    if active is None:
        return {"width": width, "height": height, "frameIndex": frame_index, "tick": tick,
                "format": "RGBA8", "pixels": bytes(width * height * 4), "texts": 0}
    return {"width": width, "height": height, "frameIndex": frame_index, "tick": tick,
            "format": "RGBA8", "pixels": active, "texts": 0}
