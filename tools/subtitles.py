#!/usr/bin/env python3
"""SRT/VTT export from the reel's caption copy (B6) — plain text, no shaping, no AI.

Input is `plan/copy.json` (the same file the renderer reads), so subtitles cannot drift from what is on
screen. The builder sorts, merges or refuses overlaps, enforces a minimum reading time, wraps to at most
two lines, and writes SRT and VTT from one cue list. Deterministic: same copy in, same bytes out.

    python3 tools/subtitles.py build plan/copy.json --srt out/ar.srt --vtt out/ar.vtt
    python3 tools/subtitles.py check out/subtitles.json

Exit codes: 0 ok · 1 invalid input/cues · 2 unreadable file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

VERSION = 1
DEFAULTS = {"minDuration": 0.6, "maxChars": 42, "maxLines": 2, "gap": 0.04, "onOverlap": "reject"}
SETTINGS_FIELDS = set(DEFAULTS)
ROOT_FIELDS = {"version", "source", "settings", "cues", "totals"}
CUE_FIELDS = {"id", "start", "end", "lines"}
TOTALS_FIELDS = {"cues", "duration", "first", "last"}
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class SubtitleError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code} {message}")


def _num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def clean(text: str) -> str:
    """Collapse whitespace and drop control characters; keep the words exactly as written."""
    return CONTROL.sub("", str(text)).replace("\r", " ").replace("\n", " ").strip()


def wrap(text: str, max_chars: int, max_lines: int) -> list[str]:
    """Greedy word wrap; raises S04 when the text cannot fit the allowed lines."""
    words = clean(text).split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        if len(word) > max_chars:
            raise SubtitleError("S04", f"word {word!r} is longer than {max_chars} characters")
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        raise SubtitleError("S04", f"text needs {len(lines)} lines, limit is {max_lines}: {text!r}")
    return lines


def build_cues(copy_payload: dict, *, min_duration: float = DEFAULTS["minDuration"],
               max_chars: int = DEFAULTS["maxChars"], max_lines: int = DEFAULTS["maxLines"],
               gap: float = DEFAULTS["gap"], on_overlap: str = DEFAULTS["onOverlap"]) -> list[dict]:
    """Turn caption entries into ordered, non-overlapping, wrapped cues."""
    if on_overlap not in ("reject", "merge"):
        raise SubtitleError("S06", "onOverlap must be 'reject' or 'merge'")
    if not _num(min_duration) or min_duration <= 0:
        raise SubtitleError("S06", "minDuration must be positive")
    if not _num(gap) or gap < 0:
        raise SubtitleError("S06", "gap must be non-negative")
    if not isinstance(max_chars, int) or max_chars < 8 or not isinstance(max_lines, int) or not 1 <= max_lines <= 3:
        raise SubtitleError("S06", "maxChars must be >= 8 and maxLines within 1..3")
    entries = copy_payload.get("copy") if isinstance(copy_payload, dict) else None
    if not isinstance(entries, list) or not entries:
        raise SubtitleError("S01", "copy.json needs a non-empty copy[] list")

    rows = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise SubtitleError("S01", f"copy[{index}]: object required")
        text = clean(entry.get("text", ""))
        if not text:
            raise SubtitleError("S04", f"copy[{index}]: empty text")
        start, end = entry.get("start"), entry.get("end")
        if not _num(start) or not _num(end):
            raise SubtitleError("S03", f"copy[{index}]: start/end must be numbers")
        if start < 0 or end <= start:
            raise SubtitleError("S03", f"copy[{index}]: requires 0 <= start < end")
        cid = str(entry.get("id") or f"cue-{index + 1}")
        rows.append({"id": cid, "start": float(start), "end": float(end), "text": text})
    rows.sort(key=lambda cue: (cue["start"], cue["end"], cue["id"]))

    resolved: list[dict] = []
    for cue in rows:
        if resolved and cue["start"] < resolved[-1]["end"] - 1e-9:
            if on_overlap == "reject":
                raise SubtitleError("S02", f"{cue['id']} overlaps {resolved[-1]['id']}")
            previous = resolved[-1]
            if cue["end"] > previous["end"]:
                previous["end"] = cue["end"]
            previous["text"] = f"{previous['text']} {cue['text']}".strip()
            continue
        resolved.append(cue)

    for index, cue in enumerate(resolved):
        limit = resolved[index + 1]["start"] - gap if index + 1 < len(resolved) else None
        wanted = cue["start"] + min_duration
        if limit is not None:
            if limit <= cue["start"]:
                raise SubtitleError("S03", f"{cue['id']}: no room before the next cue (gap {gap}s)")
            cue["end"] = min(cue["end"], limit)
            if cue["end"] - cue["start"] < min_duration - 1e-9:
                raise SubtitleError(
                    "S03", f"{cue['id']}: {cue['end'] - cue['start']:.3f}s is below minDuration {min_duration}s "
                          "and the next cue starts too soon")
        else:
            cue["end"] = max(cue["end"], wanted)
        cue["lines"] = wrap(cue["text"], max_chars, max_lines)
        del cue["text"]

    errors = validate_cues(resolved, min_duration=min_duration, max_chars=max_chars, max_lines=max_lines)
    if errors:
        raise SubtitleError("S02", "; ".join(errors))
    return [{"id": c["id"], "start": round(c["start"], 3), "end": round(c["end"], 3), "lines": c["lines"]}
            for c in resolved]


def validate_cues(cues: list[dict], *, min_duration: float = DEFAULTS["minDuration"],
                  max_chars: int = DEFAULTS["maxChars"], max_lines: int = DEFAULTS["maxLines"]) -> list[str]:
    errors: list[str] = []
    if not isinstance(cues, list) or not cues:
        return ["S01 cues: non-empty list required"]
    seen = set()
    previous_end = -1.0
    for index, cue in enumerate(cues):
        where = f"cues[{index}]"
        if not isinstance(cue, dict):
            errors.append(f"S01 {where}: object required")
            continue
        if set(cue) != CUE_FIELDS:
            errors.append(f"S01 {where}: needs exactly {sorted(CUE_FIELDS)}")
            continue
        if not isinstance(cue["id"], str) or not cue["id"]:
            errors.append(f"S02 {where}.id: non-empty string required")
        elif cue["id"] in seen:
            errors.append(f"S02 {where}.id: duplicate {cue['id']!r}")
        else:
            seen.add(cue["id"])
        if not _num(cue["start"]) or not _num(cue["end"]):
            errors.append(f"S03 {where}: start/end must be numbers")
            continue
        if cue["start"] < 0 or cue["end"] <= cue["start"]:
            errors.append(f"S03 {where}: requires 0 <= start < end")
        if cue["start"] < previous_end - 1e-9:
            errors.append(f"S02 {where}: overlaps the previous cue")
        if cue["end"] - cue["start"] < min_duration - 1e-9:
            errors.append(f"S03 {where}: shorter than minDuration {min_duration}s")
        previous_end = cue["end"]
        lines = cue["lines"]
        if not isinstance(lines, list) or not lines or any(not isinstance(line, str) or not line.strip() for line in lines):
            errors.append(f"S04 {where}.lines: non-empty strings required")
        elif len(lines) > max_lines:
            errors.append(f"S04 {where}.lines: {len(lines)} lines exceeds {max_lines}")
        elif any(len(line) > max_chars for line in lines):
            errors.append(f"S04 {where}.lines: a line exceeds {max_chars} characters")
    return errors


def _timestamp(seconds: float, separator: str) -> str:
    total_ms = int(round(seconds * 1000))
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{ms:03d}"


def to_srt(cues: list[dict]) -> str:
    blocks = []
    for index, cue in enumerate(cues, 1):
        blocks.append(f"{index}\n{_timestamp(cue['start'], ',')} --> {_timestamp(cue['end'], ',')}\n"
                      + "\n".join(cue["lines"]))
    return "\n\n".join(blocks) + "\n"


def to_vtt(cues: list[dict]) -> str:
    blocks = ["WEBVTT"]
    for cue in cues:
        text = "\n".join(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                         for line in cue["lines"])
        blocks.append(f"{_timestamp(cue['start'], '.')} --> {_timestamp(cue['end'], '.')}\n{text}")
    return "\n\n".join(blocks) + "\n"


def manifest(cues: list[dict], source_path: Path, settings: dict) -> dict:
    payload = source_path.read_bytes()
    return {
        "version": VERSION,
        "source": {"name": source_path.name, "sha256": hashlib.sha256(payload).hexdigest()},
        "settings": dict(settings),
        "cues": cues,
        "totals": {
            "cues": len(cues),
            "duration": round(max(c["end"] for c in cues), 3),
            "first": cues[0]["start"],
            "last": cues[-1]["end"],
        },
    }


def validate_manifest(data: dict) -> list[str]:
    """S01 shape · S02 order/ids · S03 timing · S04 text · S05 totals · S06 settings."""
    if not isinstance(data, dict):
        return ["S01 root: manifest must be an object"]
    if data.get("version") != VERSION:
        return [f"S01 version: only version {VERSION} is accepted"]
    if set(data) != ROOT_FIELDS:
        return [f"S01 root: needs exactly {sorted(ROOT_FIELDS)}"]
    settings = data["settings"]
    if not isinstance(settings, dict) or set(settings) != SETTINGS_FIELDS:
        return [f"S06 settings: needs exactly {sorted(SETTINGS_FIELDS)}"]
    if not isinstance(settings["minDuration"], (int, float)) or settings["minDuration"] <= 0:
        return ["S06 settings.minDuration: positive number required"]
    errors = validate_cues(data["cues"], min_duration=float(settings["minDuration"]),
                           max_chars=int(settings["maxChars"]), max_lines=int(settings["maxLines"]))
    if errors:
        return errors
    totals = data["totals"]
    if not isinstance(totals, dict) or set(totals) != TOTALS_FIELDS:
        return [f"S05 totals: needs exactly {sorted(TOTALS_FIELDS)}"]
    expected = {"cues": len(data["cues"]),
                "duration": round(max(c["end"] for c in data["cues"]), 3),
                "first": data["cues"][0]["start"],
                "last": data["cues"][-1]["end"]}
    for key in TOTALS_FIELDS:
        if totals[key] != expected[key]:
            errors.append(f"S05 totals.{key}: says {totals[key]!r} but cues give {expected[key]!r}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SRT/VTT from plan/copy.json — deterministic, plain text.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="copy.json → SRT + VTT + manifest")
    build.add_argument("copy", type=Path)
    build.add_argument("--srt", type=Path, required=True)
    build.add_argument("--vtt", type=Path, required=True)
    build.add_argument("--manifest", type=Path, default=None)
    build.add_argument("--min", dest="min_duration", type=float, default=DEFAULTS["minDuration"])
    build.add_argument("--max-chars", type=int, default=DEFAULTS["maxChars"])
    build.add_argument("--max-lines", type=int, default=DEFAULTS["maxLines"])
    build.add_argument("--gap", type=float, default=DEFAULTS["gap"])
    build.add_argument("--on-overlap", choices=("reject", "merge"), default=DEFAULTS["onOverlap"])
    check = sub.add_parser("check", help="validate a subtitle manifest")
    check.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)

    if args.command == "check":
        try:
            data = json.loads(args.manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read {args.manifest}: {exc}", file=sys.stderr)
            return 2
        errors = validate_manifest(data)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"Valid subtitles · {data['totals']['cues']} cues · {data['totals']['duration']:.2f}s")
        return 0

    try:
        payload = json.loads(args.copy.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {args.copy}: {exc}", file=sys.stderr)
        return 2
    settings = {"minDuration": args.min_duration, "maxChars": args.max_chars, "maxLines": args.max_lines,
                "gap": args.gap, "onOverlap": args.on_overlap}
    try:
        cues = build_cues(payload, min_duration=args.min_duration, max_chars=args.max_chars,
                          max_lines=args.max_lines, gap=args.gap, on_overlap=args.on_overlap)
    except SubtitleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    args.srt.parent.mkdir(parents=True, exist_ok=True)
    args.vtt.parent.mkdir(parents=True, exist_ok=True)
    args.srt.write_text(to_srt(cues), encoding="utf-8")
    args.vtt.write_text(to_vtt(cues), encoding="utf-8")
    data = manifest(cues, args.copy, settings)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.srt} and {args.vtt} · {len(cues)} cues · last {cues[-1]['end']:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
