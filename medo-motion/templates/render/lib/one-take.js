// Phase 2C — deterministic One-Take semantic states inside the existing P/K/R scene architecture.
// Absolute VO time + continuous 2D camera/element transforms + optional cursor/click narrative.
// This module owns no fonts, DOM, Canvas, accumulated state, wall-clock time or external dependency.
import { ease, lerp } from './motion.js';
import { clampWindowBox, fullscreenBox, resolveBrandRole } from './stage.js';
import { TEXT_ROLES } from './text-direction.js';

export const ONE_TAKE_EASES = Object.freeze(['linear', 'cubicInOut', 'cubicOut', 'quintOut', 'sineInOut', 'expoInOut']);
export const ONE_TAKE_KINDS = Object.freeze(['rect', 'circle', 'text']);
const FONT_ROLES = new Set(TEXT_ROLES);
const EPS = 1e-9;
const finite = (v) => typeof v === 'number' && Number.isFinite(v);
const object = (v) => v && typeof v === 'object' && !Array.isArray(v);
const field = (source, key, fallback) => Object.prototype.hasOwnProperty.call(source, key) ? source[key] : fallback;
const clamp01 = (v) => Math.max(0, Math.min(1, v));
const defaultTransform = () => ({ x: 0, y: 0, scale: 1, rotation: 0, opacity: 1 });
const normalizedOneTakes = new WeakSet();

function canvasOf(raw, errors) {
  const value = raw === undefined ? {} : raw;
  if (!object(value)) errors.push('canvas must be an object');
  const source = object(value) ? value : {};
  const out = {};
  [['w', 1080], ['h', 1920], ['fps', 30]].forEach(([key, fallback]) => {
    const v = field(source, key, fallback);
    if (!finite(v) || !Number.isInteger(v) || v <= 0) errors.push(`canvas.${key} must be a positive integer`);
    out[key] = finite(v) && Number.isInteger(v) && v > 0 ? v : fallback;
  });
  return out;
}

function roleOf(value, fallback, label, errors) {
  try { return resolveBrandRole(value, label); }
  catch (error) { errors.push(error.message); return fallback; }
}

function transformOf(raw, previous, where, errors) {
  if (raw !== undefined && !object(raw)) errors.push(`${where} must be an object`);
  const source = object(raw) ? raw : {};
  const out = {};
  ['x', 'y', 'scale', 'rotation', 'opacity'].forEach((key) => {
    const value = field(source, key, previous[key]);
    if (!finite(value)) errors.push(`${where}.${key} must be finite`);
    out[key] = finite(value) ? value : previous[key];
  });
  if (out.scale <= 0) { errors.push(`${where}.scale must be positive`); out.scale = previous.scale; }
  if (out.opacity < 0 || out.opacity > 1) {
    errors.push(`${where}.opacity must be within [0,1]`);
    out.opacity = previous.opacity;
  }
  return out;
}

