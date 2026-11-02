"""Style recipes must only name registered easings and manifest fonts — no silent fallbacks.

The engines now *throw* on an unknown easing (lib/motion.js, motion.py) instead of silently
drawing easeOut, and every family on screen must be in assets/fonts/fonts.json (SIL OFL 1.1).
These tests keep medo-motion/styles/*.md honest against both catalogs.
"""
from __future__ import annotations

import json
import re

from conftest import ROOT, SKILL

EASINGS = json.loads((SKILL / "motion" / "easings.json").read_text(encoding="utf-8"))
EASING_NAMES = set(EASINGS["cubicBezier"]) | set(EASINGS["formulas"])
MANIFEST = json.loads((ROOT / "assets" / "fonts" / "fonts.json").read_text(encoding="utf-8"))
FAMILIES = MANIFEST["families"]

WORD_WEIGHTS = {"regular": 400, "medium": 500, "semibold": 600, "bold": 700,
                "extrabold": 800, "black": 900, "light": 300, "thin": 100}

STYLES = sorted((SKILL / "styles").glob("*.md"))

# an easing-looking token = root + variant suffix (easeInOut, backOut, outCubic, ...);
# bare prose words ("elastic", "back", "Circle") do not match because the suffix is required
EASING_ROOTS = ("ease", "back", "expo", "quad", "quint", "circ", "sine", "elastic", "bounce",
                "anticipate", "smooth", "linear", "in", "out")
EASING_TOKEN = re.compile(
    r"\b((?:" + "|".join(EASING_ROOTS) + r")(?:InOut|In|Out|Cubic|Quad|Quint|Expo|Sine|Circ|Elastic|Bounce|Back))\b")
# **Family Name 700** or **Family Name** inside the fonts section
BOLD = re.compile(r"\*\*([^*]+)\*\*")


def _font_sections(text: str) -> str:
    m = re.search(r"^## الخطوط\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


def test_styles_exist():
    assert len(STYLES) >= 8


def test_styles_use_only_registered_easings():
    for path in STYLES:
        if path.name.startswith("_"):
            continue
        for token in EASING_TOKEN.findall(path.read_text(encoding="utf-8")):
            assert token in EASING_NAMES, \
                f"{path.name}: unknown easing {token!r} — see medo-motion/motion/easings.json"


def test_styles_use_only_manifest_fonts_and_weights():
    for path in STYLES:
        section = _font_sections(path.read_text(encoding="utf-8"))
        if not section:
            continue
        for bold in BOLD.findall(section):
            for part in re.split(r"\s+[ أو+]\s+", bold):
                part = part.strip()
                if not part or not re.search(r"[A-Za-z\u0600-\u06FF]", part):
                    continue
                m = re.match(r"^(.*?)\s*(\d{3})?$", part)
                name, weight = m.group(1).strip(), m.group(2)
                wm = re.search(r"(ExtraBold|Black|Bold|SemiBold|Medium|Regular|Light|Thin)$", name, re.I)
                if weight is None and wm:
                    weight = str(WORD_WEIGHTS[wm.group(1).lower()])
                    name = name[: wm.start()].strip()
                if name.lower() in ("seeded", "rtl", "ltr"):
                    continue
                assert name in FAMILIES, f"{path.name}: font {name!r} is not in assets/fonts/fonts.json"
                if weight is not None:
                    have = {w["weight"] for w in FAMILIES[name]["weights"]}
                    assert int(weight) in have, \
                        f"{path.name}: {name} has no weight {weight} (available: {sorted(have)})"


def test_style_palettes_declare_brand_conversion():
    """Non-brand palettes are allowed only as a *labelled* stylistic reference; a palette made
    purely of brand.json colours (e.g. medo-red-circle) needs no disclaimer."""
    brand = json.loads((SKILL / "brand" / "brand.json").read_text(encoding="utf-8"))
    brand_hexes = {v["hex"].upper() for v in brand["palette"].values() if isinstance(v, dict) and "hex" in v}
    brand_hexes |= {v["hex"].upper() for v in brand.get("derived", {}).values() if isinstance(v, dict) and "hex" in v}
    for path in STYLES:
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")
        if "## الألوان" not in text:
            continue
        section = text.split("## الألوان", 1)[1].split("## ", 1)[0]
        hexes = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", section)}
        assert "brand.json" in section or hexes <= brand_hexes, \
            f"{path.name}: palette section must state that colours map to brand.json tokens"
