"""Engine K's adapter reads the contract and refuses to draw — and says so in one place.

The value of this file is negative space: it pins the exact moment K stops being a `NullAdapter`
(it now compiles and validates projects) and the exact reason it still writes no pixels (`R11`).
When the Node path lands, these assertions change in the same commit as the manifest.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import adapter_k  # noqa: E402
import render_backend  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/unified_project/basic.json"


def test_k_is_conformant_even_though_it_cannot_draw() -> None:
    assert render_backend.conformance_problems(adapter_k.KAdapter()) == []


def test_k_compiles_a_valid_project_and_marks_it_not_executable() -> None:
    project = json.loads(FIXTURE.read_text(encoding="utf-8"))
    graph = adapter_k.KAdapter().compile(project)
    assert graph["executable"] is False
    assert graph["backend"]["name"] == "K"
    assert len(graph["graphSha256"]) == 64


def test_k_refuses_every_frame_with_one_documented_code() -> None:
    project = json.loads(FIXTURE.read_text(encoding="utf-8"))
    adapter = adapter_k.KAdapter()
    graph = adapter.compile(project)
    readiness = adapter.preflight(graph)
    assert readiness["status"] == "unsupported"
    assert [diagnostic["code"] for diagnostic in readiness["diagnostics"]] == ["R11"]
    with pytest.raises(adapter_k.AdapterError) as excinfo:
        adapter.render(graph, (0, 1), Path("/tmp/k-should-not-exist"))
    assert excinfo.value.code == "R11"


def test_k_claims_reading_but_not_executing_the_unified_graph() -> None:
    """The manifest describes K's own engine; the contract answer is `preflight`, and it says R11."""
    features = adapter_k.KAdapter().capabilities()["features"]
    assert features["project.read"]["state"] == "supported"
    assert features["graph.execute"]["state"] == "unsupported"


def test_the_cli_reports_preflight_and_toolchain() -> None:
    result = subprocess.run([sys.executable, str(TOOLS / "adapter_k.py"), str(FIXTURE), "--preflight"],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 1
    assert "R11" in result.stdout
    toolchain = subprocess.run([sys.executable, str(TOOLS / "adapter_k.py"), "--toolchain"],
                               capture_output=True, text=True, timeout=60)
    assert toolchain.returncode == 0
    assert "usable" in toolchain.stdout
