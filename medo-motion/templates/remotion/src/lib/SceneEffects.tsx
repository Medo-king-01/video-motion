import React from 'react';
import {staticFile} from 'remotion';
import {LightSweep} from './LightSweep';
import {WhipPan} from './WhipPan';
import {ParticleDissolve} from './ParticleDissolve';

export type SceneEffectSpec = {
  type: 'lightSweep' | 'whipPan' | 'particleDissolve';
  start?: number;
  duration?: number;
  width?: number;
  angle?: number;
  intensity?: number;
  direction?: number;
  distance?: number;
  shutter?: number;
  maxBlur?: number;
  frameWidth?: number;
  source?: string;
  count?: number;
  seed?: number;
  background?: string;
};

function validateEffects(value: unknown): SceneEffectSpec[] {
  if (value == null) return [];
  if (!Array.isArray(value)) throw new Error('plan/effects.json scene effects must be an array');
  return value.map((entry, index) => {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
      throw new Error(`plan/effects.json effects[${index}] must be an object`);
    }
    const effect = entry as Record<string, unknown>;
    if (!['lightSweep', 'whipPan', 'particleDissolve'].includes(String(effect.type))) {
      throw new Error(`plan/effects.json effects[${index}].type is unsupported`);
    }
    for (const key of ['start', 'duration', 'width', 'angle', 'intensity', 'direction',
      'distance', 'shutter', 'maxBlur', 'frameWidth', 'count', 'seed']) {
      if (effect[key] !== undefined && (typeof effect[key] !== 'number' || !Number.isFinite(effect[key]))) {
        throw new Error(`plan/effects.json effects[${index}].${key} must be a finite number`);
      }
    }
    if (effect.type === 'particleDissolve' && (typeof effect.source !== 'string' || !effect.source.trim())) {
      throw new Error(`plan/effects.json effects[${index}].source is required for particleDissolve`);
    }
    return effect as unknown as SceneEffectSpec;
  });
}

/** Applies declarative, frame-addressable effects to one scene without changing its clock. */
export const SceneEffects: React.FC<{
  effects?: unknown;
  time: number;
  width: number;
  height: number;
  children: React.ReactNode;
}> = ({effects, time, width, height, children}) => {
  const list = validateEffects(effects);
  let content = <>{children}</>;
  for (const effect of list) {
    if (effect.type === 'whipPan') {
      content = <WhipPan time={time} frameWidth={effect.frameWidth ?? width}
        start={effect.start} duration={effect.duration} direction={effect.direction}
        distance={effect.distance} shutter={effect.shutter} maxBlur={effect.maxBlur}>
        {content}
      </WhipPan>;
    } else if (effect.type === 'lightSweep') {
      content = <div style={{position: 'absolute', inset: 0, overflow: 'hidden'}}>
        {content}
        <LightSweep time={time} start={effect.start} duration={effect.duration}
          width={effect.width} angle={effect.angle} intensity={effect.intensity}/>
      </div>;
    } else {
      content = <div style={{position: 'absolute', inset: 0, overflow: 'hidden'}}>
        {content}
        <ParticleDissolve source={staticFile(effect.source!)} time={time} width={width} height={height}
          start={effect.start} duration={effect.duration} count={effect.count}
          seed={effect.seed} background={effect.background}/>
      </div>;
    }
  }
  return <>{content}</>;
};
