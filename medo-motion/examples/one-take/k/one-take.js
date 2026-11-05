// Real Engine K example: the same absolute-time One-Take contract as P and R.
import { useDirectedFonts } from '../lib/captions.js';
import { createOneTake } from '../lib/one-take-canvas.js';
import { loadOneTake } from '../lib/one-take.js';

export const supportsReducedMotion = true;
let take = null;
let currentMotionMode = 'normal';

async function requiredJson(url) {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`Cannot load ${url}: HTTP ${response.status}`);
  return response.json();
}

export async function init({ motionMode = 'normal', resources } = {}) {
  const [spec, direction] = await Promise.all([loadOneTake(), requiredJson('/plan/text-direction.json')]);
  if (!spec) throw new Error('The one-take example requires plan/one-take.json');
  currentMotionMode = motionMode;
  await useDirectedFonts(direction, 1);
  take = createOneTake(spec, { direction });
  resources?.defer(() => take.close());
}

export async function draw(ctx, t) {
  take.draw(ctx, t, { motionMode: currentMotionMode });
}
