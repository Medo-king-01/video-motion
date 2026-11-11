// Engine P's drawn sprites for the Canvas engine: devices, part icons, the flat person, speech
// bubble, marks and small props. A port of `procedural-reels/art.py` and the sprite helpers of
// `procedural-reels/lib.py`, shape for shape, so a scene written for engine P can be drawn by K.
//
//   import { drawArt, artSize } from './lib/art.js';
//   drawArt(ctx, 'laptop', 540, 900, { w: 520, screen: 'glow' });            // centred on (540, 900)
//   drawArt(ctx, 'person', 300, 1390, { shirt: 'red', expr: 'talk1', pose: 'talk' },
//           { anchor: [0.5, 1], scale: 0.9 });                               // feet on the ground line
//   drawArt(ctx, 'bubble', 620, 520, { w: 520, h: 180, tail: 'bl' }, { alpha: 0.9 });
//
// `drawArt(ctx, name, cx, cy, options, place)` mirrors P's `paste(frame, sprite, cx, cy, ...)`:
// the sprite's anchor (default its centre) lands on (cx, cy), then `scale`, `rot` (degrees) and
// `alpha` apply. `artSize(name, options)` is the sprite box `{ w, h }` in design pixels — the same
// numbers engine P's sprite has, so layouts carry over unchanged.
//
// Colours are brand tokens (`'red'`, `'inkSoft'`, …) or any CSS colour; every default is a
// `brand.js` palette colour, and P's `(r, g, b)` tuples map to the same tokens.
// Parity with engine P is measured, not assumed: `python3 tools/art_parity.py`.
import { PALETTE } from './brand.js';

const OUTLINE = PALETTE.inkShadow;
const TAU = Math.PI * 2;
const rad = deg => deg * Math.PI / 180;

