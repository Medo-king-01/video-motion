// Engine K Canvas2D adapter for Machine Explainer diagrams.
// Keeps every visible label under the explicit copy.json + text-direction.json contract
// and derives safe placement dynamically from layout.js (`safeEnvelope`).

import { buildMachineScene, drawMachineGeometry } from './machine-kit.js';
import { drawDirectedText } from './captions.js';
import { protectBox, safeEnvelope } from './layout.js';
import { BRAND, PALETTE as C } from './brand.js';

export function drawMachineDiagram(ctx, spec, time, {
  direction,
  scene,
  copyById = {},
  id = spec?.id || 'machine',
  originX,
  originY,
  scale,
  theme = 'dark',
  calloutY,
  noteY,
} = {}) {
  const env = safeEnvelope('content', { checkPlatformUi: spec?.qa?.checkPlatformUi !== false });
  const graph = buildMachineScene(spec, time, {
    originX,
    originY,
    scale,
    theme,
    fps: env.fps || BRAND.FPS,
  });
  if (!graph.state.active) return graph;

  drawMachineGeometry(ctx, graph);
  if (graph.bounds.w > 0 && graph.bounds.h > 0) {
    protectBox(ctx, `${id}.diagram`, graph.bounds, 'keep');
  }

  const activeStep = graph.state.activeStep;
  if (activeStep && direction && Number.isInteger(scene)) {
    const maxW = env.x[1] - env.x[0];
    const centerX = (env.x[0] + env.x[1]) / 2;
    const stepY = typeof calloutY === 'number'
      ? calloutY
      : Math.min(env.y[1] - 90, Math.max(env.y[0] + 60, graph.bounds.y + graph.bounds.h + 86));
    const textColor = theme === 'light' ? C.ink : C.paper;
    const primaryId = activeStep.copyIds?.[0];
    const primaryText = primaryId ? copyById[primaryId] : null;
    if (typeof primaryText === 'string' && primaryText.trim()) {
      drawDirectedText(ctx, primaryText, {
        direction,
        scene,
        role: 'label',
        elementId: primaryId,
        time,
        start: activeStep.start,
        end: activeStep.end,
        x: centerX,
        y: stepY,
        size: 46,
        maxWidth: maxW,
        color: textColor,
        theme,
        shadow: 'transparent',
      });
    }
    if (activeStep.evidence === 'illustrative' && activeStep.illustrativeLabelId) {
      const noteText = copyById[activeStep.illustrativeLabelId];
      if (typeof noteText === 'string' && noteText.trim()) {
        const badgeY = typeof noteY === 'number'
          ? noteY
          : Math.max(env.y[0] + 44, graph.bounds.y - 68);
        drawDirectedText(ctx, noteText, {
          direction,
          scene,
          role: 'label',
          elementId: activeStep.illustrativeLabelId,
          time,
          start: activeStep.start,
          end: activeStep.end,
          x: centerX,
          y: badgeY,
          size: 38,
          maxWidth: maxW,
          color: theme === 'light' ? C.redDeep : C.salmon,
          theme,
          shadow: 'transparent',
        });
      }
    }
  }
  return graph;
}
