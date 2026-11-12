"""The backend interface is frozen before the first adapter exists.

`docs/editor-architecture.md` §7.1 publishes the contract and §11 makes it a phase-0 exit criterion.
A signature that drifts silently would let P/K/R/Hybrid grow four dialects again, so the shape is
asserted here rather than described in a document.
"""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import backend_capabilities as caps  # noqa: E402
import render_backend as rb  # noqa: E402


@pytest.mark.parametrize("backend", rb.BACKENDS)
def test_null_adapters_satisfy_the_contract(backend: str) -> None:
    assert rb.conformance_problems(rb.NullAdapter(backend)) == []


def test_the_protocol_names_every_required_method() -> None:
    for method in rb.REQUIRED_METHODS:
        assert callable(getattr(rb.RenderBackend, method, None)), method


def test_null_adapters_are_runtime_instances_of_the_protocol() -> None:
    assert isinstance(rb.NullAdapter("K"), rb.RenderBackend)


@pytest.mark.parametrize("method, expected", [
    ("capabilities", []),
    ("compile", ["project"]),
    ("preflight", ["graph"]),
    ("render", ["graph", "frames", "out", "options"]),
    ("cancel", []),
])
def test_signatures_are_frozen(method: str, expected: list[str]) -> None:
    parameters = [name for name in inspect.signature(getattr(rb.RenderBackend, method)).parameters
                  if name != "self"]
    assert parameters == expected, f"update docs/editor-architecture.md §7.1 with {method}()"


def test_render_takes_a_half_open_range_and_optional_options() -> None:
    signature = inspect.signature(rb.RenderBackend.render)
    assert signature.parameters["options"].default is None
    assert "half-open" in (rb.RenderBackend.render.__doc__ or "")


def test_a_backend_missing_a_method_is_reported() -> None:
    class Half:
        backend = "K"

        def capabilities(self):
            return {"features": rb.NullAdapter("K").capabilities()["features"]}

    problems = rb.conformance_problems(Half())
    assert any("missing method cancel()" in problem for problem in problems), problems


def test_an_unknown_backend_name_is_reported() -> None:
    class Wrong:
        backend = "Q"

    assert rb.conformance_problems(Wrong()) == ["backend must be one of ['P', 'K', 'R', 'Hybrid'], got 'Q'"]


def test_runtime_state_may_not_contradict_the_manifest() -> None:
    adapter = rb.NullAdapter("P")
    capabilities = adapter.capabilities()
    capabilities["features"]["three.layer"]["state"] = "supported"
    adapter.capabilities = lambda: capabilities
    problems = rb.conformance_problems(adapter)
    assert any("runtime state contradicts the manifest" in problem for problem in problems), problems


def test_capabilities_must_answer_every_declared_feature() -> None:
    adapter = rb.NullAdapter("P")
    features = adapter.capabilities()["features"]
    features.pop("draft.half")
    adapter.capabilities = lambda: {"features": features}
    problems = rb.conformance_problems(adapter)
    assert any("does not answer every declared feature" in problem for problem in problems), problems


def test_a_null_adapter_refuses_to_pretend_it_renders() -> None:
    with pytest.raises(NotImplementedError, match="not implemented"):
        rb.NullAdapter("R").render({}, (0, 1), Path("/tmp/never-written"))


def test_a_null_adapter_preflight_is_unsupported_with_a_code() -> None:
    result = rb.NullAdapter("Hybrid").preflight({"graphVersion": "0.1"})
    assert result["status"] == "unsupported"
    assert result["diagnostics"][0]["code"] == "R01"


def test_compiling_through_a_null_adapter_uses_the_shared_compiler() -> None:
    project = json.loads((ROOT / "tests/fixtures/unified_project/basic.json").read_text(encoding="utf-8"))
    graph = rb.NullAdapter("K").compile(project)
    assert graph["executable"] is False
    assert set(graph) == {"graphVersion", "compilerVersion", "executable", "project", "clock", "tracks"}


def test_unknown_backend_constructor_is_loud() -> None:
    with pytest.raises(ValueError, match="unknown backend"):
        rb.NullAdapter("K2")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "render_backend.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=60)


def test_cli_check_passes() -> None:
    result = run("--check")
    assert result.returncode == 0, result.stderr
    assert "real adapter(s) (Hybrid, K, P)" in result.stdout


def test_the_cli_knows_which_adapters_are_real() -> None:
    assert set(rb.real_adapters()) == {"P", "K", "Hybrid"}


def test_cli_prints_one_backend() -> None:
    result = run("--backend", "P")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["backend"] == "P"


def test_cli_rejects_an_unknown_backend() -> None:
    assert run("--backend", "Q").returncode == 2
