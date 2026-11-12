#!/usr/bin/env python3
"""Engine R behind the same contract as P and K — it reads the project, and says why it cannot draw it.

R is the Remotion renderer. Its scaffold lives in `medo-motion/templates/remotion/` and it renders its
own scene format (`plan/beats.json` + React components), which is **not** the unified project. So this
adapter answers the two questions every backend must answer, honestly:

* `compile()` validates the project through the shared compiler and returns a graph stamped with R;
* `preflight()` reports `unsupported` with two separate codes — `R13` (there is no unified-graph →
  Remotion-scene bridge yet) and, when it applies, `R14` (the pinned npm toolchain is not installed in
  this checkout) — so the operator knows which of the two is blocking;
* `render()` refuses with the same codes instead of shelling out to a scene nobody wrote.

`toolchain()` measures the machine rather than guessing: node, the pinned Remotion packages, and a
Chromium/headless shell for Remotion to drive. That is what makes the difference between "not
implemented" and "not installed" visible in the editor.
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

BACKEND = "R"
VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / "medo-motion" / "templates" / "remotion"
NO_BRIDGE = ("R13", "$", "the unified render graph has no Remotion scene yet; "
                         "engine R renders its own plan/beats.json format")
NO_TOOLCHAIN = ("R14", "$", "the pinned Remotion toolchain is not installed "
                            "(npm ci --prefix medo-motion/templates/remotion)")


class AdapterError(RuntimeError):
    def __init__(self, code, path, message):
        self.code, self.path, self.message = code, path, message
        super().__init__(f"{code} {path}: {message}")


def toolchain() -> dict:
    """What this machine actually has for engine R."""
    node = shutil.which("node")
    npm = shutil.which("npm")
    modules = SCAFFOLD / "node_modules"
    pinned = {}
    for package in ("remotion", "@remotion/cli", "@remotion/renderer", "react"):
        manifest = modules / package / "package.json" if "@" not in package else modules / package / "package.json"
        pinned[package] = manifest.is_file()
    chrome = next((shutil.which(name) for name in
                   ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(name)), None)
    return {
        "node": node, "npm": npm, "scaffold": SCAFFOLD.is_dir(),
        "dependencies": pinned, "allDependencies": all(pinned.values()),
        "chrome": chrome,
        "renderable": bool(node and pinned.get("@remotion/renderer") and chrome),
    }


class RAdapter:
    """Engine R: reads and validates, refuses to draw (R13), and names a missing toolchain (R14)."""

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

    def diagnostics(self, toolchain_state: dict | None = None) -> list:
        state = toolchain_state or toolchain()
        problems = [{"code": NO_BRIDGE[0], "path": NO_BRIDGE[1], "message": NO_BRIDGE[2]}]
        if not state["renderable"]:
            missing = [name for name, present in state["dependencies"].items() if not present]
            detail = NO_TOOLCHAIN[2] + (f" — missing: {', '.join(missing)}" if missing else "")
            problems.append({"code": NO_TOOLCHAIN[0], "path": NO_TOOLCHAIN[1], "message": detail})
        return problems

    def preflight(self, graph):
        return {"backend": self.backend, "status": "unsupported",
                "graphVersion": graph.get("graphVersion"),
                "diagnostics": self.diagnostics(), "toolchain": toolchain()}

    def render(self, graph, frames, out, options=None):
        first = self.diagnostics()[0]
        raise AdapterError(first["code"], first["path"], first["message"])

    def cancel(self):
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path, nargs="?")
    parser.add_argument("--capabilities", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--toolchain", action="store_true", help="print what this machine has for R")
    args = parser.parse_args(argv)
    adapter = RAdapter()
    if args.capabilities:
        print(json.dumps(adapter.capabilities(), ensure_ascii=False, indent=2))
        return 0
    if args.toolchain:
        print(json.dumps(toolchain(), ensure_ascii=False, indent=2))
        return 0
    if args.project is None:
        parser.print_usage(sys.stderr)
        return 2
    graph = adapter.compile(json.loads(args.project.read_text(encoding="utf-8")))
    print(json.dumps(adapter.preflight(graph), ensure_ascii=False, indent=2))
    return 0 if not args.preflight else 1


if __name__ == "__main__":
    raise SystemExit(main())
