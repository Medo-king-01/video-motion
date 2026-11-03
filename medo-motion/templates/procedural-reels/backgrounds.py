"""Animated backgrounds for engine P — the same geometry engine K/R rasterise in lib/backgrounds.js.

A background is a pure function of time: `frame(bg, w, h, t)` returns an RGB uint8 array for that
instant, drawing from nothing. No accumulated state, so frame 137 is identical whether a render walks
forward, jumps, or renders chunks in parallel (engine P does all three).

Geometry is normalised to the frame box (fractions of w/h) and every colour is a BRAND ROLE from
`medo-motion/motion/backgrounds.json`; no hex appears inside a pattern.

    from backgrounds import frame, paint_into, ids
    bg = frame("pulse", 1080, 1920, 2.4)            # -> (1920,1080,3) uint8
    paint_into(canvas_rgb, "wash", t=2.4, theme="light")

tests/test_backgrounds.py fails if this file, lib/backgrounds.js and the catalog drift apart.
"""
from __future__ import annotations

import math
from functools import lru_cache

import cv2
import numpy as np

TAU = math.pi * 2

# Mirrors brand/brand.json (verified by tests/test_backgrounds.py).
PALETTE = {
    "red": "#CB271B", "red_bright": "#CB0801", "red_deep": "#9F0803",
    "ink": "#0A0A0A", "ink_soft": "#71717A", "paper": "#F3F2F1",
    "gray_1": "#D8D7D5", "gray_2": "#C9C5C2", "gray_3": "#BFBAB7", "gray_4": "#A3A2A0",
    "salmon": "#D97F68", "blush": "#D5AEA6", "inkShadow": "#030303",
}

# Embedded copy of the role maps — tests/test_backgrounds.py fails if this drifts from the catalog.
ROLES = {
    "dark": {
        "bg": "ink",
        "wash": "inkShadow",
        "line": "gray_1@0.10",
        "lineStrong": "gray_1@0.20",
        "matter": "ink@0.90",
        "text": "paper",
        "mid": "ink_soft",
        "accent": "red",
        "accentDeep": "red_deep",
        "accentSoft": "salmon@0.30",
        "glow": "red@0.50",
        "blobA": "salmon@0.26",
        "blobB": "red_deep@0.34",
        "paperWash": "ink@0.10",
    },
    "light": {
        "bg": "paper",
        "wash": "gray_1",
        "line": "ink@0.09",
        "lineStrong": "ink@0.18",
        "matter": "paper@0.92",
        "text": "ink",
        "mid": "gray_4",
        "accent": "red_deep",
        "accentDeep": "red",
        "accentSoft": "red_deep@0.20",
        "glow": "red@0.26",
        "blobA": "blush@0.55",
        "blobB": "red_deep@0.16",
        "paperWash": "gray_2@0.55",
    },
}

BACKGROUND_IDS = ("iso-grid", "grid-2d", "paper", "aura", "orbital", "orbit-mono",
                  "frames", "organic", "perspective", "glyphs", "pulse", "wash")

DEFAULTS = {"density": 45, "angle": 25, "speed": 1.0}
DEFAULT_PARAMS = {
    "iso-grid": {"angle": 25, "density": 45},
    "grid-2d": {"angle": 0, "density": 45},
    "paper": {"angle": 0, "density": 40},
    "aura": {"angle": 0, "density": 40},
    "orbital": {"angle": 0, "density": 45},
    "orbit-mono": {"angle": 0, "density": 45},
    "frames": {"angle": 0, "density": 40},
    "organic": {"angle": 45, "density": 35},
    "perspective": {"angle": 0, "density": 45},
    "glyphs": {"angle": 0, "density": 45},
    "pulse": {"angle": 0, "density": 30},
    "wash": {"angle": 0, "density": 45},
}


def ids() -> tuple[str, ...]:
    return BACKGROUND_IDS


def _rgb(name: str) -> tuple[float, float, float]:
    h = PALETTE[name].lstrip("#")
    return float(int(h[0:2], 16)), float(int(h[2:4], 16)), float(int(h[4:6], 16))


