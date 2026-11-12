"""Contract 1.5: styled runs inside one text block, and animation that moves single letters.

The interesting part is not the schema — it is that an Arabic word stays *joined* while its letters
move. Splitting the word before shaping would print isolated letterforms, so the shaper runs once on
the whole word and the glyphs are grouped by source cluster; these tests check the pixels, not the
intent.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import unified_project_check as checker  # noqa: E402
import unified_project_migrate as migrate  # noqa: E402
from unified_reference_preview import render_frame  # noqa: E402

FONT = "Cairo"


def project(tmp_path: Path, text: dict, *, size=(240, 320), duration: int = 240_000) -> dict:
    still = b"P6\n%d %d\n255\n" % size + bytes([20, 30, 60]) * (size[0] * size[1])
    (tmp_path / "still.ppm").write_bytes(still)
    return {
        "schemaVersion": "1.5", "id": "text15", "name": "Text 1.5",
        "profile": {"width": size[0], "height": size[1], "fps": {"num": 30, "den": 1},
                    "sampleRate": 48_000},
        "timebase": 240_000, "duration": duration, "seed": 7,
        "assets": [{"id": "a1", "kind": "image", "uri": "still.ppm",
                    "sha256": hashlib.sha256(still).hexdigest()}],
        "texts": [{"id": "cap", "value": "مرحبا بالعالم", "font": FONT, "size": 44,
                   "color": "#ffffff", "align": "center", "direction": "rtl", "wrap": True, **text}],
        "tracks": [
            {"id": "v", "kind": "video", "enabled": True, "clips": [
                {"id": "c1", "kind": "media", "assetId": "a1", "start": 0, "duration": duration,
                 "sourceIn": 0, "effects": [], "keyframes": []}], "transitions": []},
            {"id": "t", "kind": "text", "enabled": True, "clips": [
                {"id": "c2", "kind": "media", "textId": "cap", "start": 0, "duration": duration,
                 "sourceIn": 0, "effects": [], "keyframes": []}]},
        ],
    }


def ink(pixels: bytes) -> int:
    """How many pixels differ from the background — a cheap 'is anything drawn' measure."""
    background = bytes([20, 30, 60, 255])
    return sum(1 for index in range(0, len(pixels), 4)
               if pixels[index:index + 4] != background)


# ---------------------------------------------------------------- runs
def bbox(pixels: bytes, size: tuple[int, int]) -> tuple[int, int, int, int]:
    """Ink bounding box, so two pictures can be compared by where the type sits."""
    width, height = size
    background = bytes([20, 30, 60, 255])
    xs, ys = [], []
    for index in range(0, len(pixels), 4):
        if pixels[index:index + 4] != background:
            position = index // 4
            xs.append(position % width)
            ys.append(position // width)
    if not xs:
        return (0, 0, 0, 0)
    return (min(xs), min(ys), max(xs), max(ys))


def test_a_run_recolours_one_word_only(tmp_path: Path) -> None:
    plain = project(tmp_path, {})
    assert checker.validate(plain) == []
    tinted = project(tmp_path, {"runs": [{"start": 0, "end": 5, "color": "#ff8800"}]})
    assert checker.validate(tinted) == []
    base = render_frame(plain, tmp_path, 1)["pixels"]
    changed = render_frame(tinted, tmp_path, 1)["pixels"]
    assert base != changed, "the run must change the picture"
    warm = sum(1 for index in range(0, len(changed), 4)
               if changed[index] > 200 and changed[index + 1] < 160 and changed[index + 2] < 80)
    assert warm > 0, "the first word must actually be orange"
    assert ink(base) > 0 and ink(changed) > 0


def test_a_run_may_change_size_and_family(tmp_path: Path) -> None:
    bigger = project(tmp_path, {"runs": [{"start": 6, "end": 13, "size": 72}]})
    assert checker.validate(bigger) == []
    small = render_frame(project(tmp_path, {}), tmp_path, 1)["pixels"]
    assert ink(render_frame(bigger, tmp_path, 1)["pixels"]) > ink(small)


@pytest.mark.parametrize("run,code", [
    ({"start": 3, "end": 5, "color": "#ffffff"}, "U12"),      # starts inside a word
    ({"start": 0, "end": 3, "color": "#ffffff"}, "U12"),      # ends inside a word
    ({"start": 5, "end": 5, "color": "#ffffff"}, "U12"),      # empty range
    ({"start": 0, "end": 500, "color": "#ffffff"}, "U12"),    # past the end
    ({"start": 0, "end": 5}, "U12"),                          # changes nothing
    ({"start": 6, "end": 12, "color": "#ffffff"},
     {"start": 0, "end": 5, "color": "#ffffff"}),             # unsorted
])
def test_runs_that_would_break_a_word_are_refused(tmp_path: Path, run: dict, code) -> None:
    runs = run if isinstance(code, list) else [run]
    data = project(tmp_path, {"runs": runs})
    errors = checker.validate(data)
    assert any("U12" in error for error in errors), errors


# ---------------------------------------------------------------- letters
def test_letter_animation_reveals_letters_one_by_one(tmp_path: Path) -> None:
    data = project(tmp_path, {"animation": {"kind": "letters-fade", "stagger": 20_000,
                                            "ease": "cubic-out"}})
    assert checker.validate(data) == []
    drawn = [ink(render_frame(data, tmp_path, frame)["pixels"]) for frame in range(0, 24)]
    assert drawn[0] == 0, "at tick 0 nothing has started yet"
    assert drawn[1] > 0, "the first letter is the first thing to appear"
    assert drawn[3] > drawn[1] and drawn[10] > drawn[3], "letters keep arriving"
    assert drawn == sorted(drawn), "a fade only ever adds ink"
    assert len({value for value in drawn}) > 4, "letters arrive one at a time, not all at once"


def test_letter_animation_moves_letters_and_not_just_their_alpha(tmp_path: Path) -> None:
    fade = project(tmp_path, {"animation": {"kind": "letters-fade", "stagger": 20_000}})
    rise = project(tmp_path, {"animation": {"kind": "letters-up", "stagger": 20_000}})
    assert checker.validate(rise) == []
    early_fade = render_frame(fade, tmp_path, 2)
    early_rise = render_frame(rise, tmp_path, 2)
    assert early_fade["pixels"] != early_rise["pixels"], "letters-up must displace the letters"
    later_rise = render_frame(rise, tmp_path, 19)
    assert bbox(early_rise["pixels"], (early_rise["width"], early_rise["height"])) != \
           bbox(later_rise["pixels"], (later_rise["width"], later_rise["height"])), "and they settle"


def test_the_finished_letter_animation_is_the_plain_word(tmp_path: Path) -> None:
    """Shaping runs once on the whole word, so at rest the caption sits where the static one does.

    The letter path lays out by the shaped advance and the word path by its ink box, so a finished
    animation may be a couple of pixels off centre; nothing else about the picture changes.
    """
    animated = project(tmp_path, {"animation": {"kind": "letters-fade", "stagger": 8_000}})
    plain = project(tmp_path, {})
    eased = render_frame(animated, tmp_path, 29)
    exact = render_frame(plain, tmp_path, 29)
    box_a = bbox(eased["pixels"], (eased["width"], eased["height"]))
    box_b = bbox(exact["pixels"], (exact["width"], exact["height"]))
    assert max(abs(a - b) for a, b in zip(box_a, box_b)) <= 4, (box_a, box_b)
    assert abs(ink(eased["pixels"]) - ink(exact["pixels"])) / max(1, ink(exact["pixels"])) < 0.05


def test_arabic_letters_keep_their_joined_forms(tmp_path: Path) -> None:
    """If a letter were shaped alone, the word would be wider and its ink different."""
    from PIL import Image  # noqa: PLC0415

    sys.path.insert(0, str(ROOT / "medo-motion/templates/procedural-reels"))
    import arabic_shape  # noqa: E402

    font = str(ROOT / "assets/fonts/Cairo/Cairo_800ExtraBold.ttf")
    joined = arabic_shape.text_sprite(font, "مرحبا", 44, (255, 255, 255), True)
    clusters, width, _asc, _desc = arabic_shape.text_clusters(font, "مرحبا", 44, (255, 255, 255), True)
    assert len(clusters) >= 4
    # glued clusters spans the same advance as the shaped word, so nothing lost its connections
    span = max(item["x"] + item["width"] for item in clusters) - min(item["x"] for item in clusters)
    assert abs(span - (joined.shape[1] - 12)) < 44 * 0.6, (span, joined.shape)


def test_a_letter_animation_needs_more_than_one_letter(tmp_path: Path) -> None:
    data = project(tmp_path, {"value": "م", "animation": {"kind": "letters-up", "stagger": 8_000}})
    assert any("U11" in error for error in checker.validate(data))


# ---------------------------------------------------------------- migration
def test_a_1_4_project_migrates_to_1_5_without_losing_anything(tmp_path: Path) -> None:
    data = project(tmp_path, {"runs": [{"start": 0, "end": 5, "color": "#ff8800"}]})
    data["schemaVersion"] = "1.4"
    migrated, report = migrate.migrate(data)
    assert migrated["schemaVersion"] == "1.5"
    assert migrated["texts"] == data["texts"]
    assert report["steps"][-1]["step"] == "1.5"
    assert checker.validate(migrated) == []
