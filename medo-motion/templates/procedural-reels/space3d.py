"""3D for engine P — meshes, a pinhole camera, painter's-algorithm faces, flat shading.

Identical maths to engine K (`templates/render/lib/space3d.js`). This is not a 3D engine: it is just
enough projection to make a card, a device, a stack of tiles or a bar chart sit in real space, so a
scene can turn instead of cut. Everything is a pure function of the mesh and the camera, so it stays
frame-deterministic.

    from space3d import box, camera, project, draw_mesh
    mesh = box(220, mesh_center=(0, 0, 0))
    cam = camera(dist=900, yaw=0.6, pitch=-0.15)
    draw_mesh(draw, mesh, cam, W, H, ink=(10, 10, 10), accent=(203, 39, 27))

Coordinates: +x right, +y up, +z towards the viewer (screen space is y-down, handled in `project`).
"""
from __future__ import annotations

import math

# ------------------------------------------------------------------ small vector helpers
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    m = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / m, a[1] / m, a[2] / m)


def rotate(p: tuple, rx: float = 0.0, ry: float = 0.0, rz: float = 0.0) -> tuple:
    """Rotate a point around x, then y, then z (radians)."""
    x, y, z = p
    if rx:
        c, s = math.cos(rx), math.sin(rx)
        y, z = y * c - z * s, y * s + z * c
    if ry:
        c, s = math.cos(ry), math.sin(ry)
        x, z = x * c + z * s, -x * s + z * c
    if rz:
        c, s = math.cos(rz), math.sin(rz)
        x, y = x * c - y * s, x * s + y * c
    return (x, y, z)


# ------------------------------------------------------------------ meshes
def mesh(verts, faces) -> dict:
    """`verts` = [(x, y, z)], `faces` = [(indices, role)] — `role` picks a colour when drawing."""
    return {"verts": [tuple(map(float, v)) for v in verts],
            "faces": [(tuple(int(i) for i in f), role) for f, role in faces]}


def box(w: float, h: float = None, d: float = None, center=(0.0, 0.0, 0.0),
        roles=("front", "left", "top", "right", "bottom", "back")) -> dict:
    """An axis-aligned box. `w, h, d` are full sizes; `roles` names the six faces."""
    h = w if h is None else h
    d = w if d is None else d
    x, y, z = center
    hw, hh, hd = w / 2, h / 2, d / 2
    verts = [(x - hw, y - hh, z + hd), (x + hw, y - hh, z + hd), (x + hw, y + hh, z + hd),
             (x - hw, y + hh, z + hd), (x - hw, y - hh, z - hd), (x + hw, y - hh, z - hd),
             (x + hw, y + hh, z - hd), (x - hw, y + hh, z - hd)]
    faces = [((0, 1, 2, 3), roles[0]), ((4, 5, 1, 0), roles[4]), ((3, 2, 6, 7), roles[2]),
             ((1, 5, 6, 2), roles[3]), ((0, 4, 7, 3), roles[1]), ((5, 4, 7, 6), roles[5])]
    return mesh(verts, faces)


def prism(poly2d, depth: float, center=(0.0, 0.0, 0.0), role_cap="front", role_side="side") -> dict:
    """Extrude a 2D polygon ([(x, y)]) along z into a closed solid (2 caps + one quad per edge)."""
    x, y, z = center
    hd = depth / 2
    n = len(poly2d)
    verts = [(px + x, py + y, hd + z) for px, py in poly2d]
    verts += [(px + x, py + y, -hd + z) for px, py in poly2d]
    faces = [(tuple(range(n)), role_cap), (tuple(range(2 * n - 1, n - 1, -1)), role_cap)]
    for i in range(n):
        j = (i + 1) % n
        faces.append(((i, j, n + j, n + i), role_side))
    return mesh(verts, faces)


def transform(m: dict, rx: float = 0.0, ry: float = 0.0, rz: float = 0.0,
              move=(0.0, 0.0, 0.0), scale: float = 1.0) -> dict:
    """Scale → rotate → translate a whole mesh (returns a new mesh)."""
    verts = []
    for v in m["verts"]:
        s = (v[0] * scale, v[1] * scale, v[2] * scale)
        r = rotate(s, rx, ry, rz)
        verts.append((r[0] + move[0], r[1] + move[1], r[2] + move[2]))
    return {"verts": verts, "faces": m["faces"]}