function parseOneTake(input, externalDuration = null) {
  const errors = [];
  if (!object(input)) return { errors: ['one-take spec must be an object'], spec: null };
  if (input.version !== 1) errors.push('version must be 1');
  if (typeof input.id !== 'string' || !input.id.trim()) errors.push('id must be a non-empty stable string');
  if (field(input, 'clock', 'vo') !== 'vo') errors.push("clock must be 'vo'; state and interaction times are absolute VO seconds");
  const duration = input.duration;
  if (!finite(duration) || duration <= 0) errors.push('duration must be finite and positive');
  const sceneDuration = finite(duration) && duration > 0 ? duration : 1;
  if (externalDuration != null && (!finite(externalDuration) || externalDuration <= 0)) {
    errors.push('external duration must be finite and positive');
  } else if (externalDuration != null && Math.abs(externalDuration - sceneDuration) > EPS) {
    errors.push(`duration ${sceneDuration} must equal scene/VO duration ${externalDuration}`);
  }
  const canvas = canvasOf(input.canvas, errors);
  const backgroundRole = roleOf(field(input, 'backgroundRole', 'ink_shadow'), 'ink_shadow', 'backgroundRole', errors);

  const rawElements = Array.isArray(input.elements) ? input.elements : [];
  if (!Array.isArray(input.elements) || !rawElements.length) errors.push('elements must be a non-empty array');
  if (rawElements.length > 64) errors.push('elements supports at most 64 entries');
  const elements = [], elementIds = new Set();
  rawElements.forEach((raw, index) => {
    const where = `elements[${index}]`;
    if (!object(raw)) { errors.push(`${where} must be an object`); return; }
    let id = raw.id;
    if (typeof id !== 'string' || !id.trim()) { errors.push(`${where}.id must be non-empty`); id = `invalid-${index}`; }
    else if (elementIds.has(id)) errors.push(`duplicate element id: ${id}`);
    elementIds.add(id);
    if (!ONE_TAKE_KINDS.includes(raw.kind)) errors.push(`element ${id}: kind must be rect, circle or text`);
    const kind = ONE_TAKE_KINDS.includes(raw.kind) ? raw.kind : 'rect';
    const w = raw.w, h = raw.h;
    if (!finite(w) || w <= 0 || !finite(h) || h <= 0) errors.push(`element ${id}: w/h must be finite and positive`);
    const radius = field(raw, 'radius', 0), strokeWidth = field(raw, 'strokeWidth', 0);
    if (!finite(radius) || radius < 0) errors.push(`element ${id}: radius must be finite and non-negative`);
    if (!finite(strokeWidth) || strokeWidth < 0) errors.push(`element ${id}: strokeWidth must be finite and non-negative`);
    const element = {
      id, kind,
      w: finite(w) && w > 0 ? w : 100, h: finite(h) && h > 0 ? h : 100,
      radius: finite(radius) && radius >= 0 ? radius : 0,
      role: roleOf(field(raw, 'role', 'paper'), 'paper', `element ${id}.role`, errors),
      accentRole: roleOf(field(raw, 'accentRole', 'red'), 'red', `element ${id}.accentRole`, errors),
      strokeRole: roleOf(field(raw, 'strokeRole', 'gray_2'), 'gray_2', `element ${id}.strokeRole`, errors),
      strokeWidth: finite(strokeWidth) && strokeWidth >= 0 ? strokeWidth : 0,
    };
    if (kind === 'text') {
      if (typeof raw.text !== 'string' || !raw.text.trim()) errors.push(`element ${id}: text must be a non-empty string`);
      const fontSize = field(raw, 'fontSize', 48), scene = field(raw, 'scene', 1), fontRole = field(raw, 'fontRole', 'body');
      if (!finite(fontSize) || fontSize <= 0) errors.push(`element ${id}: fontSize must be finite and positive`);
      if (!Number.isInteger(scene) || scene <= 0) errors.push(`element ${id}: scene must be a positive integer`);
      if (!FONT_ROLES.has(fontRole)) errors.push(`element ${id}: unknown fontRole ${fontRole}`);
      if ('rtl' in raw && typeof raw.rtl !== 'boolean') errors.push(`element ${id}: rtl must be boolean`);
      Object.assign(element, {
        text: typeof raw.text === 'string' ? raw.text : '', fontSize: finite(fontSize) && fontSize > 0 ? fontSize : 48,
        scene: Number.isInteger(scene) && scene > 0 ? scene : 1, fontRole, rtl: field(raw, 'rtl', true),
      });
    }
    elements.push(element);
  });

  const rawStates = Array.isArray(input.states) ? input.states : [];
  if (!Array.isArray(input.states) || rawStates.length < 2) errors.push('states must contain at least two semantic states');
  if (rawStates.length > 16) errors.push('states supports at most 16 entries');
  const states = [], stateIds = new Set();
  let previousTransforms = Object.fromEntries(elements.map((element) => [element.id, defaultTransform()]));
  let previousTime = -Infinity;
  rawStates.forEach((raw, index) => {
    const where = `states[${index}]`;
    if (!object(raw)) { errors.push(`${where} must be an object`); return; }
    let id = raw.id;
    if (typeof id !== 'string' || !id.trim()) { errors.push(`${where}.id must be non-empty`); id = `invalid-${index}`; }
    else if (stateIds.has(id)) errors.push(`duplicate state id: ${id}`);
    stateIds.add(id);
    const time = raw.time;
    if (!finite(time)) errors.push(`${where}.time must be finite`);
    const at = finite(time) ? time : previousTime + 1;
    if (index === 0 && Math.abs(at) > EPS) errors.push('states must start at absolute VO time 0');
    if (at <= previousTime + EPS) errors.push(`${where}.time must be strictly increasing`);
    if (index === rawStates.length - 1 && Math.abs(at - sceneDuration) > EPS) {
      errors.push(`last state time ${at} must equal duration ${sceneDuration}`);
    }
    previousTime = at;
    const easeName = field(raw, 'ease', 'cubicInOut');
    if (!ONE_TAKE_EASES.includes(easeName)) errors.push(`${where}.ease must be one of ${ONE_TAKE_EASES.join(',')}`);
    if (!object(raw.camera)) errors.push(`${where}.camera must be an object`);
    const cameraRaw = object(raw.camera) ? raw.camera : {};
    const camera = {};
    ['x', 'y', 'zoom'].forEach((key) => {
      const value = cameraRaw[key];
      if (!finite(value)) errors.push(`${where}.camera.${key} must be finite`);
      camera[key] = finite(value) ? value : key === 'zoom' ? 1 : canvas[key === 'x' ? 'w' : 'h'] / 2;
    });
    if (camera.zoom <= 0) { errors.push(`${where}.camera.zoom must be positive`); camera.zoom = 1; }
    if (raw.elements !== undefined && !object(raw.elements)) errors.push(`${where}.elements must be an object`);
    const patches = object(raw.elements) ? raw.elements : {};
    Object.keys(patches).forEach((idValue) => {
      if (!elementIds.has(idValue)) errors.push(`${where}.elements references unknown element ${idValue}`);
    });
    const transforms = {};
    elements.forEach((element) => {
      transforms[element.id] = transformOf(
        patches[element.id], previousTransforms[element.id] ?? defaultTransform(),
        `${where}.elements.${element.id}`, errors,
      );
    });
    states.push({ id, time: at, ease: easeName, camera, elements: transforms });
    previousTransforms = transforms;
  });

  let cursor = null;
  if (input.cursor != null) {
    const raw = input.cursor;
    if (!object(raw)) errors.push('cursor must be an object');
    const source = object(raw) ? raw : {};
    const size = field(source, 'size', 42), opacity = field(source, 'opacity', 1);
    if (!finite(size) || size <= 0) errors.push('cursor.size must be finite and positive');
    if (!finite(opacity) || opacity < 0 || opacity > 1) errors.push('cursor.opacity must be within [0,1]');
    const rawPoints = Array.isArray(source.points) ? source.points : [];
    if (!rawPoints.length) errors.push('cursor.points must be a non-empty array');
    const points = [];
    let pointTime = -Infinity;
    rawPoints.forEach((point, index) => {
      const where = `cursor.points[${index}]`;
      if (!object(point)) { errors.push(`${where} must be an object`); return; }
      if (!finite(point.time) || !finite(point.x) || !finite(point.y)) {
        errors.push(`${where} requires finite time/x/y`); return;
      }
      if (point.time < 0 || point.time > sceneDuration) errors.push(`${where}.time must stay inside the scene`);
      if (point.time <= pointTime + EPS) errors.push(`${where}.time must be strictly increasing`);
      pointTime = point.time;
      const easeName = field(point, 'ease', 'cubicInOut');
      if (!ONE_TAKE_EASES.includes(easeName)) errors.push(`${where}.ease is invalid`);
      points.push({ time: point.time, x: point.x, y: point.y, ease: easeName });
    });
    if (source.clicks !== undefined && !Array.isArray(source.clicks)) errors.push('cursor.clicks must be an array when provided');
    const rawClicks = Array.isArray(source.clicks) ? source.clicks : [];
    const clicks = [];
    let previousClickEnd = -Infinity;
    rawClicks.forEach((click, index) => {
      const where = `cursor.clicks[${index}]`;
      if (!object(click)) { errors.push(`${where} must be an object`); return; }
      const clickDuration = field(click, 'duration', 0.36);
      if (!finite(click.time) || click.time < 0 || click.time >= sceneDuration) {
        errors.push(`${where}.time must be finite and inside [0,duration)`);
      }
      if (!finite(clickDuration) || clickDuration <= 0) errors.push(`${where}.duration must be finite and positive`);
      if (finite(click.time) && finite(clickDuration) && click.time + clickDuration > sceneDuration + EPS) {
        errors.push(`${where} must finish inside the scene`);
      }
      if (finite(click.time) && click.time < previousClickEnd - EPS) {
        errors.push('cursor.clicks must be ordered and non-overlapping');
      }
      if (finite(click.time)) {
        previousClickEnd = click.time + (finite(clickDuration) && clickDuration > 0 ? clickDuration : 0.36);
        clicks.push({ time: click.time, duration: finite(clickDuration) && clickDuration > 0 ? clickDuration : 0.36 });
      }
    });
    cursor = {
      size: finite(size) && size > 0 ? size : 42, opacity: finite(opacity) ? clamp01(opacity) : 1,
      points, clicks,
    };
  }

  if (input.viewport != null) {
    try { clampWindowBox(input.viewport, canvas); } catch (error) { errors.push(error.message); }
  }
  const spec = {
    version: 1, id: input.id, clock: 'vo', duration: sceneDuration, canvas,
    backgroundRole, elements, states, cursor,
    viewport: (() => {
      try { return clampWindowBox(input.viewport ?? fullscreenBox(canvas), canvas); }
      catch { return fullscreenBox(canvas); }
    })(),
  };
  return { errors, spec };
}

