"""Engine K's `lib/art.js` is engine P's drawn sprites, shape for shape.

The static half pins the vocabulary (every sprite, pose, expression, screen and tail engine P has is
in the port, and the parity tool exercises all of them). The slow half draws every sprite with both
engines and holds them to the limits in `tools/art_parity.py`.
"""
from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENGINE_P = ROOT / "medo-motion" / "templates" / "procedural-reels"
ART_JS = ROOT / "medo-motion" / "templates" / "render" / "lib" / "art.js"
sys.path.insert(0, str(ROOT / "tools"))

import art_parity  # noqa: E402

# engine P function -> engine K sprite name
PORTED = {
    "art.laptop": "laptop", "art.desktop": "desktop", "art.icon": "partIcon", "art.person": "person",
    "art.paper_spec": "paperSpec", "art.follow_button": "followButton", "art.cursor": "cursor",
    "lib.sparkle": "sparkle", "lib.pill": "pill", "lib.bill": "bill", "lib.checkmark": "checkmark",
    "lib.crossmark": "crossmark", "lib.bubble": "bubble",
}
CASES = art_parity.cases()


def _js() -> str:
    return ART_JS.read_text(encoding="utf-8")


def _k_names() -> list[str]:
    body = re.search(r"export const ART = \{(.*?)\};", _js(), re.S).group(1)
    return [name.strip() for name in body.replace("\n", " ").split(",") if name.strip()]


def _p_functions(module: str) -> set[str]:
    tree = ast.parse((ENGINE_P / f"{module}.py").read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def test_every_engine_p_sprite_has_a_port():
    assert sorted(_k_names()) == sorted(PORTED.values())
    for dotted in PORTED:
        module, func = dotted.split(".")
        assert func in _p_functions(module), f"{dotted} left engine P; update the port table"


def test_no_public_art_function_is_left_behind():
    """A sprite added to engine P's art.py later must be ported (or listed here) on purpose."""
    public = {name for name in _p_functions("art") if not name.startswith("_")}
    assert public == {dotted.split(".")[1] for dotted in PORTED if dotted.startswith("art.")}


def _pose_tables() -> tuple[dict, dict]:
    """Pose name -> flat list of arm coordinates, read from each engine's source."""
    numbers = lambda text: [int(n) for n in re.findall(r"\d+", text)]  # noqa: E731
    source = (ENGINE_P / "art.py").read_text(encoding="utf-8")
    p = {name: numbers(row) for name, row in re.findall(r"^\s+'(\w+)':(\[\(\[.*\])\s*,?\s*\}?\s*$", source, re.M)}
    k = {name: numbers(row) for name, row in re.findall(r"^  (\w+): (\[\[\[\[.*\]),$", _js(), re.M)}
    return p, k


def test_person_poses_have_engine_p_coordinates():
    p, k = _pose_tables()
    assert len(p) == 7, f"could not read the pose table from art.py: {sorted(p)}"
    assert k == p


def test_person_expressions_match_engine_p():
    source = (ENGINE_P / "art.py").read_text(encoding="utf-8")
    for expr in ("smile", "excited", "frustrated", "confused", "talk1", "talk2", "confident"):
        assert f"'{expr}'" in source and f"'{expr}'" in _js()


def test_parity_cases_cover_every_sprite_and_variant():
    assert {case["art"] for case in CASES} == set(_k_names())
    ids = {case["id"] for case in CASES}
    for pose in _pose_tables()[1]:
        assert f"person-pose-{pose}" in ids
    for kind in ("cpu", "ram", "ssd", "display", "gpu", "battery"):
        assert f"part-{kind}" in ids
    for screen in ("glow", "bad", "blank", "dark"):
        assert f"laptop-{screen}" in ids
    for tail in ("bl", "br", "bc"):
        assert f"bubble-{tail}" in ids
    assert len(ids) == len(CASES)


def test_parity_colours_are_the_brand_palette():
    brand = (ART_JS.parent / "brand.js").read_text(encoding="utf-8")
    for token, (r, g, b) in art_parity.COLOURS.items():
        assert re.search(rf"\b{token}:\s*'#{r:02X}{g:02X}{b:02X}'", brand, re.I), token


def test_art_js_uses_no_colour_outside_the_palette():
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", re.sub(r"//.*", "", _js()))


def test_importing_the_tool_does_not_touch_the_environment():
    """Engine P is loaded only when a render is asked for, never at import."""
    code = ("import os, sys; sys.path.insert(0, 'tools'); before = dict(os.environ); import art_parity; "
            "assert dict(os.environ) == before; assert 'lib' not in sys.modules and 'art' not in sys.modules")
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(ROOT))
    assert done.returncode == 0, done.stderr


def test_reference_sheets_are_published():
    for name in ("sprites.jpg", "scene-presenter.jpg", "scene-card.jpg", "scene-cta.jpg"):
        assert (ROOT / "docs" / "assets" / "art-parity" / name).stat().st_size > 20_000, name


def test_compare_flags_a_moved_and_a_resized_sprite(tmp_path):
    from PIL import Image, ImageDraw

    def disc(folder, box, size=(120, 120)):
        folder.mkdir(exist_ok=True)
        image = Image.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse(box, fill=(203, 39, 27, 255))
        image.save(folder / "x.png")

    disc(tmp_path / "p", (20, 20, 100, 100))
    disc(tmp_path / "same", (20, 20, 100, 100))
    disc(tmp_path / "moved", (28, 20, 108, 100))
    disc(tmp_path / "bigger", (20, 20, 100, 100), size=(124, 120))
    assert art_parity.compare("x", tmp_path / "p", tmp_path / "same")["ok"]
    moved = art_parity.compare("x", tmp_path / "p", tmp_path / "moved")
    assert not moved["ok"] and moved["shape"] < art_parity.MIN_SHAPE
    assert not art_parity.compare("x", tmp_path / "p", tmp_path / "bigger")["ok"]


# ---------------------------------------------------------------- both engines, really drawn
@pytest.fixture(scope="module")
def report(tmp_path_factory):
    if not (ROOT / "tools" / "toolkit" / "node_modules" / "playwright-core").is_dir() or not shutil.which("node"):
        pytest.skip("render toolkit not installed (bash tools/setup.sh)")
    # A subprocess, not `art_parity.run()`: engine P fixes its font and render directory at import,
    # and both would leak into every later test of this session.
    out = tmp_path_factory.mktemp("art-parity")
    done = subprocess.run([sys.executable, str(ROOT / "tools" / "art_parity.py"), "--out", str(out),
                           "--json", str(out / "report.json")], capture_output=True, text=True, cwd=str(ROOT))
    assert done.returncode == 0, (done.stderr or done.stdout)[-1500:]
    return json.loads((out / "report.json").read_text(encoding="utf-8"))


@pytest.mark.slow
@pytest.mark.parametrize("case_id", [case["id"] for case in CASES])
def test_sprite_matches_engine_p(report, case_id):
    row = next(r for r in report["sprites"] if r["id"] == case_id)
    assert row["same_size"], f"{case_id}: P {row['p_size']} vs K {row['k_size']}"
    assert row["ok"], f"{case_id}: shape {row['shape']} diff {row['diff']} (limits {report['limits']})"


@pytest.mark.slow
def test_typical_frames_and_arabic_text_agree(report):
    assert len(report["scenes"]) == 3
    for scene in report["scenes"]:
        assert scene["diff"] < 3.0, scene
        assert scene["changed"] < 0.02, scene
        for item in scene["text_widths"]:      # the two Arabic shapers set the same line
            assert abs(item["p"] - item["k"]) <= max(3, 0.01 * item["p"]), item