# ------------------------------------------------------------------ camera & projection
def camera(dist: float = 900.0, yaw: float = 0.0, pitch: float = 0.0, fov: float = 38.0,
           target=(0.0, 0.0, 0.0)) -> dict:
    """A pinhole camera orbiting `target`: `yaw`/`pitch` in radians, `dist` in world units."""
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    # camera position on a sphere around the target
    px = target[0] + dist * cp * sy
    py = target[1] + dist * sp
    pz = target[2] + dist * cp * cy
    forward = _norm(_sub(target, (px, py, pz)))
    right = _norm(_cross(forward, (0.0, 1.0, 0.0)))
    up = _cross(right, forward)
    return {"pos": (px, py, pz), "fwd": forward, "right": right, "up": up,
            "fov": math.radians(fov), "target": target}


def project(points, cam: dict, w: float, h: float) -> list[tuple[float, float, float, float]]:
    """[(screen_x, screen_y, depth, scale)] — depth is view-space z (larger = farther)."""
    f = (h / 2.0) / math.tan(cam["fov"] / 2.0)
    out = []
    for p in points:
        rel = _sub(p, cam["pos"])
        z = _dot(rel, cam["fwd"])
        if z <= 1e-6:                       # behind the camera: park it far away, drawing skips it
            out.append((0.0, 0.0, float("inf"), 0.0))
            continue
        k = f / z
        sx = w / 2.0 + _dot(rel, cam["right"]) * k
        sy = h / 2.0 - _dot(rel, cam["up"]) * k
        out.append((round(sx, 4), round(sy, 4), round(z, 4), round(k, 6)))
    return out


def face_normal(m: dict, face) -> tuple:
    idx, _role = face
    a, b, c = m["verts"][idx[0]], m["verts"][idx[1]], m["verts"][idx[2]]
    return _norm(_cross(_sub(b, a), _sub(c, a)))


def sorted_faces(m: dict, cam: dict) -> list:
    """Faces ordered far → near (painter's algorithm) with their view depth."""
    out = []
    for face in m["faces"]:
        idx, role = face
        centre = [sum(m["verts"][i][k] for i in idx) / len(idx) for k in range(3)]
        z = _dot(_sub(tuple(centre), cam["pos"]), cam["fwd"])
        out.append((z, role, idx))
    return sorted(out, key=lambda r: -r[0])


def to_rgb(color) -> tuple:
    """'#CB271B' | (r, g, b) → (r, g, b) — brand tokens are hex, meshes want numbers."""
    if isinstance(color, (tuple, list)):
        return tuple(int(c) for c in color[:3])
    h = str(color).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"not a colour: {color}")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def shade(color, normal, light=(0.35, 0.75, 0.55), ambient: float = 0.45) -> tuple:
    """Flat shading: ambient + diffuse, clamped so a face never goes black or blows out."""
    color = to_rgb(color)
    ln = _norm(light)
    k = ambient + (1 - ambient) * max(0.0, _dot(normal, ln))
    return tuple(max(0, min(255, int(c * k))) for c in color[:3])


def draw_mesh(draw, m: dict, cam: dict, w: int, h: int, colors: dict, light=(0.35, 0.75, 0.55),
              ambient: float = 0.45, cull: bool = True, outline=None) -> int:
    """Paint a mesh with flat shading; returns how many faces were drawn.

    `colors` maps a face role ("front", "side", …) to an RGB tuple. `cull` skips faces pointing away
    from the camera, which is right for closed solids and wrong for open ribbons.
    """
    projected = project(m["verts"], cam, w, h)
    drawn = 0
    for _z, role, idx in sorted_faces(m, cam):
        pts = [projected[i] for i in idx]
        if any(p[3] == 0 for p in pts):
            continue
        n = face_normal(m, (idx, role))
        if cull and _dot(n, _sub(cam["pos"], _face_centre(m, idx))) <= 0:
            continue                      # the face points away from the camera
        col = shade(colors.get(role, colors.get("side", (10, 10, 10))), n, light, ambient)
        draw.polygon([(p[0], p[1]) for p in pts], fill=col, outline=outline)
        drawn += 1
    return drawn


def _face_centre(m: dict, idx) -> tuple:
    return tuple(sum(m["verts"][i][k] for i in idx) / len(idx) for k in range(3))
