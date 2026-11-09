"""Scene recipes are the studio's answer to «لمشهد زي ده أعمل إيه؟» — these tests hold the answer honest.

A recipe (medo-motion/recipes/recipes.json) names the engine, the plan files the project must
produce, the validators that gate the scene and the looks/signature moves that fit it. Everything
it references must exist: validators and docs are checked as repository paths, looks against
looks.json, technique ids against assets/techniques.json. A recipe may be opinionated; it may not
rot.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECIPES = json.loads((ROOT / "medo-motion" / "recipes" / "recipes.json").read_text(encoding="utf-8"))
LOOK_IDS = {l["id"] for l in json.loads((ROOT / "medo-motion" / "looks" / "looks.json").read_text(encoding="utf-8"))["looks"]}
TECHNIQUES = {t["id"] for t in json.loads((ROOT / "assets" / "techniques.json").read_text(encoding="utf-8"))["techniques"]}
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PLAN_FILE = re.compile(r"^plan/[a-z0-9_/-]+(<[a-z0-9_-]+>)?[a-z0-9_/-]*\.json$")
PLAN_DIR = re.compile(r"^plan/[a-z0-9_/-]+/<[a-z0-9_-]+>\.json$")
RECIPE_LIST = RECIPES["recipes"]


def recipe_by_id(rid: str) -> dict:
    return next(r for r in RECIPE_LIST if r["id"] == rid)


def test_file_is_curated_and_versioned():
    assert RECIPES["version"] == 1
    assert RECIPES["status"] in {"locked", "curated"}
    assert RECIPES["date"]
    assert RECIPES["policy"]["weak_models"] and RECIPES["policy"]["strong_agents"]


def test_ids_are_unique_slugs():
    ids = [r["id"] for r in RECIPE_LIST]
    assert len(ids) == len(set(ids))
    for rid in ids:
        assert SLUG.match(rid), rid


def test_engines_come_from_the_studio_vocabulary():
    for recipe in RECIPE_LIST:
        engines = recipe["engines"]
        assert engines, recipe["id"]
        assert set(engines) <= {"p", "k", "r"}, f"{recipe['id']}: hybrid is a pipeline choice, not a scene recipe"
        assert len(engines) == len(set(engines)), recipe["id"]
        assert isinstance(recipe["ui"], bool), recipe["id"]


def test_use_when_and_avoid_when_are_written():
    for recipe in RECIPE_LIST:
        assert len(recipe["use_when"].strip()) >= 20, recipe["id"]
        assert len(recipe["avoid_when"].strip()) >= 10, recipe["id"]
        assert recipe["use_when"] != recipe["avoid_when"], recipe["id"]


def test_arc_is_a_short_playable_sequence():
    for recipe in RECIPE_LIST:
        arc = recipe["arc"]
        assert 2 <= len(arc) <= 6, recipe["id"]
        assert all(isinstance(step, str) and step.strip() for step in arc), recipe["id"]


def test_required_plan_files_look_like_plan_files():
    for recipe in RECIPE_LIST:
        for req in recipe["requires"]:
            assert PLAN_FILE.match(req) or PLAN_DIR.match(req), f"{recipe['id']}: {req!r}"
        assert len(recipe["requires"]) == len(set(recipe["requires"])), recipe["id"]


def test_every_required_plan_file_is_part_of_the_studio_contract():
    """A recipe may only name plan files the studio actually reads or writes — a typo'd filename fails here."""
    sources = []
    for base in ("tools", "docs", "medo-motion/skills", "medo-motion/templates"):
        for path in (ROOT / base).rglob("*"):
            if path.suffix in {".py", ".js", ".mjs", ".ts", ".tsx", ".md"} and path.is_file():
                try:
                    sources.append(path.read_text(encoding="utf-8", errors="ignore"))
                except OSError:
                    continue
    haystack = "\n".join(sources)
    for recipe in RECIPE_LIST:
        for req in recipe["requires"]:
            if "<" in req:
                stem = req.split("<", 1)[0].rsplit("/", 1)[0] + "/"
                assert stem in haystack, f"{recipe['id']}: {req!r} — the directory is never mentioned in the studio"
                continue
            assert req in haystack, f"{recipe['id']}: {req!r} is never mentioned by any tool or doc"


def test_validators_exist_in_the_repository():
    for recipe in RECIPE_LIST:
        assert recipe["validators"], recipe["id"]
        for validator in recipe["validators"]:
            assert (ROOT / validator).is_file(), f"{recipe['id']}: missing validator {validator}"


def test_docs_exist_in_the_repository():
    for recipe in RECIPE_LIST:
        assert (ROOT / recipe["docs"]).is_file(), f"{recipe['id']}: missing docs {recipe['docs']}"


def test_recommended_looks_exist():
    for recipe in RECIPE_LIST:
        assert recipe["looks"], recipe["id"]
        unknown = [l for l in recipe["looks"] if l not in LOOK_IDS]
        assert not unknown, f"{recipe['id']}: unknown looks {unknown}"


def test_signature_techniques_exist_in_the_library():
    for recipe in RECIPE_LIST:
        assert 1 <= len(recipe["techniques"]) <= 8, recipe["id"]
        missing = [t for t in recipe["techniques"] if t not in TECHNIQUES]
        assert not missing, f"{recipe['id']}: technique ids not in assets/techniques.json: {missing}"


def test_ui_recipes_name_the_files_a_screen_scene_needs():
    """A UI scene that never changes is a mock — the lint enforces events; the recipes must not fight it."""
    for recipe in RECIPE_LIST:
        if recipe["ui"]:
            assert recipe["techniques"], recipe["id"]
            assert any("copy" in r for r in recipe["requires"]), recipe["id"]
            assert any("text-direction" in r for r in recipe["requires"]), recipe["id"]


def test_no_recipe_references_the_other_namespaces():
    for recipe in RECIPE_LIST:
        for req in recipe["requires"]:
            assert ".." not in req, recipe["id"]
        assert "projects/" not in json.dumps(recipe), recipe["id"]
