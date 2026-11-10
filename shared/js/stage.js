// Shared Fixed Stage geometry & contract core for Engine K (Canvas2D) and Engine R (Remotion).
// Byte-identical across `render/lib/stage.js` and `remotion/src/lib/stage.js`.
// Strictly pure `f(t)` under the authoritative VO Clock; locked `brand.json` v2.6 palette only.

export const PALETTE_HEX = Object.freeze({
  red: '#CB271B',
  red_bright: '#CB0801',
  red_deep: '#9F0803',
  ink: '#0A0A0A',
  ink_soft: '#71717A',
  paper: '#F3F2F1',
  gray_1: '#D8D7D5',
  gray_2: '#C9C5C2',
  gray_3: '#BFBAB7',
  gray_4: '#A3A2A0',
  salmon: '#D97F68',
  blush: '#D5AEA6',
  ink_shadow: '#030303',
});

export const ROLE_ALIASES = Object.freeze({
  red: 'red',
  red_bright: 'red_bright',
  redBright: 'red_bright',
  red_deep: 'red_deep',
  redDeep: 'red_deep',
  ink: 'ink',
  ink_soft: 'ink_soft',
  inkSoft: 'ink_soft',
  paper: 'paper',
  gray_1: 'gray_1',
  gray1: 'gray_1',
  gray_2: 'gray_2',
  gray2: 'gray_2',
  gray_3: 'gray_3',
  gray3: 'gray_3',
  gray_4: 'gray_4',
  gray4: 'gray_4',
  salmon: 'salmon',
  blush: 'blush',
  ink_shadow: 'ink_shadow',
  inkShadow: 'ink_shadow',
});

export const DEFAULT_CANVAS = Object.freeze({ w: 1080, h: 1920, fps: 30 });
export const DEFAULT_FRAMED_BOX = Object.freeze({ x: 56, y: 224, w: 968, h: 1096, r: 36 });

export const BACKGROUND_IDS = Object.freeze([
  'iso-grid', 'grid-2d', 'paper', 'aura', 'orbital', 'orbit-mono',
  'frames', 'organic', 'perspective', 'glyphs', 'pulse', 'wash',
]);

const STAGE_EASES = new Set(['linear', 'cubicOut', 'cubicInOut', 'quintOut', 'quadInOut']);
const FORBIDDEN_BRANDING_KEYS = [
  'logo',
  'channelName',
  'channel_name',
  'seriesName',
  'series_name',
  'watermark',
  'permanentTitle',
  'permanent_title',
];
const VALID_TEXT_ROLES = new Set([
  'caption', 'hook', 'title', 'body', 'keyword', 'cta', 'label', 'number', 'ui', 'quote', 'hud',
]);

/** @param {unknown} v */
function isFiniteNum(v) {
  return typeof v === 'number' && Number.isFinite(v);
}

/**
 * @param {unknown} v
 * @param {string} [label]
 */
function requireFinite(v, label = 'value') {
  if (!isFiniteNum(v)) {
    throw new Error(`${label} must be a finite number`);
  }
  return /** @type {number} */ (v);
}

/**
 * @param {unknown} role
 * @param {string} [label]
 */
export function resolveBrandRole(role, label = 'colorRole') {
  if (typeof role !== 'string' || !role.trim()) {
    throw new Error(`${label} must be a non-empty locked brand role string`);
  }
  const key = role.trim();
  if (key.startsWith('#') || key.toLowerCase().startsWith('rgb')) {
    throw new Error(`${label} must use a locked brand.json role name, not raw color ${key}`);
  }
  const canonical = /** @type {Record<string, string>} */ (ROLE_ALIASES)[key];
  if (!canonical) {
    throw new Error(`${label} "${key}" is not in the locked brand.json v2.6 palette`);
  }
  return canonical;
}

/**
 * @param {unknown} role
 * @param {string} [label]
 */
export function brandHex(role, label = 'colorRole') {
  const key = resolveBrandRole(role, label);
  return /** @type {Record<string, string>} */ (PALETTE_HEX)[key];
}

/**
 * @param {unknown} role
 * @param {string} [label]
 * @returns {[number, number, number]}
 */
export function brandRgb(role, label = 'colorRole') {
  const hx = brandHex(role, label);
  return [
    parseInt(hx.slice(1, 3), 16),
    parseInt(hx.slice(3, 5), 16),
    parseInt(hx.slice(5, 7), 16),
  ];
}

/**
 * @param {string} name
 * @param {number} u
 */
export function easeStage(name, u) {
  if (!STAGE_EASES.has(name)) {
    throw new Error(`Unknown stage ease "${name}"`);
  }
  const p = u <= 0 ? 0 : u >= 1 ? 1 : u;
  if (p === 0 || p === 1 || name === 'linear') return p;
  if (name === 'cubicOut') {
    const inv = 1 - p;
    return 1 - inv * inv * inv;
  }
  if (name === 'quintOut') {
    const inv = 1 - p;
    return 1 - inv * inv * inv * inv * inv;
  }
  if (name === 'quadInOut') {
    return p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
  }
  return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
}

