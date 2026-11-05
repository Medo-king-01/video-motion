import React from 'react';
import {Composition} from 'remotion';
import {BRAND} from './brand';
import {SlideWallExample} from './SlideWallExample';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="SlideWallExample"
    component={SlideWallExample}
    durationInFrames={180}
    fps={BRAND.fps}
    width={BRAND.width}
    height={BRAND.height}
    defaultProps={{motionMode: 'normal'}}
  />
);
