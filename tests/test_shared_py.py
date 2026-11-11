"""`shared/py/` is the one editable copy of the audio + rhythm libraries.

The tools import it; engine P ships byte-identical copies so a scaffolded project stays
self-contained. These tests pin the set, the sync gate, and the direction of the dependency:
no tool may reach into the engine-P template for audio or rhythm any more.
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import ENGINE_P, ROOT, SHARED_PY

SHARED = ("audio_engine.py", "audio_mix.py", "beat.py", "music.py", "sfx.py")
SCRIPT = ROOT / "tools" / "sync_shared_py.py"

spec = importlib.util.spec_from_file_location("sync_shared_py", SCRIPT)
sync_shared_py = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_shared_py)


def test_the_shared_set_is_exactly_audio_and_rhythm():
    assert tuple(sync_shared_py.source_files()) == SHARED


def test_the_repository_is_in_sync():
    assert sync_shared_py.drift() == []
    result = subprocess.run([sys.executable, str(SCRIPT), "--check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("name", SHARED)
def test_every_shared_file_is_byte_identical_in_engine_p(name):
    assert (ENGINE_P / name).read_bytes() == (SHARED_PY / name).read_bytes()


@pytest.mark.parametrize("name", SHARED)
def test_shared_modules_need_nothing_from_the_engine(name):
    """They import only each other, the standard library, numpy and scipy — no drawing code."""
    engine_only = {p.stem for p in ENGINE_P.glob("*.py")} - {Path(n).stem for n in SHARED}
    imported = set(re.findall(r"^(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)",
                              (SHARED_PY / name).read_text(encoding="utf-8"), re.M))
    assert not imported & engine_only, f"{name} imports engine-P modules: {sorted(imported & engine_only)}"


def test_transition_cues_keep_their_sounds_without_engine_p():
    """`sfx.py` asks engine P's `transition.py` when it can; alone, it must read the catalogue."""
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import sfx; "
            "print(sfx.cues_for_transitions([{'t': 1.0, 'name': 'wipe'}, {'t': 2.0, 'name': 'flash'}]))")
    result = subprocess.run([sys.executable, "-c", code, str(SHARED_PY)], capture_output=True, text=True,
                            cwd=str(ROOT.parent))
    assert result.returncode == 0, result.stderr
    assert "'whoosh'" in result.stdout and "'impact'" in result.stdout


def test_shared_modules_import_without_the_engine_on_the_path():
    code = ("import sys; sys.path.insert(0, sys.argv[1]); "
            "import audio_engine, audio_mix, beat, music, sfx; "
            "print(len(music.preset_names()), len(sfx.CATALOG), music.PRESETS_PATH)")
    result = subprocess.run([sys.executable, "-c", code, str(SHARED_PY)], capture_output=True, text=True,
                            cwd=str(ROOT.parent))
    assert result.returncode == 0, result.stderr
    presets, sounds, path = result.stdout.split(maxsplit=2)
    assert int(presets) > 0 and int(sounds) > 0
    assert Path(path.strip()) == ROOT / "medo-motion" / "motion" / "music-presets.json"


def test_the_engine_copy_still_finds_the_music_vocabulary():
    code = "import sys; sys.path.insert(0, sys.argv[1]); import music; print(music.PRESETS_PATH)"
    result = subprocess.run([sys.executable, "-c", code, str(ENGINE_P)], capture_output=True, text=True)
    assert Path(result.stdout.strip()) == ROOT / "medo-motion" / "motion" / "music-presets.json"


@pytest.mark.parametrize("tool, modules", [
    ("audio_mix", ("audio_engine", "audio_mix", "sfx")),
    ("music_kit", ("audio_engine", "music")),
    ("sfx_kit", ("sfx",)),
])
def test_tools_load_audio_from_shared_py(tool, modules):
    names = ", ".join(modules)
    code = (f"import runpy, sys; sys.argv=['x', '--help']\n"
            f"try:\n    runpy.run_path({str(ROOT / 'tools' / (tool + '.py'))!r}, run_name='__main__')\n"
            f"except SystemExit:\n    pass\n"
            f"import {names}\n"
            f"print('|'.join(m.__file__ for m in ({names},)))")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(ROOT))
    assert result.returncode == 0, result.stderr
    origins = result.stdout.strip().splitlines()[-1].split("|")
    assert all(Path(origin).parent == SHARED_PY for origin in origins), origins


def test_pipeline_hashes_the_shared_audio_sources():
    text = (ROOT / "tools" / "pipeline.py").read_text(encoding="utf-8")
    block = text[text.index("MIX_CODE = ("):text.index(")", text.index("MIX_CODE = ("))]
    assert block.count('"shared" / "py"') == 4 and "procedural-reels" not in block


def _mirror(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(SHARED_PY, root / "shared" / "py", ignore=shutil.ignore_patterns("__pycache__"))
    target = root / "medo-motion" / "templates" / "procedural-reels"
    target.mkdir(parents=True)
    for name in SHARED:
        shutil.copy2(SHARED_PY / name, target / name)
    return root


def test_check_reports_drift_and_write_repairs_it(tmp_path):
    root = _mirror(tmp_path)
    copy = root / "medo-motion" / "templates" / "procedural-reels" / "beat.py"
    copy.write_text(copy.read_text(encoding="utf-8") + "# hand edit\n", encoding="utf-8")
    assert any(line.startswith("drift:") and "beat.py" in line for line in sync_shared_py.drift(root))
    assert sync_shared_py.sync(root, write=False) == 1
    assert sync_shared_py.sync(root, write=True) == 0
    assert sync_shared_py.drift(root) == []


def test_missing_copy_is_reported(tmp_path):
    root = _mirror(tmp_path)
    (root / "medo-motion" / "templates" / "procedural-reels" / "sfx.py").unlink()
    assert any(line.startswith("missing:") for line in sync_shared_py.drift(root))