/** @param {any} canvas */
function resolveCanvas(canvas) {
  if (canvas === undefined || canvas === null) {
    return { ...DEFAULT_CANVAS };
  }
  if (typeof canvas !== 'object' || Array.isArray(canvas)) {
    throw new Error('canvas must be an object with w, h, and optional fps');
  }
  const w = requireFinite(canvas.w ?? DEFAULT_CANVAS.w, 'canvas.w');
  const h = requireFinite(canvas.h ?? DEFAULT_CANVAS.h, 'canvas.h');
  const fps = requireFinite(canvas.fps ?? DEFAULT_CANVAS.fps, 'canvas.fps');
  if (w <= 0 || h <= 0 || fps <= 0 || !Number.isInteger(w) || !Number.isInteger(h) || !Number.isInteger(fps)) {
    throw new Error('canvas.w, canvas.h, and canvas.fps must be positive integers');
  }
  return { w, h, fps };
}

/** @param {any} [canvas] */
export function fullscreenBox(canvas) {
  const c = resolveCanvas(canvas);
  return { x: 0, y: 0, w: c.w, h: c.h, r: 0 };
}

/**
 * @param {unknown} r
 * @param {unknown} w
 * @param {unknown} h
 */
export function clampRadius(r, w, h) {
  const rf = requireFinite(r, 'r');
  const wf = requireFinite(w, 'w');
  const hf = requireFinite(h, 'h');
  if (wf <= 0 || hf <= 0) {
    throw new Error('Window width and height must be strictly positive');
  }
  const maxR = Math.min(wf, hf) / 2;
  if (rf <= 0) return 0;
  return rf >= maxR ? maxR : rf;
}

/**
 * @param {any} box
 * @param {any} [canvas]
 * @param {{ label?: string, requireInsideCanvas?: boolean }} [opts]
 */
export function clampWindowBox(box, canvas, opts = {}) {
  const label = opts.label || 'box';
  const requireInsideCanvas = opts.requireInsideCanvas !== false;
  if (!box || typeof box !== 'object' || Array.isArray(box)) {
    throw new Error(`${label} must be an object with x, y, w, h, and optional r`);
  }
  const c = resolveCanvas(canvas);
  let x = requireFinite(box.x, `${label}.x`);
  let y = requireFinite(box.y, `${label}.y`);
  let w = requireFinite(box.w, `${label}.w`);
  let h = requireFinite(box.h, `${label}.h`);
  const r = requireFinite(box.r ?? 0, `${label}.r`);

  if (w <= 0 || h <= 0) {
    throw new Error(`${label} width and height must be > 0`);
  }
  const x1 = x + w;
  const y1 = y + h;
  if (!Number.isFinite(x1) || !Number.isFinite(y1)) {
    throw new Error(`${label} bounds overflow finite range`);
  }
  if (requireInsideCanvas) {
    const eps = 1e-6;
    if (x < -eps || y < -eps || x1 > c.w + eps || y1 > c.h + eps) {
      throw new Error(`${label} [${x}, ${y}, ${w}, ${h}] exceeds physical canvas [0, 0, ${c.w}, ${c.h}]`);
    }
    if (Math.abs(x) <= eps) x = 0;
    if (Math.abs(y) <= eps) y = 0;
    if (Math.abs(x + w - c.w) <= eps) w = c.w - x;
    if (Math.abs(y + h - c.h) <= eps) h = c.h - y;
  }
  return { x, y, w, h, r: clampRadius(r, w, h) };
}

/**
 * @param {any} box
 * @param {any} [canvas]
 * @param {{ eps?: number }} [opts]
 */
export function isFullscreenWindow(box, canvas, opts = {}) {
  const eps = opts.eps ?? 1e-6;
  const c = resolveCanvas(canvas);
  const wb = clampWindowBox(box, c, { requireInsideCanvas: false });
  return (
    Math.abs(wb.x) <= eps &&
    Math.abs(wb.y) <= eps &&
    Math.abs(wb.w - c.w) <= eps &&
    Math.abs(wb.h - c.h) <= eps &&
    Math.abs(wb.r) <= eps
  );
}

/**
 * @param {{x:number,y:number,w:number,h:number,r:number}} a
 * @param {{x:number,y:number,w:number,h:number,r:number}} b
 * @param {number} [eps]
 */
function boxesEqual(a, b, eps = 1e-5) {
  return (
    Math.abs(a.x - b.x) <= eps &&
    Math.abs(a.y - b.y) <= eps &&
    Math.abs(a.w - b.w) <= eps &&
    Math.abs(a.h - b.h) <= eps &&
    Math.abs(a.r - b.r) <= eps
  );
}

/**
 * @param {any} endpoint
 * @param {{x:number,y:number,w:number,h:number,r:number}} defaultFramed
 * @param {{x:number,y:number,w:number,h:number,r:number}} fullBox
 * @param {{w:number,h:number,fps:number}} canvas
 * @param {string} label
 */
