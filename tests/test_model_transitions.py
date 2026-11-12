"""Crossfades in the unified project model: schema gate, checker rules, renderer blend, OTIO, EDL refusal.

(The transition *catalogue* — fourteen looks shared by engines P and K — is `test_transitions.py`.)
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import edl_export  # noqa: E402
import otio_export  # noqa: E402
import otio_import  # noqa: E402
import unified_project_check  # noqa: E402
import unified_reference_preview  # noqa: E402

DARK = (10, 20, 30)
LIGHT = (200, 120, 60)


def ppm(color: tuple[int, int, int], size: int = 16) -> bytes:
    return f"P6\n{size} {size}\n255\n".encode("ascii") + bytes(color) * (size * size)


def project(tmp_path: Path, *, transition: dict | None = None, length: int = 16_000) -> dict:
    first, second = ppm(DARK), ppm(LIGHT)
    (tmp_path / "a.ppm").write_bytes(first)
    (tmp_path / "b.ppm").write_bytes(second)
    track = {
        "id": "v1", "kind": "video", "enabled": True,
        "clips": [
            {"id": "c1", "kind": "media", "assetId": "a1", "start": 0, "duration": 32_000,
             "sourceIn": 0, "effects": [], "keyframes": []},
            {"id": "c2", "kind": "media", "assetId": "a2", "start": 32_000, "duration": 32_000,
             "sourceIn": 0, "effects": [], "keyframes": []},
        ],
    }
    if transition is not False:
        track["transitions"] = [transition or {"id": "t1", "kind": "crossfade", "fromClipId": "c1",
                                               "toClipId": "c2", "duration": length}]
    return {
        "schemaVersion": "1.2", "id": "fade", "name": "Fade demo",
        "profile": {"width": 16, "height": 16, "fps": {"num": 30, "den": 1}, "sampleRate": 48_000},
        "timebase": 240_000, "duration": 64_000, "seed": 4,
        "assets": [
            {"id": "a1", "kind": "image", "uri": "a.ppm", "sha256": hashlib.sha256(first).hexdigest()},
            {"id": "a2", "kind": "image", "uri": "b.ppm", "sha256": hashlib.sha256(second).hexdigest()},
        ],
        "tracks": [track],
    }


# ---------------------------------------------------------------- checker
def test_a_crossfade_between_adjacent_clips_is_valid(tmp_path: Path) -> None:
    assert unified_project_check.validate(project(tmp_path)) == []


def test_transitions_need_the_new_schema_version(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["schemaVersion"] = "1.1"
    errors = unified_project_check.validate(data)
    assert any("transitions" in error for error in errors)


@pytest.mark.parametrize(("edit", "code"), [
    (lambda t: t.update(duration=8_001), "U07"),
    (lambda t: t.update(toClipId="c1"), "U07"),
    (lambda t: t.update(fromClipId="missing"), "U07"),
    (lambda t: t.update(kind="wipe"), "U01"),
    (lambda t: t.update(duration=0), "U01"),
])
def test_a_broken_transition_is_caught(tmp_path: Path, edit, code: str) -> None:
    data = project(tmp_path)
    edit(data["tracks"][0]["transitions"][0])
    errors = unified_project_check.validate(data)
    assert errors and all(error.startswith(code) for error in errors)


def test_a_transition_needs_a_cut_to_sit_on(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["tracks"][0]["clips"][1]["start"] = 40_000  # a gap, not a cut
    assert any("adjacent" in error for error in unified_project_check.validate(data))


def test_two_transitions_may_not_overlap(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["tracks"][0]["clips"].append({"id": "c3", "kind": "media", "assetId": "a1", "start": 64_000,
                                       "duration": 32_000, "sourceIn": 0, "effects": [], "keyframes": []})
    data["duration"] = 96_000
    data["tracks"][0]["transitions"].append({"id": "t2", "kind": "crossfade", "fromClipId": "c2",
                                             "toClipId": "c3", "duration": 8_000})
    data["tracks"][0]["clips"][1]["duration"] = 32_000
    assert unified_project_check.validate(data) == []  # windows touch at most: 28000-36000 and 60000-68000

    data["tracks"][0]["transitions"][0]["duration"] = 40_000  # window 12000..52000
    data["tracks"][0]["transitions"][1]["duration"] = 40_000  # window 44000..84000
    assert any("overlaps another transition" in error for error in unified_project_check.validate(data))


def test_a_crossfade_on_an_audio_track_is_valid(tmp_path: Path) -> None:
    import math  # noqa: PLC0415
    import struct  # noqa: PLC0415
    import wave  # noqa: PLC0415

    bed = tmp_path / "bed.wav"
    with wave.open(str(bed), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(48_000)
        handle.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(i / 20))) for i in range(96_000)))
    payload = bed.read_bytes()
    data = project(tmp_path)
    data["assets"] = [{"id": "a1", "kind": "audio", "uri": "bed.wav", "duration": 960_000,
                       "sha256": hashlib.sha256(payload).hexdigest()}]
    data["tracks"][0]["kind"] = "audio"
    for clip in data["tracks"][0]["clips"]:
        clip["assetId"] = "a1"
        clip["effects"] = []
    assert unified_project_check.validate(data) == []


# ---------------------------------------------------------------- renderer
def test_the_middle_of_the_crossfade_is_a_half_mix(tmp_path: Path) -> None:
    data = project(tmp_path)
    frame = unified_reference_preview.render_frame(data, tmp_path, 4)  # tick 32000 = the cut
    pixels = frame["pixels"]
    out = tuple(pixels[:3])
    assert out == tuple((light + dark + 1) // 2 for light, dark in zip(LIGHT, DARK))
    assert set(pixels[3::4]) == {255}


def test_the_frames_either_side_are_untouched(tmp_path: Path) -> None:
    data = project(tmp_path)
    before = unified_reference_preview.render_frame(data, tmp_path, 3)["pixels"]
    after = unified_reference_preview.render_frame(data, tmp_path, 5)["pixels"]
    assert before[:3] == bytes(DARK) and after[:3] == bytes(LIGHT)


def test_a_wider_transition_blends_more_frames(tmp_path: Path) -> None:
    data = project(tmp_path, length=16_000)
    assert unified_project_check.validate(data) == []
    seen = [unified_reference_preview.render_frame(data, tmp_path, index)["pixels"][:3]
            for index in range(8)]
    assert len(set(seen)) >= 3  # dark, one or two mixes, light
    channels = [value[0] for value in seen]
    assert channels == sorted(channels)


def test_the_preview_still_refuses_effects_next_to_a_transition(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["tracks"][0]["clips"][0]["effects"] = [{"id": "e1", "type": "opacity", "version": 1,
                                                "enabled": True, "params": {"value": 5_000}}]
    with pytest.raises(unified_reference_preview.PreviewError) as excinfo:
        unified_reference_preview.render_frame(data, tmp_path, 0)
    assert excinfo.value.code == "V02"


# ---------------------------------------------------------------- OTIO
def test_a_crossfade_becomes_a_transition_between_the_two_clips(tmp_path: Path) -> None:
    payload = otio_export.build(project(tmp_path))
    children = payload["tracks"]["children"][0]["children"]
    assert [child["OTIO_SCHEMA"] for child in children] == ["Clip.1", "Transition.1", "Clip.1"]
    transition = children[1]
    assert transition["transition_type"] == "SMPTE_Dissolve"
    assert transition["in_offset"]["value"] == 1.0 and transition["out_offset"]["value"] == 1.0
    assert transition["metadata"]["medo"]["duration"] == 16_000
    assert otio_export.validate_timeline(payload) == []
    assert payload["metadata"]["medo"]["transitions"] == 1
    assert payload["metadata"]["medo"]["transitionKinds"] == ["crossfade"]


def test_the_otio_round_trip_keeps_the_crossfade(tmp_path: Path) -> None:
    data = project(tmp_path)
    payload = otio_export.build(data)
    back = otio_import.build(payload)
    assert back["tracks"][0]["transitions"] == data["tracks"][0]["transitions"]
    assert back["schemaVersion"] == "1.2"
    assert json.dumps(otio_export.build(back, name=payload["name"]), sort_keys=True) == \
        json.dumps(payload, sort_keys=True)


@pytest.mark.parametrize("edit", [
    lambda c: c.update(in_offset={"OTIO_SCHEMA": "RationalTime.1", "rate": 30.0, "value": 0.0}),
    lambda c: c.update(transition_type="SMPTE_Wipe"),
    lambda c: c["metadata"].pop("medo"),
    lambda c: c.update(out_offset={"OTIO_SCHEMA": "RationalTime.1", "rate": 30.0, "value": 2.0}),
])
def test_a_damaged_transition_is_refused_on_import(tmp_path: Path, edit) -> None:
    payload = otio_export.build(project(tmp_path))
    transition = payload["tracks"]["children"][0]["children"][1]
    edit(transition)
    with pytest.raises(otio_import.ImportError_) as excinfo:
        otio_import.build(payload)
    assert excinfo.value.code in {"N01", "N04", "N05"}


def test_a_transition_naming_a_missing_clip_is_refused(tmp_path: Path) -> None:
    payload = otio_export.build(project(tmp_path))
    transition = payload["tracks"]["children"][0]["children"][1]
    transition["metadata"]["medo"]["toClipId"] = "ghost"
    with pytest.raises(otio_import.ImportError_) as excinfo:
        otio_import.build(payload)
    assert excinfo.value.code == "N05" and "not on track" in excinfo.value.message


def audio_project(tmp_path: Path) -> dict:
    import math  # noqa: PLC0415
    import struct  # noqa: PLC0415
    import wave  # noqa: PLC0415

    bed = tmp_path / "bed.wav"
    with wave.open(str(bed), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(48_000)
        handle.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(i / 20))) for i in range(192_000)))
    payload = bed.read_bytes()
    return {
        "schemaVersion": "1.2", "id": "audio-fade", "name": "Audio fade",
        "profile": {"width": 360, "height": 640, "fps": {"num": 30, "den": 1}, "sampleRate": 48_000},
        "timebase": 240_000, "duration": 960_000, "seed": 0,
        "assets": [{"id": "a1", "kind": "audio", "uri": "bed.wav", "duration": 1_920_000,
                    "sha256": hashlib.sha256(payload).hexdigest()}],
        "tracks": [{"id": "at", "kind": "audio", "enabled": True, "clips": [
            {"id": "m1", "kind": "media", "assetId": "a1", "start": 0, "duration": 480_000,
             "sourceIn": 0, "effects": [], "keyframes": []},
            {"id": "m2", "kind": "media", "assetId": "a1", "start": 480_000, "duration": 480_000,
             "sourceIn": 480_000, "effects": [], "keyframes": []}],
            "transitions": [{"id": "t1", "kind": "crossfade", "fromClipId": "m1",
                             "toClipId": "m2", "duration": 16_000}]}],
    }


# ---------------------------------------------------------------- EDL
def test_a_crossfade_becomes_a_centred_cmx_dissolve(tmp_path: Path) -> None:
    text, manifest = edl_export.build_edl(project(tmp_path))
    lines = [line for line in text.splitlines() if line[:3].isdigit()]
    assert "C " in lines[0] and "D     2" in lines[1]
    first, second = manifest["events"]
    # the outgoing event is widened by half the dissolve at its tail, the incoming one at its head
    assert (first["recordOut"], second["recordIn"]) == (40_000, 24_000)
    assert second["dissolve"] == 2
    assert edl_export.validate_manifest(manifest) == []


def test_the_edl_round_trip_restores_the_project(tmp_path: Path) -> None:
    import edl_import  # noqa: PLC0415

    text, manifest = edl_export.build_edl(project(tmp_path))
    path = tmp_path / "fade.edl"
    path.write_text(text, encoding="utf-8")
    assets = tmp_path / "media"
    assets.mkdir()
    for name in ("a.ppm", "b.ppm"):
        (assets / name).write_bytes((tmp_path / name).read_bytes())
    back = edl_import.build_project(path, media=assets, fps=30, profile_id="reel-30")
    assert [(clip["start"], clip["duration"]) for clip in back["tracks"][0]["clips"]] == \
        [(0, 32_000), (32_000, 32_000)]
    assert back["tracks"][0]["transitions"] == project(tmp_path)["tracks"][0]["transitions"]
    assert back["tracks"][0]["transitions"][0]["duration"] == 16_000
    assert back["schemaVersion"] == "1.2"
    again, _ = edl_export.build_edl(back)
    strip = lambda payload: [line for line in payload.splitlines() if line[:3].isdigit()]  # noqa: E731
    assert strip(again) == strip(text)


def test_a_dissolve_without_media_handles_is_refused(tmp_path: Path) -> None:
    data = project(tmp_path)
    for asset in data["assets"]:
        asset.update(kind="video", uri=f"{asset['id']}.mp4", duration=32_000)
    data["assets"][0]["duration"] = 32_000  # exactly the clip length: no tail to give
    with pytest.raises(edl_export.EdlError) as excinfo:
        edl_export.build_edl(data)
    assert excinfo.value.code == "E10" and "handle" in excinfo.value.message


def test_a_dissolve_that_does_not_match_the_overlap_is_refused(tmp_path: Path) -> None:
    import edl_import  # noqa: PLC0415

    text, _ = edl_export.build_edl(project(tmp_path))
    broken = text.replace("D     2", "D     4")  # the events still overlap by two frames
    path = tmp_path / "broken.edl"
    path.write_text(broken, encoding="utf-8")
    assets = tmp_path / "media"
    assets.mkdir()
    for name in ("a.ppm", "b.ppm"):
        (assets / name).write_bytes((tmp_path / name).read_bytes())
    with pytest.raises(edl_import.ImportError_) as excinfo:
        edl_import.build_project(path, media=assets, fps=30, profile_id="reel-30")
    assert excinfo.value.code == "I06" and "overlap" in excinfo.value.message


# ---------------------------------------------------------------- CLI
def test_cli_round_trips_a_timeline_with_a_crossfade(tmp_path: Path) -> None:
    payload = otio_export.build(project(tmp_path))
    timeline = tmp_path / "fade.otio"
    timeline.write_text(json.dumps(payload), encoding="utf-8")
    result = subprocess.run([sys.executable, str(TOOLS / "otio_import.py"), "roundtrip", str(timeline)],
                            cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert "Round trip · 2 clips · 1 tracks" in result.stdout
