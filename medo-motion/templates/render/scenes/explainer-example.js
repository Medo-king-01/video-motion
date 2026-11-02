// Explainer-reel example (Arabic): editorial section → halftone wipe → colour-world section → comment CTA.
// Shows the kit from lib/kit.js. Brand lock: Cairo is the only display face.
// Download it first: python <skill>/scripts/get_fonts.py "Cairo"
import { loadFirstFont } from '../lib/arabic.js';
import * as K from '../lib/kit.js';

const F = '/assets/fonts/';
const FONT_FILES = [
  ['Cairo', ['Cairo/Cairo_800ExtraBold.ttf', 'Cairo/Cairo[wght].ttf'], { weight: '800' }],
  ['JetBrains Mono', ['JetBrains Mono/JetBrainsMono[wght].ttf'], { weight: '400' }],
];
let paper;
export async function init() {
  for (const [family, files, d] of FONT_FILES) await loadFirstFont(family, files.map(f => F + f), d);
  paper = K.paperTile(11);
}

// NOTE: this demo keeps an editorial palette to show the kit's range.
// For a brand reel, copy the tokens from ../lib/brand.js instead.
const INK = '#0A0A0A', RED = '#CB271B', PAPER = '#F3F2F1', BLUE = '#71717A', SKY = '#D5AEA6', YELLOW = '#D97F68';

function sectionOne(ctx, t, W, H) {
  K.drawPaper(ctx, W, H, paper, PAPER);
  K.sectionLabel(ctx, '// 01 · الفكرة', { x: W - 72, y: 170 });
  K.progressPips(ctx, { x: 72, y: 170, total: 3, done: 0, active: 0, rtl: false, label: '١/٣' });
  K.captionBlock(ctx, [
    { w: 'صوّرت', s: 0.1 }, { w: 'فيديو', s: 0.35 }, { w: 'كامل', s: 0.6 }, { w: 'بدون', s: 1.0, key: true }, { w: 'مونتاج', s: 1.3, key: true },
  ], t, { x: W - 90, y: 330, maxWidth: W - 180, size: 66 });

  const ph = K.enter(t, 0.15, { rise: 80 });
  K.phone(ctx, 120, 600 + ph.dy, 400, (sx, sy, sw, sh) => {
    ctx.fillStyle = '#F3F2F1'; ctx.fillRect(sx, sy, sw, sh);
    ctx.fillStyle = INK; ctx.font = K.font(700, 34, K.FONTS.text); ctx.direction = 'rtl'; ctx.textAlign = 'center';
    ctx.fillText('نصيحة اليوم', sx + sw / 2, sy + 190);
    ctx.fillStyle = RED; ctx.font = K.font(700, 44, K.FONTS.accent, K.FONTS.text); ctx.fillText('اختصر وقتك', sx + sw / 2, sy + 255);
    const r = K.rng(5);
    for (let i = 0; i < 26; i++) {                                   // waveform reacting to time
      const h = (12 + r() * 60) * (0.55 + 0.45 * Math.sin(t * 9 + i * 0.7));
      ctx.fillStyle = i < 26 * K.seg(t, 0.4, 2.4) ? RED : 'rgba(3,3,3,.18)';
      ctx.fillRect(sx + 40 + i * ((sw - 80) / 26), sy + sh - 170 - h / 2, 6, h);
    }
  }, { s: ph.s, alpha: ph.alpha, rot: -2 });

  const win = K.enter(t, 0.35, { rise: 60 });
  K.appWindow(ctx, 560, 680 + win.dy, 420, 520, {
    title: 'khaam-motion', s: win.s, alpha: win.alpha, rot: 1.5,
    body: (bx, by, bw) => K.checklist(ctx, [
      { title: 'كتابة الهوك' }, { title: 'تسجيل الصوت' }, { title: 'تحريك المشاهد' }, { title: 'توقيت الكابشن' }, { title: 'الرندر' },
    ], t, { x: bx + 20, y: by + 18, w: bw - 40, rowH: 86, size: 30, start: 0.7, step: 0.42, accent: RED }),
  });
  K.handleTag(ctx, '@khaam.hq', { x: W - 70, y: 1300 });
  K.stamp(ctx, 'جاهز', t, { x: W / 2 + 40, y: 1360, start: 2.85, size: 120, color: RED, rot: -8 });
  K.burst(ctx, W / 2 + 40, 1360, t, { start: 2.95, r: 150, n: 10, color: INK });
}

