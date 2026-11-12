"""Hybrid is a routing decision made explicit — and it may not pretend to draw what P draws.

The test that matters: the routing table is data, a graphics track is a refusal rather than a
skipped track, and a rendered frame carries the routing that produced it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import adapter_hybrid  # noqa: E402
import render_backend  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/unified_project/basic.json"


def project() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _point_at_a_real_frame(project_dict: dict, root: Path) -> None:
    """The fixture's URI has no bytes behind it; give the renderer a one-frame PPM to decode."""
    import hashlib

    media = root / "media"
    media.mkdir(parents=True, exist_ok=True)
    size = (project_dict["profile"]["width"], project_dict["profile"]["height"])
    payload = (f"P6\n{size[0]} {size[1]}\n255\n".encode("ascii")
               + bytes([40, 80, 120]) * (size[0] * size[1]))
    (media / "shot.ppm").write_bytes(payload)
    asset = project_dict["assets"][0]
    asset["uri"] = "media/shot.ppm"
    asset["kind"] = "image"
    asset["sha256"] = hashlib.sha256(payload).hexdigest()
    asset.pop("duration", None)


def test_hybrid_conforms_to_the_contract() -> None:
    adapter = adapter_hybrid.HybridAdapter()
    assert render_backend.conformance_problems(adapter) == []
    assert adapter.capabilities()["backend"] == "Hybrid"


def test_every_drawing_track_routes_to_the_backend_that_can_draw_it() -> None:
    adapter = adapter_hybrid.HybridAdapter()
    graph = adapter.compile(project())
    routing = {entry["trackId"]: entry for entry in graph["routing"]}
    for track in graph["tracks"]:
        if track.get("enabled", True):
            assert routing[track["trackId"]]["backend"] == "P", routing[track["trackId"]]
    assert graph["executable"] is True
    assert "graphSha256" in graph


def test_a_track_no_backend_can_draw_is_refused_not_dropped() -> None:
    """Validated projects cannot reach this today (the checker rejects such a clip first), so the
    routing guard is exercised directly on a graph — the day an importer produces one, it refuses."""
    adapter = adapter_hybrid.HybridAdapter()
    graph = {"tracks": [{"trackId": "g1", "kind": "graphics", "enabled": True,
                         "clips": [{"clipId": "gc1"}]}]}
    assert [item["code"] for item in adapter.refusals(graph)] == ["R12"]
    assert adapter.route(graph)[0]["backend"] is None


def test_an_empty_track_is_not_a_refusal() -> None:
    adapter = adapter_hybrid.HybridAdapter()
    graph = {"tracks": [{"trackId": "g1", "kind": "graphics", "enabled": True, "clips": []}]}
    assert adapter.refusals(graph) == []
    assert adapter.route(graph)[0]["reason"].startswith("track is empty")


def test_a_disabled_track_is_not_routed_and_not_refused() -> None:
    adapter = adapter_hybrid.HybridAdapter()
    quiet = project()
    quiet["tracks"][0]["enabled"] = False
    decisions = adapter.route(adapter.compile(quiet))
    first = next(decision for decision in decisions if decision["trackId"] == "v1")
    assert first["backend"] is None and "disabled" in first["reason"]
    assert adapter.preflight(adapter.compile(quiet))["status"] == "supported"


def test_rendering_delegates_and_records_the_routing(tmp_path: Path) -> None:
    adapter = adapter_hybrid.HybridAdapter()
    rendered = project()
    _point_at_a_real_frame(rendered, tmp_path)
    graph = adapter.compile(rendered)
    result = adapter.render(graph, (0, 1), tmp_path / "out", {"root": tmp_path})
    assert result["routedBy"] == "Hybrid"
    assert result["routing"] == graph["routing"]
    assert (tmp_path / "out" / "frame-00000.rgba").is_file()


def test_the_cli_prints_capabilities_and_preflight() -> None:
    import subprocess

    tool = str(ROOT / "tools/adapter_hybrid.py")
    caps = subprocess.run([sys.executable, tool, "--capabilities"], capture_output=True, text=True, timeout=60)
    assert caps.returncode == 0 and json.loads(caps.stdout)["backend"] == "Hybrid"
    pre = subprocess.run([sys.executable, tool, str(FIXTURE), "--preflight"],
                         capture_output=True, text=True, timeout=60)
    assert pre.returncode == 1
    assert json.loads(pre.stdout)["status"] in ("supported", "unsupported")
