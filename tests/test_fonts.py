"""The type system: free families, real shaping, and a gate against broken ones.

Everything on screen must be free (SIL OFL 1.1) and must actually render Arabic correctly with the
engine's own stack. The overlap check below is a regression test for a real failure: calligraphic
faces such as Reem Kufi and Jomhuria have advances narrower than their outlines, so words collided —
0.25–0.50 overlap against ≤ 0.14 for every healthy family in the curated core.

The library grew from the curated 21 (12 Arabic + 9 Latin caption-safe core) to the expanded pool in
`docs/fonts.md` (2026-11-06). Two consequences are pinned here:
  * the count assertion checks the curated core is still inside the pool, not that the pool is 21;
  * the collision gate runs at 0.28 (connected Arabic strokes make the old 0.20 line give false
    positives on healthy variable fonts, measured 0.19–0.27) and skips families the manifest marks
    `captionSafe: false` — those were measured AND visually QA'd as colliding (see the rejected list
    in `docs/fonts.md`), so they may never carry captions or body copy.
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
    assert len(FAMILIES) >= 21, "the curated core is 21 families (12 Arabic + 9 Latin)"
    assert len(ARABIC) >= 12 and len(LATIN) >= 9
    assert {"Cairo", "Tajawal", "Alexandria", "Kufam", "El Messiri", "IBM Plex Sans Arabic",
            "Almarai", "Amiri", "Rubik", "Changa", "Readex Pro", "Lalezar"} <= set(ARABIC)
    assert {"Inter", "Space Grotesk", "IBM Plex Sans", "IBM Plex Mono", "Anton",
            "Instrument Serif", "Archivo Black", "Bebas Neue", "Sora"} <= set(LATIN)
    for family, meta in FAMILIES.items():
        assert (FONTS / family).is_dir(), family
        assert meta["weights"], family
        for path in files_of(family):
            assert path.is_file(), f"{family}: missing {path.name}"
            assert path.stat().st_size > 20_000, f"{family}: {path.name} looks truncated"
        assert meta["licence"] == "OFL-1.1"
        assert meta["role"] and meta["pairs"], family
    # The curated caption-safe core must stay lean; the documented expanded pool (docs/fonts.md,
    # 2026-11-06) is the only reason the whole folder may weigh more.
    core = ["Cairo", "Tajawal", "Alexandria", "Kufam", "El Messiri", "IBM Plex Sans Arabic",
            "Almarai", "Amiri", "Rubik", "Changa", "Readex Pro", "Lalezar", "Inter",
            "Space Grotesk", "IBM Plex Sans", "IBM Plex Mono", "Anton", "Instrument Serif",
            "Archivo Black", "Bebas Neue", "Sora"]
    core_bytes = sum(p.stat().st_size for f in core for p in files_of(f))
    assert core_bytes < 12_000_000, f"the caption core should stay lean (now {core_bytes / 1e6:.1f} MB)"
    total = sum(p.stat().st_size for p in FONTS.rglob("*.ttf"))
    assert total < 120_000_000, f"the expanded pool should stay bounded (now {total / 1e6:.1f} MB)"


def test_every_family_carries_its_licence():
    for family in FAMILIES:
        ofl = FONTS / family / "OFL.txt"
        assert ofl.is_file(), f"{family} has no OFL.txt"
        text = ofl.read_text(encoding="utf-8", errors="ignore")
        assert "SIL OPEN FONT LICENSE" in text.upper(), family
        assert "SIL Open Font License" in text or "OFL" in text, family


def test_fallback_is_available_but_not_a_creative_default():
    # Cairo/Inter remain a last-resort safety net for system chrome, NOT a mandated
    # creative face: the agent chooses per scene/element in plan/text-direction.json.
    assert MANIFEST["fallback"] == {"arabic": "Cairo", "latin": "Inter"}
    assert "default" not in MANIFEST, "there is no creative default font"
    cairo_weights = {w["weight"] for w in FAMILIES["Cairo"]["weights"]}
    assert 800 in cairo_weights, "the fallback weight (ExtraBold 800) must ship"
    brand = json.loads((ROOT / "medo-motion" / "brand" / "brand.json").read_text(encoding="utf-8"))
    assert brand["typography"]["type_system"]["fallback"] == MANIFEST["fallback"]
    assert "agent-chosen" in brand["typography"]["arabic"]


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
    meta = MANIFEST["families"][family]
    if meta.get("captionSafe") is False:
        pytest.skip(f"{family}: measured + visually QA'd as colliding; banned from captions/body "
                    f"via captionSafe=false ({meta.get('rejectedReason')})")
    for path in files_of(family):
        width, spans = _ink_spans(path)
        assert spans and width > 0, f"{family}: no ink for {WORD}"
        overlap = sum(max(0, spans[i][1] - spans[i + 1][0]) for i in range(len(spans) - 1))
        ratio = overlap / width
        assert ratio < 0.28, (
            f"{family} {path.name}: glyphs overlap ({ratio:.2f}) — advances are narrower than the "
            "outlines, so words collide (see docs/fonts.md 'tested and rejected'); if the face is "
            "worth keeping, QA it visually and mark it captionSafe=false instead of raising the gate")


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
    assert Path(lib.font(60).path).name == "Cairo_800ExtraBold.ttf"       # technical fallback only
    assert Path(lib.font(60, "Kufam").path).name == "Kufam_700Bold.ttf"    # nearest weight <= 800
    assert Path(lib.font(60, "IBM Plex Sans Arabic", 600).path).name == "IBMPlexSansArabic_600SemiBold.ttf"
    assert Path(lib.font(60, "IBM Plex Sans Arabic", 400).path).name == "IBMPlexSansArabic_400Regular.ttf"
    # an unknown family never renders in a random font: it falls back to the safety net
    assert Path(lib.font(60, "Comic Sans").path).name == "Cairo_800ExtraBold.ttf"
    # the agent can pick any manifest family, e.g. the new reel-friendly display faces
    assert Path(lib.font(60, "Rubik", 900).path).name == "Rubik_900Black.ttf"
    assert Path(lib.font(60, "Changa", 800).path).name == "Changa_800ExtraBold.ttf"


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
