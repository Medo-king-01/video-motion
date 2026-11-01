#!/usr/bin/env python3
"""Build the animated icon layer from icons/registry.json.

    python medo-motion/icons/build.py            # regenerate artefacts
    python medo-motion/icons/build.py --check    # fail if anything on disk is stale

Artefacts (all committed, all generated — never hand-edit them):
    icons/svg/<id>.svg                                  animated SVG (CSS, currentColor + --icon-accent)
    icons/manifest.json                                 flat list for docs / tests
    medo-motion/templates/render/lib/icons.js           Canvas painter for engine K
    medo-motion/templates/procedural-reels/icons.py     Pillow painter for engine P

The registry is the only file a human edits: icons are stroke-only on a 24×24 grid and every
colour is passed at draw time, so the same icon is brand-locked to palette v2 in both engines.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
REGISTRY = HERE / "registry.json"


# --------------------------------------------------------------------------- geometry
def _arc(cx: float, cy: float, r: float, a0: float, a1: float, n: int = 24) -> list[list[float]]:
    return [[round(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / (n - 1))), 3),
             round(cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / (n - 1))), 3)] for i in range(n)]


def _circle(cx: float, cy: float, r: float, n: int = 56) -> list[list[float]]:
    return [[round(cx + r * math.cos(2 * math.pi * i / n), 3), round(cy + r * math.sin(2 * math.pi * i / n), 3)]
            for i in range(n)]


def _round_rect(x: float, y: float, w: float, h: float, r: float) -> list[list[float]]:
    r = max(0.0, min(r, w / 2, h / 2))
    pts: list[list[float]] = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0),
                       (x + r, y + h - r, 90), (x + r, y + r, 180)):
        pts += _arc(cx, cy, r, a0, a0 + 90, 5) if r else [[round(cx, 3), round(cy, 3)]]
    return pts


def _expand(shape: dict) -> dict:
    """Turn one registry primitive into either a polyline, a dot or a filled rect."""
    kind = shape["t"]
    if kind == "line":
        pts, closed = [list(map(float, p)) for p in shape["p"]], False
        return {"k": "s", "pts": pts, "closed": closed}
    if kind == "poly":
        return {"k": "s", "pts": [list(map(float, p)) for p in shape["p"]], "closed": bool(shape.get("closed"))}
    if kind == "rect":
        return {"k": "s", "pts": _round_rect(shape["x"], shape["y"], shape["w"], shape["h"], shape.get("r", 0)),
                "closed": True}
    if kind == "circle":
        return {"k": "s", "pts": _circle(shape["c"][0], shape["c"][1], shape["r"]), "closed": True}
    if kind == "arc":
        return {"k": "s", "pts": _arc(shape["c"][0], shape["c"][1], shape["r"], shape["a"][0], shape["a"][1]),
                "closed": False}
    if kind == "dot":
        return {"k": "d", "c": list(map(float, shape["c"])), "r": float(shape["r"])}
    if kind == "fillrect":
        return {"k": "f", "x": shape["x"], "y": shape["y"], "w": shape["w"], "h": shape["h"], "r": shape.get("r", 0)}
    raise SystemExit(f"unknown primitive {kind!r}")


def build_model(reg: dict) -> list[dict]:
    out = []
    seen = set()
    for icon in reg["icons"]:
        if icon["id"] in seen:
            raise SystemExit(f"duplicate icon id {icon['id']}")
        seen.add(icon["id"])
        if not icon.get("ar"):
            raise SystemExit(f"{icon['id']}: every icon needs an Arabic label for the reels")
        out.append({
            "id": icon["id"], "ar": icon["ar"], "en": icon["en"], "group": icon.get("group", "misc"),
            "anim": {"draw": icon["anim"]["draw"], "stagger": icon["anim"]["stagger"],
                     "pulse_hz": icon["anim"].get("pulse_hz", 1.2)},
            "parts": [_expand(s) for s in icon["shapes"]],
        })
    return out


# --------------------------------------------------------------------------- SVG
SVG_STYLE = """<style>
  .a{fill:none;stroke:currentColor;stroke-width:%(sw)s;stroke-linecap:round;stroke-linejoin:round;
     stroke-dasharray:1;stroke-dashoffset:1;animation:draw %(dur)s cubic-bezier(.25,.9,.25,1) both}
  .d{fill:var(--icon-accent,currentColor);stroke:none;transform-box:fill-box;transform-origin:center;
     animation:dotIn .35s ease-out both,dotPulse %(period)s infinite ease-in-out}
  .f{fill:var(--icon-accent,currentColor);stroke:none;animation:fadeIn .5s ease-out both}
  @keyframes draw{to{stroke-dashoffset:0}}
  @keyframes dotIn{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:scale(1)}}
  @keyframes dotPulse{0%%,100%%{opacity:.5}50%%{opacity:1}}
  @keyframes fadeIn{from{opacity:0}to{opacity:1}}
  @media (prefers-reduced-motion:reduce){.a{animation:none;stroke-dashoffset:0}.d,.f{animation:none}}
