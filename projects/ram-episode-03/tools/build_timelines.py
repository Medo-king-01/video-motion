#!/usr/bin/env python3
"""Build final caption timelines + data.js from measured scene words.

- Snap early onsets to measured speech activity (20ms RMS envelope).
- Hold each word until the next word begins (BRIEF requirement).
- Emit src/captions-sXX.js and src/data.js with measured bounds.
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
VO = ROOT / "assets/vo/episode-03-ram.wav"
SCENE_IDS = ["ram-intro", "ram-question", "ram-explain", "ram-choose", "ram-8gb",
             "ram-16gb", "ram-32gb", "ram-bigger", "ram-budget", "ram-cta"]


def speech_regions(x: np.ndarray, sr: int, thresh: float = 0.012) -> list[tuple[float, float]]:
    win = int(sr * 0.02)
    regions, active, start = [], False, 0.0
    for i in range(0, len(x) - win, win):
        r = float(np.sqrt(np.mean(x[i:i + win] ** 2)))
        t = i / sr
        if r > thresh and not active:
            active, start = True, t
        elif r <= thresh and active:
            active = False
            regions.append((start, t))
    if active:
        regions.append((start, len(x) / sr))
    return regions


def main() -> int:
    with wave.open(str(VO), "rb") as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    data = json.loads((ROOT / "cache/scene-measurements.json").read_text(encoding="utf-8"))
    report = []
    for idx, entry in enumerate(data):
        sid = entry["id"]
        g0, g1 = entry["start"], entry["end"]
        words = entry["words"]
        if sid == "S01":
            # Approved v6 timeline — do not re-snap; use as-is.
            out = [{"text": w["text"], "start": w["start"], "end": w["end"]} for w in words]
            entry["final"] = out
            lines = [f"// {sid} word-level timeline — approved v6 (measured Whisper + silence-snapped).",
                     f"export const CAPTIONS_{sid} = ["]
            for w in out:
                lines.append(f"  {{ text: {json.dumps(w['text'], ensure_ascii=False)}, start: {w['start']}, end: {w['end']} }},")
            lines.append("];")
            (ROOT / f"src/captions-s{idx + 1:02d}.js").write_text("\n".join(lines) + "\n", encoding="utf-8")
            report.append(f"{sid} {g0:.3f}-{g1:.3f} words={len(out)} first={out[0]['start']} last_end={out[-1]['end']} (approved-v6)")
            continue
        regions = speech_regions(x[int(g0 * sr):int(g1 * sr)], sr)
        fixed = []
        for i, w in enumerate(words):
            t = float(w["start"])
            # snap onset forward if it sits in silence >120ms before speech
            for a, b in regions:
                if a - 0.12 > t and a - t < 0.9 and (i == 0 or t <= words[i - 1]["start"] + 0.001):
                    t = round(a, 3)
                    break
            if i == 0 and regions and t < regions[0][0] - 0.02:
                t = round(regions[0][0], 3)
            fixed.append({"text": w["text"].strip("،.!؟?: "), "start": t})
        # sort by onset (ASR can emit tiny local inversions), then hold until next word
        fixed.sort(key=lambda w: w["start"])
        out = []
        for i, w in enumerate(fixed):
            end = fixed[i + 1]["start"] if i + 1 < len(fixed) else min(round(w["start"] + 0.6, 3), round(g1 - g0, 3))
            if end <= w["start"]:
                end = round(w["start"] + 0.05, 3)
            out.append({"text": w["text"], "start": round(w["start"], 3), "end": round(end, 3)})
        # strict monotonic guard
        for i in range(1, len(out)):
            if out[i]["start"] <= out[i - 1]["start"]:
                out[i]["start"] = round(out[i - 1]["start"] + 0.03, 3)
            if out[i]["start"] < out[i - 1]["end"]:
                out[i - 1]["end"] = out[i]["start"]
            if out[i]["end"] <= out[i]["start"]:
                out[i]["end"] = round(out[i]["start"] + 0.05, 3)
        entry["final"] = out
        # write captions module
        lines = [f"// {sid} word-level timeline — measured local Whisper small CT2 int8 on the real VO.",
                 "// Onsets validated against the WAV speech envelope; each word holds until the next begins.",
                 f"export const CAPTIONS_{sid} = ["]
        for w in out:
            lines.append(f"  {{ text: {json.dumps(w['text'], ensure_ascii=False)}, start: {w['start']}, end: {w['end']} }},")
        lines.append("];")
        (ROOT / f"src/captions-s{idx + 1:02d}.js").write_text("\n".join(lines) + "\n", encoding="utf-8")
        report.append(f"{sid} {g0:.3f}-{g1:.3f} words={len(out)} first={out[0]['start']} last_end={out[-1]['end']}")
    # data.js
    lines = ["// RAM Episode 03 — measured scene map (local Whisper word alignment + silence-midpoint cuts).",
             "export const W=1080,H=1920,FPS=30;", "export const scenes=["]
    for idx, entry in enumerate(data):
        lines.append(f"  {{id:'{SCENE_IDS[idx]}',start:{entry['start']},end:{entry['end']}}},")
    lines.append("];")
    lines.append("export const DURATION=scenes.at(-1).end;")
    lines.append("export const ARABIC_FONT={family:'Cairo',urls:['/assets/fonts/Cairo/Cairo_800ExtraBold.ttf'],descriptors:{weight:'800'}};")
    (ROOT / "src/data.js").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "cache/scene-measurements.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