function resolveEndpointBox(endpoint, defaultFramed, fullBox, canvas, label) {
  if (endpoint === 'fullscreen') return { ...fullBox };
  if (endpoint === 'framed') return { ...defaultFramed };
  if (endpoint && typeof endpoint === 'object' && !Array.isArray(endpoint)) {
    return clampWindowBox(endpoint, canvas, { label });
  }
  throw new Error(`${label} must be 'fullscreen', 'framed', or a window box object`);
}

/**
 * @param {any} anchor
 * @param {string} label
 * @param {string[]} errors
 */
function validateAnchor(anchor, label, errors) {
  if (anchor === undefined || anchor === null) return;
  if (typeof anchor !== 'object' || Array.isArray(anchor)) {
    errors.push(`${label} must be an object with scene and word`);
    return;
  }
  if (!Number.isInteger(anchor.scene) || anchor.scene < 1) {
    errors.push(`${label}.scene must be an integer >= 1`);
  }
  if (!Number.isInteger(anchor.word) || anchor.word < 0) {
    errors.push(`${label}.word must be a non-negative integer word index`);
  }
  if (anchor.text !== undefined && anchor.text !== null && (typeof anchor.text !== 'string' || !anchor.text.trim())) {
    errors.push(`${label}.text must be a non-empty string when provided`);
  }
}

/** @param {any} canvas @param {any} rawDefault */
function computeDefaultFramed(canvas, rawDefault) {
  if (rawDefault !== undefined && rawDefault !== null) {
    return clampWindowBox(rawDefault, canvas, { label: 'defaultFramedBox' });
  }
  if (canvas.w === 1080 && canvas.h === 1920) {
    return { ...DEFAULT_FRAMED_BOX };
  }
  const mx = Math.round(canvas.w * (56 / 1080) * 1000) / 1000;
  const yt = Math.round(canvas.h * (224 / 1920) * 1000) / 1000;
  const wh = Math.round(canvas.h * (1096 / 1920) * 1000) / 1000;
  const rr = Math.round(Math.min(canvas.w, canvas.h) * 0.033 * 1000) / 1000;
  return clampWindowBox({ x: mx, y: yt, w: canvas.w - 2 * mx, h: wh, r: rr }, canvas, { label: 'defaultFramedBox' });
}

/**
 * Validate a Fixed Stage spec and return an array of error strings (empty === valid).
 * @param {any} spec
 * @returns {string[]}
 */
