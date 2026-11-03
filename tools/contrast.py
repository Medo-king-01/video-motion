#!/usr/bin/env python3
"""Contrast gates for on-screen text: the palette is measured, not eyeballed.

`brand.json` states the rule in words (*body text ≥ 4.5:1 against its real background, large
text/keywords ≥ 3:1, never red on dark*) and again as data in `text_contrast`. This module is the
measurement behind both, so a number quoted by the audit, the lint and the tests is the same number.

Three facts make this more than a two-colour ratio:

- **Sizes are frame pixels, not points.** WCAG defines large text as ≥ 18 pt (≥ 14 pt bold). A
  1080-wide reel plays on a phone screen about 70 mm across, so 14 pt bold is 4.94 mm = **76 px of
  frame width** (18 pt regular is 98 px). `brand.json → text_contrast.large_px` declares that
  crossover once, with the derivation beside it, and a fragment at or above it is held to 3:1.
- **A scene has a ramp, not a colour.** The dark ground runs `ink → ink_shadow` and the light ground
  runs `paper → gray_1`, so text is tested against *both* ends: a token that only survives the middle
  of a gradient is not safe on a gradient.
- **Some pairs are forbidden by design, not by arithmetic.** `red` on dark is 3.63:1 — it would pass
  the large bar and still look harsh, so `forbidden_on_theme` blocks it explicitly.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND_PATH = ROOT / "medo-motion" / "brand" / "brand.json"

# Fallbacks only used if a caller hands over a brand document without `text_contrast` (an older
# project copy). brand.json is the source of truth; these never override it.
_DEFAULTS = {"body_ratio": 4.5, "large_ratio": 3.0, "large_px": 76,
             "text_tokens": ("red", "red_bright", "red_deep", "ink", "ink_soft", "paper",
                             "gray_1", "gray_2", "gray_3", "gray_4", "salmon", "blush"),
             "forbidden_on_theme": {"dark": {"red": "", "red_deep": ""},
                                    "light": {"gray_4": "", "salmon": ""}}}


def _channel(value: float) -> float:
    value /= 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def luminance(rgb) -> float:
    """WCAG 2.1 relative luminance of an sRGB triple."""
    r, g, b = (_channel(float(v)) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg, bg) -> float:
    """WCAG contrast ratio between two colours; 1.0–21.0, order-independent."""
    high, low = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def load_brand(path: Path | None = None) -> dict:
    return json.loads((path or BRAND_PATH).read_text(encoding="utf-8"))


def rules(brand: dict) -> dict:
    """The `text_contrast` contract, with defaults for a brand document that predates it."""
    declared = brand.get("text_contrast") or {}
    out = {key: declared.get(key, value) for key, value in _DEFAULTS.items()}
    out["text_tokens"] = tuple(out["text_tokens"])
    return out


def tokens(brand: dict) -> dict:
    """Palette name → RGB triple, including the one derived shade (a ground, never text)."""
    out = {name: tuple(value["rgb"]) for name, value in brand["palette"].items() if value.get("rgb")}
    out.update({name: tuple(value["rgb"]) for name, value in brand.get("derived", {}).items()
                if value.get("rgb")})
    return out


def _theme(theme: str | None) -> str:
    return "light" if theme == "light" else "dark"


def ground_edges(brand: dict, theme: str | None) -> tuple[tuple[int, int, int], ...]:
    """Both ends of a scene's background ramp; text must clear the weaker one."""
    ramp = brand["backgrounds"][_theme(theme)]
    return tuple(tuple(ramp[key]) for key in ("top", "bottom"))


def needs(brand: dict, fg: str, size_px: float | None) -> float:
    """The ratio a token must reach at this size. An unknown size is held to the body bar."""
    spec = rules(brand)
    if isinstance(size_px, (int, float)) and not isinstance(size_px, bool):
        return spec["large_ratio"] if size_px >= spec["large_px"] else spec["body_ratio"]
    return spec["body_ratio"]


def forbidden(brand: dict, token: str, theme: str | None) -> str | None:
    """Why this token is banned on this ground by design, or None if it is allowed."""
    entry = rules(brand)["forbidden_on_theme"].get(_theme(theme), {}).get(token)
    return entry if entry is not None else None


