"""Schema 1.3: text blocks, clip speed and stream choice are represented — and checked.

Every rule here exists because the alternative is silent loss: a text clip that renders nowhere,
a speed that replays the wrong frames, a stream index that picks the wrong audio track.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from unified_project_check import validate  # noqa: E402

FIXTURE = json.loads((ROOT / "tests/fixtures/unified_project/basic.json").read_text(encoding="utf-8"))


def project() -> dict:
    data = copy.deepcopy(FIXTURE)
    data["schemaVersion"] = "1.3"
    data["assets"][0].update(kind="video", duration=960_000)
    data["texts"] = [{"id": "cap", "value": "وجه واحد", "font": "Cairo", "size": 64,
                      "color": "#f3f2f1", "align": "center", "direction": "rtl"}]
    return data


def with_text_track(data: dict, **clip) -> dict:
    entry = {"id": "x1", "kind": "media", "textId": "cap", "start": 0, "duration": 240_000,
             "sourceIn": 0, "effects": [], "keyframes": []}
    entry.update(clip)
    data["tracks"].append({"id": "t1", "kind": "text", "enabled": True, "clips": [entry]})
    return data


def test_a_text_clip_on_a_text_track_is_valid() -> None:
    data = with_text_track(project())
    assert validate(data) == []


def test_text_on_a_video_track_is_refused() -> None:
    data = project()
    data["tracks"][0]["clips"][0].update(textId="cap")
    data["tracks"][0]["clips"][0].pop("assetId")
    errors = validate(data)
    assert any(error.startswith("U10") and "text track" in error for error in errors), errors


def test_an_unknown_text_id_is_refused() -> None:
    data = with_text_track(project(), textId="missing")
    assert any("unknown text" in error for error in validate(data))


def test_a_text_clip_may_not_also_point_at_an_asset() -> None:
    data = with_text_track(project(), assetId="a1")
    assert any(error.startswith("U01") for error in validate(data))


def test_text_direction_must_match_the_script() -> None:
    data = with_text_track(project())
    data["texts"][0]["direction"] = "ltr"
    assert any("ltr text with Arabic" in error for error in validate(data))
    data = with_text_track(project())
    data["texts"][0].update(value="One face", direction="rtl")
    assert any("rtl text with no Arabic" in error for error in validate(data))


def test_text_has_no_source_range() -> None:
    data = with_text_track(project(), sourceIn=8_000)
    assert any("sourceIn" in error for error in validate(data))


def test_a_text_clip_carries_opacity_but_not_gain() -> None:
    data = with_text_track(project())
    data["tracks"][1]["clips"][0]["effects"] = [
        {"id": "o", "type": "opacity", "version": 1, "enabled": True, "params": {"value": 9000}}]
    assert validate(data) == []
    data["tracks"][1]["clips"][0]["effects"][0]["type"] = "gain"
    assert any(error.startswith("U06") for error in validate(data))


def test_speed_must_be_a_reduced_positive_fraction() -> None:
    data = project()
    data["tracks"][0]["clips"][0]["speed"] = {"num": 2, "den": 2}
    assert any(error.startswith("U08") for error in validate(data))


def test_speed_widens_the_source_range_it_consumes() -> None:
    """A 2× clip eats twice the media, so the same duration can exceed the asset."""
    data = project()
    data["assets"][0]["duration"] = 480_000
    data["tracks"][0]["clips"][0]["duration"] = 400_000
    assert validate(data) == []
    data["tracks"][0]["clips"][0]["speed"] = {"num": 2, "den": 1}
    assert any("source range" in error for error in validate(data))


def test_streams_are_declared_on_video_assets_only() -> None:
    data = project()
    data["assets"][0]["streams"] = {"video": 0, "audio": 1}
    assert validate(data) == []
    data["assets"][0].update(kind="audio")
    assert any(error.startswith("U09") for error in validate(data))


def test_an_unknown_stream_key_is_refused() -> None:
    """Structural strictness comes first: the schema refuses the field before semantics run."""
    data = project()
    data["assets"][0]["streams"] = {"subtitle": 0}
    errors = validate(data)
    assert any("$.assets[0].streams.subtitle" in error for error in errors), errors


def test_a_project_without_the_new_fields_is_still_valid() -> None:
    """1.3 fields are optional: an old project does not need a rewrite to keep working."""
    data = copy.deepcopy(FIXTURE)
    assert validate(data) == []
    assert "texts" not in data
