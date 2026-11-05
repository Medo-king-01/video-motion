import React, {useEffect, useMemo, useState} from 'react';
import {
  AbsoluteFill,
  Audio,
  cancelRender,
  continueRender,
  delayRender,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {BRAND, PALETTE} from './brand';
import {DURATION_SECONDS, IS_PREVIEW_TIMELINE, STORY, TIMELINE} from './data';
import DIRECTION from '../plan/text-direction.json';
import FONTS from '../assets/fonts/fonts.json';
import {DirectedText} from './lib/DirectedText';
import {FixedStage} from './lib/FixedStage';
import {SceneEffects} from './lib/SceneEffects';
import {isStageEnabled, validateStageSpec} from './lib/stage.js';

declare const require: {
  context: (
    directory: string,
    useSubdirectories?: boolean,
    regExp?: RegExp,
  ) => {
    keys(): string[];
    (id: string): any;
  };
};

// Optional plan JSON loader: legacy Engine R projects without plan/stage.json (or
// optional copy.json) fall back cleanly to null with zero migration required.
function loadOptionalPlanJson(
  relName: './stage.json' | './copy.json' | './effects.json',
): Record<string, any> | null {
  try {
    const ctx = require.context('../plan', false, /^\.\/(stage|copy|effects)\.json$/);
    if (ctx.keys().includes(relName)) {
      const mod = ctx(relName);
      const unwrapped = mod && typeof mod === 'object' && 'default' in mod ? mod.default : mod;
      return unwrapped ?? null;
    }
  } catch {
    return null;
  }
  return null;
}

export const STAGE_PLAN = loadOptionalPlanJson('./stage.json');
const COPY_PLAN = loadOptionalPlanJson('./copy.json');
const EFFECTS_PLAN = loadOptionalPlanJson('./effects.json');

// Every manifest face is available to the agent's direction; @font-face is generated
// from the same fonts.json the other engines read (no hardcoded creative default).
const FONT_FACES = Object.entries(FONTS.families as Record<string, any>)
  .flatMap(([family, meta]) => (meta.weights || []).map((w: any) => ({family, weight: w.weight, file: w.file})));
const USED_FONTS = (() => {
  const seen = new Map<string, {family: string; weight: number}>();
  for (const sc of (DIRECTION as any).scenes || []) {
    for (const e of [...Object.values(sc.fontStyles || {}), ...Object.values(sc.fontElements || {})]) {
      const entry = e as any;
      if (entry && typeof entry.family === 'string') seen.set(`${entry.family}@${entry.weight}`, entry);
    }
  }
  return [...seen.values()];
})();

const STAGE_ERRORS = STAGE_PLAN === null ? [] : validateStageSpec(STAGE_PLAN);
const AUTO_STAGE_ACTIVE =
  STAGE_PLAN !== null &&
  STAGE_ERRORS.length === 0 &&
  isStageEnabled(STAGE_PLAN) &&
  STAGE_PLAN.autoWrap !== false;

export const COPY_BY_ID: Record<string, string> = (() => {
  const out: Record<string, string> = {};
  const list = Array.isArray(COPY_PLAN?.copy) ? COPY_PLAN.copy : [];
  for (const item of list) {
    if (item && typeof item.id === 'string' && typeof item.text === 'string') {
      out[item.id] = item.text;
    }
  }
  return out;
})();

export type ReelProps = {audioFile?: string | null; previewOnly?: boolean; motionMode?: 'normal' | 'reduced'};

export const MotionReel: React.FC<ReelProps> = ({audioFile = null, previewOnly = IS_PREVIEW_TIMELINE, motionMode = 'normal'}) => {
  if (motionMode !== 'normal' && motionMode !== 'reduced') throw Error('invalid motion mode');
  if (STAGE_ERRORS.length > 0) {
    throw new Error(`Invalid plan/stage.json: ${STAGE_ERRORS.join('; ')}`);
  }
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const [fontHandle] = useState(() => delayRender('Loading agent-chosen fonts'));
  const absSeconds = frame / fps;
  const sceneCount = TIMELINE.scenes?.length || 1;
  const sceneIndex = useMemo(() => {
    const found = TIMELINE.scenes?.findIndex((scene) => absSeconds >= scene.start && absSeconds < scene.end) ?? -1;
    return Math.max(0, found);
  }, [absSeconds]);
  const scene = TIMELINE.scenes?.[sceneIndex];
  const effectScene = Array.isArray(EFFECTS_PLAN?.scenes)
    ? EFFECTS_PLAN!.scenes.find((item: any) => item && item.scene === sceneIndex + 1)
    : null;
  const sceneEffects = effectScene?.effects;
  const localFrame = Math.max(0, frame - Math.round((scene?.start ?? 0) * fps));
  const localSeconds = localFrame / fps;
  const duration = Math.max(0.5, (scene?.end ?? durationInFrames / fps) - (scene?.start ?? 0));
  const copy = STORY[sceneIndex % STORY.length];
  const light = sceneIndex % 2 === 0;
  const bgTop = light ? PALETTE.bgLightTop : PALETTE.bgDarkTop;
  const bgBottom = light ? PALETTE.bgLightBottom : PALETTE.bgDarkBottom;
  const primary = light ? PALETTE.ink : PALETTE.paper;
  const accent = light ? PALETTE.red : PALETTE.salmon;
  const progress = frame / Math.max(1, durationInFrames - 1);
  const pulse = motionMode === 'reduced' ? 1 : 1 + Math.sin((localSeconds * Math.PI * 2) / Math.max(duration, 1)) * 0.025;

  useEffect(() => {
    const jobs = USED_FONTS.length
      ? USED_FONTS.map((f) => document.fonts.load(`${f.weight} 32px "${f.family}"`))
      : [document.fonts.load('800 32px Cairo')];
    Promise.all(jobs)
      .then(() => continueRender(fontHandle))
      .catch((error) => cancelRender(error));
  }, [fontHandle]);

  const fontStyleSheet = (
    <style>{`
      ${FONT_FACES.map((f) => `@font-face {
        font-family: "${f.family}";
        src: url('${staticFile(`fonts/${f.family}/${f.file}`)}') format('truetype');
        font-weight: ${f.weight};
        font-display: block;
      }`).join('\n')}
      * { box-sizing: border-box; }
    `}</style>
  );

  const previewBadge = previewOnly ? (
    <div style={{position: 'absolute', left: 40, bottom: 40, padding: '10px 18px',
      border: `2px solid ${PALETTE.salmon}`, borderRadius: 12, color: PALETTE.salmon,
      background: PALETTE.ink, fontSize: 22, fontFamily: 'Inter, sans-serif', direction: 'ltr'}}>
      PREVIEW · VO TIMELINE NOT SET
    </div>
  ) : null;

  const sceneBody = (
    <AbsoluteFill style={{
      background: `linear-gradient(180deg, ${bgTop} 0%, ${bgBottom} 100%)`,
      color: primary,
      fontFamily: 'Cairo, sans-serif',
      overflow: 'hidden',
      direction: 'rtl',
    }}>
      {!AUTO_STAGE_ACTIVE && fontStyleSheet}

      {/* Decorative palette disc: generated from the locked brand, never a logo placeholder. */}
      <div style={{
        position: 'absolute', width: 850, height: 850, borderRadius: '50%',
        left: '50%', top: '48%', transform: `translate(-50%, -50%) scale(${pulse})`,
        background: `radial-gradient(circle at 35% 30%, ${PALETTE.red} 0%, ${PALETTE.redDeep} 67%, ${PALETTE.inkShadow} 100%)`,
        opacity: light ? 0.11 : 0.34,
      }} />

      {!AUTO_STAGE_ACTIVE && (
        <div style={{position: 'absolute', top: BRAND.progressY, left: 40, right: 40, height: 8,
          borderRadius: 8, background: `${primary}30`, overflow: 'hidden'}}>
          <div style={{height: '100%', width: `${progress * 100}%`, background: PALETTE.red,
            transformOrigin: 'right center'}} />
        </div>
      )}

      <div style={{position: 'absolute', top: 310, right: 78, left: 78}}>
        <DirectedText direction={DIRECTION} scene={sceneIndex + 1} role="label"
          time={localSeconds} start={0} end={duration} size={40} color={accent} theme={light ? 'light' : 'dark'}
          style={{fontSize: 40, fontWeight: 800, marginBottom: 34}}>
          {copy.eyebrow}
        </DirectedText>
        <DirectedText direction={DIRECTION} scene={sceneIndex + 1} role="title"
          time={localSeconds} start={0} end={duration} size={104} color={primary} theme={light ? 'light' : 'dark'}
          style={{fontSize: 104, fontWeight: 800, lineHeight: 1.34, whiteSpace: 'pre-line'}}>
          {copy.title}
        </DirectedText>
        <div style={{height: 5, width: 166, borderRadius: 8, background: PALETTE.red, marginTop: 42}} />
        <DirectedText direction={DIRECTION} scene={sceneIndex + 1} role="body"
          time={localSeconds} start={0} end={duration} size={48} color={primary} theme={light ? 'light' : 'dark'}
          style={{fontSize: 48, fontWeight: 400, lineHeight: 1.65, marginTop: 36, opacity: 0.88}}>
          {copy.body}
        </DirectedText>
      </div>

      <DirectedText direction={DIRECTION} scene={sceneIndex + 1} role="label"
        time={localSeconds} start={0} end={duration} size={32}
        color={light ? PALETTE.inkSoft : PALETTE.gray3} theme={light ? 'light' : 'dark'}
        style={{position: 'absolute', bottom: 270, right: 78, left: 78,
          display: 'flex', alignItems: 'center', gap: 16, fontSize: 32, fontWeight: 700}}>
        <span>{String(sceneIndex + 1).padStart(2, '0')}</span>
        <div style={{height: 2, flex: 1, background: `${primary}40`}} />
        <span>{String(sceneCount).padStart(2, '0')}</span>
      </DirectedText>

      {!AUTO_STAGE_ACTIVE && previewBadge}
      {!AUTO_STAGE_ACTIVE && (audioFile ? <Audio src={staticFile(audioFile)} /> : null)}
    </AbsoluteFill>
  );

  const effectedSceneBody = (
    <SceneEffects effects={sceneEffects} time={localSeconds} width={1080} height={1920}>
      {sceneBody}
    </SceneEffects>
  );

  if (AUTO_STAGE_ACTIVE) {
    return (
      <AbsoluteFill style={{fontFamily: 'Cairo, sans-serif', overflow: 'hidden', direction: 'rtl'}}>
        {fontStyleSheet}
        <FixedStage
          spec={STAGE_PLAN as Record<string, any>}
          time={absSeconds}
          duration={DURATION_SECONDS}
          direction={DIRECTION}
          copyById={COPY_BY_ID}
          motionMode={motionMode}
          over={previewBadge}
        >
          {effectedSceneBody}
        </FixedStage>
        {audioFile ? <Audio src={staticFile(audioFile)} /> : null}
      </AbsoluteFill>
    );
  }

  return effectedSceneBody;
};
