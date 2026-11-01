"""The brand lock: values, the no-logo rule, and the two engines staying in sync."""
from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest
from conftest import ROOT, SKILL

BRAND = json.loads((SKILL / "brand" / "brand.json").read_text(encoding="utf-8"))
BRAND_JS = (SKILL / "templates" / "render" / "lib" / "brand.js").read_text(encoding="utf-8")


def test_required_tokens_exist():
    for key in ("red", "red_dark", "black", "ink", "white", "yellow", "emerald", "teal"):
        assert BRAND["palette"][key]["rgb"], key
    assert BRAND["typography"]["arabic"] == "Cairo"
    assert BRAND["typography"]["numerals"].lower().startswith("western")
    assert BRAND["canvas"] == {"w": 1080, "h": 1920, "fps": 30}


def test_safe_zone_numbers():
    safe = BRAND["safe_zone"]
    assert safe["content_y"] == [200, 1350]
    assert safe["caption_center_y"] == 1455
    assert safe["nothing_important_below_y"] == 1500
    assert safe["progress_bar_y"] == 64
    assert safe["margin_px"] == 40


def test_no_logo_and_no_series_name():
    """This studio has none by design: no keys, no fallbacks, no chip slot."""
    brand = BRAND["brand"]
    assert brand["logo"] is None
    assert brand.get("on_screen_name") is None
    assert "logo_file" not in brand and "series_title_laptop" not in brand
    assert "no logo" in brand["logo_rule"].lower()
    assert BRAND["safe_zone"]["series_chip_center_y"] is None


def test_no_chip_default_in_engine_p():
    scenes = (SKILL / "templates" / "procedural-reels" / "scenes.py").read_text(encoding="utf-8")
    assert re.search(r"^CHIP\s*=\s*None", scenes, re.M), "engine P must not draw a series chip"


def _hex(rgb) -> str:
    return "".join(f"{v:02X}" for v in rgb)


def test_brand_js_matches_brand_json():
    def hexof(key):
        m = re.search(key + r"\s*:\s*'#([0-9A-Fa-f]{6})'", BRAND_JS)
        assert m, f"{key} missing from lib/brand.js"
        return m.group(1).upper()

    for js_key, json_key in (("red", "red"), ("black", "black"), ("white", "white"),
                             ("yellow", "yellow"), ("teal", "teal")):
        assert hexof(js_key) == _hex(BRAND["palette"][json_key]["rgb"]), js_key
    assert hexof("bgDarkTop") == _hex(BRAND["backgrounds"]["dark"]["top"])
    assert hexof("bgLightBottom") == _hex(BRAND["backgrounds"]["light"]["bottom"])
    assert "font: { ar: 'Cairo'" in BRAND_JS


def test_brand_check_runs_clean():
    r = subprocess.run([sys.executable, str(SKILL / "scripts" / "brand_check.py")],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RESULT: PASS" in r.stdout


def test_contrast_rules_hold():
    """The pairs the brief actually prints must clear WCAG."""
    pairs = [("white", "ink2", 4.5), ("white", "black", 4.5), ("yellow", "black", 4.5),
             ("emerald", "black", 4.5), ("ink", "white", 4.5), ("white", "red_dark", 4.5)]

    def lum(c):
        f = lambda v: (v / 255 / 12.92) if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4
        r, g, b = (f(v) for v in c)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def ratio(a, b):
        la, lb = sorted((lum(a), lum(b)), reverse=True)
        return (la + 0.05) / (lb + 0.05)

    for fg, bg, minimum in pairs:
        value = ratio(BRAND["palette"][fg]["rgb"], BRAND["palette"][bg]["rgb"])
        assert value >= minimum, f"{fg} on {bg}: {value:.2f} < {minimum}"


def test_gold_on_light_is_decoration_only():
    """Documented known warning: gold never carries readable body text on light."""
    assert pytest.approx(2.26, abs=0.1) == _ratio(BRAND["palette"]["gold"]["rgb"], [231, 228, 226])


def _ratio(a, b):
    def lum(c):
        f = lambda v: (v / 255 / 12.92) if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4
        r, g, b2 = (f(v) for v in c)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b2
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)
