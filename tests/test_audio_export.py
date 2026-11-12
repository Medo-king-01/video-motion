"""Audio delivery: the project's audio tracks mixed to one PCM16 WAV, with a re-checkable sidecar."""
from __future__ import annotations

import hashlib
import json
import math
import struct
import subprocess
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import audio_export  # noqa: E402


def tone(path: Path, *, seconds: float = 1.0, rate: int = 24_000, amplitude: int = 12_000) -> bytes:
    frames = int(seconds * rate)
    payload = b"".join(struct.pack("<h", int(amplitude * math.sin(2 * math.pi * 440 * i / rate)))
                       for i in range(frames))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(payload)
    return payload


def project(tmp_path: Path, *, duration: int = 480_000, clips: list[dict] | None = None) -> dict:
    payload = tone(tmp_path / "vo.wav")
    return {
        "schemaVersion": "1.1", "id": "audio", "name": "Audio demo",
        "profile": {"width": 360, "height": 640, "fps": {"num": 30, "den": 1}, "sampleRate": 48_000},
        "timebase": 240_000, "duration": duration, "seed": 5,
        "assets": [{"id": "a1", "kind": "audio", "uri": "vo.wav", "duration": 240_000,
                    "sha256": hashlib.sha256(payload).hexdigest()}],
        "tracks": [{"id": "at", "kind": "audio", "enabled": True, "clips": clips or [
            {"id": "m1", "kind": "media", "assetId": "a1", "start": 0, "duration": 240_000,
             "sourceIn": 0, "effects": [], "keyframes": []},
        ]}],
    }


def peaks(pcm: bytes) -> tuple[int, int]:
    values = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    half = len(values) // 2
    return max(abs(v) for v in values[:half]), max(abs(v) for v in values[half:])


# ---------------------------------------------------------------- build
def test_a_quiet_track_becomes_a_wav_that_can_be_read_back(tmp_path: Path) -> None:
    pcm, manifest = audio_export.build(project(tmp_path), tmp_path)
    audio_export.write_wav(tmp_path / "mix.wav", pcm, manifest["sampleRate"])
    with wave.open(str(tmp_path / "mix.wav")) as handle:
        assert handle.getframerate() == 48_000 and handle.getnchannels() == 1
        assert handle.getnframes() == 96_000
        assert handle.readframes(handle.getnframes()) == pcm
    assert manifest["totals"]["seconds"] == 2.0


def test_the_gain_effect_scales_the_second_clip(tmp_path: Path) -> None:
    clips = [
        {"id": "m1", "kind": "media", "assetId": "a1", "start": 0, "duration": 240_000,
         "sourceIn": 0, "effects": [], "keyframes": []},
        {"id": "m2", "kind": "media", "assetId": "a1", "start": 240_000, "duration": 240_000,
         "sourceIn": 0, "effects": [{"id": "g", "type": "gain", "version": 1, "enabled": True,
                                     "params": {"value": 5_000}}], "keyframes": []},
    ]
    pcm, manifest = audio_export.build(project(tmp_path, clips=clips), tmp_path)
    loud, quiet = peaks(pcm)
    assert quiet == pytest.approx(loud / 2, abs=2)
    assert [clip["gain"] for clip in manifest["clips"]] == [1.0, 0.5]


