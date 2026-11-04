// Phase 2B — deterministic 3D Slide Wall. Kept byte-identical for engines K and R.
// Absolute VO timeline + stable slide ids + shared space3d camera/mesh/projection contracts.
// Rendering adapters supply slide content; this module owns no fonts, DOM text or global time.
import { box, faceNormal, lookCamera, project, rotate, sortedFaces, transform } from './space3d.js';
import { ease } from './motion.js';
import { clampWindowBox, fullscreenBox, resolveBrandRole } from './stage.js';

export const WALL_EASES = Object.freeze(['linear', 'cubicInOut', 'cubicOut', 'quintOut', 'sineInOut', 'expoInOut']);
const EPS = 1e-9;
const finite = (v) => typeof v === 'number' && Number.isFinite(v);
const vec = (v, n, fallback) => Array.isArray(v) && v.length === n && v.every(finite)
  ? v.map(Number) : [...fallback];
const canvasOf = (raw = {}) => ({
  w: finite(raw?.w) ? Math.trunc(raw.w) : 1080,
  h: finite(raw?.h) ? Math.trunc(raw.h) : 1920,
  fps: finite(raw?.fps) ? raw.fps : 30,
});
const endpointKey = (e) => e.type === 'overview' ? 'overview' : `slide:${e.slide}`;

function endpoint(raw, ids, errors, where) {
  if (raw?.type === 'overview') return { type: 'overview' };
  if (raw?.type === 'slide' && ids.has(raw.slide)) return { type: 'slide', slide: raw.slide };
  errors.push(`${where}: expected {type:'overview'} or {type:'slide',slide:<known id>}`);
  return { type: 'overview' };
}

export function slideMesh(slide, depth) {
  const [rx, ry, rz] = slide.rotation;
  return transform(box(slide.size[0], slide.size[1], depth), { rx, ry, rz, move: slide.position });
}

