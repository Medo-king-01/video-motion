#!/usr/bin/env python3
"""Import a reference reels text-animation gallery into the studio motion language.

Reads a self-contained HTML gallery whose `animationsData` array describes CSS
text animations (id / name / category / badge / class / speedBase / renderHTML /
cssCode). Re-implements each animation's @keyframes as **frame-deterministic
motion tracks** in the studio grammar ({t, v, ease}) so the same file plays in
engine K (lib/motion.js), engine P (motion.py) and engine R (Remotion).

This ships NO third-party code: only the animation *techniques* are re-expressed
as numeric tracks, re-skinned to the locked brand (semantic color roles, Cairo,
unboxed captions). CDN styling (Tailwind/Font Awesome/Google Fonts) is dropped.

Outputs:
  medo-motion/motion/text-animations.json      full catalog (all animations)
  medo-motion/templates/render/lib/caption-styles.js   generated caption-safe
                                               entrance presets for engine K

Units: x/y/blur are font-relative **em** (source px converted at REF_PX); rotate
in deg; scale unitless; opacity 0..1. The renderer multiplies em by the font size.

Usage:
  python3 tools/text_animations_import.py --html /path/reels_text_animations.html
  python3 tools/text_animations_import.py --html ... --check   # verify in sync
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "medo-motion"
OUT_JSON = SKILL / "motion" / "text-animations.json"
OUT_JS = SKILL / "templates" / "render" / "lib" / "caption-styles.js"
OUT_R_JS = SKILL / "templates" / "remotion" / "src" / "lib" / "caption-styles.js"
OUT_P_PY = SKILL / "templates" / "procedural-reels" / "caption_styles.py"
REF_PX = 40.0  # nominal caption font size used to convert source px -> em

EASINGS = json.loads((SKILL / "motion" / "easings.json").read_text(encoding="utf-8"))
NAMED_CURVES = {tuple(v): k for k, v in EASINGS["cubicBezier"].items()}
CSS_NAME_MAP = {"linear": "linear", "ease": "ease", "ease-in": "easeIn",
                "ease-out": "easeOut", "ease-in-out": "easeInOut"}


# ---------------------------------------------------------------- extraction
def extract_entries(html: str) -> list[dict]:
    region = html[html.index("const animationsData"):]
    ids = list(re.finditer(r"id:\s*'([a-z0-9]+)'", region))
    entries = []
    for k, m in enumerate(ids):
        end = ids[k + 1].start() if k + 1 < len(ids) else region.index("];", m.start())
        block = region[m.start():end]

        def field(name: str, block: str = block) -> str:
            mm = re.search(name + r":\s*'((?:[^'\\]|\\.)*)'", block)
            return mm.group(1) if mm else ""

        css = re.search(r"cssCode:\s*`([^`]*)`", block, re.S)
        render = block[block.index("renderHTML:"):block.index("cssCode:")] if "cssCode:" in block else ""
        speed = re.search(r"speedBase:\s*([\d.]+)", block)
        entries.append({
            "id": m.group(1), "name": field("name"), "category": field("category"),
            "badge": field("badge"), "class": field("class"),
            "speedBase": float(speed.group(1)) if speed else None,
            "css": css.group(1) if css else "", "render": render,
        })
    return entries


# ---------------------------------------------------------------- CSS parsing
def _balanced(css: str, start: int) -> str:
    depth, i = 0, start
    while i < len(css):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return css[start + 1:i]
        i += 1
    return css[start + 1:]


def parse_keyframes(css: str) -> dict[str, list[tuple[float, dict]]]:
    out = {}
    for m in re.finditer(r"@keyframes\s+([\w-]+)\s*\{", css):
        body = _balanced(css, m.end() - 1)
        frames = []
        for rm in re.finditer(r"([^{}]+)\{([^{}]*)\}", body):
            sel, decl = rm.group(1).strip(), rm.group(2)
            props = {}
            for part in decl.split(";"):
                if ":" in part:
                    p, v = part.split(":", 1)
                    props[p.strip()] = v.strip()
            for s in sel.split(","):
                s = s.strip()
                pct = 0.0 if s == "from" else 100.0 if s == "to" else float(s.rstrip("%"))
                frames.append((pct, props))
        frames.sort(key=lambda f: f[0])
        out[m.group(1)] = frames
    return out


def primary_animation(css: str) -> tuple[str | None, float | None, object]:
    m = re.search(r"animation:\s*([\w-]+)\s+([\d.]+)s\s+([^;]+)", css)
    if not m:
        return None, None, "easeOut"
    name, dur, rest = m.group(1), float(m.group(2)), m.group(3)
    bez = re.search(r"cubic-bezier\(([^)]*)\)", rest)
    if bez:
        pts = tuple(round(float(x), 4) for x in bez.group(1).split(","))
        ease = NAMED_CURVES.get(pts, list(pts))
    elif re.search(r"steps\(", rest):
        ease = "linear"  # steps() not in the studio grammar; noted as cssOnly
    else:
        ease = "easeOut"
        for css_name, studio in CSS_NAME_MAP.items():
            if re.search(r"\b" + re.escape(css_name) + r"\b", rest):
                ease = studio
                break
    return name, dur, ease


def _num(value: str) -> float:
    m = re.match(r"(-?[\d.]+)", value.strip())
    return float(m.group(1)) if m else 0.0


def to_em(value: str) -> float:
    v = _num(value)
    if "px" in value:
        return v / REF_PX
    if "%" in value:
        return v / 100.0
    return v  # em / rem / unitless


def parse_transform(value: str) -> dict[str, float]:
    out = {}
    for fn, arg in re.findall(r"(\w+)\(([^)]*)\)", value):
        args = [a.strip() for a in arg.split(",")]
        if fn == "translateY":
            out["y"] = to_em(args[0])
        elif fn == "translateX":
            out["x"] = to_em(args[0])
        elif fn == "translate":
            out["x"] = to_em(args[0])
            if len(args) > 1:
                out["y"] = to_em(args[1])
        elif fn in ("rotate", "rotateZ"):
            out["rotate"] = _num(args[0])
        elif fn == "scale":
            out["scale"] = _num(args[0])
        elif fn in ("scaleX", "scaleY"):
            out[fn] = _num(args[0])
        elif fn in ("skewX", "skewY"):
            out[fn] = _num(args[0])
    return out


def frame_values(props: dict) -> tuple[dict, list[str]]:
    """Numeric channel values from a keyframe's declarations + css-only leftovers."""
    vals, css_only = {}, []
    for p, v in props.items():
        if p == "opacity":
            vals["opacity"] = _num(v)
        elif p == "transform":
            vals.update(parse_transform(v))
        elif p == "filter":
            b = re.search(r"blur\(([^)]*)\)", v)
            if b:
                vals["blur"] = to_em(b.group(1))
            else:
                css_only.append(p)
        elif p in ("color", "background", "background-size", "background-position",
                   "text-shadow", "box-shadow", "-webkit-text-stroke", "clip-path",
                   "letter-spacing", "border-color"):
            css_only.append(p)
        else:
            css_only.append(p)
    return vals, css_only


