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
            source = Image.open(__import__("io").BytesIO(data))
            # The pipeline works in sRGB and has no ICC engine: a tagged still that is not sRGB is a
            # refusal, not something to silently reinterpret.
            profile = source.info.get("icc_profile")
            if profile and not _is_srgb_profile(profile):
                raise PreviewError("V10", path, "the still carries a non-sRGB ICC profile; "
                                                "convert it to sRGB before importing")
            image = source.convert("RGBA")
        except PreviewError:
            raise
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


#: AVColorSpace values this build converts. Anything else is refused rather than guessed.
COLOUR_SPACES = {1: "bt709", 4: "fcc", 5: "bt601", 6: "bt601", 7: "smpte240m"}
HDR_SPACES = {9: "bt2020-ncl", 10: "bt2020-cl", 11: "smpte2085", 12: "chroma-derived-ncl",
              13: "ictcp", 14: "ipt-c2", 15: "ycbcr", 16: "ycycgco"}
#: ITU-R coefficients for the two matrices actually used here (Kr, Kb).
COLOUR_MATRIX = {"bt709": (0.2126, 0.0722), "bt601": (0.299, 0.114), "fcc": (0.30, 0.11),
                 "smpte240m": (0.212, 0.087)}


def _is_srgb_profile(profile):
    """sRGB is the only profile this pipeline can honour; recognise it by its description."""
    text = profile.lower()
    return b"srgb" in text or b"iec61966" in text


def colour_space_of(frame, stream, height):
    """Which matrix a frame must be converted with, or a `V09` refusal.

    Unspecified is the common case in real files: HD follows BT.709 and SD follows BT.601, which is
    the same rule every player applies. HDR and anything unknown is refused — guessing there would
    produce a plausible-looking, wrong picture.
    """
    code = getattr(frame, "colorspace", None)
    if code in (None, 0, 2):
        code = getattr(stream, "colorspace", None)
    if code in (None, 0, 2):
        return "bt709" if height >= 720 else "bt601"
    if code in HDR_SPACES:
        raise PreviewError("V09", "$.tracks", f"{HDR_SPACES[code]} sources are not converted "
                                              f"(this build works in sRGB/Rec.709)")
    if code not in COLOUR_SPACES:
        raise PreviewError("V09", "$.tracks", f"unknown colour space {code}; refusing to guess")
    return COLOUR_SPACES[code]


def full_range_of(frame, stream):
    code = getattr(frame, "color_range", None) or getattr(stream, "color_range", None)
    return code == 2  # AVCOL_RANGE_JPEG; unspecified and MPEG both mean limited


def _plane(frame, index):
    import numpy as np  # noqa: PLC0415

    plane = frame.planes[index]
    return np.frombuffer(bytes(plane), dtype=np.uint8).reshape(plane.height, plane.line_size)


