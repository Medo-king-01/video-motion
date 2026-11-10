"""Time-to-first-video: the measurement has to be runnable, reproducible, and honest about failures."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import time_to_first_video as ttfv  # noqa: E402

CHROMIUM = ROOT / "tools" / "toolkit" / "node_modules" / "playwright-core"


def test_dry_run_lists_every_phase(capsys: pytest.CaptureFixture[str]) -> None:
    assert ttfv.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    for phase in ttfv.PHASES:
        assert phase in out
    assert "target" in out


@pytest.mark.parametrize("flag,value", [("--seconds", "0"), ("--runs", "0")])
def test_invalid_inputs_are_rejected_before_any_work(flag: str, value: str,
                                                     capsys: pytest.CaptureFixture[str]) -> None:
    assert ttfv.main([flag, value]) == 2
    assert "must be" in capsys.readouterr().err


def test_plan_writes_a_renderable_project(tmp_path: Path) -> None:
    """The plan must satisfy the same gates the renderer enforces: beats + directed text."""
    (tmp_path / "plan").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "data.js").write_text(
        "export const W = 1080, H = 1920, FPS = 30;\n"
        "export const scenes = [\n  { id: 'a', start: 0, end: 9 },\n  { id: 'b', start: 9, end: 20 },\n];\n"
        "export const DURATION = scenes.at(-1).end;\n", encoding="utf-8")
    ttfv.write_plan(tmp_path, 1.5)
    beats = json.loads((tmp_path / "plan" / "beats.json").read_text(encoding="utf-8"))
    assert beats["duration"] == 1.5
    assert [scene["end"] for scene in beats["scenes"]] == [1.5]
    direction = json.loads((tmp_path / "plan" / "text-direction.json").read_text(encoding="utf-8"))
    assert direction["status"] == "directed" and direction["scenes"][0]["scene"] == 1
    data = (tmp_path / "src" / "data.js").read_text(encoding="utf-8")
    assert "id: 'b'" not in data  # the demo scenes are replaced, not appended to
    assert "end: 1.5" in data and "DURATION" in data


def test_a_failed_run_exits_non_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ttfv, "one_run", lambda workdir, seconds, slug: {
        "ok": False, "seconds": 1.0, "phases": {"render": 1.0}, "notes": {},
        "media": {"ok": False}, "project": str(tmp_path), "exit_code": 1,
        "target_seconds": 180.0, "target_met": False,
    })
    monkeypatch.setattr(ttfv, "machine", lambda: {})
    assert ttfv.main([]) == 1


@pytest.mark.slow
def test_real_run_produces_a_playable_mp4(tmp_path: Path) -> None:
    """One second, engine K, real Chromium: the number and the file must both be real."""
    if not CHROMIUM.is_dir():
        pytest.skip("toolkit node_modules missing — run: npm ci --prefix tools/toolkit")
    report_path = tmp_path / "ttfv.json"
    code = ttfv.main(["--seconds", "1", "--json", str(report_path), "--keep-dir", str(tmp_path / "work")])
    assert code == 0, report_path.read_text(encoding="utf-8") if report_path.is_file() else "no report"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    run = report["runs"][0]
    assert run["ok"] and run["media"]["duration_s"] == pytest.approx(1.0, abs=0.05)
    assert run["media"]["width"] == 1080 and run["media"]["height"] == 1920
    assert set(run["phases"]) == set(ttfv.PHASES)
    assert run["seconds"] == pytest.approx(sum(run["phases"].values()), abs=0.05)
    assert Path(run["project"], "out", "master.mp4").is_file()
    assert report["target_met"] is True


def test_docs_quote_the_same_target_as_the_code() -> None:
    """The number in docs/ttfv.md is a promise; keep it equal to TARGET_SECONDS, not to memory."""
    text = (ROOT / "docs" / "ttfv.md").read_text(encoding="utf-8")
    assert f"{ttfv.TARGET_SECONDS:.0f}" in text
