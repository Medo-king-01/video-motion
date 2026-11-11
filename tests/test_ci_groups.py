"""The three CI groups are complete, disjoint, and wired into the workflow (A3 guard).

The suite is split so pull requests can run all of it as parallel jobs. These
tests fail if a new test file would fall between the jobs, if a group entry
points at a file that no longer exists, or if `.github/workflows/ci.yml` stops
running one of the groups.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import ROOT

TOOL = ROOT / "tools" / "ci_groups.py"


def _load():
    spec = importlib.util.spec_from_file_location("ci_groups", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ci_groups = _load()


def test_the_repository_assignment_is_valid():
    assert ci_groups.check(ROOT) == []


def test_every_test_file_has_exactly_one_group():
    mapping = ci_groups.assignment(ROOT)
    files = ci_groups.test_files(ROOT)
    assert sorted(mapping) == files
    assert set(mapping.values()) <= set(ci_groups.GROUPS)
    for group in ci_groups.GROUPS:
        assert ci_groups.members(group, ROOT), f"group '{group}' is empty"


def test_the_groups_are_disjoint():
    seen: dict[str, str] = {}
    for group, names in ci_groups.ASSIGNED.items():
        for name in names:
            assert name not in seen, f"{name} is in {seen[name]} and {group}"
            seen[name] = group


def test_the_workflow_runs_all_three_groups_and_the_guard():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for group in ci_groups.GROUPS:
        assert f"ci_groups.py {group}" in workflow, f"ci.yml never runs the '{group}' group"
    assert "ci_groups.py --check" in workflow
    assert "sync_docs_numbers.py --check" in workflow


def test_no_parallel_pytest_run_drops_the_xdist_groups():
    """Every `pytest -n` in the workflows/Makefile needs `--dist loadgroup`, or the marks are inert."""
    assert ci_groups.parallel_pytest_problems(ROOT) == []


@pytest.mark.parametrize("command, flagged", [
    ("python -m pytest -q -n 2 tests", True),
    ("python -m pytest -q -n2 tests", True),
    ("python -m pytest -n auto --cov", True),
    ("pytest --numprocesses=4", True),
    ("$(PY) -m pytest -q -n 2 --cov --cov-fail-under=30", True),
    ("python -m pytest -q -n 2 --cov \\\n          --cov-report=xml", True),
    ("python -m pytest -q -n 2 --dist loadgroup tests", False),
    ("python -m pytest -q -n 2 --dist=loadgroup tests", False),
    ("python -m pytest -q -n 2 \\\n          --dist loadgroup tests", False),
    ("python -m pytest -q tests", False),
    ("npm ci -n 2", False),
])
def test_parallel_pytest_guard_covers_the_whole_class(tmp_path, command, flagged):
    for relative in (".github/workflows/ci.yml", ".github/workflows/other.yaml", "Makefile"):
        root = tmp_path / relative.replace("/", "_")
        target = root / relative
        target.parent.mkdir(parents=True)
        target.write_text(f"jobs:\n  x:\n    steps:\n      - run: {command}\n" if "workflows" in relative
                          else f"coverage:\n\t{command}\n", encoding="utf-8")
        problems = ci_groups.parallel_pytest_problems(root)
        assert bool(problems) is flagged, (relative, problems)
        if flagged:
            assert relative in problems[0] and "--dist loadgroup" in problems[0]


def test_a_new_test_file_defaults_to_render(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_brand_new_thing.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    assert ci_groups.assignment(tmp_path) == {"test_brand_new_thing": "render"}


def test_a_stale_entry_is_reported(tmp_path, monkeypatch):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_brand.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    monkeypatch.setattr(ci_groups, "ASSIGNED", {"contracts": ("test_brand", "test_deleted")})
    problems = ci_groups.check(tmp_path)
    assert any("test_deleted" in problem and "does not exist" in problem for problem in problems)


def test_a_duplicate_entry_is_reported(tmp_path, monkeypatch):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_brand.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    monkeypatch.setattr(ci_groups, "ASSIGNED", {"contracts": ("test_brand",), "unit": ("test_brand",)})
    problems = ci_groups.check(tmp_path)
    assert any("assigned to both" in problem for problem in problems)


def test_list_prints_existing_files():
    result = subprocess.run(
        [sys.executable, str(TOOL), "render"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    paths = result.stdout.split()
    assert paths and all(Path(path).is_file() for path in paths)
    assert all(path.endswith(".py") for path in paths)


def test_unknown_group_is_rejected():
    result = subprocess.run(
        [sys.executable, str(TOOL), "everything"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode != 0
    assert "invalid choice" in result.stderr or "unknown group" in result.stderr
