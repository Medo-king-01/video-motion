import React from 'react';
import {Composition} from 'remotion';
import {BRAND} from './brand';
import {OneTakeExample} from './OneTakeExample';
import beats from '../plan/beats.json';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="OneTakeExample"
    component={OneTakeExample}
    durationInFrames={Math.round(beats.duration * BRAND.fps)}
    fps={BRAND.fps}
    width={BRAND.width}
    height={BRAND.height}
    defaultProps={{motionMode: 'normal'}}
  />
);