export function validateStageSpec(spec) {
  /** @type {string[]} */
  const errors = [];
  if (!spec || typeof spec !== 'object' || Array.isArray(spec)) {
    return ['stage spec must be a JSON object'];
  }
  for (const badKey of FORBIDDEN_BRANDING_KEYS) {
    if (spec[badKey] !== undefined && spec[badKey] !== null) {
      errors.push(`stage.${badKey} is forbidden: studio forbids default logos, channel names, and series names`);
    }
  }
  const version = spec.version ?? 1;
  if (!Number.isInteger(version) || version !== 1) {
    errors.push('stage.version must be 1');
  }
  if (spec.enabled !== undefined && typeof spec.enabled !== 'boolean') {
    errors.push('stage.enabled must be a boolean');
  }
  if (spec.autoWrap !== undefined && typeof spec.autoWrap !== 'boolean') {
    errors.push('stage.autoWrap must be a boolean');
  }
  const stageId = spec.id ?? 'fixed-stage';
  if (typeof stageId !== 'string' || !stageId.trim()) {
    errors.push('stage.id must be a non-empty string');
  }
  const clock = spec.clock ?? 'vo';
  if (clock !== 'vo') {
    errors.push("stage.clock must be 'vo' (authoritative VO Clock required)");
  }
  const theme = spec.theme ?? 'dark';
  if (theme !== 'dark' && theme !== 'light') {
    errors.push("stage.theme must be 'dark' or 'light'");
  }

  let canvas;
  try {
    canvas = resolveCanvas(spec.canvas);
  } catch (err) {
    errors.push(err instanceof Error ? err.message : String(err));
    return errors;
  }

  const fullBox = fullscreenBox(canvas);
  let defaultFramed = { ...fullBox };
  try {
    defaultFramed = computeDefaultFramed(canvas, spec.defaultFramedBox);
  } catch (err) {
    errors.push(err instanceof Error ? err.message : String(err));
  }

  const under = spec.under ?? {};
  if (!under || typeof under !== 'object' || Array.isArray(under)) {
    errors.push('stage.under must be an object');
  } else {
    for (const badKey of FORBIDDEN_BRANDING_KEYS) {
      if (under[badKey] !== undefined && under[badKey] !== null) {
        errors.push(`stage.under.${badKey} is forbidden`);
      }
    }
    if (under.surfaceRole !== undefined && under.surfaceRole !== null) {
      try {
        resolveBrandRole(under.surfaceRole, 'under.surfaceRole');
      } catch (err) {
        errors.push(err instanceof Error ? err.message : String(err));
      }
    }
    if (under.background !== undefined && under.background !== null) {
      const bg = under.background;
      if (typeof bg !== 'object' || Array.isArray(bg)) {
        errors.push('under.background must be an object');
      } else {
        const bgId = bg.id ?? 'wash';
        if (!BACKGROUND_IDS.includes(bgId)) {
          errors.push(`under.background.id "${bgId}" is not in the locked background catalog`);
        }
        const bgTheme = bg.theme ?? theme;
        if (bgTheme !== 'dark' && bgTheme !== 'light') {
          errors.push("under.background.theme must be 'dark' or 'light'");
        }
        for (const pKey of ['density', 'angle', 'speed']) {
          if (bg[pKey] !== undefined && !isFiniteNum(bg[pKey])) {
            errors.push(`under.background.${pKey} must be a finite number`);
          }
        }
      }
    }
    if (under.frame !== undefined && under.frame !== null) {
      const fr = under.frame;
      if (typeof fr !== 'object' || Array.isArray(fr)) {
        errors.push('under.frame must be an object');
      } else {
        for (const rKey of ['strokeRole', 'matRole']) {
          if (fr[rKey] !== undefined && fr[rKey] !== null) {
            try {
              resolveBrandRole(fr[rKey], `under.frame.${rKey}`);
            } catch (err) {
              errors.push(err instanceof Error ? err.message : String(err));
            }
          }
        }
        if (fr.strokeWidth !== undefined && (!isFiniteNum(fr.strokeWidth) || fr.strokeWidth < 0)) {
          errors.push('under.frame.strokeWidth must be a finite number >= 0');
        }
        if (fr.matAlpha !== undefined && (!isFiniteNum(fr.matAlpha) || fr.matAlpha < 0 || fr.matAlpha > 1)) {
          errors.push('under.frame.matAlpha must be between 0 and 1');
        }
      }
    }
  }

  const over = spec.over ?? {};
  if (!over || typeof over !== 'object' || Array.isArray(over)) {
    errors.push('stage.over must be an object');
  } else {
    for (const badKey of FORBIDDEN_BRANDING_KEYS) {
      if (over[badKey] !== undefined && over[badKey] !== null) {
        errors.push(`stage.over.${badKey} is forbidden`);
      }
    }
    if (over.progressBar !== undefined && over.progressBar !== null) {
      const pb = over.progressBar;
      if (typeof pb !== 'object' || Array.isArray(pb)) {
        errors.push('over.progressBar must be an object');
      } else {
        for (const rKey of ['trackRole', 'fillRole']) {
          if (pb[rKey] !== undefined && pb[rKey] !== null) {
            try {
              resolveBrandRole(pb[rKey], `over.progressBar.${rKey}`);
            } catch (err) {
              errors.push(err instanceof Error ? err.message : String(err));
            }
          }
        }
        for (const nKey of ['y', 'height', 'marginX', 'trackAlpha']) {
          if (pb[nKey] !== undefined && !isFiniteNum(pb[nKey])) {
            errors.push(`over.progressBar.${nKey} must be a finite number`);
          }
        }
      }
    }
    if (over.header !== undefined && over.header !== null) {
      const hdr = over.header;
      if (typeof hdr !== 'object' || Array.isArray(hdr)) {
        errors.push('over.header must be an object');
      } else {
        for (const badKey of FORBIDDEN_BRANDING_KEYS) {
          if (hdr[badKey] !== undefined && hdr[badKey] !== null) {
            errors.push(`over.header.${badKey} is forbidden`);
          }
        }
        if (hdr.text !== undefined && hdr.text !== null) {
          errors.push('over.header.text is forbidden: visible header text must come from plan/copy.json via slots[].copyId');
        }
        const slots = hdr.slots ?? [];
        if (!Array.isArray(slots)) {
          errors.push('over.header.slots must be an array');
        } else {
          /** @type {Array<{start:number,end:number,id:string}>} */
          const ranges = [];
          slots.forEach((slot, idx) => {
            const sLabel = `over.header.slots[${idx}]`;
            if (!slot || typeof slot !== 'object' || Array.isArray(slot)) {
              errors.push(`${sLabel} must be an object`);
              return;
            }
            if (slot.text !== undefined && slot.text !== null) {
              errors.push(`${sLabel}.text is forbidden: header slots must reference copyId from plan/copy.json, never inline text`);
            }
            for (const badKey of FORBIDDEN_BRANDING_KEYS) {
              if (slot[badKey] !== undefined && slot[badKey] !== null) {
                errors.push(`${sLabel}.${badKey} is forbidden`);
              }
            }
            if (typeof slot.id !== 'string' || !slot.id.trim()) {
              errors.push(`${sLabel}.id must be a non-empty string`);
            }
            if (typeof slot.copyId !== 'string' || !slot.copyId.trim()) {
              errors.push(`${sLabel}.copyId must reference an entry in plan/copy.json`);
            }
            if (!Number.isInteger(slot.scene) || slot.scene < 1) {
              errors.push(`${sLabel}.scene must be an integer >= 1`);
            }
            const role = slot.role ?? 'label';
            if (!VALID_TEXT_ROLES.has(role)) {
              errors.push(`${sLabel}.role "${role}" is not a valid text role`);
            }
            if (!isFiniteNum(slot.start) || !isFiniteNum(slot.end)) {
              errors.push(`${sLabel}.start and .end must be finite numbers`);
            } else if (slot.start < 0 || slot.end <= slot.start) {
              errors.push(`${sLabel} requires 0 <= start < end`);
            } else {
              ranges.push({ start: slot.start, end: slot.end, id: String(slot.id || idx) });
            }
            for (const rKey of ['colorRole', 'accentRole', 'pillRole', 'pillBorderRole']) {
              if (slot[rKey] !== undefined && slot[rKey] !== null) {
                try {
                  resolveBrandRole(slot[rKey], `${sLabel}.${rKey}`);
                } catch (err) {
                  errors.push(err instanceof Error ? err.message : String(err));
                }
              }
            }
            for (const nKey of ['x', 'y', 'size', 'maxWidth', 'pillAlpha']) {
              if (slot[nKey] !== undefined && slot[nKey] !== null && !isFiniteNum(slot[nKey])) {
                errors.push(`${sLabel}.${nKey} must be a finite number`);
              }
            }
            validateAnchor(slot.anchor, `${sLabel}.anchor`, errors);
          });
          ranges.sort((a, b) => a.start - b.start);
          for (let i = 1; i < ranges.length; i += 1) {
            if (ranges[i].start < ranges[i - 1].end - 1e-9) {
              errors.push(`over.header.slots overlap between "${ranges[i - 1].id}" and "${ranges[i].id}"`);
            }
          }
        }
      }
    }
  }

  if (spec.timeline === undefined || spec.timeline === null) {
    if (spec.mode !== undefined && spec.mode !== 'fullscreen' && spec.mode !== 'framed') {
      errors.push("stage.mode must be 'fullscreen' or 'framed' when timeline is omitted");
    }
  } else if (!Array.isArray(spec.timeline) || spec.timeline.length === 0) {
    errors.push('stage.timeline must be a non-empty list of segments');
  } else {
    let prevEnd = -1;
    /** @type {{x:number,y:number,w:number,h:number,r:number}|null} */
    let prevEndBox = null;
    spec.timeline.forEach((seg, idx) => {
      const label = `timeline[${idx}]`;
      if (!seg || typeof seg !== 'object' || Array.isArray(seg)) {
        errors.push(`${label} must be an object`);
        return;
      }
      if (seg.mode !== 'fullscreen' && seg.mode !== 'framed' && seg.mode !== 'transition') {
        errors.push(`${label}.mode must be 'fullscreen', 'framed', or 'transition'`);
        return;
      }
      if (!isFiniteNum(seg.start) || !isFiniteNum(seg.end)) {
        errors.push(`${label}.start and .end must be finite numbers`);
        return;
      }
      if (seg.start < 0 || seg.end <= seg.start) {
        errors.push(`${label} requires 0 <= start < end`);
        return;
      }
      if (prevEnd >= 0 && seg.start < prevEnd - 1e-9) {
        errors.push(`${label} overlaps previous segment (${seg.start} < ${prevEnd})`);
      }
      validateAnchor(seg.anchor, `${label}.anchor`, errors);

      try {
        let segFrom;
        let segTo;
        if (seg.mode === 'fullscreen') {
          segFrom = { ...fullBox };
          segTo = { ...fullBox };
        } else if (seg.mode === 'framed') {
          segFrom = seg.box === undefined || seg.box === null
            ? { ...defaultFramed }
            : clampWindowBox(seg.box, canvas, { label: `${label}.box` });
          segTo = { ...segFrom };
        } else {
          const easeName = seg.ease ?? 'cubicInOut';
          if (!STAGE_EASES.has(easeName)) {
            errors.push(`${label}.ease "${easeName}" is invalid`);
          }
          segFrom = resolveEndpointBox(seg.from, defaultFramed, fullBox, canvas, `${label}.from`);
          segTo = resolveEndpointBox(seg.to, defaultFramed, fullBox, canvas, `${label}.to`);
        }
        if (prevEndBox && !boxesEqual(prevEndBox, segFrom)) {
          errors.push(`${label} starts from a window box that does not match the preceding state (discontinuous jump)`);
        }
        prevEndBox = segTo;
      } catch (err) {
        errors.push(err instanceof Error ? err.message : String(err));
      }
      prevEnd = seg.end;
    });
  }

  return errors;
}

