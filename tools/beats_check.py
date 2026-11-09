#!/usr/bin/env python3
"""Check plan/beats.json against the studio schema — shape and semantics.

    python3 tools/beats_check.py projects/<slug>               # <project>/plan/beats.json
    python3 tools/beats_check.py path/to/plan/beats.json
    python3 tools/beats_check.py path/to/plan/beats.json --quiet

`medo-motion/schema/beats.schema.json` is the documented contract (external tooling, editors);
this tool is the stdlib-only checker for the same contract plus the cross-field invariants a
JSON Schema cannot express: bounds ↔ scenes ↔ duration, the frames arithmetic, index sequence,
contiguity, event containment. It runs no engine and touches no file but the plan.

Exit 0 valid · 1 invalid · 2 cannot read the file. The reel length is the measured VO length;
nothing here prescribes one. Codes: B01 shape · B02 required/measured · B03 frames arithmetic ·
B04 bounds · B05 scene sequence/contiguity · B06 scene field consistency · B07 duplicate scene id.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

EPS = 1e-6
START_TOL = 0.05      # a hand-set first cut; vo_length.py writes exactly 0
DURATION_TOL = 0.15   # last scene end vs duration — same tolerance reel_lint.py uses for S02
DUR_TOL = 0.005       # dur field vs end - start
TOP_KEYS = {"duration", "fps", "frames", "bounds", "audio", "note", "scenes"}
SCENE_KEYS = {"index", "id", "start", "end", "dur", "frames", "theme", "ui", "events"}
EVENT_KEYS = {"t", "what"}
THEMES = {"dark", "light"}
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "medo-motion" / "schema" / "beats.schema.json"


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _str(v: Any, min_len: int = 1) -> bool:
    return isinstance(v, str) and len(v.strip()) >= min_len


def _shape_top(d: dict) -> list[str]:
    errors: list[str] = []
    for key in d:
        if key not in TOP_KEYS:
            errors.append(f"B01 unknown key {key!r} — allowed: {', '.join(sorted(TOP_KEYS))}")
    duration = d.get("duration", None)
    if "duration" not in d:
        errors.append("B01 missing required key 'duration' (null for a pre-VO draft)")
    elif duration is not None and not _num(duration):
        errors.append("B01 'duration' must be a finite number of seconds or null")
    if "fps" in d and (not _num(d["fps"]) or not (0 < d["fps"] <= 240)):
        errors.append("B01 'fps' must be a number in (0, 240]")
    if "frames" in d and (not _int(d["frames"]) or d["frames"] < 0):
        errors.append("B01 'frames' must be an integer >= 0")
    if "bounds" in d:
        bounds = d["bounds"]
        if not isinstance(bounds, list) or len(bounds) < 2:
            errors.append("B01 'bounds' must be an array with at least 2 points (0 and duration)")
        elif any(not _num(b) or b < 0 for b in bounds):
            errors.append("B01 'bounds' entries must be finite numbers >= 0")
    if "audio" in d and not _str(d["audio"]):
        errors.append("B01 'audio' must be a non-empty string path")
    if "note" in d and not isinstance(d["note"], str):
        errors.append("B01 'note' must be a string")
    if "scenes" not in d:
        errors.append("B01 missing required key 'scenes' ([] for a pre-VO draft)")
    elif not isinstance(d["scenes"], list):
        errors.append("B01 'scenes' must be an array")
    return errors


def _shape_scene(s: Any, i: int) -> list[str]:
    errors: list[str] = []
    where = f"scene {i + 1}"
    if not isinstance(s, dict):
        return [f"B01 {where}: must be an object"]
    for key in s:
        if key not in SCENE_KEYS:
            errors.append(f"B01 {where}: unknown key {key!r} — allowed: {', '.join(sorted(SCENE_KEYS))}")
    if not _int(s.get("index")) or s["index"] < 1:
        errors.append(f"B01 {where}: 'index' must be an integer >= 1")
    if "id" in s and not _str(s["id"]):
        errors.append(f"B01 {where}: 'id' must be a non-empty string")
    for key in ("start", "end"):
        if not _num(s.get(key)) or s[key] < 0:
            errors.append(f"B01 {where}: {key!r} must be a finite number >= 0")
    if "dur" in s and (not _num(s["dur"]) or s["dur"] < 0):
        errors.append(f"B01 {where}: 'dur' must be a finite number >= 0")
    if "frames" in s and (not _int(s["frames"]) or s["frames"] < 0):
        errors.append(f"B01 {where}: 'frames' must be an integer >= 0")
    if "theme" in s and s["theme"] not in THEMES:
        errors.append(f"B01 {where}: 'theme' must be one of {sorted(THEMES)}")
    if "ui" in s and not isinstance(s["ui"], bool):
        errors.append(f"B01 {where}: 'ui' must be a boolean")
    events = s.get("events", [])
    if "events" in s and not isinstance(events, list):
        errors.append(f"B01 {where}: 'events' must be an array of {{t, what}}")
    elif isinstance(events, list):
        for j, ev in enumerate(events):
            if not isinstance(ev, dict):
                errors.append(f"B01 {where} event {j + 1}: must be an object")
                continue
            for key in ev:
                if key not in EVENT_KEYS:
                    errors.append(f"B01 {where} event {j + 1}: unknown key {key!r}")
            if not _num(ev.get("t")) or ev["t"] < 0:
                errors.append(f"B01 {where} event {j + 1}: 't' must be a finite number >= 0")
            if not _str(ev.get("what")):
                errors.append(f"B01 {where} event {j + 1}: 'what' must be a non-empty string")
    return errors


def _semantics(d: dict) -> list[str]:
    errors: list[str] = []
    duration, fps, frames = d["duration"], d["fps"], d["frames"]
    scenes, bounds = d["scenes"], d["bounds"]

    expect_frames = round(duration * fps)
    if frames != expect_frames:
        errors.append(f"B03 'frames' {frames} != round(duration {duration:.3f} × fps {fps:g}) "
                      f"= {expect_frames}")

    if bounds[0] != 0:
        errors.append(f"B04 'bounds' must start at 0, got {bounds[0]:g}")
    for i in range(1, len(bounds)):
        if bounds[i] < bounds[i - 1] - EPS:
            errors.append(f"B04 'bounds' not non-decreasing at index {i} ({bounds[i - 1]:g} → {bounds[i]:g})")
    if abs(bounds[-1] - duration) > DURATION_TOL:
        errors.append(f"B04 last 'bounds' point {bounds[-1]:.3f} s != duration {duration:.3f} s")
    if len(bounds) != len(scenes) + 1:
        errors.append(f"B04 {len(bounds)} bounds for {len(scenes)} scenes — expected scenes + 1")

    for i, s in enumerate(scenes):
        where = f"scene {i + 1}"
        if s["index"] != i + 1:
            errors.append(f"B05 {where}: 'index' is {s['index']}, expected {i + 1} (sequential from 1)")
        if s["end"] <= s["start"]:
            errors.append(f"B05 {where}: end {s['end']:g} must be after start {s['start']:g}")
        if i == 0 and s["start"] > START_TOL:
            errors.append(f"B05 the first scene starts at {s['start']:g} s, not 0")
        if i > 0 and abs(s["start"] - scenes[i - 1]["end"]) > EPS:
            errors.append(f"B05 {where}: starts at {s['start']:.4f} s but the previous scene ends at "
                          f"{scenes[i - 1]['end']:.4f} s — scenes must be contiguous")
        if len(bounds) == len(scenes) + 1:
            if abs(s["start"] - bounds[i]) > EPS or abs(s["end"] - bounds[i + 1]) > EPS:
                errors.append(f"B04 {where}: [{s['start']:.4f}, {s['end']:.4f}] does not match "
                              f"bounds[{i}:{i + 2}] [{bounds[i]:.4f}, {bounds[i + 1]:.4f}]")
        if "dur" in s and abs(s["dur"] - (s["end"] - s["start"])) > DUR_TOL:
            errors.append(f"B06 {where}: 'dur' {s['dur']:.4f} != end - start {s['end'] - s['start']:.4f}")
        if "frames" in s:
            expect = round((s["end"] - s["start"]) * fps)
            if s["frames"] != expect:
                errors.append(f"B06 {where}: 'frames' {s['frames']} != round(dur × fps) = {expect}")
        for j, ev in enumerate(s.get("events") or []):
            t = ev.get("t") if isinstance(ev, dict) else None
            if _num(t) and not (s["start"] - EPS <= t <= s["end"] + EPS):
                errors.append(f"B06 {where} event {j + 1}: t {t:.3f} s is outside the scene "
                              f"[{s['start']:.3f}, {s['end']:.3f}]")
    if abs(scenes[-1]["end"] - duration) > DURATION_TOL:
        errors.append(f"B05 the last scene ends at {scenes[-1]['end']:.3f} s but duration is {duration:.3f} s")

    seen: dict[str, int] = {}
    for s in scenes:
        sid = s.get("id")
        if sid is not None:
            seen[sid] = seen.get(sid, 0) + 1
    for sid, n in seen.items():
        if n > 1:
            errors.append(f"B07 duplicate scene id {sid!r} ×{n}")
    return errors


def validate(beats: Any) -> list[str]:
    if not isinstance(beats, dict):
        return ["B01 plan/beats.json must be a JSON object"]
    errors = _shape_top(beats)
    scenes = beats.get("scenes")
    if isinstance(scenes, list):
        for i, s in enumerate(scenes):
            errors.extend(_shape_scene(s, i))
    draft = beats.get("duration") is None and "duration" in beats
    if draft:
        if isinstance(scenes, list) and scenes:
            errors.append("B02 a draft (duration null) must have scenes: [] — measure the VO first: "
                          "python3 tools/vo_length.py <vo> --json plan/beats.json")
        return errors
    if any(code.startswith("B01") for code in errors):
        return errors   # shape is broken; semantics would only add noise
    duration, fps, frames, bounds = (beats.get(k) for k in ("duration", "fps", "frames", "bounds"))
    for key, val in (("duration", duration), ("fps", fps), ("frames", frames), ("bounds", bounds),
                     ("scenes", scenes)):
        if val is None and key not in beats:
            errors.append(f"B02 measured beats.json requires {key!r} (tools/vo_length.py writes it)")
    if errors:
        return errors
    if duration <= 0:
        errors.append(f"B02 'duration' must be > 0 when measured, got {duration:g}")
        return errors
    errors.extend(_semantics(beats))
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plan", help="project dir or path to plan/beats.json")
    ap.add_argument("--quiet", action="store_true", help="no OK line, only failures")
    a = ap.parse_args()

    path = Path(a.plan)
    if path.is_dir():
        path = path / "plan" / "beats.json"
    if not path.is_file():
        print(f"!! cannot read {path} — no such file", file=sys.stderr)
        return 2
    try:
        beats = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"!! cannot parse {path}: {e}", file=sys.stderr)
        return 2

    errors = validate(beats)
    if errors:
        print(f"!! {path} — {len(errors)} problem(s)")
        for e in errors:
            print(f"!! {e}")
        return 1
    if not a.quiet:
        if beats.get("duration") is None:
            print(f"OK {path} — draft (duration null, scenes empty); measure the VO before rendering")
        else:
            print(f"OK {path} — {len(beats['scenes'])} scenes, {beats['duration']:g} s "
                  f"@ {beats.get('fps', '?')} fps, length = the VO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
