"""3D extruded icon/symbol/emblem tile for explainer scenes (engine P).

Mirrors `templates/render/lib/tile3d.js` (engines K & R) with exact numeric
parity on `sample_tile_pose(spec, t)` and OpenCV perspective-homography face
warping (`cv2.getPerspectiveTransform` + `cv2.warpPerspective`).

Intended for explaining tools, hardware, protocols, or user-supplied symbols —
never as an unrequested channel/studio watermark (AGENTS.md Rule 1).
Keyframes, idle float & specular gloss sweep adapted under MIT (see assets/CREDITS.md).
"""
from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw

from lib import BLACK, DRED, EMER, GRAY, INK, LGRAY, RED, TEAL, WHITE, YEL

# Locked palette v2.6 tokens (`gray_1` #D8D7D5, `gray_3` #BFBAB7)
GRAY_1 = (216, 215, 213)
GRAY_3 = (191, 186, 183)

TILE3D_ROLES: dict[str, dict[str, tuple[int, int, int]]] = {
    "paper": {"face": WHITE, "side": LGRAY, "side_dark": GRAY, "rim": YEL, "fg": INK},
    "dark": {"face": INK, "side": TEAL, "side_dark": BLACK, "rim": YEL, "fg": WHITE},
    "accent": {"face": RED, "side": DRED, "side_dark": INK, "rim": YEL, "fg": WHITE},
    "warm": {"face": YEL, "side": RED, "side_dark": DRED, "rim": EMER, "fg": INK},
    "soft": {"face": GRAY_1, "side": GRAY_3, "side_dark": TEAL, "rim": WHITE, "fg": INK},
}


def _clamp01(v: float) -> float:
    return min(1.0, max(0.0, float(v)))


def _ease(name: str, u: float) -> float:
    k = _clamp01(u)
    if name in ("linear", "lin"):
        return k
    if name == "inout":
        return 4.0 * k * k * k if k < 0.5 else 1.0 - ((-2.0 * k + 2.0) ** 3) / 2.0
    if name == "back":
        return 1.0 + 2.2 * ((k - 1.0) ** 3) + 1.2 * ((k - 1.0) ** 2)
    return 1.0 - ((1.0 - k) ** 3)


def _interp_key(keys: list[dict[str, Any]] | None, t: float, prop: str, fallback: float) -> float:
    if not keys:
        return float(fallback)

    def val(k: dict[str, Any]) -> float:
        return float(k[prop]) if prop in k and k[prop] is not None else float(fallback)

    if t <= float(keys[0]["t"]):
        return val(keys[0])
    for i in range(len(keys) - 1):
        a = keys[i]
        b = keys[i + 1]
        tb = float(b["t"])
        if t <= tb:
            ta = float(a["t"])
            u = _clamp01((t - ta) / max(1e-4, tb - ta))
            return val(a) + (val(b) - val(a)) * _ease(str(b.get("ease", "out")), u)
    return val(keys[-1])


def sample_tile_pose(spec: dict[str, Any] | None = None, t: float = 0.0) -> dict[str, float]:
    """Pure function of `t` matching `tile3d.js:sampleTilePose`."""
    s = spec or {}
    keys = s.get("keys")
    float_amp = float(s.get("float", 1.0))
    phase = float(s.get("phase", 0.0))
    size = float(s.get("size", 280.0))
    shine_period = max(0.25, float(s.get("shinePeriod", s.get("shine_period", 2.4))))
    shine_loop = math.fmod(math.fmod(t + phase * 0.7, shine_period) + shine_period, shine_period)

    base_x = _interp_key(keys, t, "x", float(s.get("x", 540.0)))
    base_y = _interp_key(keys, t, "y", float(s.get("y", 760.0)))
    base_z = _interp_key(keys, t, "z", float(s.get("z", 0.0)))
    default_scale = _interp_key(keys, t, "s", float(s.get("scale", 1.0)))
    scale = max(0.001, _interp_key(keys, t, "scale", default_scale))
    rx = _interp_key(keys, t, "rx", float(s.get("rx", -8.0))) + float_amp * 3.0 * math.sin(t * 1.1 + phase)
    ry = (
        _interp_key(keys, t, "ry", float(s.get("ry", 14.0)))
        + float_amp * 9.0 * math.sin(t * 0.9 + phase)
        + float(s.get("spin", 0.0)) * t * 360.0
    )
    rz = _interp_key(keys, t, "rz", float(s.get("rz", 0.0)))
    default_op = _interp_key(keys, t, "o", float(s.get("opacity", 1.0)))
    opacity = _clamp01(_interp_key(keys, t, "opacity", default_op))

    return {
        "x": base_x,
        "y": base_y - float_amp * size * 0.032 * math.sin(t * 1.6 + phase),
        "z": base_z,
        "size": size,
        "scale": scale,
        "rx": rx,
        "ry": ry,
        "rz": rz,
        "opacity": opacity,
        "shineCenter": -0.4 + (shine_loop / shine_period) * 1.8,
    }