</style>"""


def to_svg(icon: dict, reg: dict) -> str:
    draw, stagger, hz = icon["anim"]["draw"], icon["anim"]["stagger"], icon["anim"]["pulse_hz"]
    body = []
    for i, part in enumerate(icon["parts"]):
        delay = round(i * stagger, 3)
        if part["k"] == "s":
            pts = " ".join(f"{p[0]:g},{p[1]:g}" for p in part["pts"])
            tag = "polygon" if part["closed"] else "polyline"
            body.append(f'  <{tag} class="a" pathLength="1" points="{pts}" style="animation-delay:{delay}s"/>')
        elif part["k"] == "d":
            body.append(f'  <circle class="d" cx="{part["c"][0]:g}" cy="{part["c"][1]:g}" r="{part["r"]:g}" '
                        f'style="animation-delay:{delay}s,{delay + 0.35}s"/>')
        else:
            body.append(f'  <rect class="f" x="{part["x"]:g}" y="{part["y"]:g}" width="{part["w"]:g}" '
                        f'height="{part["h"]:g}" rx="{part["r"]:g}" style="animation-delay:{delay}s"/>')
    style = SVG_STYLE % {"sw": reg.get("stroke", 2), "dur": f"{draw}s", "period": f"{round(1 / hz, 2)}s"}
    title = f"{icon['en']} — {icon['ar']}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {reg["grid"]} {reg["grid"]}" width="96" '
            f'height="96" role="img" aria-label="{title}" data-icon="{icon["id"]}">\n'
            f'  <title>{title}</title>\n' + style + "\n" + "\n".join(body) + "\n</svg>\n")


# --------------------------------------------------------------------------- painters
JS_TEMPLATE = r"""// AUTO-GENERATED by medo-motion/icons/build.py — edit icons/registry.json and rebuild.
// Animated stroke icons for engine K (canvas). Colours are passed at draw time, so the same icon
// is brand-locked to palette v2: outline = BRAND.colors.ink|paper, accent = red|salmon.
export const ICONS = %(data)s;

export const ICON_NAMES = Object.keys(ICONS);

const clamp01 = v => (v < 0 ? 0 : v > 1 ? 1 : v);

function segLen(pts, closed) {
  let total = 0;
  for (let i = 1; i < pts.length; i++) total += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  if (closed) total += Math.hypot(pts[0][0] - pts[pts.length - 1][0], pts[0][1] - pts[pts.length - 1][1]);
  return total;
}

function tracePartial(ctx, pts, closed, p) {
  if (p <= 0) return;
  const n = pts.length, target = segLen(pts, closed) * clamp01(p);
  let walked = 0;
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i <= n; i++) {
    const a = pts[i - 1], b = pts[i %% n];
    if (i === n && !closed) break;
    const d = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (walked + d >= target) {
      const f = d ? (target - walked) / d : 1;
      ctx.lineTo(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f);
      break;
    }
    ctx.lineTo(b[0], b[1]);
    walked += d;
  }
  ctx.stroke();
}

/** Total seconds one icon needs to finish drawing. */
export function iconDuration(name) {
  const ic = ICONS[name];
  if (!ic) throw new Error('unknown icon: ' + name);
  return ic.anim.draw + ic.parts.length * ic.anim.stagger;
}

