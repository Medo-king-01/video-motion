"""Shared fixtures: import paths and the brand font."""
from __future__ import annotations

import atexit
import functools
import importlib.abc
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave  # noqa: F401  — see below: import it BEFORE any test module touches sys.path
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
ENGINE_P = SKILL / "templates" / "procedural-reels"
SHARED_PY = ROOT / "shared" / "py"  # audio + rhythm: the editable copy (engine P ships a synced one)
ENGINE_R = SKILL / "templates" / "remotion"
FONTS = ROOT / "assets" / "fonts" / "Cairo"
TOOLS = ROOT / "tools"


# Import paths at collection time: test modules import the engine directly and we
# never install the studio as a package. Keep helpers after the standard library:
# Python 3.10 wave imports stdlib chunk, not the renderer CLI named chunk.py.
# That is why `wave` is imported above, before any test module edits sys.path: on 3.10
# it does `from chunk import Chunk`, and the engine ships a `chunk.py` CLI that raises
# SystemExit unless it gets START_FRAME END_FRAME. Once `wave` is imported here the
# stdlib module is cached and the engine folder can be on sys.path harmlessly.
# Preserve the existing tools -> scripts -> engine precedence among local helpers.
for _p in (str(ROOT / "tools"), str(SKILL / "scripts"), str(SHARED_PY), str(ENGINE_P)):
    if _p not in sys.path:
        sys.path.append(_p)


# `tools/audio_mix.py` is a CLI and `shared/py/audio_mix.py` is the library the audio tests
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
_ENGINE_OWNED = {"audio_mix": SHARED_PY / "audio_mix.py"}


class _EngineModuleFinder(importlib.abc.MetaPathFinder):
    """Resolve the claimed names from `shared/py`, whatever sys.path says."""

    def find_spec(self, fullname, path=None, target=None):
        location = _ENGINE_OWNED.get(fullname)
        if location is None or not location.is_file():
            return None
        return importlib.util.spec_from_file_location(fullname, location)


if not any(isinstance(_f, _EngineModuleFinder) for _f in sys.meta_path):
    _already = sys.modules.get("audio_mix")
    if _already is not None:
        _origin = Path(getattr(_already, "__file__", "") or "").resolve()
        if _origin.parent != SHARED_PY.resolve():
            raise RuntimeError(
                f"'audio_mix' was imported from {_origin} before conftest ran; "
                f"expected it from {SHARED_PY}"
            )
    sys.meta_path.insert(0, _EngineModuleFinder())


# ── environment guards ────────────────────────────────────────────────────────
# The K/R renderers need a Node toolkit (`tools/toolkit/`) plus a Node binary.
# A Python-only checkout (or a fresh clone before `npm ci`) must *skip* the browser
# tests with an actionable message, not fail them: the audit counted 8 red tests
# on a machine that had only installed the Python side of the studio.
TOOLKIT = ROOT / "tools" / "toolkit"


def toolkit_missing_reason() -> str | None:
    """Why the shared render toolkit cannot run here, or None when it is ready."""
    import shutil

    if shutil.which("node") is None:
        return "node is not installed"
    if not (TOOLKIT / "node_modules" / "playwright-core").is_dir():
        return "K toolkit not installed — run: npm ci --prefix tools/toolkit"
    if not (TOOLKIT / "node_modules" / "@sparticuz" / "chromium").is_dir():
        return "bundled Chromium missing — run: npm ci --prefix tools/toolkit"
    return None


_TOOLKIT_REASON: str | None = toolkit_missing_reason()
requires_toolkit = pytest.mark.skipif(_TOOLKIT_REASON is not None, reason=_TOOLKIT_REASON or "")


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


# --- Remotion temp isolation ---------------------------------------------------
#
# Remotion names its webpack bundle output after the entry point (`src/index.ts`), not after the
# project, so two projects built at the same time resolve to the same /tmp/remotion-webpack-bundle-*
# directory. Under `pytest -n 2` that collides: one process finishes and deletes the directory while
# the other is still serving it ("The requested path .../index.html could not be found"), or webpack
# exits reporting "The bundler completed without emitting bundle.js". Both were seen intermittently
# only in parallel runs, and both disappear once each test process owns its TMPDIR.


