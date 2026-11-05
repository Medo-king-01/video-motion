// Engine K adapter: pre-rendered slide textures + deterministic Canvas2D perspective triangles.
// Canvas2D has no arbitrary quad image transform, so non-aligned faces are tessellated in world
// space and each source triangle receives an affine transform. No Three.js/WebGL dependency.
import { drawMesh, project } from './space3d.js';
import { protectBox } from './layout.js';
import { normalizeSlideWall, slideHomography, slideWallStateAt } from './slide-wall.js';
import { brandHex } from './stage.js';

function texturedTriangle(ctx, image, source, dest) {
  const [[sx0, sy0], [sx1, sy1], [sx2, sy2]] = source;
  const [[dx0, dy0], [dx1, dy1], [dx2, dy2]] = dest;
  const den = sx0 * (sy1 - sy2) + sx1 * (sy2 - sy0) + sx2 * (sy0 - sy1);
  if (Math.abs(den) < 1e-9) return;
  const a = (dx0 * (sy1 - sy2) + dx1 * (sy2 - sy0) + dx2 * (sy0 - sy1)) / den;
  const c = (dx0 * (sx2 - sx1) + dx1 * (sx0 - sx2) + dx2 * (sx1 - sx0)) / den;
  const e = (dx0 * (sx1 * sy2 - sx2 * sy1) + dx1 * (sx2 * sy0 - sx0 * sy2) + dx2 * (sx0 * sy1 - sx1 * sy0)) / den;
  const b = (dy0 * (sy1 - sy2) + dy1 * (sy2 - sy0) + dy2 * (sy0 - sy1)) / den;
  const d = (dy0 * (sx2 - sx1) + dy1 * (sx0 - sx2) + dy2 * (sx1 - sx0)) / den;
  const f = (dy0 * (sx1 * sy2 - sx2 * sy1) + dy1 * (sx2 * sy0 - sx0 * sy2) + dy2 * (sx0 * sy1 - sx1 * sy0)) / den;
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(dx0, dy0);
  ctx.lineTo(dx1, dy1);
  ctx.lineTo(dx2, dy2);
  ctx.closePath();
  ctx.clip();
  ctx.transform(a, b, c, d, e, f);
  ctx.drawImage(image, 0, 0);
  ctx.restore();
}

function alignedRectangle(front) {
  const [tl, tr, br, bl] = front;
  const epsilon = 0.06;
  return Math.abs(tl[1] - tr[1]) < epsilon && Math.abs(bl[1] - br[1]) < epsilon
    && Math.abs(tl[0] - bl[0]) < epsilon && Math.abs(tr[0] - br[0]) < epsilon
    && tr[0] > tl[0] && bl[1] > tl[1];
}

function projectedRect(matrix, rect) {
  const points = [[rect.x, rect.y], [rect.x + rect.w, rect.y],
    [rect.x + rect.w, rect.y + rect.h], [rect.x, rect.y + rect.h]].map(([x, y]) => {
    const w = matrix[2][0] * x + matrix[2][1] * y + matrix[2][2];
    return [(matrix[0][0] * x + matrix[0][1] * y + matrix[0][2]) / w,
      (matrix[1][0] * x + matrix[1][1] * y + matrix[1][2]) / w];
  });
  const xs = points.map((p) => p[0]), ys = points.map((p) => p[1]);
  return { x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) };
}

/**
 * `drawSlide(ctx, slide, width, height)` paints one static RGBA texture. The scene retains
 * ownership of directed text, fonts and visual content. Optional `slideLayout` returns conservative
 * texture-space text rects so the existing screen-space layout audit can audit their projected AABBs.
 * Call `close()` through scene resources.
 */
