// 3D for engine K — meshes, a pinhole camera, painter's-algorithm faces, flat shading.
//
// Identical maths to engine P (`presenter`'s sibling `space3d.py`), so a mesh built once sits in the
// same place in both engines. Not a 3D engine: just enough projection to make a card, a device, a
// stack of tiles or a bar chart sit in real space, so a scene turns instead of cutting.
//
//   import { box, camera, drawMesh } from './space3d.js';
//   const cam = camera({ dist: 900, yaw: 0.6, pitch: -0.15 });
//   drawMesh(ctx, box(220, 260, 220), cam, W, H, { front: C.red, side: C.ink });
//
// Coordinates: +x right, +y up, +z towards the viewer (screen y is flipped inside project()).

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const cross = (a, b) => [
  a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0],
];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const norm = (a) => { const m = Math.hypot(...a) || 1; return [a[0] / m, a[1] / m, a[2] / m]; };

/** Rotate a point around x, then y, then z (radians). */
export function rotate(p, rx = 0, ry = 0, rz = 0) {
  let [x, y, z] = p;
  if (rx) { const c = Math.cos(rx), s = Math.sin(rx); [y, z] = [y * c - z * s, y * s + z * c]; }
  if (ry) { const c = Math.cos(ry), s = Math.sin(ry); [x, z] = [x * c + z * s, -x * s + z * c]; }
  if (rz) { const c = Math.cos(rz), s = Math.sin(rz); [x, y] = [x * c - y * s, x * s + y * c]; }
  return [x, y, z];
}

/** `verts` = [[x,y,z]], `faces` = [[indices, role]] — `role` picks the colour when drawing. */
export const mesh = (verts, faces) => ({
  verts: verts.map((v) => v.map(Number)),
  faces: faces.map(([f, role]) => [f.map(Number), role]),
});

/** An axis-aligned box (`w, h, d` = full sizes); `roles` names the six faces. */
export function box(w, h = w, d = w, center = [0, 0, 0],
  roles = ['front', 'left', 'top', 'right', 'bottom', 'back']) {
  const [x, y, z] = center;
  const hw = w / 2, hh = h / 2, hd = d / 2;
  const verts = [
    [x - hw, y - hh, z + hd], [x + hw, y - hh, z + hd], [x + hw, y + hh, z + hd], [x - hw, y + hh, z + hd],
    [x - hw, y - hh, z - hd], [x + hw, y - hh, z - hd], [x + hw, y + hh, z - hd], [x - hw, y + hh, z - hd],
  ];
  const faces = [
    [[0, 1, 2, 3], roles[0]], [[4, 5, 1, 0], roles[4]], [[3, 2, 6, 7], roles[2]],
    [[1, 5, 6, 2], roles[3]], [[0, 3, 7, 4], roles[1]], [[5, 4, 7, 6], roles[5]],
  ];
  return mesh(verts, faces);
}

/** Extrude a 2D polygon ([[x, y]]) along z into a closed solid (2 caps + one quad per edge). */
export function prism(poly2d, depth, center = [0, 0, 0], capRole = 'front', sideRole = 'side') {
  const [x, y, z] = center;
  const hd = depth / 2;
  const n = poly2d.length;
  const verts = poly2d.map(([px, py]) => [px + x, py + y, hd + z])
    .concat(poly2d.map(([px, py]) => [px + x, py + y, -hd + z]));
  const back = Array.from({ length: n }, (_, i) => 2 * n - 1 - i);
  const faces = [[Array.from({ length: n }, (_, i) => i), capRole], [back, capRole]];
  for (let i = 0; i < n; i++) faces.push([[i, (i + 1) % n, n + (i + 1) % n, n + i], sideRole]);
  return mesh(verts, faces);
}

/** Scale → rotate → translate a whole mesh (returns a new mesh). */
export function transform(m, { rx = 0, ry = 0, rz = 0, move = [0, 0, 0], scale = 1 } = {}) {
  return {
    verts: m.verts.map((v) => {
      const r = rotate([v[0] * scale, v[1] * scale, v[2] * scale], rx, ry, rz);
      return [r[0] + move[0], r[1] + move[1], r[2] + move[2]];
    }),
    faces: m.faces,
  };
}

/** A pinhole camera orbiting `target`; `yaw`/`pitch` in radians, `dist` in world units. */
export function camera({ dist = 900, yaw = 0, pitch = 0, fov = 38, target = [0, 0, 0] } = {}) {
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  const cy = Math.cos(yaw), sy = Math.sin(yaw);
  const pos = [target[0] + dist * cp * sy, target[1] + dist * sp, target[2] + dist * cp * cy];
  const fwd = norm(sub(target, pos));
  const right = norm(cross(fwd, [0, 1, 0]));
  const up = cross(right, fwd);
  return { pos, fwd, right, up, fov: (fov * Math.PI) / 180, target };
}

