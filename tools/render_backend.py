#!/usr/bin/env python3
"""The render-backend contract every engine must satisfy (phase 0).

`docs/editor-architecture.md` §7 freezes this interface before any adapter exists, so that P/K/R/Hybrid
are forced into one shape instead of four dialects. Nothing here renders: `NullAdapter` reports
`unsupported` and refuses to pretend otherwise.

The contract is deliberately JSON-first: every return value is a plain dict that can cross a process
boundary and be compared in a test. Rules the adapters must keep (from §7.2):

* no silent drops — an unsupported feature is a diagnostic with a code, a path and a message;
* half-open ranges, in frames for video and samples for audio;
* atomic publication: write a temporary file, then publish; never overwrite a master;
* no network during render;
* same graph + same backend version + same seed ⇒ same pixels/samples on a pinned toolchain;
* a backend may only claim what its capability manifest declares.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backend_capabilities as capabilities  # noqa: E402

BACKENDS = capabilities.BACKENDS
REQUIRED_METHODS = ("capabilities", "compile", "preflight", "render", "cancel")


@runtime_checkable
class RenderBackend(Protocol):
    """One execution backend. Implementations live next to the engine they wrap."""

    backend: str

    def capabilities(self) -> dict[str, Any]:
        """Return the manifest entry for this backend (see backend-capabilities.json)."""

    def compile(self, project: dict[str, Any]) -> dict[str, Any]:
        """Validate the project and return a versioned graph; never mutate the input."""

    def preflight(self, graph: dict[str, Any]) -> dict[str, Any]:
        """Report `supported` or `unsupported` with diagnostics before any frame is drawn."""

    def render(self, graph: dict[str, Any], frames: tuple[int, int],
               out: Path, options: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render the half-open frame range `[from, to)`; publish atomically."""

    def cancel(self) -> None:
        """Request cancellation; must be safe to call from another thread."""


def conformance_problems(adapter: Any, manifest: dict | None = None) -> list[str]:
    """Return why `adapter` is not a contract-conforming backend (empty means it is)."""
    problems: list[str] = []
    name = getattr(adapter, "backend", None)
    if name not in BACKENDS:
        problems.append(f"backend must be one of {list(BACKENDS)}, got {name!r}")
        return problems
    for method in REQUIRED_METHODS:
        if not callable(getattr(adapter, method, None)):
            problems.append(f"{name}: missing method {method}()")
    declared = (manifest or capabilities.load())["backends"][name]["features"]
    response = adapter.capabilities() if callable(getattr(adapter, "capabilities", None)) else None
    if not isinstance(response, dict):
        problems.append(f"{name}: capabilities() must return the manifest entry, got {type(response).__name__}")
        return problems
    if set(response.get("features", {})) != set(declared):
        problems.append(f"{name}: capabilities() does not answer every declared feature")
    for feature, entry in response.get("features", {}).items():
        if feature in declared and entry.get("state") != declared[feature]["state"]:
            problems.append(f"{name}.{feature}: runtime state contradicts the manifest")
    return problems


class NullAdapter:
    """A backend that has not been implemented yet: honest, and useless on purpose."""

    def __init__(self, backend: str, manifest: dict | None = None):
        if backend not in BACKENDS:
            raise ValueError(f"unknown backend {backend!r}")
        self.backend = backend
        self._entry = (manifest or capabilities.load())["backends"][backend]

    def capabilities(self) -> dict[str, Any]:
        return {"backend": self.backend, "features": self._entry["features"]}

    def compile(self, project: dict[str, Any]) -> dict[str, Any]:
        from unified_render_graph import compile_project

        return compile_project(project)

    def preflight(self, graph: dict[str, Any]) -> dict[str, Any]:
        return {
            "backend": self.backend, "status": "unsupported",
            "graphVersion": graph.get("graphVersion"),
            "diagnostics": [{
                "code": "R01", "path": "$",
                "message": "No adapter for the unified render graph is implemented for this backend.",
            }],
        }

    def render(self, graph: dict[str, Any], frames: tuple[int, int],
               out: Path, options: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError(
            f"{self.backend}: the render-backend contract is not implemented; "
            "see docs/editor-architecture.md §7")

    def cancel(self) -> None:
        return None


#: The adapters that exist. Everything not listed here is still a `NullAdapter` on purpose.
REAL = {"P": ("adapter_p", "PAdapter"), "K": ("adapter_k", "KAdapter"),
        "Hybrid": ("adapter_hybrid", "HybridAdapter")}


def real_adapters() -> dict[str, Any]:
    """Return the implemented adapters, skipping any whose module is not installed."""
    import importlib  # noqa: PLC0415

    found: dict[str, Any] = {}
    for name, (module, attribute) in REAL.items():
        try:
            found[name] = getattr(importlib.import_module(module), attribute)()
        except ImportError:  # pragma: no cover - an adapter ships with its engine
            continue
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="check the built-in null adapters")
    parser.add_argument("--backend", choices=BACKENDS, help="print one adapter's capabilities")
    args = parser.parse_args(argv)
    if args.backend:
        import json

        print(json.dumps(NullAdapter(args.backend).capabilities(), ensure_ascii=False, indent=2))
        return 0
    real = real_adapters()
    problems = [problem for name in BACKENDS if name not in real
                for problem in conformance_problems(NullAdapter(name))]
    for name, adapter in sorted(real.items()):
        problems.extend(conformance_problems(adapter))
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    null = [name for name in BACKENDS if name not in real]
    print(f"OK: {len(real)} real adapter(s) ({', '.join(sorted(real)) or 'none'}) and "
          f"{len(null)} null adapter(s) ({', '.join(null) or 'none'}) keep the contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