/** A brand token name, a CSS colour, or an `[r, g, b]` / `[r, g, b, a255]` tuple → CSS colour. */
export function artColor(value, alpha = 255) {
  let css = value;
  if (Array.isArray(value)) {
    const [r, g, b, a = 255] = value;
    css = `rgba(${r},${g},${b},${(a / 255).toFixed(4)})`;
  } else if (typeof value === 'string' && Object.hasOwn(PALETTE, value)) {
    css = PALETTE[value];
  }
  if (alpha >= 255 || typeof css !== 'string' || !css.startsWith('#') || css.length !== 7) return css;
  const n = parseInt(css.slice(1), 16);
  return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${(alpha / 255).toFixed(4)})`;
}

// The same tiny drawing vocabulary engine P's `D` class has, with Pillow's conventions:
// boxes are (x0, y0, x1, y1); an `outline` is drawn *inside* a rect/rrect/ellipse; a polygon's
// outline and every `line` are centred on the path with round joints; angles are degrees,
// clockwise from 3 o'clock.
// Engine P draws at 3x and floors every stroke width to a whole supersampled pixel.
const snap = width => Math.floor(width * 3 + 1e-6) / 3;

class Pen {
  constructor(ctx) { this.ctx = ctx; }

  _shape(path, fill, outline, rawWidth) {
    const { ctx } = this;
    const width = snap(rawWidth);
    if (fill) { path(); ctx.fillStyle = artColor(fill); ctx.fill(); }
    if (outline && width > 0) {
      ctx.save(); path(); ctx.clip();
      path(); ctx.lineWidth = width * 2; ctx.lineJoin = 'miter'; ctx.strokeStyle = artColor(outline); ctx.stroke();
      ctx.restore();
    }
  }

  rect([x0, y0, x1, y1], { fill = null, outline = null, width = 0 } = {}) {
    this._shape(() => { this.ctx.beginPath(); this.ctx.rect(x0, y0, x1 - x0, y1 - y0); }, fill, outline, width);
  }

  rrect([x0, y0, x1, y1], r, { fill = null, outline = null, width = 0 } = {}) {
    const radius = Math.max(0, Math.min(r, (x1 - x0) / 2, (y1 - y0) / 2));
    this._shape(() => { this.ctx.beginPath(); this.ctx.roundRect(x0, y0, x1 - x0, y1 - y0, radius); }, fill, outline, width);
  }

  ell([x0, y0, x1, y1], { fill = null, outline = null, width = 0 } = {}) {
    this._shape(() => {
      this.ctx.beginPath();
      this.ctx.ellipse((x0 + x1) / 2, (y0 + y1) / 2, Math.abs(x1 - x0) / 2, Math.abs(y1 - y0) / 2, 0, 0, TAU);
    }, fill, outline, width);
  }

  circ(cx, cy, r, style = {}) { this.ell([cx - r, cy - r, cx + r, cy + r], style); }

  poly(points, { fill = null, outline = null, width = 0 } = {}) {
    const { ctx } = this;
    const path = () => { ctx.beginPath(); points.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); };
    if (fill) { path(); ctx.fillStyle = artColor(fill); ctx.fill(); }
    if (outline && width > 0) {
      path(); ctx.lineWidth = snap(width); ctx.lineJoin = 'round'; ctx.strokeStyle = artColor(outline); ctx.stroke();
    }
  }

  line(points, color, width, round = true) {
    const { ctx } = this;
    ctx.beginPath(); points.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.lineWidth = snap(width); ctx.lineJoin = 'round'; ctx.lineCap = round ? 'round' : 'butt';
    ctx.strokeStyle = artColor(color); ctx.stroke();
  }

  arc([x0, y0, x1, y1], a0, a1, color, rawWidth) {
    const { ctx } = this;
    const width = snap(rawWidth);
    const rx = Math.max(0.01, (x1 - x0) / 2 - width / 2), ry = Math.max(0.01, (y1 - y0) / 2 - width / 2);
    ctx.beginPath(); ctx.ellipse((x0 + x1) / 2, (y0 + y1) / 2, rx, ry, 0, rad(a0), rad(a1));
    ctx.lineWidth = width; ctx.lineCap = 'butt'; ctx.strokeStyle = artColor(color); ctx.stroke();
  }

  // Pillow's `anchor='mm'`: the middle of the advance width and of the font's line box.
  text([x, y], txt, size, color, { rtl = false, family = 'Cairo', weight = 800 } = {}) {
    const { ctx } = this;
    ctx.save();
    ctx.font = `${weight} ${size}px "${family}", sans-serif`;
    ctx.direction = rtl ? 'rtl' : 'ltr'; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
    if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';
    const m = ctx.measureText(txt);
    ctx.fillStyle = artColor(color);
    const up = m.fontBoundingBoxAscent ?? m.actualBoundingBoxAscent, down = m.fontBoundingBoxDescent ?? m.actualBoundingBoxDescent;
    ctx.fillText(txt, x, y + (up - down) / 2);
    ctx.restore();
  }
}

// ---------------------------------------------------------------- devices
const LAPTOP_SCREEN = { glow: 'inkShadow', bad: 'redDeep', blank: 'inkShadow', dark: 'inkShadow' };

const laptop = {
  defaults: { w: 520, screen: 'glow' },
  size: ({ w }) => ({ w: Math.trunc(w * 1.1), h: Math.trunc(w * 0.62) + Math.trunc(w * 0.05) + 6 }),
  draw(d, { w, screen }) {
    if (!Object.hasOwn(LAPTOP_SCREEN, screen)) throw new Error(`laptop: unknown screen '${screen}' (glow, bad, blank, dark)`);
    const lh = Math.trunc(w * 0.62), bh = Math.trunc(w * 0.05), ox = Math.trunc(w * 0.05);
    d.rrect([ox, 0, ox + w, lh], w * 0.035, { fill: 'inkShadow', outline: OUTLINE, width: 4 });
    const sx0 = ox + w * 0.035, sy0 = w * 0.035, sx1 = ox + w * 0.965, sy1 = lh - w * 0.035;
    d.rrect([sx0, sy0, sx1, sy1], w * 0.012, { fill: LAPTOP_SCREEN[screen] });
    const cx = (sx0 + sx1) / 2, cy = (sy0 + sy1) / 2;
    if (screen === 'glow') {
      [[0.55, 'blush'], [0.38, 'inkSoft'], [0.46, 'inkSoft']].forEach(([ww, c], i) => {
        const y = sy0 + (sy1 - sy0) * (0.22 + i * 0.17);
        d.rrect([sx0 + w * 0.06, y, sx0 + w * 0.06 + w * ww, y + w * 0.045], 6, { fill: c });
      });
      d.circ(sx1 - w * 0.15, sy0 + w * 0.13, w * 0.055, { fill: 'salmon' });
    } else if (screen === 'bad') {
      d.circ(cx, cy, w * 0.15, { fill: 'red' });
      d.line([[cx - w * 0.07, cy - w * 0.07], [cx + w * 0.07, cy + w * 0.07]], 'paper', w * 0.035);
      d.line([[cx + w * 0.07, cy - w * 0.07], [cx - w * 0.07, cy + w * 0.07]], 'paper', w * 0.035);
    } else if (screen === 'blank') {
      d.circ(cx, cy, w * 0.05, { fill: 'inkSoft' });
    }
    d.rrect([0, lh + 2, w * 1.1, lh + 2 + bh], bh / 2, { fill: 'gray2', outline: OUTLINE, width: 3 });
    d.rrect([w * 0.55 - w * 0.09, lh + 2, w * 0.55 + w * 0.09, lh + 2 + bh * 0.5], bh / 3, { fill: 'gray4' });
  },
};

const desktop = {
  defaults: { w: 420 },
  size: ({ w }) => ({ w: Math.trunc(w * 1.25), h: Math.trunc(w) + 10 }),
  draw(d, { w }) {
    const T = Math.trunc, mw = T(w * 0.78), mh = T(mw * 0.6);
    d.rrect([0, 0, mw, mh], 12, { fill: 'inkShadow', outline: OUTLINE, width: 4 });
    d.rrect([14, 14, mw - 14, mh - 14], 6, { fill: 'inkShadow' });
    [[0.5, 'blush'], [0.34, 'inkSoft']].forEach(([ww, c], i) => d.rrect([34, 36 + i * 48, 34 + mw * ww, 60 + i * 48], 6, { fill: c }));
    d.rect([mw / 2 - 18, mh, mw / 2 + 18, mh + T(w * 0.14)], { fill: 'gray4', outline: OUTLINE, width: 3 });
    d.rrect([mw / 2 - T(w * 0.18), mh + T(w * 0.14), mw / 2 + T(w * 0.18), mh + T(w * 0.17)], 8, { fill: 'gray2', outline: OUTLINE, width: 3 });
    const kx = mw / 2 - T(w * 0.3);
    d.rrect([kx, mh + T(w * 0.24), kx + T(w * 0.6), mh + T(w * 0.31)], 8, { fill: 'ink', outline: OUTLINE, width: 3 });
    const tx = T(w * 0.84), th = T(w * 0.88);
    d.rrect([tx, T(w * 0.08), tx + T(w * 0.4), T(w * 0.08) + th], 12, { fill: 'inkShadow', outline: OUTLINE, width: 4 });
    d.circ(tx + T(w * 0.2), T(w * 0.2), T(w * 0.05), { fill: 'red' });
    for (let i = 0; i < 3; i++) {
      d.rrect([tx + T(w * 0.07), T(w * 0.34) + i * T(w * 0.06), tx + T(w * 0.33), T(w * 0.34) + i * T(w * 0.06) + 8], 4, { fill: 'inkSoft' });
    }
  },
};

// ---------------------------------------------------------------- part icons (200x200 design grid)
const PART_KINDS = ['cpu', 'ram', 'ssd', 'display', 'gpu', 'battery'];

const partIcon = {
  defaults: { kind: 'cpu', s: 170, color: 'paper' },
  size: ({ s }) => ({ w: s, h: s }),
  draw(d, { kind, s, color }) {
    if (!PART_KINDS.includes(kind)) throw new Error(`partIcon: unknown kind '${kind}' (${PART_KINDS.join(', ')})`);
    const k = s / 200, accent = 'red';
    const box = (x0, y0, x1, y1) => [x0 * k, y0 * k, x1 * k, y1 * k];
    if (kind === 'cpu') {
      for (let i = 0; i < 5; i++) {
        const p = 40 + i * 30;
        d.line([[p * k, 22 * k], [p * k, 40 * k]], color, 6 * k, false); d.line([[p * k, 160 * k], [p * k, 178 * k]], color, 6 * k, false);
        d.line([[22 * k, p * k], [40 * k, p * k]], color, 6 * k, false); d.line([[160 * k, p * k], [178 * k, p * k]], color, 6 * k, false);
      }
      d.rrect(box(40, 40, 160, 160), 16 * k, { fill: 'inkShadow', outline: color, width: 6 * k });
      d.rrect(box(72, 72, 128, 128), 8 * k, { fill: accent });
    } else if (kind === 'ram') {
      d.rrect(box(12, 62, 188, 138), 8 * k, { fill: 'inkShadow', outline: color, width: 6 * k });
      for (let i = 0; i < 4; i++) d.rrect(box(28 + i * 38, 78, 54 + i * 38, 106), 4 * k, { fill: i % 2 === 0 ? accent : color });
      for (let i = 0; i < 12; i++) d.rect(box(20 + i * 13.5, 138, 26 + i * 13.5, 152), { fill: 'salmon' });
    } else if (kind === 'ssd') {
      d.rrect(box(26, 50, 174, 150), 12 * k, { fill: 'inkShadow', outline: color, width: 6 * k });
      d.rrect(box(44, 68, 100, 100), 6 * k, { fill: accent }); d.rrect(box(112, 68, 156, 100), 6 * k, { fill: color });
      d.rrect(box(44, 112, 156, 126), 6 * k, { fill: 'gray4' }); d.circ(158 * k, 134 * k, 6 * k, { fill: 'blush' });
    } else if (kind === 'display') {
      d.rrect(box(14, 34, 186, 142), 12 * k, { fill: 'inkShadow', outline: color, width: 6 * k });
      d.rrect(box(28, 48, 172, 128), 6 * k, { fill: 'inkSoft' });
      d.poly([[28, 128], [80, 86], [110, 112], [132, 94], [172, 128]].map(([x, y]) => [x * k, y * k]), { fill: 'blush' });
      d.circ(142 * k, 70 * k, 10 * k, { fill: 'salmon' }); d.rrect(box(70, 150, 130, 162), 5 * k, { fill: color });
    } else if (kind === 'gpu') {
      d.rrect(box(10, 56, 190, 142), 10 * k, { fill: 'inkShadow', outline: color, width: 6 * k });
      for (const fx of [62, 128]) {
        d.circ(fx * k, 99 * k, 28 * k, { fill: 'inkShadow', outline: color, width: 5 * k });
        for (let a = 0; a < 360; a += 72) {
          d.line([[fx * k, 99 * k], [(fx + 20 * Math.cos(rad(a))) * k, (99 + 20 * Math.sin(rad(a))) * k]], accent, 5 * k, false);
        }
        d.circ(fx * k, 99 * k, 5 * k, { fill: color });
      }
      for (let i = 0; i < 10; i++) d.rect(box(22 + i * 10, 142, 27 + i * 10, 156), { fill: 'salmon' });
    } else {
      d.rrect(box(14, 56, 170, 144), 14 * k, { fill: 'inkShadow', outline: color, width: 6 * k });
      d.rrect(box(170, 82, 188, 118), 5 * k, { fill: color });
      for (let i = 0; i < 3; i++) d.rrect(box(28 + i * 42, 70, 60 + i * 42, 130), 6 * k, { fill: 'blush' });
      d.poly([[104, 62], [84, 104], [100, 104], [92, 142], [124, 92], [106, 92]].map(([x, y]) => [x * k, y * k]),
        { fill: 'salmon', outline: OUTLINE, width: 2 * k });
    }
  },
};

// ---------------------------------------------------------------- people
const EXPRESSIONS = ['smile', 'excited', 'frustrated', 'confused', 'talk1', 'talk2', 'confident'];
const POSES = {
  stand: [[[[104, 290], [84, 410], [86, 500]], [86, 512]], [[[296, 290], [316, 410], [314, 500]], [314, 512]]],
  hold: [[[[104, 290], [70, 410], [150, 440]], [160, 446]], [[[296, 290], [330, 410], [250, 440]], [240, 446]]],
  shrug: [[[[104, 290], [52, 400], [40, 330]], [38, 316]], [[[296, 290], [348, 400], [360, 330]], [362, 316]]],
  talk: [[[[104, 290], [84, 410], [86, 500]], [86, 512]], [[[296, 290], [350, 380], [360, 296]], [362, 270]]],
  paper: [[[[104, 290], [84, 410], [86, 500]], [86, 512]], [[[296, 290], [350, 350], [318, 260]], [316, 240]]],
  scratch: [[[[104, 290], [84, 410], [86, 500]], [86, 512]], [[[296, 290], [356, 210], [300, 100]], [292, 88]]],
  cross: [[[[104, 290], [90, 400], [190, 380]], [200, 384]], [[[296, 290], [310, 400], [210, 380]], [200, 384]]],
};

function curlyHair(d, cx, cy, r, col) {
  for (let a = 190; a < 351; a += 16) {
    d.circ(cx + (r + 4) * Math.cos(rad(a)), cy + (r + 4) * Math.sin(rad(a)) * 0.95, r * 0.40, { fill: col, outline: OUTLINE, width: 3 });
  }
  for (let a = 205; a < 336; a += 22) d.circ(cx + r * 0.62 * Math.cos(rad(a)), cy + r * 0.7 * Math.sin(rad(a)), r * 0.42, { fill: col });
  d.circ(cx, cy - r * 0.55, r * 0.7, { fill: col });
}

function face(d, cx, cy, expr, skin, blink) {
  const ex = 34, ey = -4, E = 'inkShadow';
  const eye = (x, y, kind) => {
    if (blink) { d.line([[x - 13, y + 2], [x + 13, y + 2]], E, 5); return; }
    if (kind === 'open') { d.ell([x - 12, y - 17, x + 12, y + 17], { fill: E }); d.circ(x + 4, y - 7, 5, { fill: 'paper' }); }
    else if (kind === 'big') {
      d.ell([x - 15, y - 21, x + 15, y + 21], { fill: E }); d.circ(x + 5, y - 9, 7, { fill: 'paper' }); d.circ(x - 5, y + 8, 3.5, { fill: 'paper' });
    } else if (kind === 'half') {
      d.ell([x - 12, y - 12, x + 12, y + 14], { fill: E }); d.rect([x - 14, y - 14, x + 14, y - 3], { fill: skin });
      d.line([[x - 14, y - 3], [x + 14, y - 3]], OUTLINE, 4, false); d.circ(x + 3, y + 3, 3.5, { fill: 'paper' });
    } else if (kind === 'side') {
      d.ell([x - 12, y - 16, x + 12, y + 16], { fill: 'paper', outline: OUTLINE, width: 3 }); d.circ(x + 5, y - 6, 7, { fill: E });
    }
  };
  const brow = (x0, y0, x1, y1, w = 7) => d.line([[x0, y0], [x1, y1]], E, w);
  const L = cx - ex, R = cx + ex;
  const droplet = x => {
    d.ell([x - 8, cy - (x > cx ? 20 : 12), x + 8, cy + (x > cx ? 8 : 16)], { fill: 'inkSoft', outline: OUTLINE, width: 2 });
  };
  if (expr === 'excited') {
    eye(L, cy + ey, 'big'); eye(R, cy + ey, 'big');
    brow(L - 16, cy - 34, L + 14, cy - 40); brow(R - 14, cy - 40, R + 16, cy - 34);
    d.rrect([cx - 26, cy + 30, cx + 26, cy + 66], 22, { fill: 'redDeep', outline: OUTLINE, width: 3 });
    d.rect([cx - 22, cy + 33, cx + 22, cy + 42], { fill: 'paper' }); d.ell([cx - 14, cy + 50, cx + 14, cy + 68], { fill: 'red' });
    d.circ(L - 12, cy + 28, 11, { fill: 'salmon' }); d.circ(R + 12, cy + 28, 11, { fill: 'salmon' });
  } else if (expr === 'frustrated') {
    eye(L, cy + ey + 4, 'half'); eye(R, cy + ey + 4, 'half');
    brow(L - 18, cy - 44, L + 14, cy - 28, 8); brow(R + 18, cy - 44, R - 14, cy - 28, 8);
    d.arc([cx - 24, cy + 44, cx + 24, cy + 84], 200, 340, E, 6);
    for (const i of [-18, 0, 18]) d.line([[cx + i, cy - 96], [cx + i, cy - 70]], 'inkSoft', 4, false);
    droplet(R + 38); d.poly([[R + 38, cy - 36], [R + 30, cy - 16], [R + 46, cy - 16]], { fill: 'inkSoft' });
  } else if (expr === 'confused') {
    eye(L, cy + ey, 'side'); eye(R, cy + ey, 'side');
    brow(L - 16, cy - 30, L + 14, cy - 38); brow(R - 14, cy - 46, R + 16, cy - 30);
    d.line([[cx - 22, cy + 54], [cx - 10, cy + 46], [cx + 2, cy + 56], [cx + 14, cy + 46], [cx + 24, cy + 54]], E, 6);
    droplet(L - 40); d.poly([[L - 40, cy - 28], [L - 48, cy - 8], [L - 32, cy - 8]], { fill: 'inkSoft' });
  } else if (expr === 'talk1' || expr === 'talk2') {
    eye(L, cy + ey, 'open'); eye(R, cy + ey, 'open'); brow(L - 16, cy - 36, L + 14, cy - 40); brow(R - 14, cy - 40, R + 16, cy - 36);
    if (expr === 'talk1') {
      d.ell([cx - 20, cy + 36, cx + 20, cy + 72], { fill: 'redDeep', outline: OUTLINE, width: 3 }); d.ell([cx - 11, cy + 54, cx + 11, cy + 70], { fill: 'red' });
    } else {
      d.ell([cx - 14, cy + 44, cx + 14, cy + 62], { fill: 'redDeep', outline: OUTLINE, width: 3 });
    }
  } else if (expr === 'confident') {
    eye(L, cy + ey, 'open'); eye(R, cy + ey, 'open'); brow(L - 16, cy - 36, L + 14, cy - 40); brow(R - 14, cy - 46, R + 16, cy - 40);
    d.arc([cx - 30, cy + 22, cx + 30, cy + 70], 20, 160, E, 7); d.circ(L - 12, cy + 28, 10, { fill: 'salmon' }); d.circ(R + 12, cy + 28, 10, { fill: 'salmon' });
  } else {
    eye(L, cy + ey, 'open'); eye(R, cy + ey, 'open'); brow(L - 16, cy - 36, L + 14, cy - 40); brow(R - 14, cy - 40, R + 16, cy - 36);
    d.arc([cx - 28, cy + 20, cx + 28, cy + 66], 20, 160, E, 7);
  }
}

const person = {
  defaults: { shirt: 'red', expr: 'smile', pose: 'stand', skin: 'salmon', pants: 'ink', hair: 'inkShadow',
              hairstyle: 'curly', tie: null, collar: null, blink: false },
  size: () => ({ w: 400, h: 780 }),
  draw(d, { shirt, expr, pose, skin, pants, hair, hairstyle, tie, collar, blink }) {
    if (!Object.hasOwn(POSES, pose)) throw new Error(`person: unknown pose '${pose}' (${Object.keys(POSES).join(', ')})`);
    if (!EXPRESSIONS.includes(expr)) throw new Error(`person: unknown expr '${expr}' (${EXPRESSIONS.join(', ')})`);
    const cx = 200, cy = 150;
    for (const x of [155, 245]) {
      d.rrect([x - 42, 470, x + 42, 730], 30, { fill: pants, outline: OUTLINE, width: 4 });
      d.rrect([x - 50, 716, x + 50, 758], 20, { fill: 'inkShadow', outline: OUTLINE, width: 4 });
    }
    d.rrect([84, 246, 316, 500], 70, { fill: shirt, outline: OUTLINE, width: 4 });
    if (collar) d.poly([[170, 246], [230, 246], [200, 300]], { fill: collar, outline: OUTLINE, width: 3 });
    if (tie) d.poly([[190, 296], [210, 296], [218, 380], [200, 404], [182, 380]], { fill: tie, outline: OUTLINE, width: 3 });
    for (const [points, hand] of POSES[pose]) {
      d.line(points, OUTLINE, 60); d.line(points, shirt, 52);
      d.circ(hand[0], hand[1], 30, { fill: OUTLINE }); d.circ(hand[0], hand[1], 26, { fill: skin });
    }
    d.rrect([172, 214, 228, 268], 16, { fill: skin, outline: OUTLINE, width: 3 });
    if (hairstyle === 'curly') curlyHair(d, cx, cy, 100, hair);
    d.circ(cx, cy, 100, { fill: skin, outline: OUTLINE, width: 4 });
    d.circ(cx - 100, cy + 6, 16, { fill: skin, outline: OUTLINE, width: 3 }); d.circ(cx + 100, cy + 6, 16, { fill: skin, outline: OUTLINE, width: 3 });
    if (hairstyle === 'curly') {
      for (let a = 205; a < 336; a += 26) d.circ(cx + 86 * Math.cos(rad(a)), cy + 78 * Math.sin(rad(a)), 26, { fill: hair });
    } else {
      d.poly([[cx - 102, cy - 10], [cx - 96, cy - 72], [cx - 40, cy - 104], [cx + 40, cy - 108], [cx + 98, cy - 70],
              [cx + 102, cy - 10], [cx + 70, cy - 46], [cx - 20, cy - 62], [cx - 70, cy - 36]], { fill: hair, outline: OUTLINE, width: 3 });
    }
    face(d, cx, cy, expr, skin, blink);
  },
};

// ---------------------------------------------------------------- props
const paperSpec = {
  defaults: { w: 200, checks: 5 },
  size: ({ w }) => ({ w, h: Math.trunc(w * 1.25) + 10 }),
  draw(d, { w, checks }) {
    const h = Math.trunc(w * 1.25);
    d.rrect([0, 0, w, h], 10, { fill: 'paper', outline: OUTLINE, width: 4 });
    for (let i = 0; i < 5; i++) {
      const y = 26 + i * Math.trunc(h / 6.4);
      d.rrect([w * 0.30, y, w * 0.88, y + 10], 4, { fill: 'gray3' });
      if (i < checks) d.line([[w * 0.08, y + 6], [w * 0.14, y + 14], [w * 0.24, y - 2]], 'blush', 5);
    }
  },
};

const followButton = {
  defaults: { w: 520, h: 150, done: false, label: 'تابع', doneLabel: 'تمت المتابعة' },
  size: ({ w, h }) => ({ w, h }),
  draw(d, { w, h, done, label, doneLabel }) {
    d.rrect([0, 0, w, h], h * 0.5, { fill: done ? 'ink' : 'red', outline: done ? 'gray4' : 'paper', width: 4 });
    if (done) {
      d.line([[w * 0.16, h * 0.52], [w * 0.2, h * 0.66], [w * 0.28, h * 0.36]], 'blush', 10);
      d.text([w * 0.62, h * 0.5], doneLabel, 46, 'paper', { rtl: true });
    } else {
      d.circ(w * 0.17, h / 2, h * 0.28, { fill: 'paper' });
      d.line([[w * 0.17 - 15, h / 2], [w * 0.17 + 15, h / 2]], 'red', 8); d.line([[w * 0.17, h / 2 - 15], [w * 0.17, h / 2 + 15]], 'red', 8);
      d.text([w * 0.60, h * 0.5], label, 64, 'paper', { rtl: true });
    }
  },
};

const cursor = {
  defaults: { s: 90 },
  size: ({ s }) => ({ w: s, h: s }),
  draw(d) {
    d.poly([[8, 6], [8, 62], [24, 48], [36, 76], [48, 70], [36, 44], [58, 44]], { fill: 'paper', outline: OUTLINE, width: 4 });
  },
};

const sparkle = {
  defaults: { r: 40, color: 'paper' },
  size: ({ r }) => ({ w: r * 2 + 4, h: r * 2 + 4 }),
  draw(d, { r, color }) {
    const c = r + 2, q = r * 0.18;
    d.poly([[c, c - r], [c + q, c - q], [c + r, c], [c + q, c + q], [c, c + r], [c - q, c + q], [c - r, c], [c - q, c - q]], { fill: color });
  },
};

const pill = {
  defaults: { w: 300, h: 80, color: 'ink', alpha: 255, r: null },
  size: ({ w, h }) => ({ w, h }),
  draw(d, { w, h, color, alpha, r }) { d.rrect([0, 0, w, h], r || Math.floor(h / 2), { fill: artColor(color, alpha) }); },
};

const bill = {
  defaults: { w: 150, label: 'EGP' },
  size: ({ w }) => ({ w, h: Math.trunc(w * 0.55) }),
  draw(d, { w, label }) {
    const h = Math.trunc(w * 0.55);
    d.rrect([0, 0, w, h], 10, { fill: 'blush', outline: 'inkSoft', width: 4 });
    d.circ(w / 2, h / 2, h * 0.3, { fill: 'paper', outline: 'inkSoft', width: 3 });
    d.text([w / 2, h / 2], label, Math.trunc(h * 0.26), 'inkSoft');
    d.rrect([10, 10, 34, 22], 4, { fill: 'inkSoft' }); d.rrect([w - 34, h - 22, w - 10, h - 10], 4, { fill: 'inkSoft' });
  },
};

const checkmark = {
  defaults: { s: 90, color: 'blush', bg: true },
  size: ({ s }) => ({ w: s, h: s }),
  draw(d, { s, color, bg }) {
    if (bg) d.circ(s / 2, s / 2, s / 2 - 2, { fill: color });
    d.line([[s * 0.27, s * 0.52], [s * 0.44, s * 0.69], [s * 0.74, s * 0.34]], bg ? 'paper' : color, s * 0.11);
  },
};

const crossmark = {
  defaults: { s: 90, color: 'red' },
  size: ({ s }) => ({ w: s, h: s }),
  draw(d, { s, color }) {
    d.circ(s / 2, s / 2, s / 2 - 2, { fill: color });
    d.line([[s * 0.3, s * 0.3], [s * 0.7, s * 0.7]], 'paper', s * 0.11); d.line([[s * 0.7, s * 0.3], [s * 0.3, s * 0.7]], 'paper', s * 0.11);
  },
};

const BUBBLE_TAILS = ['bl', 'br', 'bc', 'none'];

const bubble = {
  defaults: { w: 520, h: 180, color: 'paper', tail: 'bl', alpha: 255, outline: null },
  size: ({ w, h }) => ({ w: w + 40, h: h + 50 }),
  draw(d, { w, h, color, tail, alpha, outline }) {
    if (!BUBBLE_TAILS.includes(tail)) throw new Error(`bubble: unknown tail '${tail}' (${BUBBLE_TAILS.join(', ')})`);
    const fill = artColor(color, alpha);
    d.rrect([20, 10, 20 + w, 10 + h], h < 200 ? h * 0.28 : 40, { fill, outline, width: outline ? 4 : 0 });
    if (tail === 'bl') d.poly([[60, 10 + h - 4], [40, 10 + h + 34], [110, 10 + h - 4]], { fill });
    else if (tail === 'br') d.poly([[w - 70, 10 + h - 4], [w - 10, 10 + h + 34], [w, 10 + h - 4]], { fill });
    else if (tail === 'bc') d.poly([[w / 2 - 20, 10 + h - 4], [w / 2 + 20, 10 + h + 34], [w / 2 + 50, 10 + h - 4]], { fill });
  },
};

/** Every sprite engine P draws in `art.py` / `lib.py`, by name. */
export const ART = {
  laptop, desktop, partIcon, person, paperSpec, followButton, cursor, sparkle, pill, bill, checkmark, crossmark, bubble,
};
export const ART_NAMES = Object.keys(ART);
export const ART_OPTIONS = {
  laptopScreens: Object.keys(LAPTOP_SCREEN), partKinds: PART_KINDS, personPoses: Object.keys(POSES),
  personExpressions: EXPRESSIONS, bubbleTails: BUBBLE_TAILS,
};

function spec(name) {
  const entry = ART[name];
  if (!entry) throw new Error(`art: unknown sprite '${name}' (${ART_NAMES.join(', ')})`);
  return entry;
}

/** The sprite's box `{ w, h }` in design pixels — identical to engine P's sprite size. */
export function artSize(name, options = {}) {
  const entry = spec(name);
  return entry.size({ ...entry.defaults, ...options });
}

/**
 * Draw one sprite so its anchor lands on (cx, cy).
 * place: { scale = 1, rot = 0 (degrees), alpha = 1, anchor = [0.5, 0.5], flipX = false }
 */
export function drawArt(ctx, name, cx, cy, options = {}, place = {}) {
  const entry = spec(name);
  const opts = { ...entry.defaults, ...options };
  const { scale = 1, rot = 0, alpha = 1, anchor = [0.5, 0.5], flipX = false } = place;
  if (alpha <= 0.003 || scale <= 0.003) return;
  const { w, h } = entry.size(opts);
  const paint = target => { target.lineJoin = 'round'; entry.draw(new Pen(target), opts); };
  ctx.save();
  ctx.translate(cx, cy);
  if (rot) ctx.rotate(rad(rot));
  ctx.scale(flipX ? -scale : scale, scale);
  ctx.translate(-anchor[0] * w, -anchor[1] * h);
  if (alpha >= 0.997) {
    paint(ctx);
  } else {
    // Engine P fades a finished sprite. Fading shape by shape would let the overlaps show through,
    // so the sprite is painted opaque on its own surface first.
    const k = Math.max(1, Math.min(3, Math.ceil(scale * 2)));
    const surface = typeof OffscreenCanvas === 'function'
      ? new OffscreenCanvas(Math.ceil(w * k), Math.ceil(h * k))
      : Object.assign(document.createElement('canvas'), { width: Math.ceil(w * k), height: Math.ceil(h * k) });
    const inner = surface.getContext('2d');
    inner.scale(k, k);
    paint(inner);
    ctx.globalAlpha *= alpha;
    ctx.drawImage(surface, 0, 0, w, h);
  }
  ctx.restore();
}

export default { ART, ART_NAMES, ART_OPTIONS, artColor, artSize, drawArt };