function slideXYAabb(slide, depth) {
  const verts = slideMesh(slide, depth).verts;
  const xs = verts.map((v) => v[0]), ys = verts.map((v) => v[1]);
  return [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
}

/** Return every configuration/timing error without requiring a renderer. */
export function validateSlideWallSpec(input, duration = null) {
  const errors = [];
  if (!input || typeof input !== 'object' || Array.isArray(input)) return ['spec must be an object'];
  if (input.version !== 1) errors.push('version must be 1');
  if (typeof input.id !== 'string' || !input.id.trim()) errors.push('id must be a non-empty stable string');
  if ((input.clock ?? 'vo') !== 'vo') errors.push("clock must be 'vo'; timeline values are absolute VO seconds");
  if (input.canvas != null && (typeof input.canvas !== 'object' || Array.isArray(input.canvas))) {
    errors.push('canvas must be an object');
  }
  const rawCanvas = typeof input.canvas === 'object' && input.canvas ? input.canvas : {};
  [['w', 1080], ['h', 1920], ['fps', 30]].forEach(([key, fallback]) => {
    if (!finite(rawCanvas[key] ?? fallback)) errors.push(`canvas.${key} must be finite`);
  });
  const canvas = canvasOf(rawCanvas);
  if (canvas.w <= 0 || canvas.h <= 0 || canvas.fps <= 0) errors.push('canvas w/h/fps must be finite and positive');
  if (input.camera != null && (typeof input.camera !== 'object' || Array.isArray(input.camera))) {
    errors.push('camera must be an object');
  }
  const cameraInput = input.camera && typeof input.camera === 'object' && !Array.isArray(input.camera) ? input.camera : {};
  if (!finite(cameraInput.fov ?? 30) || (cameraInput.fov ?? 30) < 5 || (cameraInput.fov ?? 30) > 120) {
    errors.push('camera.fov must be finite and within [5,120] degrees');
  }
  if (input.viewport != null) {
    try { clampWindowBox(input.viewport, canvas); } catch (e) { errors.push(e.message); }
  }

  const layout = input.layout && typeof input.layout === 'object' && !Array.isArray(input.layout) ? input.layout : {};
  if (input.layout != null && layout !== input.layout) errors.push('layout must be an object');
  const rawDefaultSize = layout.slideSize ?? [3.2, 2];
  const defaultSize = vec(rawDefaultSize, 2, [3.2, 2]);
  if (!Array.isArray(rawDefaultSize) || rawDefaultSize.length !== 2 || !rawDefaultSize.every(finite)
    || defaultSize.some((v) => v <= 0)) errors.push('layout.slideSize must contain two finite positive values');
  const rawGap = layout.gap ?? [0.4, 0.4];
  const gap = vec(rawGap, 2, [0.4, 0.4]);
  if (!Array.isArray(rawGap) || rawGap.length !== 2 || !rawGap.every(finite) || gap.some((v) => v < 0)) {
    errors.push('layout.gap must contain two finite non-negative values');
  }
  const depth = layout.depth ?? 0.08;
  if (!finite(depth) || depth <= 0) errors.push('layout.depth must be finite and positive');
  if ('preventOverlap' in layout && typeof layout.preventOverlap !== 'boolean') {
    errors.push('layout.preventOverlap must be boolean');
  }
  const columns = layout.gridColumns ?? 3;
  if (!Number.isInteger(columns) || columns <= 0) errors.push('layout.gridColumns must be a positive integer');
  const cols = Number.isInteger(columns) && columns > 0 ? columns : 3;
  const rawOrigin = layout.origin ?? [0, 0, 0];
  const origin = vec(rawOrigin, 3, [0, 0, 0]);
  if (!Array.isArray(rawOrigin) || rawOrigin.length !== 3 || !rawOrigin.every(finite)) {
    errors.push('layout.origin must contain three finite values');
  }
  try { resolveBrandRole(input.backgroundRole ?? 'ink_shadow', 'backgroundRole'); }
  catch (e) { errors.push(e.message); }

  const rawSlides = Array.isArray(input.slides) ? input.slides : [];
  if (!Array.isArray(input.slides) || !input.slides.length) errors.push('slides must be a non-empty array');
  if (rawSlides.length > 64) errors.push('slides supports at most 64 entries per wall');
  const slides = [], ids = new Set(), rows = Math.ceil(rawSlides.length / cols);
  rawSlides.forEach((raw, index) => {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
      errors.push(`slides[${index}] must be an object`);
      return;
    }
    let id = raw.id;
    if (typeof id !== 'string' || !id.trim()) {
      errors.push(`slides[${index}].id must be a non-empty stable string`);
      id = `invalid-${index}`;
    } else if (ids.has(id)) errors.push(`duplicate slide id: ${id}`);
    ids.add(id);
    [['surfaceRole', 'paper'], ['edgeRole', 'gray_2'], ['accentRole', 'red']].forEach(([key, fallback]) => {
      try { resolveBrandRole(raw[key] ?? fallback, `slide ${id}.${key}`); }
      catch (e) { errors.push(e.message); }
    });
    const rawSize = raw.size ?? defaultSize;
    const size = vec(rawSize, 2, defaultSize);
    if (!Array.isArray(rawSize) || rawSize.length !== 2 || !rawSize.every(finite) || size.some((v) => v <= 0)) {
      errors.push(`slide ${id}: size must contain two finite positive values`);
    }
    const row = Math.floor(index / cols), col = index % cols;
    const generated = [
      origin[0] + (col - (cols - 1) / 2) * (defaultSize[0] + gap[0]),
      origin[1] + ((rows - 1) / 2 - row) * (defaultSize[1] + gap[1]), origin[2],
    ];
    if (raw.position != null && (!Array.isArray(raw.position) || raw.position.length !== 3 || !raw.position.every(finite))) {
      errors.push(`slide ${id}: position must contain three finite values`);
    }
    const position = vec(raw.position ?? generated, 3, generated);
    const rotationInput = raw.rotation ?? [0, 0, 0];
    if (!Array.isArray(rotationInput) || rotationInput.length !== 3 || !rotationInput.every(finite)) {
      errors.push(`slide ${id}: rotation must contain three finite radian values`);
    }
    slides.push({
      id, size, position, rotation: vec(rotationInput, 3, [0, 0, 0]),
      surfaceRole: raw.surfaceRole ?? 'paper', edgeRole: raw.edgeRole ?? 'gray_2', accentRole: raw.accentRole ?? 'red',
    });
  });

  if (layout.bounds != null) {
    const b = layout.bounds;
    const valid = b && typeof b === 'object' && vec(b.min, 3, [NaN, NaN, NaN]).every(finite)
      && vec(b.max, 3, [NaN, NaN, NaN]).every(finite);
    if (!valid) errors.push('layout.bounds min/max must contain three finite values');
    else if (b.min.some((v, i) => v >= b.max[i])) errors.push('layout.bounds min must be strictly below max on every axis');
    else {
      slides.forEach((slide) => {
        const outside = slideMesh(slide, finite(depth) && depth > 0 ? depth : 0.08).verts
          .some((v) => v.some((x, i) => x < b.min[i] - EPS || x > b.max[i] + EPS));
        if (outside) errors.push(`slide ${slide.id}: transformed slab leaves layout.bounds`);
      });
    }
  }
  if (layout.preventOverlap ?? true) {
    const overlapDepth = finite(depth) && depth > 0 ? depth : 0.08;
    const footprints = slides.map((slide) => slideXYAabb(slide, overlapDepth));
    for (let i = 0; i < slides.length; i++) for (let j = i + 1; j < slides.length; j++) {
      const a = slides[i], b = slides[j], aa = footprints[i], bb = footprints[j];
      // Conservative transformed-slab XY AABBs include rotation/depth; touching edges are allowed.
      if (aa[0] < bb[1] - EPS && bb[0] < aa[1] - EPS
        && aa[2] < bb[3] - EPS && bb[2] < aa[3] - EPS) {
        errors.push(`slides ${a.id} and ${b.id} overlap in the required XY separation contract`);
      }
    }
  }

  const overview = cameraInput.overview;
  if (overview != null) {
    if (typeof overview !== 'object' || Array.isArray(overview)) errors.push('camera.overview must be an object');
    else {
      [['position', [0, 0, 10]], ['target', [0, 0, 0]], ['up', [0, 1, 0]]].forEach(([key, fallback]) => {
        const value = overview[key] ?? fallback;
        if (!Array.isArray(value) || value.length !== 3 || !value.every(finite)) {
          errors.push(`camera.overview.${key} must contain three finite values`);
        }
      });
      if (!finite(overview.roll ?? 0)) errors.push('camera.overview.roll must be finite radians');
      try {
        lookCamera(vec(overview.position ?? [0, 0, 10], 3, [0, 0, 10]),
          vec(overview.target ?? [0, 0, 0], 3, [0, 0, 0]), cameraInput.fov ?? 30,
          overview.roll ?? 0, vec(overview.up ?? [0, 1, 0], 3, [0, 1, 0]));
      } catch (e) { errors.push(`camera.overview: ${e.message}`); }
    }
  }

  const timeline = Array.isArray(input.timeline) ? input.timeline : [];
  if (!Array.isArray(input.timeline) || !input.timeline.length) errors.push('timeline must be a non-empty array');
  let previousEnd = null, previousKey = null;
  timeline.forEach((raw, index) => {
    const where = `timeline[${index}]`;
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) { errors.push(`${where} must be an object`); return; }
    if (!['overview', 'slide', 'move'].includes(raw.mode)) { errors.push(`${where}.mode must be overview, slide or move`); return; }
    const { start, end } = raw;
    if (!finite(start) || !finite(end) || start < 0 || end <= start) {
      errors.push(`${where} requires finite 0 <= start < end`); return;
    }
    if (index === 0 && Math.abs(start) > EPS) errors.push('timeline must start at absolute VO time 0');
    if (previousEnd != null) {
      if (start < previousEnd - EPS) errors.push(`${where} overlaps the preceding segment`);
      else if (start > previousEnd + EPS) errors.push(`${where} leaves a timing gap after the preceding segment`);
    }
    let currentKey;
    if (raw.mode === 'move') {
      const from = endpoint(raw.from, ids, errors, `${where}.from`);
      const to = endpoint(raw.to, ids, errors, `${where}.to`);
      if (endpointKey(from) === endpointKey(to)) errors.push(`${where} must move between two different endpoints`);
      if (!WALL_EASES.includes(raw.ease ?? 'cubicInOut')) errors.push(`${where}.ease must be one of ${WALL_EASES.join(',')}`);
      if (!finite(raw.lift ?? 0) || (raw.lift ?? 0) < 0) errors.push(`${where}.lift must be finite and non-negative`);
      currentKey = endpointKey(to);
      if (previousKey != null && endpointKey(from) !== previousKey) {
        errors.push(`${where}.from must equal the preceding segment endpoint (${previousKey})`);
      }
    } else {
      if (raw.mode === 'slide' && !ids.has(raw.slide)) {
        errors.push(`${where}.slide must reference a known slide id`);
        currentKey = 'overview';
      } else currentKey = raw.mode === 'overview' ? 'overview' : `slide:${raw.slide}`;
      if (previousKey != null && currentKey !== previousKey) {
        errors.push(`${where} must start at the preceding segment endpoint (${previousKey})`);
      }
    }
    previousEnd = end;
    previousKey = currentKey;
  });
  if (duration != null) {
    if (!finite(duration) || duration <= 0) errors.push('duration must be finite and positive');
    else if (timeline.length && previousEnd != null && Math.abs(previousEnd - duration) > EPS) {
      errors.push(`timeline end ${previousEnd} must equal scene/VO duration ${duration}`);
    }
  }
  return errors;
}

