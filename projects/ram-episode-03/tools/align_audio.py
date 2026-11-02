#!/usr/bin/env python3
"""Create measured Arabic word timestamps with WhisperX forced alignment.

The source audio is read locally and is never copied into the repository by this tool.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

ARABIC_ALIGNMENT_MODEL = "jonatasgrosman/wav2vec2-large-xlsr-53-arabic"


def extract_words(aligned: dict[str, Any]) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    for segment in aligned.get("segments", []):
        for item in segment.get("words", []) or []:
            token = str(item.get("word", "")).strip()
            start, end = item.get("start"), item.get("end")
            if not token or start is None or end is None:
                continue
            start, end = float(start), float(end)
            if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
                raise ValueError(f"WhisperX returned invalid timing for {token!r}: {start}–{end}")
            words.append({"text": token, "start": round(start, 3), "end": round(end, 3)})

    words.sort(key=lambda word: (word["start"], word["end"]))
    for index in range(1, len(words)):
        if words[index]["start"] < words[index - 1]["end"]:
            raise ValueError(
                "WhisperX produced overlapping word intervals; refusing to silently alter "
                f"measured timings at word {index}: {words[index - 1]} / {words[index]}"
            )
    if not words:
        raise ValueError("WhisperX alignment returned no word-level timestamps")
    return words


def align_audio(audio_path: Path, model_name: str = "small", batch_size: int = 4) -> dict[str, Any]:
    try:
        import whisperx
    except ImportError as exc:
        raise RuntimeError("WhisperX is missing. Install tools/requirements-align.txt first.") from exc

    device = "cpu"
    compute_type = "int8"
    audio = whisperx.load_audio(str(audio_path))
    model = whisperx.load_model(
        model_name, device, compute_type=compute_type, language="ar"
    )
    transcription = model.transcribe(audio, batch_size=batch_size, language="ar")
    align_model, metadata = whisperx.load_align_model(
        language_code="ar", device=device, model_name=ARABIC_ALIGNMENT_MODEL
    )
    aligned = whisperx.align(
        transcription["segments"],
        align_model,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )
    duration = len(audio) / 16000
    return {
        "schema_version": 1,
        "language": "ar",
        "engine": "WhisperX",
        "model": model_name,
        "alignment_model": ARABIC_ALIGNMENT_MODEL,
        "duration": round(duration, 3),
        "words": extract_words(aligned),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Arabic speech transcription + word alignment")
    parser.add_argument("audio", type=Path, help="Local WAV/MP3/M4A audio file")
    parser.add_argument("--output", type=Path, default=Path("captions-s01.aligned.json"))
    parser.add_argument("--model", default="small", help="Whisper model (default: small)")
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()

    if not args.audio.is_file():
        parser.error(f"Audio file does not exist: {args.audio}")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")

    result = align_audio(args.audio, args.model, args.batch_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Aligned {len(result['words'])} words from {result['duration']:.3f}s audio")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