/**
 * Return true when `spec` is a valid, active Fixed Stage specification (`enabled !== false`).
 * Throws if `spec` is non-null and invalid.
 * @param {any} spec
 * @returns {boolean}
 */
export function isStageEnabled(spec) {
  if (spec === null || spec === undefined) return false;
  const errors = validateStageSpec(spec);
  if (errors.length > 0) {
    throw new Error(errors.join('; '));
  }
  return spec.enabled !== false;
}

/**
 * Validate and normalize a Fixed Stage specification into canonical immutable structure.
 * @param {any} spec
 */
export function normalizeStageSpec(spec) {
  const errors = validateStageSpec(spec);
  if (errors.length) {
    throw new Error(errors.join('; '));
  }
  const canvas = resolveCanvas(spec.canvas);
  const theme = spec.theme ?? 'dark';
  const fullBox = fullscreenBox(canvas);
  const defaultFramed = computeDefaultFramed(canvas, spec.defaultFramedBox);

  const underRaw = spec.under ?? {};
  const bgRaw = underRaw.background;
  const bgNorm = bgRaw
    ? {
        id: bgRaw.id ?? 'wash',
        theme: bgRaw.theme ?? theme,
        density: bgRaw.density !== undefined ? Number(bgRaw.density) : undefined,
        angle: bgRaw.angle !== undefined ? Number(bgRaw.angle) : undefined,
        speed: Number(bgRaw.speed ?? 1),
      }
    : null;
  const frRaw = underRaw.frame ?? {};
  const frameNorm = {
    enabled: Boolean(frRaw.enabled ?? true),
    strokeRole: resolveBrandRole(frRaw.strokeRole ?? (theme === 'dark' ? 'red' : 'ink'), 'under.frame.strokeRole'),
    strokeWidth: Number(frRaw.strokeWidth ?? 3),
    matRole: resolveBrandRole(frRaw.matRole ?? (theme === 'dark' ? 'ink_shadow' : 'gray_1'), 'under.frame.matRole'),
    matAlpha: Number(frRaw.matAlpha ?? 0.36),
  };

  const overRaw = spec.over ?? {};
  const pbRaw = overRaw.progressBar ?? {};
  const pbNorm = {
    enabled: Boolean(pbRaw.enabled ?? true),
    y: Number(pbRaw.y ?? 64),
    height: Number(pbRaw.height ?? 6),
    marginX: Number(pbRaw.marginX ?? 60),
    trackRole: resolveBrandRole(pbRaw.trackRole ?? (theme === 'dark' ? 'paper' : 'ink'), 'over.progressBar.trackRole'),
    trackAlpha: Number(pbRaw.trackAlpha ?? 0.18),
    fillRole: resolveBrandRole(pbRaw.fillRole ?? 'red', 'over.progressBar.fillRole'),
  };

  const hdrRaw = overRaw.header ?? {};
  const slotsNorm = (hdrRaw.slots ?? []).map((/** @type {any} */ slot) => ({
    id: slot.id.trim(),
    scene: Number(slot.scene),
    copyId: slot.copyId.trim(),
    role: slot.role ?? 'label',
    start: Number(slot.start),
    end: Number(slot.end),
    x: Number(slot.x ?? canvas.w / 2),
    y: Number(slot.y ?? 136),
    size: Number(slot.size ?? 38),
    maxWidth: Number(slot.maxWidth ?? canvas.w - 160),
    colorRole: resolveBrandRole(slot.colorRole ?? (theme === 'dark' ? 'paper' : 'ink'), 'slot.colorRole'),
    accentRole: resolveBrandRole(slot.accentRole ?? (theme === 'dark' ? 'salmon' : 'red'), 'slot.accentRole'),
    pillRole: slot.pillRole ? resolveBrandRole(slot.pillRole, 'slot.pillRole') : null,
    pillBorderRole: slot.pillBorderRole ? resolveBrandRole(slot.pillBorderRole, 'slot.pillBorderRole') : null,
    pillAlpha: Number(slot.pillAlpha ?? 0.92),
    anchor: slot.anchor ? { ...slot.anchor } : null,
  })).sort((/** @type {any} */ a, /** @type {any} */ b) => a.start - b.start);

  const hdrNorm = {
    enabled: Boolean(hdrRaw.enabled ?? slotsNorm.length > 0),
    slots: slotsNorm,
  };

  const capRaw = overRaw.captions ?? {};
  const capNorm = {
    enabled: Boolean(capRaw.enabled ?? true),
    y: Number(capRaw.y ?? 1455),
  };

  /** @type {Array<any>} */
  const segments = [];
  if (spec.timeline === undefined || spec.timeline === null) {
    const staticMode = spec.mode ?? 'framed';
    const targetBox = staticMode === 'fullscreen' ? { ...fullBox } : { ...defaultFramed };
    segments.push({
      mode: staticMode,
      start: 0,
      end: 1e9,
      ease: 'linear',
      fromBox: { ...targetBox },
      toBox: { ...targetBox },
      anchor: null,
    });
  } else {
    for (const seg of spec.timeline) {
      let fromBox;
      let toBox;
      let easeName = 'linear';
      if (seg.mode === 'fullscreen') {
        fromBox = { ...fullBox };
        toBox = { ...fullBox };
      } else if (seg.mode === 'framed') {
        fromBox = seg.box === undefined || seg.box === null
          ? { ...defaultFramed }
          : clampWindowBox(seg.box, canvas);
        toBox = { ...fromBox };
      } else {
        fromBox = resolveEndpointBox(seg.from, defaultFramed, fullBox, canvas, 'from');
        toBox = resolveEndpointBox(seg.to, defaultFramed, fullBox, canvas, 'to');
        easeName = seg.ease ?? 'cubicInOut';
      }
      segments.push({
        mode: seg.mode,
        start: Number(seg.start),
        end: Number(seg.end),
        ease: easeName,
        fromBox,
        toBox,
        anchor: seg.anchor ? { ...seg.anchor } : null,
      });
    }
  }

  return {
    _normalized: true,
    version: 1,
    enabled: spec.enabled ?? true,
    autoWrap: spec.autoWrap ?? true,
    id: (spec.id ?? 'fixed-stage').trim(),
    clock: 'vo',
    theme,
    canvas,
    fullscreenBox: fullBox,
    defaultFramedBox: defaultFramed,
    under: {
      surfaceRole: resolveBrandRole(underRaw.surfaceRole ?? (theme === 'dark' ? 'ink_shadow' : 'paper'), 'under.surfaceRole'),
      background: bgNorm,
      frame: frameNorm,
    },
    over: {
      progressBar: pbNorm,
      header: hdrNorm,
      captions: capNorm,
    },
    segments,
  };
}

