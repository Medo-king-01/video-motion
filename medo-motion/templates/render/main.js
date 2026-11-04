import { useDirectedFonts } from './lib/captions.js';
import { captureLayout } from './lib/layout.js';
import { createResourceScope } from './lib/resource-scope.js';
import { isStageEnabled, normalizeStageSpec } from './lib/stage.js';
import { renderFixedStage } from './lib/stage-canvas.js';
import { captionStyleFor } from './lib/text-direction.js';
import { W, H, scenes } from './data.js';

const params = new URLSearchParams(location.search);
const scale = Number(params.get('scale')) || 1;
const motionMode = params.get('motionMode') || 'normal';
if (!['normal', 'reduced'].includes(motionMode)) throw Error('invalid motion mode');
const hasRange = params.has('rangeStart') && params.has('rangeEnd');
const rangeStart = hasRange ? Number(params.get('rangeStart')) : null;
const rangeEnd = hasRange ? Number(params.get('rangeEnd')) : null;
if (
  params.has('rangeStart') !== params.has('rangeEnd') ||
  (hasRange && (!Number.isFinite(rangeStart) || !Number.isFinite(rangeEnd) || rangeStart < 0 || rangeEnd <= rangeStart))
) {
  throw Error('invalid render range');
}
const active = scenes.map((s) => !hasRange || (s.start < rangeEnd && s.end > rangeStart));
const canvas = document.getElementById('c');
canvas.width = Math.max(2, 2 * Math.round((W * scale) / 2));
canvas.height = Math.max(2, 2 * Math.round((H * scale) / 2));
const auditing = new URLSearchParams(location.search).has('audit');
// Readback QA must not trigger a mid-run GPU→CPU raster-mode change.
const ctx = canvas.getContext('2d', auditing ? { willReadFrequently: true } : {});
const layout = auditing ? captureLayout(ctx) : null;
window.layoutSnapshot = () => (layout ? layout.snapshot() : null);
window.stageWindowSnapshot = () => (layout ? layout.stageWindow() : null);

const mods = await Promise.all(scenes.map((s) => import(`./scenes/${s.id}.js`)));
const scopes = mods.map(() => createResourceScope());
window.closeScenes = async () => {
  const errors = [];
  for (const scope of [...scopes].reverse()) {
    try {
      await scope.close();
    } catch (e) {
      errors.push(e);
    }
  }
  if (errors.length) throw new AggregateError(errors, 'scene resource cleanup failed');
};

