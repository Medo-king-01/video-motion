#!/usr/bin/env python3
"""Build measured, caption-ready word timelines from a script + the real VO.

Studio alignment infrastructure (see docs/alignment.md).

Pipeline (per scene):
  1. slice the VO at the scene bounds,
  2. transcribe the slice with a local faster-whisper CT2 model (no VAD,
     repetition penalty) to get ASR word times,
  3. DP-align the ASR words onto the approved script words (spoken numbers like
     "اتنين وتلاتين" map onto "32"; punctuation/diacritics ignored),
  4. snap early onsets to the measured speech envelope, hold each word until the
     next begins, and enforce strict monotonic order,
  5. emit one unboxed-caption module per scene + a data.js scene map.

The pure functions (norm, dp_align, speech_regions, snap_and_hold, emit_*) are
importable and unit-tested without any model. The CLI needs faster-whisper +
ctranslate2 (tools/requirements-align.txt) and a model from tools/whisper_fetch.py.

Scenes JSON: a list of objects
    {"id": "S01", "module": "ram-intro", "text": "...", "words": ["قبل", ...],
     "start": 0.0, "end": 8.433}
`module` defaults to a slug of `id`; `words` defaults to text.split().
Frozen scenes require `final`: [{"text": "...", "start": 0.1, "end": 0.5}]
with scene-local timings matching the script. Input VO must be mono PCM16 WAV.

Usage:
    python3 tools/caption_align.py --scenes plan/script-scenes.json \\
        --vo assets/vo/episode.wav --model .cache/whisper-small-ct2-int8 \\
        --out-dir src --lang ar --freeze S01
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import re
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "medo-motion" / "scripts"))
from _safe_paths import checked_path  # noqa: E402

PUNCT = "،.!؟?;:«»\"'…ـ()[]{}،"


def norm(w: str) -> str:
    """Normalize an Arabic token for matching: strip diacritics/tatweel/punct,
    unify alef/teh-marbuta/yeh forms, lowercase."""
    w = re.sub(r"[\u064B-\u0652\u0640]", "", w)
    w = "".join(ch for ch in w if ch not in PUNCT)
    w = w.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    return w.lower().strip()


def _sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def dp_align(script: list[str], asr: list[dict]) -> list[dict]:
    """DP-align script words to ASR words; return script words with measured times.

    asr: [{"text", "start", "end"}]. Substitution cost = 1 - similarity + 0.05;
    gap cost 0.9. Matched words take ASR times; unmatched script words fill the
    gaps between anchors proportionally by normalized char length.
    """
    sw = [norm(w) for w in script]
    aw = [norm(w["text"]) for w in asr]
    n, m = len(sw), len(aw)
    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    bt = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            if dp[i][j] == INF:
                continue
            if i < n and j < m:
                c = dp[i][j] + (1.0 - _sim(sw[i], aw[j])) + 0.05
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
    pairs = {}
    i, j = n, m
    while (i, j) != (0, 0):
        op, pi, pj = bt[i][j]
        if op == "sub":
            pairs[pi] = pj
        i, j = pi, pj
    out = [{"text": script[k], "start": None, "end": None, "src": "gap"} for k in range(n)]
    for k, j in list(pairs.items()):
        s = _sim(sw[k], aw[j])
        if s >= 0.34 or (sw[k].isdigit() and aw[j].isdigit()):
            out[k].update(start=asr[j]["start"], end=asr[j]["end"], src="asr", sim=round(s, 2))
        else:
            del pairs[k]
    anchors = [k for k in range(n) if out[k]["start"] is not None]
    if not anchors:
        raise ValueError("No ASR word anchors matched the script; check speech/model/language before retrying")
    first = anchors[0]
    for k in range(first):
        out[k]["start"] = out[first]["start"]; out[k]["end"] = out[first]["start"]
    last = anchors[-1]
    for k in range(last + 1, n):
        out[k]["start"] = out[last]["end"]; out[k]["end"] = out[last]["end"]
    for a, b in zip(anchors, anchors[1:], strict=False):
        if b == a + 1:
            continue
        t0, t1 = out[a]["end"], out[b]["start"]
        if t1 <= t0:
            t1 = t0 + 0.01 * (b - a - 1)
        lens = [max(1, len(norm(script[k]))) for k in range(a + 1, b)]
        total = sum(lens)
        t = t0
        for k, L in zip(range(a + 1, b), lens, strict=True):
            dur = (t1 - t0) * L / total
            out[k]["start"] = round(t, 3); out[k]["end"] = round(t + dur, 3)
            t += dur
    for k in range(n):
        if out[k]["start"] is not None:
            out[k]["start"] = round(float(out[k]["start"]), 3)
            out[k]["end"] = round(float(out[k]["end"]), 3)
    return out


def speech_regions(x, sr: int, thresh: float = 0.012) -> list[tuple[float, float]]:
    """Speech activity regions from a 20 ms RMS envelope of mono float samples."""
    import numpy as np
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


def snap_and_hold(words: list[dict], regions: list[tuple[float, float]], scene_dur: float) -> list[dict]:
    """Snap early onsets to speech, sort by onset, hold each word until the next
    begins, and enforce strict monotonic order. words: [{"text","start",...}]."""
    if not words or any(w.get("start") is None for w in words):
        raise ValueError("No measured word onsets; cannot snap captions without ASR anchors")
    if not math.isfinite(scene_dur) or scene_dur <= 0:
        raise ValueError("scene duration must be positive and finite")
    fixed = []
    for i, w in enumerate(words):
        t = float(w["start"])
        if not math.isfinite(t) or t < 0:
            raise ValueError("word onset must be non-negative and finite")
        for a, _b in regions:
            if a - 0.12 > t and a - t < 0.9 and (i == 0 or t <= words[i - 1]["start"] + 0.001):
                t = round(a, 3)
                break
        if i == 0 and regions and t < regions[0][0] - 0.02:
            t = round(regions[0][0], 3)
        fixed.append({"text": str(w["text"]).strip("،.!؟?: "), "start": t})
    fixed.sort(key=lambda w: w["start"])
    out = []
    for i, w in enumerate(fixed):
        end = fixed[i + 1]["start"] if i + 1 < len(fixed) else min(round(w["start"] + 0.6, 3), round(scene_dur, 3))
        if end <= w["start"]:
            end = round(w["start"] + 0.05, 3)
        out.append({"text": w["text"], "start": round(w["start"], 3), "end": round(end, 3)})
    for i in range(1, len(out)):
        if out[i]["start"] <= out[i - 1]["start"]:
            out[i]["start"] = round(out[i - 1]["start"] + 0.03, 3)
        if out[i]["start"] < out[i - 1]["end"]:
            out[i - 1]["end"] = out[i]["start"]
        if out[i]["end"] <= out[i]["start"]:
            out[i]["end"] = round(out[i]["start"] + 0.05, 3)
    for w in out:
        w["end"] = min(w["end"], scene_dur)
        if not 0 <= w["start"] < w["end"] <= scene_dur:
            raise ValueError("Measured captions exceed scene bounds; review scene cuts")
    return out


def emit_caption_module(scene_id: str, words: list[dict], note: str = "measured local Whisper CT2 int8 on the real VO") -> str:
    """One unboxed-caption ES module: export const CAPTIONS_<ID> = [...]."""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", scene_id):
        raise ValueError("invalid scene id")
    validate_timed_words(words)
    note = note.replace("\n", " ").replace("\r", " ").replace("\u2028", " ").replace("\u2029", " ")
    sid = scene_id.upper().replace("-", "_")
    lines = [f"// {scene_id} word-level timeline — {note}.",
             "// Onsets validated against the WAV speech envelope; each word holds until the next begins.",
             f"export const CAPTIONS_{sid} = ["]
    for w in words:
        lines.append(f"  {{ text: {json.dumps(w['text'], ensure_ascii=False)}, start: {w['start']}, end: {w['end']} }},")
    lines.append("];")
    return "\n".join(lines) + "\n"


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def emit_data_js(scenes: list[dict], font_family: str = "Cairo",
                 font_url: str = "/assets/fonts/Cairo/Cairo_800ExtraBold.ttf") -> str:
    """Scene map module: W/H/FPS + scenes[] (id=module slug, start, end) + DURATION."""
    lines = ["// Measured scene map (local Whisper word alignment + silence-midpoint cuts).",
             "export const W=1080,H=1920,FPS=30;", "export const scenes=["]
    for sc in scenes:
        module = sc.get("module") or _slug(sc["id"])
        entry = {"id": module, "start": sc["start"], "end": sc["end"]}
        lines.append("  " + json.dumps(entry, ensure_ascii=False, allow_nan=False) + ",")
    lines.append("];")
    lines.append("export const DURATION=scenes.at(-1).end;")
    font = {"family": font_family, "urls": [font_url], "descriptors": {"weight": "800"}}
    lines.append("export const ARABIC_FONT=" + json.dumps(font, ensure_ascii=False, allow_nan=False) + ";")
    return "\n".join(lines) + "\n"


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_timed_words(words, duration=float("inf")):
    if not isinstance(words, list) or not words:
        raise ValueError("frozen final must be a non-empty list of {text,start,end}")
    previous_end = 0.0
    for word in words:
        if not isinstance(word, dict) or not isinstance(word.get("text"), str) or not word["text"].strip():
            raise ValueError("timed words require non-empty text")
        start, end = word.get("start"), word.get("end")
        if not _number(start) or not _number(end) or not previous_end <= start < end <= duration:
            raise ValueError("timed words must be finite, ordered, non-overlapping and within the scene")
        previous_end = end


def validate_scenes(scenes, freeze):
    """words are script strings; frozen final contains scene-local timed words."""
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("scenes must be a non-empty JSON list")
    ids, modules, exports = set(), set(), set()
    previous_end = 0.0
    for scene in scenes:
        if not isinstance(scene, dict):
            raise ValueError("each scene must be an object")
        sid = scene.get("id")
        if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", sid):
            raise ValueError("scene id must be a safe ASCII identifier")
        exported = sid.upper().replace("-", "_")
        module = scene.get("module", _slug(sid))
        if not isinstance(module, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", module):
            raise ValueError(f"{sid}: module must be a lowercase slug, not a path")
        if sid.lower() in ids or exported in exports or module in modules:
            raise ValueError("scene ids, exports and modules must be unique")
        ids.add(sid.lower()); exports.add(exported); modules.add(module)
        start, end = scene.get("start"), scene.get("end")
        if not _number(start) or not _number(end) or not previous_end <= start < end:
            raise ValueError(f"{sid}: scene bounds must be finite, ordered and non-overlapping")
        previous_end = end
        if not isinstance(scene.get("text"), str) or not scene["text"].strip():
            raise ValueError(f"{sid}: non-empty text is required")
        words = scene.get("words", scene["text"].split())
        if not isinstance(words, list) or not words or any(not isinstance(w, str) or not w.strip() for w in words):
            raise ValueError(f"{sid}: words must be a non-empty list of script strings; put frozen timings in final")
        if sid in freeze:
            validate_timed_words(scene.get("final"), end - start)
            if [norm(w["text"]) for w in scene["final"]] != [norm(w) for w in words]:
                raise ValueError(f"{sid}: frozen final text must match script words")
    unknown = freeze - {scene["id"] for scene in scenes}
    if unknown:
        raise ValueError(f"unknown frozen scene ids: {sorted(unknown)}")


def validate_wav(src):
    with wave.open(str(src), "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getcomptype() != "NONE":
            raise ValueError("VO must be mono PCM16 WAV; convert with ffmpeg -i input -ac 1 -c:a pcm_s16le output.wav")
        if w.getnframes() <= 0 or w.getframerate() <= 0:
            raise ValueError("VO WAV must contain audio samples")
        return w.getframerate(), w.getnframes() / w.getframerate()


def _slice_wav(src: Path, dst: Path, start: float, end: float) -> None:
    sr, duration = validate_wav(src)
    if not 0 <= start < end <= duration:
        raise ValueError("slice bounds exceed VO duration")
    with wave.open(str(src), "rb") as w:
        sr = w.getframerate()
        w.setpos(int(start * sr))
        frames = w.readframes(int((end - start) * sr))
    with wave.open(str(dst), "wb") as o:
        o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr)
        o.writeframes(frames)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenes", type=Path, required=True, help="JSON list of {id,text,words,start,end}")
    ap.add_argument("--vo", type=Path, required=True)
    ap.add_argument("--model", type=Path, help="required unless every scene is frozen")
    ap.add_argument("--out-dir", type=Path, default=Path("src"))
    ap.add_argument("--lang", default="ar")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--freeze", default="", help="comma-separated scene ids to keep as-is (approved, no re-snap)")
    ap.add_argument("--measurements", type=Path, default=Path("cache/scene-measurements.json"))
    args = ap.parse_args()

    import numpy as np
    scenes = json.loads(args.scenes.read_text(encoding="utf-8"))
    freeze = {s.strip() for s in args.freeze.split(",") if s.strip()}
    validate_scenes(scenes, freeze)
    sr, duration = validate_wav(args.vo)
    if scenes[-1]["end"] > duration:
        raise ValueError("scene bounds exceed VO duration")
    for target in (args.out_dir, args.measurements.parent / "scene-slices", args.measurements):
        checked_path(target, tree=True)
    needs_model = any(sc["id"] not in freeze for sc in scenes)
    if needs_model and args.model is None:
        ap.error("--model is required for scenes that are not frozen")
    with wave.open(str(args.vo), "rb") as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    if needs_model:
        from faster_whisper import WhisperModel
        model = WhisperModel(str(args.model), device="cpu", compute_type="int8",
                             cpu_threads=args.threads, num_workers=1, local_files_only=True)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    slices = args.measurements.parent / "scene-slices"; slices.mkdir(parents=True, exist_ok=True)
    report = []
    for sc in scenes:
        sid = sc["id"]
        g0, g1 = float(sc["start"]), float(sc["end"])
        script_words = sc.get("words") or sc["text"].split()
        if sid in freeze:
            final = [{"text": w["text"], "start": w["start"], "end": w["end"]} for w in sc["final"]]
            note = "approved (frozen, measured + silence-snapped)"
        else:
            wav = slices / f"{sid}.wav"
            _slice_wav(args.vo, wav, g0, g1)
            segments, _ = model.transcribe(
                str(wav), language=args.lang, task="transcribe", beam_size=5, word_timestamps=True,
                vad_filter=False, condition_on_previous_text=False, initial_prompt=sc.get("text"),
                temperature=(0.0, 0.2, 0.4), repetition_penalty=1.15, no_repeat_ngram_size=3,
            )
            asr = [{"text": w.word.strip(), "start": round(float(w.start), 3), "end": round(float(w.end), 3)}
                   for seg in segments for w in (seg.words or [])]
            aligned = dp_align(script_words, asr)
            regions = speech_regions(x[int(g0 * sr):int(g1 * sr)], sr)
            final = snap_and_hold(aligned, regions, g1 - g0)
            sc["asr"] = asr
            note = "measured local Whisper CT2 int8 on the real VO"
        sc["final"] = final
        (args.out_dir / f"captions-{sid.lower()}.js").write_text(emit_caption_module(sid, final, note), encoding="utf-8")
        report.append(f"{sid} {g0:.3f}-{g1:.3f} words={len(final)} first={final[0]['start']} last_end={final[-1]['end']}")
    (args.out_dir / "data.js").write_text(emit_data_js(scenes), encoding="utf-8")
    args.measurements.parent.mkdir(parents=True, exist_ok=True)
    args.measurements.write_text(json.dumps(scenes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n".join(report))
    print(f"wrote {len(scenes)} caption modules + data.js -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, wave.Error) as error:
        print(f"Caption alignment failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
