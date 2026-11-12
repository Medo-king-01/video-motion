#!/usr/bin/env python3
"""The Hybrid backend: one graph, a per-track routing decision, and a record of that decision.

Hybrid is not a third renderer. It is the composite the architecture promises: each track of the
unified project is assigned to the backend that can actually draw it, and the assignment is visible
in the compiled graph (`graph["routing"]`) instead of being an implicit choice inside a render loop.

Today that assignment is boring and honest: P is the only backend with a pixel path, so every
video, text and audio track routes to P, and a track that no backend can draw is refused with `R12`
rather than skipped. The moment engine K grows a real renderer, `route()` is the one function that
changes — the contract, the diagnostics and the tests stay put.

Rules kept here, same as everywhere else:

* the routing decision is data, so a test can assert it without rendering a frame;
* a track with no drawing backend is a diagnostic, never a silent drop (`R12`);
* `render` never claims Hybrid pixels that came from somewhere else — it delegates to the chosen
  backend and stamps the routing table into the manifest it returns.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backend_capabilities as capabilities  # noqa: E402
from unified_render_graph import compile_project, graph_digest  # noqa: E402

BACKEND = "Hybrid"
VERSION = "0.1.0"
#: tracks that carry pixels or samples and therefore need a backend that can draw/mix
DRAWING_KINDS = ("video", "text", "audio")
NO_BACKEND = ("R12", "no drawing backend for this track; engine K reads and validates only")


class AdapterError(RuntimeError):
    def __init__(self, code, path, message):
        self.code, self.path, self.message = code, path, message
        super().__init__(f"{code} {path}: {message}")


class HybridAdapter:
    """Route each track to a backend, then draw the whole frame with that backend."""

    backend = BACKEND
    version = VERSION

    def __init__(self, manifest=None, primary=None):
        self._entry = (manifest or capabilities.load())["backends"][BACKEND]
        if primary is None:
            import adapter_p  # noqa: PLC0415 - P ships with the project

            primary = adapter_p.PAdapter()
        self._primary = primary

    # -- routing -------------------------------------------------------------------------------
    def route(self, graph):
        """Return one decision per track: `{trackId, kind, backend, reason}`.

        A decision with `backend: None` means "this track draws nothing here"; when the track has
        clips and no backend can draw its kind, the decision carries the refusal code instead of
        quietly dropping those clips.
        """
        decisions = []
        for track in graph.get("tracks", []):
            kind = track.get("kind")
            track_id = track.get("trackId") or track.get("id")
            clips = track.get("clips") or []
            if kind in DRAWING_KINDS and track.get("enabled", True):
                decisions.append({
                    "trackId": track_id, "kind": kind, "backend": self._primary.backend,
                    "reason": "the only backend with a wired pixel/sample path in this build",
                })
            elif kind in DRAWING_KINDS:
                decisions.append({"trackId": track_id, "kind": kind, "backend": None,
                                  "reason": "track is disabled; it is not routed"})
            elif not clips:
                decisions.append({"trackId": track_id, "kind": kind, "backend": None,
                                  "reason": "track is empty; nothing to route"})
            else:
                decisions.append({"trackId": track_id, "kind": kind, "backend": None,
                                  "reason": f"no backend draws a {kind!r} track", "code": NO_BACKEND[0]})
        return decisions

    def refusals(self, graph):
        """Turn unroutable tracks that actually carry clips into contract diagnostics."""
        return [{"code": decision["code"], "path": f"$.tracks[{decision['trackId']}]",
                 "message": f"{decision['reason']} (track {decision['trackId']!r}, "
                            f"kind {decision['kind']!r})"}
                for decision in self.route(graph) if decision.get("code")]

    # -- the contract ---------------------------------------------------------------------------
    def capabilities(self):
        return {"backend": self.backend, "backendVersion": VERSION, "features": self._entry["features"]}

    def compile(self, project):
        graph = compile_project(project)
        routing = self.route(graph)
        graph["routing"] = routing
        graph["executable"] = all(decision["backend"] is not None for decision in routing)
        graph["backend"] = {"name": BACKEND, "version": VERSION}
        graph["graphSha256"] = graph_digest(graph)
        return graph

    def preflight(self, graph):
        if "routing" not in graph:
            graph = self.compile(graph["project"])
        refusals = self.refusals(graph)
        drawn = self._primary.preflight(graph)
        diagnostics = refusals + drawn.get("diagnostics", [])
        return {"backend": self.backend, "graphVersion": graph.get("graphVersion"),
                "status": "unsupported" if diagnostics else "supported",
                "diagnostics": diagnostics, "routing": graph["routing"]}

    def render(self, graph, frames, out, options=None):
        if "routing" not in graph:
            graph = self.compile(graph["project"])
        refusals = self.refusals(graph)
        if refusals:
            raise AdapterError(refusals[0]["code"], refusals[0]["path"],
                               "; ".join(item["message"] for item in refusals))
        result = self._primary.render(graph, frames, out, options)
        result["routing"] = graph["routing"]
        result["routedBy"] = BACKEND
        return result

    def cancel(self):
        return self._primary.cancel()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path, nargs="?")
    parser.add_argument("--capabilities", action="store_true")
    parser.add_argument("--preflight", action="store_true", help="print the preflight result")
    args = parser.parse_args(argv)
    adapter = HybridAdapter()
    if args.capabilities:
        print(json.dumps(adapter.capabilities(), ensure_ascii=False, indent=2))
        return 0
    if args.project is None:
        parser.print_usage(sys.stderr)
        return 2
    graph = adapter.compile(json.loads(args.project.read_text(encoding="utf-8")))
    print(json.dumps(adapter.preflight(graph), ensure_ascii=False, indent=2))
    return 0 if not args.preflight else 1


if __name__ == "__main__":
    raise SystemExit(main())
