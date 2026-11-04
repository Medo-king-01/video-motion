// 3D extruded icon/symbol/emblem tile for explainer scenes (engines K and R).
// Pure zero-import ES module so engines K and R share it byte for byte.
// Designed for explaining tools, hardware, protocols, or user-supplied symbols — NEVER as an
// unrequested channel/studio watermark (AGENTS.md Rule 1).
// Keyframe pose, idle float & specular gloss sweep inspired by MIT-licensed video-ad-editor (see assets/CREDITS.md).

const DEG2RAD = Math.PI / 180;

export const TILE3D_PALETTE = {
  red: '#CB271B', red_bright: '#CB0801', red_deep: '#9F0803',
  ink: '#0A0A0A', ink_soft: '#71717A', paper: '#F3F2F1',
  gray_1: '#D8D7D5', gray_2: '#C9C5C2', gray_3: '#BFBAB7', gray_4: '#A3A2A0',
  salmon: '#D97F68', blush: '#D5AEA6', inkShadow: '#030303',
};

export const TILE3D_ROLES = {
  paper: { face: TILE3D_PALETTE.paper, side: TILE3D_PALETTE.gray_2, sideDark: TILE3D_PALETTE.gray_4, rim: TILE3D_PALETTE.salmon, fg: TILE3D_PALETTE.ink },
  dark: { face: TILE3D_PALETTE.ink, side: TILE3D_PALETTE.ink_soft, sideDark: TILE3D_PALETTE.inkShadow, rim: TILE3D_PALETTE.salmon, fg: TILE3D_PALETTE.paper },
  accent: { face: TILE3D_PALETTE.red, side: TILE3D_PALETTE.red_deep, sideDark: TILE3D_PALETTE.ink, rim: TILE3D_PALETTE.salmon, fg: TILE3D_PALETTE.paper },
  warm: { face: TILE3D_PALETTE.salmon, side: TILE3D_PALETTE.red, sideDark: TILE3D_PALETTE.red_deep, rim: TILE3D_PALETTE.blush, fg: TILE3D_PALETTE.ink },
  soft: { face: TILE3D_PALETTE.gray_1, side: TILE3D_PALETTE.gray_3, sideDark: TILE3D_PALETTE.ink_soft, rim: TILE3D_PALETTE.paper, fg: TILE3D_PALETTE.ink },
};

const EASE = {
  linear: k => k,
  lin: k => k,
  out: k => 1 - Math.pow(1 - k, 3),
  inout: k => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
  back: k => 1 + 2.2 * Math.pow(k - 1, 3) + 1.2 * Math.pow(k - 1, 2),
};

const clamp01 = v => Math.min(1, Math.max(0, v));

function interpKey(keys, t, prop, fallback) {
  if (!Array.isArray(keys) || !keys.length) return fallback;
  const val = k => (k[prop] ?? fallback);
  if (t <= keys[0].t) return val(keys[0]);
  for (let i = 0; i < keys.length - 1; i += 1) {
    const a = keys[i];
    const b = keys[i + 1];
    if (t <= b.t) {
      const u = clamp01((t - a.t) / Math.max(1e-4, b.t - a.t));
      const fn = EASE[b.ease || 'out'] || EASE.out;
      return val(a) + (val(b) - val(a)) * fn(u);
    }
  }
  return val(keys[keys.length - 1]);
}

/** Pure function of `t`: evaluate 3D tile position, rotation (deg), scale, opacity & shine sweep. */
export function sampleTilePose(spec = {}, t = 0) {
  const keys = spec.keys || null;
  const floatAmp = spec.float ?? 1;
  const phase = spec.phase ?? 0;
  const size = spec.size ?? 280;
  const shinePeriod = Math.max(0.25, spec.shinePeriod ?? 2.4);
  const shineLoop = (((t + phase * 0.7) % shinePeriod) + shinePeriod) % shinePeriod;

  const baseX = interpKey(keys, t, 'x', spec.x ?? 540);
  const baseY = interpKey(keys, t, 'y', spec.y ?? 760);
  const baseZ = interpKey(keys, t, 'z', spec.z ?? 0);
  const scale = Math.max(0.001, interpKey(keys, t, 'scale', interpKey(keys, t, 's', spec.scale ?? 1)));
  const rx = interpKey(keys, t, 'rx', spec.rx ?? -8) + floatAmp * 3 * Math.sin(t * 1.1 + phase);
  const ry = interpKey(keys, t, 'ry', spec.ry ?? 14) + floatAmp * 9 * Math.sin(t * 0.9 + phase) + (spec.spin ?? 0) * t * 360;
  const rz = interpKey(keys, t, 'rz', spec.rz ?? 0);
  const opacity = clamp01(interpKey(keys, t, 'opacity', interpKey(keys, t, 'o', spec.opacity ?? 1)));

  return {
    x: baseX,
    y: baseY - floatAmp * size * 0.032 * Math.sin(t * 1.6 + phase),
    z: baseZ,
    size,
    scale,
    rx,
    ry,
    rz,
    opacity,
    shineCenter: -0.4 + (shineLoop / shinePeriod) * 1.8,
  };
}

