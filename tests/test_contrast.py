"""The contrast gate: WCAG arithmetic, the brand.json contract behind it, and the two lint rules.

The point of these tests is not that a number was typed correctly once — it is that the *rule*
cannot drift: `brand.json` declares the bars, `tools/contrast.py` measures them, `reel_lint.py`
enforces them per fragment, and `--check` refuses a contract the palette does not back up.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "contrast.py"
LINT = ROOT / "tools" / "reel_lint.py"
BRAND_PATH = ROOT / "medo-motion" / "brand" / "brand.json"
FIX = ROOT / "tests" / "fixtures" / "reel"
GOOD, BAD = FIX / "good", FIX / "bad"

sys.path.insert(0, str(ROOT / "tools"))
import contrast  # noqa: E402


def brand() -> dict:
    return contrast.load_brand()


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], capture_output=True, text=True)


# ---- the arithmetic ---------------------------------------------------------------------------
def test_ratio_matches_the_wcag_reference_values():
    white, black = (255, 255, 255), (0, 0, 0)
    assert contrast.ratio(white, black) == pytest.approx(21.0)
    assert contrast.ratio(white, white) == pytest.approx(1.0)
    assert contrast.ratio(black, white) == contrast.ratio(white, black)   # order-independent
    # #767676 on white is the classic 4.54:1 "just passes AA body" pair
    assert contrast.ratio((0x76, 0x76, 0x76), white) == pytest.approx(4.54, abs=0.01)


def test_the_studio_palette_matches_brand_check():
    """One formula, two tools: the audit and the lint must never quote different numbers."""
    source = (ROOT / "medo-motion" / "scripts" / "brand_check.py").read_text(encoding="utf-8")
    assert "def ratio(" in source and "0.2126 * r" in source
    assert "0.2126 * r" in (ROOT / "tools" / "contrast.py").read_text(encoding="utf-8")


# ---- the contract in brand.json ----------------------------------------------------------------
def test_brand_declares_the_contrast_contract_as_data():
    spec = brand()["text_contrast"]
    assert spec["body_ratio"] == 4.5 and spec["large_ratio"] == 3.0
    assert spec["large_px"] == 76
    assert "salmon" in spec["text_tokens"] and "ink_shadow" not in spec["text_tokens"]
    # the prose rules and the machine rules stay the same rule
    prose = " ".join(brand()["contrast_rules"])
    assert "4.5:1" in prose and "3:1" in prose


def test_contract_is_honest_about_its_own_bans():
    assert contrast.contract_errors(brand()) == []


def test_a_ban_the_palette_backs_at_no_size_is_rejected():
    """`paper` on dark is 17.71:1 — banning it would be a rule the next agent argues with."""
    broken = json.loads(json.dumps(brand()))
    broken["text_contrast"]["forbidden_on_theme"]["dark"]["paper"] = "made up"
    errors = contrast.contract_errors(broken)
    assert any("does not back this ban" in e for e in errors), errors


def test_a_token_outside_the_palette_is_rejected():
    broken = json.loads(json.dumps(brand()))
    broken["text_contrast"]["text_tokens"].append("teal")
    assert any("teal" in e for e in contrast.contract_errors(broken))


def test_red_on_dark_is_banned_even_though_it_clears_the_large_bar():
    """3.63:1 passes the 3:1 large bar — only the explicit ban stops a red keyword on ink."""
    result = contrast.solve(brand(), "red", "dark", 76)
    assert not result["ok"] and result["reason"] == "forbidden"
    assert result["worst"] >= 3.0, "the ban is doing work the arithmetic cannot"


# ---- per-fragment judging ---------------------------------------------------------------------
@pytest.mark.parametrize("token,theme,ok", [
    ("paper", "dark", True), ("salmon", "dark", True), ("ink", "light", True),
    ("red_deep", "light", True), ("ink_soft", "dark", True),
    ("red", "dark", False), ("red_deep", "dark", False), ("ink", "dark", False),
    ("gray_4", "light", False), ("salmon", "light", False), ("blush", "light", False),
])
def test_known_token_ground_pairs(token, theme, ok):
    assert contrast.solve(brand(), token, theme, 76)["ok"] is ok


def test_size_moves_the_bar_at_the_pixel_size_wcag_actually_names():
    """ink_soft on dark is 4.10:1: a 58 px caption fails the body bar, a bold keyword passes.

    76 px is 14 pt bold on a 1080-wide frame seen at ~70 mm — the WCAG large-text crossover, not a
    round number someone liked. A brand-minimum 58 px caption sits below it and is held to 4.5:1.
    """
    assert brand()["text_contrast"]["large_px"] == 76
    assert not contrast.solve(brand(), "ink_soft", "dark", 58)["ok"]
    assert contrast.solve(brand(), "ink_soft", "dark", 76)["ok"]


def test_a_gradient_is_judged_at_its_weaker_end():
    """The light ground runs paper → gray_1; text is measured against both ends, not the top."""
    result = contrast.solve(brand(), "ink", "light", 76)
    assert result["against"] == "light bottom"
    assert result["worst"] == pytest.approx(contrast.ratio((10, 10, 10), (0xD8, 0xD7, 0xD5)), abs=1e-9)


def test_an_unknown_colour_is_never_silently_accepted():
    result = contrast.solve(brand(), "teal", "dark", 76)
    assert not result["ok"] and result["reason"] == "unknown-token"


# ---- the CLI ----------------------------------------------------------------------------------
def test_cli_check_passes_on_the_real_brand():
    assert run(str(TOOL), "--check").returncode == 0


def test_cli_judges_one_token_and_sets_its_exit_code():
    good = run(str(TOOL), "--token", "paper", "--theme", "dark")
    bad = run(str(TOOL), "--token", "gray_4", "--theme", "light")
    assert (good.returncode, bad.returncode) == (0, 1)
    assert "17.71" in good.stdout and "LOW" in bad.stdout


# ---- the two lint rules ------------------------------------------------------------------------
def codes(result: subprocess.CompletedProcess) -> set[str]:
    out = set()
    for line in (result.stdout + result.stderr).splitlines():
        if line[:2] in ("!!", " ?"):
            parts = line.strip(" ?!").split()
            if parts and parts[0][:1] in "SCMKUT" and parts[0][1:].isdigit():
                out.add(parts[0])
    return out


def test_good_fixture_has_a_colour_checked_and_a_live_frame_zero():
    r = run(str(LINT), str(GOOD), "--strict")
    assert r.returncode == 0, r.stdout
    assert "T06  11 coloured fragment(s) clear WCAG" in r.stdout
    assert "S06  frame 0 already carries the picture" in r.stdout


def test_bad_fixture_trips_contrast_and_the_empty_poster():
    r = run(str(LINT), str(BAD))
    found = codes(r)
    assert {"T06", "S06"} <= found, r.stdout
    assert r.returncode == 1
