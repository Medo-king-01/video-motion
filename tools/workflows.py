#!/usr/bin/env python3
"""The eight working methods, expressed as edits to one unified project.

`docs/unified-editor-roadmap.md` §4 lists the methods the studio must support: Free Edit,
Script to Video, Talking Head, Montage, Podcast, Explainer, Product Review and Motion Design.
The rule that matters here is stated there too: **each one produces an editable timeline**, not a
finished video. So this module contains no renderer — only arrangements of clips, captions and
crossfades over the project the caller already has assets for.

Every builder returns a schema-1.3 project that passes `unified_project_check.validate` and is
renderable by `adapter_p` (stills, crossfades, Arabic captions). Audio beds are *not* synthesised:
a method that needs sound asks for an audio asset and adds it to a second track, keeping the
"no silent invention" rule.

Usage:
  python3 tools/workflows.py --list
  python3 tools/workflows.py montage --media shots/ --captions lines.txt --out project.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from unified_project_check import validate  # noqa: E402

TIMEBASE = 240_000
PROFILE = {"width": 1080, "height": 1920, "fps": {"num": 30, "den": 1}, "sampleRate": 48_000}

#: name -> (title, clip lengths in seconds, crossfade in seconds, captions per clip)
METHODS = {
    "free": ("Free Edit", [4.0, 4.0, 4.0, 4.0], 0.0, False),
    "script": ("Script to Video", [3.0, 3.0, 3.0, 3.0], 0.0, True),
    "talking-head": ("Talking Head", [12.0, 12.0], 0.0, True),
    "montage": ("Montage", [1.0, 1.0, 1.0, 1.0, 1.0, 1.0], 0.5, False),
    "podcast": ("Podcast", [30.0, 30.0], 0.0, True),
    "explainer": ("Explainer", [5.0, 5.0, 2.5, 2.5], 0.0, True),
    "product-review": ("Product Review", [6.0, 3.0, 3.0, 6.0], 0.5, True),
    "motion-design": ("Motion Design", [1.5, 2.5, 1.5, 2.5], 0.5, False),
}

CAPTION_FONTS = "Cairo"


class WorkflowError(ValueError):
    def __init__(self, code, message):
        self.code, self.message = code, message
        super().__init__(f"{code} {message}")


def scan_media(folder: Path, *, pattern="*.ppm") -> list[dict]:
    """Describe the stills in `folder` as assets, ordered by name, hashed for the checker."""
    folder = Path(folder)
    files = sorted(folder.glob(pattern))
    if not files:
        raise WorkflowError("W01", f"no {pattern} files in {folder}")
    assets = []
    for index, path in enumerate(files):
        payload = path.read_bytes()
        assets.append({"id": f"a{index + 1}", "kind": "image", "uri": f"{folder.name}/{path.name}",
                       "sha256": hashlib.sha256(payload).hexdigest()})
    return assets


INK_LIGHT = "#f3f2f1"
INK_DARK = "#0c0c0d"
CONTRAST_THRESHOLD = 140


def mean_luminance(root: Path, uri: str, band=(0.35, 0.65)) -> int | None:
    """Mean luminance (0..255) of the band a caption occupies, or None when it cannot be read.

    The whole frame is the wrong sample: a dark frame with a bright shape in the middle would
    still get white ink on top of that shape. The band is the horizontal strip the caption sits
    in, so a caption over a bright object gets dark ink and stays readable.
    """
    try:
        data = (Path(root) / uri).read_bytes()
    except OSError:
        return None
    if not data.startswith(b"P6"):
        return None
    parts = data.split(b"\n", 3)
    if len(parts) < 4:
        return None
    try:
        width, height = (int(value) for value in parts[1].split())
    except ValueError:
        return None
    body = parts[3]
    if len(body) < width * height * 3:
        return None
    first = max(0, int(height * band[0]))
    last = min(height, max(first + 1, int(round(height * band[1]))))
    pixels = body[first * width * 3: last * width * 3]
    if not pixels:
        return None
    total = sum(pixels[0::3]) * 299 + sum(pixels[1::3]) * 587 + sum(pixels[2::3]) * 114
    return total // (1000 * max(1, len(pixels) // 3))


def _ink_for(root: Path | None, asset: dict) -> str:
    if root is None:
        return INK_LIGHT
    luminance = mean_luminance(root, asset["uri"])
    if luminance is None:
        return INK_LIGHT
    return INK_DARK if luminance >= CONTRAST_THRESHOLD else INK_LIGHT


def _ticks(seconds: float) -> int:
    return int(round(seconds * TIMEBASE))


def _captions(lines, *, size=64, duration_ticks):
    texts = []
    for index, line in enumerate(lines):
        texts.append({"id": f"cap{index + 1}", "value": line, "font": CAPTION_FONTS, "size": size,
                      "color": "#f3f2f1", "align": "center",
                      "direction": "rtl" if any("\u0600" <= ch <= "\u06ff" for ch in line) else "ltr"})
    return texts


def build(name: str, *, assets: list[dict], captions: list[str] | None = None,
          audio: dict | None = None, profile: dict | None = None, seed: int = 0,
          root: Path | None = None) -> dict:
    """Arrange the caller's assets into one editable project for `name`."""
    if name not in METHODS:
        raise WorkflowError("W02", f"unknown method {name!r}; one of {', '.join(METHODS)}")
    if not assets:
        raise WorkflowError("W01", "a method needs at least one still asset")
    title, lengths, fade_seconds, wants_captions = METHODS[name]
    captions = list(captions or [])
    if wants_captions and not captions:
        raise WorkflowError("W03", f"{name} needs captions; pass --captions (one line per clip)")
    if len(lengths) > 1 and len(assets) == 1:
        # One still can carry a whole method; the clips then repeat the same picture.
        assets = [dict(assets[0], id=f"{assets[0]['id']}-{index}") for index in range(len(lengths))]

    clips = []
    start = 0
    fade = _ticks(fade_seconds)
    for index, seconds in enumerate(lengths):
        asset = assets[index % len(assets)]
        duration = _ticks(seconds)
        clips.append({"id": f"c{index + 1}", "kind": "media", "assetId": asset["id"],
                      "start": start, "duration": duration, "sourceIn": 0,
                      "effects": [], "keyframes": []})
        start += duration
    transitions = []
    if fade:
        for index in range(len(clips) - 1):
            transitions.append({"id": f"t{index + 1}", "kind": "crossfade",
                                "fromClipId": clips[index]["id"], "toClipId": clips[index + 1]["id"],
                                "duration": fade})
    texts = _captions(captions, duration_ticks=start) if wants_captions else []
    if texts:
        # The ink follows the picture it sits on: measured, not guessed per client.
        for index, text in enumerate(texts):
            text["color"] = _ink_for(root, assets[index % len(assets)])
    tracks = [{"id": "v1", "kind": "video", "enabled": True, "clips": clips,
               "transitions": transitions}]
    if texts:
        # Every caption owns a slice of the picture it belongs to; a clip with three captions is
        # split in three, so two captions can never claim the same ticks.
        buckets: dict[int, list[int]] = {}
        for index in range(len(texts)):
            buckets.setdefault(index % len(clips), []).append(index)
        text_clips = []
        for clip_index, indices in sorted(buckets.items()):
            clip = clips[clip_index]
            slice_length = clip["duration"] // len(indices)
            for position, index in enumerate(indices):
                start_tick = clip["start"] + position * slice_length
                length = slice_length if position < len(indices) - 1 else \
                    clip["start"] + clip["duration"] - start_tick
                text_clips.append({"id": f"x{index + 1}", "kind": "media", "textId": texts[index]["id"],
                                   "start": start_tick, "duration": length, "sourceIn": 0,
                                   "effects": [], "keyframes": []})
        text_clips.sort(key=lambda clip: clip["start"])
        tracks.append({"id": "tx1", "kind": "text", "enabled": True, "clips": text_clips,
                       "transitions": []})

    all_assets = list({asset["id"]: asset for asset in assets}.values())
    if audio is not None:
        all_assets.append(audio)
        tracks.append({"id": "au1", "kind": "audio", "enabled": True, "clips": [
            {"id": "m1", "kind": "media", "assetId": audio["id"], "start": 0,
             "duration": min(start, audio["duration"]), "sourceIn": 0, "effects": [], "keyframes": []}],
            "transitions": []})

    project = {
        "schemaVersion": "1.3", "id": f"wf-{name}", "name": title,
        "profile": dict(profile or PROFILE), "timebase": TIMEBASE,
        "duration": start, "seed": seed, "assets": all_assets,
        "texts": texts, "tracks": tracks,
    }
    errors = validate(project)
    if errors:
        raise WorkflowError("W04", f"{name} produced an invalid project: " + "; ".join(errors))
    return project


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("method", nargs="?", help="one of: " + ", ".join(METHODS))
    parser.add_argument("--list", action="store_true", help="print the eight methods")
    parser.add_argument("--media", type=Path, help="folder of stills (PPM by default)")
    parser.add_argument("--pattern", default="*.ppm")
    parser.add_argument("--captions", type=Path, help="UTF-8 text file, one caption per line")
    parser.add_argument("--out", type=Path, help="where to write project.json")
    args = parser.parse_args(argv)
    if args.list or not args.method:
        for key, (title, lengths, fade, captions) in METHODS.items():
            print(f"{key:15s} {title:18s} clips={len(lengths)} fade={fade}s captions={captions}")
        return 0
    if not args.media or not args.out:
        print("W00 --media and --out are required", file=sys.stderr)
        return 2
    lines = []
    if args.captions:
        lines = [line.strip() for line in args.captions.read_text(encoding="utf-8").splitlines() if line.strip()]
    try:
        project = build(args.method, assets=scan_media(args.media, pattern=args.pattern), captions=lines)
    except WorkflowError as exc:
        print(exc, file=sys.stderr)
        return 1
    args.out.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.method}: {len(project['tracks'])} tracks, {project['duration']} ticks -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
