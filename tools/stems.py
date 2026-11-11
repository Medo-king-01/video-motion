#!/usr/bin/env python3
"""Split a recording into stems with Demucs (optional, MIT) — voice apart from music.

What it is for in the studio:
  - a reference video: hear the voice and the music bed separately (docs/reference-workflow.md);
  - a voice-over recorded with music under it: align captions on the `vocals` stem, which is
    easier for Whisper than the full mix (docs/alignment.md).

What it is not: a clean SFX track, a mastering tool, or a rights-clearing tool. Stems are a
model's estimate; they smear transients and leak between each other. Separating someone else's
music does not give you the right to reuse it.

    python3 tools/stems.py ref.mp4 --out cache/stems                 # drums/bass/other/vocals
    python3 tools/stems.py vo.wav  --out cache/stems --two-stems vocals   # vocals + no_vocals
    python3 tools/stems.py ref.mp4 --out cache/stems --start 15 --dur 15

Needs `pip install -r tools/requirements-stems.txt` (pulls PyTorch) and ffmpeg. The model weights
(~80 MB for htdemucs) are downloaded by Demucs on first use; on a machine without access to
dl.fbaipublicfiles.com pass `--weights DIR` with a local Demucs model repository.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from media_bin import ffmpeg as find_ffmpeg  # noqa: E402 - shared precedence rule

MODELS = ("htdemucs", "htdemucs_ft", "htdemucs_6s", "mdx_extra", "mdx_extra_q")
TWO_STEMS = ("vocals", "drums", "bass", "other")
NOTE = ("Stems are a model estimate: transients smear and sources leak into each other. "
        "Use them to listen and to align captions, not as clean deliverables.")


def build_convert_command(ffmpeg: str, source: Path, target: Path,
                          start: float = 0.0, dur: float | None = None) -> list[str]:
    """Any audio/video input -> the 44.1 kHz stereo WAV Demucs models are trained on."""
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    if start > 0:
        command += ["-ss", f"{start:.6g}"]
    if dur is not None:
        command += ["-t", f"{dur:.6g}"]
    return command + ["-i", str(source), "-map", "0:a:0", "-vn", "-ac", "2", "-ar", "44100", str(target)]


def build_demucs_command(python: str, wav: Path, work: Path, model: str = "htdemucs",
                         two_stems: str | None = None, segment: int | None = None,
                         weights: Path | None = None, device: str = "cpu") -> list[str]:
    command = [python, "-m", "demucs", "-n", model, "-o", str(work), "-d", device]
    if two_stems:
        command += ["--two-stems", two_stems]
    if segment:
        command += ["--segment", str(segment)]
    if weights:
        command += ["--repo", str(weights)]
    return command + [str(wav)]


def missing_dependencies() -> list[str]:
    return [name for name in ("demucs", "torch", "torchaudio", "soundfile")
            if importlib.util.find_spec(name) is None]


def fail(message: str, code: int = 1) -> int:
    print(f"stems: {message}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("source", type=Path, help="audio or video file")
    ap.add_argument("--out", type=Path, required=True, help="output folder (keep it under cache/)")
    ap.add_argument("--model", default="htdemucs",
                    help="Demucs model name (default htdemucs; also " + ", ".join(MODELS[1:])
                         + ", or a signature inside --weights)")
    ap.add_argument("--two-stems", choices=TWO_STEMS, help="only split this stem from the rest")
    ap.add_argument("--start", type=float, default=0.0, help="start second (default 0)")
    ap.add_argument("--dur", type=float, help="seconds to process (default: to the end)")
    ap.add_argument("--segment", type=int, help="chunk length in seconds; lower it if memory runs out")
    ap.add_argument("--weights", type=Path, help="local Demucs model repository (offline use)")
    ap.add_argument("--device", default="cpu", help="torch device (default cpu)")
    args = ap.parse_args(argv)

    if not args.source.is_file():
        return fail(f"input not found: {args.source}", 2)
    if args.start < 0 or (args.dur is not None and args.dur <= 0):
        return fail("--start must be >= 0 and --dur must be > 0", 2)
    if args.segment is not None and args.segment <= 0:
        return fail("--segment must be a positive number of seconds", 2)
    if args.weights and not args.weights.is_dir():
        return fail(f"--weights is not a folder: {args.weights}", 2)
    missing = missing_dependencies()
    if missing:
        return fail(f"optional dependency missing ({', '.join(missing)}).\n"
                    "  python -m pip install -r tools/requirements-stems.txt\n"
                    "  (or: bash tools/setup_extras.sh demucs — it pulls PyTorch, several GB)")
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return fail("ffmpeg not found — bash tools/setup.sh")

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    wav = out / "input44.wav"
    result = subprocess.run(build_convert_command(ffmpeg, args.source, wav, args.start, args.dur),
                            capture_output=True, text=True)
    if result.returncode or not wav.is_file() or wav.stat().st_size <= 44:
        return fail(f"could not extract audio from {args.source}: {result.stderr.strip() or 'no audio stream'}")

    work = out / "_demucs"
    shutil.rmtree(work, ignore_errors=True)
    result = subprocess.run(build_demucs_command(sys.executable, wav, work, args.model, args.two_stems,
                                                 args.segment, args.weights, args.device),
                            capture_output=True, text=True)
    if result.returncode:
        tail = "\n".join(result.stderr.strip().splitlines()[-6:])
        hint = ""
        if "urlopen" in result.stderr or "URLError" in result.stderr or "HTTP Error" in result.stderr:
            hint = ("\n  The model weights could not be downloaded (dl.fbaipublicfiles.com unreachable)."
                    "\n  Run once on a machine with access, or pass --weights DIR with a local model repository.")
        elif "out of memory" in result.stderr.lower() or result.returncode in (-9, 137):
            hint = "\n  Out of memory: retry with --segment 5 and/or a shorter --dur."
        shutil.rmtree(work, ignore_errors=True)
        return fail(f"Demucs failed (exit {result.returncode}):\n{tail}{hint}")

    produced = sorted((work / args.model / wav.stem).glob("*.wav"))
    if not produced:
        shutil.rmtree(work, ignore_errors=True)
        return fail("Demucs finished but wrote no stems")
    stems = {}
    for path in produced:
        target = out / path.name
        shutil.move(str(path), target)
        stems[path.stem] = target.name
    shutil.rmtree(work, ignore_errors=True)
    report = {"source": str(args.source), "model": args.model, "two_stems": args.two_stems,
              "start": args.start, "dur": args.dur, "sample_rate": 44100, "input": wav.name,
              "stems": stems, "note": NOTE}
    (out / "stems.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(stems)} stem(s) -> {out}: {', '.join(sorted(stems))}")
    print(NOTE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
