import React from 'react';
import {Composition} from 'remotion';
import {CANVAS, DESIGN} from './canvas';
import {DURATION_IN_FRAMES, IS_PREVIEW_TIMELINE} from './data';
import {MotionReel} from './RemotionRoot';

// Scenes are authored in the 1080×1920 design space. CANVAS may be a uniform downscale of it, so the
// composition shrinks while the stage is laid out and then scaled as a whole — never re-flowed.
const ScaledReel: React.FC<React.ComponentProps<typeof MotionReel>> = (props) => (
  <div
    style={{
      width: DESIGN.width,
      height: DESIGN.height,
      overflow: 'hidden',
      transform: `scale(${CANVAS.scale})`,
      transformOrigin: 'top left',
    }}
  >
    <MotionReel {...props} />
  </div>
);

export const RemotionRoot: React.FC = () => (
  <Composition
    id="MedoReel"
    component={ScaledReel}
    durationInFrames={DURATION_IN_FRAMES}
    fps={CANVAS.fps}
    width={CANVAS.width}
    height={CANVAS.height}
    defaultProps={{audioFile: null, previewOnly: IS_PREVIEW_TIMELINE, motionMode: 'normal'}}
  />
);
