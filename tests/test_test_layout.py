"""Layout rules for the test suite itself (N12).

Two large files were split so a reviewer can hold one concern at a time: the Fixed Stage categories
A-G became four modules plus a support module, and the Machine Explainer file became three plus a
support module. Without a rule, the next feature recreates the problem by appending to whichever
file already imports the right things.

The cap is a review budget, not a principle: 900 lines is roughly one screen-mile of test code, and
every file currently in the suite is under it. A file that needs to grow past it should split along
the categories it already uses and put shared builders in `<feature>_support.py` - which the second
test below protects, because a `test_` function in a support module is collected by nobody and
fails silently.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
MAX_LINES = 900


def _test_modules() -> list[Path]:
    return sorted(TESTS.glob("test_*.py"))


def _support_modules() -> list[Path]:
    return sorted(TESTS.glob("*_support.py"))


def test_no_test_module_outgrows_the_review_budget():
    oversized = {
        path.name: len(path.read_text(encoding="utf-8").splitlines())
        for path in _test_modules()
        if len(path.read_text(encoding="utf-8").splitlines()) > MAX_LINES
    }
    assert not oversized, (
        f"these test modules are past {MAX_LINES} lines ({oversized}); split by category and move "
        "shared builders into <feature>_support.py instead of appending"
    )


def test_support_modules_hold_no_tests_that_would_never_run():
    swallowed: dict[str, list[str]] = {}
    for path in _support_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test")
        ]
        if names:
            swallowed[path.name] = names
    assert not swallowed, (
        f"pytest does not collect these files, so these tests never run: {swallowed}"
    )


def test_support_modules_are_used_and_importable():
    """A support module nobody imports is dead weight; one that cannot be imported breaks collection."""
    import importlib

    sources = [path.read_text(encoding="utf-8") for path in _test_modules()]
    for path in _support_modules():
        assert any(
            f"from {path.stem} import" in source or f"import {path.stem}" in source
            for source in sources
        ), f"{path.name} is not imported by any test module"
        module = importlib.import_module(path.stem)
        helpers = [
            name
            for name in dir(module)
            if not name.startswith("__") and callable(getattr(module, name))
            and not name.startswith("test")
        ]
        assert helpers, f"{path.name} exports no callable helpers"