def _rotate3(px: float, py: float, pz: float, rx_deg: float, ry_deg: float, rz_deg: float) -> tuple[float, float, float]:
    x, y, z = px, py, pz
    rx, ry, rz = math.radians(rx_deg), math.radians(ry_deg), math.radians(rz_deg)
    if rx:
        c, sn = math.cos(rx), math.sin(rx)
        y, z = y * c - z * sn, y * sn + z * c
    if ry:
        c, sn = math.cos(ry), math.sin(ry)
        x, z = x * c + z * sn, -x * sn + z * c
    if rz:
        c, sn = math.cos(rz), math.sin(rz)
        x, y = x * c - y * sn, x * sn + y * c
    return x, y, z


def _rounded_square_contour(half: float, radius: float, steps_per_corner: int = 6) -> list[tuple[float, float]]:
    r = min(half * 0.48, max(2.0, radius))
    inner = half - r
    corners = (
        (inner, -inner, -math.pi / 2, 0.0),
        (inner, inner, 0.0, math.pi / 2),
        (-inner, inner, math.pi / 2, math.pi),
        (-inner, -inner, math.pi, math.pi * 1.5),
    )
    pts: list[tuple[float, float]] = []
    for cx, cy, a0, a1 in corners:
        for i in range(steps_per_corner + 1):
            ang = a0 + ((a1 - a0) * i) / steps_per_corner
            pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
    return pts


def _mix_rgb(a: tuple[int, int, int], b: tuple[int, int, int], u: float) -> tuple[int, int, int]:
    t = _clamp01(u)
    return (
        int(round(a[0] + (b[0] - a[0]) * t)),
        int(round(a[1] + (b[1] - a[1]) * t)),
        int(round(a[2] + (b[2] - a[2]) * t)),
    )


def _fill_poly_aa(fr: np.ndarray, pts: list[tuple[float, float]], color: tuple[int, int, int], alpha: float) -> None:
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
    roi[:] = roi * (1.0 - m) + np.array(color, dtype=np.float32) * m


