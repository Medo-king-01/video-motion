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
