import React from 'react';
import {Composition} from 'remotion';
import {BRAND} from './brand';
import {DURATION_IN_FRAMES, IS_PREVIEW_TIMELINE} from './data';
import {MotionReel} from './RemotionRoot';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="MedoReel"
    component={MotionReel}
    durationInFrames={DURATION_IN_FRAMES}
    fps={BRAND.fps}
    width={BRAND.width}
    height={BRAND.height}
    defaultProps={{audioFile: null, previewOnly: IS_PREVIEW_TIMELINE, motionMode: 'normal'}}
  />
);
