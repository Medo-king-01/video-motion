import React, {useEffect, useState} from 'react';
import {cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {PALETTE} from './brand';
import {DirectedText} from './lib/DirectedText';
import {FixedStage} from './lib/FixedStage';
import {SlideWall} from './lib/SlideWall';
import {brandHex} from './lib/stage.js';
import copyDocument from '../plan/copy.json';
import stageSpec from '../plan/stage.json';
import direction from '../plan/text-direction.json';
import wallSpec from '../plan/slide-wall.json';

const COPY = Object.fromEntries(copyDocument.copy.map((item) => [item.id, item]));

export const SlideWallExample: React.FC<{motionMode?: 'normal' | 'reduced'}> = ({motionMode = 'normal'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const [fontGate] = useState(() => delayRender('Load the slide-wall example font'));
  useEffect(() => {
    new FontFace('Cairo', `url('${staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}')`, {weight: '800'})
      .load()
      .then((font) => {
        document.fonts.add(font);
        continueRender(fontGate);
      })
      .catch((error) => cancelRender(error));
  }, [fontGate]);
  const time = frame / fps;

  return (
    <FixedStage spec={stageSpec} time={time} duration={6} motionMode={motionMode}>
      {(stageState) => (
        <SlideWall
          spec={wallSpec}
          time={time}
          motionMode={motionMode}
          viewport={stageState.win}
          textureWidth={450}
          renderSlide={(slide, {width, height}) => {
            const item = COPY[slide.id];
            return (
              <div style={{position: 'relative', width, height, background: brandHex(slide.surfaceRole)}}>
                <div style={{
                  position: 'absolute', left: width * 0.1, top: height * 0.09,
                  width: width * 0.8, height: height * 0.015, background: brandHex(slide.accentRole),
                }} />
                <DirectedText
                  direction={direction}
                  scene={1}
                  role="number"
                  elementId={item.id}
                  time={1}
                  start={0}
                  end={1}
                  size={Math.trunc(width * 0.28)}
                  color={PALETTE.ink}
                  accent={PALETTE.red}
                  theme="light"
                  style={{
                    position: 'absolute', left: 0, top: height * 0.37, width,
                    textAlign: 'center', direction: 'ltr', fontSize: Math.trunc(width * 0.28), lineHeight: 1.2,
                  }}
                >
                  {item.text}
                </DirectedText>
                <div style={{
                  position: 'absolute', left: width * 0.1, top: height * 0.82,
                  width: width * 0.52, height: height * 0.015, background: PALETTE.gray2,
                }} />
              </div>
            );
          }}
        />
      )}
    </FixedStage>
  );
};
