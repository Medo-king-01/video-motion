"""Dependency constraints and inventory use the same active baseline."""
from __future__ import annotations

import sys
from pathlib import Path

import check_python_deps
from packaging.requirements import Requirement


def active_constraints():
    result = {}
    for line in Path(check_python_deps.__file__).with_name('constraints.txt').read_text().splitlines():
        if '==' not in line:
            continue
        requirement = Requirement(line)
        if not requirement.marker or requirement.marker.evaluate():
            assert requirement.name not in result, 'ambiguous active baseline'
            result[requirement.name] = next(iter(requirement.specifier)).version
    return result


def test_inventory_accepts_current_baseline_and_reports_mismatch(monkeypatch, capsys):
    baseline = active_constraints()
    assert check_python_deps.RUNTIME | {'pytest', 'ruff'} <= set(baseline)
    monkeypatch.setattr(sys, 'argv', ['check_python_deps.py', '--dev'])
    monkeypatch.setattr(check_python_deps.importlib.metadata, 'version', baseline.__getitem__)
    assert check_python_deps.main() == 0
    baseline['numpy'] = '0.0.0'
    assert check_python_deps.main() == 1
    assert 'numpy: 0.0.0; expected' in capsys.readouterr().out


def test_inventory_missing_package_is_an_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', ['check_python_deps.py'])
    def missing(_name):
        raise check_python_deps.importlib.metadata.PackageNotFoundError
    monkeypatch.setattr(check_python_deps.importlib.metadata, 'version', missing)
    assert check_python_deps.main() == 1
    assert 'missing; expected' in capsys.readouterr().out