export function validateOneTakeSpec(input, duration = null) {
  return parseOneTake(input, duration).errors;
}

export function normalizeOneTake(input) {
  // Only objects produced by this module skip parsing; a JSON `_normalized` field grants no trust.
  if (object(input) && normalizedOneTakes.has(input)) return input;
  const { errors, spec } = parseOneTake(input);
  if (errors.length) throw new Error(`Invalid one-take spec:\n - ${errors.join('\n - ')}`);
  normalizedOneTakes.add(spec);
  return spec;
}

function pointAt(points, time, motionMode) {
  if (time <= points[0].time) return { x: points[0].x, y: points[0].y };
  for (let index = 0; index < points.length - 1; index++) {
    const a = points[index], b = points[index + 1];
    if (time <= b.time + EPS) {
      const raw = clamp01((time - a.time) / (b.time - a.time));
      const progress = motionMode === 'reduced' ? 1 : ease(b.ease, raw);
      return { x: lerp(a.x, b.x, progress), y: lerp(a.y, b.y, progress) };
    }
  }
  const last = points.at(-1);
  return { x: last.x, y: last.y };
}

function screenPoint(point, camera, viewport) {
  return {
    x: viewport.x + viewport.w / 2 + (point.x - camera.x) * camera.zoom,
    y: viewport.y + viewport.h / 2 + (point.y - camera.y) * camera.zoom,
  };
}

