import React from 'react';
import {whipPan} from './effects.js';

export type WhipPanProps = {
  time: number;
  children: React.ReactNode;
  frameWidth?: number;
  start?: number;
  duration?: number;
  direction?: number;
  distance?: number;
  shutter?: number;
  maxBlur?: number;
};

/** Frame-addressable camera wrapper. Parent must define the frame's dimensions. */
export const WhipPan: React.FC<WhipPanProps> = ({
  time,
  children,
  frameWidth = 1920,
  start = 0,
  duration = 0.42,
  direction = 1,
  distance = 1.15,
  shutter = 0.055,
  maxBlur = 0.16,
}) => {
  const state = whipPan(time, start, duration, direction, distance, shutter, maxBlur);
  const blur = Math.min(frameWidth * 0.08, state.blur_distance * frameWidth * 0.25);
  return (
    <div
      data-motion-effect="whip-pan"
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          transform: `translate3d(${state.offset_x * 100}%, 0, 0)`,
          filter: blur > 0 ? `blur(${blur}px)` : 'none',
          willChange: 'transform, filter',
        }}
      >
        {children}
      </div>
    </div>
  );
};