def test_source_in_trims_the_head_and_start_moves_the_clip(tmp_path: Path) -> None:
    clips = [{"id": "m1", "kind": "media", "assetId": "a1", "start": 240_000, "duration": 120_000,
              "sourceIn": 120_000, "effects": [], "keyframes": []}]
    pcm, manifest = audio_export.build(project(tmp_path, duration=360_000, clips=clips), tmp_path)
    first_half = struct.unpack(f"<{len(pcm) // 4}h", pcm[: len(pcm) // 2])
    assert set(first_half) == {0}  # the clip starts at 1 s, so the first second is silence
    assert any(value != 0 for value in struct.unpack(f"<{len(pcm) // 4}h", pcm[len(pcm) // 2:]))


def test_resampling_follows_the_requested_rate(tmp_path: Path) -> None:
    pcm, manifest = audio_export.build(project(tmp_path), tmp_path, sample_rate=24_000)
    assert manifest["sampleRate"] == 24_000
    assert manifest["samples"] == 48_000 and len(pcm) == 96_000


def test_the_mix_is_deterministic(tmp_path: Path) -> None:
    data = project(tmp_path)
    first = audio_export.build(data, tmp_path)
    second = audio_export.build(data, tmp_path)
    assert first[0] == second[0]
    assert json.dumps(first[1], sort_keys=True) == json.dumps(second[1], sort_keys=True)


def test_an_invalid_project_is_refused(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["duration"] = 10
    with pytest.raises(audio_export.AudioError) as excinfo:
        audio_export.build(data, tmp_path)
    assert excinfo.value.code == "A01"


def test_a_project_without_an_enabled_audio_track_is_refused(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["tracks"][0]["enabled"] = False
    with pytest.raises(audio_export.AudioError) as excinfo:
        audio_export.build(data, tmp_path)
    assert excinfo.value.code == "A02" and "no enabled audio track" in excinfo.value.message


def test_missing_media_is_named(tmp_path: Path) -> None:
    data = project(tmp_path)
    (tmp_path / "vo.wav").unlink()
    with pytest.raises(audio_export.AudioError) as excinfo:
        audio_export.build(data, tmp_path)
    assert excinfo.value.code == "A03" and "vo.wav" in excinfo.value.message


def test_a_clip_past_the_end_is_refused(tmp_path: Path) -> None:
    # The unified checker rejects a clip that outruns the project before the mixer ever sees it; A04 stays
    # as the mixer's own guard for a project that reached it another way.
    clips = [{"id": "m1", "kind": "media", "assetId": "a1", "start": 240_000, "duration": 480_000,
              "sourceIn": 0, "effects": [], "keyframes": []}]
    with pytest.raises(audio_export.AudioError) as excinfo:
        audio_export.build(project(tmp_path, duration=360_000, clips=clips), tmp_path)
    assert excinfo.value.code == "A01" and "exceeds project duration" in excinfo.value.message


def test_clipping_is_reported_not_hidden(tmp_path: Path) -> None:
    clips = [{"id": "m1", "kind": "media", "assetId": "a1", "start": 0, "duration": 240_000,
              "sourceIn": 0, "effects": [], "keyframes": []}]
    data = project(tmp_path, clips=clips)
    data["tracks"].append({"id": "at2", "kind": "audio", "enabled": True, "clips": [
        {"id": "m2", "kind": "media", "assetId": "a1", "start": 0, "duration": 240_000,
         "sourceIn": 0, "effects": [{"id": "g", "type": "gain", "version": 1, "enabled": True,
                                     "params": {"value": 20_000}}], "keyframes": []}]})
    pcm, manifest = audio_export.build(data, tmp_path)
    assert manifest["totals"]["peak"] > 1.0 and manifest["totals"]["clipped"] is True
    assert max(abs(v) for v in struct.unpack(f"<{len(pcm) // 2}h", pcm)) >= 32_767


# ---------------------------------------------------------------- crossfades
def crossfade_project(tmp_path: Path) -> dict:
    rate = 48_000
    path = tmp_path / "bed.wav"
    frames = 4 * rate
    payload = b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 330 * i / rate)))
                       for i in range(frames))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(payload)
    return {
        "schemaVersion": "1.2", "id": "fade", "name": "Audio fade",
        "profile": {"width": 360, "height": 640, "fps": {"num": 30, "den": 1}, "sampleRate": rate},
        "timebase": 240_000, "duration": 960_000, "seed": 0,
        "assets": [{"id": "a1", "kind": "audio", "uri": "bed.wav", "duration": 960_000,
                    "sha256": hashlib.sha256(payload).hexdigest()}],
        "tracks": [{"id": "at", "kind": "audio", "enabled": True, "clips": [
            {"id": "m1", "kind": "media", "assetId": "a1", "start": 0, "duration": 480_000,
             "sourceIn": 0, "effects": [], "keyframes": []},
            {"id": "m2", "kind": "media", "assetId": "a1", "start": 480_000, "duration": 480_000,
             "sourceIn": 480_000, "effects": [], "keyframes": []}],
            "transitions": [{"id": "t1", "kind": "crossfade", "fromClipId": "m1",
                             "toClipId": "m2", "duration": 24_000}]}],
    }


def test_a_crossfade_ramps_one_clip_down_as_the_other_rises(tmp_path: Path) -> None:
    data = crossfade_project(tmp_path)
    data["tracks"][0]["clips"][1]["effects"] = [{"id": "g", "type": "gain", "version": 1, "enabled": True,
                                                 "params": {"value": 5_000}}]
    pcm, manifest = audio_export.build(data, tmp_path)
    values = struct.unpack(f"<{len(pcm) // 2}h", pcm)

    def peak(start: int, end: int) -> int:
        return max(abs(value) for value in values[start:end])

    before, opening, middle, closing, after = (peak(80_000, 93_000), peak(93_600, 94_000),
                                               peak(95_800, 96_200), peak(98_000, 98_400),
                                               peak(99_000, 120_000))
    assert before > opening > middle > closing > after
    assert middle == pytest.approx(6_750, rel=0.08)  # half of 9000 plus half of 4500
    assert manifest["clips"][0]["fade"] == {"start": 468_000, "end": 492_000, "rising": False}
    assert manifest["clips"][1]["fade"]["rising"] is True


def test_a_crossfade_without_handles_is_refused(tmp_path: Path) -> None:
    data = crossfade_project(tmp_path)
    data["tracks"][0]["clips"][1]["sourceIn"] = 0
    with pytest.raises(audio_export.AudioError) as excinfo:
        audio_export.build(data, tmp_path)
    assert excinfo.value.code == "A06" and "head handle" in excinfo.value.message


def test_a_crossfade_keeps_the_level_when_both_sides_match(tmp_path: Path) -> None:
    pcm, _ = audio_export.build(crossfade_project(tmp_path), tmp_path)
    values = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    inside = max(abs(value) for value in values[93_600:98_400])
    outside = max(abs(value) for value in values[60_000:80_000])
    assert inside == pytest.approx(outside, rel=0.01)


# ---------------------------------------------------------------- manifest
def test_an_edited_wav_is_caught(tmp_path: Path) -> None:
    pcm, manifest = audio_export.build(project(tmp_path), tmp_path)
    out = tmp_path / "mix.wav"
    audio_export.write_wav(out, pcm, manifest["sampleRate"])
    assert audio_export.verify(manifest, out) == []
    audio_export.write_wav(out, bytes(len(pcm)), manifest["sampleRate"])
    assert any("no longer match" in error for error in audio_export.verify(manifest, out))


@pytest.mark.parametrize("edit", [
    lambda m: m.update(sampleRate=44_100),
    lambda m: m.update(samples=1),
    lambda m: m["pcm"].update(bytes=1),
    lambda m: m["clips"][0].update(start=-1),
    lambda m: m.update(version=9),
])
def test_a_drifted_manifest_is_caught(tmp_path: Path, edit) -> None:
    _, manifest = audio_export.build(project(tmp_path), tmp_path)
    edit(manifest)
    assert audio_export.validate_manifest(manifest) != []


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "audio_export.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=180)


def test_cli_builds_and_checks(tmp_path: Path) -> None:
    path = tmp_path / "project.json"
    path.write_text(json.dumps(project(tmp_path)), encoding="utf-8")
    result = run("build", str(path), "-o", str(tmp_path / "mix.wav"))
    assert result.returncode == 0, result.stderr
    assert "48_000" not in result.stdout and "48000 Hz" in result.stdout
    checked = run("check", str(tmp_path / "mix.wav.json"))
    assert checked.returncode == 0, checked.stderr
    assert "Valid mix · 2.00s" in checked.stdout


def test_cli_refuses_a_project_without_audio(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["tracks"] = []
    path = tmp_path / "silent.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert run("build", str(path), "-o", str(tmp_path / "mix.wav")).returncode == 1


def test_cli_reports_a_missing_project(tmp_path: Path) -> None:
    assert run("build", str(tmp_path / "gone.json"), "-o", str(tmp_path / "mix.wav")).returncode == 2