def build_tracks(frames: list[tuple[float, dict]], duration: float, ease) -> tuple[dict, list[str]]:
    channels: dict[str, list] = {}
    css_only: set[str] = set()
    for pct, props in frames:
        vals, co = frame_values(props)
        css_only.update(co)
        t = round(pct / 100.0 * duration, 4)
        for ch, v in vals.items():
            channels.setdefault(ch, []).append({"t": t, "v": round(v, 4)})
    tracks = {}
    for ch, kfs in channels.items():
        kfs.sort(key=lambda k: k["t"])
        dedup = []
        for kf in kfs:
            if dedup and kf["t"] == dedup[-1]["t"]:
                dedup[-1] = kf
            else:
                dedup.append(kf)
        for i in range(1, len(dedup)):
            dedup[i]["ease"] = ease
        tracks[f"word.{ch}"] = dedup
    return tracks, sorted(css_only)


# ---------------------------------------------------------------- classification
def classify(entry: dict) -> dict:
    css, render = entry["css"], entry["render"]
    boxed = bool(re.search(r"border-radius|border-inline|border-left|border-right|border:\s", css)
                 and re.search(r"background|padding", css))
    highlight = bool(re.search(r"background(?!-clip)", css) and re.search(r"background-size|background-position", css)
                     and not re.search(r"\.1[0-9]em|\.2em", css))  # underline uses a thin bar
    gradient_text = "background-clip: text" in css or "-webkit-background-clip: text" in css
    underline = bool(re.search(r"background-size[^;]*\.1[0-9]em", css))
    caption_safe = not boxed and not highlight and not gradient_text
    split = "char" if ("splitUnits" in render or "Array.from" in render) else "word"
    stag = re.search(r"animation-delay:\s*\$\{i\s*\*\s*([\d.]+)", render)
    # semantic brand color role (never a hex): accent warm -> salmon, strong -> red
    if re.search(r"#facc15|#fbbf24|#f59e0b|yellow", css):
        role = "salmon"
    elif re.search(r"#ef4444|#dc2626|#ff004c|red", css):
        role = "red"
    elif re.search(r"color:\s*#000|#0a0a0a|color:\s*#1", css):
        role = "ink"
    else:
        role = "paper"
    return {"boxed": boxed, "captionSafe": caption_safe, "gradientText": gradient_text,
            "underline": underline, "split": split,
            "stagger": float(stag.group(1)) if stag else None, "colorRole": role}


