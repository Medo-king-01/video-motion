"""The executable motion catalog may not count prose as moves.

`medo-motion/motion/moves.json` separates runnable families (a real implementation, its symbols and
evidence) from the descriptive technique library. `docs/exploitation-map.md` §1 corrects the premise
that 2,239 techniques are 2,239 moves; this file keeps the correction true.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import moves  # noqa: E402


@pytest.fixture()
def registry() -> dict:
    return moves.load()


def test_the_repository_registry_is_consistent(registry) -> None:
    assert moves.validate(registry) == []


def test_totals_are_measured_from_the_sources(registry) -> None:
    summary = moves.audit(registry)
    assert summary["families"]["caption-entrances"]["count"] == 51
    assert summary["families"]["transitions"]["count"] == 14
    assert summary["families"]["element-effects"]["count"] == 3
    assert summary["executable_moves"] == 78
    assert summary["descriptive_units"] == summary["families"]["techniques-library"]["count"]


def test_the_technique_library_is_never_counted_as_moves(registry) -> None:
    family = registry["families"]["techniques-library"]
    assert family["state"] == "descriptive"
    assert family["engines"] == {}
    assert moves.audit(registry)["descriptive_units"] > 0


@pytest.mark.parametrize("family", ["caption-entrances", "element-effects", "transitions"])
def test_every_executable_family_has_a_preview(registry, family: str) -> None:
    assert "preview" in registry["families"][family]


def test_a_wrong_count_is_reported(registry) -> None:
    broken = copy.deepcopy(registry)
    broken["families"]["transitions"]["count"] = 15
    errors = moves.validate(broken)
    assert any("source has 14" in error for error in errors), errors


def test_a_symbol_missing_from_the_implementation_is_reported(registry) -> None:
    broken = copy.deepcopy(registry)
    broken["families"]["caption-entrances"]["engines"]["K"]["symbols"] = ["captionTransform", "nope"]
    errors = moves.validate(broken)
    assert any("'nope' not found" in error for error in errors), errors


def test_missing_evidence_is_reported(registry) -> None:
    broken = copy.deepcopy(registry)
    broken["families"]["transitions"]["engines"]["K"]["evidence"] = []
    errors = moves.validate(broken)
    assert any("supported needs evidence" in error for error in errors), errors


def test_a_nonexistent_evidence_path_is_reported(registry) -> None:
    broken = copy.deepcopy(registry)
    broken["families"]["element-effects"]["engines"]["P"]["evidence"] = ["tests/nope.py"]
    errors = moves.validate(broken)
    assert any("is not an existing repo file" in error for error in errors), errors


def test_a_descriptive_family_cannot_claim_an_engine(registry) -> None:
    broken = copy.deepcopy(registry)
    broken["families"]["techniques-library"]["engines"] = {
        "K": {"state": "supported", "impl": "medo-motion/templates/render/lib/motion.js",
              "symbols": ["keyframes"], "evidence": ["tests/test_motion.py"]}}
    errors = moves.validate(broken)
    assert any("descriptive family cannot claim engines" in error for error in errors), errors


def test_a_descriptive_family_must_say_why(registry) -> None:
    broken = copy.deepcopy(registry)
    del broken["families"]["techniques-library"]["why"]
    errors = moves.validate(broken)
    assert any("must say why" in error for error in errors), errors


def test_an_executable_family_needs_a_supported_engine(registry) -> None:
    broken = copy.deepcopy(registry)
    broken["families"]["transitions"]["engines"]["K"]["state"] = "unsupported"
    broken["families"]["transitions"]["engines"]["P"]["state"] = "unsupported"
    errors = moves.validate(broken)
    assert any("needs at least one supported engine" in error for error in errors), errors


def test_an_unknown_engine_is_reported(registry) -> None:
    broken = copy.deepcopy(registry)
    broken["families"]["transitions"]["engines"]["Q"] = {"state": "unsupported"}
    errors = moves.validate(broken)
    assert any("unknown engine" in error for error in errors), errors


def test_members_must_exist_in_the_source(registry) -> None:
    broken = copy.deepcopy(registry)
    broken["families"]["transitions"]["members"] = ["not-a-transition"]
    errors = moves.validate(broken)
    assert any("not in source" in error for error in errors), errors


def test_a_missing_preview_is_reported(registry) -> None:
    broken = copy.deepcopy(registry)
    broken["families"]["transitions"]["preview"] = "docs/nope.md"
    errors = moves.validate(broken)
    assert any("preview" in error for error in errors), errors


def test_duplicate_json_keys_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "moves.json"
    path.write_text('{"version": 1, "version": 1}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        moves.load(path)


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "moves.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=60)


def test_cli_check_passes() -> None:
    result = run("--check")
    assert result.returncode == 0, result.stderr
    assert "78 executable moves" in result.stdout


def test_cli_audit_prints_every_family() -> None:
    result = run("--audit")
    assert result.returncode == 0, result.stderr
    for family in ("caption-entrances", "element-effects", "transitions", "techniques-library"):
        assert family in result.stdout
    assert "descriptive units: 2239" in result.stdout


def test_cli_reports_an_unreadable_registry(tmp_path: Path) -> None:
    result = run("--registry", str(tmp_path / "missing.json"))
    assert result.returncode == 2
    assert "Cannot read moves registry" in result.stderr
