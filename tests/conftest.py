"""Shared fixtures: import paths and the brand font."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
ENGINE_P = SKILL / "templates" / "procedural-reels"
FONTS = ROOT / "assets" / "fonts" / "Cairo"


# Import paths at collection time: test modules import the engine directly and we
# never install the studio as a package.
for _p in (str(ENGINE_P), str(SKILL / "scripts"), str(ROOT / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


@pytest.fixture(scope="session")
def cairo_bold() -> str:
    font = FONTS / "Cairo_800ExtraBold.ttf"
    if not font.is_file():
        pytest.skip("Cairo font missing — run: bash tools/setup.sh")
    return str(font)


@pytest.fixture()
def project(tmp_path):
    """A throw-away engine-P project (fonts copied, no render output)."""
    import shutil

    root = ROOT / "projects"
    root.mkdir(exist_ok=True)
    name = f"_test-{tmp_path.name}"
    proj = root / name
    if proj.exists():
        shutil.rmtree(proj)
    proj.mkdir()
    for f in ENGINE_P.iterdir():
        if f.is_file():
            shutil.copy2(f, proj / f.name)
    font_dir = proj / "assets" / "fonts" / "Cairo"
    font_dir.mkdir(parents=True)
    for f in FONTS.glob("*.ttf"):
        shutil.copy2(f, font_dir / f.name)
    yield proj
    shutil.rmtree(proj, ignore_errors=True)