export function normalizeSlideWall(input) {
  if (input?._normalized) return input;
  const errors = validateSlideWallSpec(input);
  if (errors.length) throw new Error(`Invalid slide-wall spec:\n - ${errors.join('\n - ')}`);
  const canvas = canvasOf(input.canvas);
  const viewport = clampWindowBox(input.viewport ?? fullscreenBox(canvas), canvas);
  const layout = input.layout ?? {}, defaultSize = (layout.slideSize ?? [3.2, 2]).map(Number);
  const gap = (layout.gap ?? [0.4, 0.4]).map(Number), columns = layout.gridColumns ?? 3;
  const origin = (layout.origin ?? [0, 0, 0]).map(Number), rows = Math.ceil(input.slides.length / columns);
  const slides = input.slides.map((raw, index) => {
    const row = Math.floor(index / columns), col = index % columns;
    const generated = [
      origin[0] + (col - (columns - 1) / 2) * (defaultSize[0] + gap[0]),
      origin[1] + ((rows - 1) / 2 - row) * (defaultSize[1] + gap[1]), origin[2],
    ];
    return {
      id: raw.id, size: (raw.size ?? defaultSize).map(Number), position: (raw.position ?? generated).map(Number),
      rotation: (raw.rotation ?? [0, 0, 0]).map(Number), surfaceRole: resolveBrandRole(raw.surfaceRole ?? 'paper'),
      edgeRole: resolveBrandRole(raw.edgeRole ?? 'gray_2'), accentRole: resolveBrandRole(raw.accentRole ?? 'red'),
    };
  });
  const timeline = input.timeline.map((raw) => {
    const segment = { mode: raw.mode, start: raw.start, end: raw.end };
    if (raw.mode === 'move') Object.assign(segment, {
      from: { ...raw.from }, to: { ...raw.to }, ease: raw.ease ?? 'cubicInOut', lift: raw.lift ?? 0,
    });
    else if (raw.mode === 'slide') segment.slide = raw.slide;
    return segment;
  });
  return {
    version: 1, id: input.id, clock: 'vo', _normalized: true, canvas, viewport,
    backgroundRole: resolveBrandRole(input.backgroundRole ?? 'ink_shadow'),
    layout: {
      slideSize: defaultSize, gap, gridColumns: columns, origin, depth: layout.depth ?? 0.08,
      preventOverlap: layout.preventOverlap ?? true, bounds: layout.bounds ?? null,
    },
    slides, slideById: new Map(slides.map((slide) => [slide.id, slide])),
    camera: { fov: input.camera?.fov ?? 30, overview: input.camera?.overview ? { ...input.camera.overview } : null },
    timeline,
  };
}