def _build_face_texture(
    tex_size: int,
    radius_ratio: float,
    role: dict[str, tuple[int, int, int]],
    shine_center: float,
    shine_alpha: float,
    icon_sprite: np.ndarray | None,
    symbol_scale: float,
) -> np.ndarray:
    """Build a straight-RGBA (tex_size, tex_size, 4) float32 front tile texture with specular gloss."""
    im = Image.new("RGBA", (tex_size, tex_size), (0, 0, 0, 0))
    rad = int(round(tex_size * min(0.48, max(0.02, radius_ratio))))
    mask_im = Image.new("L", (tex_size, tex_size), 0)
    ImageDraw.Draw(mask_im).rounded_rectangle([0, 0, tex_size - 1, tex_size - 1], radius=rad, fill=255)
    base = Image.new("RGBA", (tex_size, tex_size), role["face"] + (255,))
    im.paste(base, (0, 0), mask_im)
    arr = np.array(im, dtype=np.float32)

    # Composite optional icon_sprite (premultiplied RGBA float32 from `lib` or `icons`)
    if icon_sprite is not None and icon_sprite.ndim == 3 and icon_sprite.shape[2] == 4:
        sh, sw = icon_sprite.shape[:2]
        target = max(8, int(round(tex_size * symbol_scale)))
        aspect = sw / max(1.0, float(sh))
        nw = target if aspect >= 1.0 else max(1, int(round(target * aspect)))
        nh = max(1, int(round(target / aspect))) if aspect >= 1.0 else target
        resized = cv2.resize(icon_sprite.astype(np.float32), (nw, nh), interpolation=cv2.INTER_AREA)
        ox = (tex_size - nw) // 2
        oy = (tex_size - nh) // 2
        sa = np.clip(resized[..., 3:4] / 255.0, 0.0, 1.0)
        roi = arr[oy:oy + nh, ox:ox + nw]
        # `icon_sprite` is premultiplied RGB; blend onto opaque face RGB while preserving tile alpha mask
        roi[..., :3] = np.clip(resized[..., :3] + roi[..., :3] * (1.0 - sa), 0.0, 255.0)

    # Top soft studio sheen + diagonal specular gloss sweep inside rounded mask
    yy, xx = np.mgrid[0:tex_size, 0:tex_size].astype(np.float32) / float(tex_size)
    inside = (arr[..., 3:4] > 0).astype(np.float32)
    top_sheen = np.clip(1.0 - yy / 0.55, 0.0, 1.0)[..., None] * 0.14
    diag_proj = (xx + yy) * 0.5
    band = np.clip(1.0 - np.abs(diag_proj - shine_center * 0.65) / 0.18, 0.0, 1.0)[..., None] * float(shine_alpha)
    gleam = np.clip(top_sheen + band, 0.0, 0.65) * inside
    paper_vec = np.array(WHITE, dtype=np.float32)
    arr[..., :3] = arr[..., :3] * (1.0 - gleam) + paper_vec * gleam

    # Rim stroke
    rim_im = Image.new("RGBA", (tex_size, tex_size), (0, 0, 0, 0))
    ImageDraw.Draw(rim_im).rounded_rectangle(
        [2, 2, tex_size - 3, tex_size - 3],
        radius=max(2, rad - 2),
        outline=role["rim"] + (190,),
        width=max(2, tex_size // 96),
    )
    rim_arr = np.array(rim_im, dtype=np.float32)
    ra = rim_arr[..., 3:4] / 255.0
    arr[..., :3] = arr[..., :3] * (1.0 - ra) + rim_arr[..., :3] * ra
    return arr


def draw_tile3d(
    fr: np.ndarray,
    t: float,
    spec: dict[str, Any] | None = None,
    *,
    icon_sprite: np.ndarray | None = None,
) -> dict[str, float]:
    """Render a 3D beveled explainer tile onto an engine-P frame `fr` at time `t`."""
    s = spec or {}
    pose = sample_tile_pose(s, t)
    if pose["opacity"] <= 0.003:
        return pose

    role = TILE3D_ROLES.get(str(s.get("role", "paper")), TILE3D_ROLES["paper"])
    full_size = pose["size"] * pose["scale"]
    half = full_size / 2.0
    radius_ratio = float(s.get("radiusRatio", s.get("radius_ratio", 0.22)))
    depth = full_size * float(s.get("depthRatio", s.get("depth_ratio", 0.18)))
    cam_dist = max(full_size * 3.2, float(s.get("cameraDist", s.get("camera_dist", 1100.0))))
    shine_alpha = float(s.get("shine", 0.22))
    symbol_scale = float(s.get("symbolScale", s.get("symbol_scale", 0.58)))

    def proj(lx: float, ly: float, lz: float) -> tuple[float, float, float]:
        wx, wy, wz = _rotate3(lx, ly, lz, pose["rx"], pose["ry"], pose["rz"])
        denom = max(120.0, cam_dist - wz - pose["z"])
        k = cam_dist / denom
        return pose["x"] + wx * k, pose["y"] + wy * k, wz

    contour = _rounded_square_contour(half, full_size * radius_ratio, 6)
    front_pts = [proj(px, py, depth / 2.0) for px, py in contour]
    back_pts = [proj(px, py, -depth / 2.0) for px, py in contour]

    # 1. Soft perspective drop shadow
    if s.get("shadow", True) is not False:
        sh_x = -pose["ry"] * 0.45
        sh_y = full_size * 0.09 + pose["rx"] * 0.35
        sh_poly = [(bx + sh_x, by + sh_y) for bx, by, _ in back_pts]
        _fill_poly_aa(fr, sh_poly, BLACK, pose["opacity"] * float(s.get("shadowOpacity", 0.26)))

    # 2. Painter-sorted extruded side quads with directional + salmon rim shading
    quads = []
    n_pts = len(contour)
    for i in range(n_pts):
        j = (i + 1) % n_pts
        f0, f1 = front_pts[i], front_pts[j]
        b0, b1 = back_pts[i], back_pts[j]
        mx = (contour[i][0] + contour[j][0]) * 0.5
        my = (contour[i][1] + contour[j][1]) * 0.5
        n_len = math.hypot(mx, my) or 1.0
        nx, ny, nz = _rotate3(mx / n_len, my / n_len, 0.0, pose["rx"], pose["ry"], pose["rz"])
        key_dot = _clamp01(nx * 0.42 - ny * 0.58 + nz * 0.69)
        rim_dot = _clamp01(-nx * 0.65 - ny * 0.35 + (1.0 - abs(nz)) * 0.45) ** 2.2
        base_col = _mix_rgb(role["side_dark"], role["side"], key_dot)
        shaded = _mix_rgb(base_col, role["rim"], rim_dot * 0.65) if rim_dot > 0.15 else base_col
        avg_z = (f0[2] + f1[2] + b0[2] + b1[2]) * 0.25
        quads.append((avg_z, [(b0[0], b0[1]), (b1[0], b1[1]), (f1[0], f1[1]), (f0[0], f0[1])], shaded))

    quads.sort(key=lambda item: item[0])
    for _z, q_pts, col in quads:
        _fill_poly_aa(fr, q_pts, col, pose["opacity"])

    # 3. Perspective-homography warped front (or back) cap
    _fnx, _fny, fnz = _rotate3(0.0, 0.0, 1.0, pose["rx"], pose["ry"], pose["rz"])
    showing_front = fnz >= 0.0
    cap_z = depth / 2.0 if showing_front else -depth / 2.0
    dst_corners = np.array(
        [
            proj(-half, -half, cap_z)[:2],
            proj(half, -half, cap_z)[:2],
            proj(half, half, cap_z)[:2],
            proj(-half, half, cap_z)[:2],
        ],
        dtype=np.float32,
    )
    tex_size = 384
    tex = _build_face_texture(
        tex_size,
        radius_ratio,
        role,
        pose["shineCenter"],
        shine_alpha if showing_front else 0.0,
        icon_sprite if showing_front else None,
        symbol_scale,
    )
    src_corners = np.array(
        [[0, 0], [tex_size - 1, 0], [tex_size - 1, tex_size - 1], [0, tex_size - 1]],
        dtype=np.float32,
    )
    x0 = max(0, int(math.floor(float(dst_corners[:, 0].min()))) - 3)
    y0 = max(0, int(math.floor(float(dst_corners[:, 1].min()))) - 3)
    x1 = min(fr.shape[1], int(math.ceil(float(dst_corners[:, 0].max()))) + 4)
    y1 = min(fr.shape[0], int(math.ceil(float(dst_corners[:, 1].max()))) + 4)
    if x1 > x0 and y1 > y0:
        shifted_dst = dst_corners - np.array([[x0, y0]], dtype=np.float32)
        homography = cv2.getPerspectiveTransform(src_corners, shifted_dst)
        warped = cv2.warpPerspective(
            tex,
            homography,
            (x1 - x0, y1 - y0),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0),
        )
        a = (warped[..., 3:4] / 255.0) * pose["opacity"]
        roi = fr[y0:y1, x0:x1]
        roi[:] = np.clip(roi * (1.0 - a) + warped[..., :3] * a, 0.0, 255.0)

    return pose
