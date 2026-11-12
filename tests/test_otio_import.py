"""OTIO import: exact reconstruction from metadata, and a refusal — never a guessed edit — for anything else."""
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
import otio_import  # noqa: E402
from unified_project_check import validate  # noqa: E402


def project() -> dict:
    return {
        "schemaVersion": "1.1", "id": "round-trip", "name": "Round trip",
        "profile": {"width": 1080, "height": 1920, "fps": {"num": 30, "den": 1}, "sampleRate": 48_000},
        "timebase": 240_000, "duration": 480_000, "seed": 11,
        "assets": [
            {"id": "a1", "kind": "video", "uri": "media/shot.mp4", "duration": 720_000, "sha256": "a" * 64},
            {"id": "a2", "kind": "audio", "uri": "audio/vo.wav", "duration": 480_000, "sha256": "b" * 64},
        ],
        "tracks": [
            {"id": "v1", "kind": "video", "enabled": True, "clips": [
                {"id": "c1", "kind": "media", "assetId": "a1", "start": 0, "duration": 240_000,
                 "sourceIn": 120_000,
                 "effects": [{"id": "e1", "type": "opacity", "version": 1, "enabled": True,
                              "params": {"value": 8_000}}],
                 "keyframes": [{"effectId": "e1", "property": "value",
                                "points": [{"t": 0, "value": 0, "interpolation": "linear"},
                                           {"t": 240_000, "value": 10_000, "interpolation": "hold"}]}]},
                {"id": "c2", "kind": "media", "assetId": "a1", "start": 240_000, "duration": 240_000,
                 "sourceIn": 0, "effects": [], "keyframes": []},
            ]},
            {"id": "at", "kind": "audio", "enabled": False, "clips": [
                {"id": "m1", "kind": "media", "assetId": "a2", "start": 0, "duration": 480_000,
                 "sourceIn": 0, "effects": [], "keyframes": []}]},
        ],
    }


def timeline() -> dict:
    return otio_export.build(project())


# ---------------------------------------------------------------- round trip
def test_a_medo_timeline_comes_back_exactly() -> None:
    back = otio_import.build(timeline())
    assert json.dumps(back, sort_keys=True) == json.dumps(project(), sort_keys=True)
    assert validate(back) == []


def test_effects_keyframes_and_disabled_tracks_survive() -> None:
    back = otio_import.build(timeline())
    clip = back["tracks"][0]["clips"][0]
    assert clip["effects"][0]["params"]["value"] == 8_000
    assert clip["keyframes"][0]["points"][1]["value"] == 10_000
    assert back["tracks"][1]["enabled"] is False
    assert back["assets"][1]["duration"] == 480_000


def test_the_second_export_matches_the_first() -> None:
    first = timeline()
    again = otio_export.build(otio_import.build(first), name=first["name"])
    assert json.dumps(again, sort_keys=True) == json.dumps(first, sort_keys=True)


def test_the_seed_travels_with_the_timeline() -> None:
    assert otio_import.build(timeline())["seed"] == 11


def test_ticks_come_from_metadata_not_from_rounded_frames() -> None:
    payload = timeline()
    payload["tracks"]["children"][0]["children"][0]["metadata"]["medo"]["sourceIn"] = 123_456
    with pytest.raises(otio_import.ImportError_) as excinfo:
        otio_import.build(payload)
    assert excinfo.value.code == "N04" and "disagree" in excinfo.value.message


# ---------------------------------------------------------------- refusals
def test_a_foreign_timeline_is_refused_not_guessed() -> None:
    payload = timeline()
    payload["metadata"] = {}
    with pytest.raises(otio_import.ImportError_) as excinfo:
        otio_import.build(payload)
    assert excinfo.value.code == "N02" and "not a Medo timeline" in excinfo.value.message


def test_an_unknown_version_is_refused() -> None:
    payload = timeline()
    payload["metadata"]["medo"]["version"] = 7
    with pytest.raises(otio_import.ImportError_) as excinfo:
        otio_import.build(payload)
    assert excinfo.value.code == "N02" and "not supported" in excinfo.value.message


def test_a_malformed_timeline_is_refused() -> None:
    payload = timeline()
    payload["tracks"]["children"][0]["children"][0]["source_range"]["duration"]["value"] = -1
    with pytest.raises(otio_import.ImportError_) as excinfo:
        otio_import.build(payload)
    assert excinfo.value.code == "N01"


def test_a_frame_value_that_is_not_a_whole_tick_is_refused() -> None:
    payload = timeline()
    clip = payload["tracks"]["children"][0]["children"][0]
    clip["source_range"]["duration"]["value"] = 1.0001
    clip["metadata"]["medo"]["duration"] = 240_002
    with pytest.raises(otio_import.ImportError_) as excinfo:
        otio_import.build(payload)
    assert excinfo.value.code == "N03" and "whole tick" in excinfo.value.message


def test_a_missing_seed_is_refused() -> None:
    payload = timeline()
    payload["metadata"]["medo"].pop("seed")
    with pytest.raises(otio_import.ImportError_) as excinfo:
        otio_import.build(payload)
    assert excinfo.value.code == "N03" and "seed" in excinfo.value.message


def test_a_duplicate_clip_id_is_refused() -> None:
    payload = timeline()
    track = payload["tracks"]["children"][0]
    track["children"][1] = copy.deepcopy(track["children"][0])
    with pytest.raises(otio_import.ImportError_) as excinfo:
        otio_import.build(payload)
    assert excinfo.value.code == "N04" and "duplicate clip id" in excinfo.value.message


def test_a_media_reference_without_a_hash_is_refused() -> None:
    payload = timeline()
    payload["tracks"]["children"][0]["children"][0]["media_reference"]["metadata"]["medo"]["sha256"] = "x"
    with pytest.raises(otio_import.ImportError_) as excinfo:
        otio_import.build(payload)
    assert excinfo.value.code == "N04" and "sha256" in excinfo.value.message


def test_a_track_kind_disagreeing_with_otio_is_refused() -> None:
    payload = timeline()
    payload["tracks"]["children"][0]["metadata"]["medo"]["trackKind"] = "audio"
    with pytest.raises(otio_import.ImportError_) as excinfo:
        otio_import.build(payload)
    assert excinfo.value.code == "N04" and "disagrees" in excinfo.value.message


def test_a_missing_project_profile_is_refused() -> None:
    payload = timeline()
    payload["metadata"]["medo"].pop("profile")
    with pytest.raises(otio_import.ImportError_) as excinfo:
        otio_import.build(payload)
    assert excinfo.value.code == "N03" and "profile" in excinfo.value.message


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "otio_import.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=120)


def test_cli_writes_a_project_that_validates(tmp_path: Path) -> None:
    path = tmp_path / "timeline.otio"
    path.write_text(json.dumps(timeline()), encoding="utf-8")
    out = tmp_path / "project.json"
    result = run("build", str(path), "-o", str(out))
    assert result.returncode == 0, result.stderr
    assert "2 tracks" in result.stdout
    checked = run("check", str(out))
    assert checked.returncode == 0, checked.stderr
    assert "Valid project · 3 clips" in checked.stdout


def test_cli_reports_a_refusal(tmp_path: Path) -> None:
    payload = timeline()
    payload["metadata"] = {}
    path = tmp_path / "foreign.otio"
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = run("build", str(path), "-o", str(tmp_path / "project.json"))
    assert result.returncode == 1 and "N02" in result.stderr


def test_cli_reports_a_missing_timeline(tmp_path: Path) -> None:
    assert run("build", str(tmp_path / "gone.otio"), "-o", str(tmp_path / "p.json")).returncode == 2