/**
 * @param {{x:number,y:number,w:number,h:number,r:number}} a
 * @param {{x:number,y:number,w:number,h:number,r:number}} b
 * @param {number} p
 * @param {{w:number,h:number,fps:number}} canvas
 */
function mixBox(a, b, p, canvas) {
  if (p <= 0) return { ...a };
  if (p >= 1) return { ...b };
  const q = 1 - p;
  const x = a.x * q + b.x * p;
  const y = a.y * q + b.y * p;
  const w = a.w * q + b.w * p;
  const h = a.h * q + b.h * p;
  const r = clampRadius(a.r * q + b.r * p, w, h);
  return clampWindowBox({ x, y, w, h, r }, canvas);
}

/**
 * @param {any} norm
 * @param {number} t
 */
function evalSegments(norm, t) {
  const segs = norm.segments;
  const canvas = norm.canvas;
  const first = segs[0];
  if (t <= first.start) {
    const box = { ...first.fromBox };
    return { box, mode: isFullscreenWindow(box, canvas) ? 'fullscreen' : 'framed', p: 0 };
  }
  for (let i = 0; i < segs.length; i += 1) {
    const seg = segs[i];
    if (i > 0 && t < seg.start) {
      const held = { ...segs[i - 1].toBox };
      return { box: held, mode: isFullscreenWindow(held, canvas) ? 'fullscreen' : 'framed', p: 1 };
    }
    if (t >= seg.start && t <= seg.end) {
      if (seg.mode !== 'transition') {
        return { box: { ...seg.fromBox }, mode: seg.mode, p: 1 };
      }
      if (t <= seg.start) {
        const box = { ...seg.fromBox };
        return { box, mode: isFullscreenWindow(box, canvas) ? 'fullscreen' : 'framed', p: 0 };
      }
      if (t >= seg.end) {
        const box = { ...seg.toBox };
        return { box, mode: isFullscreenWindow(box, canvas) ? 'fullscreen' : 'framed', p: 1 };
      }
      const rawU = (t - seg.start) / (seg.end - seg.start);
      const p = easeStage(seg.ease, rawU);
      return { box: mixBox(seg.fromBox, seg.toBox, p, canvas), mode: 'transition', p };
    }
  }
  const last = segs[segs.length - 1];
  const box = { ...last.toBox };
  return { box, mode: isFullscreenWindow(box, canvas) ? 'fullscreen' : 'framed', p: 1 };
}