const windowOf = (spec, viewport) => clampWindowBox(viewport ?? spec.viewport, spec.canvas);

function overviewState(spec, viewport) {
  const custom = spec.camera.overview;
  if (custom) return {
    position: vec(custom.position ?? [0, 0, 10], 3, [0, 0, 10]),
    target: vec(custom.target ?? [0, 0, 0], 3, [0, 0, 0]),
    up: vec(custom.up ?? [0, 1, 0], 3, [0, 1, 0]), roll: custom.roll ?? 0,
  };
  const verts = spec.slides.flatMap((slide) => slideMesh(slide, spec.layout.depth).verts);
  const lo = [0, 1, 2].map((i) => Math.min(...verts.map((v) => v[i])));
  const hi = [0, 1, 2].map((i) => Math.max(...verts.map((v) => v[i])));
  const center = lo.map((v, i) => (v + hi[i]) / 2);
  const tanHalf = Math.tan(spec.camera.fov * Math.PI / 360);
  const distance = Math.max(
    (hi[0] - lo[0]) * spec.canvas.h / (2 * viewport.w * tanHalf),
    (hi[1] - lo[1]) * spec.canvas.h / (2 * viewport.h * tanHalf),
  ) * 1.15 + Math.max(0, center[2] - lo[2]) + spec.layout.depth;
  return { position: [center[0], center[1], center[2] + distance], target: center, up: [0, 1, 0], roll: 0 };
}

