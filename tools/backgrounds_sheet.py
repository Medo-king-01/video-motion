#!/usr/bin/env python3
"""Review sheet for the animated backgrounds — and a P↔K parity check in one place.

Renders a contact sheet of every background in `medo-motion/motion/backgrounds.json` (both themes) as
engine P draws it, and — when Chromium is available — the same frames through engine K, with the
per-tile difference so a drift between `backgrounds.py` and `lib/backgrounds.js` is visible instead of
argued about.

    python3 tools/backgrounds_sheet.py                     # -> cache/backgrounds-sheet.png
    python3 tools/backgrounds_sheet.py --only pulse,wash --theme dark
    python3 tools/backgrounds_sheet.py --compare           # P | K | diff per tile
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "medo-motion"
P_DIR = SKILL / "templates" / "procedural-reels"
K_LIB = SKILL / "templates" / "render" / "lib" / "backgrounds.js"
CATALOG = SKILL / "motion" / "backgrounds.json"

sys.path.insert(0, str(P_DIR))


def catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def background_ids(only: list[str] | None = None) -> list[str]:
    ids = [b["id"] for b in catalog()["backgrounds"]]
    return [i for i in ids if not only or i in only]


def render_p(bg: str, w: int, h: int, t: float, theme: str) -> np.ndarray:
    import backgrounds  # noqa: PLC0415

    return backgrounds.frame(bg, w, h, t, theme)


def render_k(bgs: list[str], w: int, h: int, t: float, theme: str) -> dict[str, np.ndarray]:
    """Render the same frames in engine K (real Canvas in Chromium) and return them as arrays."""
    import base64
    import io

    from PIL import Image  # noqa: PLC0415

    cache = ROOT / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    page_path = cache / "_bgk.html"
    js_path = cache / "_bgk.mjs"
    page_path.write_text(f"""<!doctype html><meta charset="utf-8"><body><script type="module">
const {{ backgroundFrame }} = await import({json.dumps(str(K_LIB))} + '?v=' + Date.now());
const ids = {json.dumps(bgs)};
const out = {{}};
for (const id of ids) {{
  const c = document.createElement('canvas');
  c.width = {w}; c.height = {h};
  backgroundFrame(c.getContext('2d'), {w}, {h}, {t}, {{ id, theme: {json.dumps(theme)} }});
  out[id] = c.toDataURL('image/png');
}}
window.__out = out;
window.__done = true;
</script></body>""", encoding="utf-8")
    js_path.write_text(f"""
const {{ chromium }} = await import({json.dumps(str(ROOT / "tools/toolkit/node_modules/playwright-core/index.mjs"))});
const browser = await chromium.launch({{ executablePath: process.env.MEDO_CHROMIUM,
  args: (process.env.MEDO_CHROMIUM_ARGS || '').split(' ').filter(Boolean) }});
const page = await browser.newPage();
const errors = [];
page.on('console', m => {{ if (m.type() === 'error') errors.push(m.text()); }});
page.on('pageerror', e => errors.push(String(e)));
await page.goto('file://{page_path}');
await page.waitForFunction(() => window.__done === true, null, {{ timeout: 120000 }}).catch(e => errors.push(String(e)));
const data = await page.evaluate(() => window.__out || {{}});
if (!Object.keys(data).length) console.error('engine K rendered nothing: ' + errors.join(' | '));
console.log(JSON.stringify(data));
await browser.close();
""", encoding="utf-8")
    env = subprocess.run(["node", str(ROOT / "tools" / "chromium.mjs"), "--env"],
                         capture_output=True, text=True, cwd=ROOT).stdout
    r = subprocess.run(["bash", "-lc", f'{env}\nnode {js_path}'], capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    payload = json.loads(r.stdout.strip().splitlines()[-1] or "{}")
    if not payload:
        raise RuntimeError(r.stderr or "engine K returned no frames")
    return {k: np.asarray(Image.open(io.BytesIO(base64.b64decode(v.split(",", 1)[1]))).convert("RGB"))
            for k, v in payload.items()}


def sheet(out: Path, only=None, themes=("dark", "light"), compare=False,
          w: int = 270, h: int = 480, t: float = 2.4) -> Path:
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415

    ids = background_ids(only)
    cat = {b["id"]: b for b in catalog()["backgrounds"]}
    cols = len(ids)
    cols_per_theme = cols * (3 if compare else 1)
    pad, label_h = 10, 22
    img = Image.new("RGB", (cols_per_theme * (w + pad) + pad,
                            len(themes) * (h + label_h + pad) + pad + 26), (3, 3, 3))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(str(sorted((ROOT / "assets" / "fonts").rglob("Cairo*Regular*.ttf"))[0]), 14)
    except Exception:  # noqa: BLE001
        font = ImageFont.load_default()
    d.text((pad, 6), f"Medo backgrounds — {len(ids)} patterns × {len(themes)} themes"
                     + (" · P | K | diff" if compare else " (engine P)"),
           font=font, fill=(213, 174, 166))
    kf = {}
    if compare:
        for theme in themes:
            kf[theme] = render_k(ids, w, h, t, theme)
    for row, theme in enumerate(themes):
        y0 = 26 + pad + row * (h + label_h + pad)
        for i, bg in enumerate(ids):
            p = render_p(bg, w, h, t, theme)
            pil = Image.fromarray(p, "RGB").resize((w, h))
            x = pad + i * (w + pad) * (3 if compare else 1)
            if not compare:
                img.paste(pil, (x, y0))
                d.text((x + 2, y0 + h + 3), f"{bg} · {cat[bg]['ar']}", font=font, fill=(216, 215, 213))
                continue
            k = kf[theme][bg]
            kpil = Image.fromarray(k, "RGB").resize((w, h))
            diff = np.abs(p.astype(np.int16) - k.astype(np.int16)).mean()
            dimg = Image.fromarray(np.clip(np.abs(p.astype(np.int16) - k.astype(np.int16)) * 3, 0, 255)
                                   .astype(np.uint8), "RGB").resize((w, h))
            for j, tile in enumerate((pil, kpil, dimg)):
                img.paste(tile, (x + j * (w + pad), y0))
            d.text((x + 2, y0 + h + 3), f"{bg} · {theme} · Δ{diff:.1f}", font=font,
                   fill=(159, 8, 3) if diff > 12 else (216, 215, 213))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma separated ids")
    ap.add_argument("--theme", choices=("dark", "light", "both"), default="both")
    ap.add_argument("--compare", action="store_true", help="render engine K beside P and show the diff")
    ap.add_argument("--out", default=str(ROOT / "cache" / "backgrounds-sheet.png"))
    ap.add_argument("--time", type=float, default=2.4)
    args = ap.parse_args()
    only = [s.strip() for s in args.only.split(",")] if args.only else None
    themes = ("dark", "light") if args.theme == "both" else (args.theme,)
    path = sheet(Path(args.out), only=only, themes=themes, compare=args.compare, t=args.time)
    print(f"sheet -> {path}")
    if args.compare:
        ids = background_ids(only)
        for theme in themes:
            p = [render_p(bg, 270, 480, args.time, theme).astype(np.int16) for bg in ids]
            k = render_k(ids, 270, 480, args.time, theme)
            worst = max(((np.abs(a - k[bg].astype(np.int16))).mean(), bg) for a, bg in zip(p, ids, strict=True))
            print(f"  {theme:5s} worst Δ {worst[0]:.2f} ({worst[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
