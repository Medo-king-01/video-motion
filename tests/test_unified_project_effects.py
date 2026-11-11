"""Experimental 1.1 effect and keyframe contract."""
import copy
import json
import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from unified_project_check import SCHEMA, _shape, validate  # noqa: E402
from unified_project_edit import move_clip, ripple_delete, split_clip, trim_clip  # noqa: E402
from unified_project_effects import effect_value  # noqa: E402
from unified_project_store import load, save  # noqa: E402


def animated():
    p = json.loads((ROOT / "tests/fixtures/unified_project/basic.json").read_text())
    p["schemaVersion"] = "1.1"
    clip = p["tracks"][0]["clips"][0]
    clip["effects"] = [{"id": "fx", "type": "opacity", "version": 1,
                        "enabled": True, "params": {"value": 8000}}]
    clip["keyframes"] = [{"effectId": "fx", "property": "value", "points": [
        {"t": 100, "value": 2000, "interpolation": "linear"},
        {"t": 200, "value": 6000, "interpolation": "linear"},
        {"t": 300, "value": 10000, "interpolation": "hold"},
    ]}]
    return p


def test_evaluation_and_boundaries():
    p = animated()
    assert validate(p) == []
    assert [effect_value(p, "c1", "fx", t) for t in (0, 100, 150, 200, 250, 300, 480000)] == [
        Fraction(1, 5), Fraction(1, 5), Fraction(2, 5), Fraction(3, 5),
        Fraction(3, 5), Fraction(1), Fraction(1)]
    clip = p["tracks"][0]["clips"][0]
    clip["keyframes"] = []
    assert effect_value(p, "c1", "fx", 0) == Fraction(4, 5)
    clip["effects"][0]["enabled"] = False
    assert effect_value(p, "c1", "fx", 0) is None
    for t in (-1, True, 480001):
        with pytest.raises(ValueError):
            effect_value(p, "c1", "fx", t)
    with pytest.raises(ValueError):
        effect_value(p, "c1", "missing", 0)


@pytest.mark.parametrize("change,code", [
    (lambda p, c: p.update(schemaVersion="1.0"), "U01"),
    (lambda p, c: c["effects"][0].update(version=True), "U01"),
    (lambda p, c: c["keyframes"][0].update(points=[]), "U01"),
    (lambda p, c: c["effects"][0].update(id="c1"), "U03"),
    (lambda p, c: c["effects"][0].update(type="gain"), "U06"),
    (lambda p, c: c["effects"][0]["params"].update(value=10001), "U06"),
    (lambda p, c: c["keyframes"][0].update(effectId="missing"), "U06"),
    (lambda p, c: c["keyframes"].append(copy.deepcopy(c["keyframes"][0])), "U06"),
    (lambda p, c: c["keyframes"][0]["points"][1].update(t=100), "U06"),
    (lambda p, c: c["keyframes"][0]["points"][1].update(t=480001), "U06"),
    (lambda p, c: c["keyframes"][0]["points"][0].update(value=10001), "U06"),
])
def test_rejections(change, code):
    p = animated()
    change(p, p["tracks"][0]["clips"][0])
    assert any(e.startswith(code) for e in validate(p))


def test_audio_gain_and_compatibility():
    p = animated()
    p["tracks"][0]["kind"] = "audio"
    p["assets"][0]["kind"] = "audio"
    clip = p["tracks"][0]["clips"][0]
    clip["effects"][0]["type"] = "gain"
    clip["effects"][0]["params"]["value"] = 20000
    clip["keyframes"][0]["points"][-1]["value"] = 20000
    assert validate(p) == []
    assert effect_value(p, "c1", "fx", 300) == 2
    clip["effects"][0]["type"] = "opacity"
    assert any(e.startswith("U06") for e in validate(p))


def test_safe_edits_and_storage(tmp_path):
    p = animated()
    before = copy.deepcopy(p)
    with pytest.raises(ValueError, match="split"):
        split_clip(p, "c1", 100, "c2")
    with pytest.raises(ValueError, match="trim"):
        trim_clip(p, "c1", 100, 480000)
    assert p == before
    assert trim_clip(p, "c1", 0, 480000) == p
    assert move_clip(p, "c1", "v1", 0) == p
    assert ripple_delete(p, 0, 480000, ["v1"])["tracks"][0]["clips"] == []
    path = tmp_path / "project.json"
    save(path, p)
    assert load(path)[0] == p


def test_shape_matches_json_schema_for_samples():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    samples = [animated()]
    for mutate in (
        lambda p: p.update(schemaVersion="1.0"),
        lambda p: p["tracks"][0]["clips"][0]["keyframes"][0].update(points=[]),
        lambda p: p["tracks"][0]["clips"][0]["effects"][0].update(version=True),
    ):
        p = animated()
        mutate(p)
        samples.append(p)
    for p in samples:
        assert (not _shape(p, schema, schema)) == jsonschema.Draft202012Validator(schema).is_valid(p)
