"""The type system: 125 free families (61 Arabic + 64 Latin), real shaping, and a gate against broken ones.

Everything on screen must be free (123 SIL OFL 1.1 families + Permanent Marker, Apache-2.0, Font Diner + Ubuntu, UFL-1.0, Canonical) and must actually render Arabic correctly with the engine's own stack. The overlap
check below is a regression test for a real failure: advances narrower than outlines make words
collide. Families measured >= 0.20 on 2026-11-09 carry status="review" in the manifest and are
kept out of the recommended shortlist (medo-motion/looks/shortlist.json) — see docs/fonts.md.
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


REVIEWED = {
    # measured >= 0.20 collision ratio on 'النهاردة' @ 54px (2026-11-09) — see docs/fonts.md
    "Jomhuria", "Aref Ruqaa", "Aref Ruqaa Ink", "Noto Nastaliq Urdu", "Gulzar",
    "Noto Sans Arabic", "Estedad", "Reem Kufi", "Reem Kufi Fun", "Reem Kufi Ink",
    "Mirza", "Noto Naskh Arabic", "Noto Kufi Arabic", "Katibeh", "Fustat",
}


def test_manifest_and_files_agree():
    assert len(FAMILIES) == 125, "the manifest is the curated set: 125 families (61 Arabic + 64 Latin)"
    assert len(ARABIC) == 61 and len(LATIN) == 64
    for family, meta in FAMILIES.items():
        assert (FONTS / family).is_dir(), family
        assert meta["weights"], family
        for path in files_of(family):
            assert path.is_file(), f"{family}: missing {path.name}"
            assert path.stat().st_size > 20_000, f"{family}: {path.name} looks truncated"
        assert meta["licence"] in {"OFL-1.1", "Apache-2.0", "UFL-1.0"}
        assert meta["role"] and meta["pairs"], family
    total = sum(p.stat().st_size for p in FONTS.rglob("*.ttf"))
    # The 125-family inventory is ~86 MB on disk; the per-family tests are the real gate.
    # Kept as a regression alarm — investigate any growth beyond this, don't just raise it silently.
    assert total < 120_000_000, f"unexpected growth — re-audit the inventory (now {total / 1e6:.1f} MB)"


def test_every_family_carries_its_licence():
    """Each family ships the licence file its manifest entry declares.

    Most families are OFL-1.1; Permanent Marker is Apache-2.0 (Font Diner) and Ubuntu is
    UFL-1.0 (Canonical). The test reads the declared licence rather than assuming one —
    mislabelling was a real bug.
    """
    markers = {"OFL-1.1": ("SIL OPEN FONT LICENSE",), "Apache-2.0": ("APACHE LICENSE",), "UFL-1.0": ("UBUNTU FONT LICENCE",)}
    for family, meta in FAMILIES.items():
        declared = meta["licence"]
        assert declared in markers, f"{family}: unknown licence {declared!r}"
        licence_file = ROOT / "assets" / "fonts" / meta["licence_file"]
        assert licence_file.is_file(), f"{family} has no {meta['licence_file']}"
        text = licence_file.read_text(encoding="utf-8", errors="ignore").upper()
        assert any(marker in text for marker in markers[declared]), family


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


def _worst_collision_ratio(family: str) -> float:
    worst = 0.0
    for path in files_of(family):
        width, spans = _ink_spans(path)
        assert spans and width > 0, f"{family}: no ink for {WORD}"
        overlap = sum(max(0, spans[i][1] - spans[i + 1][0]) for i in range(len(spans) - 1))
        worst = max(worst, overlap / width)
    return worst


@pytest.mark.parametrize("family", ARABIC)
def test_arabic_families_shape_without_collisions(family: str):
    ratio = _worst_collision_ratio(family)
    status = FAMILIES[family].get("status")
    if status == "ok":
        assert ratio < 0.20, (
            f"{family}: glyphs overlap ({ratio:.2f}) across the shipped weights — advances are narrower "
            "than the outlines, so words collide (flip status to 'review' and update docs/fonts.md)")
    else:
        assert status == "review", f"{family}: missing status in the manifest"
        assert family in REVIEWED, f"{family}: not in the measured review set — update REVIEWED + docs/fonts.md"
        assert ratio >= 0.20, (
            f"{family} now measures {ratio:.2f} (< 0.20) — flip status back to 'ok', "
            "update REVIEWED, docs/fonts.md and medo-motion/looks/shortlist.json")


def test_manifest_status_covers_every_family_and_pins_the_review_set():
    for family, meta in FAMILIES.items():
        assert meta.get("status") in {"ok", "review"}, f"{family}: status must be 'ok' or 'review'"
    review = {f for f, m in FAMILIES.items() if m["status"] == "review"}
    assert review == REVIEWED, f"the measured review set drifted: {sorted(review ^ REVIEWED)}"
    for family in REVIEWED:
        assert FAMILIES[family]["script"] == "arabic"


def test_looks_shortlist_is_manifest_backed():
    shortlist = json.loads((ROOT / "medo-motion" / "looks" / "shortlist.json").read_text(encoding="utf-8"))
    picks = shortlist["families"]
    assert shortlist["status"] == "curated-for-weak-models"
    assert len(picks) >= 8
    for entry in picks:
        family = entry["family"]
        assert family in FAMILIES, f"{family}: shortlisted but not in the manifest"
        assert FAMILIES[family]["status"] == "ok", f"{family}: shortlisted but not collision-clean"
        assert FAMILIES[family]["script"] == entry["script"]
        assert entry["role"] and entry["pairs"], family
    scripts = [entry["script"] for entry in picks]
    assert scripts.count("arabic") >= 6 and scripts.count("latin") >= 4


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
