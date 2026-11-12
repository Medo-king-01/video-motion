// Declarative board interpreter (B2): data in, draw ops out.
//
// A board never runs scene code. `boardFrame(board, time)` samples the board into a flat list of
// ops (pure numbers, sorted by z) and `drawBoardFrame(ctx, frame, assets)` paints them. The split
// is what makes a board testable without a browser and scrubbable frame by frame.
//
// Unsupported values throw. Nothing here guesses a colour, a pose or a move id.
import {
  pixelListItem, parallaxLayer, orbitItem, wordPathItem, explodePart, cardStackItem, cameraPush,
} from './moves.js';
import { clamp } from './motion.js';

export const KINDS = ['text', 'shape', 'draw', 'data', 'person', 'image'];
export const ELEMENT_MOVES = ['pixel-list', 'orbit', 'word-path', 'explode', 'card-stack', 'parallax'];
export const CAMERA_MOVES = ['camera-push', 'parallax'];
export const SHAPES = ['rect', 'ellipse', 'line'];

const IDENTITY = { x: 0, y: 0, scale: 1, rotation: 0, alpha: 1 };

const emOf = element => element.size ?? element.h ?? 40;

function elementMoveState(move, elapsed, element) {
  if (!move) return { ...IDENTITY, progress: 1 };
  const id = move.move;
  const params = move.params ?? {};
  if (!ELEMENT_MOVES.includes(id)) throw new RangeError(`Unknown element move ${id}`);
  const em = params.em ?? emOf(element);
  let raw;
  if (id === 'pixel-list') raw = pixelListItem(0, elapsed, params);
  else if (id === 'orbit') raw = orbitItem(0, elapsed, params);
  else if (id === 'word-path') raw = wordPathItem(0, elapsed, params);
  else if (id === 'explode') raw = explodePart(0, elapsed, params);
  else if (id === 'card-stack') raw = cardStackItem(0, elapsed, params);
  else {
    const duration = params.duration ?? 1;
    raw = parallaxLayer(params.depth ?? 0.5, clamp(elapsed / duration, 0, 1),
      { panX: params.panX, panY: params.panY, zoom: params.zoom });
  }
  return {
    x: (raw.x ?? 0) * em,
    y: (raw.y ?? 0) * em,
    scale: raw.scale ?? 1,
    rotation: raw.rotation ?? 0,
    alpha: raw.opacity ?? 1,
    progress: raw.progress ?? raw.p ?? 1,
  };
}

function cameraState(camera, elapsed) {
  if (!camera) return { ...IDENTITY };
  const params = camera.params ?? {};
  if (!Object.prototype.hasOwnProperty.call({ 'camera-push': 1, parallax: 1 }, camera.move)) {
    throw new RangeError(`Unknown camera move ${camera.move}`);
  }
  if (camera.move === 'camera-push') {
    const state = cameraPush(elapsed, params);
    return { x: state.x, y: state.y, scale: state.scale, rotation: 0, alpha: 1 };
  }
  const state = parallaxLayer(params.depth ?? 0.5, clamp(elapsed / (params.duration ?? 1), 0, 1),
    { panX: params.panX, panY: params.panY, zoom: params.zoom });
  return { x: state.x, y: state.y, scale: state.scale, rotation: 0, alpha: 1 };
}

function sceneAt(board, time) {
  for (const scene of board.scenes) {
    if (time >= scene.start && time < scene.start + scene.duration) return scene;
  }
  return null;
}

/**
 * Sample the board at `time`. Returns {sceneId, time, local, stage, camera, ops}.
 * Throws on a time outside the board, an unknown kind or an unknown move.
 */
export function boardFrame(board, time) {
  if (!board || board.version !== 1) throw new RangeError('board version must be 1');
  if (!Array.isArray(board.scenes) || board.scenes.length === 0) throw new RangeError('board has no scenes');
  const t = Number(time);
  if (!Number.isFinite(t) || t < 0) throw new RangeError('time must be a finite number >= 0');
  const total = board.duration;
  if (!(t < total)) throw new RangeError(`time ${t} is outside the board (duration ${total})`);
  const scene = sceneAt(board, t);
  if (!scene) throw new RangeError(`no scene covers time ${t}`);
  const local = t - scene.start;
  const ops = [];
  for (const element of scene.elements) {
    if (!KINDS.includes(element.kind)) throw new RangeError(`Unknown board kind ${element.kind}`);
    const start = element.at ?? 0;
    if (local < start) continue;
    const state = elementMoveState(element.move, local - start, element);
    ops.push({
      id: element.id, kind: element.kind, z: element.z,
      x: element.x + state.x, y: element.y + state.y,
      scale: state.scale, rotation: state.rotation, alpha: state.alpha,
      progress: state.progress,
      ...(element.kind === 'text' ? {
        text: element.text, size: element.size, font: element.font ?? null,
        color: element.color ?? 'ink', align: element.align ?? 'right',
        maxWidth: element.maxWidth ?? null,
      } : {}),
      ...(element.kind === 'shape' ? {
        shape: element.shape, w: element.w, h: element.h,
        fill: element.fill ?? null, stroke: element.stroke ?? null,
        strokeWidth: element.strokeWidth ?? 0, radius: element.radius ?? 0,
      } : {}),
      ...(element.kind === 'draw' ? {
        points: element.points, stroke: element.stroke ?? 'ink',
        strokeWidth: element.strokeWidth ?? 6, arrow: element.arrow ?? false,
      } : {}),
      ...(element.kind === 'data' ? {
        values: element.values, w: element.w, h: element.h,
        fill: element.fill ?? 'ink', gap: element.gap ?? 0.25,
      } : {}),
      ...(element.kind === 'person' ? {
        pose: element.pose, h: element.h,
        w: element.w ?? Math.max(1, Math.round(element.h * 0.62)),
      } : {}),
      ...(element.kind === 'image' ? {
        src: element.src, w: element.w, h: element.h, fit: element.fit ?? 'cover',
      } : {}),
    });
  }
  ops.sort((a, b) => a.z - b.z);
  return {
    sceneId: scene.id, time: t, local,
    stage: { width: board.stage.width, height: board.stage.height, background: board.stage.background },
    camera: cameraState(scene.camera, local),
    ops,
  };
}

