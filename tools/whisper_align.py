#!/usr/bin/env python3
"""Measure word timestamps with a local faster-whisper CTranslate2 model.

Studio alignment infrastructure (see docs/alignment.md).

No Hugging Face download is performed: pass a local model directory containing
model.bin, config.json, tokenizer.json and vocabulary.json (build it with
tools/whisper_fetch.py). Emits measured word intervals as JSON — the only
acceptable source for burned-in caption timing (never estimate from scene cuts).

Usage:
    python3 tools/whisper_align.py vo.wav \\
        --model .cache/whisper-small-ct2-int8 --out cache/words.json --language ar

For short per-scene slices, prefer --no-vad: VAD can drop real speech at slice
edges. If an exact-script --initial-prompt makes Whisper skip a slice opening,
retry without the prompt (see tools/caption_align.py).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from faster_whisper import WhisperModel


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("audio", type=Path)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--language", default="ar")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--beam-size", type=int, default=5)
    ap.add_argument("--initial-prompt", default=None)
    ap.add_argument("--no-vad", action="store_true")
    ap.add_argument("--vad-min-silence-ms", type=int, default=300)
    ap.add_argument("--vad-speech-pad-ms", type=int, default=120)
    ap.add_argument("--vad-threshold", type=float, default=0.5)
    args = ap.parse_args()

    model = WhisperModel(
        str(args.model), device="cpu", compute_type="int8",
        cpu_threads=args.threads, num_workers=1, local_files_only=True,
    )
    segments, info = model.transcribe(
        str(args.audio),
        language=args.language,
        task="transcribe",
        beam_size=args.beam_size,
        word_timestamps=True,
        vad_filter=not args.no_vad,
        vad_parameters={"min_silence_duration_ms": args.vad_min_silence_ms, "speech_pad_ms": args.vad_speech_pad_ms},
        condition_on_previous_text=False,
        initial_prompt=args.initial_prompt,
        temperature=0.0,
    )
    words, segs = [], []
    for seg in segments:
        segs.append({"start": seg.start, "end": seg.end, "text": seg.text})
        for w in seg.words or []:
            words.append({
                "word": w.word.strip(),
                "start": round(float(w.start), 3),
                "end": round(float(w.end), 3),
                "probability": round(float(w.probability), 4),
            })
        print(f"[{seg.start:7.3f} -> {seg.end:7.3f}] {seg.text}", flush=True)
    payload = {
        "source": str(args.audio),
        "model": str(args.model),
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "duration_after_vad": info.duration_after_vad,
        "segments": segs,
        "words": words,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {len(words)} words -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
