"""The browser check is a script the owner can run, so it must stay runnable and honest.

It is not part of the pytest run (it needs Chromium), but three things can rot silently and are cheap
to pin: the file's syntax, its refusal when no browser is present, and the docs pointing at it.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "editor" / "visual-check.mjs"
DOC = ROOT / "docs" / "editor-ui.md"


def test_the_browser_check_script_parses() -> None:
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    result = subprocess.run(["node", "--check", str(SCRIPT)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr


def test_it_refuses_clearly_when_no_browser_is_available() -> None:
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    env = {"PATH": str(Path(shutil.which("node")).parent) + ":/usr/bin:/bin", "HOME": "/tmp"}
    result = subprocess.run(["node", str(SCRIPT), "--url", "http://127.0.0.1:1"],
                            capture_output=True, text=True, timeout=120, env=env,
                            cwd=str(ROOT))
    assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
    assert "no browser" in result.stderr


def test_the_docs_say_how_to_run_it_and_what_it_proves() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "editor/visual-check.mjs" in text
    assert "Chromium" in text
    assert "--out" in text


def test_the_script_checks_the_things_jsdom_cannot() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for needle in ("computedDirection", "scrollWidth", "binX", "console stayed clean", "stageNatural"):
        assert needle in text, needle
