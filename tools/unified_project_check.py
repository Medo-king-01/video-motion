#!/usr/bin/env python3
"""Validate the experimental unified-project media subset; does not render or open assets.

Exit codes: 0 valid, 1 invalid/unsupported, 2 unreadable or invalid JSON.
Structural checks interpret the deliberately small vocabulary used by the bundled schema;
semantic checks cover cross-field constraints. This is not a general JSON Schema validator.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "medo-motion/schema/unified-project.schema.json"
MAX_INT = 9007199254740991


def _shape(value, schema, root, path="$", errors=None):
    if errors is None:
        errors = []
    supported = {"$schema", "$id", "$defs", "$ref", "title", "description", "type", "properties",
                 "required", "additionalProperties", "const", "enum", "minLength", "pattern",
                 "minimum", "maximum", "items", "minItems", "maxItems", "allOf", "if", "then", "not"}
    unknown = set(schema) - supported
    if unknown:
        raise ValueError(f"Unsupported schema keywords: {sorted(unknown)}")
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise ValueError(f"Unsupported schema reference: {ref}")
        return _shape(value, root["$defs"][ref.split("/")[-1]], root, path, errors)
    typ = schema.get("type")
    matches = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
    }
    if typ and (typ not in matches or not matches[typ](value)):
        errors.append(f"U01 {path}: expected {typ}")
        return errors
    if "const" in schema and value != schema["const"]:
        errors.append(f"U01 {path}: expected {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"U01 {path}: invalid value {value!r}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or ("pattern" in schema and not re.search(schema["pattern"], value)):
            errors.append(f"U01 {path}: invalid string")
    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            errors.append(f"U01 {path}: integer out of range")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            errors.append(f"U01 {path}: invalid number of items")
        if "items" in schema:
            for i, item in enumerate(value):
                _shape(item, schema["items"], root, f"{path}[{i}]", errors)
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"U01 {path}.{key}: required")
        for key, item in value.items():
            if key in props:
                _shape(item, props[key], root, f"{path}.{key}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"U01 {path}.{key}: unknown field")
    for sub in schema.get("allOf", []):
        _shape(value, sub, root, path, errors)
    if "if" in schema and not _shape(value, schema["if"], root, path):
        _shape(value, schema.get("then", {}), root, path, errors)
    if "not" in schema and not _shape(value, schema["not"], root, path):
        errors.append(f"U01 {path}: forbidden shape")
    return errors


def _safe_uri(uri):
    # Portable paths only. Symlink containment must also be checked when opening an asset.
    return (not any(ord(c) < 32 or ord(c) == 127 for c in uri)
            and "\\" not in uri and ":" not in uri
            and all(part not in ("", ".", "..") for part in uri.split("/")))



def _run_errors(path, text):
    """U12: a run is a styled range of one text block, and it may only cut at a word boundary.

    Cutting inside a word would hand the shaper two halves of a joined Arabic word and print the
    isolated letterforms — a wrong picture that looks like a rendering bug, so it is refused here.
    """
    errors = []
    value = text["value"]
    runs = text.get("runs") or []
    previous_end = 0
    for index, run in enumerate(runs):
        loc = f"{path}.runs[{index}]"
        start, end = run["start"], run["end"]
        if start >= end:
            errors.append(f"U12 {loc}: start must come before end")
            continue
        if end > len(value):
            errors.append(f"U12 {loc}.end: past the end of the text ({len(value)} characters)")
            continue
        if start < previous_end:
            errors.append(f"U12 {loc}: runs must be sorted and must not overlap")
        previous_end = max(previous_end, end)
        if start > 0 and value[start - 1].strip():
            errors.append(f"U12 {loc}.start: a run must begin at a word boundary")
        if end < len(value) and value[end].strip():
            errors.append(f"U12 {loc}.end: a run must end at a word boundary")
        if not {"color", "size", "font"} & set(run):
            errors.append(f"U12 {loc}: a run that changes nothing is not a run")
    return errors


def validate(project):
    """Return diagnostic strings. No file access or mutation of the input project."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = _shape(project, schema, schema)
    if errors:
        return errors
    p = project["profile"]
    fps = p["fps"]
    tb = project["timebase"]
    if math.gcd(fps["num"], fps["den"]) != 1:
        errors.append("U02 $.profile.fps: fraction must be reduced")
    if tb * fps["den"] % fps["num"] or tb % p["sampleRate"]:
        errors.append("U02 $.timebase: frame and sample boundaries must be integer ticks")

    ids = {project["id"]}
    assets = {}

    def add_id(ident, path):
        if ident in ids:
            errors.append(f"U03 {path}: duplicate id {ident!r}")
        ids.add(ident)

    for i, asset in enumerate(project["assets"]):
        path = f"$.assets[{i}]"
        add_id(asset["id"], path + ".id")
        assets[asset["id"]] = asset
        if not _safe_uri(asset["uri"]):
            errors.append(f"U04 {path}.uri: expected safe project-relative path")
        streams = asset.get("streams")
        if streams is not None:
            if asset["kind"] != "video":
                errors.append(f"U09 {path}.streams: only a video asset has streams to choose")
            if set(streams) - {"video", "audio"}:
                errors.append(f"U09 {path}.streams: unknown stream key")
    texts = {}
    for i, text in enumerate(project.get("texts") or []):
        path = f"$.texts[{i}]"
        add_id(text["id"], path + ".id")
        texts[text["id"]] = text
        if text["direction"] == "rtl" and not any("\u0600" <= ch <= "\u06ff" for ch in text["value"]):
            errors.append(f"U10 {path}.direction: rtl text with no Arabic letters")
        if text["direction"] == "ltr" and any("\u0600" <= ch <= "\u06ff" for ch in text["value"]):
            errors.append(f"U10 {path}.direction: ltr text with Arabic letters")
        animation = text.get("animation")
        if animation is not None:
            if animation["kind"] == "none" and len(animation) > 1:
                errors.append(f"U11 {path}.animation: `none` carries no timing")
            if animation["kind"].startswith("words-") and not text.get("wrap", False):
                value_words = [word for word in text["value"].split() if word]
                if len(value_words) < 2:
                    errors.append(f"U11 {path}.animation: a word animation needs more than one word")
            if animation["kind"].startswith("letters-"):
                letters = [char for char in text["value"] if char.strip()]
                if len(letters) < 2:
                    errors.append(f"U11 {path}.animation: a letter animation needs more than one letter")
        errors.extend(_run_errors(path, text))
    for i, track in enumerate(project["tracks"]):
        path = f"$.tracks[{i}]"
        add_id(track["id"], path + ".id")
        ranges = []
        for j, clip in enumerate(track["clips"]):
            loc = f"{path}.clips[{j}]"
            add_id(clip["id"], loc + ".id")
            end = clip["start"] + clip["duration"]
            if end > project["duration"] or end > MAX_INT:
                errors.append(f"U05 {loc}: clip exceeds project duration")
            ranges.append((clip["start"], end, loc))
            effects = {}
            for k, effect in enumerate(clip["effects"]):
                epath = f"{loc}.effects[{k}]"
                add_id(effect["id"], epath + ".id")
                effects[effect["id"]] = effect
                if (effect["type"], track["kind"]) not in {("opacity", "video"), ("opacity", "text"),
                                                           ("gain", "audio")}:
                    errors.append(f"U06 {epath}: effect incompatible with track")
                maximum = 10000 if effect["type"] == "opacity" else 20000
                if effect["params"]["value"] > maximum:
                    errors.append(f"U06 {epath}.params.value: value outside effect range")
            seen_curves = set()
            for k, curve in enumerate(clip["keyframes"]):
                kpath = f"{loc}.keyframes[{k}]"
                eid = curve["effectId"]
                if eid in seen_curves:
                    errors.append(f"U06 {kpath}: duplicate curve")
                seen_curves.add(eid)
                effect = effects.get(eid)
                if effect is None:
                    errors.append(f"U06 {kpath}.effectId: unknown effect on this clip")
                maximum = 10000 if effect and effect["type"] == "opacity" else 20000
                previous = -1
                for n, point in enumerate(curve["points"]):
                    ppath = f"{kpath}.points[{n}]"
                    if point["t"] <= previous or point["t"] > clip["duration"]:
                        errors.append(f"U06 {ppath}.t: must increase and stay within clip duration")
                    if point["value"] > maximum:
                        errors.append(f"U06 {ppath}.value: value outside effect range")
                    previous = point["t"]
            if clip.get("textId") is not None:
                if track["kind"] != "text":
                    errors.append(f"U10 {loc}: a text clip needs a text track")
                elif clip["textId"] not in texts:
                    errors.append(f"U10 {loc}.textId: unknown text")
                if clip["sourceIn"] != 0:
                    errors.append(f"U10 {loc}.sourceIn: text has no source range")
                continue
            asset = assets.get(clip["assetId"])
            if asset is None:
                errors.append(f"U03 {loc}.assetId: unknown asset")
                continue
            allowed = {"video": {"video", "image"}, "audio": {"audio", "video"},
                       "text": set(), "graphics": set()}
            if asset["kind"] not in allowed[track["kind"]]:
                errors.append(f"U05 {loc}: asset incompatible with track")
            speed = clip.get("speed") or {"num": 1, "den": 1}
            if math.gcd(speed["num"], speed["den"]) != 1:
                errors.append(f"U08 {loc}.speed: fraction must be reduced")
            if speed["num"] < 1 or speed["den"] < 1:
                errors.append(f"U08 {loc}.speed: must be positive")
            source_end = clip["sourceIn"] + -(-clip["duration"] * speed["num"] // speed["den"])
            if asset["kind"] != "image" and (source_end > asset["duration"] or source_end > MAX_INT):
                errors.append(f"U05 {loc}: source range exceeds asset duration")
            if asset["kind"] == "image" and clip["sourceIn"] != 0:
                errors.append(f"U05 {loc}.sourceIn: image source must start at zero")
        ranges.sort()
        for left, right in zip(ranges, ranges[1:], strict=False):
            if right[0] < left[1]:
                errors.append(f"U05 {right[2]}: overlaps another clip on this track")
        by_clip = {clip["id"]: clip for clip in track["clips"]}
        windows = []
        for k, transition in enumerate(track.get("transitions") or []):
            tpath = f"{path}.transitions[{k}]"
            add_id(transition["id"], tpath + ".id")
            if track["kind"] not in ("video", "audio"):
                errors.append(f"U07 {tpath}: a crossfade needs a video or audio track")
            source = by_clip.get(transition["fromClipId"])
            target = by_clip.get(transition["toClipId"])
            if source is None or target is None:
                errors.append(f"U07 {tpath}: both clips must live on this track")
                continue
            if source["id"] == target["id"]:
                errors.append(f"U07 {tpath}: a transition needs two different clips")
                continue
            if source["start"] + source["duration"] != target["start"]:
                errors.append(f"U07 {tpath}: clips are not adjacent — no cut to dissolve")
                continue
            if transition["kind"] not in ("crossfade", "wipe"):
                errors.append(f"U07 {tpath}.kind: {transition['kind']!r} is not a transition this build knows")
                continue
            if transition["kind"] == "wipe" and track["kind"] != "video":
                errors.append(f"U07 {tpath}: a wipe needs a video track (audio has no geometry)")
                continue
            length = transition["duration"]
            if length % 2:
                errors.append(f"U07 {tpath}.duration: must be even so the cut sits mid-transition")
                continue
            half = length // 2
            if half > min(source["duration"], target["duration"]):
                errors.append(f"U07 {tpath}.duration: longer than the clips it joins")
                continue
            cut = target["start"]
            windows.append((cut - half, cut + half, tpath))
        windows.sort()
        for left, right in zip(windows, windows[1:], strict=False):
            if right[0] < left[1]:
                errors.append(f"U07 {right[2]}: overlaps another transition on this track")
    return errors


def _unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON key {key!r}")
        obj[key] = value
    return obj


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="path to project.json")
    args = parser.parse_args(argv)
    try:
        project = json.loads(args.project.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs,
                             parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid constant {value}")))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Cannot read project: {exc}", file=sys.stderr)
        return 2
    errors = validate(project)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Valid experimental unified-project media subset (assets not opened; no render support implied).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
