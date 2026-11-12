"""B6b EDL: the owner chose EDL first, so this is the delivery format — cuts and timecodes only.

The exporter must refuse what CMX3600 cannot say (stacked channels, text tracks, off-frame ticks)
instead of rounding silently.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import edl_export  # noqa: E402

BASIC = ROOT / "tests" / "fixtures" / "unified_project" / "basic.json"


def basic() -> dict:
    return json.loads(BASIC.read_text(encoding="utf-8"))


def demo() -> dict:
    project = basic()
    project.update({"id": "reel-demo", "name": "Reel demo", "duration": 1_920_000})
    project["assets"] = [
        {"id": "a1", "kind": "video", "uri": "media/shot-a.mp4", "duration": 1_440_000, "sha256": "a" * 64},
        {"id": "a2", "kind": "video", "uri": "media/shot-b.mp4", "duration": 960_000, "sha256": "b" * 64},
        {"id": "a3", "kind": "audio", "uri": "audio/vo.wav", "duration": 1_920_000, "sha256": "c" * 64},
    ]
    project["tracks"] = [
        {"id": "v1", "kind": "video", "enabled": True, "clips": [
            {"id": "c1", "kind": "media", "assetId": "a1", "start": 0, "duration": 720_000,
             "sourceIn": 240_000, "effects": [], "keyframes": []},
            {"id": "c2", "kind": "media", "assetId": "a1", "start": 720_000, "duration": 480_000,
             "sourceIn": 960_000, "effects": [], "keyframes": []},
            {"id": "c3", "kind": "media", "assetId": "a2", "start": 1_200_000, "duration": 720_000,
             "sourceIn": 0, "effects": [], "keyframes": []},
        ]},
        {"id": "aud", "kind": "audio", "enabled": True, "clips": [
            {"id": "m1", "kind": "media", "assetId": "a3", "start": 0, "duration": 1_920_000,
             "sourceIn": 0, "effects": [], "keyframes": []},
        ]},
        {"id": "g1", "kind": "graphics", "enabled": False, "clips": []},
    ]
    return project


# ---------------------------------------------------------------- timecode + reels
@pytest.mark.parametrize(("ticks", "fps", "expected"), [
    (0, 30, "00:00:00:00"),
    (240_000, 30, "00:00:01:00"),
    (1_920_000, 30, "00:00:08:00"),
    (960_000, 60, "00:00:04:00"),
    (960_000, 12, "00:00:04:00"),
    (48_000, 15, "00:00:00:03"),
    (480_000, 15, "00:00:02:00"),
    (240_000 * 3661, 30, "01:01:01:00"),
])
def test_timecode_follows_the_profile(ticks: int, fps: int, expected: str) -> None:
    assert edl_export.timecode(ticks, fps, 240_000 // fps) == expected


@pytest.mark.parametrize(("uri", "expected"), [
    ("media/shot-a.mp4", "SHOT_A"),
    ("media/My Long Clip.mov", "MY_LONG_"),
    ("audio/vo.wav", "VO"),
    ("", "AX"),
])
def test_reels_are_short_tags(uri: str, expected: str) -> None:
    assert edl_export.reel_for(uri) == expected


# ---------------------------------------------------------------- build
def test_the_fixture_becomes_one_event() -> None:
    text, manifest = edl_export.build_edl(basic())
    assert text.startswith("TITLE: Example\nFCM: NON-DROP FRAME\n")
    assert text.count("\n* CLIP") == 1
    assert "00:00:00:00 00:00:02:00 00:00:00:00 00:00:02:00" in text
    assert manifest["totals"] == {"events": 1, "durationTc": "00:00:02:00"}
    assert manifest["fps"] == 30 and manifest["frameTicks"] == 8000
    assert edl_export.validate_manifest(manifest) == []


def test_video_events_come_first_then_audio() -> None:
    text, manifest = edl_export.build_edl(demo())
    channels = [event["channel"] for event in manifest["events"]]
    assert channels == ["V", "V", "V", "A"]
    assert [event["clipId"] for event in manifest["events"]] == ["c1", "c2", "c3", "m1"]


def test_timecodes_match_the_ticks() -> None:
    _, manifest = edl_export.build_edl(demo())
    first = manifest["events"][0]
    assert (first["sourceInTc"], first["sourceOutTc"]) == ("00:00:01:00", "00:00:04:00")
    assert (first["recordInTc"], first["recordOutTc"]) == ("00:00:00:00", "00:00:03:00")
    assert first["reel"] == "SHOT_A" and first["fileName"] == "shot-a.mp4"


def test_a_disabled_track_is_not_exported() -> None:
    text, manifest = edl_export.build_edl(demo())
    assert "graphics" not in text.lower()
    assert len(manifest["events"]) == 4


def test_two_audio_tracks_get_two_channels() -> None:
    project = demo()
    project["tracks"].append({"id": "aud2", "kind": "audio", "enabled": True, "clips": [
        {"id": "m2", "kind": "media", "assetId": "a3", "start": 0, "duration": 1_920_000,
         "sourceIn": 0, "effects": [], "keyframes": []}]})
    _, manifest = edl_export.build_edl(project)
    assert [e["channel"] for e in manifest["events"]][-2:] == ["A", "A2"]


def test_building_twice_is_identical() -> None:
    first_text, first_manifest = edl_export.build_edl(demo())
    second_text, second_manifest = edl_export.build_edl(demo())
    assert first_text == second_text
    assert json.dumps(first_manifest, sort_keys=True) == json.dumps(second_manifest, sort_keys=True)


def test_the_title_is_ascii_and_the_real_name_is_kept() -> None:
    project = demo()
    project["name"] = "ريل ميدو · 8s"
    text, manifest = edl_export.build_edl(project)
    first = text.splitlines()[0]
    assert first.startswith("TITLE: ") and all(ord(ch) < 128 for ch in first)
    assert "* PROJECT NAME: ريل ميدو · 8s" in text
    assert manifest["title"] == first.removeprefix("TITLE: ")


@pytest.mark.parametrize(("edit", "code"), [
    (lambda p: p["tracks"].append({"id": "t1", "kind": "text", "enabled": True, "clips": []}), "E05"),
    (lambda p: p["tracks"][0]["clips"][1].update(sourceIn=720_100), "E04"),
    (lambda p: [t.update(enabled=False) for t in p["tracks"]], "E05"),
    (lambda p: p["profile"]["fps"].update(num=30000, den=1001), "E02"),
    (lambda p: p.update(duration=10), "E01"),
    (lambda p: p["assets"].pop(0), "E01"),
])
def test_refusals_are_code_named(edit, code: str) -> None:
    project = demo()
    edit(project)
    with pytest.raises(edl_export.EdlError) as excinfo:
        edl_export.build_edl(project)
    assert excinfo.value.code == code


def test_the_asset_gate_still_guards_when_validation_is_bypassed(monkeypatch) -> None:
    """E01 catches most of this first; E03 is defence in depth for a project that slipped through."""
    monkeypatch.setattr(edl_export, "validate", lambda project: [])
    project = demo()
    project["tracks"][0]["clips"][1]["assetId"] = "a3"  # audio asset on a video track
    with pytest.raises(edl_export.EdlError) as excinfo:
        edl_export.build_edl(project)
    assert excinfo.value.code == "E03"


def test_a_still_is_held_for_exactly_the_clip_length() -> None:
    project = basic()
    project["assets"] = [{"id": "a1", "kind": "image", "uri": "media/poster.png", "sha256": "d" * 64}]
    text, manifest = edl_export.build_edl(project)
    event = manifest["events"][0]
    assert event["still"] is True
    assert (event["sourceIn"], event["sourceOut"]) == (0, 480_000)
    assert "* STILL" in text
    assert edl_export.validate_manifest(manifest) == []


def test_a_media_clip_is_not_marked_as_a_still() -> None:
    _, manifest = edl_export.build_edl(basic())
    assert manifest["events"][0]["still"] is False


def test_a_stacked_video_track_is_refused() -> None:
    project = demo()
    project["tracks"].append({"id": "v2", "kind": "video", "enabled": True, "clips": [
        {"id": "x1", "kind": "media", "assetId": "a2", "start": 240_000, "duration": 240_000,
         "sourceIn": 0, "effects": [], "keyframes": []}]})
    with pytest.raises(edl_export.EdlError) as excinfo:
        edl_export.build_edl(project)
    assert excinfo.value.code == "E06"


def test_more_than_999_events_are_refused() -> None:
    project = basic()
    project["duration"] = 8_000_000
    project["assets"][0]["duration"] = 8_000_000
    project["tracks"][0]["clips"] = [
        {"id": f"c{i}", "kind": "media", "assetId": "a1", "start": i * 8000, "duration": 8000,
         "sourceIn": 0, "effects": [], "keyframes": []} for i in range(1000)]
    with pytest.raises(edl_export.EdlError) as excinfo:
        edl_export.build_edl(project)
    assert excinfo.value.code == "E07"


# ---------------------------------------------------------------- parse + manifest
def test_the_export_parses_back() -> None:
    text, manifest = edl_export.build_edl(demo())
    events = edl_export.parse_edl(text)
    assert len(events) == len(manifest["events"]) == 4
    assert [int(e["n"]) for e in events] == [1, 2, 3, 4]


@pytest.mark.parametrize("mutate", [
    lambda t: t.replace("FCM: NON-DROP FRAME", "FCM: DROP FRAME"),
    lambda t: t.replace("TITLE: Reel demo", "TITLE Reel demo"),
    lambda t: t.replace("002  ", "005  "),
    lambda t: t.replace("00:00:06:00 00:00:03:00", "00:00:03:00 00:00:03:00"),
])
def test_broken_edl_text_is_refused(mutate) -> None:
    text, _ = edl_export.build_edl(demo())
    with pytest.raises(edl_export.EdlError) as excinfo:
        edl_export.parse_edl(mutate(text))
    assert excinfo.value.code == "E08"


@pytest.mark.parametrize(("edit", "code"), [
    (lambda m: m.update(version=2), "E01"),
    (lambda m: m["totals"].update(events=9), "E09"),
    (lambda m: m["events"][1].update(n=7), "E04"),
    (lambda m: m["events"][0].update(recordOut=m["events"][0]["recordIn"]), "E04"),
    (lambda m: m["events"][0].update(sourceIn=1), "E04"),
])
def test_manifest_drift_is_caught(edit, code: str) -> None:
    _, manifest = edl_export.build_edl(demo())
    broken = copy.deepcopy(manifest)
    edit(broken)
    errors = edl_export.validate_manifest(broken)
    assert any(error.startswith(code) for error in errors), errors


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "edl_export.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=120)


def test_cli_builds_edl_and_sidecar(tmp_path: Path) -> None:
    project = tmp_path / "project.json"
    project.write_text(json.dumps(demo()), encoding="utf-8")
    edl = tmp_path / "out" / "reel.edl"
    result = run("build", str(project), "-o", str(edl))
    assert result.returncode == 0, result.stderr
    assert "4 events" in result.stdout
    assert edl.exists() and (tmp_path / "out" / "reel.edl.json").exists()
    check = run("check", str(tmp_path / "out" / "reel.edl.json"), "--edl", str(edl))
    assert check.returncode == 0, check.stderr
    assert "Valid EDL · 4 events" in check.stdout


def test_cli_refuses_and_writes_nothing(tmp_path: Path) -> None:
    project = demo()
    project["tracks"].append({"id": "t1", "kind": "text", "enabled": True, "clips": []})
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(project), encoding="utf-8")
    edl = tmp_path / "bad.edl"
    result = run("build", str(path), "-o", str(edl))
    assert result.returncode == 1 and "E05" in result.stderr
    assert not edl.exists()


def test_cli_reports_a_missing_file(tmp_path: Path) -> None:
    assert run("check", str(tmp_path / "gone.json")).returncode == 2
    assert run("build", str(tmp_path / "gone.json"), "-o", str(tmp_path / "x.edl")).returncode == 2


def test_cli_catches_an_edl_that_does_not_match_its_manifest(tmp_path: Path) -> None:
    full = tmp_path / "full"
    full.mkdir()
    (full / "project.json").write_text(json.dumps(demo()), encoding="utf-8")
    run("build", str(full / "project.json"), "-o", str(full / "reel.edl"))
    one = tmp_path / "one"
    one.mkdir()
    (one / "project.json").write_text(json.dumps(basic()), encoding="utf-8")
    run("build", str(one / "project.json"), "-o", str(one / "single.edl"))
    result = run("check", str(full / "reel.edl.json"), "--edl", str(one / "single.edl"))
    assert result.returncode == 1
    assert "E09" in result.stderr
