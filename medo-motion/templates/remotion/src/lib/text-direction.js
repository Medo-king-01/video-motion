// Agent-authored text direction: the single source of truth for which motion
// style each scene's captions and on-screen text use. Mirrors engine P's
// text_direction.py. The agent decides per scene (no default, no random picker);
// this module only validates and resolves those explicit choices.
import { CAPTION_STYLE_IDS } from './caption-styles.js';
import { SPECIAL_STYLES, STYLE_ALIAS } from './caption-motion.js';

export const TEXT_ROLES = ['hook', 'title', 'body', 'keyword', 'cta', 'label'];
const KNOWN_STYLES = new Set([...SPECIAL_STYLES, ...Object.keys(STYLE_ALIAS), ...CAPTION_STYLE_IDS]);
const MIN_REASON = 12;

export function isTextStyle(style) {
  return typeof style === 'string' && (KNOWN_STYLES.has(style) || KNOWN_STYLES.has(STYLE_ALIAS[style]));
}

const sceneIndex = (scene, pos) => scene.index ?? pos + 1;
const longEnough = v => typeof v === 'string' && v.trim().length >= MIN_REASON;

/** Return { errors, warnings }. Errors block a render/lint. */
export function validateTextDirection(direction, beats = null) {
  const errors = [], warnings = [];
  if (!direction || typeof direction !== 'object') {
    return { errors: ['plan/text-direction.json must be an object'], warnings };
  }
  if (direction.version !== 1) errors.push('text-direction version must be 1');
  if (direction.status !== 'directed') errors.push('text-direction status must be "directed" (the agent has chosen the styles)');
  if (!['agent', 'user'].includes(direction.decidedBy)) errors.push('text-direction decidedBy must be "agent" or "user"');
  if (!longEnough(direction.concept)) errors.push("text-direction concept must explain the reel's text-motion idea (>= 12 chars)");

  const scenes = direction.scenes;
  if (!Array.isArray(scenes)) {
    errors.push('text-direction scenes must be a list');
    return { errors, warnings };
  }
  const byIndex = new Map();
  for (const sc of scenes) {
    if (!sc || !Number.isInteger(sc.scene)) { errors.push("each text-direction scene needs an integer 'scene' index"); continue; }
    const idx = sc.scene;
    if (byIndex.has(idx)) errors.push(`duplicate text-direction scene ${idx}`);
    byIndex.set(idx, sc);
    if (!isTextStyle(sc.captionStyle)) errors.push(`scene ${idx}: captionStyle must be an explicit caption-safe style`);
    if (!longEnough(sc.captionWhy)) errors.push(`scene ${idx}: captionWhy must justify the caption style (>= ${MIN_REASON} chars)`);
    const ts = sc.textStyles || {};
    if (typeof ts !== 'object' || Array.isArray(ts)) {
      errors.push(`scene ${idx}: textStyles must be an object keyed by role`);
    } else {
      for (const [role, style] of Object.entries(ts)) {
        if (!TEXT_ROLES.includes(role)) errors.push(`scene ${idx}: unknown text role '${role}'`);
        if (!isTextStyle(style)) errors.push(`scene ${idx}: textStyles.${role} must be an explicit caption-safe style`);
      }
      if (Object.keys(ts).length && !longEnough(sc.textWhy)) {
        errors.push(`scene ${idx}: textWhy must justify the on-screen text styles`);
      }
    }
  }
  if (beats && Array.isArray(beats.scenes)) {
    const wanted = new Set(beats.scenes.map(sceneIndex));
    const missing = [...wanted].filter(i => !byIndex.has(i)).sort((a, b) => a - b);
    const extra = [...byIndex.keys()].filter(i => !wanted.has(i)).sort((a, b) => a - b);
    if (missing.length) errors.push(`text-direction missing scenes: ${missing}`);
    if (extra.length) errors.push(`text-direction has scenes not in the timeline: ${extra}`);
  }
  const styles = scenes.map(sc => sc.captionStyle).filter(isTextStyle);
  if (styles.length >= 3 && new Set(styles).size === 1 && !direction.motifReason) {
    warnings.push('every scene uses the same captionStyle — vary it per scene, or add motifReason to justify a deliberate motif');
  }
  return { errors, warnings };
}

function find(direction, scene) {
  const sc = (direction.scenes || []).find(s => s.scene === scene);
  if (!sc) throw new Error(`No text direction for scene ${scene}; the agent must choose its styles.`);
  return sc;
}

export function captionStyleFor(direction, scene) {
  const style = find(direction, scene).captionStyle;
  if (!isTextStyle(style)) throw new Error(`Scene ${scene} has no explicit captionStyle.`);
  return style;
}

export function textStyleFor(direction, scene, role) {
  const style = (find(direction, scene).textStyles || {})[role];
  if (!isTextStyle(style)) throw new Error(`Scene ${scene} has no explicit textStyles.${role}.`);
  return style;
}
