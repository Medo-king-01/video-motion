// Real Engine K example: Slide Wall inside the native Fixed Stage renderer.
import { drawDirectedText, useDirectedFonts } from '../lib/captions.js';
import { createSlideWall } from '../lib/slide-wall-canvas.js';
import { loadSlideWall } from '../lib/slide-wall.js';
import { brandHex, normalizeStageSpec } from '../lib/stage.js';
import { renderFixedStage } from '../lib/stage-canvas.js';

export const supportsReducedMotion = true;
export const manualFixedStage = true;
let wall = null;
let stageSpec = null;
let currentMotionMode = 'normal';

async function requiredJson(url) {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`Cannot load ${url}: HTTP ${response.status}`);
  return response.json();
}

export async function init({ motionMode = 'normal', resources } = {}) {
  const [wallSpec, rawStage, direction, copyDoc] = await Promise.all([
    loadSlideWall(), requiredJson('/plan/stage.json'), requiredJson('/plan/text-direction.json'),
    requiredJson('/plan/copy.json'),
  ]);
  stageSpec = normalizeStageSpec(rawStage);
  currentMotionMode = motionMode;
  const copy = Object.fromEntries(copyDoc.copy.map((item) => [item.id, item]));
  await useDirectedFonts(direction, 1);

  wall = createSlideWall(wallSpec, {
    textureWidth: 450,
    slideLayout: (slide, width, height) => [{
      id: 'number', text: copy[slide.id].text,
      x: width * 0.18, y: height * 0.40, w: width * 0.64, h: height * 0.20,
    }],
    drawSlide(ctx, slide, width, height) {
      ctx.fillStyle = brandHex(slide.surfaceRole);
      ctx.fillRect(0, 0, width, height);
      ctx.fillStyle = brandHex(slide.accentRole);
      ctx.fillRect(width * 0.1, height * 0.09, width * 0.8, height * 0.015);
      ctx.fillStyle = brandHex('gray_2');
      ctx.fillRect(width * 0.1, height * 0.82, width * 0.52, height * 0.015);
      const item = copy[slide.id];
      drawDirectedText(ctx, item.text, {
        direction, scene: 1, role: 'number', elementId: item.id,
        time: 1, start: 0, end: 1, x: width / 2, y: height * 0.5,
        size: Math.trunc(width * 0.28), maxWidth: width * 0.82,
        color: brandHex('ink'), accent: brandHex(slide.accentRole), theme: 'light', rtl: false,
      });
    },
  });
  resources?.defer(() => wall.close());

}

export async function draw(ctx, t) {
  await renderFixedStage(ctx, stageSpec, t, {
    duration: 6,
    motionMode: currentMotionMode,
    drawContent: (content, stageState) => wall.draw(content, t, {
      motionMode: currentMotionMode,
      viewport: stageState.win,
    }),
  });
}
