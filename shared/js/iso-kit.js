// Isometric cutaway "How it works" diagram kit for engines K and R.
// Pure zero-import ES module so engines K and R share it byte for byte.
// Every colour literal comes strictly from the locked 12-colour Medo palette (+ ink_shadow).
// Projection & cutaway layering inspired by MIT-licensed iso-kit / video-ad-editor (see assets/CREDITS.md).

const COS30 = 0.8660254037844386;
const SIN30 = 0.5;
const LAYER_RANK = { back: 0, mid: 1, front: 2 };

export const ISO_PALETTE = {
  red: '#CB271B', red_bright: '#CB0801', red_deep: '#9F0803',
  ink: '#0A0A0A', ink_soft: '#71717A', paper: '#F3F2F1',
  gray_1: '#D8D7D5', gray_2: '#C9C5C2', gray_3: '#BFBAB7', gray_4: '#A3A2A0',
  salmon: '#D97F68', blush: '#D5AEA6', inkShadow: '#030303',
};

const ROLE_THEMES = {
  dark: {
    housing: { top: ISO_PALETTE.ink_soft, left: ISO_PALETTE.ink, right: ISO_PALETTE.inkShadow, stroke: ISO_PALETTE.gray_4 },
    paper: { top: ISO_PALETTE.paper, left: ISO_PALETTE.gray_1, right: ISO_PALETTE.gray_3, stroke: ISO_PALETTE.ink },
    chip: { top: ISO_PALETTE.gray_4, left: ISO_PALETTE.ink_soft, right: ISO_PALETTE.ink, stroke: ISO_PALETTE.paper },
    accent: { top: ISO_PALETTE.salmon, left: ISO_PALETTE.red, right: ISO_PALETTE.red_deep, stroke: ISO_PALETTE.paper },
    warm: { top: ISO_PALETTE.blush, left: ISO_PALETTE.salmon, right: ISO_PALETTE.red, stroke: ISO_PALETTE.paper },
  },
  light: {
    housing: { top: ISO_PALETTE.paper, left: ISO_PALETTE.gray_1, right: ISO_PALETTE.gray_3, stroke: ISO_PALETTE.ink },
    paper: { top: ISO_PALETTE.paper, left: ISO_PALETTE.gray_1, right: ISO_PALETTE.gray_2, stroke: ISO_PALETTE.ink },
    chip: { top: ISO_PALETTE.ink_soft, left: ISO_PALETTE.ink, right: ISO_PALETTE.inkShadow, stroke: ISO_PALETTE.ink },
    accent: { top: ISO_PALETTE.salmon, left: ISO_PALETTE.red, right: ISO_PALETTE.red_deep, stroke: ISO_PALETTE.ink },
    warm: { top: ISO_PALETTE.blush, left: ISO_PALETTE.salmon, right: ISO_PALETTE.red, stroke: ISO_PALETTE.ink },
  },
};

const clamp01 = v => Math.min(1, Math.max(0, v));

export function isoProject(x, y, z, { originX = 540, originY = 820, scale = 1 } = {}) {
  return {
    x: originX + (x - y) * COS30 * scale,
    y: originY + (x + y) * SIN30 * scale - z * scale,
    depth: x + y + z,
  };
}

function polylineLength(pts) {
  let len = 0;
  for (let i = 1; i < pts.length; i += 1) {
    len += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
  }
  return len;
}

function tracePartialPolyline(ctx, pts, progress, close = false) {
  const closed = close && pts.length > 2 ? [...pts, pts[0]] : pts;
  if (closed.length < 2) return;
  const p = clamp01(progress);
  if (p <= 0) return;
  const total = polylineLength(closed);
  let budget = total * p;
  ctx.beginPath();
  ctx.moveTo(closed[0].x, closed[0].y);
  for (let i = 1; i < closed.length && budget > 0; i += 1) {
    const a = closed[i - 1];
    const b = closed[i];
    const seg = Math.hypot(b.x - a.x, b.y - a.y);
    if (seg <= 1e-6) continue;
    if (budget >= seg) {
      ctx.lineTo(b.x, b.y);
      budget -= seg;
    } else {
      const f = budget / seg;
      ctx.lineTo(a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f);
      budget = 0;
    }
  }
  ctx.stroke();
}

function pointAtPolyline(pts, p) {
  if (!pts.length) return { x: 0, y: 0 };
  if (pts.length === 1) return pts[0];
  const total = polylineLength(pts);
  let target = total * clamp01(p);
  for (let i = 1; i < pts.length; i += 1) {
    const a = pts[i - 1];
    const b = pts[i];
    const seg = Math.hypot(b.x - a.x, b.y - a.y);
    if (target <= seg || i === pts.length - 1) {
      const f = seg > 1e-6 ? clamp01(target / seg) : 0;
      return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f };
    }
    target -= seg;
  }
  return pts[pts.length - 1];
}