/**
 * Pure stateless Fixed Stage content window `win(spec, t) -> { x, y, w, h, r }`.
 * @param {any} spec
 * @param {number} t
 */
export function win(spec, t) {
  const tf = requireFinite(t, 't');
  const norm = spec && spec._normalized === true ? spec : normalizeStageSpec(spec);
  return evalSegments(norm, tf).box;
}

/**
 * @param {{x:number,y:number,w:number,h:number,r:number}} box
 * @param {{w:number,h:number}} canvas
 */
function chromeOpacity(box, canvas) {
  const inset = Math.max(box.x, box.y, canvas.w - (box.x + box.w), canvas.h - (box.y + box.h), box.r);
  if (inset <= 1e-6) return 0;
  if (inset >= 24) return 1;
  const u = inset / 24;
  return u * u * (3 - 2 * u);
}

/**
 * @param {any} norm
 * @param {number} t
 */
export function activeHeaderAt(norm, t) {
  const hdr = norm.over.header;
  if (!hdr.enabled) return null;
  for (const slot of hdr.slots) {
    if (t >= slot.start && t < slot.end) {
      return { ...slot };
    }
  }
  return null;
}

/**
 * Pure stateless Fixed Stage state evaluation at VO timestamp `t`.
 * @param {any} spec
 * @param {number} t
 * @param {{ duration?: number | null }} [opts]
 */
export function stageStateAt(spec, t, opts = {}) {
  const tf = requireFinite(t, 't');
  const norm = spec && spec._normalized === true ? spec : normalizeStageSpec(spec);
  const { box, mode, p } = evalSegments(norm, tf);
  const full = isFullscreenWindow(box, norm.canvas);
  let prog = 0;
  if (opts.duration !== undefined && opts.duration !== null) {
    const df = requireFinite(opts.duration, 'duration');
    if (df > 0) prog = Math.max(0, Math.min(1, tf / df));
  }
  return {
    time: tf,
    win: box,
    mode: full ? 'fullscreen' : mode,
    isFullscreen: full,
    transitionProgress: p,
    chromeOpacity: full ? 0 : chromeOpacity(box, norm.canvas),
    activeHeader: activeHeaderAt(norm, tf),
    progress: prog,
  };
}

