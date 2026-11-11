"""Graph compilation is deterministic and does not imply rendering support."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from unified_render_graph import BACKENDS, InvalidProject, compile_project, graph_digest, preflight  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/unified_project/basic.json"
TOOL = ROOT / "tools/unified_render_graph.py"


def project():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_plan_exact_ranges_and_order():
    p = project()
    p["duration"] = 480001
    clip = p["tracks"][0]["clips"][0]
    clip.update(start=1, duration=479999)
    p["tracks"].append({"id": "empty", "kind": "text", "enabled": False, "clips": []})
    before = copy.deepcopy(p)
    g = compile_project(p)
    assert p == before
    assert g["project"] == p
    assert g["clock"] == {"frameTicks": 8000, "audioSampleTicks": 5,
                          "frameCount": 61, "audioSampleCount": 96001}
    assert g["tracks"][0]["clips"][0] == {
        "clipId": "c1", "projectPath": "$.tracks[0].clips[0]", "assetId": "a1",
        "tickRange": [1, 480000], "sampleRange": [1, 60]}
    assert [t["trackId"] for t in g["tracks"]] == ["v1", "empty"]
    assert not g["executable"]
    g["project"]["tracks"][0]["clips"][0]["start"] = 99
    assert p == before


def test_sample_ranges_match_half_open_timestamps():
    p = project()
    p["duration"] = 48001
    clip = p["tracks"][0]["clips"][0]
    for start, end in ((0, 1), (1, 7999), (1, 8000), (8000, 8001), (7999, 16001)):
        clip.update(start=start, duration=end - start)
        g = compile_project(p)
        first, stop = g["tracks"][0]["clips"][0]["sampleRange"]
        expected = [i for i in range(g["clock"]["frameCount"]) if start <= i * 8000 < end]
        assert list(range(first, stop)) == expected


def test_digest_is_deterministic_and_sensitive():
    p = project()
    assert graph_digest(compile_project(p)) == graph_digest(compile_project(copy.deepcopy(p)))
    p["seed"] += 1
    assert graph_digest(compile_project(p)) != graph_digest(compile_project(project()))


def test_audio_samples_and_disabled_track():
    p = project()
    p["tracks"][0].update(kind="audio", enabled=False)
    p["assets"][0]["kind"] = "audio"
    p["tracks"][0]["clips"][0].update(start=1, duration=9)
    g = compile_project(p)
    assert g["tracks"][0]["clips"][0]["sampleRange"] == [1, 2]
    assert g["tracks"][0]["enabled"] is False


def test_effects_are_preserved_without_support():
    p = project()
    p["schemaVersion"] = "1.1"
    clip = p["tracks"][0]["clips"][0]
    clip["effects"] = [{"id": "fx", "type": "opacity", "version": 1,
                        "enabled": True, "params": {"value": 5000}}]
    clip["keyframes"] = [{"effectId": "fx", "property": "value", "points": [
        {"t": 0, "value": 10000, "interpolation": "hold"}]}]
    assert compile_project(p)["project"] == p
    assert preflight(p, "P")["status"] == "unsupported"


@pytest.mark.parametrize("backend", BACKENDS)
def test_backends_fail_closed_even_for_empty_project(backend):
    p = project()
    p.update(duration=0, tracks=[], assets=[])
    result = preflight(p, backend)
    assert result["status"] == "unsupported"
    assert result["diagnostics"][0]["code"] == "R01"
    assert result["graphSha256"] == graph_digest(compile_project(p))


def test_invalid_and_unknown_are_rejected():
    p = project()
    p["tracks"][0]["clips"][0]["assetId"] = "missing"
    with pytest.raises(InvalidProject) as exc:
        compile_project(p)
    assert any(e.startswith("U03") for e in exc.value.diagnostics)
    with pytest.raises(InvalidProject):
        preflight(p, "P")
    with pytest.raises(ValueError, match="Unknown backend"):
        preflight(project(), "invented")


def test_cli_output_and_fail_closed(tmp_path):
    run = subprocess.run([sys.executable, str(TOOL), str(FIXTURE)], capture_output=True, text=True)
    assert run.returncode == 0
    assert not json.loads(run.stdout)["executable"]
    run = subprocess.run([sys.executable, str(TOOL), str(FIXTURE), "--backend", "Hybrid"],
                         capture_output=True, text=True)
    assert run.returncode == 1
    assert json.loads(run.stdout)["status"] == "unsupported"
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"id":1,"id":2}')
    run = subprocess.run([sys.executable, str(TOOL), str(invalid)], capture_output=True, text=True)
    assert run.returncode == 1
    assert not run.stdout