export function createSlideWall(input, { drawSlide, slideLayout = null, textureWidth = 540, subdivision = 6 } = {}) {
  const spec = normalizeSlideWall(input);
  if (typeof drawSlide !== 'function') throw new TypeError('drawSlide must be callable');
  if (!Number.isInteger(textureWidth) || textureWidth < 32) throw new Error('textureWidth must be an integer >= 32');
  if (!Number.isInteger(subdivision) || subdivision < 1 || subdivision > 16) {
    throw new Error('subdivision must be an integer in [1,16]');
  }
  const textures = new Map();
  spec.slides.forEach((slide) => {
    const height = Math.max(1, Math.round(textureWidth * slide.size[1] / slide.size[0]));
    const canvas = document.createElement('canvas');
    canvas.width = textureWidth;
    canvas.height = height;
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) throw new Error(`slide ${slide.id}: Canvas2D texture context unavailable`);
    ctx.clearRect(0, 0, textureWidth, height);
    drawSlide(ctx, slide, textureWidth, height);
    textures.set(slide.id, canvas);
  });
  const layouts = new Map(spec.slides.map((slide) => {
    const rects = slideLayout ? slideLayout(slide, textures.get(slide.id).width, textures.get(slide.id).height) : [];
    if (!Array.isArray(rects)) throw new Error(`slide ${slide.id}: slideLayout must return an array`);
    rects.forEach((rect) => {
      if (!rect || typeof rect.id !== 'string' || !['x', 'y', 'w', 'h'].every((key) => Number.isFinite(rect[key]))
        || rect.w <= 0 || rect.h <= 0) throw new Error(`slide ${slide.id}: invalid conservative text rect`);
    });
    return [slide.id, rects];
  }));

  function stateAt(t, { motionMode = 'normal', viewport = null } = {}) {
    return slideWallStateAt(spec, t, { motionMode, viewport });
  }

  function draw(ctx, t, { motionMode = 'normal', viewport = null } = {}) {
    const state = stateAt(t, { motionMode, viewport });
    const { w: W, h: H } = spec.canvas;
    ctx.save();
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = brandHex(spec.backgroundRole);
    ctx.fillRect(0, 0, W, H);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    for (const item of state.slides) {
      if (!item.visible) continue;
      const { slide, mesh, front } = item;
      const colors = {};
      ['front', 'left', 'top', 'right', 'bottom', 'back'].forEach((role) => {
        colors[role] = brandHex(role === 'front' ? slide.surfaceRole : slide.edgeRole);
      });
      drawMesh(ctx, mesh, state.camera, W, H, colors, { ambient: 1 });
      const texture = textures.get(slide.id);
      const tw = texture.width, th = texture.height;
      const segment = spec.timeline[state.segmentIndex];
      const activeIds = state.mode === 'slide' ? [segment.slide]
        : state.mode === 'move' ? [segment.from, segment.to].filter((e) => e.type === 'slide').map((e) => e.slide)
          : spec.slides.map((entry) => entry.id);
      if (activeIds.includes(slide.id)) {
        const matrix = slideHomography(tw, th, front);
        layouts.get(slide.id).forEach((rect) => {
          const projectedBox = projectedRect(matrix, rect);
          const x0 = Math.max(projectedBox.x, state.viewport.x), y0 = Math.max(projectedBox.y, state.viewport.y);
          const x1 = Math.min(projectedBox.x + projectedBox.w, state.viewport.x + state.viewport.w);
          const y1 = Math.min(projectedBox.y + projectedBox.h, state.viewport.y + state.viewport.h);
          if (x1 - x0 > 1 && y1 - y0 > 1) {
            protectBox(ctx, `${slide.id}/${rect.id}`, { x: x0, y: y0, w: x1 - x0, h: y1 - y0 }, 'text');
          }
        });
      }
      if (alignedRectangle(front)) {
        ctx.drawImage(texture, front[0][0], front[0][1], front[1][0] - front[0][0], front[3][1] - front[0][1]);
        continue;
      }
      // Bilinear interpolation happens on the planar world rectangle, not in screen space.
      const tl = mesh.verts[3], tr = mesh.verts[2], br = mesh.verts[1], bl = mesh.verts[0];
      const point = (u, v) => {
        const world = [0, 1, 2].map((axis) => {
          const top = tl[axis] + (tr[axis] - tl[axis]) * u;
          const bottom = bl[axis] + (br[axis] - bl[axis]) * u;
          return top + (bottom - top) * v;
        });
        return project([world], state.camera, W, H)[0];
      };
      for (let y = 0; y < subdivision; y++) for (let x = 0; x < subdivision; x++) {
        const u0 = x / subdivision, u1 = (x + 1) / subdivision;
        const v0 = y / subdivision, v1 = (y + 1) / subdivision;
        const p00 = point(u0, v0), p10 = point(u1, v0), p11 = point(u1, v1), p01 = point(u0, v1);
        const s00 = [u0 * tw, v0 * th], s10 = [u1 * tw, v0 * th];
        const s11 = [u1 * tw, v1 * th], s01 = [u0 * tw, v1 * th];
        texturedTriangle(ctx, texture, [s00, s10, s11], [p00, p10, p11]);
        texturedTriangle(ctx, texture, [s00, s11, s01], [p00, p11, p01]);
      }
    }
    ctx.restore();
    return state;
  }

  function close() {
    textures.forEach((canvas) => { canvas.width = 1; canvas.height = 1; });
    textures.clear();
    layouts.clear();
  }
  return { spec, textures, stateAt, draw, close };
}
