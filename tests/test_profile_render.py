"""A declared profile now reaches the renderer — the rate, explicitly, and only the rate.

`tools/profiles.py canvas` writes a small `$REEL_CANVAS` document; `layout_p` and `run_all` read it.
Size stays owned by `brand/brand.json`: asking for a different canvas fails at startup instead of
drawing the wrong thing.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
TEMPLATE = ROOT / "medo-motion" / "templates" / "procedural-reels"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TEMPLATE))

import canvas_profile  # noqa: E402
import profiles  # noqa: E402

BASIC = ROOT / "tests" / "fixtures" / "unified_project" / "basic.json"


def project() -> dict:
    return json.loads(BASIC.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- the block
@pytest.mark.parametrize(("profile_id", "size", "fps"), [
    ("reel-30", (1080, 1920), 30),
    ("motion-film-60", (1080, 1920), 60),
    ("stop-motion-12", (1080, 1920), 12),
    ("draft-15", (540, 960), 15),
    ("reel-4x5", (1080, 1350), 30),
    ("reel-1x1", (1080, 1080), 30),
    ("reel-16x9", (1920, 1080), 30),
])
def test_every_profile_has_a_renderer_block(profile_id: str, size: tuple[int, int], fps: int) -> None:
    block = profiles.canvas_for(profile_id, approval=True)
    assert (block["w"], block["h"], block["fps"]) == (*size, fps)
    assert block["profile"] == profile_id
    assert "device scale" in block["note"]


def test_60fps_still_needs_the_owner_flag() -> None:
    with pytest.raises(profiles.ProfileError) as excinfo:
        profiles.canvas_for("motion-film-60")
    assert excinfo.value.code == "P04"
    assert profiles.canvas_for("motion-film-60", approval=True)["fps"] == 60


def test_a_project_block_reports_whether_the_registry_declares_it() -> None:
    block = profiles.canvas_from_project(project())
    assert (block["w"], block["h"], block["fps"], block["declared"]) == (1080, 1920, 30, True)
    assert block["profile"] == "project:project-1"


def test_applying_a_profile_changes_what_the_renderer_gets() -> None:
    profiled, _ = profiles.apply_profile(project(), "stop-motion-12")
    block = profiles.canvas_from_project(profiled)
    assert block["fps"] == 12 and block["declared"] is True
    draft, _ = profiles.apply_profile(project(), "draft-15")
    assert profiles.canvas_from_project(draft)["h"] == 960


def test_a_non_integer_rate_cannot_reach_the_renderer() -> None:
    odd = project()
    odd["profile"]["fps"] = {"num": 30000, "den": 1001}
    assert profiles.validate(odd) == []
    with pytest.raises(profiles.ProfileError) as excinfo:
        profiles.canvas_from_project(odd)
    assert excinfo.value.code == "P07"


def test_an_invalid_project_is_refused() -> None:
    broken = project()
    broken["duration"] = 10
    with pytest.raises(profiles.ProfileError) as excinfo:
        profiles.canvas_from_project(broken)
    assert excinfo.value.code == "P05"


# ---------------------------------------------------------------- env override
def test_no_override_means_the_brand_default() -> None:
    assert canvas_profile.env_fps(30) == 30
    assert canvas_profile.load() == {}


def test_a_valid_override_sets_the_rate(tmp_path: Path) -> None:
    path = tmp_path / "canvas.json"
    path.write_text(json.dumps({"fps": 60}), encoding="utf-8")
    assert canvas_profile.env_fps(30, path) == 60
    assert canvas_profile.env_fps(30, str(path)) == 60


@pytest.mark.parametrize("payload", ["not json", "[]", '{"fps": 0}', '{"fps": true}', '{"fps": "60"}'])
def test_garbage_overrides_never_guess(tmp_path: Path, payload: str) -> None:
    path = tmp_path / "canvas.json"
    path.write_text(payload, encoding="utf-8")
    assert canvas_profile.env_fps(30, path) == 30


def test_a_missing_override_file_is_not_an_error(tmp_path: Path) -> None:
    assert canvas_profile.env_fps(30, tmp_path / "gone.json") == 30


def test_a_half_size_profile_becomes_the_device_scale(tmp_path: Path) -> None:
    path = tmp_path / "canvas.json"
    path.write_text(json.dumps({"profile": "draft-15", "w": 540, "h": 960, "fps": 15}), encoding="utf-8")
    doc = canvas_profile.plan(path=path)
    assert doc["scale"] == 0.5
    assert doc["device"] == (540, 960)
    assert doc["fps"] == 15


def test_a_reshaped_canvas_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "canvas.json"
    path.write_text(json.dumps({"w": 1080, "h": 1080}), encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        canvas_profile.plan(path=path)
    assert "uniform scale" in str(excinfo.value)


def test_a_canvas_bigger_than_the_design_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "canvas.json"
    path.write_text(json.dumps({"w": 2160, "h": 3840}), encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        canvas_profile.plan(path=path)
    assert "larger than" in str(excinfo.value)


def test_a_non_9x16_profile_is_refused_by_the_engine(tmp_path: Path) -> None:
    path = tmp_path / "square.json"
    path.write_text(json.dumps(profiles.canvas_for("reel-1x1")), encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        canvas_profile.plan(path=path)
    assert "uniform scale" in str(excinfo.value)


def test_the_design_size_is_scale_one() -> None:
    doc = canvas_profile.plan()
    assert doc["scale"] == 1.0 and doc["device"] == (1080, 1920) and doc["overridden"] is False


def test_describe_names_the_profile_and_the_scale(tmp_path: Path) -> None:
    path = tmp_path / "canvas.json"
    path.write_text(json.dumps({"profile": "draft-15", "w": 540, "h": 960, "fps": 15}), encoding="utf-8")
    line = canvas_profile.describe(canvas_profile.plan(path=path))
    assert "draft-15" in line and "15 fps" in line and "0.5" in line and "540×960" in line


# ---------------------------------------------------------------- layout_p reads it
def layout_fps(env_canvas: Path | None) -> str:
    env = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(TEMPLATE)}
    if env_canvas is not None:
        env["REEL_CANVAS"] = str(env_canvas)
    result = subprocess.run([sys.executable, "-c", "import layout_p; print(layout_p.FPS)"],
                            cwd=str(TEMPLATE), capture_output=True, text=True, timeout=120, env=env)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_layout_keeps_30_without_an_override() -> None:
    assert layout_fps(None) == "30"


def layout_canvas(env_canvas: Path) -> str:
    env = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(TEMPLATE), "REEL_CANVAS": str(env_canvas)}
    result = subprocess.run([sys.executable, "-c", "import layout_p; print(layout_p.W, layout_p.H, layout_p.FPS)"],
                            cwd=str(TEMPLATE), capture_output=True, text=True, timeout=120, env=env)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_a_half_size_profile_shrinks_the_layout_zones(tmp_path: Path) -> None:
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(profiles.canvas_for("draft-15")), encoding="utf-8")
    assert layout_canvas(path) == "540 960 15"


def test_layout_follows_a_declared_profile(tmp_path: Path) -> None:
    for profile_id, fps in (("motion-film-60", 60), ("stop-motion-12", 12), ("draft-15", 15)):
        path = tmp_path / f"{profile_id}.json"
        path.write_text(json.dumps(profiles.canvas_for(profile_id, approval=True)), encoding="utf-8")
        assert layout_fps(path) == str(fps)


def test_layout_ignores_a_broken_override(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{", encoding="utf-8")
    assert layout_fps(path) == "30"


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "profiles.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=120)


def test_cli_writes_a_canvas_for_a_profile(tmp_path: Path) -> None:
    out = tmp_path / "canvas.json"
    result = run("canvas", "--profile", "draft-15", "-o", str(out))
    assert result.returncode == 0, result.stderr
    block = json.loads(out.read_text(encoding="utf-8"))
    assert (block["w"], block["h"], block["fps"]) == (540, 960, 15)
    assert "540×960 · 15 fps" in result.stdout


def test_cli_refuses_60fps_without_approval(tmp_path: Path) -> None:
    out = tmp_path / "canvas.json"
    refused = run("canvas", "--profile", "motion-film-60", "-o", str(out))
    assert refused.returncode == 3 and "P04" in refused.stderr
    assert not out.exists()
    assert run("canvas", "--profile", "motion-film-60", "-o", str(out), "--approval").returncode == 0


def test_cli_can_take_the_project_instead(tmp_path: Path) -> None:
    out = tmp_path / "canvas.json"
    result = run("canvas", "--project", str(BASIC), "-o", str(out))
    assert result.returncode == 0, result.stderr
    assert json.loads(out.read_text(encoding="utf-8"))["declared"] is True


def test_cli_needs_exactly_one_source(tmp_path: Path) -> None:
    out = tmp_path / "canvas.json"
    assert run("canvas", "-o", str(out)).returncode == 2
    both = run("canvas", "--profile", "reel-30", "--project", str(BASIC), "-o", str(out))
    assert both.returncode == 2


def test_cli_reports_unreadable_input(tmp_path: Path) -> None:
    out = tmp_path / "canvas.json"
    assert run("canvas", "--project", str(tmp_path / "gone.json"), "-o", str(out)).returncode == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    assert run("canvas", "--project", str(bad), "-o", str(out)).returncode == 2
