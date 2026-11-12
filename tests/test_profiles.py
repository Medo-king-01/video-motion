"""B6 profiles: 12/15/30/60 fps are declarations, not a global switch.

The 30 fps contract stays the default and the 60 fps profile refuses to be applied without an explicit
approval flag, because that go-ahead belongs to the owner.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import profiles  # noqa: E402


def project() -> dict:
    p = json.loads((ROOT / "tests" / "fixtures" / "unified_project" / "basic.json").read_text(encoding="utf-8"))
    p["duration"] = 960_000  # 4 s at 30 fps
    return p


def registry() -> dict:
    return profiles.load_registry()


# ---------------------------------------------------------------- registry
def test_the_registry_is_valid() -> None:
    assert profiles.validate_registry(registry()) == []


def test_the_declared_profiles() -> None:
    reg = registry()
    ids = [p["id"] for p in reg["profiles"]]
    assert ids == ["reel-30", "motion-film-60", "stop-motion-12", "draft-15",
                   "reel-4x5", "reel-1x1", "reel-16x9"]
    ticks = {p["id"]: profiles.frame_ticks(reg, p) for p in reg["profiles"]}
    assert ticks == {"reel-30": 8000, "motion-film-60": 4000, "stop-motion-12": 20000,
                     "draft-15": 16000, "reel-4x5": 8000, "reel-1x1": 8000, "reel-16x9": 8000}
    sizes = {(p["id"], p["width"], p["height"]) for p in reg["profiles"]}
    assert ("reel-4x5", 1080, 1350) in sizes and ("reel-1x1", 1080, 1080) in sizes
    assert ("reel-16x9", 1920, 1080) in sizes


def test_only_60fps_needs_approval() -> None:
    approvals = {p["id"]: p["requiresApproval"] for p in registry()["profiles"]}
    assert approvals == {"reel-30": False, "motion-film-60": True, "stop-motion-12": False,
                         "draft-15": False, "reel-4x5": False, "reel-1x1": False, "reel-16x9": False}


def test_the_table_shows_the_numbers() -> None:
    text = profiles.table(registry())
    assert "reel-30" in text and "motion-film-60" in text and "yes" in text and "20000" in text


@pytest.mark.parametrize(("edit", "code"), [
    (lambda r: r["profiles"].append(dict(r["profiles"][0])), "P02"),
    (lambda r: r["profiles"][0]["fps"].update(num=60, den=2), "P03"),
    (lambda r: r["profiles"][0].update(width=1081), "P03"),
    (lambda r: r["profiles"].pop(0), "P02"),
    (lambda r: r["profiles"][2]["fps"].update(num=7, den=1), "P06"),
    (lambda r: r.update(timebase=250_000), "P06"),
    (lambda r: r["profiles"][1].update(requiresApproval="no"), "P01"),
    (lambda r: r["profiles"][1].update(colour="red"), "P01"),
])
def test_broken_registries_are_refused(edit, code: str) -> None:
    reg = copy.deepcopy(registry())
    edit(reg)
    errors = profiles.validate_registry(reg)
    assert any(error.startswith(code) for error in errors), errors


# ---------------------------------------------------------------- apply
def test_applying_a_profile_never_changes_timing() -> None:
    original = project()
    before = copy.deepcopy(original)
    profiled, report = profiles.apply_profile(original, "stop-motion-12")
    assert original == before, "apply must not mutate its input"
    assert profiled["duration"] == original["duration"]
    assert profiled["tracks"] == original["tracks"]
    assert profiled["timebase"] == original["timebase"]
    assert profiled["profile"] == {"width": 1080, "height": 1920, "fps": {"num": 12, "den": 1}, "sampleRate": 48000}
    assert report == {"profile": "stop-motion-12", "frameTicks": 20000, "framesBefore": 120,
                      "framesAfter": 48, "duration": 960_000, "requiresApproval": False}


def test_the_frame_count_follows_the_profile() -> None:
    _, thirty = profiles.apply_profile(project(), "reel-30")
    _, twelve = profiles.apply_profile(project(), "stop-motion-12")
    _, fifteen = profiles.apply_profile(project(), "draft-15", )
    assert (thirty["framesAfter"], twelve["framesAfter"], fifteen["framesAfter"]) == (120, 48, 60)


def test_applying_is_deterministic() -> None:
    first, first_report = profiles.apply_profile(project(), "draft-15")
    second, second_report = profiles.apply_profile(project(), "draft-15")
    assert first == second and first_report == second_report
    assert first["profile"]["width"] == 540


def test_60fps_needs_an_explicit_approval() -> None:
    with pytest.raises(profiles.ProfileError) as excinfo:
        profiles.apply_profile(project(), "motion-film-60")
    assert excinfo.value.code == "P04"
    approved, report = profiles.apply_profile(project(), "motion-film-60", approval=True)
    assert approved["profile"]["fps"] == {"num": 60, "den": 1}
    assert report["framesAfter"] == 240


def test_unknown_profile_is_refused() -> None:
    with pytest.raises(profiles.ProfileError) as excinfo:
        profiles.apply_profile(project(), "imax-90")
    assert excinfo.value.code == "P02"


def test_an_invalid_project_is_refused_before_profiling() -> None:
    broken = project()
    broken["duration"] = 10  # clips now exceed the project duration
    with pytest.raises(profiles.ProfileError) as excinfo:
        profiles.apply_profile(broken, "reel-30")
    assert excinfo.value.code == "P05"


def test_a_foreign_timebase_is_refused() -> None:
    foreign = project()
    foreign["timebase"] = 480_000
    with pytest.raises(profiles.ProfileError, match="timebase"):
        profiles.apply_profile(foreign, "reel-30")


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "profiles.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=60)


def write_project(tmp_path: Path) -> Path:
    path = tmp_path / "project.json"
    path.write_text(json.dumps(project()), encoding="utf-8")
    return path


def test_cli_list_and_check() -> None:
    listed = run("list")
    assert listed.returncode == 0 and "motion-film-60" in listed.stdout
    checked = run("check")
    assert checked.returncode == 0 and "7 profiles" in checked.stdout


def test_cli_applies_and_reports(tmp_path: Path) -> None:
    source = write_project(tmp_path)
    out = tmp_path / "draft.json"
    result = run("apply", str(source), "draft-15", "-o", str(out))
    assert result.returncode == 0, result.stderr
    assert "120 → 60 frames" in result.stdout
    assert json.loads(out.read_text(encoding="utf-8"))["profile"]["height"] == 960


def test_cli_dry_run_writes_nothing(tmp_path: Path) -> None:
    source = write_project(tmp_path)
    out = tmp_path / "never.json"
    result = run("apply", str(source), "reel-30", "-o", str(out), "--dry-run")
    assert result.returncode == 0
    assert not out.exists()


def test_cli_refuses_60fps_without_approval(tmp_path: Path) -> None:
    source = write_project(tmp_path)
    refused = run("apply", str(source), "motion-film-60", "-o", str(tmp_path / "film.json"))
    assert refused.returncode == 3
    assert "P04" in refused.stderr
    approved = run("apply", str(source), "motion-film-60", "-o", str(tmp_path / "film.json"), "--approval")
    assert approved.returncode == 0


def test_cli_reports_a_missing_project(tmp_path: Path) -> None:
    result = run("apply", str(tmp_path / "gone.json"), "reel-30", "-o", str(tmp_path / "x.json"))
    assert result.returncode == 2
