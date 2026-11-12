#!/usr/bin/env python3
"""Engine K behind the same contract as P — reading and validating now, drawing later.

K is the Node/Remotion renderer. This adapter gives it the *same* interface P has
(`compile`/`preflight`/`render`/`cancel`) and the same guarantee: it never pretends. It reads and
validates a project and returns an executable-looking graph, but `preflight` answers
`unsupported` with `R11` until K's rendering path is wired into this contract, and `render`
refuses with the same code instead of writing frames that were actually produced by P.

Why ship an adapter that cannot draw? Because the honest alternative to "the adapter exists" is not
silence: `tools/backend_capabilities.py` refuses a `project.read` claim from a backend with no
`adapter_<x>.py`, and the editor asks every backend the same two questions. K now answers both.

The day the Node path lands, `render` grows a subprocess call to it and `R11` disappears — the
manifest entry is the switch, and `tests/test_adapter_k.py` is what keeps it honest until then.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backend_capabilities as capabilities  # noqa: E402
from unified_render_graph import compile_project, graph_digest  # noqa: E402

BACKEND = "K"
VERSION = "0.1.0"
MISSING = ("R11", "$", "engine K has no wired pixel path in this build; the Node renderer is "
                       "not connected to the unified graph yet")


class AdapterError(RuntimeError):
    def __init__(self, code, path, message):
        self.code, self.path, self.message = code, path, message
        super().__init__(f"{code} {path}: {message}")


class KAdapter:
    """Engine K: reads and validates the graph, refuses to render."""

    backend = BACKEND
    version = VERSION

    def __init__(self, manifest=None):
        self._entry = (manifest or capabilities.load())["backends"][BACKEND]

    def capabilities(self):
        return {"backend": self.backend, "backendVersion": VERSION, "features": self._entry["features"]}

    def compile(self, project):
        graph = compile_project(project)
        graph["executable"] = False
        graph["backend"] = {"name": BACKEND, "version": VERSION}
        graph["graphSha256"] = graph_digest(graph)
        return graph

    def preflight(self, graph):
        return {"backend": self.backend, "status": "unsupported",
                "graphVersion": graph.get("graphVersion"),
                "diagnostics": [{"code": MISSING[0], "path": MISSING[1], "message": MISSING[2]}]}

    def render(self, graph, frames, out, options=None):
        raise AdapterError(*MISSING)

    def cancel(self):
        return None


def node_available() -> dict:
    """Report whether the Node toolchain K needs is on this machine at all."""
    node = shutil.which("node")
    return {"node": node, "usable": bool(node)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path, nargs="?")
    parser.add_argument("--capabilities", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--toolchain", action="store_true", help="print what the machine has for K")
    args = parser.parse_args(argv)
    adapter = KAdapter()
    if args.capabilities:
        print(json.dumps(adapter.capabilities(), ensure_ascii=False, indent=2))
        return 0
    if args.toolchain:
        print(json.dumps(node_available(), ensure_ascii=False))
        return 0
    if args.project is None:
        parser.print_usage(sys.stderr)
        return 2
    graph = adapter.compile(json.loads(args.project.read_text(encoding="utf-8")))
    print(json.dumps(adapter.preflight(graph), ensure_ascii=False, indent=2))
    return 0 if not args.preflight else 1


if __name__ == "__main__":
    raise SystemExit(main())
