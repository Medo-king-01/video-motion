import React, {useEffect, useState} from 'react';
import {cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {OneTake} from './lib/OneTake';
import direction from '../plan/text-direction.json';
import spec from '../plan/one-take.json';

export const OneTakeExample: React.FC<{motionMode?: 'normal' | 'reduced'}> = ({motionMode = 'normal'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const [fontGate] = useState(() => delayRender('Load the one-take example font'));
  useEffect(() => {
    Promise.all([
      new FontFace('Cairo', `url('${staticFile('fonts/Cairo/Cairo_400Regular.ttf')}')`, {weight: '400'}).load(),
      new FontFace('Cairo', `url('${staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}')`, {weight: '800'}).load(),
    ]).then((fonts) => {
      fonts.forEach((font) => document.fonts.add(font));
      continueRender(fontGate);
    }).catch((error) => cancelRender(error));
  }, [fontGate]);

  return <OneTake spec={spec} direction={direction} time={frame / fps} motionMode={motionMode} />;
};
