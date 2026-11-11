#!/usr/bin/env python3
"""Mix a reel's audio from ONE cue sheet: music + SFX + voice-over, ducked and mastered.

`sfx_kit.py --cues` mixes SFX and `mix.py` mixes a hard-coded bed; this tool is the single timeline
that knows about both, plus the voice, plus where the music changes. Everything it does is
reproducible: same sheet + same voice → same samples.

    python3 tools/audio_mix.py --sheet cues.json --vo out/vo.wav --out out/final_audio.wav
    python3 tools/audio_mix.py --from-cuts cuts.json --preset tech --duration 24 --out out/mix.wav
    python3 tools/audio_mix.py --sheet cues.json --dry-run          # print the resolved timeline
    python3 tools/audio_mix.py --sheet cues.json --stems out/stems   # music.wav sfx.wav vo.wav
    python3 tools/audio_mix.py --sheet cues.json --sr 48000 --out out/mix48.wav

Cue sheet (JSON) — see `medo-motion/templates/procedural-reels/audio_mix.py` for the full schema:

    {"duration": 24.0, "sr": 44100, "seed": 7,
     "music": {"preset": "tech", "bpm": 112,
               "changes": [{"t": 12.0, "preset": "cinematic"}]},
     "sfx": [{"t": 6.4, "sfx": "whoosh", "gain": 0.9, "pan": [-0.6, 0.6], "anchor": true}]}

The final master is FFmpeg's two-pass `loudnorm` at the brand values (-14.5 LUFS, -1.5 dBTP); with
`--no-loudnorm` (or no ffmpeg) the library's own limiter/level stage is used and the measured values
are reported instead of silently skipped.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
P_DIR = ROOT / "medo-motion" / "templates" / "procedural-reels"
sys.path.insert(0, str(P_DIR))
sys.path.insert(0, str(ROOT / "shared" / "py"))  # audio + rhythm live here, not in engine P
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import audio_engine as ax  # noqa: E402
import audio_mix as AM  # noqa: E402
import sfx  # noqa: E402
from media_bin import ffmpeg as find_ffmpeg  # noqa: E402


def build_sheet(args) -> dict:
    if args.sheet:
        sheet = AM.load_sheet(args.sheet)
    else:
        cuts = json.loads(Path(args.from_cuts).read_text(encoding="utf-8"))
        preset = args.preset or "tech"
        if isinstance(cuts, dict):
            sheet = AM.from_storyboard(cuts, preset=preset, duration=args.duration,
                                       sr=args.sr or ax.SR, seed=args.seed)
        else:
            duration = args.duration or (max((c["t"] for c in cuts), default=0.0) + 2.0)
            sheet = AM.validate_sheet({
                "duration": duration, "sr": args.sr or ax.SR, "seed": args.seed,
                "music": {"preset": preset, "duration": duration, "sr": args.sr or ax.SR, "seed": args.seed},
                "sfx": sfx.cues_for_transitions(cuts),
            })
    if args.sr:
        sheet["sr"] = args.sr
        if sheet.get("music") is not None:
            sheet["music"]["sr"] = args.sr
    if args.duration:
        sheet["duration"] = float(args.duration)
    if args.preset and sheet.get("music") is not None:
        sheet["music"]["preset"] = args.preset
    if args.seed is not None:
        sheet["seed"] = int(args.seed)
        if sheet.get("music") is not None:
            sheet["music"]["seed"] = int(args.seed)
    if args.no_music:
        sheet["music"] = None
    return AM.validate_sheet(sheet)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", help="cue sheet JSON (music + sfx + duck + master)")
    ap.add_argument("--from-cuts", dest="from_cuts", help="cut list JSON (transitions) to build a sheet from")
    ap.add_argument("--vo", help="voice-over WAV to place and duck under")
    ap.add_argument("--out", default="mix.wav")
    ap.add_argument("--stems", help="directory for music.wav / sfx.wav / vo.wav")
    ap.add_argument("--sr", type=int, default=None, help="override the sheet's sample rate (44100/48000)")
    ap.add_argument("--duration", type=float, default=0.0)
    ap.add_argument("--preset", help="override the sheet's music preset (default: keep the sheet's)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-music", dest="no_music", action="store_true")
    ap.add_argument("--no-loudnorm", dest="no_loudnorm", action="store_true")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true", help="print the resolved timeline")
    ap.add_argument("--report", help="write the JSON report here")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if not args.sheet and not args.from_cuts:
        ap.error("need --sheet or --from-cuts")

    sheet = build_sheet(args)
    if args.dry_run:
        print("\n".join(AM.describe(sheet)))
        return 0

    out = Path(args.out)
    if out.exists() and not args.force:
        raise SystemExit(f"{out} exists — pass --force or choose another name")
    out.parent.mkdir(parents=True, exist_ok=True)

    result = AM.mix(sheet, voice_path=args.vo, master=False)
    report = result["report"]
    wav = out.with_suffix(".wav") if out.suffix.lower() in (".mp3", ".m4a") else out
    AM.write_mix(result, wav)

    if args.stems:
        stems = Path(args.stems)
        stems.mkdir(parents=True, exist_ok=True)
        sr = sheet["sr"]
        ax.write_wav(stems / "music.wav", result["music"], sr)
        ax.write_wav(stems / "sfx.wav", result["sfx"], sr)
        if args.vo:
            ax.write_wav(stems / "vo.wav", np.stack([result["voice"], result["voice"]], 1), sr)
        report["stems"] = str(stems)

    # ---- final master: ffmpeg loudnorm when available, the library limiter otherwise ----
    if not args.no_loudnorm and find_ffmpeg():
        meas = AM.master_to_target(wav, lufs=sheet["master"].get("lufs", -14.5),
                                   true_peak=sheet["master"].get("true_peak", -1.5))
        report["loudnorm"] = meas
        if not meas.get("ok"):
            print(f"note: loudnorm failed ({meas.get('reason')}) — keeping the library master")
    else:
        mastered = AM.mix(sheet, voice_path=args.vo, master=True)
        result = mastered
        report = mastered["report"]
        AM.write_mix(mastered, wav)
        report["loudnorm"] = {"ok": False, "reason": "disabled or ffmpeg missing; library normaliser used"}

    if out.suffix.lower() == ".mp3":
        subprocess_args = [find_ffmpeg(), "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "libmp3lame",
                           "-b:a", "192k", str(out)]
        import subprocess
        subprocess.run(subprocess_args, check=True)
        wav.unlink(missing_ok=True)

    # ---- measure what was actually written (never trust the intent) ----
    from scipy.io import wavfile
    final_sr, data = wavfile.read(str(wav))
    arr = np.asarray(data, np.float32) / 32768.0
    if arr.ndim == 1:
        arr = np.stack([arr, arr], 1)
    report["output"] = {
        "path": str(wav), "sr": int(final_sr), "samples": int(arr.shape[0]),
        "seconds": round(arr.shape[0] / float(final_sr), 4),
        "peak_dbtp": round(ax.true_peak(arr, final_sr), 2),
        "rms_dbfs": round(ax.to_db(float(np.sqrt(np.mean(arr ** 2)))), 2),
    }
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n",
                                     encoding="utf-8")

    o = report["output"]
    print(f"mix -> {o['path']}  {o['seconds']:.2f}s @ {o['sr']} Hz · peak {o['peak_dbtp']} dBTP · "
          f"rms {o['rms_dbfs']} dBFS")
    print(f"  music {report['music']['segments'].__len__()} segment(s) · "
          f"{report['sfx']['cues']} sfx cue(s) · "
          + (f"vo {report['voice']['kept'] / o['sr']:.2f}s" if report.get("voice") else "no vo"))
    ln = report.get("loudnorm") or {}
    if ln.get("ok"):
        m = ln.get("measured") or {}
        extra = f" · trim {ln['trim_db']:+.2f} dB" if ln.get("trim_db") else ""
        print(f"  mastered: {m.get('lufs')} LUFS / {m.get('true_peak')} dBTP (EBU R128){extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
