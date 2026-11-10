"""Hybrid v2.2 — several transparent Engine-K overlays above one opaque base.

Two overlays need two *different* pictures, and a hybrid project has one K source tree, so an
overlay names the K scenes it may draw (`scenes`). That makes a stack exact: scene → overlay is a
partition, a scene can never be drawn twice, and an unmatched scene never silently disappears into
the wrong layer. These tests pin the plan rules and the single-pass filtergraph; the pixel proof is
in `tests/test_hybrid_layers.py`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.render_hybrid import (
    PlanError,
    build_alpha_command,
    build_stack_command,
    composite_stack,
    validate_plan,
)


def stack_plan(*overlays) -> dict:
    return {
        "version": 2,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "duration_frames": 60,
        "audio": None,
        "segments": [
            {"id": "intro", "start_frame": 0, "end_frame": 60,
             "layers": [{"engine": "p"}, *overlays]},
        ],
    }


def overlay(scenes=None, **extra) -> dict:
    layer = {"engine": "k", "alpha": True}
    if scenes is not None:
        layer["scenes"] = scenes
    layer.update(extra)
    return layer


# ── the plan contract ────────────────────────────────────────────────────────
def test_three_overlays_keep_their_order_and_scene_filters():
    plan = validate_plan(stack_plan(overlay(["title"]), overlay(["card"]), overlay(["badge"])))
    layers = plan["segments"][0]["layers"]
    assert [layer.get("scenes") for layer in layers] == [None, ["title"], ["card"], ["badge"]]
    assert all(layer["alpha"] for layer in layers[1:])
    assert layers[0] == {"engine": "p", "alpha": False}


def test_four_overlays_is_the_ceiling():
    four = [overlay([f"s{i}"]) for i in range(4)]
    assert len(validate_plan(stack_plan(*four))["segments"][0]["layers"]) == 5
    with pytest.raises(PlanError, match="at most 4 overlays"):
        validate_plan(stack_plan(*[overlay([f"s{i}"]) for i in range(5)]))


def test_every_overlay_must_name_its_scenes_once_there_are_two():
    with pytest.raises(PlanError, match="overlay 2 has none"):
        validate_plan(stack_plan(overlay(["title"]), overlay()))
    with pytest.raises(PlanError, match="overlay 1 has none"):
        validate_plan(stack_plan(overlay(), overlay(["card"])))


def test_a_scene_may_not_be_drawn_by_two_overlays():
    with pytest.raises(PlanError, match="drawn by overlay 1 and overlay 2"):
        validate_plan(stack_plan(overlay(["title"]), overlay(["title"])))


def test_a_single_overlay_needs_no_scene_filter():
    """The v2.0 shape stays valid: one overlay renders the whole K timeline."""
    plan = validate_plan(stack_plan(overlay()))
    assert "scenes" not in plan["segments"][0]["layers"][1]


@pytest.mark.parametrize("layer, message", [
    (overlay([]), "non-empty array"),
    (overlay(["  "]), "letters, digits, _ or -"),
    (overlay(["a b"]), "letters, digits, _ or -"),
    (overlay(["title", "title"]), "lists the same id twice"),
    (overlay("title"), "non-empty array"),
])
def test_bad_scene_filters_are_rejected(layer, message):
    with pytest.raises(PlanError, match=message):
        validate_plan(stack_plan(layer))


def test_the_base_layer_cannot_select_scenes():
    plan = stack_plan(overlay(["title"]))
    plan["segments"][0]["layers"][0] = {"engine": "p", "scenes": ["title"]}
    with pytest.raises(PlanError, match="only a transparent overlay can select scenes"):
        validate_plan(plan)


def test_an_opaque_overlay_still_cannot_carry_scenes():
    plan = stack_plan({"engine": "k", "alpha": False, "scenes": ["title"]})
    with pytest.raises(PlanError, match="only a transparent Engine-K overlay"):
        validate_plan(plan)


# ── the commands ─────────────────────────────────────────────────────────────
def test_the_alpha_command_forwards_the_scene_filter():
    command = build_alpha_command("node", 0, 30, Path("/tmp/frames"), only=["title", "card"])
    assert command[command.index("--only") + 1] == "title,card"
    assert "--alpha" in command
    assert "--only" not in build_alpha_command("node", 0, 30, Path("/tmp/frames"))


def test_a_stack_is_one_encode_with_one_input_per_overlay():
    command = build_stack_command(
        "ffmpeg", Path("/tmp/base.mp4"),
        [{"frames_dir": Path("/tmp/a")}, {"frames_dir": Path("/tmp/b")}], 30, Path("/tmp/out.mp4"))
    assert command[-1] == "/tmp/out.mp4"
    assert command.count("-filter_complex") == 1 and command.count("-frames:v") == 1
    assert str(Path("/tmp/a") / "%05d.png") in command and str(Path("/tmp/b") / "%05d.png") in command
    graph = command[command.index("-filter_complex") + 1]
    assert "[1:v]format=rgba,setsar=1[ov1]" in graph
    assert "[2:v]format=rgba,setsar=1[ov2]" in graph
    assert "[acc0][ov1]overlay=format=auto[acc1]" in graph
    assert graph.endswith("[acc1][ov2]overlay=format=auto")  # last overlay paints on top
    assert command[command.index("-frames:v") + 1] == "30"


def test_only_the_masked_overlay_gets_alpha_maths():
    command = build_stack_command(
        "ffmpeg", Path("/tmp/base.mp4"),
        [{"frames_dir": Path("/tmp/a")},
         {"frames_dir": Path("/tmp/b"),
          "mask": {"type": "rect", "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "feather": 0.0}}],
        30, Path("/tmp/out.mp4"))
    graph = command[command.index("-filter_complex") + 1]
    assert "alphamerge" in graph and "ka2" in graph and "ka1" not in graph
    assert "drawbox" in graph  # the rect matte is generated inside the graph


def test_an_empty_stack_is_refused():
    with pytest.raises(RuntimeError, match="at least one overlay"):
        build_stack_command("ffmpeg", Path("/tmp/base.mp4"), [], 30, Path("/tmp/out.mp4"))


def test_composite_stack_names_the_overlay_with_the_wrong_frame_count(tmp_path, monkeypatch):
    """'overlay produced 2 frames' is useless without saying which one."""
    empty = tmp_path / "a"
    empty.mkdir()
    good, bad = tmp_path / "b", tmp_path / "c"
    for directory, count in ((good, 3), (bad, 2)):
        directory.mkdir()
        for index in range(count):
            (directory / f"{index:05d}.png").write_bytes(b"not really a png")
    monkeypatch.setattr("tools.render_hybrid.run", lambda *a, **k: None)
    with pytest.raises(RuntimeError, match="overlay 2 produced 2 frame"):
        composite_stack("ffmpeg", tmp_path / "base.mp4",
                        [{"frames_dir": good}, {"frames_dir": bad}], 3,
                        tmp_path, {"PATH": "/usr/bin:/bin"}, label="stack")
