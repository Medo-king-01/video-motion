#!/usr/bin/env python3
"""Procedural background music: render it, audition the presets, or describe a bed before rendering.

Everything is synthesised (`medo-motion/templates/procedural-reels/music.py`) from
`medo-motion/motion/music-presets.json` — offline, deterministic, and sample-rate honest: the same
seed renders the same music at 44.1 kHz or 48 kHz, and the bed is exactly as long as you ask for.

    python3 tools/music_kit.py --presets
    python3 tools/music_kit.py --render out/bed.wav --preset tech --bpm 112 --duration 16
    python3 tools/music_kit.py --render out/bed48.wav --preset cinematic --sr 48000 --key B --scale phrygian
    python3 tools/music_kit.py --preview cache/music-demo.mp3        # every preset, one bar each
    python3 tools/music_kit.py --info --preset energetic --duration 20
    python3 tools/music_kit.py --validate                            # data file + every preset renders

Controls (all optional): --bpm --key --scale --mood --energy --seed --sections --intro --build
--drop --break --outro --layer kick=0.8 --layer hat=0 --width --sr --channels
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
import audio_engine as ax  # noqa: E402
import music  # noqa: E402
from media_bin import ffmpeg as find_ffmpeg  # noqa: E402

SECTION_FLAGS = ("intro", "build", "drop", "break", "outro")


def _config(args) -> music.MusicConfig:
    sections = None
    if args.sections:
        sections = {k: float(v) for k, v in (p.split("=") for p in args.sections.split(","))}
    else:
        given = {name: getattr(args, name) for name in SECTION_FLAGS if getattr(args, name) is not None}
        if given:
            base = dict(music.presets()[args.preset]["sections"])
            base.update(given)
            total = sum(base.values()) or 1.0
            sections = {k: v / total for k, v in base.items() if v > 0}
    layers = {}
    for item in args.layer or []:
        name, _, value = item.partition("=")
        if name not in music.LAYERS:
            raise SystemExit(f"--layer {name}: unknown layer (known: {', '.join(music.LAYERS)})")
        layers[name] = float(value)
    return music.MusicConfig(
        preset=args.preset, duration=args.duration, bpm=args.bpm, key=args.key, scale=args.scale,
        mood=args.mood, energy=args.energy, seed=args.seed, sr=args.sr, channels=args.channels,
        sections=sections, layers=layers or None, swings=args.swing,
        fade_in=args.fade_in, fade_out=args.fade_out,
    )


def stereo_width(audio: np.ndarray) -> float:
    """Side/mid ratio: 0 = mono, ~1 = very wide. Measured, not guessed."""
    if audio.ndim < 2 or audio.shape[1] < 2:
        return 0.0
    mid = (audio[:, 0] + audio[:, 1]) / 2.0
    side = (audio[:, 0] - audio[:, 1]) / 2.0
    m = float(np.sqrt(np.mean(mid ** 2))) + 1e-12
    return float(np.sqrt(np.mean(side ** 2)) / m)


def render(args) -> Path:
    cfg = _config(args)
    out = Path(args.render)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and not args.force:
        raise SystemExit(f"{out} exists — pass --force or choose another name")
    audio = music.render_music(cfg)
    if args.width is not None and audio.shape[1] == 2:
        audio = apply_width(audio, args.width)          # once, before any write
    if out.suffix.lower() in (".mp3", ".m4a"):
        wav = out.with_suffix(".wav")
        ax.write_wav(wav, audio, cfg.sr)
        to_mp3(wav, out)
    else:
        ax.write_wav(out, audio, cfg.sr)
    rms = float(np.sqrt(np.mean(audio ** 2)))
    print(f"music -> {out}  {audio.shape[0] / cfg.sr:.2f}s @ {cfg.sr} Hz · {cfg.preset} "
          f"{cfg.resolved()['bpm']:g} BPM {cfg.resolved()['key']} {cfg.resolved()['scale']} · "
          f"rms {ax.to_db(rms):.1f} dBFS · peak {ax.to_db(float(np.abs(audio).max())):.1f} dBFS · "
          f"width {stereo_width(audio):.2f}")
    return out


def apply_width(audio: np.ndarray, width: float) -> np.ndarray:
    """Mid/side width control: 0 = mono, 1 = as rendered, >1 = wider (bounded)."""
    mid = (audio[:, 0] + audio[:, 1]) / 2.0
    side = (audio[:, 0] - audio[:, 1]) / 2.0 * float(max(0.0, width))
    out = np.stack([mid + side, mid - side], axis=1)
    peak = float(np.max(np.abs(out))) or 1.0
    return (out / max(1.0, peak / 0.95)).astype(np.float32)


def to_mp3(wav: Path, out: Path) -> Path:
    ff = find_ffmpeg()
    if not ff:
        print("ffmpeg not found — keeping the WAV")
        return wav
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "192k", str(out)],
                   check=True)
    wav.unlink(missing_ok=True)
    return out


def preview(args) -> Path:
    """One bar of every preset, separated by a short gap — the audition that proves they differ."""
    cues = []
    t = 0.0
    chunks = []
    for name in music.preset_names():
        cfg = music.MusicConfig(preset=name, duration=args.duration, seed=args.seed, sr=args.sr)
        audio = music.render_music(cfg)
        chunks.append((name, audio))
        cues.append((t, name))
        t += len(audio) / cfg.sr + 0.35
    total = t
    out = np.zeros((int(total * args.sr) + 1, 2), np.float32)
    # `chunks` and `cues` are appended in the same loop above, so the two lists are equal length
    # by construction; strict=True makes that a guarantee instead of an assumption.
    assert len(chunks) == len(cues)
    for (_name, audio), (start, _label) in zip(chunks, cues, strict=True):
        ax.mix_into(out, audio, int(round(start * args.sr)), 0.85)
    dest = Path(args.preview)
    dest.parent.mkdir(parents=True, exist_ok=True)
    wav = dest.with_suffix(".wav")
    if wav.exists() and not args.force:
        raise SystemExit(f"{wav} exists — pass --force or choose another name")
    ax.write_wav(wav, out, args.sr)
    print(f"preview -> {dest}  ({len(chunks)} presets, {total:.1f}s)")
    for start, name in cues:
        print(f"  {start:6.2f}s  {name}")
    return to_mp3(wav, dest) if dest.suffix.lower() == ".mp3" else dest


def validate(args) -> int:
    """Data file sanity + every preset renders, is finite, bounded, stereo and the right length."""
    problems = []
    vocab = music.vocabulary()
    for section, meta in vocab["sections"].items():
        if section.startswith("_") or not isinstance(meta, dict):
            continue
        if not meta.get("layers") and meta.get("density", 0) > 0:
            problems.append(f"section {section}: has density but no layers")
    for name in vocab["presets"]:
        try:
            cfg = music.MusicConfig(preset=name, duration=args.duration, sr=args.sr)
            audio = music.render_music(cfg)
        except Exception as exc:                                    # noqa: BLE001
            problems.append(f"preset {name}: {type(exc).__name__}: {exc}")
            continue
        expect = int(round(args.duration * args.sr))
        if audio.shape != (expect, 2):
            problems.append(f"preset {name}: shape {audio.shape} != {(expect, 2)}")
        if not np.all(np.isfinite(audio)):
            problems.append(f"preset {name}: non-finite samples")
        if float(np.max(np.abs(audio))) > 1.0:
            problems.append(f"preset {name}: clips")
        if float(np.sqrt(np.mean(audio ** 2))) < 1e-3:
            problems.append(f"preset {name}: silent")
        print(f"  {name:<10} ok  {audio.shape[0] / args.sr:5.2f}s  "
              f"rms {ax.to_db(float(np.sqrt(np.mean(audio ** 2)))):6.1f} dBFS  "
              f"width {stereo_width(audio):.2f}")
    for p in problems:
        print(f"  FAIL {p}")
    print("validate:", "PASS" if not problems else f"{len(problems)} problem(s)")
    return 0 if not problems else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--presets", action="store_true", help="list the presets and what makes each one different")
    ap.add_argument("--render", help="write a bed to this path (.wav/.mp3)")
    ap.add_argument("--preview", nargs="?", const=str(ROOT / "cache" / "music-demo.mp3"),
                    help="audition every preset in sequence")
    ap.add_argument("--info", action="store_true", help="describe the bed without rendering audio")
    ap.add_argument("--validate", action="store_true", help="check the data file and every preset")
    ap.add_argument("--preset", default="tech")
    ap.add_argument("--duration", type=float, default=16.0)
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--key")
    ap.add_argument("--scale")
    ap.add_argument("--mood")
    ap.add_argument("--energy", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--sr", type=int, default=ax.SR, help="44100 (default) or 48000")
    ap.add_argument("--channels", type=int, default=2)
    ap.add_argument("--swing", type=float, default=0.0)
    ap.add_argument("--fade-in", type=float, default=0.8, dest="fade_in")
    ap.add_argument("--fade-out", type=float, default=1.2, dest="fade_out")
    ap.add_argument("--sections", help="explicit ratios: intro=0.1,build=0.2,drop=0.5,break=0.1,outro=0.1")
    for name in SECTION_FLAGS:
        ap.add_argument(f"--{name}", type=float)
    ap.add_argument("--layer", action="append", help="override a layer level, e.g. --layer hat=0")
    ap.add_argument("--width", type=float, help="stereo width: 0 mono, 1 as rendered, 1.5 wider")
    ap.add_argument("--force", action="store_true", help="overwrite an existing file")
    args = ap.parse_args()

    if args.presets or not any((args.render, args.preview, args.info, args.validate)):
        print(f"{len(music.preset_names())} music presets @ {args.sr} Hz default\n")
        for name, p in music.presets().items():
            layers = ", ".join(f"{k} {v:g}" for k, v in p["layers"].items() if v > 0)
            print(f"  {name:<10} {p['en']:<24} {p['bpm']:>3} BPM  {p['key']:<2} {p['scale']:<15} {p['why']}")
            print(f"             layers: {layers}")
    if args.render:
        render(args)
    if args.preview:
        preview(args)
    if args.info:
        print(json.dumps(music.music_info(_config(args)), indent=2, ensure_ascii=False))
    if args.validate:
        return validate(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