function focusState(spec, slideId, viewport) {
  const slide = spec.slideById.get(slideId), rotation = slide.rotation;
  const right = rotate([1, 0, 0], ...rotation), up = rotate([0, 1, 0], ...rotation);
  const normal = rotate([0, 0, 1], ...rotation);
  const frontCenter = slide.position.map((v, i) => v + normal[i] * spec.layout.depth / 2);
  const [w, h] = slide.size, { w: W, h: H } = spec.canvas;
  const tanHalf = Math.tan(spec.camera.fov * Math.PI / 360);
  const distance = Math.max(w * H / (2 * viewport.w * tanHalf), h * H / (2 * viewport.h * tanHalf));
  const focal = (H / 2) / tanHalf;
  const vx = viewport.x + viewport.w / 2, vy = viewport.y + viewport.h / 2;
  const position = frontCenter.map((v, i) => v + normal[i] * distance
    + right[i] * ((W / 2 - vx) * distance / focal) + up[i] * ((vy - H / 2) * distance / focal));
  return { position, target: position.map((v, i) => v - normal[i] * distance), up, roll: 0 };
}

const endpointState = (spec, endpoint, viewport) => endpoint.type === 'overview'
  ? overviewState(spec, viewport) : focusState(spec, endpoint.slide, viewport);

function segmentAt(spec, t) {
  const index = spec.timeline.findIndex((s) => s.start - EPS <= t && t <= s.end + EPS);
  if (index >= 0) return [index, spec.timeline[index]];
  return t < spec.timeline[0].start ? [0, spec.timeline[0]]
    : [spec.timeline.length - 1, spec.timeline.at(-1)];
}

