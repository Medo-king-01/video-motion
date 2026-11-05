import React from 'react';
import {lightSweep} from './effects.js';

export type LightSweepProps = {
  time: number;
  start?: number;
  duration?: number;
  width?: number;
  angle?: number;
  intensity?: number;
};

/** Frame-addressable CSS overlay. Place it after scene content in the same stacking context. */
export const LightSweep: React.FC<LightSweepProps> = ({
  time,
  start = 0,
  duration = 0.72,
  width = 0.18,
  angle = -0.22,
  intensity = 0.72,
}) => {
  const state = lightSweep(time, start, duration, width, angle, intensity);
  if (state.alpha <= 0) return null;
  return (
    <div
      aria-hidden="true"
      data-motion-effect="light-sweep"
      style={{
        position: 'absolute',
        left: `${state.center_x * 100}%`,
        top: '-25%',
        width: `${state.width * 100}%`,
        height: '150%',
        transform: `translateX(-50%) rotate(${state.angle}rad)`,
        transformOrigin: 'center center',
        opacity: state.alpha,
        background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.10) 28%, rgba(255,255,255,0.82) 50%, rgba(255,255,255,0.10) 72%, transparent 100%)',
        pointerEvents: 'none',
      }}
    />
  );
};