/** Local time samples for a board, used by previews and tests. */
export function boardTimes(board, count = 4) {
  const step = board.duration / count;
  return Array.from({ length: count }, (_, i) => Math.min(board.duration - 1e-6, i * step));
}

const colorOf = (assets, role) => {
  const palette = assets?.colors ?? {};
  return Object.prototype.hasOwnProperty.call(palette, role) ? palette[role] : role;
};

function drawShape(ctx, op, assets) {
  const fill = op.fill ? colorOf(assets, op.fill) : null;
  const stroke = op.stroke ? colorOf(assets, op.stroke) : null;
  if (!fill && !stroke) throw new TypeError(`shape ${op.id} needs a fill or a stroke`);
  ctx.beginPath();
  if (op.shape === 'rect') {
    if (typeof ctx.roundRect === 'function' && op.radius > 0) {
      ctx.roundRect(0, 0, op.w, op.h, op.radius);
    } else {
      ctx.rect(0, 0, op.w, op.h);
    }
  } else if (op.shape === 'ellipse') {
    if (typeof ctx.ellipse !== 'function') throw new TypeError('ellipse requires ctx.ellipse()');
    ctx.ellipse(op.w / 2, op.h / 2, op.w / 2, op.h / 2, 0, 0, Math.PI * 2);
  } else {
    ctx.moveTo(0, 0);
    ctx.lineTo(op.w, 0);
  }
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = op.strokeWidth;
    ctx.stroke();
  }
}

function drawPolyline(ctx, op, assets) {
  ctx.beginPath();
  op.points.forEach(([px, py], index) => {
    if (index === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  });
  ctx.strokeStyle = colorOf(assets, op.stroke);
  ctx.lineWidth = op.strokeWidth;
  ctx.stroke();
  if (op.arrow) {
    const [ax, ay] = op.points[op.points.length - 1];
    const [bx, by] = op.points[op.points.length - 2];
    const angle = Math.atan2(ay - by, ax - bx);
    const head = Math.max(10, op.strokeWidth * 3);
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(ax - head * Math.cos(angle - Math.PI / 6), ay - head * Math.sin(angle - Math.PI / 6));
    ctx.moveTo(ax, ay);
    ctx.lineTo(ax - head * Math.cos(angle + Math.PI / 6), ay - head * Math.sin(angle + Math.PI / 6));
    ctx.stroke();
  }
}

function drawBars(ctx, op, assets) {
  const max = Math.max(...op.values.map(Math.abs), 1);
  const slot = op.w / op.values.length;
  const bar = slot * (1 - op.gap);
  ctx.fillStyle = colorOf(assets, op.fill);
  op.values.forEach((value, index) => {
    const height = Math.max(0, (value / max) * op.h);
    ctx.fillRect(index * slot + (slot - bar) / 2, op.h - height, bar, height);
  });
}

/**
 * Paint a sampled frame. `assets.colors` maps brand roles to CSS colours (defaults to the role name)
 * and `assets.images` maps element ids to loaded images for `person`/`image` ops.
 * Returns the number of ops painted.
 */
export function drawBoardFrame(ctx, frame, assets = {}) {
  if (!ctx || typeof ctx.save !== 'function') throw new TypeError('drawBoardFrame requires a Canvas2D context');
  const { width, height } = frame.stage;
  ctx.save();
  ctx.translate(width / 2 + frame.camera.x, height / 2 + frame.camera.y);
  ctx.scale(frame.camera.scale, frame.camera.scale);
  ctx.translate(-width / 2, -height / 2);
  for (const op of frame.ops) {
    ctx.save();
    ctx.globalAlpha = (ctx.globalAlpha ?? 1) * op.alpha;
    ctx.translate(op.x, op.y);
    if (op.rotation) ctx.rotate((op.rotation * Math.PI) / 180);
    if (op.scale !== 1) ctx.scale(op.scale, op.scale);
    if (op.kind === 'text') {
      ctx.font = `${op.size}px ${op.font ?? 'sans-serif'}`;
      ctx.fillStyle = colorOf(assets, op.color);
      ctx.textAlign = op.align === 'center' ? 'center' : op.align === 'left' ? 'left' : 'right';
      if (op.maxWidth) ctx.fillText(op.text, 0, 0, op.maxWidth);
      else ctx.fillText(op.text, 0, 0);
    } else if (op.kind === 'shape') {
      drawShape(ctx, op, assets);
    } else if (op.kind === 'draw') {
      drawPolyline(ctx, op, assets);
    } else if (op.kind === 'data') {
      drawBars(ctx, op, assets);
    } else {
      const image = assets.images?.[op.id];
      if (!image) throw new TypeError(`${op.kind} ${op.id} needs assets.images['${op.id}']`);
      ctx.drawImage(image, -op.w / 2, -op.h, op.w, op.h);
    }
    ctx.restore();
  }
  ctx.restore();
  return frame.ops.length;
}
