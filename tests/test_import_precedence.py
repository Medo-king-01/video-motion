"""The engine's audio library must own the `audio_mix` name, in any collection order.

`tools/audio_mix.py` (a CLI) and `shared/py/audio_mix.py` (the library
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

from conftest import ENGINE_P, ROOT, SHARED_PY

LIBRARY = (SHARED_PY / "audio_mix.py").resolve()
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


def _finder():
    from conftest import _EngineModuleFinder

    return next(f for f in sys.meta_path if isinstance(f, _EngineModuleFinder))


def test_the_finder_claims_only_the_one_colliding_name():
    """It must be a targeted claim, not a general redirect: everything else resolves as before."""
    finder = _finder()
    probes = ["audio_mix", "audio_mix.extra", "audio_engine", "music", "sfx", "text_direction",
              "media_bin", "json", "wave", "chunk", "numpy", "pytest", "audio_mix_kit"]
    claimed = [name for name in probes if finder.find_spec(name, None, None) is not None]
    assert claimed == ["audio_mix"]


def test_a_correctly_loaded_module_is_never_replaced():
    """sys.modules is consulted before meta_path, so a second import returns the same object."""
    import audio_mix

    finder = _finder()
    calls = []
    original = type(finder).find_spec

    def recording(self, fullname, path=None, target=None):
        calls.append(fullname)
        return original(self, fullname, path, target)

    type(finder).find_spec = recording
    try:
        import audio_mix as second
    finally:
        type(finder).find_spec = original

    assert second is audio_mix, "the finder handed back a different module object"
    assert calls == [], f"the finder was consulted for an already-imported module: {calls}"


def test_a_wrong_module_cached_before_conftest_is_an_error_not_a_silent_replace():
    """If something did poison the name first, registration must fail loudly instead of patching over it."""
    script = textwrap.dedent(
        f"""
        import importlib.util, sys
        sys.path.insert(0, {str(ROOT / "tests")!r})
        spec = importlib.util.spec_from_file_location("audio_mix", {str(CLI)!r})
        module = importlib.util.module_from_spec(spec)
        sys.modules["audio_mix"] = module          # the CLI, cached before the guard exists
        import conftest
        print("no error")
        """
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, cwd=ROOT)
    assert result.returncode != 0, "conftest accepted a module imported from the wrong place"
    assert "expected it from" in result.stderr, result.stderr
