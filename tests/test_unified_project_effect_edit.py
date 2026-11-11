"""Effects can be authored without silently discarding curves."""
import copy
import json
import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from unified_project_effect_edit import (  # noqa: E402
    add_effect,
    enable_effects_contract,
    remove_curve,
    remove_effect,
    replace_effect,
    set_curve,
)
from unified_project_effects import effect_value  # noqa: E402
from unified_project_history import History  # noqa: E402
from unified_project_store import load, save  # noqa: E402


def project():
    return json.loads((ROOT / "tests/fixtures/unified_project/basic.json").read_text(encoding="utf-8"))


def effect():
    return {"id": "fx", "type": "opacity", "version": 1, "enabled": True, "params": {"value": 6000}}


def curve():
    return {"effectId": "fx", "property": "value", "points": [
        {"t": 0, "value": 0, "interpolation": "linear"},
        {"t": 100, "value": 10000, "interpolation": "linear"}]}


def test_effect_authoring_roundtrip_and_undo(tmp_path):
    p = project()
    e, c = effect(), curve()
    with pytest.raises(ValueError):
        add_effect(p, "c1", e)
    h = History(p)
    h.apply(enable_effects_contract)
    h.apply(add_effect, "c1", e)
    h.apply(set_curve, "c1", c)
    e["params"]["value"] = 0
    c["points"][0]["value"] = 5000
    assert effect_value(h.project, "c1", "fx", 50) == Fraction(1, 2)
    with pytest.raises(ValueError, match="curve first"):
        h.apply(remove_effect, "c1", "fx")
    h.apply(remove_curve, "c1", "fx")
    assert effect_value(h.project, "c1", "fx", 50) == Fraction(3, 5)
    h.undo()
    assert effect_value(h.project, "c1", "fx", 50) == Fraction(1, 2)
    path = tmp_path / "p.json"
    rev = save(path, h.project)
    assert load(path) == (h.project, rev)
    h.apply(remove_curve, "c1", "fx")
    h.apply(remove_effect, "c1", "fx")
    assert not h.project["tracks"][0]["clips"][0]["effects"]
    assert p == project()


def test_replace_and_rejections():
    p = add_effect(enable_effects_contract(project()), "c1", effect())
    p = set_curve(p, "c1", curve())
    replacement = curve()
    replacement["points"][-1]["value"] = 8000
    p = set_curve(p, "c1", replacement)
    assert effect_value(p, "c1", "fx", 50) == Fraction(2, 5)
    e = effect()
    e["enabled"] = False
    p = replace_effect(p, "c1", "fx", e)
    assert effect_value(p, "c1", "fx", 50) is None
    before = copy.deepcopy(p)
    for operation in (
        lambda: replace_effect(p, "c1", "fx", {**e, "id": "changed"}),
        lambda: set_curve(p, "c1", {**curve(), "effectId": "missing"}),
        lambda: set_curve(p, "c1", None),
        lambda: remove_curve(p, "c1", "missing"),
        lambda: remove_effect(p, "c1", "missing"),
        lambda: add_effect(p, "c1", effect()),
    ):
        with pytest.raises(ValueError):
            operation()
        assert p == before
