import React from 'react';
import {Composition} from 'remotion';
import {BRAND} from './brand';
import {OneTakeExample} from './OneTakeExample';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="OneTakeExample"
    component={OneTakeExample}
    durationInFrames={240}
    fps={BRAND.fps}
    width={BRAND.width}
    height={BRAND.height}
    defaultProps={{motionMode: 'normal'}}
  />
);
