"""Unit tests for the studio caption-alignment logic (tools/caption_align.py).

These cover the pure, model-free functions: Arabic normalization, DP alignment
of ASR words onto a script, speech-envelope detection, onset snap + hold +
monotonic guard, and caption/data module emission. No faster-whisper required.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

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
    assert '{"id": "ram-intro", "start": 0.0, "end": 8.433},' in js
    assert "export const DURATION=scenes.at(-1).end;" in js


@pytest.mark.parametrize('asr', [[], [{'text': 'xyz', 'start': 0.0, 'end': 0.4}]])
def test_no_asr_anchors_is_actionable(asr):
    with pytest.raises(ValueError, match='No ASR word anchors'):
        ca.dp_align(['قبل'], asr)
    with pytest.raises(ValueError, match='No measured word onsets'):
        ca.snap_and_hold([{'text': 'قبل', 'start': None}], [], 1.0)


def scene():
    return {'id': 'S01', 'module': 'intro', 'text': 'قبل', 'words': ['قبل'], 'start': 0.0, 'end': 1.0,
            'final': [{'text': 'قبل', 'start': 0.1, 'end': 0.8}]}


def test_scene_schema_and_frozen_words():
    ca.validate_scenes([scene()], {'S01'})
    sc = scene()
    del sc['final']
    with pytest.raises(ValueError, match='frozen final'):
        ca.validate_scenes([sc], {'S01'})
    ca.validate_scenes([sc], set())


@pytest.mark.parametrize(('field', 'value'), [('id', '../escape'), ('id', 'S01\nexport'),
    ('module', '../outside'), ('module', "a';alert(1)//"), ('start', float('nan')), ('end', float('inf')),
    ('words', ['a', {'text': 'b'}]), ('words', []), ('text', '')])
def test_invalid_scene_schema(field, value):
    sc = scene()
    sc[field] = value
    with pytest.raises(ValueError):
        ca.validate_scenes([sc], set())


@pytest.mark.parametrize('words', [[{'text': 'قبل', 'start': None, 'end': 1}],
    [{'text': 'قبل', 'start': 0.2, 'end': 1.1}], [{'text': 'قبل', 'start': 0, 'end': float('nan')}],
    [{'text': 'قبل', 'start': 0, 'end': 0.7}, {'text': 'ما', 'start': 0.5, 'end': 0.9}]])
def test_invalid_frozen_timing(words):
    sc = scene()
    sc['final'] = words
    with pytest.raises(ValueError):
        ca.validate_scenes([sc], {'S01'})


def test_duplicate_and_unknown_scenes():
    with pytest.raises(ValueError, match='unique'):
        ca.validate_scenes([scene(), scene()], set())
    with pytest.raises(ValueError, match='unknown frozen'):
        ca.validate_scenes([scene()], {'MISSING'})


def make_wav(path, channels=1, width=2):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(24000)
        w.writeframes(b'\0' * 24000 * channels * width)


@pytest.mark.parametrize(('channels', 'width'), [(2, 2), (1, 1), (1, 3), (2, 4)])
def test_wav_rejects_unsupported_layout_before_slice(tmp_path, channels, width):
    source, output = tmp_path / 'source.wav', tmp_path / 'slice.wav'
    make_wav(source, channels, width)
    with pytest.raises(ValueError, match='mono PCM16'):
        ca._slice_wav(source, output, 0, 0.5)
    assert not output.exists()


def test_pcm16_slice_duration_and_bytes(tmp_path):
    source, output = tmp_path / 'source.wav', tmp_path / 'slice.wav'
    make_wav(source)
    ca._slice_wav(source, output, 0.25, 0.75)
    assert ca.validate_wav(output) == (24000, 0.5)
    with pytest.raises(ValueError, match='bounds'):
        ca._slice_wav(source, output, 0, 2)


def test_frozen_cli_without_asr_model(tmp_path):
    source = tmp_path / 'source.wav'
    make_wav(source)
    scenes = tmp_path / 'scenes.json'
    scenes.write_text(json.dumps([scene()]))
    output = tmp_path / 'src'
    result = subprocess.run([sys.executable, str(Path(ca.__file__)), '--scenes', str(scenes), '--vo', str(source),
        '--out-dir', str(output), '--measurements', str(tmp_path / 'cache' / 'measurement.json'), '--freeze', 'S01'],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'CAPTIONS_S01' in (output / 'captions-s01.js').read_text()
    assert '0.1' in (output / 'captions-s01.js').read_text()


def test_generated_js_quotes_untrusted_strings(tmp_path):
    payload = "x';globalThis.INJECTED=true;//\n\\\""
    sc = {'id': 'S01', 'module': payload, 'start': 0, 'end': 1}
    js = ca.emit_data_js([sc], payload, payload)
    assert json.dumps(payload) in js
    import shutil
    if not shutil.which('node'):
        pytest.skip('node unavailable for JS evaluation')
    path = tmp_path / 'data.mjs'
    path.write_text(js)
    script = f'import {{scenes, ARABIC_FONT}} from {json.dumps(path.as_uri())}; console.log(JSON.stringify([scenes[0].id, ARABIC_FONT.family, ARABIC_FONT.urls[0], !!globalThis.INJECTED]));'
    result = subprocess.run(['node', '--input-type=module', '-e', script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [payload, payload, payload, False]
    with pytest.raises(ValueError, match='scene id'):
        ca.emit_caption_module('S01\nmalicious', scene()['final'])


def test_snap_rejects_out_of_scene_onsets():
    with pytest.raises(ValueError, match='bounds'):
        ca.snap_and_hold([{'text': 'a', 'start': 1.0}], [], 1.0)


def test_freeze_accepts_generated_punctuation_normalization():
    sc = scene()
    sc['words'] = ['قبل؟']
    ca.validate_scenes([sc], {'S01'})


@pytest.mark.parametrize('target', ['src', 'slices', 'measurements'])
def test_caption_cli_rejects_output_symlinks(tmp_path, target):
    source = tmp_path / 'source.wav'
    make_wav(source)
    scenes = tmp_path / 'scenes.json'
    scenes.write_text(json.dumps([scene()]))
    outside = tmp_path / 'outside'
    outside.mkdir()
    protected = outside / 'captions-s01.js'
    protected.write_text('keep')
    output = tmp_path / 'src'
    measurements = tmp_path / 'cache' / 'scene-measurements.json'
    measurements.parent.mkdir()
    if target == 'src':
        output.symlink_to(outside, target_is_directory=True)
    elif target == 'slices':
        (measurements.parent / 'scene-slices').symlink_to(outside, target_is_directory=True)
    else:
        measurements.symlink_to(protected)
    result = subprocess.run([sys.executable, str(Path(ca.__file__)), '--scenes', str(scenes), '--vo', str(source),
        '--out-dir', str(output), '--measurements', str(measurements), '--freeze', 'S01'],
        capture_output=True, text=True)
    assert result.returncode != 0
    assert 'symlink' in result.stderr
    assert protected.read_text() == 'keep'