function rotate3(px, py, pz, rxDeg, ryDeg, rzDeg) {
  let x = px, y = py, z = pz;
  const rx = rxDeg * DEG2RAD, ry = ryDeg * DEG2RAD, rz = rzDeg * DEG2RAD;
  if (rx) { const c = Math.cos(rx), s = Math.sin(rx); [y, z] = [y * c - z * s, y * s + z * c]; }
  if (ry) { const c = Math.cos(ry), s = Math.sin(ry); [x, z] = [x * c + z * s, -x * s + z * c]; }
  if (rz) { const c = Math.cos(rz), s = Math.sin(rz); [x, y] = [x * c - y * s, x * s + y * c]; }
  return [x, y, z];
}

function roundedSquareContour(half, radius, stepsPerCorner = 6) {
  const r = Math.min(half * 0.48, Math.max(2, radius));
  const inner = half - r;
  const corners = [
    [inner, -inner, -Math.PI / 2, 0],
    [inner, inner, 0, Math.PI / 2],
    [-inner, inner, Math.PI / 2, Math.PI],
    [-inner, -inner, Math.PI, Math.PI * 1.5],
  ];
  const pts = [];
  for (const [cx, cy, a0, a1] of corners) {
    for (let i = 0; i <= stepsPerCorner; i += 1) {
      const a = a0 + ((a1 - a0) * i) / stepsPerCorner;
      pts.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]);
    }
  }
  return pts;
}