def solve(brand: dict, fg: str, theme: str | None, size_px: float | None = None) -> dict:
    """Judge one text colour against one scene ground.

    Returns `ok`, `worst` (the weaker end of the ramp), `required`, and `against` (which end, or
    which design rule, decided it) so a report can say exactly why a fragment fails.
    """
    table = tokens(brand)
    required = needs(brand, fg, size_px)
    banned = forbidden(brand, fg, theme)
    if fg not in table:
        return {"ok": False, "worst": 0.0, "required": required, "reason": "unknown-token",
                "against": f"not a brand token ({fg})"}
    worst, against = 99.0, ""
    for end, colour in zip(("top", "bottom"), ground_edges(brand, theme), strict=True):
        value = ratio(table[fg], colour)
        if value < worst:
            worst, against = value, f"{_theme(theme)} {end}"
    if banned:
        return {"ok": False, "worst": worst, "required": required, "reason": "forbidden",
                "against": banned}
    return {"ok": worst >= required, "worst": worst, "required": required, "reason": "ratio",
            "against": against}


def audit(brand: dict) -> dict:
    """Every text token against both grounds and both thresholds: the table behind the rule."""
    rows = []
    for token in rules(brand)["text_tokens"]:
        for theme in ("dark", "light"):
            for size_px, label in ((None, "body"), (64, "large")):
                result = solve(brand, token, theme, size_px)
                rows.append({"token": token, "theme": theme, "size": label, **result})
    return {"rows": rows,
            "passing": sorted({r["token"] for r in rows if r["ok"]}),
            "failing": sorted({r["token"] for r in rows if not r["ok"]})}


def contract_errors(brand: dict) -> list[str]:
    """The contract must be internally honest: real tokens, and bans the palette backs up.

    A ban is worth its line only if the pair really is unreadable *at body size* — that is the
    case the arithmetic alone can miss. `red` on dark is the model: 3.63:1 clears the large bar,
    so nothing would stop an agent putting a red keyword on ink, and the explicit entry does.
    A ban on a pair that clears even the body bar (`paper` on dark, 17.71:1) is a rule the next
    agent will argue with, so it is an error here. A token that is not in the palette is a typo
    that would silently paint black.
    """
    spec, table, errors = rules(brand), tokens(brand), []
    for token in spec["text_tokens"]:
        if token not in table:
            errors.append(f"text_tokens names {token!r}, which is not in the palette")
    for theme, entries in spec["forbidden_on_theme"].items():
        for token, why in entries.items():
            if not str(why).strip():
                errors.append(f"forbidden_on_theme.{theme}.{token} needs a reason")
            if token not in table:
                continue
            result = solve(brand, token, _theme(theme), None)
            if result["worst"] >= spec["body_ratio"]:
                errors.append(f"forbidden_on_theme.{theme}.{token} is banned but reads fine "
                              f"({result['worst']:.2f}:1 ≥ {spec['body_ratio']}) — the palette "
                              f"does not back this ban; drop the rule or pick another token")
    return errors


def _rows_table(brand: dict) -> str:
    spec = rules(brand)
    lines = [f"contrast contract: body ≥ {spec['body_ratio']}, large ≥ {spec['large_ratio']} "
             f"at ≥ {spec['large_px']} px", ""]
    header = f"{'token':11s} {'dark body':>9s} {'dark large':>10s} {'light body':>10s} {'light large':>11s}"
    lines += [header, "-" * len(header)]
    for token in spec["text_tokens"]:
        cells = []
        for theme, size in (("dark", None), ("dark", 64), ("light", None), ("light", 64)):
            result = solve(brand, token, theme, size)
            cells.append(f"{result['worst']:6.2f}{'' if result['ok'] else '!'}")
        lines.append(f"{token:11s} " + " ".join(f"{c:>9s}" for c in cells))
    lines += ["", "! = below its bar, or banned on that ground by design"]
    return "\n".join(lines)


def main() -> int:
    import argparse
    import json
    import sys

    ap = argparse.ArgumentParser(description="WCAG contrast of the brand palette, per ground and size.")
    ap.add_argument("--token", help="one palette token to judge")
    ap.add_argument("--theme", choices=["dark", "light"], default="dark")
    ap.add_argument("--size", type=float, default=None, help="text size in stage px (default: body bar)")
    ap.add_argument("--check", action="store_true", help="verify the brand.json contract is honest")
    ap.add_argument("--json", type=Path, help="write the full audit as JSON")
    a = ap.parse_args()

    brand = load_brand()
    if a.token:
        result = solve(brand, a.token, a.theme, a.size)
        flag = "OK " if result["ok"] else "LOW"
        print(f"{flag} {a.token} on {a.theme}: {result['worst']:.2f}:1 "
              f"(needs {result['required']}, decided by {result['against']})")
        if a.json:
            a.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return 0 if result["ok"] else 1

    print(_rows_table(brand))
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(audit(brand), indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    if a.check:
        errors = contract_errors(brand)
        for error in errors:
            print(f"!! {error}", file=sys.stderr)
        print(f"\n{'FAIL' if errors else 'PASS'}  brand contrast contract — {len(errors)} error(s)")
        return 1 if errors else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