def entrance_preset(tracks: dict, duration: float) -> dict | None:
    """Trim a loop to its entrance (0 -> first full-opacity hold), scaled snappy."""
    op = tracks.get("word.opacity")
    if op:
        hold = next((k["t"] for k in op if k["t"] > 0 and k["v"] >= 0.99), None)
    else:
        hold = None
    if hold is None:
        ts = sorted({k["t"] for tr in tracks.values() for k in tr if k["t"] > 0})
        hold = ts[0] if ts else None
    if not hold:
        return None
    enter = round(min(max(hold, 0.2), 0.45), 3)
    scale = enter / hold
    out = {}
    for name, tr in tracks.items():
        ent = [k for k in tr if k["t"] <= hold + 1e-6]
        if len(ent) < 2:
            continue
        out[name] = [{"t": round(k["t"] * scale, 4), "v": k["v"], **({"ease": k["ease"]} if "ease" in k else {})}
                     for k in ent]
    return {"enter": enter, "tracks": out} if out else None


# ---------------------------------------------------------------- emission
def build_catalog(html: str) -> dict:
    animations = []
    for e in extract_entries(html):
        kf = parse_keyframes(e["css"])
        name, dur, ease = primary_animation(e["css"])
        dur = dur or e["speedBase"] or 2.0
        frames = kf.get(name, []) if name else []
        tracks, css_only = build_tracks(frames, dur, ease) if frames else ({}, [])
        cls = classify(e)
        badge = re.sub(r"[^\w\s\u0600-\u06FF]", "", e["badge"]).strip()
        anim = {
            "id": e["id"], "name": e["name"], "nameAr": badge, "family": e["category"],
            "split": cls["split"], "stagger": cls["stagger"], "duration": dur, "ease": ease,
            "captionSafe": cls["captionSafe"], "boxed": cls["boxed"],
            "gradientText": cls["gradientText"], "underline": cls["underline"],
            "colorRole": cls["colorRole"],
            "keyframes": {str(pct): props for pct, props in frames},
            "tracks": tracks, "cssOnly": css_only,
        }
        if cls["captionSafe"] and tracks:
            ent = entrance_preset(tracks, dur)
            if ent:
                anim["entrance"] = ent
        animations.append(anim)
    return {
        "_doc": "Reels text-animation techniques re-implemented as frame-deterministic studio motion tracks. "
                "Source: a user-provided reference gallery (no third-party code shipped). Plays in K/P/R via "
                f"lib/motion.js / motion.py. Units: x/y/blur in em (px converted at REF_PX={REF_PX:g}), rotate deg, "
                "scale x, opacity 0..1. colorRole is a semantic brand token resolved by the renderer (never a hex). "
                "captionSafe=false means boxed/highlight/gradient — use for cards/CTAs, not unboxed captions.",
        "refPx": REF_PX,
        "families": ["reels", "trending", "kinetic", "cyber", "cinematic"],
        "animations": animations,
    }