function hexRgb(hex) {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function mixHex(hexA, hexB, u) {
  const t = clamp01(u);
  const a = hexRgb(hexA), b = hexRgb(hexB);
  const r = Math.round(a[0] + (b[0] - a[0]) * t);
  const g = Math.round(a[1] + (b[1] - a[1]) * t);
  const bl = Math.round(a[2] + (b[2] - a[2]) * t);
  return `rgb(${r},${g},${bl})`;
}

/**
 * Draw a 3D beveled explainer tile on a 2D Canvas (`ctx`) at time `t`.
 * Pass `drawSymbol(ctx, faceSize, fgColor)` or `image` to render an icon, badge, or SVG path on the front face.
 */
export function drawTile3d(ctx, t, spec = {}) {
  const pose = sampleTilePose(spec, t);
  if (pose.opacity <= 0.003) return pose;

  const role = TILE3D_ROLES[spec.role || 'paper'] || TILE3D_ROLES.paper;
  const fullSize = pose.size * pose.scale;
  const half = fullSize / 2;
  const radius = fullSize * (spec.radiusRatio ?? 0.22);
  const depth = fullSize * (spec.depthRatio ?? 0.18);
  const camDist = Math.max(fullSize * 3.2, spec.cameraDist ?? 1100);
  const shineAlpha = spec.shine ?? 0.22;

  const proj = (lx, ly, lz) => {
    const [wx, wy, wz] = rotate3(lx, ly, lz, pose.rx, pose.ry, pose.rz);
    const denom = Math.max(120, camDist - wz - pose.z);
    const k = camDist / denom;
    return [pose.x + wx * k, pose.y + wy * k, wz];
  };

  const contour = roundedSquareContour(half, radius, 6);
  const frontPts = contour.map(([x, y]) => proj(x, y, depth / 2));
  const backPts = contour.map(([x, y]) => proj(x, y, -depth / 2));

  ctx.save();
  ctx.globalAlpha *= pose.opacity;

  // 1. Soft perspective drop shadow
  if (spec.shadow !== false) {
    const shOffX = -pose.ry * 0.45;
    const shOffY = fullSize * 0.09 + pose.rx * 0.35;
    ctx.save();
    ctx.globalAlpha *= spec.shadowOpacity ?? 0.26;
    ctx.fillStyle = TILE3D_PALETTE.inkShadow;
    ctx.beginPath();
    backPts.forEach(([px, py], idx) => {
      if (idx === 0) ctx.moveTo(px + shOffX, py + shOffY);
      else ctx.lineTo(px + shOffX, py + shOffY);
    });
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  // 2. Extruded side perimeter quads (painter-sorted back-to-front with directional + rim shading)
  const quads = [];
  for (let i = 0; i < contour.length; i += 1) {
    const j = (i + 1) % contour.length;
    const f0 = frontPts[i], f1 = frontPts[j];
    const b0 = backPts[i], b1 = backPts[j];
    const midX = (contour[i][0] + contour[j][0]) * 0.5;
    const midY = (contour[i][1] + contour[j][1]) * 0.5;
    const nLen = Math.hypot(midX, midY) || 1;
    const [nx, ny, nz] = rotate3(midX / nLen, midY / nLen, 0, pose.rx, pose.ry, pose.rz);
    const keyDot = clamp01(nx * 0.42 - ny * 0.58 + nz * 0.69);
    const rimDot = Math.pow(clamp01(-nx * 0.65 - ny * 0.35 + (1 - Math.abs(nz)) * 0.45), 2.2);
    const baseCol = mixHex(role.sideDark, role.side, keyDot);
    const shaded = rimDot > 0.15 ? mixHex(baseCol, role.rim, rimDot * 0.65) : baseCol;
    const avgZ = (f0[2] + f1[2] + b0[2] + b1[2]) * 0.25;
    quads.push({ pts: [b0, b1, f1, f0], color: shaded, z: avgZ });
  }
  quads.sort((a, b) => a.z - b.z);
  for (const q of quads) {
    ctx.fillStyle = q.color;
    ctx.strokeStyle = q.color;
    ctx.lineWidth = 1.1;
    ctx.beginPath();
    ctx.moveTo(q.pts[0][0], q.pts[0][1]);
    for (let k = 1; k < 4; k += 1) ctx.lineTo(q.pts[k][0], q.pts[k][1]);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }

  // 3. Front (or back when spun > 90 deg) cap + clipped face artwork + diagonal gloss sweep
  const [fnx, fny, fnz] = rotate3(0, 0, 1, pose.rx, pose.ry, pose.rz);
  const showingFront = fnz >= 0;
  const capPts = showingFront ? frontPts : backPts;
  const capCenter = proj(0, 0, showingFront ? depth / 2 : -depth / 2);
  const capRight = proj(half, 0, showingFront ? depth / 2 : -depth / 2);
  const capDown = proj(0, half, showingFront ? depth / 2 : -depth / 2);

  ctx.save();
  ctx.beginPath();
  capPts.forEach(([px, py], idx) => (idx === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)));
  ctx.closePath();
  ctx.fillStyle = showingFront ? role.face : role.sideDark;
  ctx.fill();
  ctx.clip();

  // Map 2D local face coordinates [-half..half] onto the projected 3D cap basis
  const ux = (capRight[0] - capCenter[0]) / Math.max(1e-4, half);
  const uy = (capRight[1] - capCenter[1]) / Math.max(1e-4, half);
  const vx = (capDown[0] - capCenter[0]) / Math.max(1e-4, half);
  const vy = (capDown[1] - capCenter[1]) / Math.max(1e-4, half);

  ctx.save();
  ctx.transform(ux, uy, vx, vy, capCenter[0], capCenter[1]);

  if (showingFront) {
    if (spec.image) {
      const iconS = fullSize * (spec.symbolScale ?? 0.58);
      ctx.drawImage(spec.image, -iconS / 2, -iconS / 2, iconS, iconS);
    }
    if (typeof spec.drawSymbol === 'function') {
      spec.drawSymbol(ctx, fullSize, role.fg);
    }
  }

  // Top soft studio sheen
  if (typeof ctx.createLinearGradient === 'function') {
    const topG = ctx.createLinearGradient(0, -half, 0, half * 0.15);
    topG.addColorStop(0, 'rgba(243,242,241,0.16)');
    topG.addColorStop(1, 'rgba(243,242,241,0)');
    ctx.fillStyle = topG;
    ctx.fillRect(-half * 1.2, -half * 1.2, fullSize * 1.2, fullSize * 0.7);

    // Animated diagonal specular gloss sweep (pure function of `t`)
    if (shineAlpha > 0) {
      const c = pose.shineCenter;
      const g = ctx.createLinearGradient(
        (-0.5 + c - 0.25) * fullSize,
        -half,
        (-0.5 + c + 0.25) * fullSize,
        half,
      );
      g.addColorStop(0, 'rgba(243,242,241,0)');
      g.addColorStop(0.5, `rgba(243,242,241,${shineAlpha})`);
      g.addColorStop(1, 'rgba(243,242,241,0)');
      ctx.fillStyle = g;
      ctx.fillRect(-half * 1.3, -half * 1.3, fullSize * 1.3, fullSize * 1.3);
    }
  }
  ctx.restore();

  // Subtle rim outline around the front face
  ctx.strokeStyle = role.rim;
  ctx.globalAlpha *= 0.55 + 0.35 * clamp01(Math.abs(fnx) + Math.abs(fny));
  ctx.lineWidth = Math.max(1.5, fullSize * 0.01);
  ctx.stroke();
  ctx.restore();

  ctx.restore();
  return pose;
}
