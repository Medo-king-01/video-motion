#!/usr/bin/env python3
"""Import the vendored itshover components (Apache-2.0) into the reel icon format.

    python3 tools/itshover_import.py                 # rebuild icons/itshover/registry.json from icons/itshover/tsx
    python3 tools/itshover_import.py --list          # print the ids that were imported
    python3 tools/itshover_import.py --promote cpu   # copy one upstream icon into the house registry

The itshover sources are React components driven by `motion`; the video engines need plain geometry.
So each component's `<svg>` children are extracted (path / rect / circle / ellipse / line / polyline /
polygon, with fill / transform), renamed and written to `icons/itshover/registry.json` with:
  * the upstream id (same as https://itshover.com/icons/<id>)
  * an Arabic label for the ones the studio actually uses (others fall back to English)
  * a shared reveal animation (draw-in) — their JS choreography cannot run in Canvas/Pillow,
    so the reel engines use one consistent, brand-safe entrance instead of a per-icon timeline.

Requires no network: everything comes from the vendored files in `medo-motion/icons/itshover/tsx`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITS = ROOT / "medo-motion" / "icons" / "itshover"
TSX = ITS / "tsx"
OUT = ITS / "registry.json"
HOUSE = ROOT / "medo-motion" / "icons" / "registry.json"

# Arabic labels for the icons a tech/education reel is likely to use.
AR = {
    "battery-icon": "البطارية", "battery-charging-icon": "شحن البطارية", "checked-icon": "تم",
    "simple-checked-icon": "تم", "double-check-icon": "تم التأكيد", "filled-checked-icon": "تم",
    "gear-icon": "الإعدادات", "magnifier-icon": "بحث", "globe-icon": "الإنترنت",
    "rocket-icon": "انطلاق", "moon-icon": "الليل", "book-icon": "كتاب", "bookmark-icon": "محفوظ",
    "bulb-svg": "فكرة", "question-mark": "سؤال", "meh-icon": "مش متأكد", "angry-icon": "مشكلة",
    "refresh-icon": "تحديث", "send-icon": "إرسال", "send-horizontal-icon": "إرسال",
    "copy-icon": "نسخ", "logout-icon": "خروج", "home-icon": "الرئيسية", "router-icon": "راوتر",
    "satellite-dish-icon": "بثّ", "javascript-icon": "جافاسكريبت", "python-icon": "بايثون",
    "mysql-icon": "قاعدة بيانات", "docker-icon": "دوكر", "github-icon": "جيت هاب",
    "figma-icon": "فيجما", "notion-icon": "نوشن", "linkedin-icon": "لينكدإن",
    "instagram-icon": "إنستجرام", "facebook-icon": "فيسبوك", "telegram-icon": "تليجرام",
    "alarm-clock-plus-icon": "منبّه", "credit-card": "بطاقة دفع", "cart-icon": "سلة",
    "shopping-cart-icon": "سلة", "qrcode-svg": "كود QR", "player-icon": "تشغيل",
    "keyframes-icon": "كيفريمز", "focus-icon": "تركيز", "expand-icon": "تكبير",
    "arrow-narrow-right-icon": "التالي", "arrow-narrow-left-icon": "السابق",
    "arrow-back-icon": "رجوع", "down-chevron": "تحت", "right-chevron": "يمين",
    "shield-check": "حماية", "mouse-pointer-2-icon": "كليك", "phone-volume": "مكالمة",
    "apple-brand-logo": "آبل", "brand-google-icon": "جوجل", "brand-openai-icon": "أوبن إيه آي",
    "brand-anthropic-icon": "أنثروبيك", "brand-gemini-icon": "جيميناي", "brand-grok-icon": "جروك",
    "brand-qwen-icon": "كوين", "brand-notion-icon": "نوشن", "brand-vercel-icon": "فيرسل",
    "brand-react-icon": "رياكت", "brand-nextjs-icon": "نكست", "brand-nodejs-icon": "نود",
    "brand-aws-icon": "AWS", "brand-windows-icon": "ويندوز", "brand-zoom-icon": "زووم",
    "brand-stripe-icon": "سترايب", "brand-paypal-icon": "باي بال", "brand-threads-icon": "ثريدز",
    "brand-telegram-icon": "تليجرام", "brand-railway-icon": "Railway", "brand-cursor-icon": "كيرسر",
    "brand-lmstudio-icon": "LM Studio", "brand-midjourney-icon": "ميدجورني",
    "brand-aistudio-icon": "Google AI Studio", "brand-apple-icon": "آبل",
    "brand-github-copilot-icon": "كوبايلوت", "brand-discord-icon": "ديسكورد",
}

# Upstream is trademarked brand marks: usable only with Medo's explicit approval.
BRAND_PREFIXES = ("brand-", "apple-brand", "github-icon", "gitlab-icon", "figma-icon", "notion-icon",
                  "discord-icon", "slack-icon", "gmail-icon", "instagram-icon", "facebook-icon",
                  "telegram-icon", "linkedin-icon", "pinterest-icon", "snapchat-icon", "zoom-icon")

TAGS = ("path", "rect", "circle", "ellipse", "line", "polyline", "polygon")
ELEM = re.compile(r"<(?:motion\.)?(" + "|".join(TAGS) + r")\b([^>]*?)/?>", re.S)
ATTR = re.compile(r'\b([a-zA-Z][a-zA-Z0-9-]*)\s*=\s*(?:"([^"]*)"|\{([^}]*)\})', re.S)
COMMENT = re.compile(r"\{/\*.*?\*/\}", re.S)


def _num(v: str | None, default: float = 0.0) -> float:
    if v is None:
        return default
    m = re.match(r"^\s*\{?\s*(-?[\d.]+)", v)
    return float(m.group(1)) if m else default


def _matrix(transform: str | None) -> list[float] | None:
    """translate / scale / rotate about the origin — enough for the handful of upstream transforms."""
    if not transform:
        return None
    m = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    for fn, args in re.findall(r"(translate|scale|rotate)\(([^)]*)\)", transform):
        vals = [float(x) for x in re.findall(r"-?[\d.]+", args)]
        if fn == "translate":
            tx, ty = vals[0], (vals[1] if len(vals) > 1 else 0.0)
            m[4] += m[0] * tx + m[2] * ty
            m[5] += m[1] * tx + m[3] * ty
        elif fn == "scale":
            sx = vals[0]
            sy = vals[1] if len(vals) > 1 else sx
            m[0] *= sx
            m[1] *= sx
            m[2] *= sy
            m[3] *= sy
        elif fn == "rotate":
            import math
            a = math.radians(vals[0])
            ca, sa = math.cos(a), math.sin(a)
            m[0], m[1], m[2], m[3] = m[0] * ca + m[2] * sa, m[1] * ca + m[3] * sa, \
                -m[0] * sa + m[2] * ca, -m[1] * sa + m[3] * ca
    return m if m != [1.0, 0.0, 0.0, 1.0, 0.0, 0.0] else None


def parse_icon(path: Path) -> dict | None:
    src = COMMENT.sub("", path.read_text(encoding="utf-8"))
    svg_start = src.find("<motion.svg")
    if svg_start < 0:
        svg_start = src.find("<svg")
    if svg_start < 0:
        return None
    svg = src[svg_start:]
    end = svg.find("</motion.svg>")
    if end < 0:
        end = svg.find("</svg>")
    svg = svg[: end if end > 0 else len(svg)]
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    grid = float(vb.group(1)) if vb else 24.0
    stroke_m = re.search(r"strokeWidth=\{?([\d.]+)", svg)
    stroke = float(stroke_m.group(1)) if stroke_m else 2.0

    shapes, skipped = [], 0
    for tag, raw in ELEM.findall(svg):
        a, expr = {}, set()
        for key, dq, brace in ATTR.findall(raw):
            if dq != "":
                a[key] = dq
            else:
                a[key] = brace
                expr.add(key)          # {variable} — geometry lives elsewhere in the file
        fill = (a.get("fill") or "").strip()
        stroke_attr = (a.get("stroke") or "").strip()
        filled = bool(fill) and fill not in ("none", "transparent")
        if tag == "path":
            d = "" if "d" in expr else a.get("d", "")
            if not d or d.replace(" ", "") in ("M0 0h24v24H0z",):
                skipped += 1
                continue
            shape = {"t": "path", "d": d}
        elif tag == "rect":
            shape = {"t": "rect", "x": _num(a.get("x")), "y": _num(a.get("y")),
                     "w": _num(a.get("width")), "h": _num(a.get("height")),
                     "r": _num(a.get("rx") or a.get("ry"))}
        elif tag == "circle":
            shape = {"t": "circle", "c": [_num(a.get("cx")), _num(a.get("cy"))], "r": _num(a.get("r"))}
        elif tag == "ellipse":
            shape = {"t": "ellipse", "c": [_num(a.get("cx")), _num(a.get("cy"))],
                     "rx": _num(a.get("rx")), "ry": _num(a.get("ry"))}
        elif tag == "line":
            shape = {"t": "line", "p": [[_num(a.get("x1")), _num(a.get("y1"))],
                                        [_num(a.get("x2")), _num(a.get("y2"))]]}
        elif tag in ("polyline", "polygon"):
            pts = [[float(x), float(y)] for x, y in re.findall(r"(-?[\d.]+)[,\s]+(-?[\d.]+)",
                                                               a.get("points", ""))]
            if len(pts) < 2:
                skipped += 1
                continue
            shape = {"t": "poly", "p": pts, "closed": tag == "polygon"}
        else:  # pragma: no cover - TAGS is exhaustive
            continue
        if filled:
            shape["fill"] = True
        if stroke_attr == "none" and not filled:
            skipped += 1
            continue
        m = _matrix(a.get("transform"))
        if m:
            shape["m"] = m
        if shape.get("r") == 0 and shape["t"] in ("circle", "ellipse"):
            skipped += 1
            continue
        shapes.append(shape)
    if not any(not sh.get("fill") for sh in shapes):
        # Some upstream components build their paths in JSX expressions (`.map()` over a string
        # array, or a `d={variable}`). Recover the literals so the icon is not lost.
        seen = {sh.get("d") for sh in shapes}
        for d in re.findall(r'"([Mm][^"\\]{6,})"', src):
            if d not in seen:
                seen.add(d)
                shapes.append({"t": "path", "d": d})
    if not shapes:
        return None
    return {"grid": grid, "stroke": stroke, "shapes": shapes, "skipped": skipped}


def icon_id(stem: str) -> str:
    return stem[:-4] if stem.endswith(".tsx") else stem


def is_brand(ident: str) -> bool:
    return ident.startswith(BRAND_PREFIXES)


def build() -> dict:
    icons = []
    for path in sorted(TSX.glob("*.tsx")):
        ident = icon_id(path.name)
        parsed = parse_icon(path)
        if not parsed:
            print(f"  skip (no geometry): {ident}")
            continue
        shapes = parsed["shapes"]
        # brand-safe default: one uniform draw-in; dotted detail = last filled shape, if any
        icons.append({
            "id": ident,
            "ar": AR.get(ident, ""),
            "en": ident.replace("-", " ").title(),
            "group": "brand" if is_brand(ident) else "itshover",
            "grid": parsed["grid"],
            "stroke": parsed["stroke"],
            "anim": {"draw": 0.85, "stagger": 0.06, "pulse_hz": 1.2},
            "shapes": shapes,
        })
    return {
        "_doc": "Generated by tools/itshover_import.py from the vendored itshover components "
                "(Apache-2.0, https://github.com/itshover/itshover). Do not hand-edit: re-run the importer. "
                "`group: brand` entries are third-party trademarks — never use them as Medo's identity.",
        "source": "https://itshover.com/icons",
        "licence": "Apache-2.0 (see icons/itshover/LICENSE)",
        "grid": 24,
        "icons": icons,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--promote", nargs="+", help="copy upstream icon id(s) into the house registry")
    args = ap.parse_args()

    data = build()
    if args.list:
        for icon in data["icons"]:
            print(f"{icon['id']:<40} {icon['group']:<9} shapes={len(icon['shapes'])} {icon['ar']}")
        return 0
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"itshover: imported {len(data['icons'])} icons -> {OUT.relative_to(ROOT)}")
    if args.promote:
        house = json.loads(HOUSE.read_text(encoding="utf-8"))
        have = {i["id"] for i in house["icons"]}
        by_id = {i["id"]: i for i in data["icons"]}
        for ident in args.promote:
            if ident not in by_id:
                print(f"  unknown icon: {ident}")
                continue
            if ident in have:
                print(f"  already in the house registry: {ident}")
                continue
            icon = dict(by_id[ident])
            icon["group"] = "imported"
            house["icons"].append(icon)
        HOUSE.write_text(json.dumps(house, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"house registry now has {len(house['icons'])} icons — run medo-motion/icons/build.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
