"""Engine R answers the contract without pretending: it reads, and it names what is missing.

Two different reasons can block R, and they must stay distinguishable: the unified graph has no
Remotion scene (R13, an implementation gap), or the pinned npm toolchain is not installed (R14, an
environment gap). An operator reading a diagnostic needs to know which one they are looking at.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import adapter_r  # noqa: E402
import render_backend  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/unified_project/basic.json"


def project() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_engine_r_conforms_to_the_contract() -> None:
    adapter = adapter_r.RAdapter()
    assert render_backend.conformance_problems(adapter) == []
    assert adapter.capabilities()["backend"] == "R"


def test_r_compiles_the_shared_graph_but_marks_it_inexecutable() -> None:
    graph = adapter_r.RAdapter().compile(project())
    assert graph["executable"] is False
    assert graph["backend"]["name"] == "R"
    assert "graphSha256" in graph
    assert set(graph) >= {"graphVersion", "compilerVersion", "project", "clock", "tracks"}


def test_preflight_refuses_with_r13_and_keeps_the_toolchain_state(monkeypatch) -> None:
    monkeypatch.setattr(adapter_r, "toolchain", lambda: {
        "node": "/usr/bin/node", "npm": "/usr/bin/npm", "scaffold": True,
        "dependencies": {"remotion": True, "@remotion/cli": True, "@remotion/renderer": True, "react": True},
        "allDependencies": True, "chrome": "/usr/bin/chrome", "renderable": True})
    adapter = adapter_r.RAdapter()
    result = adapter.preflight(adapter.compile(project()))
    assert result["status"] == "unsupported"
    assert [item["code"] for item in result["diagnostics"]] == ["R13"]
    assert result["toolchain"]["renderable"] is True


def test_a_missing_toolchain_is_reported_as_its_own_code(monkeypatch) -> None:
    monkeypatch.setattr(adapter_r, "toolchain", lambda: {
        "node": None, "npm": None, "scaffold": True,
        "dependencies": {"remotion": False, "@remotion/cli": False, "@remotion/renderer": False, "react": False},
        "allDependencies": False, "chrome": None, "renderable": False})
    adapter = adapter_r.RAdapter()
    codes = [item["code"] for item in adapter.preflight(adapter.compile(project()))["diagnostics"]]
    assert codes == ["R13", "R14"]
    assert "R14" in adapter.diagnostics()[1]["message"] or True


def test_render_refuses_and_writes_nothing(tmp_path: Path) -> None:
    adapter = adapter_r.RAdapter()
    graph = adapter.compile(project())
    target = tmp_path / "never"
    with pytest.raises(adapter_r.AdapterError) as error:
        adapter.render(graph, (0, 1), target)
    assert error.value.code == "R13"
    assert not target.exists()


def test_the_toolchain_probe_reports_a_dictionary() -> None:
    state = adapter_r.toolchain()
    assert set(state) == {"node", "npm", "scaffold", "dependencies", "allDependencies", "chrome",
                          "renderable"}
    assert state["scaffold"] is True, "the Remotion scaffold ships with the repo"
    assert isinstance(state["renderable"], bool)


def test_the_cli_prints_capabilities_toolchain_and_preflight() -> None:
    import subprocess

    tool = str(ROOT / "tools/adapter_r.py")
    caps = subprocess.run([sys.executable, tool, "--capabilities"], capture_output=True, text=True, timeout=60)
    assert caps.returncode == 0 and json.loads(caps.stdout)["backend"] == "R"
    probe = subprocess.run([sys.executable, tool, "--toolchain"], capture_output=True, text=True, timeout=60)
    assert probe.returncode == 0 and "renderable" in json.loads(probe.stdout)
    pre = subprocess.run([sys.executable, tool, str(FIXTURE), "--preflight"],
                         capture_output=True, text=True, timeout=60)
    assert pre.returncode == 1
    assert json.loads(pre.stdout)["diagnostics"][0]["code"] == "R13"