function aabbOf(element, screen) {
  const angle = screen.rotation * Math.PI / 180;
  const c = Math.abs(Math.cos(angle)), s = Math.abs(Math.sin(angle));
  const w = (element.w * c + element.h * s) * screen.scale;
  const h = (element.w * s + element.h * c) * screen.scale;
  return { x: screen.x - w / 2, y: screen.y - h / 2, w, h };
}

/** Pure absolute-time evaluation; repeated and reverse-order seeks return the same state. */
export function oneTakeStateAt(input, time, { motionMode = 'normal', viewport = null } = {}) {
  if (!finite(time)) throw new Error('one-take time must be finite');
  if (!['normal', 'reduced'].includes(motionMode)) throw new Error("motionMode must be 'normal' or 'reduced'");
  const spec = normalizeOneTake(input);
  const win = clampWindowBox(viewport ?? spec.viewport, spec.canvas);
  const t = Math.max(0, Math.min(spec.duration, time));
  let index = spec.states.length - 2;
  for (let i = 0; i < spec.states.length - 1; i++) {
    if (t <= spec.states[i + 1].time + EPS) { index = i; break; }
  }
  const from = spec.states[index], to = spec.states[index + 1];
  const rawProgress = clamp01((t - from.time) / (to.time - from.time));
  const progress = motionMode === 'reduced' ? 1 : ease(to.ease, rawProgress);
  const camera = {
    x: lerp(from.camera.x, to.camera.x, progress), y: lerp(from.camera.y, to.camera.y, progress),
    zoom: Math.exp(lerp(Math.log(from.camera.zoom), Math.log(to.camera.zoom), progress)),
  };
  const elements = spec.elements.map((element) => {
    const a = from.elements[element.id], b = to.elements[element.id];
    const transform = {};
    ['x', 'y', 'scale', 'rotation', 'opacity'].forEach((key) => { transform[key] = lerp(a[key], b[key], progress); });
    const point = screenPoint(transform, camera, win);
    const screen = { ...point, scale: transform.scale * camera.zoom, rotation: transform.rotation };
    return { ...element, ...transform, screen, aabb: aabbOf(element, screen) };
  });
  let cursor = null;
  if (spec.cursor?.points.length) {
    const point = pointAt(spec.cursor.points, t, motionMode);
    let press = false, click = null;
    if (motionMode !== 'reduced') {
      spec.cursor.clicks.forEach((event, clickIndex) => {
        if (t >= event.time && t < event.time + event.duration) {
          const clickProgress = (t - event.time) / event.duration;
          press = t - event.time < Math.min(0.14, event.duration / 2);
          const anchor = pointAt(spec.cursor.points, event.time, 'normal');
          click = {
            index: clickIndex, progress: clickProgress, opacity: 1 - clickProgress,
            screen: screenPoint(anchor, camera, win),
          };
        }
      });
    }
    cursor = { ...point, screen: screenPoint(point, camera, win), press, click };
  }
  return {
    time: t, segmentIndex: index, fromState: from.id, toState: to.id, rawProgress, progress,
    camera, viewport: win, elements, cursor,
  };
}

/** Strict fetch + validation for K. R imports the same plan through its data module. */
export async function loadOneTake(url = '/plan/one-take.json') {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) {
    if (response.status === 404) return null;
    throw new Error(`Cannot load ${url}: HTTP ${response.status}`);
  }
  const text = await response.text();
  let spec;
  try { spec = JSON.parse(text); } catch (error) { throw new Error(`Invalid JSON in ${url}: ${error.message}`); }
  return normalizeOneTake(spec);
}