function cameraQuaternion(camera) {
  // Right-handed matrix columns are right, up and back=-forward.
  const r = camera.right, u = camera.up, b = camera.fwd.map((v) => -v);
  const m00 = r[0], m01 = u[0], m02 = b[0];
  const m10 = r[1], m11 = u[1], m12 = b[1];
  const m20 = r[2], m21 = u[2], m22 = b[2];
  const trace = m00 + m11 + m22;
  let q;
  if (trace > 0) {
    const s = Math.sqrt(trace + 1) * 2;
    q = [s / 4, (m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s];
  } else if (m00 > m11 && m00 > m22) {
    const s = Math.sqrt(1 + m00 - m11 - m22) * 2;
    q = [(m21 - m12) / s, s / 4, (m01 + m10) / s, (m02 + m20) / s];
  } else if (m11 > m22) {
    const s = Math.sqrt(1 + m11 - m00 - m22) * 2;
    q = [(m02 - m20) / s, (m01 + m10) / s, s / 4, (m12 + m21) / s];
  } else {
    const s = Math.sqrt(1 + m22 - m00 - m11) * 2;
    q = [(m10 - m01) / s, (m02 + m20) / s, (m12 + m21) / s, s / 4];
  }
  const length = Math.sqrt(q.reduce((sum, v) => sum + v * v, 0));
  return q.map((v) => v / length);
}

function quaternionSlerp(a, b, t) {
  let dot = a.reduce((sum, v, i) => sum + v * b[i], 0);
  if (dot < 0) { b = b.map((v) => -v); dot = -dot; }
  dot = Math.max(-1, Math.min(1, dot));
  let q;
  if (dot > 0.9995) q = a.map((v, i) => v + (b[i] - v) * t);
  else {
    const theta = Math.acos(dot), sinTheta = Math.sin(theta);
    const wa = Math.sin((1 - t) * theta) / sinTheta, wb = Math.sin(t * theta) / sinTheta;
    q = a.map((v, i) => wa * v + wb * b[i]);
  }
  const length = Math.sqrt(q.reduce((sum, v) => sum + v * v, 0));
  return q.map((v) => v / length);
}

function quaternionRotate(q, v) {
  const [w, x, y, z] = q;
  const t = [2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])];
  return [
    v[0] + w * t[0] + y * t[2] - z * t[1],
    v[1] + w * t[1] + z * t[0] - x * t[2],
    v[2] + w * t[2] + x * t[1] - y * t[0],
  ];
}

function interpolateCamera(from, to, progress, fov) {
  // Keep near-aligned legacy moves; SLERP larger orientations independently of position/target.
  const fromCamera = lookCamera(from.position, from.target, fov, 0, from.up);
  const toCamera = lookCamera(to.position, to.target, fov, 0, to.up);
  const fromQ = cameraQuaternion(fromCamera), toQ = cameraQuaternion(toCamera);
  const deltaRoll = Math.atan2(Math.sin(to.roll - from.roll), Math.cos(to.roll - from.roll));
  const roll = from.roll + deltaRoll * progress;
  const alignment = Math.abs(fromQ.reduce((sum, v, i) => sum + v * toQ[i], 0));
  if (alignment > 0.9995) {
    const state = {};
    ['position', 'target', 'up'].forEach((key) => {
      state[key] = from[key].map((v, i) => v + (to[key][i] - v) * progress);
    });
    return lookCamera(state.position, state.target, fov, roll, state.up);
  }
  const q = quaternionSlerp(fromQ, toQ, progress);
  let right = quaternionRotate(q, [1, 0, 0]), up = quaternionRotate(q, [0, 1, 0]);
  const back = quaternionRotate(q, [0, 0, 1]);
  if (roll) {
    const c = Math.cos(roll), s = Math.sin(roll);
    const nextRight = right.map((v, i) => v * c + up[i] * s);
    const nextUp = right.map((v, i) => -v * s + up[i] * c);
    right = nextRight;
    up = nextUp;
  }
  return {
    pos: from.position.map((v, i) => v + (to.position[i] - v) * progress),
    fwd: back.map((v) => -v), right, up, fov: fov * Math.PI / 180,
    target: from.target.map((v, i) => v + (to.target[i] - v) * progress), roll,
  };
}

function cameraAt(spec, t, motionMode, viewport) {
  const [index, segment] = segmentAt(spec, t);
  let state, camera = null, progress = 0;
  if (segment.mode === 'overview') state = overviewState(spec, viewport);
  else if (segment.mode === 'slide') state = focusState(spec, segment.slide, viewport);
  else {
    const raw = Math.max(0, Math.min(1, (t - segment.start) / (segment.end - segment.start)));
    const from = endpointState(spec, segment.from, viewport), to = endpointState(spec, segment.to, viewport);
    if (motionMode === 'reduced') { state = to; progress = 1; }
    else if (raw <= 0) state = from;
    else if (raw >= 1) { state = to; progress = 1; }
    else {
      progress = ease(segment.ease, raw);
      camera = interpolateCamera(from, to, progress, spec.camera.fov);
      camera.pos[2] += Math.sin(Math.PI * raw) * segment.lift;
    }
  }
  if (!camera) camera = lookCamera(state.position, state.target, spec.camera.fov, state.roll, state.up);
  return [camera, index, segment.mode, progress];
}

