#!/usr/bin/env python3
"""Measure the VO and derive the reel's timeline from it.

**The reel has no target length.** The video is exactly as long as the voice-over, and every other
number (scene bounds, mix length, render range, progress bar) is derived from that measurement.
This tool is the single place where that number comes from:

    python3 tools/vo_length.py out/vo24.wav                 # duration + scene bounds from silences
    python3 tools/vo_length.py out/vo24.wav --json plan/beats.json
    python3 tools/vo_length.py --check projects/<slug>      # does the project agree with the VO?

Bounds are cut at the **midpoint of each silence** (silences shorter than `--min-gap` are ignored) and
scenes shorter than `--min-scene` are merged forward, because a 0.4 s scene can't be read anyway.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "medo-motion" / "templates" / "procedural-reels"))
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from media_bin import ffmpeg, ffprobe  # noqa: E402

FFPROBE = ffprobe() or "ffprobe"     # the shim/PATH/bundled rule lives in tools/lib/media_bin.py
FFMPEG = ffmpeg() or "ffmpeg"


# ---------------------------------------------------------------- measurement
def duration_of(path: Path) -> float:
    """Seconds of audio, via ffprobe (falls back to the wave module for plain .wav)."""
    try:
        r = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            try:
                return float(json.loads(r.stdout)["format"]["duration"])
            except (KeyError, ValueError, json.JSONDecodeError):
                pass
    except FileNotFoundError:
        pass   # no ffprobe on this machine — the wave fallback below still measures a .wav
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def silences_of(path: Path, noise_db: float, min_len: float) -> list[tuple[float, float]]:
    """[(start, end)] of every silence ffmpeg's silencedetect reports."""
    r = subprocess.run(
        [FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-af",
         f"silencedetect=noise={noise_db}dB:d={min_len}", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    log = r.stderr
    starts = [float(m) for m in re.findall(r"silence_start:\s*(-?[\d.]+)", log)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([\d.]+)", log)]
    out = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else float("inf")
        out.append((max(0.0, s), e))
    return out


def bounds_from_silences(silences: list[tuple[float, float]], total: float,
                         min_scene: float) -> list[float]:
    """Scene bounds: 0, the midpoint of every long enough silence, and the VO duration."""
    cuts = []
    for s, e in silences:
        if e == float("inf") or e - s < 0.05:
            continue
        if s <= 0.05:            # leading silence is not a cut
            continue
        if e >= total - 0.05:    # trailing silence is not a cut
            continue
        cuts.append(min(total, max(0.0, (s + e) / 2)))
    bounds = [0.0]
    for c in sorted(cuts):
        if c - bounds[-1] >= min_scene:
            bounds.append(round(c, 3))
    bounds.append(round(total, 3))
    return bounds


# ---------------------------------------------------------------- checks
def project_bounds(proj: Path) -> tuple[list[float] | None, str]:
    """The declared bounds: engine K (`src/data.js`), engine P (`scenes.py`), or engine R (`plan/beats.json`)."""
    data = proj / "src" / "data.js"
    if data.is_file():
        text = data.read_text(encoding="utf-8")
        end = re.search(r"DURATION\s*=\s*scenes\.at\(-1\)\.end", text)
        starts = [float(m) for m in re.findall(r"start:\s*([\d.]+)", text)]
        ends = [float(m) for m in re.findall(r"end:\s*([\d.]+)", text)]
        if ends and starts and end:
            return [starts[0], *ends], "src/data.js"
        return (ends or None), "src/data.js"
    scenes = proj / "scenes.py"
    if scenes.is_file():
        m = re.search(r"^B\s*=\s*\[([^\]]+)\]", scenes.read_text(encoding="utf-8"), re.M)
        if m:
            return [float(x) for x in m.group(1).split(",") if x.strip()], "scenes.py"
    beats = proj / "plan" / "beats.json"
    if beats.is_file():
        d = json.loads(beats.read_text(encoding="utf-8"))
        if d.get("duration") is None:
            return None, "plan/beats.json (duration still null)"
        sc = d.get("scenes") or []
        return [s["start"] for s in sc] + [s["end"] for s in sc[-1:]], "plan/beats.json"
    return None, "nothing to check"


def check(proj: Path, total: float, tol: float) -> int:
    bounds, where = project_bounds(proj)
    if bounds is None:
        print(f"!! {where} — no usable timeline yet")
        return 2
    last = bounds[-1]
    print(f"VO      {total:7.2f} s")
    print(f"{where:<18} ends at {last:7.2f} s  ({len(bounds) - 1} scenes)")
    if abs(last - total) > tol:
        print(f"!! MISMATCH {last - total:+.2f} s — the video must be exactly the VO length. "
              f"Rebuild the bounds: python3 tools/vo_length.py <vo> --json plan/beats.json")
        return 1
    print("OK — the reel is exactly as long as the voice-over")
    return 0


# ---------------------------------------------------------------- cli
def main() -> int:
    ap = argparse.ArgumentParser(description="Measure the VO; the reel length comes from it.")
    ap.add_argument("audio", nargs="?", help="the VO file (or a project dir with --check)")
    ap.add_argument("--json", type=Path, help="write plan/beats.json")
    ap.add_argument("--check", type=Path, metavar="PROJECT", help="compare a project's timeline with the VO")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--min-gap", type=float, default=0.30, help="shortest silence that may cut a scene")
    ap.add_argument("--min-scene", type=float, default=1.2, help="shortest scene kept (smaller ones merge)")
    ap.add_argument("--noise", type=float, default=-38.0, help="silence threshold in dB")
    ap.add_argument("--tol", type=float, default=0.15, help="allowed mismatch in --check")
    ap.add_argument("--bpm", type=float, default=0.0, help="tempo: snap cut points to its grid")
    ap.add_argument("--snap-div", type=int, default=2, help="grid steps per beat for --bpm (2 = eighths)")
    ap.add_argument("--snap-tol", type=float, default=0.12, help="max distance a cut may move (s)")
    a = ap.parse_args()

    if a.check:
        total = duration_of(Path(a.audio)) if a.audio else None
        if total is None:
            d = json.loads((a.check / "plan" / "beats.json").read_text(encoding="utf-8")) \
                if (a.check / "plan" / "beats.json").is_file() else {}
            total = d.get("duration")
        if total is None:
            print("need the VO file (or a plan/beats.json that already has a duration)")
            return 2
        return check(a.check, float(total), a.tol)

    if not a.audio:
        ap.error("give the VO file (or --check PROJECT with the VO alongside)")
    audio = Path(a.audio)
    if not audio.is_file():
        print(f"no such file: {audio}")
        return 2

    total = duration_of(audio)
    silences = silences_of(audio, a.noise, a.min_gap)
    bounds = bounds_from_silences(silences, total, a.min_scene)
    if a.bpm > 0:
        from beat import snap_bounds  # noqa: PLC0415  (engine P module, same maths as engine K)

        before = list(bounds)
        bounds, moved = snap_bounds(bounds, a.bpm, a.snap_div, tol=a.snap_tol)
        print(f"grid     {a.bpm:g} BPM / {a.snap_div} steps per beat -> {moved} of "
              f"{len(before) - 2} cuts snapped (tol {a.snap_tol:g}s)")

    print(f"VO       {audio}  {total:.2f} s  =  {round(total * a.fps)} frames @ {a.fps:g} fps")
    print(f"speech   {total - sum(e - s for s, e in silences if e != float('inf')):.2f} s "
          f"({len(silences)} silences)")
    print(f"scenes   {len(bounds) - 1}\n")
    print(f"{'#':>2}  {'start':>7}  {'end':>7}  {'dur':>6}  frames")
    for i in range(len(bounds) - 1):
        s, e = bounds[i], bounds[i + 1]
        print(f"{i + 1:>2}  {s:7.2f}  {e:7.2f}  {e - s:6.2f}  {round((e - s) * a.fps)}")
    print("\nCut points (midpoint of a silence):", ", ".join(f"{b:.2f}" for b in bounds[1:-1]) or "—")

    if a.json:
        payload = {
            "duration": round(total, 3),
            "fps": a.fps,
            "frames": round(total * a.fps),
            "audio": str(audio),
            "bounds": bounds,
            "scenes": [{"index": i + 1, "start": bounds[i], "end": bounds[i + 1],
                        "dur": round(bounds[i + 1] - bounds[i], 3),
                        "frames": round((bounds[i + 1] - bounds[i]) * a.fps)}
                       for i in range(len(bounds) - 1)],
            "note": "derived from the VO with tools/vo_length.py — the reel length is the VO length",
        }
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
