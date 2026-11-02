#!/usr/bin/env python3
"""Retry S06/S07 without initial_prompt (prompt caused beginning-skip)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from measure_scenes import MODEL, align, norm  # noqa: E402


def main() -> int:
    from faster_whisper import WhisperModel
    scenes = {s["id"]: s for s in json.loads((ROOT / "cache/script-scenes.json").read_text(encoding="utf-8"))}
    data = json.loads((ROOT / "cache/scene-measurements.json").read_text(encoding="utf-8"))
    model = WhisperModel(MODEL, device="cpu", compute_type="int8", cpu_threads=2, num_workers=1, local_files_only=True)
    for entry in data:
        sid = entry["id"]
        if sid not in {"S06", "S07"}:
            continue
        wav = ROOT / "cache/scene-slices" / f"{sid}.wav"
        segments, _ = model.transcribe(
            str(wav), language="ar", task="transcribe", beam_size=5, word_timestamps=True,
            vad_filter=False, condition_on_previous_text=False,
            temperature=(0.0, 0.2, 0.4), repetition_penalty=1.1,
        )
        asr = []
        for seg in segments:
            for w in seg.words or []:
                asr.append({"text": w.word.strip(), "start": round(float(w.start), 3), "end": round(float(w.end), 3), "p": round(float(w.probability), 3)})
        timeline = align(scenes[sid]["words"], asr)
        matched = sum(1 for w in timeline if w["src"] == "asr")
        print(f"{sid} matched={matched}/{len(scenes[sid]['words'])}")
        print("  asr:", " | ".join(f"{w['text']}@{w['start']}" for w in asr))
        for w in timeline:
            if w["src"] != "asr":
                print(f"  GAP {w['text']} -> {w['start']}-{w['end']}")
        entry.update(words=timeline, asr=asr, status=f"{matched}/{len(scenes[sid]['words'])} asr-matched (no-prompt retry)")
    (ROOT / "cache/scene-measurements.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("updated cache/scene-measurements.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
