"""Engine K and R canvases: a uniform device downscale of the 1080×1920 design space, or a refusal by name."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import canvas_engines  # noqa: E402
import profiles  # noqa: E402

BRAND_CANVAS = canvas_engines.design()


def document(profile_id: str, *, approval: bool = False) -> dict:
    return profiles.canvas_for(profile_id, approval=approval)


# ---------------------------------------------------------------- resolve
def test_the_brand_canvas_needs_no_override() -> None:
    plan = canvas_engines.resolve({"profile": "brand", "w": 1080, "h": 1920, "fps": 30})
    assert plan["scale"] == 1 and plan["device"] == (1080, 1920)
    assert plan["k"] == [] and plan["r"]["scale"] == 1


def test_a_half_size_draft_becomes_a_k_scale_and_an_r_canvas() -> None:
    plan = canvas_engines.resolve(document("draft-15"))
    assert plan["device"] == (540, 960) and plan["scale"] == 0.5 and plan["fps"] == 15
    assert plan["k"] == ["--scale", "0.5"]
    assert plan["r"] == {"width": 540, "height": 960, "scale": 0.5, "fps": 15}


def test_k_arguments_are_exactly_what_the_renderer_takes() -> None:
    assert canvas_engines.k_args(document("reel-30")) == []
    assert canvas_engines.k_args(document("draft-15")) == ["--scale", "0.5"]


def test_a_reshape_is_refused_by_shape() -> None:
    square = document("reel-1x1")
    with pytest.raises(canvas_engines.CanvasError) as excinfo:
        canvas_engines.resolve(square)
    assert excinfo.value.code == "X02" and "1080×1080" in excinfo.value.message
    assert "not a uniform scale" in excinfo.value.message


def test_an_upscale_is_refused() -> None:
    with pytest.raises(canvas_engines.CanvasError) as excinfo:
        canvas_engines.resolve({"w": 2160, "h": 3840, "fps": 30})
    assert excinfo.value.code == "X03" and "larger" in excinfo.value.message


def test_three_quarter_size_is_allowed_but_an_odd_buffer_is_not() -> None:
    plan = canvas_engines.resolve({"w": 810, "h": 1440, "fps": 30})
    assert plan["scale"] == 0.75 and plan["k"] == ["--scale", "0.75"]
    with pytest.raises(canvas_engines.CanvasError) as excinfo:
        canvas_engines.resolve({"w": 9, "h": 16, "fps": 30})  # uniform, but odd for 4:2:0
    assert excinfo.value.code == "X04"


def test_a_malformed_document_is_refused() -> None:
    with pytest.raises(canvas_engines.CanvasError) as excinfo:
        canvas_engines.resolve({"w": "wide", "h": 1920, "fps": 30})
    assert excinfo.value.code == "X01"


# ---------------------------------------------------------------- engine R file
def test_the_generated_canvas_file_carries_size_scale_and_rate() -> None:
    source = canvas_engines.r_source(document("draft-15"))
    assert "DESIGN = {width: 1080, height: 1920}" in source
    assert "CANVAS = {width: 540, height: 960, scale: 0.5, fps: 15}" in source
    assert "canvas_engines.py" in source


def test_apply_writes_a_file_that_checks_clean(tmp_path: Path) -> None:
    target = canvas_engines.apply(document("draft-15"), src=tmp_path)
    assert target == tmp_path / "canvas.ts" and target.is_file()
    assert canvas_engines.check(target) == []
    assert "540" in target.read_text(encoding="utf-8")


@pytest.mark.parametrize("edit", [
    lambda t: t.replace("width: 540", "width: 640"),
    lambda t: t.replace("scale: 0.5", "scale: 0.4"),
    lambda t: t.replace("fps: 15", "fps: 0"),
    lambda t: t.replace("CANVAS =", "canvas ="),
])
def test_a_tampered_canvas_file_is_caught(tmp_path: Path, edit) -> None:
    target = canvas_engines.apply(document("draft-15"), src=tmp_path)
    target.write_text(edit(target.read_text(encoding="utf-8")), encoding="utf-8")
    assert canvas_engines.check(target) != []


def test_the_shipped_template_canvas_is_the_brand_canvas() -> None:
    assert canvas_engines.check() == []
    source = canvas_engines.CANVAS_FILE.read_text(encoding="utf-8")
    assert f"width: {BRAND_CANVAS['width']}" in source and f"height: {BRAND_CANVAS['height']}" in source


def test_engine_r_root_uses_the_generated_canvas() -> None:
    root = (ROOT / "medo-motion" / "templates" / "remotion" / "src" / "Root.tsx").read_text(encoding="utf-8")
    assert "from './canvas'" in root
    assert "width={CANVAS.width}" in root and "height={CANVAS.height}" in root
    assert "scale(${CANVAS.scale})" in root


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "canvas_engines.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=120)


def test_cli_prints_the_k_arguments(tmp_path: Path) -> None:
    path = tmp_path / "canvas.json"
    path.write_text(json.dumps(document("draft-15")), encoding="utf-8")
    result = run("resolve", str(path), "--engine", "k")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "engine K · --scale 0.5 · 15 fps"


def test_cli_refuses_a_square_profile(tmp_path: Path) -> None:
    path = tmp_path / "canvas.json"
    path.write_text(json.dumps(document("reel-1x1")), encoding="utf-8")
    assert run("resolve", str(path)).returncode == 1


def test_cli_reports_a_missing_document(tmp_path: Path) -> None:
    assert run("resolve", str(tmp_path / "gone.json")).returncode == 2
