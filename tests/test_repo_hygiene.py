"""Repository hygiene that Git itself must enforce: binary assets and line endings.

There is no Git LFS here on purpose (see `.gitattributes`), so the attribute file is the only
thing standing between a binary font and a textconv/EOL rewrite. These assertions are cheap and
they fail the moment someone deletes the file or narrows it while "cleaning up".
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ATTRIBUTES = ROOT / ".gitattributes"


def check_attr(attribute: str, path: str) -> str:
    result = subprocess.run(["git", "check-attr", attribute, "--", path], cwd=str(ROOT),
                            capture_output=True, text=True, check=True)
    return result.stdout.strip().rsplit(": ", 1)[-1]


def test_gitattributes_exists_and_declares_auto_text() -> None:
    assert ATTRIBUTES.is_file()
    text = ATTRIBUTES.read_text(encoding="utf-8")
    assert "* text=auto" in text
    assert "filter=lfs" not in text  # LFS is a deliberate non-decision, not an accident


@pytest.mark.parametrize("path", [
    "assets/fonts/Cairo/Cairo_800ExtraBold.ttf",
    "assets/poses/source/5be9f266.png",
    "docs/audition/01-six-presets.mp3",
])
def test_assets_are_marked_binary(path: str) -> None:
    assert check_attr("binary", path) == "set"


@pytest.mark.parametrize("path", [
    "tools/doctor.py",
    "AGENTS.md",
    "medo-motion/motion/transitions.json",
])
def test_text_files_are_pinned_to_lf(path: str) -> None:
    assert check_attr("text", path) == "set"
    assert check_attr("eol", path) == "lf"
