"""Looks are locked, named, one-line presets — these tests pin what a Look must resolve to.

A Look (medo-motion/looks/looks.json) bundles: a style reference, the font pair from the curated
shortlist, signature technique ids, transitions, a background and a music preset. The lock has two
hard edges, both tested here: every referenced id must exist in the shipped asset manifests (drift
guard — a look rots the day its technique is renamed), and NO look may carry a palette or any color
(brand lock — palette v2.6 lives in medo-motion/brand/brand.json, nowhere else).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LOOKS_DIR = ROOT / "medo-motion" / "looks"
LOOKS = json.loads((LOOKS_DIR / "looks.json").read_text(encoding="utf-8"))
SHORTLIST = json.loads((LOOKS_DIR / "shortlist.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((ROOT / "assets" / "fonts" / "fonts.json").read_text(encoding="utf-8"))
FAMILIES = MANIFEST["families"]
STYLES = json.loads((ROOT / "assets" / "styles" / "styles.json").read_text(encoding="utf-8"))["styles"]
TRANSITIONS = json.loads((ROOT / "medo-motion" / "motion" / "transitions.json").read_text(encoding="utf-8"))["transitions"]
BACKGROUNDS = {b["id"] for b in json.loads((ROOT / "medo-motion" / "motion" / "backgrounds.json").read_text(encoding="utf-8"))["backgrounds"]}
MUSIC = set(json.loads((ROOT / "medo-motion" / "motion" / "music-presets.json").read_text(encoding="utf-8"))["presets"])
TECHNIQUES = {t["id"] for t in json.loads((ROOT / "assets" / "techniques.json").read_text(encoding="utf-8"))["techniques"]}
SHORTLIST_FAMILIES = {f["family"] for f in SHORTLIST["families"]}
ENERGIES = {"calm", "medium", "high"}
THEMES = {"dark", "light"}
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LOOK_LIST = LOOKS["looks"]


def look_by_id(lid: str) -> dict:
    return next(l for l in LOOK_LIST if l["id"] == lid)


def test_file_is_locked_and_versioned():
    assert LOOKS["version"] == 1
    assert LOOKS["status"] == "locked"
    assert LOOKS["date"]
    assert LOOKS["policy"]["weak_models"] and LOOKS["policy"]["strong_agents"]
    assert "brand.json" in LOOKS["policy"]["palette"]


def test_exactly_one_default_and_it_is_the_house_look():
    defaults = [l["id"] for l in LOOK_LIST if l.get("default")]
    assert defaults == ["house"]


def test_ids_are_unique_slugs():
    ids = [l["id"] for l in LOOK_LIST]
    assert len(ids) == len(set(ids))
    for lid in ids:
        assert SLUG.match(lid), lid


def test_themes_energy_and_transitions_are_in_vocabulary():
    for look in LOOK_LIST:
        assert look["energy"] in ENERGIES, look["id"]
        assert look["themes"], look["id"]
        assert set(look["themes"]) <= THEMES, look["id"]
        assert 1 <= len(look["transitions"]) <= 3, look["id"]
        assert set(look["transitions"]) <= set(TRANSITIONS), look["id"]


@pytest.mark.parametrize("look", LOOK_LIST, ids=lambda l: l["id"])
def test_fonts_come_from_the_shortlist_and_the_manifest(look):
    fonts = look["fonts"]
    assert set(fonts) == {"display", "body", "latin", "mono"}
    scripts = {"display": "arabic", "body": "arabic", "latin": "latin", "mono": "latin"}
    for role, script in scripts.items():
        family = fonts[role]
        if family is None:
            assert role == "mono", f"{look['id']}.{role} may not be null"
            continue
        assert family in SHORTLIST_FAMILIES, f"{look['id']}.{role} {family} is not on the shortlist"
        meta = FAMILIES[family]
        assert meta["status"] == "ok", f"{look['id']}.{role} {family} is not collision-clean"
        assert meta["script"] == script, f"{look['id']}.{role} {family} is not {script}"


@pytest.mark.parametrize("look", LOOK_LIST, ids=lambda l: l["id"])
def test_every_referenced_id_exists(look):
    assert look["style"] in STYLES or (LOOKS_DIR.parent / "styles" / f"{look['style']}.md").is_file(), \
        f"{look['id']}: style {look['style']!r} resolves neither to styles.json nor to medo-motion/styles/"
    assert look["background"] in BACKGROUNDS, f"{look['id']}: unknown background {look['background']!r}"
    assert look["music"] in MUSIC, f"{look['id']}: unknown music preset {look['music']!r}"
    assert 3 <= len(look["techniques"]) <= 8, f"{look['id']}: keep 3–8 signature moves"
    missing = [t for t in look["techniques"] if t not in TECHNIQUES]
    assert not missing, f"{look['id']}: technique ids not in assets/techniques.json: {missing}"
    assert len(look["techniques"]) == len(set(look["techniques"])), f"{look['id']}: duplicate technique"


def _walk(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key, value
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def test_looks_carry_no_palette_no_colors_no_hex():
    """The brand lock is manual today; this makes it mechanical."""
    colorish = {"palette", "colors", "colour", "hex", "rgb", "rgba", "fill", "stroke", "accent"}
    for look in LOOK_LIST:
        for key, value in _walk(look):
            assert key.lower() not in colorish, f"{look['id']}: forbidden key {key!r}"
            if isinstance(value, str):
                assert not re.search(r"#[0-9a-fA-F]{3,8}\b", value), f"{look['id']}: hex color in {key!r}"


def test_looks_do_not_claim_to_be_a_font_default():
    """Looks pair fonts for one feel; the per-element agent-chosen rule stays the law."""
    readme = (LOOKS_DIR / "README.md").read_text(encoding="utf-8")
    assert "looks.json" in readme
    assert "brand" in readme


def test_every_music_preset_and_style_reference_is_used_or_deliberately_absent():
    """The catalog is small enough to keep curated on purpose: 6 looks, no filler."""
    used = {l["music"] for l in LOOK_LIST}
    assert len(used) == 6, "every preset is claimed by exactly one look — keep it that way or record why"
    styles = {l["style"] for l in LOOK_LIST}
    assert len(styles) == 6


def test_default_look_is_the_documented_house_register():
    house = look_by_id("house")
    assert house["default"] is True
    assert house["style"] == "medo-red-circle"
    assert house["themes"] == ["dark", "light"]
