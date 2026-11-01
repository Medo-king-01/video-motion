#!/usr/bin/env python3
"""Convert a Theatre.js project state into the studio's timeline format.

Theatre.js Studio is a great place to *author* motion (scrub, drag keyframes, tweak curves), but its
runtime is real-time and DOM-shaped, while a reel is rendered frame by frame. So: author in Studio →
export the state JSON → import it here → all three engines use the same deterministic timeline math
(`templates/render/lib/motion.js`, its tested R copy, and `templates/procedural-reels/motion.py`).

    python3 tools/theatre_import.py state.json                    # write <name>.timeline.json next to it
    python3 tools/theatre_import.py state.json --out tl.json --offset 18.5
    python3 tools/theatre_import.py state.json --list              # what is inside, no conversion

In Studio: Project → Export → "State" (or `studio.createContentOfSaveFile('<project id>')`).
Keyframes are mapped to `{t, v, ease}`. Each Theatre keyframe carries `handles: [[out],[in]]`; the
outgoing handle of a keyframe and the incoming handle of the next one give the segment's
`[x1, y1, x2, y2]` cubic-bezier. Vector props (`{x, y}`) become one track per component, so track
names look like `Object.path.to.prop` or `Card.position.x`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_EASE = [0.42, 0.0, 0.58, 1]


def _pair(handles, side: int):
    """Theatre stores per-keyframe handles as [[out],[in]] (or {out, in}); fall back to a default."""
    if isinstance(handles, dict):
        h = handles.get("out" if side == 0 else "in")
    elif isinstance(handles, list) and len(handles) == 2 and all(isinstance(v, (list, tuple)) for v in handles):
        h = handles[side]
    elif isinstance(handles, list) and len(handles) == 4 and all(isinstance(v, (int, float)) for v in handles):
        h = handles[0:2] if side == 0 else handles[2:4]
    else:
        return None
    if isinstance(h, (list, tuple)) and len(h) >= 2:
        return [float(h[0]), float(h[1])]
    return None


def _ease_between(a: dict, b: dict):
    out_a = _pair(a.get("handles"), 0)
    in_b = _pair(b.get("handles"), 1)
    if out_a and in_b:
        return [round(out_a[0], 4), round(out_a[1], 4), round(in_b[0], 4), round(in_b[1], 4)]
    return DEFAULT_EASE


def _split(value) -> dict[str, float | list[float]]:
    """Unwrap Theatre's {value: …} payloads; explode vectors into components keyed by sub-path."""
    if isinstance(value, dict) and "value" in value:
        return _split(value["value"])
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return {"": float(value)}
    if isinstance(value, list) and all(isinstance(v, (int, float)) for v in value):
        return {"": [float(v) for v in value]}
    if isinstance(value, dict):
        out: dict[str, float | list[float]] = {}
        for k, sub in value.items():
            for sk, sv in _split(sub).items():
                out[f"{k}.{sk}" if sk else k] = sv
        return out
    return {}


def _track_from_keyframes(keyframes: list[dict]) -> dict[str, list[dict]]:
    """One {t, v, ease} list per component path (empty path = the prop itself)."""
    tracks: dict[str, list[dict]] = {}
    for i, kf in enumerate(keyframes):
        for sub, v in _split(kf.get("value")).items():
            item = {"t": round(float(kf.get("position", 0)), 4), "v": v}
            if i:
                item["ease"] = _ease_between(keyframes[i - 1], kf)
            tracks.setdefault(sub, []).append(item)
    return tracks


def convert(state: dict, offset: float = 0.0, only_sheet: str | None = None) -> dict:
    sheets = state.get("sheetsById") or {}
    tracks: dict[str, list] = {}
    duration = 0.0
    for sheet_name, sheet in sheets.items():
        if only_sheet and sheet_name != only_sheet:
            continue
        seq = sheet.get("sequence") or {}
        for obj_name, obj in (seq.get("tracksByObject") or {}).items():
            names = {tid: path for path, tid in (obj.get("trackIdByPropPath") or {}).items()}
            for key, track in (obj.get("trackData") or {}).items():
                label = names.get(key, key)
                try:
                    label = ".".join(json.loads(label)) if label.startswith("[") else str(label)
                except json.JSONDecodeError:
                    pass
                kfs = track.get("keyframes") if isinstance(track, dict) else None
                if not kfs:
                    continue
                converted = _track_from_keyframes(kfs)
                for sub, items in converted.items():
                    if offset:
                        for item in items:
                            item["t"] = round(item["t"] + offset, 4)
                    name = f"{obj_name}.{label}" + (f".{sub}" if sub else "")
                    tracks[name] = items
                    duration = max(duration, items[-1]["t"])
        # A shorter track set still lasts as long as the sheet's sequence.
        if seq.get("length"):
            duration = max(duration, float(seq["length"]) + offset)
    return {
        "_doc": "Generated by tools/theatre_import.py from a Theatre.js state export. "
                "Play it with timeline(spec).at(t) in either engine.",
        "source": {"theatre": True, "sheets": list(sheets) if not only_sheet else [only_sheet],
                   "offset": offset},
        "duration": round(duration, 4),
        "tracks": tracks,
    }


def list_state(state: dict) -> None:
    for sheet_name, sheet in (state.get("sheetsById") or {}).items():
        seq = sheet.get("sequence") or {}
        print(f"sheet {sheet_name!r} · length {seq.get('length', '?')}")
        for obj_name, obj in (seq.get("tracksByObject") or {}).items():
            names = {tid: path for path, tid in (obj.get("trackIdByPropPath") or {}).items()}
            for key, track in (obj.get("trackData") or {}).items():
                kfs = track.get("keyframes") if isinstance(track, dict) else []
                label = names.get(key, key)
                try:
                    label = ".".join(json.loads(label)) if label.startswith("[") else str(label)
                except json.JSONDecodeError:
                    pass
                print(f"  {obj_name}.{label:<24} {len(kfs or [])} keyframe(s)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("state")
    ap.add_argument("--out")
    ap.add_argument("--offset", type=float, default=0.0, help="shift every keyframe (e.g. scene start time)")
    ap.add_argument("--sheet", help="only convert this sheet")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    src = Path(args.state)
    if not src.is_file():
        print(f"not found: {src}")
        return 1
    state = json.loads(src.read_text(encoding="utf-8"))
    if args.list:
        list_state(state)
        return 0
    out = convert(state, only_sheet=args.sheet, offset=args.offset)
    if not out["tracks"]:
        print("no keyframe tracks found — export the State (not a project file) from Theatre Studio")
        return 1
    dest = Path(args.out) if args.out else src.with_suffix(".timeline.json")
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"theatre: {len(out['tracks'])} track(s), {out['duration']}s -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
