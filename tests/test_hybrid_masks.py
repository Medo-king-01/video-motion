"""Hybrid v2.1 — a masked K overlay, so type can pass *behind* a P presenter.

The mask is a static matte where **white keeps the base**: the overlay's own alpha is multiplied by
`1 - mask` in FFmpeg, which means Engine-K pixels are discarded exactly where the presenter stands.
These tests pin the plan contract and the graph shape; the pixel proof lives in
`tests/test_hybrid_layers.py` (it needs a real encoder).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.render_hybrid import (
    PlanError,
    build_composite_command,
    build_mask_source,
    resolve_mask_image,
    validate_plan,
)


def masked_plan(mask=None) -> dict:
    overlay = {"engine": "k", "alpha": True}
    if mask is not None:
        overlay["mask"] = mask
    return {
        "version": 2,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "duration_frames": 60,
        "audio": None,
        "segments": [
            {"id": "intro", "start_frame": 0, "end_frame": 60,
             "layers": [{"engine": "p"}, overlay]},
        ],
    }


def rect_mask(**overrides) -> dict:
    mask = {"type": "rect", "x": 0.34, "y": 0.42, "w": 0.32, "h": 0.58, "feather": 0.0}
    mask.update(overrides)
    return mask


# ── the plan contract ─────────────────────────────────────────────────────────
def test_a_rect_mask_is_normalised_to_floats_and_kept_on_the_overlay():
    plan = validate_plan(masked_plan(rect_mask(feather=8)))
    base, overlay = plan["segments"][0]["layers"]
    assert "mask" not in base  # the base is never masked
    assert overlay["mask"] == {"type": "rect", "x": 0.34, "y": 0.42, "w": 0.32, "h": 0.58,
                               "feather": 8.0}


def test_an_unmasked_overlay_keeps_its_exact_old_shape():
    """v2 plans written before v2.1 must normalise byte-identically."""
    plan = validate_plan(masked_plan())
    assert plan["segments"][0]["layers"] == [{"engine": "p", "alpha": False},
                                             {"engine": "k", "alpha": True}]


def test_a_matte_image_mask_is_kept_as_a_project_relative_path():
    plan = validate_plan(masked_plan({"type": "image", "path": "assets/presenter-matte.png"}))
    assert plan["segments"][0]["layers"][1]["mask"] == {
        "type": "image", "path": "assets/presenter-matte.png"}


@pytest.mark.parametrize("mask, message", [
    ({"type": "rect", "x": 0.6, "y": 0.4, "w": 0.5, "h": 0.5}, "stay inside the canvas"),
    ({"type": "rect", "x": 0.1, "y": 0.4, "w": 0.0, "h": 0.5}, "must be positive"),
    ({"type": "rect", "x": -0.1, "y": 0.4, "w": 0.2, "h": 0.5}, "between 0 and 1"),
    ({"type": "rect", "x": "0.1", "y": 0.4, "w": 0.2, "h": 0.5}, "must be a number"),
    ({"type": "rect", "x": 0.1, "y": 0.4, "w": 0.2, "h": 0.5, "feather": -1}, "feather must be between"),
    ({"type": "rect", "x": 0.1, "y": 0.4, "w": 0.2, "h": 0.5, "feather": 400}, "feather must be between"),
    ({"type": "blob"}, "mask type must be rect or image"),
    ({"type": "image", "path": "/etc/passwd"}, "stay inside the project"),
    ({"type": "image", "path": "../outside.png"}, "stay inside the project"),
    ({"type": "image", "path": "  "}, "project-relative file path"),
    ("rect", "mask must be an object"),
])
def test_invalid_masks_are_rejected(mask, message):
    with pytest.raises(PlanError, match=message):
        validate_plan(masked_plan(mask))


def test_a_mask_on_the_base_layer_is_rejected():
    plan = masked_plan()
    plan["segments"][0]["layers"] = [{"engine": "p", "mask": rect_mask()},
                                     {"engine": "k", "alpha": True}]
    with pytest.raises(PlanError, match="only a transparent overlay can carry a mask"):
        validate_plan(plan)


def test_a_mask_on_an_opaque_overlay_is_rejected():
    """`alpha: true` is what makes the overlay separable; a mask without it means nothing."""
    plan = masked_plan()
    plan["segments"][0]["layers"] = [{"engine": "k"}, {"engine": "k", "alpha": False,
                                                       "mask": rect_mask()}]
    with pytest.raises(PlanError, match="only a transparent overlay|only a transparent Engine-K"):
        validate_plan(plan)


# ── the filtergraph ──────────────────────────────────────────────────────────
def test_the_mask_source_is_white_where_the_base_wins():
    chain = build_mask_source(rect_mask())
    assert "color=c=black" in chain and "color=white" in chain
    assert "drawbox=x=367:y=806:w=346:h=1114" in chain  # fractions × 1080×1920, rounded
    assert "format=gray" in chain
    assert "gblur" not in chain  # no feather requested, no blur


def test_a_feathered_mask_is_blurred_but_never_inverted():
    chain = build_mask_source(rect_mask(feather=10))
    assert "gblur=sigma=5.000" in chain


def test_the_masked_composite_multiplies_the_overlay_alpha():
    command = build_composite_command("ffmpeg", Path("/tmp/base.mp4"), Path("/tmp/frames"), 30,
                                      Path("/tmp/out.mp4"), mask=rect_mask())
    graph = command[command.index("-filter_complex") + 1]
    assert "alphaextract" in graph and "alphamerge" in graph
    assert "blend=all_mode=multiply" in graph
    assert "negate" in graph                     # white (base) → zero overlay alpha
    assert graph.endswith("[mb][ovm]overlay=format=auto")
    assert command[command.index("-frames:v") + 1] == "30"


def test_an_unmasked_composite_keeps_the_plain_overlay():
    command = build_composite_command("ffmpeg", Path("/tmp/base.mp4"), Path("/tmp/frames"), 30,
                                      Path("/tmp/out.mp4"))
    graph = command[command.index("-filter_complex") + 1]
    assert graph == "[0:v][1:v]overlay=format=auto"
    assert "alphamerge" not in graph


def test_a_matte_image_becomes_a_third_input_not_a_filter():
    command = build_composite_command("ffmpeg", Path("/tmp/base.mp4"), Path("/tmp/frames"), 30,
                                      Path("/tmp/out.mp4"),
                                      mask={"type": "image", "path": "matte.png"},
                                      mask_image=Path("/tmp/matte.png"))
    assert "-loop" in command and "1" in command
    assert command[command.index("-i", command.index("-loop")) + 1] == "/tmp/matte.png"
    assert "[2:v]format=gray,negate" in command[command.index("-filter_complex") + 1]


# ── the matte file itself ────────────────────────────────────────────────────
def test_a_matte_must_exist(tmp_path):
    with pytest.raises(RuntimeError, match="mask matte not found"):
        resolve_mask_image({"type": "image", "path": "assets/none.png"}, tmp_path, "segment intro")


def test_a_matte_may_not_escape_the_project(tmp_path):
    outside = tmp_path.parent / "elsewhere.png"
    outside.write_bytes(b"\x89PNG\r\n\x1a\n")
    project = tmp_path / "project"
    project.mkdir()
    (project / "link.png").symlink_to(outside)
    with pytest.raises(RuntimeError, match="escapes the project"):
        resolve_mask_image({"type": "image", "path": "link.png"}, project, "segment intro")


def test_a_matte_inside_the_project_resolves(tmp_path):
    matte = tmp_path / "assets" / "matte.png"
    matte.parent.mkdir()
    matte.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert resolve_mask_image({"type": "image", "path": "assets/matte.png"}, tmp_path, "x") == matte
