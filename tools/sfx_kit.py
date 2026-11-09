#!/usr/bin/env python3
"""The procedural sound kit: render it, audition it, or mix a cue sheet against the voice.

Everything is synthesised (`medo-motion/templates/procedural-reels/sfx.py`) — free, offline, and
deterministic: the same seed renders the same samples, so a mix can be rebuilt byte-identically.

    python3 tools/sfx_kit.py --list
    python3 tools/sfx_kit.py --bank out/sfx                    # one WAV per sound (editor import)
    python3 tools/sfx_kit.py --demo cache/sfx-demo.mp3          # 20 s audition of the whole kit
    python3 tools/sfx_kit.py --cues cuts.json --vo vo.wav --out mix.wav   # length = the VO's
    python3 tools/sfx_kit.py --grid "k.h.|k.h." --bpm 120 --bars 2 --out cache/grid-cues.json
    python3 tools/sfx_kit.py --bank out/sfx48 --sr 48000        # the same kit, natively at 48 kHz
    python3 tools/sfx_kit.py --list --json > cache/sfx-catalog.json

Cue sheet (JSON) — `t` in seconds, gain/pan optional, `sfx` must exist in the catalogue:

    [{"t": 1.20, "sfx": "whoosh", "gain": 0.9, "pan": [0.7, -0.7]},
     {"t": 2.05, "sfx": "chime"}]

Or derive the cues from the cut list, so each transition gets the sound it declares:

    [{"scene": 2, "t": 12.4, "name": "wipe"}]   →  whoosh at 12.4 s
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
P_DIR = ROOT / "medo-motion" / "templates" / "procedural-reels"
sys.path.insert(0, str(P_DIR))
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import sfx  # noqa: E402
from media_bin import ffmpeg as find_ffmpeg  # noqa: E402
from media_bin import ffprobe as find_ffprobe  # noqa: E402


def _to_mp3(wav: Path, out: Path) -> Path:
    ff = find_ffmpeg()
    if not ff:
        print("ffmpeg not found — keeping the WAV")
        return wav
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "192k", str(out)],
                   check=True)
    wav.unlink(missing_ok=True)
    return out


def demo(out: Path, limit_db: float = -1.5, sr: int = sfx.SR) -> Path:
    """Walk the catalogue in families with a little space between hits, then a transition run."""
    cues, t = [], 0.28
    for name in sfx.BANK:
        cues.append({"t": t, "sfx": name, "gain": 1.0})
        t += max(0.34, sfx.duration(name, sr=sr) + 0.22)
    # a short "cut run": one entry per transition, using the sound each one declares
    try:
        from transition import NAMES as TRANSITION_NAMES
        from transition import sfx_for
    except ImportError:
        TRANSITION_NAMES, sfx_for = [], lambda _n: None
    t += 0.35
    for name in TRANSITION_NAMES:
        sound = sfx_for(name)
        if sound:
            cues.append({"t": t, "sfx": sound, "gain": 0.85, "pan": [0.4, -0.4]})
        t += 0.5
    total = t + 1.0
    bus = sfx.bus(total, cues, sr=sr, tail=True)
    # gentle master: soft clip then normalise to the brand's true-peak ceiling
    peak = float(np.max(np.abs(bus))) or 1.0
    bus = bus / peak * (10 ** (limit_db / 20)) * 0.9
    wav = out.with_suffix(".wav")
    out.parent.mkdir(parents=True, exist_ok=True)
    sfx.write_wav(wav, bus, sr)
    return _to_mp3(wav, out) if out.suffix == ".mp3" else wav


def audio_duration(path: Path) -> float:
    """Length of an audio file in seconds (the reel is as long as its voice-over)."""
    probe = find_ffprobe() or "ffprobe"  # env override -> tools/bin shim -> PATH (AGENTS.md §9)
    r = subprocess.run([probe, "-v", "error", "-show_entries",
                        "format=duration", "-of", "json", str(path)], capture_output=True, text=True)
    if r.returncode == 0:
        try:
            return float(json.loads(r.stdout)["format"]["duration"])
        except (KeyError, ValueError, json.JSONDecodeError):
            pass
    import wave  # noqa: PLC0415

    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def mix(cues_path: Path, length: float, voice: Path | None, out: Path, duck: float = 0.6,
        sr: int = sfx.SR, anchored: bool = False) -> Path:
    cues = json.loads(cues_path.read_text(encoding="utf-8"))
    if isinstance(cues, dict):  # {"cuts": [...]} or {"cues": [...]}
        if "cuts" in cues:
            cues = sfx.cues_for_transitions(cues["cuts"])
        else:
            cues = cues.get("cues", [])
    # the bus lasts exactly as long as the mix: an explicit --length, else the VO, else the last cue
    total = length or (audio_duration(voice) if voice else (max((c["t"] for c in cues), default=0.0) + 2.0))
    bus = sfx.bus(total, cues, sr=sr, anchored=anchored)
    if voice:
        from scipy.io import wavfile  # noqa: PLC0415
        from scipy.signal import resample_poly  # noqa: PLC0415

        rate, data = wavfile.read(voice)
        v = data.astype(np.float32) / 32768
        if v.ndim > 1:
            v = v.mean(1)
        if rate != sr:
            v = resample_poly(v, sr, rate).astype(np.float32)
        vo = np.zeros(len(bus), np.float32)
        vo[: min(len(v), len(bus))] = v[: len(bus)]
        bus = sfx.duck(vo, bus, depth=duck, sr=sr)
        mixd = np.stack([vo, vo], 1) + bus
    else:
        mixd = bus
    peak = float(np.max(np.abs(mixd))) or 1.0
    sfx.write_wav(out, mixd / max(1.0, peak * 1.02), sr)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--bank", help="directory for one WAV per sound")
    ap.add_argument("--demo", nargs="?", const=str(ROOT / "cache" / "sfx-demo.mp3"), help="audition mix")
    ap.add_argument("--cues", help="cue sheet JSON (or a cut list under 'cuts')")
    ap.add_argument("--grid", help="write a tempo-locked cue sheet: 'k.h.|k.h.' (one char per 16th)")
    ap.add_argument("--bpm", type=float, default=120.0, help="tempo for --grid")
    ap.add_argument("--bars", type=int, default=1, help="how many bars for --grid")
    ap.add_argument("--length", type=float, default=0.0)
    ap.add_argument("--vo", help="voice track to duck the sfx under")
    ap.add_argument("--out", default="mix.wav")
    ap.add_argument("--sr", type=int, default=sfx.SR, help="sample rate: 44100 (default) or 48000")
    ap.add_argument("--anchored", action="store_true",
                    help="cue times mark the sound's event (a riser peaks at `t`), not its start")
    ap.add_argument("--json", action="store_true", help="machine-readable --list")
    ap.add_argument("--force", action="store_true", help="overwrite an existing bank/demo/mix")
    args = ap.parse_args()
    if args.sr not in (44100, 48000):
        ap.error("--sr must be 44100 or 48000")

    if args.list or not any((args.bank, args.demo, args.cues, args.grid)):
        width = max(len(n) for n in sfx.BANK)
        if args.json:
            print(json.dumps({name: {"family": sfx.CATALOG[name]["family"], "gain": sfx.CATALOG[name]["gain"],
                                     "tags": sfx.CATALOG[name]["tags"], "seconds": round(sfx.duration(name, sr=args.sr), 4),
                                     "anchor": round(sfx.anchor(name, args.sr), 4)}
                              for name in sfx.BANK}, indent=2, ensure_ascii=False))
            return 0
        print(f"{len(sfx.BANK)} procedural sounds @ {args.sr} Hz")
        for name in sfx.BANK:
            meta = sfx.CATALOG.get(name, {})
            print(f"  {name:<{width}}  {sfx.duration(name, sr=args.sr):5.2f}s  {meta.get('family', ''):<7} {meta.get('tags', '')}")
    if args.bank:
        files = sfx.render_bank(args.bank, sr=args.sr, overwrite=args.force)
        print(f"bank -> {len(files)} wav(s) in {args.bank}")
    if args.demo:
        print(f"demo -> {demo(Path(args.demo), sr=args.sr)}")
    if args.grid:
        dest = Path(args.out)
        if dest.suffix.lower() != ".json":
            dest = Path("cache") / "grid-cues.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        cues = sfx.grid_cues(args.grid, args.bpm, args.bars)
        dest.write_text(json.dumps(cues, indent=2) + "\n", encoding="utf-8")
        print(f"grid -> {dest}  ({len(cues)} cues @ {args.bpm:g} BPM, {args.bars} bar(s), "
              f"{sfx.bars_seconds(args.bpm, args.bars):.2f}s)")
    if args.cues:
        out = mix(Path(args.cues), args.length, Path(args.vo) if args.vo else None, Path(args.out),
                  sr=args.sr, anchored=args.anchored)
        print(f"mix  -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
