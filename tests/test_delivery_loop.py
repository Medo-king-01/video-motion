"""The delivery loop: edit in the session (or review a cut plan), then hand out an EDL.

Two doors into the same exporter — `timeline_session.export` and `cut_plan edl` — so the EDL always
describes the current edit and never a copied list.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import cut_plan  # noqa: E402
import edl_export  # noqa: E402
import timeline_session  # noqa: E402

BASIC = ROOT / "tests" / "fixtures" / "unified_project" / "basic.json"


def project() -> dict:
    return json.loads(BASIC.read_text(encoding="utf-8"))


def session() -> timeline_session.Session:
    return timeline_session.Session(project())


def media_report(fps: int = 30, frames: int = 90, duration: float = 3.0) -> dict:
    deltas = [round(0.4 + (i % 3) * 0.05, 3) for i in range(frames - 1)]
    deltas[29], deltas[59] = 75.7, 101.1
    return {
        "version": 1,
        "source": {"name": "clip.mp4", "sha256": "a3" * 32, "bytes": 4096},
        "video": {"width": 160, "height": 120, "fps": fps, "duration": duration, "frames": frames,
                  "vfr": False, "codec": "mpeg4", "container": "mp4"},
        "sampling": {"grid": [16, 9], "decoded": frames, "step": 1, "maxFrames": 7200},
        "deltas": deltas,
    }


# ---------------------------------------------------------------- session → EDL
def test_a_session_exports_its_own_edit() -> None:
    text, manifest = session().to_edl()
    assert text.startswith("TITLE: Example")
    assert manifest["totals"]["events"] == 1
    assert edl_export.validate_manifest(manifest) == []
    assert edl_export.parse_edl(text)[0]["reel"] == "SHOT"


def test_an_edit_changes_the_edl_not_the_other_way_round() -> None:
    s = session()
    _, before = s.to_edl()
    s.apply({"op": "trim", "clip": "c1", "start": 0, "end": 240_000})
    _, after = s.to_edl()
    assert before["events"][0]["recordOut"] == 480_000
    assert after["events"][0]["recordOut"] == 240_000
    assert after["events"][0]["recordOutTc"] == "00:00:01:00"


def test_a_refused_project_is_a_session_error() -> None:
    data = project()
    data["tracks"].append({"id": "t1", "kind": "text", "enabled": True, "clips": []})
    s = timeline_session.Session(data)
    with pytest.raises(timeline_session.SessionError) as excinfo:
        s.to_edl()
    assert excinfo.value.code == "T06"
    assert "E05" in excinfo.value.message


def test_export_writes_the_edl_and_its_sidecar(tmp_path: Path) -> None:
    out = tmp_path / "out" / "reel.edl"
    manifest = session().export_edl(out)
    assert out.exists() and (tmp_path / "out" / "reel.edl.json").exists()
    assert json.loads((tmp_path / "out" / "reel.edl.json").read_text(encoding="utf-8")) == manifest
    assert edl_export.parse_edl(out.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- plan → EDL
def test_kept_cuts_become_events_in_order() -> None:
    plan = cut_plan.build_plan(media_report())
    plan["cuts"][1]["keep"] = False
    text, manifest = edl_export.build_from_plan(plan)
    assert [e["clipId"] for e in manifest["events"]] == ["cut-01", "cut-03"]
    assert manifest["events"][0]["recordIn"] == 0
    assert manifest["events"][1]["recordIn"] == manifest["events"][0]["recordOut"]
    assert manifest["totals"]["durationTc"] == "00:00:02:00"
    assert edl_export.validate_manifest(manifest) == []
    assert "* CLIP cut-03" in text


def test_rejecting_everything_leaves_nothing_to_deliver() -> None:
    plan = cut_plan.build_plan(media_report())
    for cut in plan["cuts"]:
        cut["keep"] = False
    with pytest.raises(edl_export.EdlError) as excinfo:
        edl_export.build_from_plan(plan)
    assert excinfo.value.code == "E05"


def test_non_integer_fps_is_refused() -> None:
    plan = cut_plan.build_plan(media_report())
    plan["source"]["fps"] = 29.97
    with pytest.raises(edl_export.EdlError) as excinfo:
        edl_export.build_from_plan(plan)
    assert excinfo.value.code == "E02"


def test_a_float_integer_fps_from_a_plan_is_accepted() -> None:
    plan = cut_plan.build_plan(media_report())
    plan["source"]["fps"] = 25.0
    _, manifest = edl_export.build_from_plan(plan)
    assert manifest["fps"] == 25 and manifest["frameTicks"] == 9600


def test_a_cut_that_collapses_to_zero_frames_is_refused() -> None:
    plan = cut_plan.build_plan(media_report())
    plan["cuts"][0]["out"] = plan["cuts"][0]["in"] + 0.001
    with pytest.raises(edl_export.EdlError) as excinfo:
        edl_export.build_from_plan(plan)
    assert excinfo.value.code == "E04"


@pytest.mark.parametrize("mutate", [
    lambda plan: plan.update(version=2),
    lambda plan: plan.pop("settings"),
    lambda plan: plan["cuts"][0].update(keep="yes"),
    lambda plan: plan["cuts"][0].update(out=plan["cuts"][0]["in"]),
])
def test_broken_plans_are_refused(mutate) -> None:
    plan = cut_plan.build_plan(media_report())
    mutate(plan)
    with pytest.raises(edl_export.EdlError) as excinfo:
        edl_export.build_from_plan(plan)
    assert excinfo.value.code in {"E01", "E04"}


def test_plan_export_is_deterministic() -> None:
    plan = cut_plan.build_plan(media_report())
    first = edl_export.build_from_plan(plan)
    second = edl_export.build_from_plan(plan)
    assert first == second


def test_more_than_999_kept_cuts_are_refused() -> None:
    plan = cut_plan.build_plan(media_report())
    plan["cuts"] = [{"id": f"cut-{i:04d}", "in": 0.0, "out": 1.0, "keep": True,
                     "reason": "synthetic", "score": 0.0} for i in range(1000)]
    with pytest.raises(edl_export.EdlError) as excinfo:
        edl_export.build_from_plan(plan)
    assert excinfo.value.code == "E07"


# ---------------------------------------------------------------- CLI doors
def run(module: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / module), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=120)


def test_cli_export_and_check(tmp_path: Path) -> None:
    edl = tmp_path / "reel.edl"
    result = run("timeline_session.py", "export", str(BASIC), "-o", str(edl))
    assert result.returncode == 0, result.stderr
    assert "1 events" in result.stdout
    checked = run("edl_export.py", "check", str(tmp_path / "reel.edl.json"), "--edl", str(edl))
    assert checked.returncode == 0, checked.stderr


def test_cli_export_refuses_a_text_track(tmp_path: Path) -> None:
    data = project()
    data["tracks"].append({"id": "t1", "kind": "text", "enabled": True, "clips": []})
    path = tmp_path / "project.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    edl = tmp_path / "x.edl"
    result = run("timeline_session.py", "export", str(path), "-o", str(edl))
    assert result.returncode == 1 and "T06" in result.stderr
    assert not edl.exists()


def test_cli_script_can_export_after_editing(tmp_path: Path) -> None:
    script = tmp_path / "edit.json"
    script.write_text(json.dumps({"commands": [{"op": "trim", "clip": "c1", "start": 0, "end": 160_000}],
                                  "frames": []}), encoding="utf-8")
    out = tmp_path / "edited.json"
    edl = tmp_path / "edited.edl"
    result = run("timeline_session.py", "script", str(BASIC), str(script), "-o", str(out), "--edl", str(edl))
    assert result.returncode == 0, result.stderr
    manifest = json.loads(Path(str(edl) + ".json").read_text(encoding="utf-8"))
    assert manifest["events"][0]["recordOut"] == 160_000
    assert manifest["events"][0]["recordOutTc"] == "00:00:00:20"


def test_cli_cut_plan_edl(tmp_path: Path) -> None:
    media = tmp_path / "media-report.json"
    media.write_text(json.dumps(media_report()), encoding="utf-8")
    plan = tmp_path / "cut-plan.json"
    built = run("cut_plan.py", "build", str(media), "-o", str(plan))
    assert built.returncode == 0, built.stderr
    edl = tmp_path / "plan.edl"
    result = run("cut_plan.py", "edl", str(plan), "-o", str(edl))
    assert result.returncode == 0, result.stderr
    assert "3 kept cuts" in result.stdout
    checked = run("edl_export.py", "check", str(tmp_path / "plan.edl.json"), "--edl", str(edl))
    assert checked.returncode == 0, checked.stderr
    assert edl.read_text(encoding="utf-8").count("\n001  ")


def test_cli_cut_plan_refuses_an_invalid_plan(tmp_path: Path) -> None:
    plan = cut_plan.build_plan(media_report())
    plan["cuts"][0]["out"] = 99.0
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    edl = tmp_path / "bad.edl"
    result = run("cut_plan.py", "edl", str(path), "-o", str(edl))
    assert result.returncode == 1
    assert not edl.exists()
