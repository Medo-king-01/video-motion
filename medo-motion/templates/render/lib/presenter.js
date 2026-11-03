import { protectBox } from './layout.js';
// Medo, the presenter — engine K.
//
// The poses come from `assets/poses/` (`<slug>.png` + `poses.json`, built by
// `tools/presenter_build.py`): transparent cut-outs normalised to the same figure height with the
// feet on the same baseline, so switching pose never makes him jump.
//
// This module adds what the images can't do on their own: idle life (breathing, bob, sway),
// pose acting with cross-fades, and placement on the brand ground line. The numbers are the same as
// presenter.py, so engine P breathes identically.
import { clamp } from './motion.js';

export const GROUND = 1390;      // soles land here for full shots
export const TOP_GUIDE = 190;    // hair line for close-ups

// Embedded fallback (a project that only received templates/ still works); poses.json wins.
const DEFAULT_POSES = {
  neutral: { file: 'neutral.png', scale: 1.0, place: 'feet' },
  explain: { file: 'explain.png', scale: 1.0, place: 'feet' },
  point: { file: 'point.png', scale: 1.0, place: 'feet' },
  welcome: { file: 'welcome.png', scale: 1.0, place: 'feet' },
  wave: { file: 'wave.png', scale: 1.0, place: 'feet' },
  clap: { file: 'clap.png', scale: 1.0, place: 'feet' },
  like: { file: 'like.png', scale: 1.0, place: 'feet' },
  thinking: { file: 'thinking.png', scale: 1.0, place: 'feet' },
  'thinking-deep': { file: 'thinking-deep.png', scale: 0.86, place: 'feet' },
  puzzled: { file: 'puzzled.png', scale: 1.0, place: 'feet' },
  sad: { file: 'sad.png', scale: 1.0, place: 'feet' },
  shocked: { file: 'shocked.png', scale: 1.0, place: 'feet' },
  walk: { file: 'walk.png', scale: 0.97, place: 'feet' },
  run: { file: 'run.png', scale: 0.94, place: 'feet' },
  waiting: { file: 'waiting.png', scale: 1.0, place: 'feet' },
  warm: { file: 'warm.png', scale: 1.0, place: 'feet' },
  phone: { file: 'phone.png', scale: 1.0, place: 'feet' },
  unfold: { file: 'unfold.png', scale: 1.0, place: 'feet' },
  'point-up': { file: 'point-up.png', scale: 1.0, place: 'feet' },
  'seated-talk': { file: 'seated-talk.png', scale: 1.0, place: 'feet' },
  'close-neutral': { file: 'close-neutral.png', scale: 1.0, place: 'top' },
  'close-explain': { file: 'close-explain.png', scale: 1.0, place: 'top' },
  'close-point': { file: 'close-point.png', scale: 1.0, place: 'top' },
  'close-thinking': { file: 'close-thinking.png', scale: 1.0, place: 'top' },
};

const ALIASES = {
  medo: 'neutral', medo_neutral: 'neutral', medo_wave: 'wave', medo_think: 'thinking',
  medo_thinking: 'thinking', medo_deep: 'thinking-deep', medo_point: 'point',
  medo_explain: 'explain', medo_welcome: 'welcome', medo_clap: 'clap', medo_like: 'like',
  medo_puzzled: 'puzzled', medo_sad: 'sad', medo_shocked: 'shocked', medo_walk: 'walk', medo_run: 'run',
};

let POSES = { ...DEFAULT_POSES };
const IMAGES = new Map();
let basePath = '/assets/poses/';

export function poseNames() { return Object.keys(POSES); }
export function resolve(name) { const n = ALIASES[name] || name; return POSES[n] ? n : 'neutral'; }

/** Load the manifest + every image (call from the scene's init(), once). */
export async function loadPoses(base = '/assets/poses/') {
  basePath = base.endsWith('/') ? base : `${base}/`;
  try {
    const res = await fetch(`${basePath}poses.json`, { cache: 'force-cache' });
    if (res.ok) {
      const data = await res.json();
      if (data && data.poses) POSES = { ...DEFAULT_POSES, ...data.poses };
    }
  } catch { /* offline project without the manifest → defaults */ }
  await Promise.all(Object.entries(POSES).map(async ([slug, meta]) => {
    const img = new Image();
    img.src = basePath + (meta.file || `${slug}.png`);
    try { await img.decode(); IMAGES.set(slug, img); } catch { /* missing file: draw() no-ops */ }
  }));
  return POSES;
}

export const image = slug => IMAGES.get(resolve(slug));

// ---------- idle motion (identical to presenter.py) ----------
export const breathe = t => 1 + 0.008 * Math.sin(2 * Math.PI * 0.28 * t);
export const bob = (t, amount = 2.5) => amount * Math.sin(2 * Math.PI * 0.22 * t);
export const sway = (t, amount = 2) => amount * Math.sin(2 * Math.PI * 0.13 * t + 0.7);

export function lean(name, t) {
  const slug = resolve(name);
  if (slug === 'wave') return 1.1 * Math.sin(2 * Math.PI * 1.05 * t);
  if (slug === 'clap') return 0.6 * Math.sin(2 * Math.PI * 2.2 * t);
  if (slug === 'run' || slug === 'walk') return 1.4 * Math.sin(2 * Math.PI * 1.6 * t);
  if (slug === 'thinking' || slug === 'thinking-deep') return 0.35 * Math.sin(2 * Math.PI * 0.09 * t);
  if (slug === 'shocked') return 0.9 * Math.sin(2 * Math.PI * 7 * t) * Math.exp(-((t % 1) * 6));
  return 0.25 * Math.sin(2 * Math.PI * 0.11 * t);
}

