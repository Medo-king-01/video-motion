#!/usr/bin/env python3
"""Validate a declarative board (`board.json`) against the studio's real vocabularies.

A board is data, not code: scenes, six element kinds and moves. This tool refuses anything the
renderer cannot honour — an unknown kind, a colour that is not a brand role, a pose the catalog does
not have, a move the catalog does not ship, an element outside its scene, duplicate ids — so the
interpreter never has to guess.

    python3 tools/board_check.py board.json
    python3 tools/board_check.py board.json --json

Exit codes: 0 valid, 1 invalid/unsupported, 2 unreadable or invalid JSON.

Scope (B2): structure, timing, ids, brand roles, poses and moves. It does not open images, decode
fonts or render; the K interpreter (`render/lib/board.js`) does the drawing and throws on the same
unsupported values.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "medo-motion" / "brand" / "brand.json"
POSES = ROOT / "assets" / "poses" / "poses.json"
MOVES = ROOT / "medo-motion" / "motion" / "moves.json"

KINDS = ("text", "shape", "draw", "data", "person", "image")
ELEMENT_MOVES = ("pixel-list", "orbit", "word-path", "explode", "card-stack", "parallax")
CAMERA_MOVES = ("camera-push", "parallax")
ALIGNS = ("right", "center", "left")
SHAPES = ("rect", "ellipse", "line")
FITS = ("cover", "contain")
SAFE_SRC = re.compile(r"^(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._\-/]+$")


def _no_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON key {key!r}")
        obj[key] = value
    return obj


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError(f"invalid constant {value}")))


def vocabularies() -> tuple[set[str], set[str], set[str]]:
    """Brand palette keys, pose names and executable move ids, read from their owners."""
    palette = set(json.loads(BRAND.read_text(encoding="utf-8"))["palette"])
    poses = set(json.loads(POSES.read_text(encoding="utf-8"))["poses"])
    moves = json.loads(MOVES.read_text(encoding="utf-8"))["families"]["element-moves"]["members"]
    return palette, poses, set(moves)


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _positive(value) -> bool:
    return _number(value) and value > 0


def _non_negative(value) -> bool:
    return _number(value) and value >= 0


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unknown(obj: dict, allowed: set[str], where: str, errors: list[str],
             required: set[str] = frozenset()) -> None:
    """Unknown keys are refused; `required` lists the keys this object cannot omit."""
    for key in sorted(set(obj) - allowed):
        errors.append(f"B01 {where}.{key}: unknown field")
    for key in sorted(set(required) - set(obj)):
        errors.append(f"B01 {where}.{key}: required")


COMMON = {"id", "kind", "x", "y", "z", "at", "move"}
KIND_REQUIRED = {
    "text": {"text", "size"},
    "shape": {"shape", "w", "h"},
    "draw": {"points"},
    "data": {"values", "w", "h"},
    "person": {"pose", "h"},
    "image": {"src", "w", "h"},
}
KIND_FIELDS = {
    "text": {"text", "size", "font", "color", "align", "maxWidth"},
    "shape": {"shape", "w", "h", "fill", "stroke", "strokeWidth", "radius"},
    "draw": {"points", "stroke", "strokeWidth", "arrow"},
    "data": {"values", "w", "h", "fill", "gap"},
    "person": {"pose", "h", "w"},
    "image": {"src", "w", "h", "fit"},
}


def _check_move(move, allowed: tuple[str, ...], where: str, errors: list[str]) -> None:
    if not isinstance(move, dict):
        errors.append(f"B05 {where}: object expected")
        return
    _unknown(move, {"move", "params"}, where, errors, {"move"})
    if move.get("move") not in allowed:
        errors.append(f"B05 {where}.move: {move.get('move')!r} is not one of {list(allowed)}")
    params = move.get("params", {})
    if not isinstance(params, dict):
        errors.append(f"B05 {where}.params: object expected")


def kind_required(kind: str) -> set[str]:
    return KIND_REQUIRED[kind]


def _check_element(element, scene_duration: float, palette: set[str], poses: set[str],
                   where: str, errors: list[str]) -> None:
    if not isinstance(element, dict):
        errors.append(f"B04 {where}: object expected")
        return
    kind = element.get("kind")
    if kind not in KINDS:
        errors.append(f"B04 {where}.kind: {kind!r} is not one of {list(KINDS)}")
        return
    required = {"id", "kind", "x", "y", "z"} | kind_required(kind)
    _unknown(element, COMMON | KIND_FIELDS[kind], where, errors, required)
    if not _text(element.get("id")):
        errors.append(f"B04 {where}.id: nonempty string required")
    for axis in ("x", "y"):
        if not _number(element.get(axis)):
            errors.append(f"B04 {where}.{axis}: finite number required")
    if not isinstance(element.get("z"), int) or isinstance(element.get("z"), bool):
        errors.append(f"B04 {where}.z: integer required")
    at = element.get("at", 0)
    if not _non_negative(at):
        errors.append(f"B04 {where}.at: nonnegative number required")
    elif at >= scene_duration:
        errors.append(f"B04 {where}.at: element starts after its scene ends")
    if "move" in element:
        _check_move(element["move"], ELEMENT_MOVES, f"{where}.move", errors)
    if kind == "text":
        if not _text(element.get("text")):
            errors.append(f"B04 {where}.text: nonempty string required")
        if not _positive(element.get("size")):
            errors.append(f"B04 {where}.size: positive number required")
        if element.get("align", "right") not in ALIGNS:
            errors.append(f"B04 {where}.align: {element.get('align')!r} is not one of {list(ALIGNS)}")
        if "maxWidth" in element and not _positive(element["maxWidth"]):
            errors.append(f"B04 {where}.maxWidth: positive number required")
        if element.get("color", "ink") not in palette:
            errors.append(f"B06 {where}.color: {element.get('color')!r} is not a brand role")
        if "font" in element and not _text(element["font"]):
            errors.append(f"B04 {where}.font: nonempty string required")
    elif kind == "shape":
        if element.get("shape") not in SHAPES:
            errors.append(f"B04 {where}.shape: {element.get('shape')!r} is not one of {list(SHAPES)}")
        if not _positive(element.get("w")) or not _positive(element.get("h")):
            errors.append(f"B04 {where}.w/.h: positive numbers required")
        for key in ("fill", "stroke"):
            if key in element and element[key] not in palette:
                errors.append(f"B06 {where}.{key}: {element[key]!r} is not a brand role")
        if "strokeWidth" in element and not _non_negative(element["strokeWidth"]):
            errors.append(f"B04 {where}.strokeWidth: nonnegative number required")
        if "radius" in element and not _non_negative(element["radius"]):
            errors.append(f"B04 {where}.radius: nonnegative number required")
    elif kind == "draw":
        points = element.get("points")
        if (not isinstance(points, list) or len(points) < 2
                or any(not isinstance(point, list) or len(point) != 2
                       or not all(_number(value) for value in point) for point in points)):
            errors.append(f"B04 {where}.points: a list of [x, y] numbers with at least 2 points")
        if element.get("stroke", "ink") not in palette:
            errors.append(f"B06 {where}.stroke: {element.get('stroke')!r} is not a brand role")
        if not _positive(element.get("strokeWidth", 6)):
            errors.append(f"B04 {where}.strokeWidth: positive number required")
        if "arrow" in element and not isinstance(element["arrow"], bool):
            errors.append(f"B04 {where}.arrow: boolean required")
    elif kind == "data":
        values = element.get("values")
        if (not isinstance(values, list) or not values or len(values) > 12
                or any(not _number(value) for value in values)):
            errors.append(f"B04 {where}.values: 1..12 finite numbers required")
        if not _positive(element.get("w")) or not _positive(element.get("h")):
            errors.append(f"B04 {where}.w/.h: positive numbers required")
        if element.get("fill", "ink") not in palette:
            errors.append(f"B06 {where}.fill: {element.get('fill')!r} is not a brand role")
        gap = element.get("gap", 0.25)
        if not (_number(gap) and 0 <= gap <= 0.9):
            errors.append(f"B04 {where}.gap: number within 0..0.9 required")
    elif kind == "person":
        if element.get("pose") not in poses:
            errors.append(f"B07 {where}.pose: {element.get('pose')!r} is not in assets/poses")
        if not _positive(element.get("h")):
            errors.append(f"B04 {where}.h: positive number required")
        if "w" in element and not _positive(element.get("w")):
            errors.append(f"B04 {where}.w: positive number when present")
    elif kind == "image":
        src = element.get("src")
        if not _text(src) or not SAFE_SRC.match(src):
            errors.append(f"B09 {where}.src: safe project-relative path required")
        if not _positive(element.get("w")) or not _positive(element.get("h")):
            errors.append(f"B04 {where}.w/.h: positive numbers required")
        if element.get("fit", "cover") not in FITS:
            errors.append(f"B04 {where}.fit: {element.get('fit')!r} is not one of {list(FITS)}")


def validate(board, *, palette: set[str] | None = None, poses: set[str] | None = None) -> list[str]:
    """Return diagnostics; empty means the board is renderable by the B2 interpreter."""
    if palette is None or poses is None:
        palette, poses, _ = vocabularies()
    errors: list[str] = []
    if not isinstance(board, dict):
        return ["B00 $: object expected"]
    _unknown(board, {"version", "stage", "duration", "scenes"}, "$", errors,
             {"version", "stage", "duration", "scenes"})
    if board.get("version") != 1:
        errors.append("B00 $.version: only version 1 is defined")
    stage = board.get("stage")
    if not isinstance(stage, dict):
        errors.append("B00 $.stage: object expected")
    else:
        _unknown(stage, {"width", "height", "background"}, "$.stage", errors,
                 {"width", "height", "background"})
        for key in ("width", "height"):
            if not isinstance(stage.get(key), int) or isinstance(stage.get(key), bool) or stage[key] < 1:
                errors.append(f"B02 $.stage.{key}: positive integer required")
        if stage.get("background") not in palette:
            errors.append(f"B06 $.stage.background: {stage.get('background')!r} is not a brand role")
    if not _positive(board.get("duration")):
        errors.append("B00 $.duration: positive number required")

    scenes = board.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return errors + ["B00 $.scenes: nonempty list required"]

    ids: set[str] = set()
    previous_end = 0.0
    total = board.get("duration") if _positive(board.get("duration")) else 0.0
    for index, scene in enumerate(scenes):
        where = f"$.scenes[{index}]"
        if not isinstance(scene, dict):
            errors.append(f"B03 {where}: object expected")
            continue
        _unknown(scene, {"id", "start", "duration", "elements", "camera"}, where, errors,
                 {"id", "start", "duration", "elements"})
        if not _text(scene.get("id")):
            errors.append(f"B03 {where}.id: nonempty string required")
        elif scene["id"] in ids:
            errors.append(f"B03 {where}.id: duplicate id {scene['id']!r}")
        else:
            ids.add(scene["id"])
        start, length = scene.get("start"), scene.get("duration")
        if not _non_negative(start):
            errors.append(f"B03 {where}.start: nonnegative number required")
        if not _positive(length):
            errors.append(f"B03 {where}.duration: positive number required")
        if _non_negative(start) and _positive(length):
            if start < previous_end - 1e-9:
                errors.append(f"B03 {where}.start: scenes may not overlap")
            if start + length > total + 1e-9:
                errors.append(f"B03 {where}: scene exceeds board duration")
            previous_end = max(previous_end, start + length)
        if "camera" in scene:
            _check_move(scene["camera"], CAMERA_MOVES, f"{where}.camera", errors)
        elements = scene.get("elements")
        if not isinstance(elements, list) or not elements:
            errors.append(f"B03 {where}.elements: nonempty list required")
            continue
        if len(elements) > 64:
            errors.append(f"B03 {where}.elements: at most 64 elements per scene")
        for position, element in enumerate(elements):
            location = f"{where}.elements[{position}]"
            _check_element(element, length if _positive(length) else 1.0, palette, poses, location, errors)
            if isinstance(element, dict) and _text(element.get("id")):
                if element["id"] in ids:
                    errors.append(f"B03 {location}.id: duplicate id {element['id']!r}")
                else:
                    ids.add(element["id"])
    return errors


def summary(board) -> dict:
    kinds: dict[str, int] = {}
    for scene in board["scenes"]:
        for element in scene["elements"]:
            kinds[element["kind"]] = kinds.get(element["kind"], 0) + 1
    return {"scenes": len(board["scenes"]), "duration": board["duration"], "kinds": kinds,
            "has_camera": any("camera" in scene for scene in board["scenes"])}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("board", type=Path, nargs="?",
                        default=ROOT / "medo-motion" / "motion" / "boards" / "explainer-sample.json")
    parser.add_argument("--json", action="store_true", help="print a summary instead of a sentence")
    args = parser.parse_args(argv)
    try:
        board = load(args.board)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Cannot read board: {exc}", file=sys.stderr)
        return 2
    errors = validate(board)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(summary(board), ensure_ascii=False, indent=2))
    else:
        counts = summary(board)["kinds"]
        print("Valid board: " + " · ".join(f"{kind}={count}" for kind, count in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
