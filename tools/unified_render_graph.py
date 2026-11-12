#!/usr/bin/env python3
"""Compile a validated unified project into an experimental, non-executable graph.

This module neither opens media nor renders. No current backend accepts this graph.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

from unified_project_check import validate
from unified_project_store import load

GRAPH_VERSION = "0.1"
COMPILER_VERSION = "0.1"
BACKENDS = ("P", "K", "R", "Hybrid")


class InvalidProject(ValueError):
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        super().__init__("; ".join(diagnostics))


def _ceil_div(numerator, denominator):
    return (numerator + denominator - 1) // denominator


def compile_project(project):
    """Return a detached deterministic plan, or raise InvalidProject with diagnostics.

    The project snapshot is preserved in full. Track and clip indices refer to that
    snapshot. Sample ranges specify sample timestamps inside each half-open clip,
    not a claim that decoding, compositing or output padding is implemented.
    """
    errors = validate(project)
    if errors:
        raise InvalidProject(errors)
    snapshot = deepcopy(project)
    fps = snapshot["profile"]["fps"]
    frame_step = snapshot["timebase"] * fps["den"] // fps["num"]
    sample_step = snapshot["timebase"] // snapshot["profile"]["sampleRate"]
    tracks = []
    for track_index, track in enumerate(snapshot["tracks"]):
        clips = []
        for clip_index, clip in enumerate(track["clips"]):
            start, end = clip["start"], clip["start"] + clip["duration"]
            step = sample_step if track["kind"] == "audio" else frame_step
            entry = {
                "clipId": clip["id"], "projectPath": f"$.tracks[{track_index}].clips[{clip_index}]",
                "tickRange": [start, end],
                "sampleRange": [_ceil_div(start, step), _ceil_div(end, step)],
            }
            if clip.get("textId") is not None:
                entry["textId"] = clip["textId"]
            else:
                entry["assetId"] = clip["assetId"]
                speed = clip.get("speed") or {"num": 1, "den": 1}
                entry["speed"] = [speed["num"], speed["den"]]
                entry["sourceTicks"] = [_ceil_div(clip["sourceIn"] * speed["num"], speed["den"]),
                                        _ceil_div((clip["sourceIn"] + clip["duration"]) * speed["num"],
                                                  speed["den"])]
            clips.append(entry)
        tracks.append({"trackId": track["id"], "kind": track["kind"], "enabled": track["enabled"],
                       "projectPath": f"$.tracks[{track_index}]", "clips": clips})
    return {
        "graphVersion": GRAPH_VERSION, "compilerVersion": COMPILER_VERSION,
        "executable": False, "project": snapshot,
        "clock": {"frameTicks": frame_step, "audioSampleTicks": sample_step,
                  "frameCount": _ceil_div(snapshot["duration"], frame_step),
                  "audioSampleCount": _ceil_div(snapshot["duration"], sample_step)},
        "tracks": tracks,
    }


def canonical_bytes(graph):
    """Canonical JSON encoding for this Python graph version, not a cross-language standard."""
    return json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def graph_digest(graph):
    return hashlib.sha256(canonical_bytes(graph)).hexdigest()


def preflight(project, backend):
    """Validate and compile before reporting backend readiness; never claim render support."""
    if backend not in BACKENDS:
        raise ValueError(f"Unknown backend: {backend!r}")
    graph = compile_project(project)
    return {
        "backend": backend, "status": "unsupported", "graphVersion": GRAPH_VERSION,
        "graphSha256": graph_digest(graph),
        "diagnostics": [{"code": "R01", "path": "$", "message":
                         "No adapter for the unified render graph is implemented for this backend."}],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--backend", choices=BACKENDS, help="report backend readiness instead of the graph")
    args = parser.parse_args(argv)
    try:
        project, _ = load(args.project)
        result = preflight(project, args.backend) if args.backend else compile_project(project)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Cannot compile project: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.backend else 0


if __name__ == "__main__":
    raise SystemExit(main())