async function fetchOptionalJson(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

let direction = null;
let loadedStageSpec = null;
let autoStage = null;
let stageCopyById = {};
let stageDuration = scenes.at(-1)?.end ?? null;
let stageWords = [];

try {
  if (motionMode === 'reduced' && mods.some((m, i) => active[i] && m.supportsReducedMotion !== true)) {
    throw Error('Reduced motion requires every active K scene to explicitly declare supportsReducedMotion');
  }
  direction = await fetchOptionalJson('/plan/text-direction.json');
  const stageRes = await fetch('/plan/stage.json').catch(() => null);
  if (stageRes && stageRes.ok) {
    const rawText = await stageRes.text();
    const trimmed = rawText.trimStart();
    // Ignore SPA dev-server HTML 404 fallbacks when plan/stage.json does not exist;
    // still fail fast on invalid JSON or invalid stage schema when a real file is present.
    if (trimmed && !trimmed.startsWith('<')) {
      const rawStage = JSON.parse(rawText);
      if (isStageEnabled(rawStage)) {
        loadedStageSpec = normalizeStageSpec(rawStage);
        const [copyDoc, beatsDoc, wtDoc] = await Promise.all([
          fetchOptionalJson('/plan/copy.json'),
          fetchOptionalJson('/plan/beats.json'),
          fetchOptionalJson('/plan/word-timings.json'),
        ]);
        if (copyDoc && Array.isArray(copyDoc.copy)) {
          for (const item of copyDoc.copy) {
            if (item && typeof item.id === 'string' && typeof item.text === 'string') {
              stageCopyById[item.id] = item.text;
            }
          }
        }
        if (beatsDoc && Number.isFinite(Number(beatsDoc.duration)) && Number(beatsDoc.duration) > 0) {
          stageDuration = Number(beatsDoc.duration);
        }
        if (wtDoc && Array.isArray(wtDoc.scenes)) {
          for (const sc of wtDoc.scenes) {
            for (const w of sc?.words || []) {
              if (w && Number.isFinite(w.start) && Number.isFinite(w.end)) {
                stageWords.push({ text: String(w.text ?? ''), start: Number(w.start), end: Number(w.end) });
              }
            }
          }
        }
        if (direction && loadedStageSpec.over.header.slots.length > 0) {
          const hdrScenes = [...new Set(loadedStageSpec.over.header.slots.map((sl) => sl.scene))];
          await Promise.all(hdrScenes.map((scNum) => useDirectedFonts(direction, scNum)));
        }
        if (loadedStageSpec.autoWrap !== false) {
          autoStage = loadedStageSpec;
        }
      }
    }
  }

  const initialized = await Promise.allSettled(
    mods.map((m, i) =>
      Promise.resolve().then(() =>
        motionMode === 'normal' || active[i]
          ? m.init?.({ W, H, scale, motionMode, resources: scopes[i] })
          : undefined,
      ),
    ),
  );
  const failures = initialized.filter((r) => r.status === 'rejected').map((r) => r.reason);
  if (failures.length) throw new AggregateError(failures, 'scene initialization failed');
  await document.fonts.ready;
} catch (error) {
  try {
    await window.closeScenes();
  } catch (cleanup) {
    console.error('scene cleanup failed', cleanup);
  }
  window.__error = String(error?.message || error);
}

window.renderFrame = async (t) => {
  if (motionMode === 'reduced' && hasRange && (t < rangeStart || t >= rangeEnd)) {
    throw Error('frame outside reduced-motion render range');
  }
  layout?.begin();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const activeIndices = [];
  for (let i = 0; i < scenes.length; i += 1) {
    if (t >= scenes[i].start && t < scenes[i].end) activeIndices.push(i);
  }
  const sceneHandlesStage = activeIndices.some((i) => mods[i]?.manualFixedStage === true);

  if (autoStage && !sceneHandlesStage) {
    let captionStyle = null;
    if (stageWords.length > 0 && direction && activeIndices.length > 0) {
      const idx = activeIndices[0];
      const scNum = scenes[idx].index ?? idx + 1;
      captionStyle = captionStyleFor(direction, scNum);
    }
    ctx.save();
    try {
      ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
      await renderFixedStage(ctx, autoStage, t, {
        duration: stageDuration,
        direction,
        copyById: stageCopyById,
        words: stageWords.length > 0 ? stageWords : null,
        captionStyle,
        motionMode,
        drawContent: async (c, stageState) => {
          for (const i of activeIndices) {
            const s = scenes[i];
            c.save();
            try {
              await mods[i].draw(c, t - s.start, {
                W,
                H,
                scale,
                dur: s.end - s.start,
                t,
                scene: s,
                direction,
                stage: stageState,
                copyById: stageCopyById,
                motionMode,
                resources: scopes[i],
              });
            } finally {
              c.restore();
            }
          }
        },
      });
    } finally {
      ctx.restore();
    }
    return;
  }

  for (const i of activeIndices) {
    const s = scenes[i];
    ctx.save();
    try {
      ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
      await mods[i].draw(ctx, t - s.start, {
        W,
        H,
        scale,
        dur: s.end - s.start,
        t,
        scene: s,
        direction,
        stageSpec: loadedStageSpec,
        copyById: stageCopyById,
        motionMode,
        resources: scopes[i],
      });
    } finally {
      ctx.restore();
    }
  }
};
window.grab = (type, quality = 0.95) => canvas.toDataURL(type, quality);
if (!window.__error) window.__ready = true;