def role_color(role: str) -> tuple[tuple[float, float, float], float]:
    """'salmon@0.30' → ((217,127,104), 0.30). Roles only, never a raw hex."""
    name, _, alpha = role.partition("@")
    return _rgb(name), (float(alpha) if alpha else 1.0)


@lru_cache(maxsize=8)
def theme_colors(theme: str = "dark") -> tuple[tuple[tuple[float, float, float], float], ...]:
    """(role, (rgb, alpha)) pairs, cached — resolved once per theme, not per frame."""
    src = ROLES.get(theme) or ROLES["dark"]
    return tuple((k, role_color(v)) for k, v in src.items())


def _c(theme: str, role: str) -> tuple[np.ndarray, float]:
    for name, (rgb, alpha) in theme_colors(theme):
        if name == role:
            return np.array(rgb, np.float32), alpha
    raise KeyError(role)


def hash01(i: int) -> float:
    """Deterministic 0..1 hash — identical to hash01() in lib/backgrounds.js."""
    return ((i * 1103515245 + 12345) % 2147483647) / 2147483647


# ---------------- helpers (numpy twins of the Canvas helpers) ----------------

def _blend(img: np.ndarray, rgb, alpha: float, mask=None) -> None:
    """Alpha-composite a flat colour (optionally per-pixel masked, float 0..1) in place."""
    if mask is None:
        img[:] = img * (1 - alpha) + np.asarray(rgb, np.float32) * alpha
        return
    m = mask[..., None] * alpha
    img[:] = img * (1 - m) + np.asarray(rgb, np.float32) * m


# Mask maths runs on a smaller grid and is upscaled: a soft gradient loses nothing, and a frame
# budget is the difference between "usable in engine P" and "usable in a prototype".
MASK_SCALE = 2


