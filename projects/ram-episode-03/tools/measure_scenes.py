#!/usr/bin/env python3
"""Measure per-scene word timings for S02–S10 with the local Whisper model.

v2: no VAD (it dropped speech), repetition penalty (S07 hallucination loop),
punctuation-insensitive matching, and DP alignment of ASR words onto the
approved script (spoken numbers like "اتنين وتلاتين" map onto "32").
Output: cache/scene-measurements.json with caption-ready script-word timelines.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = "/home/user/video-motion/.cache/whisper-model-hunt/whisper-small-ct2-int8"
VO = ROOT / "assets/vo/episode-03-ram.wav"

# Cuts at silence midpoints (ffmpeg silencedetect -38dB on the real WAV),
# cross-checked against the full-audio Whisper transcript.
# S09/S10 cut moved to ~67.0: "دلوقتي" starts ≈67.28 (old 68.386 cut inside S10).
BOUNDS = [0.0, 8.433, 12.358, 19.951, 22.042, 33.44, 45.254, 57.469, 62.41, 67.0, 70.52]

PUNCT = "،.!؟?;:«»\"'…ـ()[]{}،"


def norm(w: str) -> str:
    w = re.sub(r"[\u064B-\u0652\u0640]", "", w)
    w = "".join(ch for ch in w if ch not in PUNCT)
    w = w.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    return w.lower().strip()


def slice_wav(src: Path, dst: Path, start: float, end: float) -> None:
    with wave.open(str(src), "rb") as w:
        sr = w.getframerate()
        w.setpos(int(start * sr))
        frames = w.readframes(int((end - start) * sr))
    with wave.open(str(dst), "wb") as o:
        o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr)
        o.writeframes(frames)


def align(script: list[str], asr: list[dict]) -> list[dict]:
    """DP-align script words to ASR words; return script words with measured times.

    Substitution cost = 1 - similarity; gaps allowed. Contiguous unmatched script
    words inside a matched span share that span proportionally (by char length).
    """
    sw = [norm(w) for w in script]
    aw = [norm(w["text"]) for w in asr]
    n, m = len(sw), len(aw)

    def sim(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return difflib.SequenceMatcher(None, a, b).ratio()

    # cost matrix
    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    bt = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            if dp[i][j] == INF:
                continue
            if i < n and j < m:
                c = dp[i][j] + (1.0 - sim(sw[i], aw[j])) + 0.05
                if c < dp[i + 1][j + 1]:
                    dp[i + 1][j + 1] = c; bt[i + 1][j + 1] = ("sub", i, j)
            if i < n:
                c = dp[i][j] + 0.9
                if c < dp[i + 1][j]:
                    dp[i + 1][j] = c; bt[i + 1][j] = ("del", i, j)
            if j < m:
                c = dp[i][j] + 0.9
                if c < dp[i][j + 1]:
                    dp[i][j + 1] = c; bt[i][j + 1] = ("ins", i, j)
    # backtrack
    pairs = {}
    i, j = n, m
    while (i, j) != (0, 0):
        op, pi, pj = bt[i][j]
        if op == "sub":
            pairs[pi] = pj
        i, j = pi, pj
    # build timeline: matched words take ASR times; unmatched fill gaps
    out = [{"text": script[k], "start": None, "end": None, "src": "gap"} for k in range(n)]
    for k, j in list(pairs.items()):
        s = sim(sw[k], aw[j])
        if s >= 0.34 or (sw[k].isdigit() and aw[j].isdigit()):
            out[k].update(start=asr[j]["start"], end=asr[j]["end"], src="asr", sim=round(s, 2))
        else:
            del pairs[k]
    # number special-case: script "32" may be spoken as two words; merge spans
    # handled naturally by gap fill below.
    # fill gaps between anchors
    anchors = [k for k in range(n) if out[k]["start"] is not None]
    if not anchors:
        return out
    # leading gap: from first anchor start backwards is unknown; clamp to anchor
    first = anchors[0]
    for k in range(first):
        out[k]["start"] = out[first]["start"]
        out[k]["end"] = out[first]["start"]
    # trailing gap
    last = anchors[-1]
    for k in range(last + 1, n):
        out[k]["start"] = out[last]["end"]
        out[k]["end"] = out[last]["end"]
    # interior gaps: proportional by char length between prev.end and next.start
    for a, b in zip(anchors, anchors[1:]):
        if b == a + 1:
            continue
        t0, t1 = out[a]["end"], out[b]["start"]
        if t1 <= t0:
            t1 = t0 + 0.01 * (b - a - 1)
        lens = [max(1, len(norm(script[k]))) for k in range(a + 1, b)]
        total = sum(lens)
        t = t0
        for k, L in zip(range(a + 1, b), lens):
            dur = (t1 - t0) * L / total
            out[k]["start"] = round(t, 3)
            out[k]["end"] = round(t + dur, 3)
            t += dur
    for k in range(n):
        if out[k]["start"] is not None:
            out[k]["start"] = round(float(out[k]["start"]), 3)
            out[k]["end"] = round(float(out[k]["end"]), 3)
    return out


def main() -> int:
    from faster_whisper import WhisperModel
    scenes = json.loads((ROOT / "cache/script-scenes.json").read_text(encoding="utf-8"))
    model = WhisperModel(MODEL, device="cpu", compute_type="int8", cpu_threads=2, num_workers=1, local_files_only=True)
    out = []
    cache = ROOT / "cache/scene-slices"; cache.mkdir(parents=True, exist_ok=True)
    for i, sc in enumerate(scenes):
        start, end = BOUNDS[i], BOUNDS[i + 1]
        if sc["id"] == "S01":
            prev = json.loads((ROOT / "artifacts/s01-v6-measured-words.json").read_text(encoding="utf-8"))
            out.append({"id": "S01", "start": start, "end": end, "words": prev["final_caption_timeline"], "status": "approved-v6"})
            continue
        wav = cache / f"{sc['id']}.wav"
        slice_wav(VO, wav, start, end)
        segments, _ = model.transcribe(
            str(wav), language="ar", task="transcribe", beam_size=5, word_timestamps=True,
            vad_filter=False, condition_on_previous_text=False, initial_prompt=sc["text"],
            temperature=0.0, repetition_penalty=1.15, no_repeat_ngram_size=3,
        )
        asr = []
        for seg in segments:
            for w in seg.words or []:
                asr.append({"text": w.word.strip(), "start": round(float(w.start), 3), "end": round(float(w.end), 3), "p": round(float(w.probability), 3)})
        timeline = align(sc["words"], asr)
        matched = sum(1 for w in timeline if w["src"] == "asr")
        out.append({"id": sc["id"], "start": start, "end": end, "words": timeline,
                    "status": f"{matched}/{len(sc['words'])} asr-matched", "asr": asr})
        print(f"{sc['id']} [{start:.3f}-{end:.3f}] matched={matched}/{len(sc['words'])}", flush=True)
        print("  asr:", " | ".join(w["text"] for w in asr), flush=True)
        for w in timeline:
            if w["src"] != "asr":
                print(f"  GAP {w['text']} -> {w['start']}-{w['end']}", flush=True)
    (ROOT / "cache/scene-measurements.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote cache/scene-measurements.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
