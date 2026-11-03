// Animated backgrounds for engines K and R — identical geometry to engine P
// (templates/procedural-reels/backgrounds.py).
//
// A background is a PURE FUNCTION of time: `backgroundFrame(ctx, w, h, t, spec)` paints frame `t`
// from nothing. No accumulated state, no requestAnimationFrame, no CSS — so frame 137 is the same
// picture whether a render walks forward, jumps, or renders frames in parallel.
//
// Geometry is normalised to the frame box (fractions of w/h) and every colour is a BRAND ROLE from
// motion/backgrounds.json (`roles.dark` / `roles.light`), resolved here against PALETTE. A pattern
// never mentions a hex value; change the palette and every background follows.
//
// Catalog: medo-motion/motion/backgrounds.json — tests/test_backgrounds.py fails if this file, the
// Python mirror and the catalog drift apart.
// Pure module: no imports, so engines K and R share this file byte for byte (like motion.js).
// The palette below mirrors brand/brand.json and is verified by tests/test_backgrounds.py.
// Keys are the exact brand.json names (so tests/test_backgrounds.py can verify them), plus the
// camelCase aliases the rest of the studio uses.
export const PALETTE = {
  red: '#CB271B', red_bright: '#CB0801', red_deep: '#9F0803',
  ink: '#0A0A0A', ink_soft: '#71717A', paper: '#F3F2F1',
  gray_1: '#D8D7D5', gray_2: '#C9C5C2', gray_3: '#BFBAB7', gray_4: '#A3A2A0',
  salmon: '#D97F68', blush: '#D5AEA6', inkShadow: '#030303',
};

const C = { ...PALETTE, redBright: PALETTE.red_bright, redDeep: PALETTE.red_deep,
  inkSoft: PALETTE.ink_soft, gray1: PALETTE.gray_1, gray2: PALETTE.gray_2,
  gray3: PALETTE.gray_3, gray4: PALETTE.gray_4 };

const hex = h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];

/** 'red@0.5' → 'rgba(203,39,27,0.5)'; 'ink' → '#0A0A0A'. Roles only, never raw hex. */
export function roleColor(role, alphaFallback = 1) {
  if (!role) return 'rgba(0,0,0,0)';
  const [name, a] = role.split('@');
  const rgb = hex(C[name] || PALETTE[name] || PALETTE.ink);
  const alpha = a === undefined ? alphaFallback : Number(a);
  return alpha >= 1 ? `rgb(${rgb[0]},${rgb[1]},${rgb[2]})` : `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${alpha})`;
}

// Embedded copy of the role maps so a project (which only receives templates/) behaves identically.
// tests/test_backgrounds.py fails if this drifts from medo-motion/motion/backgrounds.json.
export const ROLES = {
  dark: {
    bg: 'ink',
    wash: 'inkShadow',
    line: 'gray_1@0.10',
    lineStrong: 'gray_1@0.20',
    matter: 'ink@0.90',
    text: 'paper',
    mid: 'ink_soft',
    accent: 'red',
    accentDeep: 'red_deep',
    accentSoft: 'salmon@0.30',
    glow: 'red@0.50',
    blobA: 'salmon@0.26',
    blobB: 'red_deep@0.34',
    paperWash: 'ink@0.10',
  },
  light: {
    bg: 'paper',
    wash: 'gray_1',
    line: 'ink@0.09',
    lineStrong: 'ink@0.18',
    matter: 'paper@0.92',
    text: 'ink',
    mid: 'gray_4',
    accent: 'red_deep',
    accentDeep: 'red',
    accentSoft: 'red_deep@0.20',
    glow: 'red@0.26',
    blobA: 'blush@0.55',
    blobB: 'red_deep@0.16',
    paperWash: 'gray_2@0.55',
  },
};

export const BACKGROUND_IDS = [
  'iso-grid', 'grid-2d', 'paper', 'aura', 'orbital', 'orbit-mono',
  'frames', 'organic', 'perspective', 'glyphs', 'pulse', 'wash',
];

export const DEFAULTS = {
  density: 45, angle: 25, speed: 1,
  params: {
    'iso-grid': { angle: 25, density: 45 },
    'grid-2d': { angle: 0, density: 45 },
    paper: { angle: 0, density: 40 },
    aura: { angle: 0, density: 40 },
    orbital: { angle: 0, density: 45 },
    'orbit-mono': { angle: 0, density: 45 },
    frames: { angle: 0, density: 40 },
    organic: { angle: 45, density: 35 },
    perspective: { angle: 0, density: 45 },
    glyphs: { angle: 0, density: 45 },
    pulse: { angle: 0, density: 30 },
    wash: { angle: 0, density: 45 },
  },
};

