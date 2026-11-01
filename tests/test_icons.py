"""The animated icon layer: one registry, three consumers, palette-locked colours."""
from __future__ import annotations

import json
import re
import subprocess
import sys

import numpy as np
import pytest
from conftest import ROOT, SKILL

ICONS_DIR = SKILL / "icons"
REGISTRY = json.loads((ICONS_DIR / "registry.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((ICONS_DIR / "manifest.json").read_text(encoding="utf-8"))
ICONS_JS = (SKILL / "templates" / "render" / "lib" / "icons.js").read_text(encoding="utf-8")
IDS = [icon["id"] for icon in REGISTRY["icons"]]

sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))


def test_registry_is_sane():
    assert len(IDS) == len(set(IDS)), "duplicate icon ids"
    assert len(IDS) >= 12
    for icon in REGISTRY["icons"]:
        assert icon["ar"] and icon["en"], icon["id"]
        assert icon["anim"]["draw"] > 0 and icon["anim"]["stagger"] >= 0
        assert icon["shapes"], icon["id"]
        for shape in icon["shapes"]:
            assert shape["t"] in {"line", "poly", "rect", "circle", "arc", "dot", "fillrect"}, shape["t"]


def test_generated_files_are_in_sync():
    r = subprocess.run([sys.executable, str(ICONS_DIR / "build.py"), "--check"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stdout + r.stderr


def test_manifest_matches_registry():
    assert [i["id"] for i in MANIFEST["icons"]] == IDS
    assert MANIFEST["grid"] == REGISTRY["grid"]


@pytest.mark.parametrize("icon_id", IDS)
def test_svg_is_animated_and_palette_locked(icon_id):
    svg = (ICONS_DIR / "svg" / f"{icon_id}.svg").read_text(encoding="utf-8")
    assert f'data-icon="{icon_id}"' in svg
    assert "currentColor" in svg and "--icon-accent" in svg
    assert "@keyframes draw" in svg and "pathLength=\"1\"" in svg
    assert not re.search(r"#[0-9A-Fa-f]{6}", svg), "icons must never bake a colour"


def test_engine_k_painter_exposes_every_icon():
    assert "export function drawIcon" in ICONS_JS
    assert "export const ICONS" in ICONS_JS
    for icon_id in IDS:
        assert f'"{icon_id}":' in ICONS_JS, icon_id


def test_engine_p_painter_exposes_every_icon():
    from icons import ICONS, draw_icon, icon_duration  # noqa: PLC0415

    assert sorted(ICONS) == sorted(IDS)
    assert all(icon_duration(i) > 0 for i in IDS)
    frame = np.zeros((64, 64, 3), dtype=np.float32)
    draw_icon(frame, "check-circle", 2.0, 32, 32, size=48, color=(243, 242, 241), accent=(203, 39, 27), loop=False)
    assert frame.max() > 0.1, "icon drew nothing"


def test_engine_p_reveal_grows_with_time():
    from icons import draw_icon  # noqa: PLC0415

    def ink_at(t: float) -> int:
        frame = np.zeros((128, 128, 3), dtype=np.float32)
        frame[:, :] = (46, 36, 35)
        draw_icon(frame, "cpu", t, 64, 64, size=112, color=(243, 242, 241), loop=False)
        return int(((frame[:, :, 0] > 150)).sum())

    assert ink_at(0.0) < ink_at(0.4) < ink_at(2.0)
    assert ink_at(0.0) == 0


def test_sheet_tool_runs(tmp_path):
    out = tmp_path / "sheet.png"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "icons_sheet.py"), "--out", str(out)],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.is_file() and out.stat().st_size > 5_000
