"""Isometric cutaway "How it works" diagram kit for engine P.

Mirrors `templates/render/lib/iso-kit.js` (engines K & R) using locked Medo
brand tokens only. Supports 3-layer cutaway ordering (`back`, `mid`, `front`),
progressive ink-stroke reveal (`reveal=0..1`), and animated signal/heat pulses
along wires (`flow_p=0..1`). See assets/CREDITS.md for MIT attribution.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

from lib import BLACK, DRED, EMER, GRAY, INK, LGRAY, RED, TEAL, WHITE, YEL

COS30 = 0.8660254037844386
SIN30 = 0.5
LAYER_RANK = {"back": 0, "mid": 1, "front": 2}

# Locked palette v2.6 tokens from brand/brand.json (`gray_1` #D8D7D5, `gray_3` #BFBAB7)
GRAY_1 = (216, 215, 213)
GRAY_3 = (191, 186, 183)

ROLE_THEMES = {
    "dark": {
        "housing": {"top": TEAL, "left": INK, "right": BLACK, "stroke": GRAY},
        "paper": {"top": WHITE, "left": GRAY_1, "right": GRAY_3, "stroke": INK},
        "chip": {"top": GRAY, "left": TEAL, "right": INK, "stroke": WHITE},
        "accent": {"top": YEL, "left": RED, "right": DRED, "stroke": WHITE},
        "warm": {"top": EMER, "left": YEL, "right": RED, "stroke": WHITE},
    },
    "light": {
        "housing": {"top": WHITE, "left": GRAY_1, "right": GRAY_3, "stroke": INK},
        "paper": {"top": WHITE, "left": GRAY_1, "right": LGRAY, "stroke": INK},
        "chip": {"top": TEAL, "left": INK, "right": BLACK, "stroke": INK},
        "accent": {"top": YEL, "left": RED, "right": DRED, "stroke": INK},
        "warm": {"top": EMER, "left": YEL, "right": RED, "stroke": INK},
    },
}


def _clamp01(v: float) -> float:
    return min(1.0, max(0.0, float(v)))


def iso_project(
    x: float,
    y: float,
    z: float,
    *,
    origin_x: float = 540.0,
    origin_y: float = 820.0,
    scale: float = 1.0,
) -> tuple[float, float, float]:
    """Project 3D isometric `(x, y, z)` to `(screen_x, screen_y, painter_depth)`."""
    sx = origin_x + (x - y) * COS30 * scale
    sy = origin_y + (x + y) * SIN30 * scale - z * scale
    return sx, sy, x + y + z


def _polyline_length(pts: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        for i in range(1, len(pts))
    )


def _point_at_polyline(pts: list[tuple[float, float]], p: float) -> tuple[float, float]:
    if not pts:
        return 0.0, 0.0
    if len(pts) == 1:
        return pts[0]
    target = _polyline_length(pts) * _clamp01(p)
    for i in range(1, len(pts)):
        ax, ay = pts[i - 1]
        bx, by = pts[i]
        seg = math.hypot(bx - ax, by - ay)
        if target <= seg or i == len(pts) - 1:
            f = _clamp01(target / seg) if seg > 1e-6 else 0.0
            return ax + (bx - ax) * f, ay + (by - ay) * f
        target -= seg
    return pts[-1]


def _blend_overlay(fr: np.ndarray, overlay: np.ndarray, mask: np.ndarray, alpha: float) -> None:
    if alpha <= 0.004:
        return
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    m = (mask[y0:y1, x0:x1].astype(np.float32) / 255.0)[..., None] * float(alpha)
    roi = fr[y0:y1, x0:x1]
    roi[:] = roi * (1.0 - m) + overlay[y0:y1, x0:x1] * m


def _fill_poly(fr: np.ndarray, pts: list[tuple[float, float]], color: tuple[int, int, int], alpha: float) -> None:
    if alpha <= 0.004 or len(pts) < 3:
        return
    arr = np.round(np.array(pts, dtype=np.float32)).astype(np.int32)
    x0 = max(0, int(arr[:, 0].min()) - 2)
    y0 = max(0, int(arr[:, 1].min()) - 2)
    x1 = min(fr.shape[1], int(arr[:, 0].max()) + 3)
    y1 = min(fr.shape[0], int(arr[:, 1].max()) + 3)
    if x1 <= x0 or y1 <= y0:
        return
    mask = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
    shifted = arr - np.array([[x0, y0]], dtype=np.int32)
    cv2.fillPoly(mask, [shifted], 255, lineType=cv2.LINE_AA)
    m = (mask.astype(np.float32) / 255.0)[..., None] * float(alpha)
    roi = fr[y0:y1, x0:x1]
    col = np.array(color, dtype=np.float32)
    roi[:] = roi * (1.0 - m) + col * m


def _stroke_partial(
    fr: np.ndarray,
    pts: list[tuple[float, float]],
    color: tuple[int, int, int],
    width: float,
    progress: float,
    alpha: float,
    close: bool = False,
) -> None:
    p = _clamp01(progress)
    if p <= 0.002 or alpha <= 0.004 or len(pts) < 2:
        return
    closed = [*pts, pts[0]] if (close and len(pts) > 2) else list(pts)
    budget = _polyline_length(closed) * p
    sub: list[tuple[float, float]] = [closed[0]]
    for i in range(1, len(closed)):
        if budget <= 0:
            break
        ax, ay = closed[i - 1]
        bx, by = closed[i]
        seg = math.hypot(bx - ax, by - ay)
        if seg <= 1e-6:
            continue
        if budget >= seg:
            sub.append((bx, by))
            budget -= seg
        else:
            f = budget / seg
            sub.append((ax + (bx - ax) * f, ay + (by - ay) * f))
            budget = 0.0
    if len(sub) < 2:
        return
    arr = np.round(np.array(sub, dtype=np.float32)).astype(np.int32)
    pad = max(4, int(math.ceil(width)) + 3)
    x0 = max(0, int(arr[:, 0].min()) - pad)
    y0 = max(0, int(arr[:, 1].min()) - pad)
    x1 = min(fr.shape[1], int(arr[:, 0].max()) + pad + 1)
    y1 = min(fr.shape[0], int(arr[:, 1].max()) + pad + 1)
    if x1 <= x0 or y1 <= y0:
        return
    mask = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
    shifted = arr - np.array([[x0, y0]], dtype=np.int32)
    cv2.polylines(mask, [shifted], False, 255, max(1, int(round(width))), lineType=cv2.LINE_AA)
    m = (mask.astype(np.float32) / 255.0)[..., None] * float(alpha)
    roi = fr[y0:y1, x0:x1]
    col = np.array(color, dtype=np.float32)
    roi[:] = roi * (1.0 - m) + col * m


class IsoScene:
    """Deterministic 3-layer isometric cutaway diagram collector for engine P."""

    def __init__(
        self,
        *,
        origin_x: float = 540.0,
        origin_y: float = 820.0,
        scale: float = 1.0,
        theme: str = "dark",
        line_width: float = 3.0,
    ) -> None:
        self.origin_x = float(origin_x)
        self.origin_y = float(origin_y)
        self.scale = float(scale)
        self.theme = "light" if theme == "light" else "dark"
        self.line_width = float(line_width)
        self._palette = ROLE_THEMES[self.theme]
        self._ops: list[tuple[int, float, int, object]] = []

    def project(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        return iso_project(x, y, z, origin_x=self.origin_x, origin_y=self.origin_y, scale=self.scale)

    def _xy(self, x: float, y: float, z: float) -> tuple[float, float]:
        sx, sy, _ = self.project(x, y, z)
        return sx, sy

    def _role(self, role: str) -> dict[str, tuple[int, int, int]]:
        return self._palette.get(role, self._palette["housing"])

    def _push(self, layer: str, depth: float, fn) -> None:
        self._ops.append((LAYER_RANK.get(layer, 1), float(depth), len(self._ops), fn))

    def slab(
        self,
        *,
        x: float = 0,
        y: float = 0,
        z: float = 0,
        dx: float = 120,
        dy: float = 90,
        dz: float = 28,
        role: str = "housing",
        layer: str = "mid",
        reveal: float = 1.0,
        alpha: float = 1.0,
    ) -> IsoScene:
        r = _clamp01(reveal)
        if r <= 0 or alpha <= 0:
            return self
        c = self._role(role)
        p100 = self._xy(x + dx, y, z)
        p010 = self._xy(x, y + dy, z)
        p110 = self._xy(x + dx, y + dy, z)
        p001 = self._xy(x, y, z + dz)
        p101 = self._xy(x + dx, y, z + dz)
        p011 = self._xy(x, y + dy, z + dz)
        p111 = self._xy(x + dx, y + dy, z + dz)
        fill_a = float(alpha) * _clamp01((r - 0.25) / 0.75)
        depth = x + dx * 0.5 + y + dy * 0.5 + z + dz * 0.5

        def _draw(fr: np.ndarray) -> None:
            left_f = [p010, p110, p111, p011]
            right_f = [p100, p110, p111, p101]
            top_f = [p001, p101, p111, p011]
            _fill_poly(fr, left_f, c["left"], fill_a)
            _fill_poly(fr, right_f, c["right"], fill_a)
            _fill_poly(fr, top_f, c["top"], fill_a)
            _stroke_partial(fr, left_f, c["stroke"], self.line_width, r, alpha, True)
            _stroke_partial(fr, right_f, c["stroke"], self.line_width, r, alpha, True)
            _stroke_partial(fr, top_f, c["stroke"], self.line_width, r, alpha, True)

        self._push(layer, depth, _draw)
        return self

    def cylinder(
        self,
        *,
        x: float = 0,
        y: float = 0,
        z: float = 0,
        r: float = 36,
        h: float = 48,
        segments: int = 24,
        role: str = "chip",
        layer: str = "mid",
        reveal: float = 1.0,
        alpha: float = 1.0,
    ) -> IsoScene:
        rev = _clamp01(reveal)
        if rev <= 0 or alpha <= 0:
            return self
        c = self._role(role)
        top_pts = []
        bot_pts = []
        for i in range(segments):
            ang = (i / segments) * math.tau
            px = x + math.cos(ang) * r
            py = y + math.sin(ang) * r
            top_pts.append(self._xy(px, py, z + h))
            bot_pts.append(self._xy(px, py, z))
        min_i = min(range(segments), key=lambda idx: top_pts[idx][0])
        max_i = max(range(segments), key=lambda idx: top_pts[idx][0])
        front_arc = []
        cur = min_i
        while len(front_arc) <= segments:
            front_arc.append(bot_pts[cur])
            if cur == max_i:
                break
            cur = (cur + 1) % segments
        side_poly = [top_pts[min_i], *front_arc, top_pts[max_i]]
        fill_a = float(alpha) * _clamp01((rev - 0.25) / 0.75)

        def _draw(fr: np.ndarray) -> None:
            _fill_poly(fr, side_poly, c["left"], fill_a)
            _fill_poly(fr, top_pts, c["top"], fill_a)
            _stroke_partial(fr, side_poly, c["stroke"], self.line_width, rev, alpha, False)
            _stroke_partial(fr, top_pts, c["stroke"], self.line_width, rev, alpha, True)

        self._push(layer, x + y + z + h * 0.5, _draw)
        return self

    def ring(
        self,
        *,
        x: float = 0,
        y: float = 0,
        z: float = 0,
        r_outer: float = 64,
        r_inner: float = 24,
        h: float = 16,
        blades: int = 0,
        spin_deg: float = 0.0,
        role: str = "housing",
        layer: str = "mid",
        reveal: float = 1.0,
        alpha: float = 1.0,
    ) -> IsoScene:
        self.cylinder(x=x, y=y, z=z, r=r_outer, h=h, role=role, layer=layer, reveal=reveal, alpha=alpha)
        self.cylinder(x=x, y=y, z=z + 1, r=r_inner, h=h, role="accent", layer=layer, reveal=reveal, alpha=alpha)
        if blades > 0 and reveal > 0.2:
            c = self._role("warm")
            spin = math.radians(spin_deg)

            def _draw(fr: np.ndarray) -> None:
                for b in range(blades):
                    ang = spin + (b / blades) * math.tau
                    p0 = self._xy(x + math.cos(ang) * r_inner, y + math.sin(ang) * r_inner, z + h)
                    p1 = self._xy(
                        x + math.cos(ang + 0.25) * (r_outer * 0.9),
                        y + math.sin(ang + 0.25) * (r_outer * 0.9),
                        z + h,
                    )
                    _stroke_partial(fr, [p0, p1], c["stroke"], self.line_width * 1.1, 1.0, alpha * _clamp01(reveal))

            self._push(layer, x + y + z + h + 0.5, _draw)
        return self

    def coil(
        self,
        *,
        x: float = 0,
        y: float = 0,
        z: float = 0,
        length: float = 140,
        radius: float = 16,
        turns: int = 6,
        axis: str = "x",
        role: str = "warm",
        layer: str = "mid",
        reveal: float = 1.0,
        alpha: float = 1.0,
    ) -> IsoScene:
        steps = max(24, turns * 12)
        pts = []
        for i in range(steps + 1):
            u = i / steps
            ang = u * turns * math.tau
            along = u * length
            c1 = math.cos(ang) * radius
            c2 = math.sin(ang) * radius
            px = x + along if axis == "x" else x + c1
            py = y + along if axis == "y" else (y + c1 if axis == "x" else y + c2)
            pz = z + along if axis == "z" else z + c2
            pts.append(self._xy(px, py, pz))
        c = self._role(role)

        def _draw(fr: np.ndarray) -> None:
            _stroke_partial(fr, pts, c["top"], self.line_width * 1.35, reveal, alpha, False)

        self._push(layer, x + y + z + length * 0.5, _draw)
        return self

    def wire(
        self,
        *,
        points: list[tuple[float, float, float]],
        role: str = "accent",
        layer: str = "mid",
        width: float = 4.0,
        reveal: float = 1.0,
        flow_p: float = -1.0,
        alpha: float = 1.0,
    ) -> IsoScene:
        if len(points) < 2:
            return self
        pts = [self._xy(px, py, pz) for px, py, pz in points]
        avg_d = sum(px + py + pz for px, py, pz in points) / len(points)
        c = self._role(role)

        def _draw(fr: np.ndarray) -> None:
            _stroke_partial(fr, pts, c["top"], width, reveal, alpha, False)
            if 0.0 <= flow_p <= 1.0 and reveal > 0.2:
                px, py = _point_at_polyline(pts, flow_p)
                rad = max(3, int(round(width * 1.45)))
                x0, y0 = max(0, int(px) - rad - 2), max(0, int(py) - rad - 2)
                x1, y1 = min(fr.shape[1], int(px) + rad + 3), min(fr.shape[0], int(py) + rad + 3)
                if x1 > x0 and y1 > y0:
                    mask = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
                    cv2.circle(mask, (int(round(px)) - x0, int(round(py)) - y0), rad, 255, -1, lineType=cv2.LINE_AA)
                    overlay = np.empty((y1 - y0, x1 - x0, 3), dtype=np.float32)
                    overlay[:] = WHITE
                    _blend_overlay(fr, overlay, mask, alpha)

        self._push(layer, avg_d, _draw)
        return self

    def render(self, fr: np.ndarray) -> int:
        sorted_ops = sorted(self._ops, key=lambda item: (item[0], item[1], item[2]))
        for _layer, _depth, _seq, fn in sorted_ops:
            fn(fr)
        return len(sorted_ops)
