"""Unit tests for the studio caption-alignment logic (tools/caption_align.py).

These cover the pure, model-free functions: Arabic normalization, DP alignment
of ASR words onto a script, speech-envelope detection, onset snap + hold +
monotonic guard, and caption/data module emission. No faster-whisper required.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

_SPEC = importlib.util.spec_from_file_location(
    "caption_align", Path(__file__).resolve().parents[1] / "tools" / "caption_align.py"
)
ca = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ca)


def test_norm_unifies_arabic_forms():
    assert ca.norm("أحمد") == ca.norm("احمد")
    assert ca.norm("مدرسة") == ca.norm("مدرسه")
    assert ca.norm("عَلَى") == ca.norm("علي")  # diacritics + yeh form
    assert ca.norm("الفرق؟") == ca.norm("الفرق")
    assert ca.norm("  RAM ") == "ram"


def test_dp_align_matches_and_times():
    script = ["قبل", "ما", "تشتري", "لابتوب"]
    asr = [
        {"text": "قبل", "start": 0.8, "end": 1.0},
        {"text": "ما", "start": 1.0, "end": 1.2},
        {"text": "تشتري", "start": 1.2, "end": 1.6},
        {"text": "لابتوب", "start": 1.6, "end": 2.3},
    ]
    out = ca.dp_align(script, asr)
    assert [w["text"] for w in out] == script
    assert all(w["src"] == "asr" for w in out)
    assert out[0]["start"] == 0.8 and out[-1]["end"] == 2.3


def test_dp_align_maps_spoken_number_to_digit():
    script = ["فيها", "32", "جيجا"]
    asr = [
        {"text": "فيها", "start": 6.8, "end": 7.0},
        {"text": "32", "start": 7.1, "end": 7.6},
        {"text": "جيجا", "start": 7.7, "end": 8.0},
    ]
    out = ca.dp_align(script, asr)
    assert out[1]["text"] == "32"
    assert out[1]["start"] == 7.1 and out[1]["src"] == "asr"


def test_dp_align_fills_gap_proportionally():
    script = ["a", "bb", "cccc", "d"]  # middle two unmatched
    asr = [
        {"text": "a", "start": 0.0, "end": 0.5},
        {"text": "d", "start": 2.0, "end": 2.5},
    ]
    out = ca.dp_align(script, asr)
    assert out[0]["src"] == "asr" and out[3]["src"] == "asr"
    # gap words lie strictly between the anchors and are ordered
    assert out[0]["end"] <= out[1]["start"] <= out[1]["end"] <= out[2]["start"] <= out[2]["end"] <= out[3]["start"]
    # longer token gets a longer share of the gap
    assert (out[2]["end"] - out[2]["start"]) > (out[1]["end"] - out[1]["start"])


def test_speech_regions_detects_activity():
    sr = 24000
    silence = np.zeros(int(sr * 0.5), dtype=np.float32)
    tone = (0.2 * np.sin(2 * np.pi * 220 * np.arange(int(sr * 0.5)) / sr)).astype(np.float32)
    x = np.concatenate([silence, tone, silence])
    regions = ca.speech_regions(x, sr)
    assert len(regions) == 1
    a, b = regions[0]
    assert abs(a - 0.5) < 0.05 and abs(b - 1.0) < 0.05


def test_snap_and_hold_monotonic_and_holds():
    words = [
        {"text": "واحد", "start": 0.1},   # early onset in silence -> snapped
        {"text": "اتنين", "start": 0.9},
        {"text": "تلاتة", "start": 0.9},  # duplicate onset -> separated
    ]
    regions = [(0.5, 2.0)]
    out = ca.snap_and_hold(words, regions, scene_dur=3.0)
    assert out[0]["start"] >= 0.5  # snapped to speech start
    starts = [w["start"] for w in out]
    assert starts == sorted(starts)
    assert all(starts[i] > starts[i - 1] for i in range(1, len(starts)))
    # each word holds until the next begins
    for i in range(len(out) - 1):
        assert out[i]["end"] == out[i + 1]["start"]
    assert all(w["end"] > w["start"] for w in out)


def test_emit_caption_module_format():
    words = [{"text": "قبل", "start": 0.865, "end": 1.04}, {"text": "ما", "start": 1.04, "end": 1.16}]
    js = ca.emit_caption_module("S01", words)
    assert "export const CAPTIONS_S01 = [" in js
    assert '{ text: "قبل", start: 0.865, end: 1.04 },' in js
    assert js.rstrip().endswith("];")


def test_emit_data_js_map():
    scenes = [
        {"id": "S01", "module": "ram-intro", "start": 0.0, "end": 8.433},
        {"id": "S02", "module": "ram-question", "start": 8.433, "end": 12.358},
    ]
    js = ca.emit_data_js(scenes)
    assert "export const W=1080,H=1920,FPS=30;" in js
    assert "{id:'ram-intro',start:0.0,end:8.433}," in js
    assert "export const DURATION=scenes.at(-1).end;" in js
