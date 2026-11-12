// Exploded-view preview: six SVG frames built from `machine-kit.js` itself.
// Deterministic — no clock, no RNG, no canvas backend. Run twice, compare bytes.
import { readFileSync, writeFileSync } from 'node:fs';
import { buildMachineScene, drawMachineGeometry } from '../shared/js/machine-kit.js';

const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const n = v => (Number.isFinite(v) ? Math.round(v * 100) / 100 : 0);

/** Minimal Canvas2D recorder: transforms + polygons/lines/circles → SVG. */
function recorder() {
  const out = [];
  let m = [1, 0, 0, 1, 0, 0]; // a b c d e f
  const stack = [];
  const pt = (x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
  let path = [];
  let dash = [];
  const ctx = {
    canvas: { width: 1080, height: 1920 },
    globalAlpha: 1, fillStyle: '#000', strokeStyle: '#000', lineWidth: 1, lineJoin: 'round', lineCap: 'round',
    save() { stack.push({ m: [...m], alpha: ctx.globalAlpha, fill: ctx.fillStyle, stroke: ctx.strokeStyle, w: ctx.lineWidth, dash: [...dash] }); },
    restore() {
      const s = stack.pop();
      if (!s) return;
      m = s.m; ctx.globalAlpha = s.alpha; ctx.fillStyle = s.fill; ctx.strokeStyle = s.stroke; ctx.lineWidth = s.w; dash = s.dash;
    },
    translate(x, y) { m = [m[0], m[1], m[2], m[3], m[4] + m[0] * x + m[2] * y, m[5] + m[1] * x + m[3] * y]; },
    scale(sx, sy) { m = [m[0] * sx, m[1] * sx, m[2] * sy, m[3] * sy, m[4], m[5]]; },
    rotate(a) {
      const c = Math.cos(a); const s = Math.sin(a);
      m = [m[0] * c + m[2] * s, m[1] * c + m[3] * s, m[0] * -s + m[2] * c, m[1] * -s + m[3] * c, m[4], m[5]];
    },
    setLineDash(d) { dash = d || []; },
    beginPath() { path = []; },
    moveTo(x, y) { path.push(['M', pt(x, y)]); },
    lineTo(x, y) { path.push(['L', pt(x, y)]); },
    closePath() { path.push(['Z']); },
    arc(cx, cy, r, a0, a1) { path.push(['A', pt(cx, cy), r, a0, a1]); },
    fill() {
      const verts = path.filter(p => p[0] !== 'Z').map(p => p[1]);
      if (verts.length < 3) return;
      out.push(`<polygon points="${verts.map(v => `${n(v[0])},${n(v[1])}`).join(' ')}" fill="${esc(ctx.fillStyle)}" fill-opacity="${n(ctx.globalAlpha)}"/>`);
    },
    stroke() {
      const pts = path.map((p, i) => {
        if (p[0] === 'A') {
          const [c, r] = [p[1], p[2]];
          return null;
        }
        return p[1];
      }).filter(Boolean);
      const d = dash.length ? ` stroke-dasharray="${dash.map(n).join(' ')}"` : '';
      if (path.some(p => p[0] === 'A')) {
        for (const p of path.filter(p => p[0] === 'A')) {
          out.push(`<circle cx="${n(p[1][0])}" cy="${n(p[1][1])}" r="${n(p[2])}" fill="none" stroke="${esc(ctx.strokeStyle)}" stroke-width="${n(ctx.lineWidth)}" opacity="${n(ctx.globalAlpha)}"/>`);
        }
      }
      if (pts.length >= 2) {
        out.push(`<polyline points="${pts.map(v => `${n(v[0])},${n(v[1])}`).join(' ')}" fill="none" stroke="${esc(ctx.strokeStyle)}" stroke-width="${n(ctx.lineWidth)}" stroke-linecap="${ctx.lineCap}" stroke-linejoin="${ctx.lineJoin}"${d} opacity="${n(ctx.globalAlpha)}"/>`);
      }
    },
  };
  return { ctx, out };
}

const [input, output] = process.argv.slice(2);
if (!input || !output) {
  console.error('usage: node tools/machine_explode_preview.mjs <machine-spec.json> <out.html>');
  process.exit(2);
}
const spec = JSON.parse(readFileSync(input, 'utf8'));
const cfg = spec.explode || { start: spec.start, end: spec.end };
const fractions = [0, 0.22, 0.42, 0.55, 0.76, 0.94];
const times = fractions.map(f => Math.min(cfg.end - 1e-4, cfg.start + (cfg.end - cfg.start) * f));

const FRAMING = { originX: 540, originY: 960, scale: 2.0 };
const built = times.map(time => ({ graph: buildMachineScene(spec, time, { theme: 'dark', ...FRAMING }), time }));

// One viewBox for every frame: the union of all six, so growing/shrinking is visible.
let minX = Infinity; let minY = Infinity; let maxX = -Infinity; let maxY = -Infinity;
for (const { graph } of built) {
  minX = Math.min(minX, graph.bounds.x);
  minY = Math.min(minY, graph.bounds.y);
  maxX = Math.max(maxX, graph.bounds.x + graph.bounds.w);
  maxY = Math.max(maxY, graph.bounds.y + graph.bounds.h);
}
const pad = 42;
const view = { x: minX - pad, y: minY - pad, w: maxX - minX + pad * 2, h: maxY - minY + pad * 2 };

const frames = built.map(({ graph, time }) => {
  const { ctx, out } = recorder();
  drawMachineGeometry(ctx, graph);
  return { graph, time, svg: out };
});

const cells = frames.map(frame => {
  const g = frame.graph;
  return `<figure><svg viewBox="${n(view.x)} ${n(view.y)} ${n(view.w)} ${n(view.h)}" width="300" role="img" aria-label="explode ${g.explode.phase} ${g.explode.amount}">`
    + `<rect x="${n(view.x)}" y="${n(view.y)}" width="${n(view.w)}" height="${n(view.h)}" fill="#0A0A0A"/>`
    + `<g>${frame.svg.join('')}</g>`
    + `</svg><figcaption>t=${frame.time.toFixed(2)}s · ${g.explode.phase} · amount ${g.explode.amount.toFixed(3)} · w ${Math.round(g.bounds.w)}</figcaption></figure>`;
}).join('');

const html = `<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<title>Exploded view — machine kit</title>
<style>
 body{font:14px/1.55 system-ui,sans-serif;background:#111;color:#F3F2F1;margin:24px}
 h1{font-size:19px;margin:0 0 4px} p{color:#A3A2A0;margin:0 0 22px;font-size:13px}
 .row{display:flex;gap:16px;flex-wrap:wrap} figure{margin:0;text-align:center}
 figcaption{font-size:11.5px;color:#A3A2A0;margin-top:6px;direction:ltr}
 svg{border-radius:10px;border:1px solid #262626}
</style>
<h1>Exploded view — ${esc(spec.id)}</h1>
<p>ستة إطارات من نفس <code>buildMachineScene</code>: فتح → ثبات → رجوع. البنية تُترجم في العالم ثلاثي الأبعاد قبل الإسقاط، فالترتيب والحجم يتغيّران مع الحركة.</p>
<div class="row">${cells}</div>
</html>`;

writeFileSync(output, html);
console.log(`wrote ${output} (${frames.length} frames, deterministic)`);
