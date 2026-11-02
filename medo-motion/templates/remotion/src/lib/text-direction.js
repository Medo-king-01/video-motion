// Agent-authored text direction: the single source of truth for which motion
// style EVERY visible text element uses — captions, titles, keywords, numbers,
// CTAs, labels and UI text. Mirrors engine P's text_direction.py. The agent
// decides per scene (no default, no random picker); this module only validates
// and resolves those explicit choices.
import { CAPTION_STYLE_IDS } from './caption-styles.js';
import { SPECIAL_STYLES, STYLE_ALIAS } from './caption-motion.js';

export const TEXT_ROLES = ['hook', 'title', 'body', 'keyword', 'cta', 'label', 'number', 'ui', 'quote'];
const KNOWN_STYLES = new Set([...SPECIAL_STYLES, ...Object.keys(STYLE_ALIAS), ...CAPTION_STYLE_IDS]);
const MIN_REASON = 12;
export const VERSION = 2;

export function isTextStyle(style) {
  return typeof style === 'string' && (KNOWN_STYLES.has(style) || KNOWN_STYLES.has(STYLE_ALIAS[style]));
}

const sceneIndex = (scene, pos) => scene.index ?? pos + 1;
const longEnough = v => typeof v === 'string' && v.trim().length >= MIN_REASON;

/** Return { errors, warnings }. Errors block a render/lint.
 * `copy` is plan/copy.json: when supplied, every visible text fragment must
 * resolve to an explicit agent-chosen style, not just captions. */
export function validateTextDirection(direction, beats = null, copy = null) {
  const errors = [], warnings = [];
  if (!direction || typeof direction !== 'object') {
    return { errors: ['plan/text-direction.json must be an object'], warnings };
  }
  if (direction.version !== VERSION) errors.push(`text-direction version must be ${VERSION}`);
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
    const ts = sc.textStyles;
    if (!ts || typeof ts !== 'object' || Array.isArray(ts)) {
      errors.push(`scene ${idx}: textStyles must be an object keyed by text role`);
    } else {
      for (const [role, style] of Object.entries(ts)) {
        if (!TEXT_ROLES.includes(role)) errors.push(`scene ${idx}: unknown text role '${role}'`);
        if (!isTextStyle(style)) errors.push(`scene ${idx}: textStyles.${role} must be an explicit caption-safe style`);
      }
      if (Object.keys(ts).length && !longEnough(sc.textWhy)) {
        errors.push('scene ' + idx + ': textWhy must justify the on-screen text styles');
      }
    }
    const elements = sc.textElements || {};
    if (typeof elements !== 'object' || Array.isArray(elements)) {
      errors.push(`scene ${idx}: textElements must be an object keyed by element id`);
    } else {
      for (const [eid, el] of Object.entries(elements)) {
        if (!el || typeof el !== 'object') { errors.push(`scene ${idx}: textElements.${eid} must be an object`); continue; }
        if (!TEXT_ROLES.includes(el.role)) errors.push(`scene ${idx}: textElements.${eid} has an unknown role`);
        if (!isTextStyle(el.style)) errors.push(`scene ${idx}: textElements.${eid}.style must be an explicit caption-safe style`);
        if (!longEnough(el.why)) errors.push(`scene ${idx}: textElements.${eid}.why must justify this element's motion`);
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
  if (copy && Array.isArray(copy.copy)) {
    copy.copy.forEach((item, i) => {
      if (!item || typeof item !== 'object') { errors.push(`copy[${i}] must be an object`); return; }
      const scene = item.scene;
      const role = item.role;
      const label = item.id || `copy[${i}]`;
      const sc = byIndex.get(scene);
      if (!sc) { errors.push(`${label}: scene ${scene} has no text direction`); return; }
      if (!TEXT_ROLES.includes(role)) {
        errors.push(`${label}: every on-screen text fragment needs a known role (got '${role}')`);
        return;
      }
      const elements = sc.textElements || {};
      const eid = item.id;
      if (eid && elements[eid]) {
        const el = elements[eid];
        if (el.role !== role) errors.push(`${label}: textElements role does not match the copy role`);
        if (!isTextStyle(el.style)) errors.push(`${label}: no explicit style for this text element`);
      } else if (!isTextStyle((sc.textStyles || {})[role])) {
        errors.push(`${label}: scene ${scene} has no textStyles.${role} (or textElements.${eid}) for this text`);
      }
    });
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

/** Resolve the agent's choice for ANY visible text: element override first,
 * then the scene's role style. Never falls back to a default.
 * @param {any} direction
 * @param {number} scene
 * @param {string} role
 * @param {string|null} [elementId]
 * @returns {string}
 */
export function textStyleFor(direction, scene, role, elementId = null) {
  const sc = find(direction, scene);
  if (elementId) {
    const el = (sc.textElements || {})[elementId];
    if (el && isTextStyle(el.style)) {
      if (el.role != null && el.role !== role) {
        throw new Error(`Scene ${scene} textElements.${elementId} role does not match '${role}'.`);
      }
      return el.style;
    }
  }
  const style = (sc.textStyles || {})[role];
  if (!isTextStyle(style)) {
    throw new Error(`Scene ${scene} has no explicit text style for role '${role}'`
      + (elementId ? ` (element '${elementId}')` : '') + '.');
  }
  return style;
}