/** Pure absolute-time evaluation: camera + sorted projected slides, with no global state. */
export function slideWallStateAt(input, t, { motionMode = 'normal', viewport = null } = {}) {
  if (!finite(t)) throw new Error('slide-wall time must be finite');
  if (!['normal', 'reduced'].includes(motionMode)) throw new Error("motionMode must be 'normal' or 'reduced'");
  const spec = normalizeSlideWall(input), win = windowOf(spec, viewport);
  const [camera, segmentIndex, mode, progress] = cameraAt(spec, t, motionMode, win);
  const slides = spec.slides.map((slide) => {
    const wallMesh = slideMesh(slide, spec.layout.depth);
    const projected = project(wallMesh.verts, camera, spec.canvas.w, spec.canvas.h);
    const front = [3, 2, 1, 0].map((i) => projected[i]); // texture TL, TR, BR, BL
    const normal = faceNormal(wallMesh, wallMesh.faces[0]);
    const toCamera = camera.pos.map((v, i) => v - slide.position[i]);
    const facing = normal.reduce((sum, v, i) => sum + v * toCamera[i], 0);
    const visible = facing > 0.001 && front.every((p) => p.every(finite) && p[2] > 0);
    const depth = project([slide.position], camera, spec.canvas.w, spec.canvas.h)[0][2];
    const xs = front.map((p) => p[0]), ys = front.map((p) => p[1]);
    const faces = sortedFaces(wallMesh, camera).map(([faceDepth, role, idx]) => {
      const faceNormalVector = faceNormal(wallMesh, [idx, role]);
      const center = [0, 1, 2].map((axis) => idx.reduce((sum, i) => sum + wallMesh.verts[i][axis], 0) / idx.length);
      const towardCamera = camera.pos.map((v, axis) => v - center[axis]);
      const cull = faceNormalVector.reduce((sum, v, axis) => sum + v * towardCamera[axis], 0) <= 0;
      return { role, idx, depth: faceDepth, cull, points: idx.map((index) => projected[index]) };
    });
    return {
      slide, mesh: wallMesh, projected, front, visible, depth, faces,
      aabb: visible ? { x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) } : null,
    };
  }).sort((a, b) => b.depth - a.depth);
  return { time: t, camera, segmentIndex, mode, progress, viewport: win, slides };
}

/** Map texture pixels (TL,TR,BR,BL) to a projected quad; P warps and R CSS share this equation. */
export function slideHomography(srcW, srcH, quad) {
  const [[x0, y0], [x1, y1], [x2, y2], [x3, y3]] = quad.map((p) => [p[0], p[1]]);
  const dx1 = x1 - x2, dx2 = x3 - x2, dx3 = x0 - x1 + x2 - x3;
  const dy1 = y1 - y2, dy2 = y3 - y2, dy3 = y0 - y1 + y2 - y3;
  const den = dx1 * dy2 - dx2 * dy1;
  const g = Math.abs(den) > EPS ? (dx3 * dy2 - dx2 * dy3) / den : 0;
  const h = Math.abs(den) > EPS ? (dx1 * dy3 - dx3 * dy1) / den : 0;
  const a = x1 - x0 + g * x1, b = x3 - x0 + h * x3, c = x0;
  const d = y1 - y0 + g * y1, e = y3 - y0 + h * y3, f = y0;
  return [[a / srcW, b / srcH, c], [d / srcW, e / srcH, f], [g / srcW, h / srcH, 1]];
}

/** Strict fetch + validation for K. R receives imported plan JSON through its data module. */
export async function loadSlideWall(url = '/plan/slide-wall.json') {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) {
    if (response.status === 404) return null;
    throw new Error(`Cannot load ${url}: HTTP ${response.status}`);
  }
  const text = await response.text();
  let spec;
  try { spec = JSON.parse(text); } catch (e) { throw new Error(`Invalid JSON in ${url}: ${e.message}`); }
  return normalizeSlideWall(spec);
}

export { resolveBrandRole };
