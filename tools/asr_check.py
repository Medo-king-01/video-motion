#!/usr/bin/env python3
"""ASR & word-timing sanity auditor: hallucinations, loops, bad bounds, and missed speech gaps.

    python3 tools/asr_check.py projects/my-reel
    python3 tools/asr_check.py plan/word-timings.json --vo out/vo24.wav --script plan/script.md --json
    python3 tools/asr_check.py cache/scene-measurements.json --vo out/vo24.wav --strict

Checks:
  - A01 (error):   Known Arabic/English Whisper silence hallucinations not present in the script
  - A02 (error):   4x consecutive word stutter loop or Whisper segment `compression_ratio > 2.4`
  - A03 (error):   Invalid, inverted, overlapping, >3.5s stretched, or post-VO word timestamps
  - A04 (warning): Untranscribed gap >= 1.0s containing >= 0.6s of voiced energy in the VO WAV
                   (exits non-zero when `--strict` is set)

Accepts a project directory (auto-discovering `plan/word-timings.json` or
`cache/scene-measurements.json`, `out/vo24.wav`, and `plan/script.md`) or a direct JSON path.
Inspired by Whisper QA checks in MIT-licensed `majedphotos/video-ad-editor` (see assets/CREDITS.md).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import wave
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
sys.path.insert(0, str(SKILL / "scripts"))

from _safe_paths import checked_path  # noqa: E402

HALLUCINATION_PHRASES = (
    "اشتركوا في القناه",
    "لا تنسوا الاشتراك",
    "فعلوا الجرس",
    "ترجمه نانسي",
    "نانسي قنقر",
    "شكرا للمشاهده",
    "شكرا على المشاهده",
    "شاهدوا ايضا",
    "ترجمه وتحرير",
    "thank you for watching",
    "thanks for watching",
    "subtitles by",
    "amara org",
)

_NORM_AR_RE = re.compile(r"[\u064B-\u065F\u0670\u0640]")
_NON_WORD_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def _safe_abs(path: Path, *, tree: bool = False) -> Path:
    checked_path(Path(os.path.abspath(path)), tree=tree)
    return checked_path(path.resolve(), tree=tree)


def normalize_text(text: str) -> str:
    s = _NORM_AR_RE.sub("", str(text or "")).lower()
    s = (
        s.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ٱ", "ا")
        .replace("ة", "ه")
        .replace("ى", "ي")
    )
    s = _NON_WORD_RE.sub(" ", s)
    return " ".join(s.split())


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))


def _extract_words_and_meta(doc: Any) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """Return `(global_timed_words, raw_asr_texts, segment_meta)` across studio JSON formats."""
    words: list[dict[str, Any]] = []
    asr_texts: list[str] = []
    segments_meta: list[dict[str, Any]] = []

    if isinstance(doc, dict):
        if isinstance(doc.get("segments"), list):
            for seg in doc["segments"]:
                if not isinstance(seg, dict):
                    continue
                segments_meta.append(seg)
                if isinstance(seg.get("text"), str):
                    asr_texts.append(seg["text"])
                for w in seg.get("words") or []:
                    if isinstance(w, dict):
                        words.append({
                            "text": str(w.get("text") if "text" in w else w.get("word", "")).strip(),
                            "start": w.get("start"),
                            "end": w.get("end"),
                        })
        elif isinstance(doc.get("words"), list):
            for w in doc["words"]:
                if isinstance(w, dict):
                    words.append({
                        "text": str(w.get("text") if "text" in w else w.get("word", "")).strip(),
                        "start": w.get("start"),
                        "end": w.get("end"),
                    })
        elif isinstance(doc.get("scenes"), list):
            return _extract_words_and_meta(doc["scenes"])
    elif isinstance(doc, list):
        if doc and isinstance(doc[0], dict) and ("final" in doc[0] or "asr" in doc[0] or "words" in doc[0]):
            # `plan/word-timings.json` (`scenes: [{scene, words: [...]}]`) or `cache/scene-measurements.json`
            clock_scene_local = any("final" in sc for sc in doc if isinstance(sc, dict))
            for sc in doc:
                if not isinstance(sc, dict):
                    continue
                g0 = (
                    float(sc.get("start", 0.0))
                    if (clock_scene_local and _is_num(sc.get("start")))
                    else 0.0
                )
                for aw in sc.get("asr") or []:
                    if isinstance(aw, dict) and isinstance(aw.get("text"), str):
                        asr_texts.append(aw["text"])
                if isinstance(sc.get("asr"), list) and sc["asr"]:
                    asr_texts.append(" ".join(str(x.get("text", "")) for x in sc["asr"] if isinstance(x, dict)))
                seq = sc.get("final") if "final" in sc else sc.get("words")
                for fw in seq or []:
                    if isinstance(fw, dict):
                        s = fw.get("start")
                        e = fw.get("end")
                        words.append({
                            "text": str(fw.get("text") if "text" in fw else fw.get("word", "")).strip(),
                            "start": (float(s) + g0) if _is_num(s) else s,
                            "end": (float(e) + g0) if _is_num(e) else e,
                        })
        else:
            for w in doc:
                if isinstance(w, dict):
                    words.append({
                        "text": str(w.get("text") if "text" in w else w.get("word", "")).strip(),
                        "start": w.get("start"),
                        "end": w.get("end"),
                    })
    return words, asr_texts, segments_meta


def _read_mono_wav(wav_path: Path) -> tuple[np.ndarray, int, float]:
    with wave.open(str(wav_path), "rb") as wf:
        ch = wf.getnchannels()
        sw = wf.getsampwidth()
        sr = wf.getframerate()
        nf = wf.getnframes()
        raw = wf.readframes(nf)
    if sw != 2 or sr <= 0 or nf <= 0:
        raise ValueError(f"{wav_path.name}: expected 16-bit PCM WAV, got width={sw * 8}b rate={sr} frames={nf}")
    pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        pcm = pcm.reshape(-1, ch).mean(axis=1)
    return pcm, sr, nf / float(sr)


def _find_voiced_gaps(
    words: list[dict[str, Any]],
    pcm: np.ndarray,
    sr: int,
    vo_duration: float,
    *,
    min_gap_s: float = 1.0,
    min_voiced_s: float = 0.6,
) -> list[dict[str, float]]:
    win = max(1, int(round(sr * 0.02)))  # 20ms energy frame
    usable = (len(pcm) // win) * win
    if usable <= 0:
        return []
    frames = pcm[:usable].reshape(-1, win)
    rms = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
    db = 20.0 * np.log10(rms)
    noise_floor = float(np.percentile(db, 15))
    thresh_db = max(-35.0, min(-22.0, noise_floor + 12.0))
    voiced_mask = db > thresh_db

    valid = [
        (float(w["start"]), float(w["end"]))
        for w in words
        if _is_num(w.get("start")) and _is_num(w.get("end")) and float(w["end"]) > float(w["start"])
    ]
    valid.sort()

    intervals: list[tuple[float, float]] = []
    cursor = 0.0
    for s, e in valid:
        if s - cursor >= min_gap_s:
            intervals.append((cursor, s))
        cursor = max(cursor, e)
    if vo_duration - cursor >= min_gap_s:
        intervals.append((cursor, vo_duration))

    flagged: list[dict[str, float]] = []
    for g0, g1 in intervals:
        i0 = max(0, int(math.floor(g0 / 0.02)))
        i1 = min(len(voiced_mask), int(math.ceil(g1 / 0.02)))
        if i1 <= i0:
            continue
        voiced_s = float(voiced_mask[i0:i1].sum()) * 0.02
        if voiced_s >= min_voiced_s:
            flagged.append({
                "start": round(g0, 3),
                "end": round(g1, 3),
                "gap_s": round(g1 - g0, 3),
                "voiced_s": round(voiced_s, 3),
            })
    return flagged


def audit_asr(
    target: Path,
    *,
    vo_path: Path | None = None,
    script_path: Path | None = None,
    max_word_s: float = 3.5,
    min_gap_s: float = 1.0,
    min_voiced_s: float = 0.6,
) -> dict[str, Any]:
    resolved = _safe_abs(target, tree=target.is_dir())
    if resolved.is_dir():
        candidates = [
            resolved / "plan" / "word-timings.json",
            resolved / "cache" / "scene-measurements.json",
        ]
        timings_file = next((p for p in candidates if p.is_file()), None)
        if timings_file is None:
            raise FileNotFoundError(f"No plan/word-timings.json or cache/scene-measurements.json in {resolved}")
        if vo_path is None and (resolved / "out" / "vo24.wav").is_file():
            vo_path = resolved / "out" / "vo24.wav"
        if script_path is None and (resolved / "plan" / "script.md").is_file():
            script_path = resolved / "plan" / "script.md"
    else:
        if not resolved.is_file():
            raise FileNotFoundError(f"Timings file not found: {resolved}")
        timings_file = resolved

    vo_resolved = _safe_abs(vo_path) if vo_path is not None else None
    script_resolved = _safe_abs(script_path) if script_path is not None else None

    doc = json.loads(timings_file.read_text(encoding="utf-8"))
    words, asr_texts, segments_meta = _extract_words_and_meta(doc)

    script_norm = ""
    if script_resolved is not None and script_resolved.is_file():
        script_norm = normalize_text(script_resolved.read_text(encoding="utf-8"))

    issues: list[dict[str, str]] = []

    def add(level: str, code: str, msg: str) -> None:
        issues.append({"level": level, "code": code, "msg": msg})

    if not words:
        add("error", "A03", f"{timings_file.name} contains zero timed words")

    # A01: Known Whisper silence/outro hallucinations
    joined_words_norm = normalize_text(" ".join(w.get("text", "") for w in words))
    joined_asr_norm = normalize_text(" ".join(asr_texts))
    for phrase in HALLUCINATION_PHRASES:
        if phrase in script_norm:
            continue
        if phrase in joined_words_norm or phrase in joined_asr_norm:
            add("error", "A01", f"Whisper hallucination phrase detected ({phrase!r}) and absent from script")

    # A02: Consecutive word repetition loops & high compression_ratio segments
    norm_tokens = [normalize_text(w.get("text", "")) for w in words]
    run_len = 0
    prev_tok = ""
    for idx, tok in enumerate(norm_tokens):
        if tok and tok == prev_tok:
            run_len += 1
            if run_len == 4:
                repeated = " ".join([tok] * 4)
                if repeated not in script_norm:
                    add("error", "A02", f"4x consecutive repeated word loop {tok!r} around word #{idx}")
        else:
            prev_tok = tok
            run_len = 1

    for idx, seg in enumerate(segments_meta):
        cr = seg.get("compression_ratio")
        if _is_num(cr) and float(cr) > 2.4:
            add("error", "A02", f"Segment #{idx} has abnormal compression_ratio={float(cr):.2f} (>2.4 hallucination risk)")

    # Load VO WAV if available for duration & gap energy checks
    vo_duration: float | None = None
    pcm: np.ndarray | None = None
    sr = 0
    if vo_resolved is not None and vo_resolved.is_file():
        pcm, sr, vo_duration = _read_mono_wav(vo_resolved)

    # A03: Timestamp anomalies
    prev_end = 0.0
    for idx, w in enumerate(words):
        txt = w.get("text", "")
        s, e = w.get("start"), w.get("end")
        if not isinstance(txt, str) or not txt.strip():
            add("error", "A03", f"Word #{idx} has empty text")
            continue
        if not _is_num(s) or not _is_num(e):
            add("error", "A03", f"Word #{idx} ({txt!r}) has non-numeric start/end")
            continue
        sf, ef = float(s), float(e)
        if sf < 0 or ef <= sf:
            add("error", "A03", f"Word #{idx} ({txt!r}) has inverted/negative timing ({sf:.3f}..{ef:.3f}s)")
            continue
        if idx > 0 and sf < prev_end - 0.005:
            add("error", "A03", f"Word #{idx} ({txt!r}) overlaps previous word ({sf:.3f}s < {prev_end:.3f}s)")
        if ef - sf > max_word_s:
            add("error", "A03", f"Word #{idx} ({txt!r}) spans {ef - sf:.2f}s (> {max_word_s:.1f}s stretch anomaly)")
        if vo_duration is not None and ef > vo_duration + 0.15:
            add("error", "A03", f"Word #{idx} ({txt!r}) ends at {ef:.3f}s past VO duration {vo_duration:.3f}s")
        prev_end = max(prev_end, ef)

    # A04: Untranscribed voiced speech gaps
    voiced_gaps: list[dict[str, float]] = []
    if pcm is not None and vo_duration is not None and words:
        voiced_gaps = _find_voiced_gaps(
            words, pcm, sr, vo_duration, min_gap_s=min_gap_s, min_voiced_s=min_voiced_s,
        )
        for g in voiced_gaps:
            add(
                "warning",
                "A04",
                f"Untranscribed speech gap {g['start']:.2f}..{g['end']:.2f}s "
                f"({g['gap_s']:.2f}s gap contains {g['voiced_s']:.2f}s of voiced audio)",
            )

    errors = [x for x in issues if x["level"] == "error"]
    warnings = [x for x in issues if x["level"] == "warning"]
    status = "fail" if errors else ("warn" if warnings else "pass")
    return {
        "version": 1,
        "status": status,
        "timings_file": str(timings_file),
        "vo_file": str(vo_resolved) if vo_resolved else None,
        "vo_duration_s": round(vo_duration, 3) if vo_duration is not None else None,
        "word_count": len(words),
        "errors": errors,
        "warnings": warnings,
        "voiced_gaps": voiced_gaps,
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", type=Path, help="project directory or word-timings/scene-measurements JSON")
    ap.add_argument("--vo", type=Path, default=None, help="optional mono 16-bit PCM WAV (auto-detected for project dirs)")
    ap.add_argument("--script", type=Path, default=None, help="optional script.md to exempt intentional phrases")
    ap.add_argument("--max-word-s", type=float, default=3.5, help="maximum allowed single-word duration in seconds")
    ap.add_argument("--min-gap-s", type=float, default=1.0, help="minimum word gap in seconds to inspect for missed speech")
    ap.add_argument("--min-voiced-s", type=float, default=0.6, help="voiced audio seconds inside a gap that triggers A04")
    ap.add_argument("--strict", action="store_true", help="promote A04 voiced-gap warnings to a non-zero exit code")
    ap.add_argument("--json", action="store_true", help="emit JSON report to stdout")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_asr(
            args.target,
            vo_path=args.vo,
            script_path=args.script,
            max_word_s=args.max_word_s,
            min_gap_s=args.min_gap_s,
            min_voiced_s=args.min_voiced_s,
        )
    except BaseException as error:  # noqa: BLE001
        if isinstance(error, SystemExit):
            raise
        if args.json:
            print(json.dumps({"version": 1, "status": "error", "error": str(error)}, ensure_ascii=False))
        else:
            print(f"asr_check error: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(
            f"asr_check [{report['status'].upper()}] · {report['word_count']} word(s)"
            + (f" · VO {report['vo_duration_s']:.2f}s" if report["vo_duration_s"] is not None else "")
        )
        for item in report["errors"]:
            print(f"  FAIL [{item['code']}] {item['msg']}")
        for item in report["warnings"]:
            print(f"  WARN [{item['code']}] {item['msg']}")

    if report["errors"] or (args.strict and report["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
