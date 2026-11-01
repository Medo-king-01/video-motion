import React from 'react';
import {Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import manifest from '../../assets/poses/poses.json';
import {BRAND} from '../brand';

const poseData = manifest as {
  ground: number;
  topGuide: number;
  poses: Record<string, {file: string; scale?: number; place?: string; feet?: number; w?: number; h?: number}>;
};

type Props = {
  pose?: string;
  x?: number;
  height?: number;
  offsetSeconds?: number;
  flip?: boolean;
  opacity?: number;
};

/** Deterministic Medo pose cut-out, using the same anchors and idle values as P/K. */
export const MedoPresenter: React.FC<Props> = ({
  pose = 'neutral', x = 0.5, height = 0.62, offsetSeconds = 0, flip = false, opacity = 1,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps + offsetSeconds;
  const meta = poseData.poses[pose] ?? poseData.poses.neutral;
  const h = height * BRAND.height * (meta.scale ?? 1);
  const w = h * ((meta.w ?? 428) / Math.max(1, meta.h ?? 1216));
  const close = meta.place === 'top';
  const feet = meta.feet ?? 0.9934;
  const anchorY = close ? poseData.topGuide + h / 2 : (poseData.ground ?? 1390) - (feet - 0.5) * h;
  const bob = 2.5 * Math.sin(2 * Math.PI * 0.22 * t);
  const sway = 2 * Math.sin(2 * Math.PI * 0.13 * t + 0.7);
  const breathe = 1 + 0.008 * Math.sin(2 * Math.PI * 0.28 * t);
  const lean = pose === 'wave' ? 1.1 * Math.sin(2 * Math.PI * 1.05 * t)
    : pose === 'clap' ? 0.6 * Math.sin(2 * Math.PI * 2.2 * t)
      : pose === 'run' || pose === 'walk' ? 1.4 * Math.sin(2 * Math.PI * 1.6 * t)
        : pose === 'thinking' || pose === 'thinking-deep' ? 0.35 * Math.sin(2 * Math.PI * 0.09 * t)
          : pose === 'shocked' ? 0.9 * Math.sin(2 * Math.PI * 7 * t) * Math.exp(-((t % 1) * 6))
            : 0.25 * Math.sin(2 * Math.PI * 0.11 * t);
  const centerX = x * BRAND.width + sway;

  return (
    <Img
      src={staticFile(`assets/poses/${meta.file}`)}
      style={{
        position: 'absolute',
        left: centerX,
        top: anchorY - bob,
        width: w,
        height: h,
        opacity,
        objectFit: 'contain',
        transform: `translate(-50%, -50%) rotate(${lean}deg) scale(${flip ? -breathe : breathe}, ${breathe})`,
        transformOrigin: 'center center',
      }}
    />
  );
};
