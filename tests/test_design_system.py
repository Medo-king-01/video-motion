"""The unified design system reference exists and the normative docs stay aligned.

DESIGN_SYSTEM.md is the single human-facing index. These tests guard against the old
"forced Cairo default" / boxed-caption wording creeping back into the active contract,
and keep the design.html style board inside the brand palette + font manifest.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "medo-motion"
DOC = ROOT / "DESIGN_SYSTEM.md"


def test_design_system_doc_exists_and_indexes_the_sources():
    text = DOC.read_text(encoding="utf-8")
    for needle in [
        "brand/brand.json",
        "assets/fonts/fonts.json",
        "plan/text-direction.json",
        "medo-motion/motion/easings.json",
        "TASTE.md",
        "STYLE.md",
        "plan/design.html",
        "reel_lint.py",
        "brand_check.py",
    ]:
        assert needle in text, f"DESIGN_SYSTEM.md does not reference {needle}"
    assert "T04" in text and "T05" in text
    assert "unboxed" in text or "من غير صندوق" in text


def test_indexes_link_to_the_design_system():
    assert "DESIGN_SYSTEM.md" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "DESIGN_SYSTEM.md" in (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "DESIGN_SYSTEM.md" in (ROOT / "AGENTS.md").read_text(encoding="utf-8")


def test_no_forced_cairo_default_in_active_docs():
    checks = {
        ROOT / "README.md": ["Cairo الافتراضي", "بالِت ١٢ لون + Cairo"],
        SKILL / "templates" / "STYLE.md": ["Cairo for Arabic"],
        SKILL / "styles" / "README.md": ["وخطوط هوية ميدو المقفولة"],
        SKILL / "brand" / "BRAND.md": ["Cairo (ExtraBold/Bold) للعربي"],
    }
    for path, banned in checks.items():
        text = path.read_text(encoding="utf-8")
        for phrase in banned:
            assert phrase not in text, f"{path.relative_to(ROOT)} still forces a default: {phrase!r}"


def test_font_manifest_roles_are_not_creative_defaults():
    manifest = json.loads((ROOT / "assets" / "fonts" / "fonts.json").read_text(encoding="utf-8"))
    assert "default" not in manifest, "the manifest must not declare a creative default"
    for family in ("Cairo", "Inter"):
        meta = manifest["families"][family]
        assert "default" not in meta["role"].lower() or "not a forced" in meta["role"].lower()
        assert "default" not in meta["tags"]


def test_brand_caption_is_unboxed_and_style_required():
    brand = json.loads((SKILL / "brand" / "brand.json").read_text(encoding="utf-8"))
    cap = brand["caption"]
    assert cap["boxed"] is False
    assert cap["border"] == "none"
    assert "text-direction.json" in cap["style"]


def test_design_board_uses_brand_palette_and_manifest_fonts():
    html = (SKILL / "templates" / "design.html").read_text(encoding="utf-8")
    m = re.search(r"const DESIGN = \{(.*?)\n\};", html, re.S)
    assert m, "design.html must keep a DESIGN object"
    obj = m.group(1)
    brand = json.loads((SKILL / "brand" / "brand.json").read_text(encoding="utf-8"))
    allowed = {v["hex"].upper() for v in brand["palette"].values() if isinstance(v, dict) and "hex" in v}
    allowed |= {v["hex"].upper() for v in brand.get("derived", {}).values() if isinstance(v, dict) and "hex" in v}
    hexes = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", obj)}
    assert hexes <= allowed, f"design board palette drifts from brand.json: {hexes - allowed}"
    assert "fontshare.com" not in obj
    manifest = json.loads((ROOT / "assets" / "fonts" / "fonts.json").read_text(encoding="utf-8"))["families"]
    for family in re.findall(r'family:\s*"([^"]+)"', obj):
        assert family in manifest, f"design board names a non-manifest font: {family}"
