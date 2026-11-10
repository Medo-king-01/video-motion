"""tools/pipeline.py — engine detection, step planning, timing report (no real renders)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline", ROOT / "tools" / "pipeline.py")
pipeline = importlib.util.module_from_spec(SPEC)
sys.modules["pipeline"] = pipeline
SPEC.loader.exec_module(pipeline)


def make_project(tmp_path: Path, kind: str) -> Path:
    proj = tmp_path / kind
    (proj / "plan").mkdir(parents=True)
    (proj / "out").mkdir(exist_ok=True)
    (proj / "plan" / "beats.json").write_text(json.dumps({"fps": 30, "frames": 18, "duration": 0.6}), encoding="utf-8")
    if kind == "p":
        (proj / "run_all.py").write_text("# p\n", encoding="utf-8")
        (proj / "scenes.py").write_text("# p\n", encoding="utf-8")
    elif kind == "k":
        (proj / "src").mkdir()
        (proj / "src" / "render.js").write_text("# k\n", encoding="utf-8")
        (proj / "package.json").write_text('{"type":"module"}\n', encoding="utf-8")
    elif kind == "r":
        (proj / "scripts").mkdir()
        (proj / "scripts" / "render.mjs").write_text("# r\n", encoding="utf-8")
        (proj / "package.json").write_text('{"dependencies":{"remotion":"4.0.539"}}\n', encoding="utf-8")
    elif kind == "hybrid":
        (proj / "src").mkdir()
        (proj / "src" / "render.js").write_text("# k\n", encoding="utf-8")
        (proj / "scripts").mkdir()
        (proj / "scripts" / "render.mjs").write_text("# r\n", encoding="utf-8")
        (proj / "package.json").write_text('{"dependencies":{"remotion":"4.0.539"}}\n', encoding="utf-8")
        (proj / "plan" / "hybrid.json").write_text('{"version":1}\n', encoding="utf-8")
        (proj / "run_all.py").write_text("# p\n", encoding="utf-8")
        (proj / "scenes.py").write_text("# p\n", encoding="utf-8")
    return proj


@pytest.mark.parametrize("kind,expected", [("p", "p"), ("k", "k"), ("r", "r"), ("hybrid", "hybrid")])
def test_detect_engine(tmp_path, kind, expected):
    proj = make_project(tmp_path, kind)
    assert pipeline.detect_engine(proj) == expected


def test_detect_engine_hybrid_wins_over_all_others(tmp_path):
    proj = make_project(tmp_path, "hybrid")
    assert pipeline.detect_engine(proj) == "hybrid"


def test_detect_engine_unknown(tmp_path):
    proj = tmp_path / "empty"
    proj.mkdir()
    assert pipeline.detect_engine(proj) is None


def test_step_order_resume_filter():
    assert pipeline.STEPS.index("mix") < pipeline.STEPS.index("render")
    assert pipeline.STEPS.index("mux") < pipeline.STEPS.index("qa") < pipeline.STEPS.index("gate")
    start = pipeline.STEPS.index("qa")
    assert [s for s in pipeline.STEPS if pipeline.STEPS.index(s) >= start] == ["qa", "gate"]


def test_main_writes_timings_and_stops_on_failure(tmp_path, monkeypatch, capsys):
    proj = make_project(tmp_path, "p")
    calls = []

    def fake_run(cmd, cwd, env=None, timeout=1800, log=None):
        calls.append(cmd)
        return 1 if "vo_length" in str(cmd[1]) else 0

    monkeypatch.setattr(pipeline, "run_cmd", fake_run)
    code = pipeline.main.__wrapped__() if hasattr(pipeline.main, "__wrapped__") else None
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj)])
    code = pipeline.main()
    assert code == 1
    out = capsys.readouterr().out
    assert "PIPELINE FAILED at step 'vo'" in out
    timings = json.loads((proj / "cache" / "pipeline-timings.json").read_text(encoding="utf-8"))
    assert timings["ok"] is False
    assert [s["step"] for s in timings["steps"]] == ["vo"]          # aborted: lint never ran
    assert all(s["status"] in {"PASS", "FAIL"} for s in timings["steps"])
    assert timings["total_ms"] >= 0
    assert (proj / "cache" / "pipeline.log").is_file()


def test_main_dry_run_runs_nothing(tmp_path, monkeypatch, capsys):
    proj = make_project(tmp_path, "k")
    monkeypatch.setattr(pipeline, "run_cmd", lambda *a, **k: pytest.fail("run_cmd called during --dry-run"))
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj), "--dry-run"])
    assert pipeline.main() == 0
    assert "dry-run" in capsys.readouterr().out


def test_main_rejects_unknown_steps(tmp_path, monkeypatch):
    proj = make_project(tmp_path, "p")
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj), "--steps", "vo,bogus"])
    assert pipeline.main() == 2


def test_main_full_run_sequence_and_report(tmp_path, monkeypatch, capsys):
    proj = make_project(tmp_path, "p")
    (proj / "out" / "final_audio.wav").write_bytes(b"fake wav")
    sequence = []

    def fake_run(cmd, cwd, env=None, timeout=1800, log=None):
        joined = " ".join(str(c) for c in cmd)
        if "run_all.py" in joined:
            sequence.append("run_all.py")
            (proj / "out" / "video_only.mp4").write_bytes(b"fake picture")
        elif joined.startswith("/fake/ffmpeg") or " -shortest " in joined:
            sequence.append("ffmpeg")
            (proj / "out" / "master.mp4").write_bytes(b"fake master")
        else:
            for marker in ("vo_length", "reel_lint", "brand_check", "media_qa", "stage_gate"):
                if marker in joined:
                    sequence.append(marker)
                    break
            else:
                sequence.append(joined)
        return 0

    monkeypatch.setattr(pipeline, "run_cmd", fake_run)
    monkeypatch.setattr(pipeline, "_ffmpeg", lambda: "/fake/ffmpeg")
    monkeypatch.setattr(pipeline, "_ffprobe", lambda: "/fake/ffprobe")
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj)])
    assert pipeline.main() == 0
    out = capsys.readouterr().out
    assert "PIPELINE OK" in out
    # mux step ran ffmpeg after the P render; mix short-circuited on the existing wav
    assert sequence[:2] == ["vo_length", "reel_lint"]
    assert "run_all.py" in sequence and "media_qa" in sequence and "stage_gate" in sequence
    timings = json.loads((proj / "cache" / "pipeline-timings.json").read_text(encoding="utf-8"))
    assert timings["ok"] and len(timings["steps"]) == len(pipeline.STEPS)
    assert any("already exists" in s["note"] for s in timings["steps"] if s["step"] == "mix")


def test_draft_is_rejected_for_engines_without_a_scale_knob(tmp_path, monkeypatch, capsys):
    proj = make_project(tmp_path, "r")
    monkeypatch.setattr(pipeline, "_ffmpeg", lambda: "/fake/ffmpeg")
    monkeypatch.setattr(pipeline, "_ffprobe", lambda: "/fake/ffprobe")
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj), "--draft"])
    assert pipeline.main() == 2
    assert "engines P, K and hybrid" in capsys.readouterr().err


def _fake_ffmpeg_probe(monkeypatch):
    monkeypatch.setattr(pipeline, "_ffmpeg", lambda: "/fake/ffmpeg")
    monkeypatch.setattr(pipeline, "_ffprobe", lambda: "/fake/ffprobe")


def test_draft_engine_p_renders_through_run_all_and_never_muxes(tmp_path, monkeypatch, capsys):
    proj = make_project(tmp_path, "p")
    seen = []

    def fake_run(cmd, cwd, env=None, timeout=1800, log=None):
        seen.append({"cmd": " ".join(str(c) for c in cmd), "env": dict(env or {})})
        if "run_all.py" in seen[-1]["cmd"]:
            (proj / "out" / "draft.mp4").write_bytes(b"fake draft")
        return 0

    monkeypatch.setattr(pipeline, "run_cmd", fake_run)
    _fake_ffmpeg_probe(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj), "--draft"])
    assert pipeline.main() == 0

    out = capsys.readouterr().out
    assert "DRAFT · 540x960 @15fps" in out
    assert "draft -> out/draft.mp4" in out
    render_calls = [c for c in seen if "run_all.py" in c["cmd"]]
    assert len(render_calls) == 1
    env = render_calls[0]["env"]
    # run_all.py is the only half-resolution path for engine P: it must be told so.
    assert env["REEL_DRAFT"] == "1"
    assert env["REEL_DIR"] == str(proj)
    assert env["FFMPEG_BIN"] == "/fake/ffmpeg" and env["FFPROBE_BIN"] == "/fake/ffprobe"
    assert not any("ffmpeg" in c["cmd"] for c in seen)  # a draft is never muxed
    timings = json.loads((proj / "cache" / "pipeline-timings.json").read_text(encoding="utf-8"))
    assert [step["step"] for step in timings["steps"]] == ["render"]


def test_draft_engine_p_fails_when_run_all_writes_no_preview(tmp_path, monkeypatch):
    proj = make_project(tmp_path, "p")
    monkeypatch.setattr(pipeline, "run_cmd", lambda *a, **k: 0)
    _fake_ffmpeg_probe(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj), "--draft"])
    assert pipeline.main() == 1


def test_draft_engine_p_keeps_master_env_clean_without_draft(tmp_path, monkeypatch):
    """The master path must stay untouched: no REEL_DRAFT leaking into a normal render."""
    proj = make_project(tmp_path, "p")
    seen = []

    def fake_run(cmd, cwd, env=None, timeout=1800, log=None):
        seen.append({"cmd": " ".join(str(c) for c in cmd), "env": dict(env or {})})
        if "run_all.py" in seen[-1]["cmd"]:
            (proj / "out" / "video_only.mp4").write_bytes(b"fake picture")
        return 0

    monkeypatch.setattr(pipeline, "run_cmd", fake_run)
    _fake_ffmpeg_probe(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj), "--steps", "render"])
    assert pipeline.main() == 0
    render_calls = [c for c in seen if "run_all.py" in c["cmd"]]
    assert render_calls and "REEL_DRAFT" not in render_calls[0]["env"]


def test_draft_renders_only_half_resolution_and_never_muxes(tmp_path, monkeypatch, capsys):
    proj = make_project(tmp_path, "k")
    seen = []

    def fake_run(cmd, cwd, env=None, timeout=1800, log=None):
        joined = " ".join(str(c) for c in cmd)
        seen.append(joined)
        if "src/render.js" in joined:
            (proj / "out" / "Draft.mp4").write_bytes(b"fake draft")
        return 0

    monkeypatch.setattr(pipeline, "run_cmd", fake_run)
    monkeypatch.setattr(pipeline, "_ffmpeg", lambda: "/fake/ffmpeg")
    monkeypatch.setattr(pipeline, "_ffprobe", lambda: "/fake/ffprobe")
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj), "--draft"])
    assert pipeline.main() == 0
    out = capsys.readouterr().out
    assert "DRAFT · 540x960 @15fps" in out
    render_calls = [c for c in seen if "src/render.js" in c]
    assert render_calls and "--fps 15" in render_calls[0] and "--scale 0.5" in render_calls[0]
    assert "--name Draft" in render_calls[0]
    assert (proj / "out" / "draft.mp4").is_file()
    assert not (proj / "out" / "Draft.mp4").exists()  # renamed, one canonical name
    assert not any("ffmpeg" in c for c in seen)  # no mux in a draft
    timings = json.loads((proj / "cache" / "pipeline-timings.json").read_text(encoding="utf-8"))
    assert [step["step"] for step in timings["steps"]] == ["render"]


def test_draft_that_produces_nothing_fails_loudly(tmp_path, monkeypatch):
    proj = make_project(tmp_path, "k")
    monkeypatch.setattr(pipeline, "run_cmd", lambda *a, **k: 0)
    monkeypatch.setattr(pipeline, "_ffmpeg", lambda: "/fake/ffmpeg")
    monkeypatch.setattr(pipeline, "_ffprobe", lambda: "/fake/ffprobe")
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj), "--draft"])
    assert pipeline.main() == 1


@pytest.mark.slow
def test_draft_real_render_is_playable_half_size(tmp_path):
    """One real Chromium render: the preview must be 540x960 at 15fps, not a relabelled master."""
    import shutil
    import subprocess

    toolkit = ROOT / "tools" / "toolkit" / "node_modules" / "playwright-core"
    if not toolkit.is_dir() or not shutil.which("node"):
        pytest.skip("toolkit node_modules missing — run: npm ci --prefix tools/toolkit")
    spec = importlib.util.spec_from_file_location("ttfv_helpers", ROOT / "tools" / "time_to_first_video.py")
    ttfv = importlib.util.module_from_spec(spec)
    sys.modules["ttfv_helpers"] = ttfv
    spec.loader.exec_module(ttfv)
    proj = tmp_path / "draft"
    subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"), "draft", "--engine", "k",
                    "--out", str(proj)], check=True, capture_output=True)
    (proj / "node_modules").symlink_to(ROOT / "tools" / "toolkit" / "node_modules")
    ttfv.write_plan(proj, 1.0)
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "pipeline.py"), str(proj), "--draft"],
                            capture_output=True, text=True, cwd=str(ROOT))
    assert result.returncode == 0, result.stdout + result.stderr
    media = proj / "out" / "draft.mp4"
    assert media.is_file()
    info = ttfv.probe(media)
    assert (info["width"], info["height"]) == (540, 960)
    assert info["duration_s"] == pytest.approx(1.0, abs=0.1)
    assert info["frames"] == "15"


def test_hybrid_draft_is_routed_to_the_preview_file(tmp_path, monkeypatch):
    proj = make_project(tmp_path, "hybrid")
    (proj / "out" / "hybrid-draft.mp4").write_bytes(b"stub")
    calls = []
    monkeypatch.setattr(pipeline, "run_cmd", lambda cmd, *a, **k: calls.append(cmd) or 0)
    monkeypatch.setattr(pipeline.shutil, "which", lambda name: "/fake/node")
    monkeypatch.setattr(pipeline.subprocess, "run",
                        lambda *a, **k: type("R", (), {"returncode": 0,
                                                      "stdout": '{"executablePath": "/c"}',
                                                      "stderr": ""})())
    monkeypatch.setattr(pipeline, "_ffmpeg", lambda: "/fake/ffmpeg")
    monkeypatch.setattr(pipeline, "_ffprobe", lambda: "/fake/ffprobe")
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj), "--engine", "hybrid", "--draft"])
    assert pipeline.main() == 0
    assert "--draft" in calls[0]  # the engine is told, not just the file name
    assert not any("ffmpeg" in part for part in calls[0][:1])  # no mux in a draft


@pytest.mark.slow
def test_hybrid_draft_is_playable_half_size_with_half_the_frames(tmp_path):
    """P base + masked K overlay at 540x960/15fps: same seconds, half the frames, no audio."""
    import shutil
    import subprocess

    toolkit = ROOT / "tools" / "toolkit" / "node_modules" / "playwright-core"
    if not toolkit.is_dir() or not shutil.which("node"):
        pytest.skip("toolkit node_modules missing — run: npm ci --prefix tools/toolkit")
    spec = importlib.util.spec_from_file_location("ttfv_helpers", ROOT / "tools" / "time_to_first_video.py")
    ttfv = importlib.util.module_from_spec(spec)
    sys.modules["ttfv_helpers"] = ttfv
    spec.loader.exec_module(ttfv)
    proj = tmp_path / "hybriddraft"
    subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"), "hybriddraft",
                    "--engine", "hybrid", "--out", str(proj)], check=True, capture_output=True)
    (proj / "node_modules").symlink_to(ROOT / "tools" / "toolkit" / "node_modules")
    beats = proj / "plan" / "beats.json"
    if beats.exists():
        beats.unlink()
    (proj / "plan" / "hybrid.json").write_text(json.dumps({
        "version": 2, "duration_frames": 30, "audio": None,
        "segments": [{"id": "intro", "start_frame": 0, "end_frame": 30,
                      "layers": [{"engine": "p"},
                                 {"engine": "k", "alpha": True, "scenes": ["example"],
                                  "mask": {"type": "rect", "x": 0.3, "y": 0.2, "w": 0.4, "h": 0.6}}]}]}),
        encoding="utf-8")
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "pipeline.py"), str(proj), "--draft"],
                            capture_output=True, text=True, cwd=str(ROOT))
    assert result.returncode == 0, result.stdout + result.stderr
    media = proj / "out" / "hybrid-draft.mp4"
    assert media.is_file()
    info = ttfv.probe(media)
    assert (info["width"], info["height"]) == (540, 960)
    assert info["frames"] == "15"
    assert info["duration_s"] == pytest.approx(1.0, abs=0.1)


def test_scene_cache_rejects_other_engines_and_draft(tmp_path, monkeypatch, capsys):
    proj_p = make_project(tmp_path, "p")
    monkeypatch.setattr(pipeline, "_ffmpeg", lambda: "/fake/ffmpeg")
    monkeypatch.setattr(pipeline, "_ffprobe", lambda: "/fake/ffprobe")
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj_p), "--scene-cache"])
    assert pipeline.main() == 2
    assert "engine K only" in capsys.readouterr().err

    proj_k = make_project(tmp_path, "k")
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj_k), "--scene-cache", "--draft"])
    assert pipeline.main() == 2
    assert "Pick one" in capsys.readouterr().err


def test_scene_cache_renders_through_the_scene_tool_and_keeps_qa(tmp_path, monkeypatch, capsys):
    proj = make_project(tmp_path, "k")
    (proj / "out" / "final_audio.wav").write_bytes(b"fake wav")
    calls = []

    def fake_run(cmd, cwd, env=None, timeout=1800, log=None):
        joined = " ".join(str(c) for c in cmd)
        calls.append(joined)
        if "render_scenes.py" in joined:
            (proj / "out" / "master.mp4").write_bytes(b"fake master")
        return 0

    monkeypatch.setattr(pipeline, "run_cmd", fake_run)
    monkeypatch.setattr(pipeline, "_ffmpeg", lambda: "/fake/ffmpeg")
    monkeypatch.setattr(pipeline, "_ffprobe", lambda: "/fake/ffprobe")
    monkeypatch.setattr(sys, "argv", ["pipeline.py", str(proj), "--scene-cache", "--steps", "render,qa"])
    assert pipeline.main() == 0
    out = capsys.readouterr().out
    assert "SCENE CACHE" in out
    scene_calls = [c for c in calls if "render_scenes.py" in c]
    assert scene_calls and "--out" in scene_calls[0] and "master.mp4" in scene_calls[0]
    assert any("media_qa" in c for c in calls)  # the cached master is still measured