function sectionTwo(ctx, t, W, H) {
  ctx.fillStyle = SKY; ctx.fillRect(0, 0, W, H);
  K.dotGrid(ctx, W, H, { gap: 40, r: 2.4, color: 'rgba(113,113,122,.25)' });
  ctx.fillStyle = BLUE; ctx.fillRect(0, 1330, W, H - 1330);                 // "desk" band of the colour world
  K.sectionLabel(ctx, '02 · الأدوات', { x: W - 72, y: 172, style: 'tape' });
  K.slotStrip(ctx, t, { x: 70, y: 120, w: 470, total: 4, plugTimes: [4.3, 5.3, 6.3], labels: ['الصوت', 'الخطوط', 'الستايل', '؟'] });

  const c = K.enter(t, 3.95, { rise: 60 });
  K.card(ctx, 100, 470 + c.dy, W - 200, 290, { r: 30, s: c.s, alpha: c.alpha, rot: -1 }, (x, y, w) => {
    ctx.fillStyle = INK; ctx.font = K.font(700, 46, K.FONTS.mono); ctx.direction = 'ltr'; ctx.textAlign = 'left'; ctx.fillText('khaam-motion', x + 44, y + 92);
    ctx.fillStyle = 'rgba(3,3,3,.55)'; ctx.font = K.font(500, 32, K.FONTS.text); ctx.direction = 'rtl'; ctx.textAlign = 'right';
    ctx.fillText('مهارة موشن عربية لـ Claude', x + w - 44, y + 170);
    ctx.fillStyle = INK; ctx.font = K.font(800, 54, K.FONTS.mono); ctx.direction = 'ltr'; ctx.textAlign = 'left';
    ctx.fillText('★ ' + K.rolling(0, 4210, K.seg(t, 4.3, 1.2)), x + 44, y + 245);
  });
  K.circleMark(ctx, 120, 650, 330, 120, { p: K.seg(t, 5.6, 0.45), color: YELLOW });

  const w2 = K.enter(t, 4.6, { rise: 60 });
  K.appWindow(ctx, 100, 820 + w2.dy, W - 200, 400, {
    title: 'claude — ~/my-video', s: w2.s, alpha: w2.alpha, rot: 1,
    body: (bx, by, bw) => K.typeLines(ctx, [
      { text: '> /khaam-motion', color: '#D97F68' },
      '✓ fonts: Cairo',
      '✓ sfx: openverse (CC0)',
      { text: 'جاري تحريك المشاهد…', color: YELLOW },
    ], t, { x: bx + 36, y: by + 70, w: bw - 72, size: 30, start: 4.9, cps: 34 }),
  });

  K.keycaps(ctx, [
    { s: 3.85, e: 5.25, words: [{ w: 'كل', s: 3.9 }, { w: 'شي', s: 4.15 }, { w: 'جاهز', s: 4.45, key: true }] },
    { s: 5.25, e: 7.7, words: [{ w: 'بس', s: 5.3 }, { w: 'اطلب', s: 5.6 }, { w: 'وخلاص', s: 6.0 }] },
  ], t, { x: W / 2, y: 1520, size: 62 });
}

function sectionThree(ctx, t, W, H) {
  K.drawPaper(ctx, W, H, paper, PAPER);
  K.sectionLabel(ctx, '// 03 · الهدية', { x: W - 72, y: 170 });
  K.progressPips(ctx, { x: 72, y: 170, total: 3, done: 2, active: 2, rtl: false, label: '٣/٣' });
  K.captionBlock(ctx, [
    { w: 'علّق', s: 7.75 }, { w: '«موشن»', s: 8.0, key: true }, { w: 'وأرسلها', s: 8.35 }, { w: 'لك', s: 8.6 },
  ], t, { x: W - 90, y: 330, maxWidth: W - 180, size: 66 });
  const f = K.enter(t, 7.7, { rise: 60 });
  K.folder(ctx, W / 2 - 230, 470 + f.dy, 460, { label: 'khaam-motion', tabs: ['SKILL.md', 'styles/', 'fonts/'], p: K.seg(t, 7.9, 0.5), s: f.s, alpha: f.alpha, rot: -2 });
  K.chip(ctx, K.rolling(0, 72, K.seg(t, 8.0, 0.8), { digits: 'arabic' }) + ' ملف', { x: W / 2, y: 860, size: 30, s: K.enter(t, 8.0).s, alpha: K.enter(t, 8.0).alpha });
  K.commentCTA(ctx, t, { x: 110, y: 960, w: W - 220, keyword: 'موشن', start: 8.4, dmTitle: 'وصلتك المهارة 🎁', dmBody: 'khaam-motion.zip', accent: RED });
}

export function draw(ctx, t, { W, H }) {
  if (t < 3.8) sectionOne(ctx, t, W, H);
  else if (t < 7.7) sectionTwo(ctx, t, W, H);
  else sectionThree(ctx, t, W, H);
  K.halftoneWipe(ctx, W, H, K.seg(t, 3.4, 0.8), { origin: [W * 0.8, H * 0.3] });   // chapter 1 → 2
  if (t >= 7.7 && t < 7.8) { ctx.fillStyle = 'rgba(243,242,241,.85)'; ctx.fillRect(0, 0, W, H); }   // 3-frame flash cut into the CTA
}
