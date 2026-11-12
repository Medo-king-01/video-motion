"""OTIO delivery: cuts, effects and keyframes — with transitions named as absent, never faked."""
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

import otio_export  # noqa: E402


def project() -> dict:
    return {
        "schemaVersion": "1.1", "id": "otio-demo", "name": "OTIO demo",
        "profile": {"width": 1080, "height": 1920, "fps": {"num": 30, "den": 1}, "sampleRate": 48000},
        "timebase": 240_000, "duration": 480_000, "seed": 3,
        "assets": [
            {"id": "a1", "kind": "video", "uri": "media/shot.mp4", "duration": 720_000, "sha256": "a" * 64},
            {"id": "a2", "kind": "audio", "uri": "audio/vo.wav", "duration": 480_000, "sha256": "b" * 64},
        ],
        "tracks": [
            {"id": "v1", "kind": "video", "enabled": True, "clips": [
                {"id": "c1", "kind": "media", "assetId": "a1", "start": 0, "duration": 240_000,
                 "sourceIn": 240_000,
                 "effects": [{"id": "e1", "type": "opacity", "version": 1, "enabled": True,
                              "params": {"value": 8000}}],
                 "keyframes": [{"effectId": "e1", "property": "value",
                                "points": [{"t": 0, "value": 0, "interpolation": "linear"},
                                           {"t": 240_000, "value": 10000, "interpolation": "hold"}]}]},
                {"id": "c2", "kind": "media", "assetId": "a1", "start": 240_000, "duration": 240_000,
                 "sourceIn": 0, "effects": [], "keyframes": []},
            ]},
            {"id": "at", "kind": "audio", "enabled": False, "clips": [
                {"id": "m1", "kind": "media", "assetId": "a2", "start": 0, "duration": 480_000,
                 "sourceIn": 0, "effects": [], "keyframes": []}]},
        ],
    }


# ---------------------------------------------------------------- structure
def test_the_timeline_has_the_otio_shape() -> None:
    payload = otio_export.build(project())
    assert payload["OTIO_SCHEMA"] == "Timeline.1"
    assert payload["tracks"]["OTIO_SCHEMA"] == "Stack.1"
    tracks = payload["tracks"]["children"]
    assert [track["kind"] for track in tracks] == ["Video", "Audio"]
    assert [len(track["children"]) for track in tracks] == [2, 1]
    assert otio_export.validate_timeline(payload) == []


def test_ticks_become_frames_at_the_timeline_rate() -> None:
    payload = otio_export.build(project())
    first = payload["tracks"]["children"][0]["children"][0]
    assert first["source_range"]["start_time"]["value"] == 30.0   # 240000 ticks = 1s
    assert first["source_range"]["duration"]["value"] == 30.0
    assert first["metadata"]["medo"]["start"] == 0
    assert first["media_reference"]["target_url"] == "media/shot.mp4"


def test_effects_and_keyframes_are_carried_not_dropped() -> None:
    payload = otio_export.build(project())
    clip = payload["tracks"]["children"][0]["children"][0]
    assert clip["metadata"]["medo"]["effects"][0]["type"] == "opacity"
    assert len(clip["metadata"]["medo"]["keyframes"][0]["points"]) == 2
    meta = payload["metadata"]["medo"]
    assert meta["effects"] == 1 and meta["keyframes"] == 1


def test_transitions_are_counted_not_claimed() -> None:
    meta = otio_export.build(project())["metadata"]["medo"]
    assert meta["transitions"] == 0 and meta["transitionKinds"] == []


def test_a_disabled_track_is_kept_and_marked() -> None:
    tracks = otio_export.build(project())["tracks"]["children"]
    assert tracks[1]["metadata"]["medo"]["enabled"] is False
    assert tracks[1]["children"][0]["name"] == "m1"


def test_the_project_hash_travels_with_the_file() -> None:
    payload = otio_export.build(project())
    digest = payload["tracks"]["metadata"]["medo"]["sha256"]
    assert len(digest) == 64


def test_the_duration_is_reported_in_frames() -> None:
    meta = otio_export.build(project())["metadata"]["medo"]
    assert meta["durationTicks"] == 480_000 and meta["durationFrames"] == 60.0


