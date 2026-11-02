"""The brand lock: palette v2.6 muted (12 colours), the no-logo rule, and all three engines staying in sync."""
from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest
from conftest import ROOT, SKILL

BRAND = json.loads((SKILL / "brand" / "brand.json").read_text(encoding="utf-8"))
BRAND_JS = (SKILL / "templates" / "render" / "lib" / "brand.js").read_text(encoding="utf-8")
PALETTE = BRAND["palette"]
SHADOW = BRAND["derived"]["ink_shadow"]["rgb"]

# the 12 hex values given by Medo — locked, nothing invented
LOCKED = ["#71717A", "#0A0A0A", "#CB271B", "#BFBAB7", "#C9C5C2", "#F3F2F1",
          "#9F0803", "#D8D7D5", "#CB0801", "#A3A2A0", "#D97F68", "#D5AEA6"]


def _hex(rgb) -> str:
    return "".join(f"{v:02X}" for v in rgb)


def _lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4
    r, g, b = (f(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_palette_is_exactly_the_locked_twelve():
    assert len(PALETTE) == 12
    assert sorted("#" + v["hex"].strip("#").upper() for v in PALETTE.values()) == sorted(LOCKED)
    for key, value in PALETTE.items():
        assert [int(value["hex"][i:i + 2], 16) for i in (1, 3, 5)] == value["rgb"], key
        assert value["role"], key


def test_derived_shade_is_the_locked_v26_value():
    # palette v2.6 locks ink_shadow at #030303 (ink darkened toward black) — the only derived shade
    assert SHADOW == [3, 3, 3]
    assert all(s < i for s, i in zip(SHADOW, PALETTE["ink"]["rgb"], strict=True))


def test_required_tokens_exist():
    for key in ("red", "red_bright", "red_deep", "ink", "ink_soft", "paper",
                "gray_1", "gray_2", "gray_3", "gray_4", "salmon", "blush"):
        assert PALETTE[key]["rgb"], key
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


def test_brand_js_matches_brand_json():
    def hexof(key):
        m = re.search(key + r"\s*:\s*'(#[0-9A-Fa-f]{6})'", BRAND_JS)
        assert m, f"{key} missing from lib/brand.js"
        return m.group(1).lstrip("#").upper()

    for js_key, json_key in (("red", "red"), ("redBright", "red_bright"), ("redDeep", "red_deep"),
                             ("ink", "ink"), ("inkSoft", "ink_soft"), ("paper", "paper"),
                             ("gray1", "gray_1"), ("gray4", "gray_4"),
                             ("salmon", "salmon"), ("blush", "blush")):
        assert hexof(js_key) == _hex(PALETTE[json_key]["rgb"]), js_key
    assert hexof("inkShadow") == _hex(SHADOW)
    assert hexof("bgDarkTop") == _hex(BRAND["backgrounds"]["dark"]["top"])
    assert hexof("bgDarkBottom") == _hex(BRAND["backgrounds"]["dark"]["bottom"])
    assert hexof("bgLightBottom") == _hex(BRAND["backgrounds"]["light"]["bottom"])
    assert "font: { ar: 'Cairo'" in BRAND_JS


def test_engines_hold_no_off_palette_colour():
    """Every colour literal in either engine must be one of the 12 (+ the derived ink shade)."""
    allowed = {"#" + v["hex"].strip("#").upper() for v in PALETTE.values()} | {"#" + _hex(SHADOW)}
    for engine_root in (SKILL / "templates" / "render", SKILL / "templates" / "remotion"):
        for path in engine_root.rglob("*.js"):
            if "node_modules" in path.parts:
                continue
            for found in re.findall(r"#[0-9A-Fa-f]{6}", path.read_text(encoding="utf-8")):
                assert found.upper() in allowed, f"{path.name}: {found}"
        for path in engine_root.rglob("*.ts*"):
            if "node_modules" in path.parts:
                continue
            for found in re.findall(r"#[0-9A-Fa-f]{6}", path.read_text(encoding="utf-8")):
                assert found.upper() in allowed, f"{path.name}: {found}"

    # engine P's constants are covered by brand_check.py --project (it ignores coordinates
    # and audio buffers, which share the (r,g,b) shape); here we only pin the named tokens.
    libpy = (SKILL / "templates" / "procedural-reels" / "lib.py").read_text(encoding="utf-8")
    for name, key in (("RED", "red"), ("DRED", "red_deep"), ("WHITE", "paper"),
                      ("EMER", "blush"), ("TEAL", "ink_soft"), ("YEL", "salmon"),
                      ("INK", "ink"), ("GRAY", "gray_4"), ("LGRAY", "gray_2")):
        m = re.search(name + r"=\((\d+),(\d+),(\d+)\)", libpy)
        assert m, name
        assert list(map(int, m.groups())) == PALETTE[key]["rgb"], name


def test_brand_check_runs_clean():
    r = subprocess.run([sys.executable, str(SKILL / "scripts" / "brand_check.py"),
                        "--project", str(SKILL / "templates")],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RESULT: PASS" in r.stdout


def test_contrast_rules_hold():
    """The pairs the reels actually print must clear WCAG."""
    for fg, bg, minimum in (("paper", "ink", 4.5), ("paper", "red_deep", 4.5), ("ink", "paper", 4.5),
                            ("ink", "gray_2", 4.5), ("blush", "ink", 4.5),
                            ("red", "paper", 3.0), ("red_bright", "paper", 3.0),
                            ("gray_4", "ink", 3.0), ("salmon", "ink", 3.0)):
        value = _ratio(PALETTE[fg]["rgb"], PALETTE[bg]["rgb"])
        assert value >= minimum, f"{fg} on {bg}: {value:.2f} < {minimum}"


def test_forbidden_pairs_stay_low():
    """Documented limits: red text never goes on dark, salmon/gray_4 never on light."""
    assert _ratio(PALETTE["red"]["rgb"], PALETTE["ink"]["rgb"]) < 4.5  # v2.6: 3.63:1 — still never red on dark
    assert _ratio(PALETTE["salmon"]["rgb"], PALETTE["paper"]["rgb"]) < 4.5
    assert _ratio(PALETTE["gray_4"]["rgb"], PALETTE["paper"]["rgb"]) < 4.5


@pytest.mark.parametrize("hex_value", LOCKED)
def test_locked_hex_parses(hex_value):
    assert re.fullmatch(r"#[0-9A-F]{6}", hex_value)