@functools.lru_cache(maxsize=1)
def remotion_tmpdir() -> Path:
    """One scratch TMPDIR per test process, so parallel workers never share a bundle directory."""
    path = Path(tempfile.mkdtemp(prefix=f"medo-remotion-{os.getpid()}-"))
    atexit.register(shutil.rmtree, path, ignore_errors=True)
    return path


def remotion_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """`base` (usually os.environ) plus the per-process temp dirs Remotion's bundler reads."""
    env = dict(os.environ if base is None else base)
    tmp = str(remotion_tmpdir())
    env.update({"TMPDIR": tmp, "TMP": tmp, "TEMP": tmp})
    return env


# --- Fixed Stage suite infrastructure -----------------------------------------
#
# The Chromium/Remotion runtimes are expensive and were duplicated across three test modules when
# the category A-G file was split. They live here so the modules can stay about one concern each,
# and they are session-scoped: splitting one module into three must not mean three `npm ci` runs and
# three browser boots per CI job. Only the Fixed Stage modules request them, so everything else pays
# nothing.


@pytest.fixture(scope="session")
def _chromium_env():
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    chrom_proc = subprocess.run(
        ["node", str(TOOLS / "chromium.mjs"), "--json"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if chrom_proc.returncode != 0:
        pytest.skip(f"Chromium unavailable: {chrom_proc.stderr}")
    chrom = json.loads(chrom_proc.stdout)
    env = remotion_env(
        {
            **os.environ,
            "PATH": f"{ROOT / 'tools' / 'bin'}:{ROOT / '.venv' / 'bin'}:{os.environ.get('PATH', '')}",
            "MEDO_TOOLKIT": str(ROOT / "tools" / "toolkit"),
            "MEDO_CHROMIUM": chrom["executablePath"],
            "REMOTION_BROWSER_EXECUTABLE": chrom["executablePath"],
        }
    )
    if chrom.get("args"):
        env["REMOTION_CHROMIUM_ARGS"] = " ".join(chrom["args"])
    if chrom.get("libraryPath"):
        env["LD_LIBRARY_PATH"] = ":".join(
            [p for p in (chrom["libraryPath"], env.get("LD_LIBRARY_PATH")) if p]
        )
    return chrom, env


@pytest.fixture
def _cleanup_stage_tmp(request):
    """Reclaim multi-hundred-MB scaffolded assets/fonts/bundles right after each test
    so multi-pass CI jobs (`ci.sh` + `selftest.py --remotion --hybrid`) never hit ENOSPC."""
    tmp_root = Path(tempfile.gettempdir())
    before_bundles = set(tmp_root.glob("remotion-webpack-bundle-*"))
    yield
    tp = request.node.funcargs.get("tmp_path")
    if isinstance(tp, Path) and tp.is_dir():
        for child in tp.iterdir():
            if child.is_symlink():
                child.unlink(missing_ok=True)
            elif child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
    for leaked in set(tmp_root.glob("remotion-webpack-bundle-*")) - before_bundles:
        shutil.rmtree(leaked, ignore_errors=True)


@pytest.fixture(scope="session")
def _remotion_runtime(_chromium_env, tmp_path_factory):
    _chrom, env = _chromium_env
    env_mods = os.environ.get("MEDO_REMOTION_TEST_NODE_MODULES")
    owned_deps_dir: Path | None = None
    if env_mods and Path(env_mods).is_dir():
        modules_dir = Path(env_mods).resolve()
    else:
        if shutil.which("npm") is None:
            pytest.skip("npm is not installed and MEDO_REMOTION_TEST_NODE_MODULES is unset")
        owned_deps_dir = tmp_path_factory.mktemp("remotion_stage_deps")
        shutil.copy2(ENGINE_R / "package.json", owned_deps_dir / "package.json")
        shutil.copy2(ENGINE_R / "package-lock.json", owned_deps_dir / "package-lock.json")
        ci_res = subprocess.run(
            ["npm", "ci", "--prefer-offline", "--no-audit", "--no-fund"],
            cwd=owned_deps_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if ci_res.returncode != 0:
            shutil.rmtree(owned_deps_dir, ignore_errors=True)
            pytest.skip(f"Remotion npm ci unavailable offline: {ci_res.stderr[:240]}")
        modules_dir = owned_deps_dir / "node_modules"
    try:
        yield modules_dir, env
    finally:
        if owned_deps_dir is not None:
            shutil.rmtree(owned_deps_dir, ignore_errors=True)