def caption_presets(catalog: dict) -> dict:
    presets = {a["id"]: a["entrance"] for a in catalog["animations"] if a.get("entrance")}
    # Unboxed Hormozi-style pop: reuse the boxed entry's transform tracks (no plate),
    # so the trending pop is available as a brand-safe caption style.
    hz = next((a for a in catalog["animations"] if a["id"] == "hormozi"), None)
    if hz and hz["tracks"]:
        ent = entrance_preset(hz["tracks"], hz["duration"])
        if ent:
            presets["hormozipop"] = ent
    return presets


def emit_caption_styles_js(catalog: dict) -> str:
    presets = caption_presets(catalog)
    lines = [
        "// GENERATED by tools/text_animations_import.py — do not edit by hand.",
        "// Caption-safe entrance presets (unboxed, brand color roles) in the studio motion grammar.",
        "// Each preset: { enter, tracks } sampled with keyframes() from lib/motion.js.",
        "// Timing is driven by the MEASURED word onset (caption_align), never a fixed stagger.",
        "export const CAPTION_ENTRANCES = " + json.dumps(presets, ensure_ascii=False, indent=2) + ";",
        "",
        "export const CAPTION_STYLE_IDS = Object.keys(CAPTION_ENTRANCES);",
        "",
    ]
    return "\n".join(lines)


def emit_caption_styles_py(catalog: dict) -> str:
    presets = caption_presets(catalog)
    return "\n".join([
        "# GENERATED by tools/text_animations_import.py — do not edit by hand.",
        "# Caption-safe entrance presets (unboxed, brand color roles) for engine P.",
        "# Same data as lib/caption-styles.js; sampled with motion.py keyframes().",
        "CAPTION_ENTRANCES = " + json.dumps(presets, ensure_ascii=False, indent=2),
        "",
        "CAPTION_STYLE_IDS = list(CAPTION_ENTRANCES)",
        "",
    ])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", type=Path, required=True)
    ap.add_argument("--check", action="store_true", help="verify outputs are in sync, write nothing")
    args = ap.parse_args()
    catalog = build_catalog(args.html.read_text(encoding="utf-8"))
    js = emit_caption_styles_js(catalog)
    py = emit_caption_styles_py(catalog)
    json_text = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    outputs = ((OUT_JSON, json_text), (OUT_JS, js), (OUT_R_JS, js), (OUT_P_PY, py))
    if args.check:
        ok = all(p.is_file() and p.read_text(encoding="utf-8") == text for p, text in outputs)
        print("text-animations in sync" if ok else "text-animations OUT OF SYNC — re-run the importer")
        return 0 if ok else 1
    for p, text in outputs:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    n = len(catalog["animations"])
    safe = sum(1 for a in catalog["animations"] if a["captionSafe"])
    ent = sum(1 for a in catalog["animations"] if a.get("entrance"))
    print(f"imported {n} animations ({safe} caption-safe, {ent} entrance presets)")
    for p, _ in outputs:
        print(f"  -> {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