@lru_cache(maxsize=128)
def _coords(w: int, h: int) -> tuple[np.ndarray, np.ndarray]:
    """Cached pixel-centre grids — allocating these per frame dominated the cost."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return yy, xx


def _mask(w: int, h: int, build) -> np.ndarray:
    """Build a mask at 1/MASK_SCALE then upscale — `build(sw, sh)` returns a (sh, sw) float array."""
    sw, sh = max(1, w // MASK_SCALE), max(1, h // MASK_SCALE)
    small = build(sw, sh).astype(np.float32)
    if (sw, sh) == (w, h):
        return small
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def _radial(w: int, h: int, cx: float, cy: float, r: float, falloff: float = 1.0) -> np.ndarray:
    """Soft disc mask: 1 at the centre → 0 at `r` (quadratic-ish falloff, like a radial gradient)."""
    def build(sw, sh):
        yy, xx = _coords(sw, sh)
        d = np.hypot(xx - cx * sw / w, yy - cy * sh / h) / max(r * sw / w, 1e-6)
        return np.clip(1.0 - d, 0.0, 1.0) ** falloff
    return _mask(w, h, build)


def _wash(img: np.ndarray, rgb, alpha: float, cx: float, cy: float, r: float) -> None:
    """Linear radial falloff — the numpy twin of two gradient stops (K/R use Canvas gradients)."""
    _blend(img, rgb, alpha, _radial(img.shape[1], img.shape[0], cx, cy, r, 1.0))


def _grid(img: np.ndarray, t: float, density: float, angle: float, rgb, alpha: float) -> None:
    """Straight grid, optionally rotated about the frame centre, drifting at 14/9 px per second."""
    h, w = img.shape[:2]
    size = max(10.0, density * (w / 420.0))
    ox, oy = (t * 14) % size, (t * 9) % size
    ca, sa = math.cos(-angle), math.sin(-angle)

    def build(sw, sh):
        k = sw / w
        yy, xx = _coords(sw, sh)
        dx, dy = xx - sw / 2.0, yy - sh / 2.0
        gx = dx * ca - dy * sa + sw / 2.0 - ox * k
        gy = dx * sa + dy * ca + sh / 2.0 - oy * k
        step = size * k
        w_line = max(1.2, 1.0 * k)
        return (((gx % step) < w_line) | ((gy % step) < w_line)).astype(np.float32)

    _blend(img, rgb, alpha, _mask(w, h, build))


def _beat(q: float) -> float:
    if 0.10 < q < 0.20:
        return math.sin((q - 0.10) / 0.10 * math.pi) * 0.15
    if 0.30 < q < 0.35:
        return -0.20
    if 0.35 <= q < 0.40:
        return 1.0
    if 0.40 <= q < 0.45:
        return -0.40
    if 0.60 < q < 0.80:
        return math.sin((q - 0.60) / 0.20 * math.pi) * 0.25
    return 0.0


# ---------------- the 12 backgrounds ----------------
# Every painter: (img, w, h, t, theme, density, angle) and draws in place.

def _paint_iso_grid(img, w, h, t, theme, density, angle):
    img[:] = _c(theme, "bg")[0]
    rgb, a = _c(theme, "glow")
    lx = w * 0.35 + math.sin(t * 0.6) * w * 0.15
    ly = h * 0.28 + math.cos(t * 0.45) * h * 0.09
    _wash(img, rgb, a, lx, ly, max(w, h) * 0.72)
    _grid(img, t, density, angle, *_c(theme, "line"))


def _paint_grid_2d(img, w, h, t, theme, density, angle):
    img[:] = _c(theme, "bg")[0]
    rgb, _ = _c(theme, "accent")
    pulse = 0.40 + math.sin(t * 1.2) * 0.16
    _wash(img, rgb, pulse, w * 0.28, h * 0.32, max(w, h) * 0.78)
    _grid(img, t, density, 0.0, rgb, 0.30)


def _paint_paper(img, w, h, t, theme, density, angle):
    img[:] = _c(theme, "bg")[0]
    rgb, a = _c(theme, "paperWash")
    for i in range(4):
        ox = w * (0.2 + i * 0.25) + math.sin(t * 0.3 + i) * w * 0.12
        oy = h * (0.15 + i * 0.22) + math.cos(t * 0.4 + i) * h * 0.08
        _wash(img, rgb, a, ox, oy, max(w, h) * 0.44)
    _grid(img, t, density, 0.0, *_c(theme, "line"))


def _paint_aura(img, w, h, t, theme, density, angle):
    img[:] = _c(theme, "bg")[0]
    rgb, a = _c(theme, "blobA")
    ax = w * 0.32 + math.sin(t * 0.5) * w * 0.16
    ay = h * 0.22 + math.cos(t * 0.4) * h * 0.08
    _wash(img, rgb, a, ax, ay, max(w, h) * 0.62)
    rgb, a = _c(theme, "blobB")
    bx = w * 0.72 + math.cos(t * 0.6) * w * 0.14
    by = h * 0.78 + math.sin(t * 0.5) * h * 0.08
    _wash(img, rgb, a, bx, by, max(w, h) * 0.62)


def _orbitals(img, w, h, t, theme, density, hot):
    """Two orbits with three nodes each — composited as ONE ring mask + ONE node mask, not 14."""
    base = min(w, h) * (density / 100.0) * 0.6
    line_rgb, line_a = _c(theme, "accentSoft") if hot else _c(theme, "lineStrong")
    node_rgb = _c(theme, "accent")[0] if hot else _c(theme, "text")[0]
    node_glow = 14.0 if hot else 0.0
    centres = ((w * 0.82, h * 0.16, 1), (w * 0.18, h * 0.84, -1))
    s_node = max(6.0, min(w, h) * 0.038)

    def rings(sw, sh):
        k = sw / w
        yy, xx = _coords(sw, sh)
        out = np.zeros((sh, sw), np.float32)
        for idx, (cx, cy, _d) in enumerate(centres):
            r = base * (1 + idx * 0.18) * k
            d = np.abs(np.hypot(xx - cx * k, yy - cy * k) - r)
            out = np.maximum(out, np.clip(1.0 - (d - 1.6 * k / 2.0), 0.0, 1.0))
        return out

    def nodes(sw, sh):
        k = sw / w
        yy, xx = _coords(sw, sh)
        out = np.zeros((sh, sw), np.float32)
        for idx, (cx, cy, direction) in enumerate(centres):
            r = base * (1 + idx * 0.18)
            for n in range(3):
                a = t * 0.5 * direction + n * (TAU / 3)
                nx, ny = (cx + math.cos(a) * r) * k, (cy + math.sin(a) * r) * k
                ca, sa = math.cos(-(a + math.pi / 4)), math.sin(-(a + math.pi / 4))
                dx, dy = xx - nx, yy - ny
                u, v = dx * ca - dy * sa, dx * sa + dy * ca
                half = s_node * k / 2
                square = ((np.abs(u) <= half) & (np.abs(v) <= half)).astype(np.float32)
                if node_glow:
                    d = np.hypot(dx, dy)
                    halo = np.clip(1.0 - (d - half * 2) / (half * 2 + node_glow * k), 0.0, 1.0) * 0.45
                    out = np.maximum(out, np.maximum(square, halo))
                else:
                    out = np.maximum(out, square)
        return out

    _blend(img, line_rgb, line_a, _mask(w, h, rings))
    _blend(img, node_rgb, 1.0, _mask(w, h, nodes))


def _ring(w, h, cx, cy, r, width):
    def build(sw, sh):
        k = sw / w
        yy, xx = _coords(sw, sh)
        d = np.abs(np.hypot(xx - cx * k, yy - cy * k) - r * k)
        return np.clip(1.0 - (d - width * k / 2.0), 0.0, 1.0)
    return _mask(w, h, build)


def _square(w, h, cx, cy, s, rot):
    def build(sw, sh):
        k = sw / w
        yy, xx = _coords(sw, sh)
        ca, sa = math.cos(-rot), math.sin(-rot)
        dx, dy = xx - cx * k, yy - cy * k
        u, v = dx * ca - dy * sa, dx * sa + dy * ca
        half = s * k / 2
        return ((np.abs(u) <= half) & (np.abs(v) <= half)).astype(np.float32)
    return _mask(w, h, build)


def _orbital_backdrop(img, theme, w, h):
    """Radial ramp: `bg` at the centre → `wash` at the edge, exactly the Canvas gradient stops."""
    img[:] = _c(theme, "bg")[0]
    rgb, _ = _c(theme, "wash")
    t = _radial(w, h, w / 2, h / 2, max(w, h) * 0.8, falloff=1.0)
    _blend(img, rgb, 1.0, 1.0 - t)


def _paint_orbital(img, w, h, t, theme, density, angle):
    _orbital_backdrop(img, theme, w, h)
    _orbitals(img, w, h, t, theme, density, True)


def _paint_orbit_mono(img, w, h, t, theme, density, angle):
    _orbital_backdrop(img, theme, w, h)
    _orbitals(img, w, h, t, theme, density, False)


def _paint_frames(img, w, h, t, theme, density, angle):
    img[:] = _c(theme, "bg")[0]
    rgb, a = _c(theme, "accentSoft")
    _wash(img, rgb, a, w * 0.12, h * 0.10, max(w, h) * 0.60)
    _wash(img, rgb, a, w * 0.90, h * 0.92, max(w, h) * 0.50)
    _grid(img, t, density, 0.0, *_c(theme, "line"))
    accent, _ = _c(theme, "accent")
    pulse = 0.5 + math.sin(t * 2) * 0.35
    # both frames in ONE mask (two full-frame masks per frame is what made this expensive)
    boxes = [(0.08, 0.60, 0.42, 0.16), (0.52, 0.74, 0.34, 0.12)]

    def build(sw, sh):
        k = sw / w
        yy, xx = _coords(sw, sh)
        out = np.zeros((sh, sw), np.float32)
        for (x, y, fw, fh) in boxes:
            x0, y0 = x * sw, y * sh
            rw, rh = fw * sw, fh * sh
            thick = max(1.0, 1.4 * k)
            inside = (xx >= x0) & (xx <= x0 + rw) & (yy >= y0) & (yy <= y0 + rh)
            inner = ((xx >= x0 + thick) & (xx <= x0 + rw - thick)
                     & (yy >= y0 + thick) & (yy <= y0 + rh - thick))
            out = np.maximum(out, (inside & ~inner).astype(np.float32))
        return out

    _blend(img, accent, 0.5 * pulse, _mask(w, h, build))
    # status dot bottom-right + travelling scanline band
    _blend(img, accent, 1.0, _disc(w, h, w * 0.84 + math.sin(t) * w * 0.03, h * 0.93,
                                  max(2.5, w * 0.012), glow=6.0))
    ly = ((t * 60) % (h + 240)) - 120
    band = np.clip(1.0 - np.abs(np.arange(h, dtype=np.float32) - ly) / 90.0, 0.0, 1.0)
    _blend(img, rgb, a, np.repeat(band[:, None], w, axis=1))


def _rect_outline(w, h, x0, y0, rw, rh, width):
    def build(sw, sh):
        k = sw / w
        yy, xx = _coords(sw, sh)
        inside = (xx >= x0 * k) & (xx <= (x0 + rw) * k) & (yy >= y0 * k) & (yy <= (y0 + rh) * k)
        inner = ((xx >= (x0 + width) * k) & (xx <= (x0 + rw - width) * k)
                 & (yy >= (y0 + width) * k) & (yy <= (y0 + rh - width) * k))
        return (inside & ~inner).astype(np.float32)
    return _mask(w, h, build)


def _disc(w, h, cx, cy, r, glow=0.0):
    def build(sw, sh):
        k = sw / w
        yy, xx = _coords(sw, sh)
        d = np.hypot(xx - cx * k, yy - cy * k)
        m = (d <= r * k).astype(np.float32)
        if glow:
            m = np.maximum(m, np.clip(1.0 - (d - r * k) / (r * k + glow * k), 0.0, 1.0) * 0.55)
        return m
    return _mask(w, h, build)


def _paint_organic(img, w, h, t, theme, density, angle):
    # Canvas: `bg` at the centre → `wash` at the edge (the wash sits in the corners)
    img[:] = _c(theme, "bg")[0]
    _blend(img, _c(theme, "wash")[0], 1.0, 1.0 - _radial(w, h, w / 2, h / 2, max(w, h) * 0.78, falloff=1.0))
    _grid(img, t, density, angle, *_c(theme, "line"))
    _blend(img, *_c(theme, "matter"), mask=_blob(w, h, t))


def _blob(w: int, h: int, t: float) -> np.ndarray:
    """The corner blob of `organic`: a bezier-ish wedge whose top edge breathes with t."""
    off = math.sin(t * 0.8) * w * 0.06

    def build(sw, sh):
        k = sw / w
        yy, xx = _coords(sw, sh)
        top = -10 * k
        mid = (h * 0.30) * k + off * k
        # the wedge is bounded left by a cubic that bulges toward the frame centre
        u = np.clip((yy - top) / max(1e-6, mid - top), 0, 1)
        edge = (w * 0.72 - w * 0.08 * np.sin(u * math.pi)) * k
        return ((xx >= edge) & (yy <= mid)).astype(np.float32)
    return _mask(w, h, build)


def _paint_perspective(img, w, h, t, theme, density, angle):
    img[:] = _c(theme, "bg")[0]
    cx, cy, cam_y, f = w / 2.0, h / 2.0, h * 0.5, max(w, h) * 0.8
    nx, nz, z_near, z_far = 12, 20, 0.2, 50.0
    line_rgb, line_a = _c(theme, "line")
    accent, _ = _c(theme, "accent")
    off = (t * 2.5) % 1

    def build(sw, sh):
        k = sw / w
        yy, xx = _coords(sw, sh)
        mask = np.zeros((sh, sw), np.float32)
        for i in range(-nx, nx + 1):
            x3 = i * (w / nx)
            x1, y1 = (cx + (x3 * f) / (z_near * w)) * k, (cy + (cam_y * f) / (z_near * w)) * k
            x2, y2 = (cx + (x3 * f) / (z_far * w)) * k, (cy + (cam_y * f) / (z_far * w)) * k
            px, py = xx - x1, yy - y1
            vx, vy = x2 - x1, y2 - y1
            seg = np.clip((px * vx + py * vy) / max(1e-6, vx * vx + vy * vy), 0.0, 1.0)
            d = np.hypot(px - seg * vx, py - seg * vy)
            mask = np.maximum(mask, np.clip(1.0 - (d - 0.5), 0.0, 1.0))
        return mask

    _blend(img, line_rgb, line_a, _mask(w, h, build))
    rungs = np.zeros((h, w), np.float32)
    rows = np.arange(h, dtype=np.float32)
    for i in range(nz):
        u = (i + off) / nz
        z = 0.5 + (1 - u) ** 3 * (z_far - 0.5)
        y = cy + (cam_y * f) / (z * w)
        if y < -2 or y > h + 2:
            continue
        a = max(0.0, min(1.0, 1 - z / z_far)) * 0.42
        rungs = np.maximum(rungs, np.clip(1.0 - np.abs(rows - y), 0.0, 1.0)[:, None] * a)
    _blend(img, accent, 1.0, np.repeat(rungs, 1, axis=1))


def _paint_glyphs(img, w, h, t, theme, density, angle):
    """Falling glyphs — Arabic letters and digits, never the katakana of the source library."""
    from PIL import Image, ImageDraw  # noqa: PLC0415

    img[:] = _c(theme, "bg")[0]
    fs = max(12.0, density * (w / 600.0))
    col_w = fs * 1.5
    cols = int(math.ceil(w / col_w))
    font = _font(int(round(fs)))
    tr, tg, tb = (int(v) for v in _c(theme, "text")[0])
    ar, ag, ab = (int(v) for v in _c(theme, "accent")[0])
    base = Image.fromarray(img.astype(np.uint8), "RGB").convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(cols):
        x = i * col_w + col_w / 2
        offset = (i * 157.3) % h
        speed = 60 + (i % 5) * 30
        y_base = (t * speed + offset) % (h + fs * 15)
        for j in range(15):
            y = y_base - j * fs * 1.3
            if y < -fs or y > h + fs:
                continue
            ch = GLYPHS[int(hash01(int(i * 13 + j * 7 + math.floor(t * 3))) * len(GLYPHS))]
            if j == 0:
                draw.text((x, y), ch, font=font, fill=(tr, tg, tb, 255), anchor="ma")
            else:
                alpha = int(max(0.0, 1 - j / 15) * 0.75 * 255)
                draw.text((x, y), ch, font=font, fill=(ar, ag, ab, alpha), anchor="ma")
    img[:] = np.asarray(Image.alpha_composite(base, layer).convert("RGB"), np.float32)


GLYPHS = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي٠١٢٣٤٥٦٧٨٩"


@lru_cache(maxsize=4)
def _font(size: int):
    from PIL import ImageFont  # noqa: PLC0415

    for path in _font_candidates():
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _font_candidates():
    import glob
    import os

    root = os.environ.get("REEL_DIR") or os.getcwd()
    found = sorted(glob.glob(os.path.join(root, "assets", "fonts", "**", "Cairo*ExtraBold*.ttf"), recursive=True))
    found += sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets",
                                           "fonts", "**", "Cairo*ExtraBold*.ttf"), recursive=True))
    found.append("Cairo_800ExtraBold.ttf")
    return found


def _paint_pulse(img, w, h, t, theme, density, angle):
    img[:] = _c(theme, "bg")[0]
    gs = max(15.0, density * (w / 400.0))
    line_rgb, line_a = _c(theme, "line")

    def grid_mask(sw, sh):
        k = sw / w
        step = gs * k
        w_line = max(1.2, 1.0 * k)
        yy, xx = _coords(sw, sh)
        return (((xx % step) < w_line) | ((yy % step) < w_line)).astype(np.float32)

    _blend(img, line_rgb, line_a, _mask(w, h, grid_mask))
    cy, amp = h / 2.0, h * 0.18
    cycle = w * 1.5
    off = (t * 2 * 100) % cycle
    accent, _ = _c(theme, "accent")

    def wave_y(xs: np.ndarray) -> np.ndarray:
        q = (((xs + off) % cycle) + cycle) % cycle / cycle
        beat = np.where((q > 0.10) & (q < 0.20), np.sin((q - 0.10) / 0.10 * np.pi) * 0.15, 0.0)
        beat = np.where((q > 0.30) & (q < 0.35), -0.20, beat)
        beat = np.where((q >= 0.35) & (q < 0.40), 1.0, beat)
        beat = np.where((q >= 0.40) & (q < 0.45), -0.40, beat)
        beat = np.where((q > 0.60) & (q < 0.80), np.sin((q - 0.60) / 0.20 * np.pi) * 0.25, beat)
        return cy - (beat + np.sin(q * 200 + t * 10) * 0.015) * amp

    def wave_mask(sw, sh):
        k = sw / w
        yy, xx = _coords(sw, sh)
        y = wave_y(xx[0] / k) * k
        return np.clip(1.0 - np.abs(yy - y[None, :]), 0.0, 1.0)

    _blend(img, accent, 1.0, _mask(w, h, wave_mask))
    px = (t * 150) % w
    _blend(img, *_c(theme, "text"),
           mask=_disc(w, h, px, float(wave_y(np.array([px]))[0]), max(2.0, w * 0.008), glow=4.0))


def _paint_wash(img, w, h, t, theme, density, angle):
    img[:] = _c(theme, "bg")[0]
    rgb, a = _c(theme, "wash")
    _wash(img, rgb, a, w * 0.8, h * 0.2, w * 1.25)
    _wash(img, np.array(_rgb("ink"), np.float32), 0.18, w * 0.2, h * 0.8, w * 0.9)


PAINTERS = {
    "iso-grid": _paint_iso_grid,
    "grid-2d": _paint_grid_2d,
    "paper": _paint_paper,
    "aura": _paint_aura,
    "orbital": _paint_orbital,
    "orbit-mono": _paint_orbit_mono,
    "frames": _paint_frames,
    "organic": _paint_organic,
    "perspective": _paint_perspective,
    "glyphs": _paint_glyphs,
    "pulse": _paint_pulse,
    "wash": _paint_wash,
}


def resolve_spec(spec: dict | None = None) -> dict:
    """Unknown ids fall back to `wash`; unknown keys fall back to the catalog defaults."""
    spec = spec or {}
    bg = spec.get("id") if spec.get("id") in BACKGROUND_IDS else "wash"
    base = DEFAULT_PARAMS.get(bg, {})
    theme = "light" if spec.get("theme") == "light" else "dark"
    return {
        "id": bg,
        "theme": theme,
        "density": float(spec.get("density", base.get("density", DEFAULTS["density"]))),
        "angle": math.radians(float(spec.get("angle", base.get("angle", DEFAULTS["angle"])))),
        "speed": float(spec.get("speed", DEFAULTS["speed"])),
    }


def frame(bg: str = "wash", w: int = 1080, h: int = 1920, t: float = 0.0,
          theme: str = "dark", density: float | None = None, angle: float | None = None,
          speed: float | None = None) -> np.ndarray:
    """RGB uint8 frame for background `bg` at time `t` seconds. Same picture as engine K."""
    spec = {"id": bg, "theme": theme}
    if density is not None:
        spec["density"] = density
    if angle is not None:
        spec["angle"] = angle
    if speed is not None:
        spec["speed"] = speed
    r = resolve_spec(spec)
    img = np.zeros((h, w, 3), np.float32)
    PAINTERS[r["id"]](img, w, h, t * r["speed"], r["theme"], r["density"], r["angle"])
    return np.clip(img, 0, 255).astype(np.uint8)


def paint_into(dst: np.ndarray, bg: str = "wash", t: float = 0.0, theme: str = "dark", **params) -> np.ndarray:
    """Paint background `bg` straight into an existing RGB frame (in place) — the common case."""
    h, w = dst.shape[:2]
    dst[:] = frame(bg, w, h, t, theme, **params)
    return dst
