"""Shared fixtures: import paths and the brand font."""
from __future__ import annotations

import importlib.abc
import importlib.util
import sys
import wave  # noqa: F401  — see below: import it BEFORE any test module touches sys.path
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
ENGINE_P = SKILL / "templates" / "procedural-reels"
FONTS = ROOT / "assets" / "fonts" / "Cairo"


# Import paths at collection time: test modules import the engine directly and we
# never install the studio as a package. Keep helpers after the standard library:
# Python 3.10 wave imports stdlib chunk, not the renderer CLI named chunk.py.
# That is why `wave` is imported above, before any test module edits sys.path: on 3.10
# it does `from chunk import Chunk`, and the engine ships a `chunk.py` CLI that raises
# SystemExit unless it gets START_FRAME END_FRAME. Once `wave` is imported here the
# stdlib module is cached and the engine folder can be on sys.path harmlessly.
# Preserve the existing tools -> scripts -> engine precedence among local helpers.
for _p in (str(ROOT / "tools"), str(SKILL / "scripts"), str(ENGINE_P)):
    if _p not in sys.path:
        sys.path.append(_p)


# `tools/audio_mix.py` is a CLI and `procedural-reels/audio_mix.py` is the library the audio tests
# mean. `tools/` sits above the engine directory on the path set up here, and test modules push their
# own directory to the front while they are being *collected* — test_cover_generator.py inserts
# `tools`, alphabetically after test_audio_mix.py inserts the engine directory. So the first
# `import audio_mix`, which happens inside a test function, could land on the CLI; once that module
# object was cached in sys.modules every later import returned it, and the audio tests failed with
# `module 'audio_mix' has no attribute 'save_sheet'`. Which order pytest picked depended on the
# module set, which is why the full suite could pass while a two-file run failed.
#
# The name is therefore claimed here, while conftest is imported and before pytest collects any test
# module. A finder is registered rather than the module being imported: importing it eagerly would
# pull in numpy and scipy for every test in the suite, including the ones that have nothing to do
# with audio (the fast CI job installs neither scipy nor runs anything but the cover generator).
#
# Only the one colliding name is claimed. Reordering the whole path would also shadow
# `text_direction.py`, which exists in both trees with different contents and is used by
# `reel_lint`, `stage_gate` and `layout_audit_p`.
_ENGINE_OWNED = {"audio_mix": ENGINE_P / "audio_mix.py"}


class _EngineModuleFinder(importlib.abc.MetaPathFinder):
    """Resolve the claimed names from the engine directory, whatever sys.path says."""

    def find_spec(self, fullname, path=None, target=None):
        location = _ENGINE_OWNED.get(fullname)
        if location is None or not location.is_file():
            return None
        return importlib.util.spec_from_file_location(fullname, location)


if not any(isinstance(_f, _EngineModuleFinder) for _f in sys.meta_path):
    _already = sys.modules.get("audio_mix")
    if _already is not None:
        _origin = Path(getattr(_already, "__file__", "") or "").resolve()
        if _origin.parent != ENGINE_P.resolve():
            raise RuntimeError(
                f"'audio_mix' was imported from {_origin} before conftest ran; "
                f"expected it from {ENGINE_P}"
            )
    sys.meta_path.insert(0, _EngineModuleFinder())


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
    # projects/ is a scratch workspace, never a package and never tracked: nothing to do here.
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