/**
 * Draw an animated icon centred on (x, y).
 * @param {CanvasRenderingContext2D} ctx
 * @param {string} name  registry id, e.g. 'cpu' | 'plug-connected'
 * @param {number} t     seconds since the icon should start animating
 * @param {{x:number,y:number,size?:number,color?:string,accent?:string,stroke?:number,alpha?:number,loop?:boolean}} o
 */
export function drawIcon(ctx, name, t, { x = 0, y = 0, size = 96, color = '#F3F2F1', accent = '#CB271B', stroke = 2, alpha = 1, loop = false } = {}) {
  const ic = ICONS[name];
  if (!ic) throw new Error('unknown icon: ' + name + ' (have: ' + ICON_NAMES.join(', ') + ')');
  const total = iconDuration(name);
  const time = loop && t > total ? t %% (total + 1.2) : t;
  const k = size / %(grid)s, { draw, stagger, pulse_hz: hz } = ic.anim;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(k, k);
  ctx.globalAlpha *= alpha;
  ctx.lineWidth = stroke;   // in the 24x24 grid, scaled by the transform above
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.strokeStyle = color;
  ctx.fillStyle = accent;
  ic.parts.forEach((part, i) => {
    const p = clamp01((time - i * stagger) / draw);
    if (p <= 0) return;
    if (part.k === 's') {
      tracePartial(ctx, part.pts, part.closed, p);
    } else if (part.k === 'd') {
      const pulse = 0.45 + 0.55 * (0.5 + 0.5 * Math.sin(2 * Math.PI * hz * time));
      ctx.globalAlpha = alpha * clamp01(p * 3) * pulse;
      ctx.beginPath(); ctx.arc(part.c[0], part.c[1], part.r * (0.85 + 0.15 * pulse), 0, Math.PI * 2); ctx.fill();
      ctx.globalAlpha = alpha;
    } else {
      ctx.globalAlpha = alpha * clamp01(p * 2);
      const r = Math.min(part.r, part.w / 2, part.h / 2);
      if (r > 0 && ctx.roundRect) { ctx.beginPath(); ctx.roundRect(part.x, part.y, part.w, part.h, r); ctx.fill(); }
      else ctx.fillRect(part.x, part.y, part.w, part.h);
      ctx.globalAlpha = alpha;
    }
  });
  ctx.restore();
}

export default drawIcon;
"""

PY_TEMPLATE = '''# AUTO-GENERATED by medo-motion/icons/build.py — edit icons/registry.json and rebuild.
"""Animated stroke icons for engine P (Pillow / numpy). Palette v2 colours are passed at draw time.

    from icons import draw_icon
    draw_icon(fr, 'cpu', t, 540, 400, size=128, color=WHITE, accent=RED)
