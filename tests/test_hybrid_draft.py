"""Hybrid drafts — a 540x960 / 15 fps review copy of a layered reel.

The rule that makes it honest: a draft halves **frames**, not quality claims. P still renders at
1080x1920 (so it saves frames only), K renders at half scale, and the timeline stays anchored to
absolute frame numbers — draft frame k is source frame 2k — so a 60-frame master and its draft are
both 2.000 s. Nothing here re-encodes a master and calls it a preview.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import render_hybrid  # noqa: E402
from render_hybrid import (  # noqa: E402
    build_alpha_command,
    build_mask_source,
    build_segment_command,
    build_stack_command,
    canvas,
    draft_frames,
)


def test_the_draft_canvas_is_half_size_at_half_the_rate():
    assert canvas(True) == (540, 960, 15)
    assert canvas(False) == (1080, 1920, 30)


@pytest.mark.parametrize("start, end, expected", [
    (0, 60, 30), (0, 30, 15), (30, 60, 15), (30, 61, 15), (1, 7, 3), (0, 2, 1),
])
def test_draft_frames_are_anchored_to_absolute_frame_numbers(start, end, expected):
    assert draft_frames(start, end) == expected


def test_a_pt_segment_asks_engine_p_for_a_draft():
    master = build_segment_command("p", python="python", node="node", ffmpeg="ffmpeg",
                                   project=Path("/p"), start=0, end=60, sid="intro",
                                   target=Path("/out/intro.mp4"), frames_dir=Path("/run"))
    draft = build_segment_command("p", python="python", node="node", ffmpeg="ffmpeg",
                                  project=Path("/p"), start=0, end=60, sid="intro",
                                  target=Path("/out/intro.mp4"), frames_dir=Path("/run"), draft=True)
    assert "--draft" not in master and draft[-1] == "--draft"


def test_a_k_base_segment_renders_at_half_scale_and_rate():
    draft = build_segment_command("k", python="python", node="node", ffmpeg="ffmpeg",
                                  project=Path("/p"), start=0, end=60, sid="intro",
                                  target=Path("/out/intro.mp4"), frames_dir=Path("/run"), draft=True)
    assert draft[draft.index("--fps") + 1] == "15"
    assert draft[draft.index("--scale") + 1] == "0.5"


def test_an_r_base_segment_refuses_to_pretend_it_has_a_draft():
    with pytest.raises(RuntimeError, match="R/Remotion base"):
        build_segment_command("r", python="python", node="node", ffmpeg="ffmpeg",
                              project=Path("/p"), start=0, end=60, sid="intro",
                              target=Path("/out/intro.mp4"), frames_dir=Path("/run"), draft=True)


def test_a_draft_overlay_is_transparent_at_fifteen_fps():
    draft = build_alpha_command("node", 0, 60, Path("/frames"), only=["title"], draft=True)
    assert draft[draft.index("--fps") + 1] == "15"
    assert draft[draft.index("--scale") + 1] == "0.5"
    assert "--alpha" in draft and draft[draft.index("--only") + 1] == "title"


def test_the_mask_is_built_on_the_draft_canvas():
    mask = {"type": "rect", "x": 0.5, "y": 0.5, "w": 0.5, "h": 0.5, "feather": 0.0}
    source = build_mask_source(mask, 540, 960, 15)
    assert "s=540x960:r=15" in source
    assert "drawbox=x=270:y=480:w=270:h=480" in source


def test_the_stack_encodes_at_the_draft_rate():
    command = build_stack_command("ffmpeg", Path("/base.mp4"),
                                  [{"frames_dir": Path("/a")}], 30, Path("/out.mp4"),
                                  width=540, height=960, fps=15)
    assert command[command.index("-r") + 1] == "15"
    assert "15" in command  # the PNG sequence is read at 15 fps too


def _project(tmp_path: Path, plan: dict) -> Path:
    project = tmp_path / "project"
    (project / "plan").mkdir(parents=True)
    (project / "out").mkdir()
    (project / "plan" / "hybrid.json").write_text(json.dumps(plan), encoding="utf-8")
    return project


def layered_plan(duration: int = 60, segment_frames: int | None = None) -> dict:
    frames = segment_frames if segment_frames is not None else duration
    return {"version": 2, "duration_frames": duration, "audio": None,
            "segments": [{"id": "intro", "start_frame": 0, "end_frame": frames,
                          "layers": [{"engine": "p"}, {"engine": "k", "alpha": True}]}]}


def test_a_draft_is_never_qaed(tmp_path, monkeypatch):
    project = _project(tmp_path, layered_plan())
    monkeypatch.setattr(sys, "argv", ["render_hybrid.py", "--project", str(project),
                                      "--draft", "--qa"])
    with pytest.raises(RuntimeError, match="not QA'd"):
        render_hybrid.main()


def test_a_draft_has_no_soundtrack(tmp_path, monkeypatch):
    project = _project(tmp_path, layered_plan())
    monkeypatch.setattr(sys, "argv", ["render_hybrid.py", "--project", str(project),
                                      "--draft", "--audio", "assets/vo.wav"])
    with pytest.raises(RuntimeError, match="no soundtrack"):
        render_hybrid.main()


def test_a_segment_too_short_to_halve_is_refused(tmp_path, monkeypatch):
    project = _project(tmp_path, layered_plan(duration=1, segment_frames=1))
    monkeypatch.setattr(sys, "argv", ["render_hybrid.py", "--project", str(project), "--draft"])
    with pytest.raises(RuntimeError, match="too short"):
        render_hybrid.main()


# --- the master path is pinned: a draft fix must not move a single master argument ------------

MASTER_RANGES = [(0, 3, "0", "0.1"), (3, 6, "0.1", "0.2"), (4, 7, "0.133333333333", "0.233333333333"),
                 (30, 61, "1", "2.03333333333"), (0, 60, "0", "2")]


@pytest.mark.parametrize("start, end, time_from, time_to", MASTER_RANGES)
def test_the_master_commands_are_exactly_these(tmp_path, start, end, time_from, time_to):
    """Regression guard, written before the draft frame rule is changed: full size, 30 fps, [start, end)."""
    project, target, frames = tmp_path / "reel", tmp_path / "s.mp4", tmp_path / "frames"
    common = dict(python="py", node="node", ffmpeg="ff", project=project, start=start, end=end, sid="s",
                  target=target, frames_dir=frames)
    assert build_segment_command("k", **common) == [
        "node", "src/render.js", "--from", time_from, "--to", time_to, "--fps", "30", "--scale", "1",
        "--out", str(frames), "--name", "s"]
    assert build_segment_command("p", **common) == [
        "py", str(render_hybrid.ROOT / "tools" / "render_p_segment.py"), "--project", str(project),
        "--from-frame", str(start), "--to-frame", str(end), "--out", str(target), "--ffmpeg", "ff", "--fps", "30"]
    assert build_segment_command("r", **common) == [
        "node", "scripts/render.mjs", "--silent", "--from-frame", str(start), "--to-frame", str(end),
        "--out", str(target)]
    assert build_alpha_command("node", start, end, frames) == [
        "node", "src/render.js", "--from", time_from, "--to", time_to, "--fps", "30", "--scale", "1",
        "--alpha", "--out", str(frames)]
    assert build_alpha_command("node", start, end, frames, only=["a", "b"])[-2:] == ["--only", "a,b"]
