import pytest

from tools.render_hybrid import PlanError, executable, validate_plan

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
    ({"version": 2}, "version"),
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
