"""The engine's audio library must own the `audio_mix` name, in any collection order.

`tools/audio_mix.py` (a CLI) and `medo-motion/templates/procedural-reels/audio_mix.py` (the library
the audio tests import) share a name, and `tools/` sits above the engine directory on sys.path. Test
modules push their own directory to the front while being collected, so before conftest claimed the
name the library tests passed or failed depending on whether test_cover_generator.py happened to be
collected after test_audio_mix.py — `module 'audio_mix' has no attribute 'save_sheet'`.

These tests fail if that regresses, whichever order pytest happens to run in.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

from conftest import ENGINE_P, ROOT

LIBRARY = (ENGINE_P / "audio_mix.py").resolve()
CLI = (ROOT / "tools" / "audio_mix.py").resolve()


def test_the_bare_name_resolves_to_the_engine_library():
    import audio_mix

    assert Path(audio_mix.__file__).resolve() == LIBRARY
    assert audio_mix.__file__ != str(CLI)
    assert hasattr(audio_mix, "save_sheet"), "the CLI was imported instead of the library"


def test_the_name_survives_a_path_order_that_favours_the_cli():
    """Replay the poisoning order in a fresh process: tools first, then a bare import."""
    script = textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, {str(ROOT / "tools")!r})   # the CLI would win a plain path search
        sys.path.insert(0, {str(ROOT / "tests")!r})
        sys.path.append({str(ENGINE_P)!r})
        import conftest                              # claims the name before anything imports it
        import audio_mix
        print(audio_mix.__file__)
        """
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).resolve() == LIBRARY


def test_the_two_same_named_files_are_not_the_same_module():
    """If the CLI ever re-exported the library the collision would be harmless; it does not."""
    assert LIBRARY.is_file() and CLI.is_file()
    assert LIBRARY != CLI
    assert "def save_sheet" in LIBRARY.read_text(encoding="utf-8")
    assert "save_sheet" not in CLI.read_text(encoding="utf-8")


def test_the_cli_is_still_reachable_as_a_program():
    """The CLI keeps its own identity: tests run it as a process, never import it as `audio_mix`."""
    result = subprocess.run([sys.executable, str(CLI), "--help"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "--sheet" in (result.stdout + result.stderr)


def test_importing_the_name_does_not_drag_in_the_audio_stack():
    """conftest must not import numpy/scipy for tests that have nothing to do with audio."""
    script = textwrap.dedent(
        """
        import sys
        sys.path.insert(0, {tests!r})
        import conftest
        print("scipy" in sys.modules, "numpy" in sys.modules)
        """.format(tests=str(ROOT / "tests"))
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["False", "False"], result.stdout