/**
 * Validate `spec` once and return bound pure evaluators.
 * @param {any} spec
 */
export function createStage(spec) {
  const norm = normalizeStageSpec(spec);
  return {
    spec: norm,
    /** @param {number} t */
    win: (t) => win(norm, t),
    /** @param {number} t @param {{ duration?: number | null }} [opts] */
    stateAt: (t, opts = {}) => stageStateAt(norm, t, opts),
  };
}

/**
 * Compute safe inner content envelope intersected with `win(t)` and corner clearance.
 * @param {any} winBox
 * @param {{ margin?: number, padding?: number, contentY?: readonly [number, number], canvas?: any }} [opts]
 */
export function stageSafeEnvelope(winBox, opts = {}) {
  const margin = opts.margin ?? 40;
  const padding = opts.padding ?? 24;
  const contentY = opts.contentY ?? [200, 1350];
  const c = resolveCanvas(opts.canvas);
  const wb = clampWindowBox(winBox, c);
  let x0;
  let x1;
  let y0;
  let y1;
  if (isFullscreenWindow(wb, c)) {
    x0 = margin;
    x1 = c.w - margin;
    y0 = contentY[0];
    y1 = contentY[1];
  } else {
    const cornerInset = wb.r * (1 - 1 / Math.SQRT2) + 8;
    const pad = Math.max(padding, cornerInset);
    x0 = Math.max(margin, wb.x + pad);
    x1 = Math.min(c.w - margin, wb.x + wb.w - pad);
    y0 = Math.max(contentY[0], wb.y + pad);
    y1 = Math.min(contentY[1], wb.y + wb.h - pad);
  }
  return {
    x: /** @type {[number, number]} */ ([x0, Math.max(x0, x1)]),
    y: /** @type {[number, number]} */ ([y0, Math.max(y0, y1)]),
    w: Math.max(0, x1 - x0),
    h: Math.max(0, y1 - y0),
    win: wb,
  };
}

/**
 * Return true if screen-space AABB `box` extends outside the rectangular bounds of `winBox`.
 * @param {{x:number,y:number,w:number,h:number}} box
 * @param {{x:number,y:number,w:number,h:number,r?:number}} winBox
 * @param {{ eps?: number }} [opts]
 */
export function boxOutsideWindow(box, winBox, opts = {}) {
  const eps = opts.eps ?? 0.5;
  const bx0 = box.x;
  const by0 = box.y;
  const bx1 = bx0 + box.w;
  const by1 = by0 + box.h;
  const wx0 = winBox.x;
  const wy0 = winBox.y;
  const wx1 = wx0 + winBox.w;
  const wy1 = wy0 + winBox.h;
  return bx0 < wx0 - eps || by0 < wy0 - eps || bx1 > wx1 + eps || by1 > wy1 + eps;
}

/**
 * Return which rounded corners of `winBox` (`r > 0`) clip AABB `box`.
 * @param {{x:number,y:number,w:number,h:number}} box
 * @param {{x:number,y:number,w:number,h:number,r?:number}} winBox
 * @param {{ eps?: number }} [opts]
 * @returns {string[]}
 */
export function boxClippedByWindowCorners(box, winBox, opts = {}) {
  const eps = opts.eps ?? 0.5;
  const r = Number(winBox.r ?? 0);
  if (r <= eps) return [];
  const bx0 = box.x;
  const by0 = box.y;
  const bx1 = bx0 + box.w;
  const by1 = by0 + box.h;
  const wx0 = winBox.x;
  const wy0 = winBox.y;
  const wx1 = wx0 + winBox.w;
  const wy1 = wy0 + winBox.h;

  const px0 = Math.max(wx0, Math.min(wx1, bx0));
  const py0 = Math.max(wy0, Math.min(wy1, by0));
  const px1 = Math.max(wx0, Math.min(wx1, bx1));
  const py1 = Math.max(wy0, Math.min(wy1, by1));
  if (px1 <= px0 || py1 <= py0) return [];

  /** @type {string[]} */
  const clipped = [];
  const tlCx = wx0 + r;
  const tlCy = wy0 + r;
  if (px0 < tlCx && py0 < tlCy && Math.hypot(tlCx - px0, tlCy - py0) > r + eps) {
    clipped.push('top-left');
  }
  const trCx = wx1 - r;
  const trCy = wy0 + r;
  if (px1 > trCx && py0 < trCy && Math.hypot(px1 - trCx, trCy - py0) > r + eps) {
    clipped.push('top-right');
  }
  const blCx = wx0 + r;
  const blCy = wy1 - r;
  if (px0 < blCx && py1 > blCy && Math.hypot(blCx - px0, py1 - blCy) > r + eps) {
    clipped.push('bottom-left');
  }
  const brCx = wx1 - r;
  const brCy = wy1 - r;
  if (px1 > brCx && py1 > brCy && Math.hypot(px1 - brCx, py1 - brCy) > r + eps) {
    clipped.push('bottom-right');
  }
  return clipped;
}
