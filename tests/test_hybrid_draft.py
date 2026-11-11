"""Hybrid drafts — a 540x960 / 15 fps review copy of a layered reel.

The rule that makes it honest: a draft halves **frames**, not quality claims. P still renders at
1080x1920 (so it saves frames only), K renders at half scale, and a segment [start, end) shows
source frames start, start+2, … — `end // 2 - start // 2` of them, all inside the segment — so a
60-frame master and its draft are both 2.000 s. Nothing here re-encodes a master and calls it a preview.
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


# --- one sampling rule for P, K and the K alpha overlay ---------------------------------------
#
# A draft of [start, end) shows source frames start, start+2, … stopping before end // 2 * 2.

GRID = [(start, end) for start in range(12) for end in range(start + 1, start + 13)]
RENDER_JS = Path(__file__).resolve().parents[1] / "medo-motion" / "templates" / "render" / "render.js"


def _k_source_frames(command: list[str]) -> list[int]:
    """The source frames `render.js` draws for this command: its own arithmetic, restated.

    render.js: `count = Math.ceil((to - from) * fps - 1e-8)` frames at `from + i / fps`
    (`test_the_k_arithmetic_restated_here_is_still_render_js` fails if that changes)."""
    import math

    time_from, time_to, fps = (float(command[command.index(flag) + 1]) for flag in ("--from", "--to", "--fps"))
    count = math.ceil((time_to - time_from) * fps - 1e-8)
    times = [time_from + index / fps for index in range(count)]
    frames = [round(time * 30) for time in times]
    assert all(abs(time * 30 - frame) < 1e-6 for time, frame in zip(times, frames, strict=True)), (
        f"K would sample between source frames: {times}")
    return frames


def _draft_commands(start: int, end: int) -> tuple[list[str], list[str]]:
    base = build_segment_command("k", python="py", node="node", ffmpeg="ff", project=Path("/p"), start=start,
                                 end=end, sid="s", target=Path("/o.mp4"), frames_dir=Path("/run"), draft=True)
    return base, build_alpha_command("node", start, end, Path("/frames"), only=["title"], draft=True)


def test_the_k_arithmetic_restated_here_is_still_render_js():
    source = RENDER_JS.read_text(encoding="utf-8")
    assert "const count=Math.ceil((to-from)*fps-1e-8)" in source
    assert "window.renderFrame(t),from+i/fps" in source


@pytest.mark.parametrize("start, end, samples", [
    (0, 3, [0]), (3, 6, [3, 5]), (3, 5, [3]), (30, 61, list(range(30, 60, 2))), (4, 7, [4]), (0, 60, list(range(0, 60, 2))),
])
def test_the_reference_ranges_sample_these_source_frames(start, end, samples):
    import render_p_segment

    base, alpha = _draft_commands(start, end)
    assert render_hybrid.draft_samples(start, end) == samples
    assert render_p_segment.draft_source_frames(start, end) == samples
    assert _k_source_frames(base) == samples and _k_source_frames(alpha) == samples
    assert draft_frames(start, end) == len(samples)


@pytest.mark.parametrize("start, end", GRID)
def test_p_k_and_the_overlay_sample_the_same_frames_inside_the_segment(start, end):
    import render_p_segment

    expected = end // 2 - start // 2
    if expected == 0:  # e.g. [2, 3): no whole draft frame — the runner refuses it (tested above), every engine agrees
        assert render_p_segment.draft_source_frames(start, end) == render_hybrid.draft_samples(start, end) == []
        with pytest.raises(RuntimeError, match="no frame to show"):
            _draft_commands(start, end)
        return
    base, alpha = _draft_commands(start, end)
    p_frames = render_p_segment.draft_source_frames(start, end)
    k_frames, alpha_frames = _k_source_frames(base), _k_source_frames(alpha)
    assert len(p_frames) == len(k_frames) == len(alpha_frames) == draft_frames(start, end) == expected   # (a) count
    assert p_frames == k_frames == alpha_frames == render_hybrid.draft_samples(start, end)               # (b) same list
    assert all(start <= frame < end for frame in p_frames), p_frames                                       # (c) inside
    assert p_frames[0] == start and all(b - a == 2 for a, b in zip(p_frames, p_frames[1:], strict=False))
    assert float(base[base.index("--to") + 1]) <= end / 30 + 1e-9, "K is asked for time past the segment"


@pytest.mark.parametrize("cuts", [[0, 3, 6], [0, 3, 5, 8, 13], [0, 1, 2], [0, 2, 3, 4], [0, 7, 12, 61], list(range(0, 25))])
def test_consecutive_segments_add_up_to_half_the_reel_and_never_overlap(cuts):
    segments = list(zip(cuts, cuts[1:], strict=False))
    samples = [frame for start, end in segments for frame in render_hybrid.draft_samples(start, end)]
    assert len(samples) == sum(draft_frames(start, end) for start, end in segments) == cuts[-1] // 2
    assert samples == sorted(set(samples)), "a source frame is shown twice or out of order"
    gaps = {b - a for a, b in zip(samples, samples[1:], strict=False)}
    assert gaps <= {1, 2, 3, 4}, f"draft samples are {gaps} source frames apart"