def _yuv_to_rgba(frame, matrix, full_range):
    """YUV → RGBA with the declared matrix; chroma is upsampled nearest-neighbour (4:2:0, 4:2:2 or 4:4:4)."""
    import numpy as np  # noqa: PLC0415

    height, width = frame.height, frame.width
    y = _plane(frame, 0)[:height, :width].astype(np.float32)

    def chroma(index):
        plane = frame.planes[index]
        values = _plane(frame, index)[:plane.height, :plane.width].astype(np.float32)
        rows = max(1, height // plane.height)
        columns = max(1, width // plane.width)
        values = np.repeat(np.repeat(values, rows, axis=0), columns, axis=1)
        return values[:height, :width]

    u, v = chroma(1), chroma(2)
    if full_range:
        yy, cb, cr = y, u - 128.0, v - 128.0
    else:
        yy, cb, cr = (y - 16.0) * (255.0 / 219.0), (u - 128.0) * (255.0 / 224.0), (v - 128.0) * (255.0 / 224.0)
    kr, kb = COLOUR_MATRIX[matrix]
    kg = 1.0 - kr - kb
    red = yy + 2.0 * (1.0 - kr) * cr
    blue = yy + 2.0 * (1.0 - kb) * cb
    green = (yy - kr * red - kb * blue) / kg
    rgb = np.stack([red, green, blue], axis=-1)
    rgb = np.rint(np.clip(rgb, 0, 255)).astype(np.uint8)
    rgba = np.empty((height, width, 4), dtype=np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = 255
    return rgba.tobytes()


def _frame_at(container, stream, seconds):
    """The frame on screen at `seconds`: the last one whose timestamp is at or before it.

    This is what makes variable frame rate work: a frame covers the span until the next frame's
    presentation time, so picking by timestamp is correct whether the gaps are regular or not.
    """
    chosen = None
    for frame in container.decode(stream):
        if frame.pts is None:
            chosen = chosen or frame
            continue
        moment = float(frame.pts * (frame.time_base or stream.time_base))
        if moment > seconds + 1e-6:
            break
        chosen = frame
    return chosen


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
            chosen = _frame_at(container, stream, seconds)
            if chosen is None:
                # the seek landed past the requested instant (possible with sparse keyframes):
                # decode from the head once instead of returning a later picture
                container.seek(0, stream=stream)
                chosen = _frame_at(container, stream, seconds)
            if chosen is None:
                raise PreviewError("V08", path, "no decodable video frame")
            matrix = colour_space_of(chosen, stream, height)
            pixels = _yuv_to_rgba(chosen, matrix, full_range_of(chosen, stream))
            if chosen.format.name not in ("yuv420p", "yuvj420p", "yuv422p", "yuv444p"):
                # anything exotic falls back to PyAV's own conversion, which applies the same matrix
                image = chosen.to_image().convert("RGBA")
            else:
                image = Image.frombytes("RGBA", (chosen.width, chosen.height), pixels)
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


def _word_sprite(font, word, size, color, rtl):
    """The shaped word on its full canvas — the same frame `text_clusters` cuts letters out of."""
    return _shaper().word_canvas(str(font_path(font)), word, size, color, rtl)


def _word_positions(value):
    """`[(word, character_offset)]` — the offset is what a `run` is matched against."""
    words, index = [], 0
    for token in value.split():
        index = value.index(token, index)
        words.append((token, index))
        index += len(token)
    return words


def _colour(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def _style_at(text, offset):
    """The style of the word that starts at `offset`: the text's own, refined by any run covering it."""
    style = {"font": text["font"], "size": text["size"], "color": _colour(text["color"])}
    for run in text.get("runs") or []:
        if run["start"] <= offset < run["end"]:
            for key in ("font", "size", "color"):
                if key in run:
                    style[key] = _colour(run[key]) if key == "color" else run[key]
            break
    return style


def _wrap_words(text, words, max_width, styles):
    """Group words into lines that fit `max_width`, measuring each candidate with its own style."""
    shaper = _shaper()
    rtl = text["direction"] == "rtl"
    lines, current, width = [], [], 0
    for index, (word, _offset) in enumerate(words):
        style = styles[index]
        span = shaper.measure(str(font_path(style["font"])), word, style["size"], rtl=rtl)[0]
        if current and width + span > max_width:
            lines.append(current)
            current, width = [index], span
        else:
            current.append(index)
            width += span
    if current:
        lines.append(current)
    return lines


def _ease(progress, ease):
    if ease == "cubic-out":
        inverse = 1000 - progress
        return 1000 - inverse * inverse * inverse // 1000_000
    return progress


def _word_pieces(style, word, rtl, per_letter):
    """One piece per word, or one per letter cluster when the animation moves letters."""
    shaper = _shaper()
    path = str(font_path(style["font"]))
    if per_letter:
        # The letter path and the word path must agree on the box, or a finished animation would sit
        # a few pixels off the static caption. Both use the shaped word's measured box; each letter
        # is placed inside it at its shaped offset.
        canvas = shaper.word_canvas(path, word, style["size"], style["color"], rtl)
        clusters, _advance, _ascender, _descender = shaper.text_clusters(
            path, word, style["size"], style["color"], rtl)
        pieces = [{"sprite": item["sprite"], "dx": item["x"], "dy": item["y"],
                   "order": item["cluster"]} for item in clusters]
        return pieces, canvas.width, canvas.height
    sprite = _word_sprite(style["font"], word, style["size"], style["color"], rtl)
    return [{"sprite": sprite, "dx": 0, "dy": 0, "order": 0}], sprite.width, sprite.height


def _text_layers(project, tick, height, width):
    """Sprites for the text clips visible at `tick`: wrapping to the frame, runs, word/letter animation."""
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
            words = _word_positions(text["value"])
            styles = [_style_at(text, offset) for _word, offset in words]
            animation = text.get("animation") or {"kind": "none"}
            kind = animation["kind"]
            per_letter = kind.startswith("letters-")
            stagger = int(animation.get("stagger", 0))
            ease = animation.get("ease", "linear")
            local = tick - clip["start"]
            lines = (_wrap_words(text, words, room, styles) if text.get("wrap")
                     else [list(range(len(words)))])
            pieces_seen = 0  # letters: one step per cluster, in reading order
            words_seen = 0   # words: one step per word, in reading order
            rows = []
            for line in lines:
                row = []
                for index in line:
                    word, _offset = words[index]
                    style = styles[index]
                    items, advance, box_height = _word_pieces(style, word, rtl, per_letter)
                    for piece in items:
                        step = pieces_seen if per_letter else words_seen
                        progress = 1000
                        if kind != "none" and stagger > 0:
                            start = step * stagger
                            progress = max(0, min(1000, (local - start) * 1000 // stagger))
                            progress = _ease(progress, ease)
                        piece["progress"] = progress
                        if per_letter:
                            pieces_seen += 1
                    row.append({"width": advance, "height": box_height, "pieces": items})
                    if not per_letter:
                        words_seen += 1
                if row:
                    rows.append(row)
            if not rows:
                continue

            def shrink(ratio):
                for row in rows:
                    for item in row:
                        item["width"] *= ratio
                        item["height"] *= ratio
                        for piece in item["pieces"]:
                            piece["dx"] *= ratio
                            piece["dy"] *= ratio
                            piece["sprite"] = piece["sprite"].resize(
                                (max(1, int(piece["sprite"].width * ratio)),
                                 max(1, int(piece["sprite"].height * ratio))))

            line_height = max(max(item["height"] for item in row) for row in rows)
            if line_height * len(rows) > height - 2 * margin:
                shrink((height - 2 * margin) / (line_height * len(rows)))
                line_height = max(max(item["height"] for item in row) for row in rows)
            block_height = line_height * len(rows)
            top = (height - block_height) // 2
            first = len(layers)
            for index, row in enumerate(rows):
                line_width = sum(item["width"] for item in row)
                if line_width > room:
                    shrink(room / line_width)
                    line_width = sum(item["width"] for item in row)
                y = top + index * line_height
                if rtl:
                    x = {"left": margin, "center": (width - line_width) // 2,
                         "right": width - margin - line_width}[text["align"]] + line_width
                else:
                    x = {"left": margin, "center": (width - line_width) // 2,
                         "right": width - margin - line_width}[text["align"]]
                for item in row:
                    base = x - item["width"] if rtl else x
                    for piece in item["pieces"]:
                        progress = piece["progress"]
                        if progress <= 0:
                            continue
                        sprite = piece["sprite"]
                        if kind in ("fade", "words-fade", "words-up", "letters-fade", "letters-up"):
                            sprite = sprite.copy()
                            sprite.putalpha(sprite.getchannel("A").point(
                                lambda value, p=progress: value * p // 1000))
                        rise = 0
                        if kind in ("words-up", "letters-up"):
                            rise = int((item["height"] * 0.6) * (1000 - progress) // 1000)
                        layers.append((sprite, (int(base + piece["dx"]),
                                                int(y + piece["dy"] + rise))))
                    x = x - item["width"] if rtl else x + item["width"]
            opacity = _opacity(project, clip, local)
            if opacity < 10000:
                for index in range(first, len(layers)):
                    if opacity <= 0:
                        continue
                    sprite, position = layers[index]
                    faded = sprite.copy()
                    faded.putalpha(faded.getchannel("A").point(
                        lambda value, o=opacity: value * o // 10000))
                    layers[index] = (faded, position)
    return layers


# ------------------------------------------------------------------ frame
def render_frame(project, root, frame_index):
    """Compile and preview one absolute frame as detached, row-major RGBA8 bytes.

    Rejects an out-of-range index, more than one enabled video track, more than one enabled text
    track, a graphics track, and any clip whose asset cannot be decoded. Audio tracks and disabled
    tracks are ignored — a frame has no samples; gaps stay transparent.
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
    # A frame is pixels only: an audio track contributes nothing to it and is skipped (the mixer
    # writes it), while a graphics track is refused because nothing in this build draws it.
    for index, track in enumerate(p["tracks"]):
        if track["enabled"] and track["kind"] not in ("video", "text", "audio"):
            raise PreviewError("V02", f"$.tracks[{index}]",
                               f"only video and text tracks are drawn; {track['kind']} has no renderer")
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
