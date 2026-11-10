from pathlib import Path

import pytest

from tools.render_hybrid import (
    PlanError,
    build_alpha_command,
    build_composite_command,
    build_segment_command,
    executable,
    validate_plan,
)

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop


def valid_plan():
    return {
        "version": 1,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "duration_frames": 90,
        "audio": "assets/vo/test.wav",
        "segments": [
            {"id": "presenter", "engine": "p", "start_frame": 0, "end_frame": 30},
            {"id": "type", "engine": "k", "start_frame": 30, "end_frame": 60},
            {"id": "chart", "engine": "r", "start_frame": 60, "end_frame": 90},
        ],
    }


def test_executable_falls_back_to_path_when_repo_default_is_missing(monkeypatch):
    monkeypatch.delenv("FFMPEG_BIN", raising=False)
    monkeypatch.setattr("tools.render_hybrid.shutil.which", lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)
    assert executable(None, "ffmpeg", "/missing/repository/ffmpeg") == "/usr/bin/ffmpeg"


def test_executable_preserves_environment_symlink_paths(tmp_path):
    target = tmp_path / "python-base"
    target.write_text("interpreter placeholder")
    environment_python = tmp_path / "python-env"
    environment_python.symlink_to(target)
    assert executable(None, "python", str(environment_python)) == str(environment_python)


def test_valid_hybrid_plan_accepts_all_three_engines_and_half_open_ranges():
    result = validate_plan(valid_plan())
    assert [item["engine"] for item in result["segments"]] == ["p", "k", "r"]
    assert result["segments"][-1]["end_frame"] == result["duration_frames"]


@pytest.mark.parametrize("change, message", [
    ({"version": 3}, "version"),
    ({"fps": 24}, "frame rate"),
    ({"width": 720}, "canvas"),
    ({"duration_frames": 0}, "duration_frames"),
    ({"segments": []}, "non-empty"),
])
def test_invalid_hybrid_plan_header_is_rejected(change, message):
    plan = valid_plan() | change
    with pytest.raises(PlanError, match=message):
        validate_plan(plan)


def test_plan_rejects_gaps_and_overlaps():
    plan = valid_plan()
    plan["segments"][1]["start_frame"] = 31
    with pytest.raises(PlanError, match="gap or overlap"):
        validate_plan(plan)


def test_plan_rejects_end_before_duration():
    plan = valid_plan()
    plan["segments"][-1]["end_frame"] = 89
    with pytest.raises(PlanError, match="duration_frames"):
        validate_plan(plan)


def test_plan_rejects_unknown_engine_and_duplicate_ids():
    plan = valid_plan()
    plan["segments"][0]["engine"] = "x"
    with pytest.raises(PlanError, match="engine must be"):
        validate_plan(plan)
    plan = valid_plan()
    plan["segments"][1]["id"] = "presenter"
    with pytest.raises(PlanError, match="duplicate segment"):
        validate_plan(plan)


def test_plan_rejects_noninteger_or_empty_segment_ranges():
    plan = valid_plan()
    plan["segments"][0]["end_frame"] = 30.0
    with pytest.raises(PlanError, match="integer frame indexes"):
        validate_plan(plan)
    plan = valid_plan()
    plan["segments"][0]["end_frame"] = 0
    with pytest.raises(PlanError, match="at least one frame"):
        validate_plan(plan)


def test_audio_may_be_explicitly_disabled_but_not_blank():
    plan = valid_plan()
    plan["audio"] = None
    assert validate_plan(plan)["audio"] is None
    plan["audio"] = "  "
    with pytest.raises(PlanError, match="project-relative file path or null"):
        validate_plan(plan)
    plan["audio"] = "../outside.wav"
    with pytest.raises(PlanError, match="stay inside the project"):
        validate_plan(plan)


# ── version 2: one opaque base + one transparent Engine-K overlay ────────────
def layered_plan():
    return {
        "version": 2,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "duration_frames": 90,
        "audio": None,
        "segments": [
            {"id": "intro", "start_frame": 0, "end_frame": 60,
             "layers": [{"engine": "p"}, {"engine": "k", "alpha": True}]},
            {"id": "outro", "start_frame": 60, "end_frame": 90, "engine": "r"},
        ],
    }


def test_version_2_plan_keeps_the_base_engine_and_the_overlay():
    result = validate_plan(layered_plan())
    intro, outro = result["segments"]
    assert intro["engine"] == "p" and intro["layers"] == [
        {"engine": "p", "alpha": False}, {"engine": "k", "alpha": True}]
    assert outro["engine"] == "r" and outro["layers"] == [{"engine": "r", "alpha": False}]


def test_version_1_plans_normalise_to_single_layer_segments():
    result = validate_plan(valid_plan())
    assert all(segment["layers"] == [{"engine": segment["engine"], "alpha": False}]
               for segment in result["segments"])


@pytest.mark.parametrize("layers, message", [
    ([{"engine": "k", "alpha": True}], "base layer cannot be transparent"),
    ([{"engine": "p"}, {"engine": "r", "alpha": True}], "Engine K only"),
    ([{"engine": "p"}, {"engine": "k"}], "only a transparent Engine-K overlay"),
    ([{"engine": "p"}, {"engine": "k", "alpha": True}, {"engine": "k", "alpha": True}], "at most one overlay"),
    ([], "one base and at most one overlay"),
    ([{"engine": "x"}], "layer engine must be"),
])
def test_invalid_layer_stacks_are_rejected(layers, message):
    plan = layered_plan()
    plan["duration_frames"] = 60
    plan["segments"] = [{"id": "only", "start_frame": 0, "end_frame": 60, "layers": layers}]
    with pytest.raises(PlanError, match=message):
        validate_plan(plan)


def test_engine_and_layers_together_are_rejected():
    plan = layered_plan()
    plan["segments"][0]["engine"] = "p"
    with pytest.raises(PlanError, match="either engine or layers"):
        validate_plan(plan)


def test_the_alpha_command_is_a_transparent_png_sequence():
    command = build_alpha_command("node", 30, 60, Path("/tmp/frames"))
    assert "--alpha" in command
    assert command[command.index("--fps") + 1] == "30"
    assert command[command.index("--out") + 1] == "/tmp/frames"
    assert "--name" not in command


def test_the_composite_command_overlays_frame_for_frame():
    command = build_composite_command("ffmpeg", Path("/tmp/base.mp4"), Path("/tmp/frames"), 30, Path("/tmp/out.mp4"))
    assert any("overlay=format=auto" in part for part in command)
    assert command[command.index("-frames:v") + 1] == "30"
    assert str(Path("/tmp/frames") / "%05d.png") in command
    assert command[-1] == "/tmp/out.mp4"


def test_the_base_k_command_still_writes_named_footage(tmp_path):
    command = build_segment_command("k", python="python", node="node", ffmpeg="ffmpeg",
                                    project=Path("/p"), start=0, end=30, sid="intro",
                                    target=tmp_path / "intro.mp4", frames_dir=tmp_path)
    assert command[command.index("--name") + 1] == "intro"
    assert "--alpha" not in command
