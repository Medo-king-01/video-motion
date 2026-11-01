"""The technique library: a measured catalogue, a reproducible draw, and no length rule.

The draw is the point. An agent choosing by hand picks the same fade-up, push-in and end card in
every film; these tests pin that the draw actually varies with the seed, respects the energy and
format filters, never repeats an id, and stays connected to the docs.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "techniques.py"
LIB = ROOT / "assets" / "techniques.json"
sys.path.insert(0, str(ROOT / "tools"))

import techniques  # noqa: E402

DATA = techniques.load(LIB)


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


def test_library_is_valid():
    assert techniques.validate(DATA) == []


def test_library_shape():
    picks = DATA["techniques"]
    assert len(picks) >= 30, "a draw from fewer than 30 entries converges again"
    ids = {e["id"] for e in picks}
    assert len(ids) == len(picks)
    order = DATA["format"]["reel"]["order"]
    assert set(order) <= {e["category"] for e in picks}
    for e in picks:
        assert len(e["how"]) > 60, f"{e['id']}: 'how' must be a build step, not a mood"
        assert e["primitive"] in techniques.PRIMITIVES
        assert e["role"] in techniques.ROLES


API_SURFACE = sorted({
    n for f in [*(ROOT / "medo-motion" / "templates" / "procedural-reels").glob("*.py"),
                *(ROOT / "medo-motion" / "templates" / "render" / "lib").glob("*.js")]
    for n in re.findall(r"(?:^def |^export (?:function|const|class) )(\w+)", f.read_text(encoding="utf-8"), re.M)
    if len(n) > 2
})


def test_each_recipe_names_a_real_api():
    """A recipe must point at code this studio actually has, so it is buildable the day it is drawn."""
    for e in DATA["techniques"]:
        assert any(api in e["how"] for api in API_SURFACE), f"{e['id']}: no known API in 'how'"


def test_recipes_were_rewritten_for_this_studio():
    """The library is adapted from cinetic (MIT); a copied React recipe would mean it was not."""
    foreign = ("useCurrentFrame", "AbsoluteFill", "Remotion", "gsap", "npm ", "src/brand/tokens")
    for e in DATA["techniques"]:
        for token in foreign:
            assert token not in e["how"], f"{e['id']}: still speaks {token}"


def test_every_primitive_maps_to_a_shipped_module():
    need = {
        "type": ["procedural-reels/lib.py", "render/lib/kit.js"],
        "grid": ["procedural-reels/beat.py", "render/lib/beat.js"],
        "camera": ["procedural-reels/lib.py", "render/lib/motion.js"],
        "depth": ["procedural-reels/space3d.py", "render/lib/space3d.js"],
        "transition": ["procedural-reels/transition.py", "render/lib/transition.js"],
        "layout": ["procedural-reels/presenter.py", "render/lib/presenter.js"],
        "finish": ["render/lib/kit.js"],
        "blur": ["render/lib/kit.js"],
        "sound": ["procedural-reels/sfx.py"],
        "timeline": ["procedural-reels/lib.py"],
    }
    base = ROOT / "medo-motion" / "templates"
    for primitive, paths in need.items():
        assert primitive in techniques.PRIMITIVES
        for rel in paths:
            assert (base / rel).is_file(), f"primitive '{primitive}' points at missing {rel}"


def test_draw_is_reproducible():
    a = techniques.draw(DATA, 24, "calm", seed=41)
    b = techniques.draw(DATA, 24, "calm", seed=41)
    assert [p["id"] for p in a["picks"]] == [p["id"] for p in b["picks"]]
    assert a["seed"] == 41


def test_draw_varies_with_the_seed():
    plans = {tuple(p["id"] for p in techniques.draw(DATA, 24, "calm", seed=s)["picks"]) for s in range(12)}
    assert len(plans) >= 8, "the draw must not converge on one plan"


def test_plan_size_comes_from_the_length():
    fmt = DATA["format"]["reel"]
    assert techniques.plan_size(fmt, 10, "calm") == techniques.MIN_PICKS
    assert techniques.plan_size(fmt, 24, "calm") == 7
    assert techniques.plan_size(fmt, 24, "medium") > techniques.plan_size(fmt, 24, "calm")
    assert techniques.plan_size(fmt, 600, "calm") == len(fmt["order"])


def test_calm_never_draws_a_high_energy_move():
    for seed in range(30):
        for p in techniques.draw(DATA, 30, "calm", seed=seed)["picks"]:
            assert p["energy"] != "high", f"seed {seed} drew {p['id']}"


def test_energy_high_can_draw_high():
    drawn = {p["id"] for seed in range(20) for p in techniques.draw(DATA, 30, "high", seed=seed)["picks"]}
    assert any(e["energy"] == "high" and e["id"] in drawn for e in DATA["techniques"])


def test_no_id_repeats_and_signatures_are_budgeted():
    for seed in range(20):
        picks = techniques.draw(DATA, 45, "medium", seed=seed)["picks"]
        ids = [p["id"] for p in picks]
        assert len(ids) == len(set(ids))
        sigs = sum(1 for p in picks if p["role"] == "signature")
        assert sigs <= (2 if len(picks) >= 10 else 1)


def test_exclude_rerolls_and_category_filters():
    first = techniques.draw(DATA, 24, "calm", seed=41)["picks"][0]
    second = techniques.draw(DATA, 24, "calm", seed=41, exclude=[first["id"]])["picks"]
    assert first["id"] not in [p["id"] for p in second]
    camera = techniques.draw(DATA, 24, "calm", seed=3, only="camera")["picks"]
    assert camera and all(p["category"] == "camera" for p in camera)


def test_from_plan_reads_the_vo_length(tmp_path):
    plan = tmp_path / "beats.json"
    plan.write_text(json.dumps({"duration": 18.4, "scenes": []}), encoding="utf-8")
    out = tmp_path / "picks.json"
    r = run("--from-plan", str(plan), "--json", str(out), "--seed", "5")
    assert r.returncode == 0, r.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["seconds"] == 18.4
    assert len(payload["picks"]) == techniques.plan_size(DATA["format"]["reel"], 18.4, "calm")
    assert {"id", "how", "timing", "bans"} <= set(payload["picks"][0])


def test_from_plan_without_a_duration_asks_for_the_vo(tmp_path):
    plan = tmp_path / "beats.json"
    plan.write_text(json.dumps({"duration": None, "scenes": []}), encoding="utf-8")
    r = run("--from-plan", str(plan))
    assert r.returncode == 2
    assert "vo_length.py" in r.stderr


def test_cli_list_show_validate():
    assert run("--validate").returncode == 0
    listing = run("--list", "--category", "camera")
    assert listing.returncode == 0 and "cam-" in listing.stdout
    shown = run("--show", "tr-velocity-handoff-cut")
    assert shown.returncode == 0 and "velocity" in shown.stdout.lower()
    assert run("--show", "no-such-id").returncode == 2


def test_docs_are_generated_from_the_library(tmp_path):
    out = tmp_path / "techniques.md"
    assert run("--markdown", str(out)).returncode == 0
    assert "Velocity handoff cut" in out.read_text(encoding="utf-8")
    docs = ROOT / "docs" / "techniques.md"
    assert docs.is_file(), "docs/techniques.md must exist (make techniques-doc)"
    assert run("--markdown", str(docs), "--check").returncode == 0, "docs/techniques.md is stale"
