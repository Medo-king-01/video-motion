"""The editing verbs behind the page: pure project in, pure project out, or a real refusal.

`tools/editor_ops.py` exists so that the browser never invents an edit the checker would reject.
Every verb returns a *new* project, leaves the argument untouched, and raises `ValueError` carrying
the checker's own message — which is what the page shows to the user.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import editor_ops as ops  # noqa: E402
import unified_project_check  # noqa: E402
import unified_project_migrate as migrate  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/unified_project/basic.json"


def project() -> dict:
    """The fixture is a 1.0 project; effects and keyframes only exist from 1.2/1.3 on."""
    return migrate.migrate(json.loads(FIXTURE.read_text(encoding="utf-8")))[0]


def captioned() -> dict:
    """A project with one text block and a text track holding one clip of it."""
    data = ops.add_text(project(), "cap1", "العنوان الأول")
    data = ops.add_track(data, "tx1", "text")
    return ops.add_text_clip(data, "tx1", "c9", "cap1", 0, 30_000)


def test_update_clip_returns_a_new_valid_project() -> None:
    original = project()
    frozen = copy.deepcopy(original)
    edited = ops.update_clip(original, "c1", duration=240_000)
    assert edited["tracks"][0]["clips"][0]["duration"] == 240_000
    assert unified_project_check.validate(edited) == []
    assert original == frozen, "the verbs must not mutate their argument"


def test_a_caption_is_created_and_then_clipped() -> None:
    data = captioned()
    text = next(item for item in data["texts"] if item["id"] == "cap1")
    assert text["value"] == "العنوان الأول" and text["direction"] == "rtl" and text["wrap"] is True
    clip = data["tracks"][1]["clips"][0]
    assert clip["textId"] == "cap1" and "assetId" not in clip
    assert unified_project_check.validate(data) == []


def test_text_animation_can_be_set_and_cleared() -> None:
    data = ops.set_text(captioned(), "cap1", animation={"kind": "words-up", "stagger": 24_000})
    assert data["texts"][0]["animation"]["kind"] == "words-up"
    cleared = ops.set_text(data, "cap1", animation="none")
    assert "animation" not in cleared["texts"][0]


def test_an_empty_caption_is_refused() -> None:
    with pytest.raises(ValueError, match="needs a value"):
        ops.add_text(project(), "cap1", "   ")
    with pytest.raises(ValueError, match="duplicate text id"):
        ops.add_text(captioned(), "cap1", "آخر")


def test_an_impossible_edit_is_refused_with_the_checker_message() -> None:
    with pytest.raises(ValueError) as error:
        ops.update_clip(project(), "c1", source_in=720_000)
    assert "U05" in str(error.value)
    with pytest.raises(ValueError, match="unknown clip"):
        ops.update_clip(project(), "ghost", duration=1000)


def test_a_keyframe_curve_needs_a_real_effect() -> None:
    with pytest.raises(ValueError):
        ops.add_keyframe(project(), "c1", "nope", 0, 1000)
    with_effect = ops.add_effect(project(), "c1", {"id": "op", "type": "opacity", "version": 1,
                                                   "enabled": True, "params": {"value": 8000}})
    curved = ops.add_keyframe(with_effect, "c1", "op", 0, 0)
    assert curved["tracks"][0]["clips"][0]["keyframes"][0]["points"][0]["value"] == 0
    straight = ops.remove_keyframe(curved, "c1", "op", 0)
    assert straight["tracks"][0]["clips"][0]["keyframes"] == [], "an emptied curve is dropped"


def test_set_project_still_validates() -> None:
    assert ops.set_project(project(), name="نسخة تانية")["name"] == "نسخة تانية"
    with pytest.raises(ValueError, match="unknown project fields"):
        ops.set_project(project(), profile={})