function fillPoly(ctx, pts, fill, alpha) {
  if (alpha <= 0.005 || pts.length < 3) return;
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.fillStyle = fill;
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);
  for (let i = 1; i < pts.length; i += 1) ctx.lineTo(pts[i].x, pts[i].y);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

export function createIsoScene({
  originX = 540,
  originY = 820,
  scale = 1,
  theme = 'dark',
  lineWidth = 2.6,
} = {}) {
  const paletteMap = ROLE_THEMES[theme === 'light' ? 'light' : 'dark'];
  const ops = [];
  const proj = (x, y, z) => isoProject(x, y, z, { originX, originY, scale });
  const roleColors = role => paletteMap[role] || paletteMap.housing;

  return {
    project: proj,

    slab({
      x = 0, y = 0, z = 0, dx = 120, dy = 90, dz = 28,
      role = 'housing', layer = 'mid', reveal = 1, alpha = 1,
    } = {}) {
      const r = clamp01(reveal);
      if (r <= 0 || alpha <= 0) return this;
      const c = roleColors(role);
      const p000 = proj(x, y, z);
      const p100 = proj(x + dx, y, z);
      const p010 = proj(x, y + dy, z);
      const p110 = proj(x + dx, y + dy, z);
      const p001 = proj(x, y, z + dz);
      const p101 = proj(x + dx, y, z + dz);
      const p011 = proj(x, y + dy, z + dz);
      const p111 = proj(x + dx, y + dy, z + dz);
      const fillAlpha = alpha * clamp01((r - 0.25) / 0.75);
      const depth = x + dx * 0.5 + y + dy * 0.5 + z + dz * 0.5;
      ops.push({
        layer: LAYER_RANK[layer] ?? 1,
        depth,
        draw(ctx) {
          const leftFace = [p010, p110, p111, p011];
          const rightFace = [p100, p110, p111, p101];
          const topFace = [p001, p101, p111, p011];
          fillPoly(ctx, leftFace, c.left, fillAlpha);
          fillPoly(ctx, rightFace, c.right, fillAlpha);
          fillPoly(ctx, topFace, c.top, fillAlpha);
          ctx.save();
          ctx.globalAlpha *= alpha;
          ctx.strokeStyle = c.stroke;
          ctx.lineWidth = lineWidth;
          ctx.lineJoin = 'round';
          ctx.lineCap = 'round';
          tracePartialPolyline(ctx, leftFace, r, true);
          tracePartialPolyline(ctx, rightFace, r, true);
          tracePartialPolyline(ctx, topFace, r, true);
          ctx.restore();
        },
      });
      return this;
    },

    cylinder({
      x = 0, y = 0, z = 0, r = 36, h = 48, segments = 24,
      role = 'chip', layer = 'mid', reveal = 1, alpha = 1,
    } = {}) {
      const rev = clamp01(reveal);
      if (rev <= 0 || alpha <= 0) return this;
      const c = roleColors(role);
      const topPts = [];
      const botPts = [];
      for (let i = 0; i < segments; i += 1) {
        const a = (i / segments) * Math.PI * 2;
        const px = x + Math.cos(a) * r;
        const py = y + Math.sin(a) * r;
        topPts.push(proj(px, py, z + h));
        botPts.push(proj(px, py, z));
      }
      let minIdx = 0, maxIdx = 0;
      for (let i = 1; i < segments; i += 1) {
        if (topPts[i].x < topPts[minIdx].x) minIdx = i;
        if (topPts[i].x > topPts[maxIdx].x) maxIdx = i;
      }
      const frontArc = [];
      for (let i = minIdx; ; i = (i + 1) % segments) {
        frontArc.push(botPts[i]);
        if (i === maxIdx) break;
        if (frontArc.length > segments) break;
      }
      const sidePoly = [topPts[minIdx], ...frontArc, topPts[maxIdx]];
      const fillAlpha = alpha * clamp01((rev - 0.25) / 0.75);
      ops.push({
        layer: LAYER_RANK[layer] ?? 1,
        depth: x + y + z + h * 0.5,
        draw(ctx) {
          fillPoly(ctx, sidePoly, c.left, fillAlpha);
          fillPoly(ctx, topPts, c.top, fillAlpha);
          ctx.save();
          ctx.globalAlpha *= alpha;
          ctx.strokeStyle = c.stroke;
          ctx.lineWidth = lineWidth;
          ctx.lineJoin = 'round';
          tracePartialPolyline(ctx, sidePoly, rev, false);
          tracePartialPolyline(ctx, topPts, rev, true);
          ctx.restore();
        },
      });
      return this;
    },

    ring({
      x = 0, y = 0, z = 0, rOuter = 64, rInner = 24, h = 16,
      blades = 0, spinDeg = 0, role = 'housing', layer = 'mid', reveal = 1, alpha = 1,
    } = {}) {
      this.cylinder({ x, y, z, r: rOuter, h, role, layer, reveal, alpha });
      this.cylinder({ x, y, z: z + 1, r: rInner, h, role: 'accent', layer, reveal, alpha });
      if (blades > 0 && reveal > 0.2) {
        const c = roleColors('warm');
        const spin = (spinDeg * Math.PI) / 180;
        ops.push({
          layer: LAYER_RANK[layer] ?? 1,
          depth: x + y + z + h + 0.5,
          draw(ctx) {
            ctx.save();
            ctx.globalAlpha *= alpha * clamp01(reveal);
            ctx.strokeStyle = c.stroke;
            ctx.lineWidth = lineWidth * 1.1;
            ctx.lineCap = 'round';
            for (let b = 0; b < blades; b += 1) {
              const a = spin + (b / blades) * Math.PI * 2;
              const p0 = proj(x + Math.cos(a) * rInner, y + Math.sin(a) * rInner, z + h);
              const p1 = proj(x + Math.cos(a + 0.25) * (rOuter * 0.9), y + Math.sin(a + 0.25) * (rOuter * 0.9), z + h);
              ctx.beginPath();
              ctx.moveTo(p0.x, p0.y);
              ctx.lineTo(p1.x, p1.y);
              ctx.stroke();
            }
            ctx.restore();
          },
        });
      }
      return this;
    },

    coil({
      x = 0, y = 0, z = 0, length = 140, radius = 16, turns = 6,
      axis = 'x', role = 'warm', layer = 'mid', reveal = 1, alpha = 1,
    } = {}) {
      const steps = Math.max(24, turns * 12);
      const pts = [];
      for (let i = 0; i <= steps; i += 1) {
        const u = i / steps;
        const ang = u * turns * Math.PI * 2;
        const along = u * length;
        const c1 = Math.cos(ang) * radius;
        const c2 = Math.sin(ang) * radius;
        const px = axis === 'x' ? x + along : x + c1;
        const py = axis === 'y' ? y + along : (axis === 'x' ? y + c1 : y + c2);
        const pz = axis === 'z' ? z + along : z + c2;
        pts.push(proj(px, py, pz));
      }
      const c = roleColors(role);
      ops.push({
        layer: LAYER_RANK[layer] ?? 1,
        depth: x + y + z + length * 0.5,
        draw(ctx) {
          ctx.save();
          ctx.globalAlpha *= alpha;
          ctx.strokeStyle = c.top;
          ctx.lineWidth = lineWidth * 1.35;
          ctx.lineCap = 'round';
          ctx.lineJoin = 'round';
          tracePartialPolyline(ctx, pts, reveal, false);
          ctx.restore();
        },
      });
      return this;
    },

    wire({
      points = [], role = 'accent', layer = 'mid', width = 4,
      reveal = 1, flowP = -1, alpha = 1,
    } = {}) {
      if (!Array.isArray(points) || points.length < 2) return this;
      const pts = points.map(([px, py, pz]) => proj(px, py, pz));
      const avgDepth = points.reduce((s, [px, py, pz]) => s + px + py + pz, 0) / points.length;
      const c = roleColors(role);
      ops.push({
        layer: LAYER_RANK[layer] ?? 1,
        depth: avgDepth,
        draw(ctx) {
          ctx.save();
          ctx.globalAlpha *= alpha;
          ctx.strokeStyle = c.top;
          ctx.lineWidth = width;
          ctx.lineCap = 'round';
          ctx.lineJoin = 'round';
          tracePartialPolyline(ctx, pts, reveal, false);
          if (flowP >= 0 && flowP <= 1 && reveal > 0.2) {
            const pulse = pointAtPolyline(pts, flowP);
            ctx.fillStyle = ISO_PALETTE.paper;
            ctx.beginPath();
            ctx.arc(pulse.x, pulse.y, width * 1.45, 0, Math.PI * 2);
            ctx.fill();
          }
          ctx.restore();
        },
      });
      return this;
    },

    render(ctx) {
      const sorted = [...ops].sort((a, b) => (a.layer - b.layer) || (a.depth - b.depth));
      for (const op of sorted) op.draw(ctx);
      return sorted.length;
    },
  };
}