export function pulse(name, t) {
  const slug = resolve(name);
  if (slug === 'run') return 7 * Math.abs(Math.sin(2 * Math.PI * 1.6 * t));
  if (slug === 'walk') return 3.5 * Math.abs(Math.sin(2 * Math.PI * 1.0 * t));
  if (slug === 'shocked') return 4 * Math.max(0, Math.sin(2 * Math.PI * 3 * t)) * Math.exp(-((t % 1) * 4));
  return 0;
}

/** The transform for a pose at time t (exported so QA can compare it with engine P). */
export function poseFrame(name, t, { height = 0.62, x = 0.5, ground = GROUND, top = TOP_GUIDE,
  W = 1080, H = 1920, scale } = {}) {
  const slug = resolve(name);
  const meta = POSES[slug] || {};
  const h = Math.max(8, height * H * (scale ?? meta.scale ?? 1));
  const feet = meta.feet ?? 0.9934;
  const img = IMAGES.get(slug);
  const w = img ? (img.naturalWidth / img.naturalHeight) * h : h * 0.45;
  // full shots are placed by their soles, close-ups by their hair line (a clean push-in cut)
  const anchorY = meta.place === 'top' ? top + h / 2 : ground - (feet - 0.5) * h;
  return {
    slug, h, w,
    cx: x * W + sway(t),
    cy: anchorY - bob(t) - pulse(slug, t),
    scale: breathe(t),
    rot: lean(slug, t),
  };
}

export function drawPresenter(ctx, name, t, opts = {}) {
  const f = poseFrame(name, t, opts);
  const img = IMAGES.get(f.slug);
  const alpha = opts.alpha ?? 1;
  if (!img || alpha <= 0.003) return f;
  ctx.save();
  ctx.globalAlpha *= clamp(alpha);
  ctx.translate(f.cx, f.cy);
  ctx.rotate((f.rot * Math.PI) / 180);
  ctx.scale(opts.flip ? -f.scale : f.scale, f.scale);
  const face=opts.faceBoxes ? opts.faceBoxes[f.slug] : opts.faceBox;
  // Face bounds are explicitly measured per pose; never guess from the silhouette.
  if(face) {
    if(!['x','y','w','h'].every(k=>Number.isFinite(face[k]))||face.x<0||face.y<0||face.w<=0||face.h<=0||face.x+face.w>1||face.y+face.h>1)throw Error('Invalid normalized presenter faceBox');
    protectBox(ctx,`face-${f.slug}`,{x:-f.w/2+face.x*f.w,y:-f.h/2+face.y*f.h,w:face.w*f.w,h:face.h*f.h});
  } else protectBox(ctx,`missing-faceBox-${f.slug}`,{x:0,y:0,w:0,h:0});
  ctx.drawImage(img, -f.w / 2, -f.h / 2, f.w, f.h);
  ctx.restore();
  return f;
}

/** Cross-fade between two poses (the acting layer). `p` = 0 → a, 1 → b. */
export function drawPoseBlend(ctx, a, b, p, t, opts = {}) {
  if (a && p < 1) drawPresenter(ctx, a, t, { ...opts, alpha: (opts.alpha ?? 1) * (1 - p) });
  if (b) drawPresenter(ctx, b, t, { ...opts, alpha: (opts.alpha ?? 1) * (0.35 + 0.65 * p) });
}

/** Cue list of poses with cross-fades — mirrors presenter.PoseTrack. */
export class PoseTrack {
  constructor(cues, fade = 0.12) {
    // keep the raw name and resolve at draw time: a track is usually built at module scope, before
    // loadPoses() has fetched the manifest, and eager resolve would freeze the embedded fallback
    this.cues = [...cues].map(c => ({ t: Number(c.t ?? 0), pose: c.pose ?? 'neutral' }))
      .sort((a, b) => a.t - b.t);
    this.fade = fade;
  }

  get duration() { return this.cues.length ? this.cues[this.cues.length - 1].t : 0; }

  at(t) {
    let prev = null;
    let cur = this.cues.length ? this.cues[0].pose : 'neutral';
    let start = 0;
    for (const cue of this.cues) {
      if (cue.t > t + 1e-9) break;
      prev = cur; cur = cue.pose; start = cue.t;
    }
    const blend = (prev === null || prev === cur) ? 1 : clamp((t - start) / Math.max(1e-6, this.fade));
    const fading = blend < 1 && prev !== null && prev !== cur;
    return {
      pose: resolve(cur), prev: fading ? resolve(prev) : null, blend,
      settle: 1 + 0.02 * (1 - blend) ** 2,
    };
  }

  draw(ctx, t, opts = {}) {
    const s = this.at(t);
    // shaped, not a straight dissolve: out by 60%, in from 40% — a pose change reads as a beat cut
    const out = clamp(1 - s.blend / 0.6);
    const into = clamp((s.blend - 0.4) / 0.6);
    if (s.prev && out > 0) drawPresenter(ctx, s.prev, t, { ...opts, alpha: (opts.alpha ?? 1) * out });
    drawPresenter(ctx, s.pose, t, { ...opts, alpha: (opts.alpha ?? 1) * into });
    return s;
  }
}