"""
from __future__ import annotations

import functools
import json
import math

import numpy as np
from PIL import Image, ImageDraw

GRID = %(grid)d
SS = 3  # supersampling

ICONS = json.loads("""%(data)s""")


def icon_names():
    return list(ICONS)


def icon_duration(name):
    ic = ICONS[name]
    return ic["anim"]["draw"] + len(ic["parts"]) * ic["anim"]["stagger"]


def _seg_len(pts, closed):
    total = sum(math.dist(pts[i], pts[i - 1]) for i in range(1, len(pts)))
    if closed:
        total += math.dist(pts[0], pts[-1])
    return total


def _partial(pts, closed, p):
    """Points of the polyline up to fraction p of its length."""
    if p >= 1:
        return list(pts) + ([pts[0]] if closed else [])
    target = _seg_len(pts, closed) * max(0.0, p)
    out = [pts[0]]
    walked = 0.0
    n = len(pts)
    for i in range(1, n + (1 if closed else 0)):
        a, b = pts[i - 1], pts[i %% n]
        d = math.dist(a, b)
        if walked + d >= target:
            f = (target - walked) / d if d else 1.0
            out.append([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f])
            break
        out.append(list(b))
        walked += d
    return out


@functools.lru_cache(maxsize=512)
def icon_sprite(name, size, color, accent, frame_key, stroke=2.0):
    """RGBA sprite for one moment of the animation (frame_key = quantised seconds)."""
    ic = ICONS[name]
    px = max(8, int(size)) * SS
    k = px / GRID
    im = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    t = frame_key / 1000.0
    draw, stagger, hz = ic["anim"]["draw"], ic["anim"]["stagger"], ic["anim"]["pulse_hz"]
    width = max(1, int(round(stroke * k)))
    for i, part in enumerate(ic["parts"]):
        p = min(1.0, max(0.0, (t - i * stagger) / draw))
        if p <= 0:
            continue
        if part["k"] == "s":
            pts = [(x * k, y * k) for x, y in _partial(part["pts"], part["closed"], p)]
            if len(pts) > 1:
                d.line(pts, fill=color + (255,), width=width, joint="curve")
            for x, y in (() if part["closed"] else (pts[0], pts[-1])):  # round caps at the ends only
                d.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill=color + (255,))
        elif part["k"] == "d":
            pulse = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(2 * math.pi * hz * t))
            a = int(255 * min(1.0, p * 3) * pulse)
            cx, cy, r = part["c"][0] * k, part["c"][1] * k, part["r"] * (0.85 + 0.15 * pulse) * k
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=accent + (a,))
        else:
            a = int(255 * min(1.0, p * 2))
            x0, y0 = part["x"] * k, part["y"] * k
            x1, y1 = (part["x"] + part["w"]) * k, (part["y"] + part["h"]) * k
            d.rounded_rectangle((x0, y0, x1, y1), radius=part["r"] * k, fill=accent + (a,))
    return im.resize((max(8, int(size)), max(8, int(size))), Image.LANCZOS)


def draw_icon(fr, name, t, x, y, size=128, color=(243, 242, 241), accent=(203, 39, 27),
              alpha=1.0, loop=True, stroke=2.0):
    """Blend an animated icon (centred on x, y) into a float32 HxWx3/4 frame in place."""
    if loop and t > icon_duration(name):
        t = t %% (icon_duration(name) + 1.2)
    spr = icon_sprite(name, int(size), tuple(color[:3]), tuple(accent[:3]), round(t * 1000), float(stroke))
    src = np.asarray(spr).astype(np.float32)
    h, w = src.shape[:2]
    h0 = int(round(y - h / 2))
    w0 = int(round(x - w / 2))
    fh, fw = fr.shape[:2]
    y0, y1 = max(0, h0), min(fh, h0 + h)
    x0, x1 = max(0, w0), min(fw, w0 + w)
    if y0 >= y1 or x0 >= x1:
        return fr
    part = src[y0 - h0:y1 - h0, x0 - w0:x1 - w0]
    a = part[:, :, 3:4] / 255.0 * alpha
    region = fr[y0:y1, x0:x1, :3]
    fr[y0:y1, x0:x1, :3] = region * (1 - a) + part[:, :, :3] * a
    return fr
'''


def artefacts() -> dict[Path, str]:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    model = build_model(reg)
    files: dict[Path, str] = {}
    for icon in model:
        files[HERE / "svg" / f"{icon['id']}.svg"] = to_svg(icon, reg)
    manifest = {
        "_doc": "Generated index of the animated icon layer. Rebuild with python medo-motion/icons/build.py",
        "grid": reg["grid"], "stroke": reg["stroke"],
        "icons": [{"id": i["id"], "ar": i["ar"], "en": i["en"], "group": i["group"],
                   "svg": f"icons/svg/{i['id']}.svg", "draw_seconds": round(i["anim"]["draw"], 2)}
                  for i in model],
    }
    files[HERE / "manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    data = json.dumps({i["id"]: i for i in model}, ensure_ascii=False, indent=1)
    files[SKILL / "templates" / "render" / "lib" / "icons.js"] = JS_TEMPLATE % {"data": data, "grid": reg["grid"]}
    files[SKILL / "templates" / "procedural-reels" / "icons.py"] = PY_TEMPLATE % {
        "data": json.dumps({i["id"]: i for i in model}, ensure_ascii=False), "grid": reg["grid"]}
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if the generated files are stale")
    args = ap.parse_args()
    files = artefacts()
    stale = []
    for path, text in files.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                stale.append(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    if args.check:
        for path in stale:
            print("STALE", path.relative_to(SKILL))
        print("icons:", "in sync" if not stale else f"{len(stale)} stale file(s)")
        return 1 if stale else 0
    print(f"icons: wrote {len(files)} files for {len(json.loads(REGISTRY.read_text(encoding='utf-8'))['icons'])} icons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
