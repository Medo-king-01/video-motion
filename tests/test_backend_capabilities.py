"""The capability manifest may not say more than the tree can back up.

`docs/editor-architecture.md` §8 promises that a feature is either implemented or explicitly
rejected, and §11 makes "honest capabilities" a phase-0 exit criterion. The manifest is only
useful if a claim without evidence fails a test rather than a review.
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

import backend_capabilities as caps  # noqa: E402


@pytest.fixture()
def manifest() -> dict:
    return caps.load()


def test_the_repository_manifest_is_consistent(manifest) -> None:
    assert caps.validate(manifest) == []


def test_every_backend_answers_every_feature(manifest) -> None:
    """A missing entry is a gap, not 'unknown': the state has to be written down."""
    for backend in caps.BACKENDS:
        assert set(manifest["backends"][backend]["features"]) == set(manifest["features"])


def test_matrix_covers_the_four_backends(manifest) -> None:
    summary = caps.matrix(manifest)
    assert set(summary) == set(caps.BACKENDS)
    assert summary["K"]["alpha.layer"] == "supported"
    assert summary["P"]["alpha.layer"] == "supported"  # P renders a real text/overlay layer now


def test_a_missing_feature_is_reported(manifest) -> None:
    broken = copy.deepcopy(manifest)
    del broken["backends"]["R"]["features"]["range.render"]
    errors = caps.validate(broken)
    assert any("no state for" in error and "range.render" in error for error in errors), errors


def test_conditional_needs_a_condition(manifest) -> None:
    broken = copy.deepcopy(manifest)
    broken["backends"]["Hybrid"]["features"]["alpha.layer"]["conditions"] = []
    errors = caps.validate(broken)
    assert any("conditional needs at least one condition" in error for error in errors), errors


def test_supported_without_evidence_is_rejected(manifest) -> None:
    broken = copy.deepcopy(manifest)
    broken["backends"]["K"]["features"]["alpha.layer"]["evidence"] = []
    errors = caps.validate(broken)
    assert any("supported needs evidence" in error for error in errors), errors


def test_evidence_must_exist_in_the_tree(manifest) -> None:
    broken = copy.deepcopy(manifest)
    broken["backends"]["P"]["features"]["draft.half"]["evidence"] = ["docs/does-not-exist.md"]
    errors = caps.validate(broken)
    assert any("is not an existing repo-relative file" in error for error in errors), errors


@pytest.mark.parametrize("bad", ["../outside.md", "/etc/passwd", "docs\\hybrid.md"])
def test_evidence_cannot_escape_the_repository(manifest, bad) -> None:
    broken = copy.deepcopy(manifest)
    broken["backends"]["K"]["features"]["alpha.layer"]["evidence"] = [bad]
    errors = caps.validate(broken)
    assert any("is not an existing repo-relative file" in error for error in errors), errors


def test_an_invalid_state_is_rejected(manifest) -> None:
    broken = copy.deepcopy(manifest)
    broken["backends"]["P"]["features"]["draft.half"]["state"] = "probably"
    errors = caps.validate(broken)
    assert any("expected one of" in error for error in errors), errors


def test_unknown_top_level_field_is_rejected(manifest) -> None:
    broken = copy.deepcopy(manifest)
    broken["roadmap"] = {}
    errors = caps.validate(broken)
    assert any("unknown top-level field" in error for error in errors), errors


def test_only_a_backend_with_an_adapter_claims_to_read_the_unified_project(manifest) -> None:
    """The claim and the adapter land together; a manifest ahead of the tree is a lie."""
    for backend in caps.BACKENDS:
        state = manifest["backends"][backend]["features"]["project.read"]["state"]
        if (TOOLS / f"adapter_{backend.lower()}.py").exists():
            assert state in ("supported", "conditional"), f"{backend} has an adapter but claims {state}"
        else:
            assert state in ("unsupported", "unknown"), f"{backend} claims project.read without an adapter"


def test_claiming_graph_execution_before_an_adapter_fails(manifest) -> None:
    broken = copy.deepcopy(manifest)
    broken["backends"]["R"]["features"]["graph.execute"] = {
        "version": 1, "state": "supported", "evidence": ["docs/editor-architecture.md"]}
    errors = caps.validate(broken)
    assert any("cannot be claimed before an adapter exists" in error for error in errors), errors


def test_duplicate_json_keys_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text('{"manifestVersion": 1, "manifestVersion": 1}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        caps.load(path)


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "backend_capabilities.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=60)


def test_cli_check_passes_on_the_repository() -> None:
    result = run("--check")
    assert result.returncode == 0, result.stderr
    assert "every claim has evidence" in result.stdout


def test_cli_matrix_prints_every_backend() -> None:
    result = run("--matrix")
    assert result.returncode == 0, result.stderr
    for backend in caps.BACKENDS:
        assert backend in result.stdout
    assert "alpha.layer" in result.stdout


def test_cli_reports_an_unreadable_manifest(tmp_path: Path) -> None:
    result = run("--manifest", str(tmp_path / "missing.json"))
    assert result.returncode == 2
    assert "Cannot read capabilities manifest" in result.stderr