const TAU = Math.PI * 2;

/** The role values for one theme, as ready-to-use CSS colours. */
export function themeColors(theme = 'dark') {
  const src = ROLES[theme] || ROLES.dark;
  const out = {};
  for (const [k, v] of Object.entries(src)) out[k] = roleColor(v);
  return out;
}

/* ---------------- shared drawing helpers (identical maths in backgrounds.py) ---------------- */

/** Deterministic 0..1 hash — same sequence as _hash01() in backgrounds.py. */
export const hash01 = i => ((i * 1103515245 + 12345) % 2147483647) / 2147483647;

function fill(ctx, w, h, color) {
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, w, h);
}

/** Parse 'rgb(r,g,b)' / 'rgba(r,g,b,a)' into [r,g,b,a]. */
function parts(color) {
  const m = /^rgba?\(([^)]+)\)$/.exec(color);
  if (!m) { const [r, g, b] = hex(color); return [r, g, b, 1]; }
  const v = m[1].split(',').map(Number);
  return [v[0] | 0, v[1] | 0, v[2] | 0, v.length > 3 ? v[3] : 1];
}

/**
 * The same colour at alpha 0. Canvas interpolates gradients in premultiplied alpha, so fading to
 * 'transparent' (= transparent BLACK) darkens the middle of every glow — a real bug that showed up as
 * a grey blob in the K column of `make backgrounds`. Fade to the colour's own RGB instead.
 */
const fadeOut = color => {
  const [r, g, b] = parts(color);
  return `rgba(${r},${g},${b},0)`;
};

/** Radial wash: a soft disc of `color` centred on (cx, cy), fading to the same hue at alpha 0. */
function wash(ctx, w, h, cx, cy, r, color) {
  const g = ctx.createRadialGradient(cx, cy, Math.max(0.001, r * 0.02), cx, cy, r);
  g.addColorStop(0, color);
  g.addColorStop(1, fadeOut(color));
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
}

/** Straight grid, optionally rotated about the frame centre, drifting at 14/9 px per second. */
function grid(ctx, w, h, t, density, angle, color) {
  ctx.save();
  if (angle) {
    const cx = w / 2, cy = h / 2;
    ctx.translate(cx, cy);
    ctx.rotate(angle);
    ctx.translate(-cx, -cy);
  }
  const size = Math.max(10, density * (w / 420));
  const diag = Math.hypot(w, h);
  const x0 = (w - diag) / 2, x1 = (w + diag) / 2;
  const y0 = (h - diag) / 2, y1 = (h + diag) / 2;
  const ox = (t * 14) % size, oy = (t * 9) % size;
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = x0 + ox; x < x1; x += size) { ctx.moveTo(x, y0); ctx.lineTo(x, y1); }
  for (let y = y0 + oy; y < y1; y += size) { ctx.moveTo(x0, y); ctx.lineTo(x1, y); }
  ctx.stroke();
  ctx.restore();
}

function orbitals(ctx, w, h, t, density, c, hot) {
  const base = Math.min(w, h) * (density / 100) * 0.6;
  const centres = [{ x: w * 0.82, y: h * 0.16, d: 1 }, { x: w * 0.18, y: h * 0.84, d: -1 }];
  centres.forEach((k, idx) => {
    const r = base * (1 + idx * 0.18);
    ctx.save();
    ctx.translate(k.x, k.y);
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, TAU);
    ctx.lineWidth = 1.6;
    ctx.strokeStyle = hot ? c.accentSoft : c.lineStrong;
    ctx.stroke();
    for (let n = 0; n < 3; n++) {
      const a = t * 0.5 * k.d + n * (TAU / 3);
      ctx.save();
      ctx.translate(Math.cos(a) * r, Math.sin(a) * r);
      ctx.shadowColor = hot ? c.accent : 'transparent';
      ctx.shadowBlur = hot ? 14 : 0;
      ctx.fillStyle = hot ? c.accent : c.text;
      const s = Math.max(6, Math.min(w, h) * 0.038);
      ctx.rotate(a + Math.PI / 4);
      ctx.fillRect(-s / 2, -s / 2, s, s);
      ctx.restore();
    }
    ctx.restore();
  });
}