/** Free pinhole camera with explicit position, target, up hint and roll (radians). */
export function lookCamera(position = [0, 0, 900], target = [0, 0, 0], fov = 38, roll = 0, up = [0, 1, 0]) {
  const pos = position.map(Number);
  const tgt = target.map(Number);
  const delta = sub(tgt, pos);
  if (dot(delta, delta) <= 1e-18) throw new Error('lookCamera position and target must differ');
  const forward = norm(delta);
  const rightRaw = cross(forward, norm(up));
  if (dot(rightRaw, rightRaw) <= 1e-18) {
    throw new Error('lookCamera up hint must not be parallel to the viewing direction');
  }
  let right = norm(rightRaw);
  let trueUp = norm(cross(right, forward));
  if (roll) {
    const c = Math.cos(roll), s = Math.sin(roll);
    const nextRight = right.map((v, i) => v * c + trueUp[i] * s);
    const nextUp = right.map((v, i) => -v * s + trueUp[i] * c);
    right = nextRight;
    trueUp = nextUp;
  }
  return { pos, fwd: forward, right, up: trueUp, fov: fov * Math.PI / 180, target: tgt, roll };
}

/** [[screen_x, screen_y, depth, scale]] — depth is view-space z (larger = farther). */
export function project(points, cam, w, h) {
  const f = (h / 2) / Math.tan(cam.fov / 2);
  return points.map((p) => {
    const rel = sub(p, cam.pos);
    const z = dot(rel, cam.fwd);
    if (z <= 1e-6) return [0, 0, Infinity, 0];
    const k = f / z;
    return [
      Math.round((w / 2 + dot(rel, cam.right) * k) * 1e4) / 1e4,
      Math.round((h / 2 - dot(rel, cam.up) * k) * 1e4) / 1e4,
      Math.round(z * 1e4) / 1e4,
      Math.round(k * 1e6) / 1e6,
    ];
  });
}

export function faceNormal(m, [idx]) {
  const a = m.verts[idx[0]], b = m.verts[idx[1]], c = m.verts[idx[2]];
  return norm(cross(sub(b, a), sub(c, a)));
}

const faceCentre = (m, idx) => [0, 1, 2].map(
  (k) => idx.reduce((s, i) => s + m.verts[i][k], 0) / idx.length,
);

/** Faces ordered far → near (painter's algorithm) with their view depth. */
export function sortedFaces(m, cam) {
  return m.faces.map(([idx, role]) => [dot(sub(faceCentre(m, idx), cam.pos), cam.fwd), role, idx])
    .sort((a, b) => b[0] - a[0]);
}

/** '#CB271B' | [r, g, b] → [r, g, b] — brand tokens are hex strings, meshes want numbers. */
export function toRgb(color) {
  if (Array.isArray(color)) return color;
  const h = String(color).trim().replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  if (!/^[0-9a-fA-F]{6}$/.test(full)) throw new Error(`not a colour: ${color}`);
  return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16));
}

/** Flat shading: ambient + diffuse, clamped so a face never goes black or blows out. */
export function shade(color, normal, light = [0.35, 0.75, 0.55], ambient = 0.45) {
  const ln = norm(light);
  const k = ambient + (1 - ambient) * Math.max(0, dot(normal, ln));
  return toRgb(color).map((c) => Math.max(0, Math.min(255, Math.round(c * k))));
}

/**
 * Paint a mesh with flat shading; returns how many faces were drawn.
 * `colors` maps a face role to an [r, g, b] (or a CSS colour). `cull` skips faces pointing away —
 * right for closed solids, wrong for open ribbons.
 */
export function drawMesh(ctx, m, cam, w, h, colors, opts = {}) {
  const { light = [0.35, 0.75, 0.55], ambient = 0.45, cull = true, outline = null, lineWidth = 2 } = opts;
  const projected = project(m.verts, cam, w, h);
  const rgb = (c) => (Array.isArray(c) ? `rgb(${c[0]},${c[1]},${c[2]})` : c);
  let drawn = 0;
  for (const [, role, idx] of sortedFaces(m, cam)) {
    const pts = idx.map((i) => projected[i]);
    if (pts.some((p) => p[3] === 0)) continue;
    const n = faceNormal(m, [idx, role]);
    if (cull && dot(n, sub(cam.pos, faceCentre(m, idx))) <= 0) continue;
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.closePath();
    ctx.fillStyle = rgb(shade(colors[role] ?? colors.side ?? [10, 10, 10], n, light, ambient));
    ctx.fill();
    if (outline) {
      ctx.strokeStyle = rgb(outline);
      ctx.lineWidth = lineWidth;
      ctx.stroke();
    }
    drawn++;
  }
  return drawn;
}