def test_building_twice_is_identical() -> None:
    assert json.dumps(otio_export.build(project()), sort_keys=True) == \
           json.dumps(otio_export.build(project()), sort_keys=True)


# ---------------------------------------------------------------- refusals
def test_an_invalid_project_is_refused() -> None:
    broken = project()
    broken["duration"] = 10
    with pytest.raises(otio_export.OtioError) as excinfo:
        otio_export.build(broken)
    assert excinfo.value.code == "O01"


def test_a_non_integer_rate_is_refused() -> None:
    odd = project()
    odd["profile"]["fps"] = {"num": 30000, "den": 1001}
    with pytest.raises(otio_export.OtioError) as excinfo:
        otio_export.build(odd)
    assert excinfo.value.code == "O02"


def test_an_unknown_asset_is_refused(monkeypatch) -> None:
    monkeypatch.setattr(otio_export, "validate", lambda project: [])
    broken = project()
    broken["tracks"][0]["clips"][0]["assetId"] = "ghost"
    with pytest.raises(otio_export.OtioError) as excinfo:
        otio_export.build(broken)
    assert excinfo.value.code == "O03"


def test_reading_beyond_the_asset_is_refused(monkeypatch) -> None:
    monkeypatch.setattr(otio_export, "validate", lambda project: [])
    broken = project()
    broken["tracks"][0]["clips"][0]["duration"] = 700_000
    with pytest.raises(otio_export.OtioError) as excinfo:
        otio_export.build(broken)
    assert excinfo.value.code == "O04"


def test_an_empty_timeline_is_refused() -> None:
    empty = project()
    for track in empty["tracks"]:
        track["clips"] = []
    with pytest.raises(otio_export.OtioError) as excinfo:
        otio_export.build(empty)
    assert excinfo.value.code == "O04"


def test_no_assets_means_no_references(monkeypatch) -> None:
    monkeypatch.setattr(otio_export, "validate", lambda project: [])
    empty = project()
    empty["assets"] = []
    with pytest.raises(otio_export.OtioError) as excinfo:
        otio_export.build(empty)
    assert excinfo.value.code == "O03"


# ---------------------------------------------------------------- check
@pytest.mark.parametrize("mutate", [
    lambda p: p.update(OTIO_SCHEMA="Timeline.2"),
    lambda p: p["tracks"].update(OTIO_SCHEMA="Track.1"),
    lambda p: p["tracks"]["children"][0]["children"][0]["source_range"]["duration"].update(value=0),
    lambda p: p["tracks"]["children"][0]["children"][0]["source_range"]["start_time"].update(rate=25.0),
    lambda p: p["tracks"]["children"][0]["children"][0].pop("media_reference"),
    lambda p: p["tracks"]["children"][0].pop("kind"),
])
def test_a_broken_timeline_is_caught(mutate) -> None:
    payload = copy.deepcopy(otio_export.build(project()))
    mutate(payload)
    assert otio_export.validate_timeline(payload) != []


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "otio_export.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=120)


def test_cli_writes_and_checks(tmp_path: Path) -> None:
    path = tmp_path / "project.json"
    path.write_text(json.dumps(project()), encoding="utf-8")
    out = tmp_path / "out" / "timeline.otio"
    result = run("build", str(path), "-o", str(out))
    assert result.returncode == 0, result.stderr
    assert "3 clips" in result.stdout and "1 effects" in result.stdout
    checked = run("check", str(out))
    assert checked.returncode == 0, checked.stderr
    assert "Valid OTIO · 3 clips" in checked.stdout


def test_cli_refuses_a_broken_project(tmp_path: Path) -> None:
    data = project()
    data["duration"] = 10
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert run("build", str(path), "-o", str(tmp_path / "x.otio")).returncode == 1
    assert not (tmp_path / "x.otio").exists()


def test_cli_reports_a_missing_file(tmp_path: Path) -> None:
    assert run("build", str(tmp_path / "gone.json"), "-o", str(tmp_path / "x.otio")).returncode == 2
    assert run("check", str(tmp_path / "gone.otio")).returncode == 2