/* ---------------- the 12 backgrounds ---------------- */
// Every painter has the same signature: (ctx, w, h, t, c, p) where `c` is themeColors() and `p` is
// the resolved params ({ density, angle }). Nothing reads outside these arguments.

const PAINT = {
  'iso-grid'(ctx, w, h, t, c, p) {
    fill(ctx, w, h, c.bg);
    const lx = w * 0.35 + Math.sin(t * 0.6) * w * 0.15;
    const ly = h * 0.28 + Math.cos(t * 0.45) * h * 0.09;
    wash(ctx, w, h, lx, ly, Math.max(w, h) * 0.72, c.glow);
    grid(ctx, w, h, t, p.density, p.angle, c.line);
  },

  'grid-2d'(ctx, w, h, t, c, p) {
    fill(ctx, w, h, c.bg);
    const pulse = 0.40 + Math.sin(t * 1.2) * 0.16;
    ctx.globalAlpha = 1;
    wash(ctx, w, h, w * 0.28, h * 0.32, Math.max(w, h) * 0.78, pulseColor(c.accent, pulse));
    grid(ctx, w, h, t, p.density, 0, pulseColor(c.accent, 0.30));
  },

  paper(ctx, w, h, t, c, p) {
    fill(ctx, w, h, c.bg);
    for (let i = 0; i < 4; i++) {
      const ox = w * (0.2 + i * 0.25) + Math.sin(t * 0.3 + i) * w * 0.12;
      const oy = h * (0.15 + i * 0.22) + Math.cos(t * 0.4 + i) * h * 0.08;
      wash(ctx, w, h, ox, oy, Math.max(w, h) * 0.44, c.paperWash);
    }
    grid(ctx, w, h, t, p.density, 0, c.line);
  },

  aura(ctx, w, h, t, c) {
    fill(ctx, w, h, c.bg);
    const ax = w * 0.32 + Math.sin(t * 0.5) * w * 0.16;
    const ay = h * 0.22 + Math.cos(t * 0.4) * h * 0.08;
    wash(ctx, w, h, ax, ay, Math.max(w, h) * 0.62, c.blobA);
    const bx = w * 0.72 + Math.cos(t * 0.6) * w * 0.14;
    const by = h * 0.78 + Math.sin(t * 0.5) * h * 0.08;
    wash(ctx, w, h, bx, by, Math.max(w, h) * 0.62, c.blobB);
  },

  orbital(ctx, w, h, t, c, p) {
    const g = ctx.createRadialGradient(w / 2, h / 2, Math.max(0.1, w * 0.01), w / 2, h / 2, Math.max(w, h) * 0.8);
    g.addColorStop(0, c.bg);
    g.addColorStop(1, c.wash);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    orbitals(ctx, w, h, t, p.density, c, true);
  },

  'orbit-mono'(ctx, w, h, t, c, p) {
    const g = ctx.createRadialGradient(w / 2, h / 2, Math.max(0.1, w * 0.01), w / 2, h / 2, Math.max(w, h) * 0.8);
    g.addColorStop(0, c.bg);
    g.addColorStop(1, c.wash);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    orbitals(ctx, w, h, t, p.density, c, false);
  },

  frames(ctx, w, h, t, c, p) {
    fill(ctx, w, h, c.bg);
    wash(ctx, w, h, w * 0.12, h * 0.10, Math.max(w, h) * 0.60, c.accentSoft);
    wash(ctx, w, h, w * 0.90, h * 0.92, Math.max(w, h) * 0.50, c.accentSoft);
    grid(ctx, w, h, t, p.density, 0, c.line);
    const pulse = 0.5 + Math.sin(t * 2) * 0.35;
    ctx.save();
    ctx.strokeStyle = c.accent;
    ctx.globalAlpha = 0.5 * pulse;
    ctx.lineWidth = 1;
    ctx.strokeRect(w * 0.08, h * 0.60, w * 0.42, h * 0.16);
    ctx.strokeRect(w * 0.52, h * 0.74, w * 0.34, h * 0.12);
    ctx.globalAlpha = 1;
    ctx.fillStyle = c.accent;
    ctx.shadowColor = c.accent;
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.arc(w * 0.84 + Math.sin(t) * w * 0.03, h * 0.93, Math.max(2.5, w * 0.012), 0, TAU);
    ctx.fill();
    ctx.restore();
    const ly = ((t * 60) % (h + 240)) - 120;
    const lg = ctx.createLinearGradient(0, ly - 90, 0, ly + 90);
    lg.addColorStop(0, fadeOut(c.accentSoft));
    lg.addColorStop(0.5, c.accentSoft);
    lg.addColorStop(1, fadeOut(c.accentSoft));
    ctx.fillStyle = lg;
    ctx.fillRect(0, ly - 90, w, 180);
  },

  organic(ctx, w, h, t, c, p) {
    const g = ctx.createRadialGradient(w / 2, h / 2, Math.max(0.1, w * 0.02), w / 2, h / 2, Math.max(w, h) * 0.78);
    g.addColorStop(0, c.wash);
    g.addColorStop(1, c.bg);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    grid(ctx, w, h, t, p.density, p.angle, c.line);
    ctx.save();
    ctx.fillStyle = c.matter;
    ctx.shadowColor = 'rgba(0,0,0,0.6)';
    ctx.shadowBlur = 24;
    const off = Math.sin(t * 0.8) * w * 0.06;
    ctx.beginPath();
    ctx.moveTo(w * 0.72, -10);
    ctx.bezierCurveTo(w * 0.64, h * 0.18 + off, w * 0.82, h * 0.30, w + 20, h * 0.24);
    ctx.lineTo(w + 20, -10);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  },

  perspective(ctx, w, h, t, c) {
    fill(ctx, w, h, c.bg);
    const cx = w / 2, cy = h / 2, camY = h * 0.5, f = Math.max(w, h) * 0.8;
    const NX = 12, NZ = 20, Z_NEAR = 0.2, Z_FAR = 50;
    ctx.lineWidth = 1;
    ctx.strokeStyle = c.line;
    for (let i = -NX; i <= NX; i++) {
      const x3 = i * (w / NX);
      ctx.beginPath();
      ctx.moveTo(cx + (x3 * f) / (Z_NEAR * w), cy + (camY * f) / (Z_NEAR * w));
      ctx.lineTo(cx + (x3 * f) / (Z_FAR * w), cy + (camY * f) / (Z_FAR * w));
      ctx.stroke();
    }
    const off = (t * 2.5) % 1;
    for (let i = 0; i < NZ; i++) {
      const u = (i + off) / NZ;
      const z = 0.5 + Math.pow(1 - u, 3) * (Z_FAR - 0.5);
      const y = cy + (camY * f) / (z * w);
      ctx.strokeStyle = c.accent;
      ctx.globalAlpha = Math.max(0, Math.min(1, 1 - z / Z_FAR)) * 0.42;
      ctx.beginPath();
      ctx.moveTo(cx + (-w * 2 * f) / (z * w), y);
      ctx.lineTo(cx + (w * 2 * f) / (z * w), y);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  },

  glyphs(ctx, w, h, t, c, p) {
    fill(ctx, w, h, c.bg);
    const fs = Math.max(12, p.density * (w / 600));
    ctx.font = `bold ${fs}px system-ui,"Segoe UI",sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    const chars = 'ابتثجحخدذرزسشصضطظعغفقكلمنهوي٠١٢٣٤٥٦٧٨٩';
    const colW = fs * 1.5;
    const cols = Math.ceil(w / colW);
    for (let i = 0; i < cols; i++) {
      const x = i * colW + colW / 2;
      const offset = (i * 157.3) % h;
      const speed = 60 + (i % 5) * 30;
      const yBase = (t * speed + offset) % (h + fs * 15);
      for (let j = 0; j < 15; j++) {
        const y = yBase - j * fs * 1.3;
        if (y < -fs || y > h + fs) continue;
        const ch = chars[Math.floor(hash01(i * 13 + j * 7 + Math.floor(t * 3)) * chars.length)];
        const op = Math.max(0, 1 - j / 15);
        if (j === 0) {
          ctx.fillStyle = c.text;
          ctx.shadowColor = c.accent;
          ctx.shadowBlur = 12;
        } else {
          ctx.fillStyle = pulseColor(c.accent, op * 0.75);
          ctx.shadowBlur = 0;
        }
        ctx.fillText(ch, x, y);
      }
    }
    ctx.shadowBlur = 0;
  },

  pulse(ctx, w, h, t, c, p) {
    fill(ctx, w, h, c.bg);
    const gs = Math.max(15, p.density * (w / 400));
    ctx.strokeStyle = c.line;
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = 0; x < w; x += gs) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
    for (let y = 0; y < h; y += gs) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
    ctx.stroke();
    const cy = h / 2, amp = h * 0.18, cycle = w * 1.5, off = (t * 2 * 100) % cycle;
    ctx.save();
    ctx.beginPath();
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = Math.max(1.5, w * 0.004);
    ctx.shadowColor = c.accent;
    ctx.shadowBlur = 12;
    ctx.lineJoin = 'round';
    ctx.moveTo(-10, cy);
    for (let x = -10; x < w + 10; x += 2) {
      const q = (((x + off) % cycle) + cycle) % cycle / cycle;
      const y = beat(q) + Math.sin(q * 200 + t * 10) * 0.015;
      ctx.lineTo(x, cy - y * amp);
    }
    ctx.stroke();
    ctx.restore();
    const px = (t * 150) % w;
    const q = (((px + off) % cycle) + cycle) % cycle / cycle;
    ctx.save();
    ctx.fillStyle = c.text;
    ctx.shadowColor = c.accent;
    ctx.shadowBlur = 18;
    ctx.beginPath();
    ctx.arc(px, cy - beat(q) * amp, Math.max(2, w * 0.008), 0, TAU);
    ctx.fill();
    ctx.restore();
  },

  wash(ctx, w, h, t, c) {
    fill(ctx, w, h, c.bg);
    washDisc(ctx, w, h, w * 0.8, h * 0.2, w * 1.25, c.wash);
    washDisc(ctx, w, h, w * 0.2, h * 0.8, w * 0.9, 'rgba(0,0,0,0.18)');
  },
};

/* `wash` as a background id shadows the helper name; keep a private alias. */
const washDisc = wash;

/** `rgba(...)` from a resolved `rgb(r,g,b)` / `#hex` colour plus an alpha — K-side only. */
function pulseColor(color, alpha) {
  const m = /^rgba?\(([^)]+)\)$/.exec(color);
  const [r, g, b] = m ? m[1].split(',').map(Number) : hex(color);
  return `rgba(${r | 0},${g | 0},${b | 0},${Math.max(0, Math.min(1, alpha))})`;
}

/** The ECG/WAV shape used by `pulse` — shared with backgrounds.py. */
function beat(q) {
  if (q > 0.10 && q < 0.20) return Math.sin((q - 0.10) / 0.10 * Math.PI) * 0.15;
  if (q > 0.30 && q < 0.35) return -0.20;
  if (q >= 0.35 && q < 0.40) return 1.0;
  if (q >= 0.40 && q < 0.45) return -0.40;
  if (q > 0.60 && q < 0.80) return Math.sin((q - 0.60) / 0.20 * Math.PI) * 0.25;
  return 0;
}

/* ---------------- public API ---------------- */

/** Resolve a spec into everything a painter needs. Unknown keys fall back to the defaults. */
export function resolveSpec(spec = {}) {
  const id = BACKGROUND_IDS.includes(spec.id) ? spec.id : 'wash';
  const base = DEFAULTS.params[id] || {};
  const theme = spec.theme === 'light' ? 'light' : 'dark';
  return {
    id,
    theme,
    colors: themeColors(theme),
    params: {
      density: spec.density ?? base.density ?? DEFAULTS.density,
      angle: ((spec.angle ?? base.angle ?? DEFAULTS.angle) * Math.PI) / 180,
      speed: spec.speed ?? DEFAULTS.speed,
    },
  };
}

/**
 * Paint background frame `t` (seconds) into a 2D context, filling the whole `w × h` box.
 * The ctx is expected to be in CSS pixels (set your DPR transform before calling).
 */
export function backgroundFrame(ctx, w, h, t, spec = {}) {
  const r = resolveSpec(spec);
  const painter = PAINT[r.id] || PAINT.wash;
  ctx.save();
  painter(ctx, w, h, (Number(t) || 0) * r.params.speed, r.colors, r.params);
  ctx.restore();
  return r.id;
}

/** Convenience for a canvas element: sizes it, paints one frame. */
export function paintBackground(canvas, t, spec = {}) {
  const dpr = Math.min((typeof devicePixelRatio === 'number' ? devicePixelRatio : 1), 2);
  const w = canvas.clientWidth || canvas.width;
  const h = canvas.clientHeight || canvas.height;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return backgroundFrame(ctx, w, h, t, spec);
}
