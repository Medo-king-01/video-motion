#!/usr/bin/env python3
"""Engine P vs engine K, the same drawing side by side — measured, not assumed.

Engine K's `lib/art.js` is a port of engine P's drawn sprites (`art.py` and the sprite helpers of
`lib.py`). This tool draws every sprite, and three typical talking-reel frames (presenter + speech
bubble + Arabic caption, a parts card, a follow call-to-action), once with each engine, then
reports how far apart they are and writes sheets a person can look at.

    python3 tools/art_parity.py                    # table + sheets in out/art-parity/
    python3 tools/art_parity.py --check            # exit 1 when a sprite drifts past the limits
    python3 tools/art_parity.py --json report.json
    python3 tools/art_parity.py --only person,bubble

Needs the render toolkit (`bash tools/setup.sh`) for the engine-K half.

What the numbers mean, per image, both engines composited on mid-grey:
    size    the two sprite boxes, in pixels — must be identical
    shape   share of the silhouette where the two engines agree to within one pixel, 1.0 = same
            outline. A one-pixel band is allowed because the two rasterisers place an edge up to
            a third of a pixel apart, which on a thin stroke is a visible share of its area.
    iou     the strict overlap (intersection over union), reported, not gated
    diff    mean absolute colour difference, 0..255 — anti-aliasing alone costs about 1
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P_DIR = ROOT / "medo-motion" / "templates" / "procedural-reels"
FONT = ROOT / "assets" / "fonts" / "Cairo" / "Cairo_800ExtraBold.ttf"
POSES = ROOT / "assets" / "poses"

# Limits for --check. A port that keeps the geometry stays far inside them; a wrong coordinate,
# a missing shape or a swapped colour does not.
MIN_SHAPE = 0.995
MAX_DIFF = 4.0
# Sprites carrying text are shaped by two different text stacks (FreeType/HarfBuzz vs the browser).
MAX_DIFF_TEXT = 7.0
GREY = 128

# P's RGB tuples and the K palette token that is the same colour (lib/brand.js).
COLOURS = {
    "paper": (243, 242, 241), "red": (203, 39, 27), "redDeep": (159, 8, 3), "ink": (10, 10, 10),
    "inkShadow": (3, 3, 3), "blush": (213, 174, 166), "inkSoft": (113, 113, 122),
    "salmon": (217, 127, 104), "gray2": (201, 197, 194), "gray4": (163, 162, 160),
}


def _c(token: str) -> tuple[int, int, int]:
    return COLOURS[token]


def cases() -> list[dict]:
    """Every sprite and every variant. `p` is the engine-P call, `options` the engine-K one."""
    out: list[dict] = []

    def add(case_id, art, p, options=None, text=False):
        out.append({"id": case_id, "art": art, "p": p, "options": options or {}, "text": text})

    for screen in ("glow", "bad", "blank", "dark"):
        add(f"laptop-{screen}", "laptop", ("art", "laptop", {"w": 520, "screen": screen}), {"w": 520, "screen": screen})
    add("desktop", "desktop", ("art", "desktop", {"w": 420}), {"w": 420})
    for kind in ("cpu", "ram", "ssd", "display", "gpu", "battery"):
        add(f"part-{kind}", "partIcon", ("art", "icon", {"kind": kind, "s": 170}), {"kind": kind, "s": 170})
    for pose in ("stand", "hold", "shrug", "talk", "paper", "scratch", "cross"):
        add(f"person-pose-{pose}", "person", ("art", "person", {"pose": pose}), {"pose": pose})
    for expr in ("smile", "excited", "frustrated", "confused", "talk1", "talk2", "confident"):
        add(f"person-expr-{expr}", "person", ("art", "person", {"expr": expr}), {"expr": expr})
    add("person-blink", "person", ("art", "person", {"blink": True}), {"blink": True})
    add("person-dressed", "person",
        ("art", "person", {"shirt": _c("paper"), "hairstyle": "short", "tie": _c("red"), "collar": _c("gray2")}),
        {"shirt": "paper", "hairstyle": "short", "tie": "red", "collar": "gray2"})
    add("paper-spec", "paperSpec", ("art", "paper_spec", {"w": 200, "checks": 3}), {"w": 200, "checks": 3})
    add("follow", "followButton", ("art", "follow_button", {}), {}, text=True)
    add("follow-done", "followButton", ("art", "follow_button", {"done": True}), {"done": True}, text=True)
    add("cursor", "cursor", ("art", "cursor", {"s": 90}), {"s": 90})
    add("sparkle", "sparkle", ("lib", "sparkle", {"r": 40}), {"r": 40})
    add("pill", "pill", ("lib", "pill", {"w": 300, "h": 80, "color": _c("ink")}), {"w": 300, "h": 80, "color": "ink"})
    add("bill", "bill", ("lib", "bill", {"w": 150}), {"w": 150}, text=True)
    add("checkmark", "checkmark", ("lib", "checkmark", {"s": 90}), {"s": 90})
    add("checkmark-bare", "checkmark", ("lib", "checkmark", {"s": 90, "bg": False}), {"s": 90, "bg": False})
    add("crossmark", "crossmark", ("lib", "crossmark", {"s": 90}), {"s": 90})
    for tail in ("bl", "br", "bc"):
        add(f"bubble-{tail}", "bubble", ("lib", "bubble", {"w": 520, "h": 180, "tail": tail}), {"w": 520, "h": 180, "tail": tail})
    add("bubble-outline", "bubble", ("lib", "bubble", {"w": 420, "h": 240, "color": _c("ink"), "outline": _c("paper")}),
        {"w": 420, "h": 240, "color": "ink", "outline": "paper"})
    return out


def scenes() -> list[dict]:
    """Three frames of the kind engine P is used for, as a neutral list of drawing operations."""
    w, h = 1080, 1920
    art = lambda name, cx, cy, options=None, **place: {"op": "art", "art": name, "cx": cx, "cy": cy,  # noqa: E731
                                                       "options": options or {}, "place": place}
    text = lambda t, cx, cy, size, color="paper": {"op": "text", "text": t, "cx": cx, "cy": cy,  # noqa: E731
                                                   "size": size, "color": color}
    return [
        {"id": "scene-presenter", "w": w, "h": h, "ops": [
            {"op": "fill", "color": "ink"},
            {"op": "image", "image": "explain", "cx": 330, "cy": 1390, "height": 1150, "anchor": [0.5, 0.9934]},
            art("bubble", 700, 470, {"w": 560, "h": 220, "tail": "bl"}),
            text("المعالج هو عقل الجهاز", 700, 458, 50, "ink"),
            art("laptop", 780, 980, {"w": 420, "screen": "glow"}),
            art("checkmark", 640, 1250, {"s": 90}), art("crossmark", 780, 1250, {"s": 90}),
            art("sparkle", 920, 1250, {"r": 44}, rot=20),
            art("pill", 540, 1580, {"w": 900, "h": 130, "color": "red"}),
            text("اختار اللابتوب الصح من أول مرة", 540, 1580, 54),
        ]},
        {"id": "scene-card", "w": w, "h": h, "ops": [
            {"op": "fill", "color": "ink"},
            text("إيه اللي يهمك في المواصفات؟", 540, 300, 62),
            *[art("partIcon", 260 + (i % 3) * 280, 620 + (i // 3) * 300, {"kind": kind, "s": 190})
              for i, kind in enumerate(("cpu", "ram", "ssd", "display", "gpu", "battery"))],
            art("desktop", 330, 1310, {"w": 380}),
            art("paperSpec", 800, 1290, {"w": 230, "checks": 4}, rot=-6),
            art("bill", 760, 1560, {"w": 190}, rot=8), art("bill", 880, 1590, {"w": 190}, rot=-10, alpha=0.6),
            text("الرامات والهارد أهم من الشكل", 540, 1730, 50, "blush"),
        ]},
        {"id": "scene-cta", "w": w, "h": h, "ops": [
            {"op": "fill", "color": "ink"},
            art("person", 300, 1390, {"expr": "excited", "pose": "talk"}, anchor=[0.5, 1.0], scale=1.15),
            art("person", 820, 1390, {"expr": "confused", "pose": "scratch", "shirt": "inkSoft"},
                anchor=[0.5, 1.0], scale=0.9, flipX=True),
            art("bubble", 640, 380, {"w": 620, "h": 200, "tail": "bc"}),
            text("تابعني عشان يوصلك الجديد", 640, 370, 46, "ink"),
            art("followButton", 540, 1560, {}), art("cursor", 760, 1620, {"s": 90}, scale=1.4),
            art("followButton", 540, 1740, {"done": True}, scale=0.8),
        ]},
    ]


# ---------------------------------------------------------------- engine P
def _load_engine_p():
    os.environ.setdefault("REEL_DIR", str(ROOT))
    os.environ["REEL_FONT"] = str(FONT)
    if str(P_DIR) not in sys.path:
        sys.path.insert(0, str(P_DIR))
    import art  # noqa: PLC0415
    import lib  # noqa: PLC0415
    return lib, art


def _straight(sprite):
    """Premultiplied float RGBA -> straight 8-bit RGBA."""
    import numpy as np

    rgba = np.asarray(sprite, dtype=np.float32)
    alpha = rgba[..., 3:4]
    rgb = np.where(alpha > 0, rgba[..., :3] * 255.0 / np.maximum(alpha, 1e-6), 0)
    return np.clip(np.concatenate([rgb, alpha], axis=-1) + 0.5, 0, 255).astype(np.uint8)


def render_p(selected: list[dict], scene_list: list[dict], out: Path) -> dict:
    import numpy as np
    from PIL import Image

    lib, art = _load_engine_p()
    modules = {"art": art, "lib": lib}
    k_to_p = {"laptop": art.laptop, "desktop": art.desktop, "partIcon": art.icon, "person": art.person,
              "paperSpec": art.paper_spec, "followButton": art.follow_button, "cursor": art.cursor,
              "sparkle": lib.sparkle, "pill": lib.pill, "bill": lib.bill, "checkmark": lib.checkmark,
              "crossmark": lib.crossmark, "bubble": lib.bubble}
    out.mkdir(parents=True, exist_ok=True)
    meta: dict = {}
    for case in selected:
        module, func, kwargs = case["p"]
        if func == "person":
            kwargs = {"shirt": _c("red"), **kwargs}        # P has no default shirt; K's is brand red
        sprite = getattr(modules[module], func)(**kwargs)
        Image.fromarray(_straight(sprite), "RGBA").save(out / f"{case['id']}.png")
        meta[case["id"]] = {"w": int(sprite.shape[1]), "h": int(sprite.shape[0]), "textWidths": {}}
    for scene in scene_list:
        frame = np.zeros((scene["h"], scene["w"], 3), np.float32)
        widths = {}
        for op in scene["ops"]:
            if op["op"] == "fill":
                frame[:] = _c(op["color"])
            elif op["op"] == "art":
                options = {k: (_c(v) if isinstance(v, str) and v in COLOURS else v) for k, v in op["options"].items()}
                if op["art"] == "person":
                    options = {"shirt": _c("red"), **options}
                sprite = k_to_p[op["art"]](**options)
                place = op.get("place", {})
                lib.paste(frame, sprite, op["cx"], op["cy"], scale=place.get("scale", 1.0), rot=place.get("rot", 0.0),
                          alpha=place.get("alpha", 1.0), anchor=tuple(place.get("anchor", (0.5, 0.5))),
                          flipx=place.get("flipX", False))
            elif op["op"] == "image":
                image = Image.open(POSES / f"{op['image']}.png").convert("RGBA")
                height = op["height"]
                image = image.resize((int(image.width * height / image.height), height), Image.LANCZOS)
                lib.paste(frame, lib.prem(np.array(image)), op["cx"], op["cy"], anchor=tuple(op.get("anchor", (0.5, 0.5))))
            elif op["op"] == "text":
                sprite = lib.text_sprite(op["text"], op["size"], _c(op["color"]))
                lib.paste(frame, sprite, op["cx"], op["cy"])
                ink = np.flatnonzero(sprite[..., 3].max(axis=0) > 8)
                widths[op["text"]] = int(ink[-1] - ink[0] + 1) if ink.size else 0
        Image.fromarray(np.clip(frame + 0.5, 0, 255).astype(np.uint8), "RGB").save(out / f"{scene['id']}.png")
        meta[scene["id"]] = {"w": scene["w"], "h": scene["h"], "textWidths": widths}
    meta["_backend"] = {"layout": lib.LAYOUT_BACKEND, "supersample": int(lib.SS)}
    return meta


# ---------------------------------------------------------------- engine K
def render_k(selected: list[dict], scene_list: list[dict], out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    images = {op["image"]: str(POSES / f"{op['image']}.png")
              for scene in scene_list for op in scene["ops"] if op["op"] == "image"}
    spec = {"cases": [{"id": c["id"], "art": c["art"], "options": c["options"]} for c in selected],
            "scenes": scene_list, "fonts": {"Cairo": str(FONT)}, "images": images}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(spec, handle, ensure_ascii=False)
    try:
        # same launch environment the render toolkit uses (browser path + its shared libraries)
        command = (f'eval "$(node {shlex.quote(str(ROOT / "tools" / "chromium.mjs"))} --env)" && '
                   f'node {shlex.quote(str(ROOT / "tools" / "art_parity.mjs"))} '
                   f'--cases {shlex.quote(handle.name)} --out {shlex.quote(str(out))}')
        done = subprocess.run(["bash", "-c", command], capture_output=True, text=True, cwd=ROOT)
    finally:
        os.unlink(handle.name)
    if done.returncode != 0:
        raise SystemExit("engine K could not draw (is the render toolkit installed? `bash tools/setup.sh`)\n"
                         + (done.stderr or done.stdout).strip()[-1500:])
    return json.loads((out / "k.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- compare
def _on_grey(path: Path):
    import numpy as np
    from PIL import Image

    rgba = np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32)
    alpha = rgba[..., 3:4] / 255.0
    return rgba[..., :3] * alpha + GREY * (1 - alpha), rgba[..., 3]


def compare(image_id: str, p_dir: Path, k_dir: Path, has_text: bool = False, scene: bool = False) -> dict:
    import numpy as np

    p_rgb, p_alpha = _on_grey(p_dir / f"{image_id}.png")
    k_rgb, k_alpha = _on_grey(k_dir / f"{image_id}.png")
    row = {"id": image_id, "p_size": [p_rgb.shape[1], p_rgb.shape[0]], "k_size": [k_rgb.shape[1], k_rgb.shape[0]],
           "text": has_text, "scene": scene}
    row["same_size"] = row["p_size"] == row["k_size"]
    if not row["same_size"]:
        row.update(shape=0.0, iou=0.0, diff=255.0, changed=1.0, ok=False)
        return row
    if scene:
        row["shape"] = None
    else:
        import cv2

        a, b = p_alpha > 127, k_alpha > 127
        union = np.logical_or(a, b).sum()
        row["iou"] = round(float(np.logical_and(a, b).sum() / union), 4) if union else 1.0
        grow = lambda m: cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0  # noqa: E731
        stray = np.logical_and(a, ~grow(b)).sum() + np.logical_and(b, ~grow(a)).sum()
        row["shape"] = round(float(1 - stray / union), 4) if union else 1.0
    delta = np.abs(p_rgb - k_rgb).max(axis=-1)
    row["diff"] = round(float(delta.mean()), 3)
    row["changed"] = round(float((delta > 48).mean()), 4)          # share of clearly different pixels
    limit = MAX_DIFF_TEXT if has_text else MAX_DIFF
    row["ok"] = bool(scene or (row["shape"] >= MIN_SHAPE and row["diff"] <= limit))
    return row


def _label(draw, xy, text, font, fill=(243, 242, 241)):
    draw.text(xy, text, font=font, fill=fill)


def sheet(rows: list[dict], p_dir: Path, k_dir: Path, path: Path, cell: int = 250, cols: int = 3) -> None:
    """Sprites: P | K | difference, one triple per sprite."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype(str(FONT), 17)
    head = 26
    triple = cell * 3 + 16
    lines = (len(rows) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * triple + 8, lines * (cell + head + 10) + 8), (24, 24, 27))
    draw = ImageDraw.Draw(canvas)
    for index, row in enumerate(rows):
        x0, y0 = 8 + (index % cols) * triple, 8 + (index // cols) * (cell + head + 10)
        colour = (243, 242, 241) if row["ok"] else (203, 39, 27)
        _label(draw, (x0, y0), f"{row['id']}   P | K | diff   shape {row['shape']}  diff {row['diff']}", font, colour)
        tiles = []
        for folder in (p_dir, k_dir):
            rgb, _ = _on_grey(folder / f"{row['id']}.png")
            tiles.append(rgb)
        if row["same_size"]:
            delta = np.abs(tiles[0] - tiles[1]).max(axis=-1, keepdims=True)
            tiles.append(np.clip(np.repeat(delta, 3, axis=-1) * 4, 0, 255))
        for slot, tile in enumerate(tiles):
            image = Image.fromarray(tile.astype(np.uint8), "RGB")
            image.thumbnail((cell - 6, cell - 6), Image.LANCZOS)
            canvas.paste(image, (x0 + slot * cell + (cell - 6 - image.width) // 2, y0 + head + (cell - 6 - image.height) // 2))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)


def scene_sheet(scene_id: str, p_dir: Path, k_dir: Path, path: Path, height: int = 1280) -> None:
    """One frame: engine P | engine K | difference."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype(str(FONT), 30)
    p = np.asarray(Image.open(p_dir / f"{scene_id}.png").convert("RGB"), dtype=np.float32)
    k = np.asarray(Image.open(k_dir / f"{scene_id}.png").convert("RGB"), dtype=np.float32)
    delta = np.clip(np.repeat(np.abs(p - k).max(axis=-1, keepdims=True), 3, axis=-1) * 4, 0, 255)
    width = int(p.shape[1] * height / p.shape[0])
    canvas = Image.new("RGB", (width * 3 + 40, height + 70), (24, 24, 27))
    draw = ImageDraw.Draw(canvas)
    for slot, (tile, name) in enumerate(((p, "Engine P  (Pillow)"), (k, "Engine K  (Canvas)"), (delta, "difference x4"))):
        image = Image.fromarray(tile.astype(np.uint8), "RGB").resize((width, height), Image.LANCZOS)
        canvas.paste(image, (10 + slot * (width + 10), 60))
        _label(draw, (20 + slot * (width + 10), 12), name, font)
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, quality=92)


def run(only: list[str] | None = None, out: Path | None = None, with_scenes: bool = True, sheets: bool = True) -> dict:
    out = Path(out or ROOT / "out" / "art-parity")
    selected = [c for c in cases() if not only or any(c["id"].startswith(name) or c["art"] == name for name in only)]
    scene_list = scenes() if with_scenes else []
    p_dir, k_dir = out / "p", out / "k"
    p_meta = render_p(selected, scene_list, p_dir)
    k_meta = render_k(selected, scene_list, k_dir)
    rows = [compare(c["id"], p_dir, k_dir, has_text=c["text"]) for c in selected]
    scene_rows = []
    for scene in scene_list:
        row = compare(scene["id"], p_dir, k_dir, scene=True)
        row["text_widths"] = [
            {"text": text, "p": width, "k": round(k_meta[scene["id"]]["textWidths"].get(text, 0), 1)}
            for text, width in p_meta[scene["id"]]["textWidths"].items()]
        scene_rows.append(row)
    report = {"backend": p_meta["_backend"], "limits": {"min_shape": MIN_SHAPE, "max_diff": MAX_DIFF, "max_diff_text": MAX_DIFF_TEXT},
              "sprites": rows, "scenes": scene_rows, "out": str(out), "ok": all(r["ok"] for r in rows)}
    if sheets:
        if rows:
            sheet(rows, p_dir, k_dir, out / "sprites.png")
        for scene in scene_list:
            scene_sheet(scene["id"], p_dir, k_dir, out / f"{scene['id']}.jpg")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", help="output folder (default out/art-parity)")
    ap.add_argument("--only", help="comma-separated sprite names or case-id prefixes")
    ap.add_argument("--no-scenes", action="store_true", help="skip the three full frames")
    ap.add_argument("--json", help="write the report here")
    ap.add_argument("--check", action="store_true", help="exit 1 when a sprite is outside the limits")
    args = ap.parse_args(argv)
    report = run([s.strip() for s in args.only.split(",")] if args.only else None,
                 Path(args.out) if args.out else None, with_scenes=not args.no_scenes)
    print(f"engine P text layout: {report['backend']['layout']}, supersample x{report['backend']['supersample']}")
    print(f"{'sprite':24} {'size P':>10} {'size K':>10} {'shape':>7} {'iou':>7} {'diff':>7}  ")
    for row in report["sprites"]:
        print(f"{row['id']:24} {'x'.join(map(str, row['p_size'])):>10} {'x'.join(map(str, row['k_size'])):>10} "
              f"{row['shape']:>7.4f} {row['iou']:>7.4f} {row['diff']:>7.3f}  {'ok' if row['ok'] else 'DRIFT'}")
    for row in report["scenes"]:
        print(f"{row['id']:24} mean diff {row['diff']:.3f}, clearly different pixels {row['changed'] * 100:.2f}%")
        for item in row["text_widths"]:
            print(f"    text width P {item['p']} px / K {item['k']} px")
    drifted = [r["id"] for r in report["sprites"] if not r["ok"]]
    print(f"{len(report['sprites']) - len(drifted)}/{len(report['sprites'])} sprites inside the limits"
          f" (shape >= {MIN_SHAPE}, diff <= {MAX_DIFF}; with text <= {MAX_DIFF_TEXT}). Sheets: {report['out']}")
    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if drifted:
        print("outside the limits: " + ", ".join(drifted))
    return 1 if (args.check and drifted) else 0


if __name__ == "__main__":
    raise SystemExit(main())
