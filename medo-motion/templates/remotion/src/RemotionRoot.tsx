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
import {IS_PREVIEW_TIMELINE, STORY, TIMELINE} from './data';
import DIRECTION from '../plan/text-direction.json';
import {DirectedText} from './lib/DirectedText';

export type ReelProps = {audioFile?: string | null; previewOnly?: boolean};

export const MotionReel: React.FC<ReelProps> = ({audioFile = null, previewOnly = IS_PREVIEW_TIMELINE}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const [fontHandle] = useState(() => delayRender('Loading local Cairo font'));
  const sceneCount = TIMELINE.scenes?.length || 1;
  const sceneIndex = useMemo(() => {
    const seconds = frame / fps;
    const found = TIMELINE.scenes?.findIndex((scene) => seconds >= scene.start && seconds < scene.end) ?? -1;
    return Math.max(0, found);
  }, [frame, fps]);
  const scene = TIMELINE.scenes?.[sceneIndex];
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
  const pulse = 1 + Math.sin((localSeconds * Math.PI * 2) / Math.max(duration, 1)) * 0.025;

  useEffect(() => {
    Promise.all([document.fonts.load('800 96px Cairo'), document.fonts.load('400 20px Inter')])
      .then(() => continueRender(fontHandle))
      .catch((error) => cancelRender(error));
  }, [fontHandle]);

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(180deg, ${bgTop} 0%, ${bgBottom} 100%)`,
      color: primary,
      fontFamily: 'Cairo, sans-serif',
      overflow: 'hidden',
      direction: 'rtl',
    }}>
      <style>{`
        @font-face {
          font-family: Cairo;
          src: url('${staticFile('fonts/Cairo_800ExtraBold.ttf')}') format('truetype');
          font-weight: 700 900;
          font-display: block;
        }
        @font-face {
          font-family: Cairo;
          src: url('${staticFile('fonts/Cairo_400Regular.ttf')}') format('truetype');
          font-weight: 400;
          font-display: block;
        }
        @font-face {
          font-family: Inter;
          src: url('${staticFile('fonts/Inter_400Regular.ttf')}') format('truetype');
          font-weight: 400;
          font-display: block;
        }
        @font-face {
          font-family: Inter;
          src: url('${staticFile('fonts/Inter_800ExtraBold.ttf')}') format('truetype');
          font-weight: 800;
          font-display: block;
        }
        * { box-sizing: border-box; }
      `}</style>

      {/* Decorative palette disc: generated from the locked brand, never a logo placeholder. */}
      <div style={{
        position: 'absolute', width: 850, height: 850, borderRadius: '50%',
        left: '50%', top: '48%', transform: `translate(-50%, -50%) scale(${pulse})`,
        background: `radial-gradient(circle at 35% 30%, ${PALETTE.red} 0%, ${PALETTE.redDeep} 67%, ${PALETTE.inkShadow} 100%)`,
        opacity: light ? 0.11 : 0.34,
      }} />

      <div style={{position: 'absolute', top: BRAND.progressY, left: 40, right: 40, height: 8,
        borderRadius: 8, background: `${primary}30`, overflow: 'hidden'}}>
        <div style={{height: '100%', width: `${progress * 100}%`, background: PALETTE.red,
          transformOrigin: 'right center'}} />
      </div>

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

      {previewOnly && (
        <div style={{position: 'absolute', left: 40, bottom: 40, padding: '10px 18px',
          border: `2px solid ${PALETTE.salmon}`, borderRadius: 12, color: PALETTE.salmon,
          background: PALETTE.ink, fontSize: 22, fontFamily: 'Inter, sans-serif', direction: 'ltr'}}>
          PREVIEW · VO TIMELINE NOT SET
        </div>
      )}

      {audioFile ? <Audio src={staticFile(audioFile)} /> : null}
    </AbsoluteFill>
  );
};
