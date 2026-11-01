"""The type system: 14 free families, real shaping, and a gate against broken ones.

Everything on screen must be free (SIL OFL 1.1) and must actually render Arabic correctly with the
engine's own stack. The overlap check below is a regression test for a real failure: Reem Kufi's
static instants have advances narrower than their outlines, so words collided — 0.27 overlap against
≤ 0.14 for every healthy family.
"""
from __future__ import annotations

import json
from pathlib import Path

import arabic_shape
import freetype
import lib
import numpy as np
import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "assets" / "fonts"
MANIFEST = json.loads((FONTS / "fonts.json").read_text(encoding="utf-8"))
FAMILIES = MANIFEST["families"]
ARABIC = [f for f, m in FAMILIES.items() if m["script"] == "arabic"]
LATIN = [f for f, m in FAMILIES.items() if m["script"] == "latin"]
WORD = "النهاردة"


def files_of(family: str) -> list[Path]:
    return [FONTS / family / w["file"] for w in FAMILIES[family]["weights"]]


def test_manifest_and_files_agree():
    assert len(FAMILIES) >= 14, "the curated set is 14 families (8 Arabic + 6 Latin)"
    assert len(ARABIC) == 8 and len(LATIN) == 6
    for family, meta in FAMILIES.items():
        assert (FONTS / family).is_dir(), family
        assert meta["weights"], family
        for path in files_of(family):
            assert path.is_file(), f"{family}: missing {path.name}"
            assert path.stat().st_size > 20_000, f"{family}: {path.name} looks truncated"
        assert meta["licence"] == "OFL-1.1"
        assert meta["role"] and meta["pairs"], family
    total = sum(p.stat().st_size for p in FONTS.rglob("*.ttf"))
    assert total < 12_000_000, f"the type system should stay lean (now {total / 1e6:.1f} MB)"


def test_every_family_carries_its_licence():
    for family in FAMILIES:
        ofl = FONTS / family / "OFL.txt"
        assert ofl.is_file(), f"{family} has no OFL.txt"
        text = ofl.read_text(encoding="utf-8", errors="ignore")
        assert "SIL OPEN FONT LICENSE" in text.upper(), family
        assert "SIL Open Font License" in text or "OFL" in text, family


def test_defaults_are_the_brand_face():
    assert MANIFEST["default"] == {"arabic": "Cairo", "latin": "Inter"}
    cairo_weights = {w["weight"] for w in FAMILIES["Cairo"]["weights"]}
    assert 800 in cairo_weights, "the brand weight (ExtraBold 800) must ship"
    brand = json.loads((ROOT / "medo-motion" / "brand" / "brand.json").read_text(encoding="utf-8"))
    assert brand["typography"]["type_system"]["default"] == MANIFEST["default"]
    assert brand["typography"]["arabic"] == "Cairo"


def _ink_spans(path: Path, text: str = WORD, size: int = 54):
    placements, width, _asc, _desc, ft = arabic_shape._layout(str(path), text, size, True)
    spans = []
    for gid, x, _y in placements:
        ft.load_glyph(gid, freetype.FT_LOAD_RENDER)
        if ft.glyph.bitmap.width:
            left = x + ft.glyph.bitmap_left
            spans.append((left, left + ft.glyph.bitmap.width))
    spans.sort()
    return width, spans


@pytest.mark.parametrize("family", ARABIC)
def test_arabic_families_shape_without_collisions(family: str):
    for path in files_of(family):
        width, spans = _ink_spans(path)
        assert spans and width > 0, f"{family}: no ink for {WORD}"
        overlap = sum(max(0, spans[i][1] - spans[i + 1][0]) for i in range(len(spans) - 1))
        ratio = overlap / width
        assert ratio < 0.20, (
            f"{family} {path.name}: glyphs overlap ({ratio:.2f}) — advances are narrower than the "
            "outlines, so words collide (see docs/fonts.md 'tested and rejected')")


@pytest.mark.parametrize("family", ARABIC)
def test_arabic_families_render_a_full_word(family: str):
    """A shaped sprite must be wide and have ink: catches a font with no Arabic coverage at all."""
    path = files_of(family)[-1]
    arr = arabic_shape.text_sprite(str(path), WORD, 54, (243, 242, 241))
    assert arr.size > 0
    alpha = arr[..., 3] if arr.ndim == 3 else arr
    ink = float((alpha > 0.05).mean())
    assert 0.02 < ink < 0.9, f"{family}: implausible ink coverage {ink:.2f}"
    height, width = alpha.shape[:2]
    assert width > height, f"{family}: a 8-letter word should be wider than tall ({width}×{height})"


@pytest.mark.parametrize("family", LATIN)
def test_latin_families_render(family: str):
    from PIL import ImageFont  # noqa: PLC0415

    img = Image.new("L", (900, 120), 0)
    ImageDraw.Draw(img).text((10, 20), "Sphinx of black quartz 4.2K",
                             font=ImageFont.truetype(str(files_of(family)[-1]), 44), fill=255)
    assert img.getextrema()[1] > 100, family
    assert (np.asarray(img) > 100).sum() > 800, family


def test_engine_p_font_selector():
    assert Path(lib.font(60).path).name == "Cairo_800ExtraBold.ttf"       # brand default, brand weight
    assert Path(lib.font(60, "Kufam").path).name == "Kufam_700Bold.ttf"    # nearest weight <= 800
    assert Path(lib.font(60, "IBM Plex Sans Arabic", 600).path).name == "IBMPlexSansArabic_600SemiBold.ttf"
    assert Path(lib.font(60, "IBM Plex Sans Arabic", 400).path).name == "IBMPlexSansArabic_400Regular.ttf"
    # an unknown family never renders in a random font: it falls back to the brand face
    assert Path(lib.font(60, "Comic Sans").path).name == "Cairo_800ExtraBold.ttf"


def test_engine_k_loads_from_the_manifest():
    js = (ROOT / "medo-motion" / "templates" / "render" / "lib" / "fonts.js").read_text(encoding="utf-8")
    assert "fonts.json" in js and "useFont" in js and "FontFace" in js or "loadFont" in js
    # no hard-coded family list: the manifest is the only source
    assert "Cairo_" not in js and "Tajawal" not in js
    new_project = (ROOT / "tools" / "new_project.py").read_text(encoding="utf-8")
    assert "fonts.json" in new_project and "assets" in new_project


def test_every_family_is_documented():
    doc = (ROOT / "docs" / "fonts.md").read_text(encoding="utf-8")
    missing = [f for f in FAMILIES if f not in doc]
    assert not missing, f"docs/fonts.md does not describe: {missing}"
    credits = (ROOT / "assets" / "CREDITS.md").read_text(encoding="utf-8")
    assert "OFL" in credits and "Cairo" in credits
    for family in FAMILIES:
        assert family in credits, f"{family} missing from assets/CREDITS.md"
