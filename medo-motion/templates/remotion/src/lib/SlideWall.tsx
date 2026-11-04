import React, {useMemo} from 'react';
import {AbsoluteFill} from 'remotion';
import {
  normalizeSlideWall,
  slideHomography,
  slideWallStateAt,
} from './slide-wall.js';
import {brandHex} from './stage.js';

export type SlideWallWindow = {x: number; y: number; w: number; h: number; r?: number};

type SlideWallProps = {
  spec: any;
  time: number;
  motionMode?: 'normal' | 'reduced';
  viewport?: SlideWallWindow | null;
  textureWidth?: number;
  renderSlide: (
    slide: any,
    options: {width: number; height: number; focused: boolean},
  ) => React.ReactNode;
  style?: React.CSSProperties;
};

const cssMatrix = (matrix: number[][]): string => {
  const [[a, b, tx], [c, d, ty], [g, h]] = matrix;
  // CSS matrix3d is column-major. The fourth column/row carries the projective w term.
  return `matrix3d(${a},${c},0,${g},${b},${d},0,${h},0,0,1,0,${tx},${ty},0,1)`;
};

/**
 * Native Remotion adapter. Slide faces stay real DOM, so DirectedText, font shaping and the
 * existing DOM layout audit continue to work after the shared projective matrix is applied.
 * Slab sides use SVG polygons from the same space3d mesh/camera as P and K.
 */
export const SlideWall: React.FC<SlideWallProps> = ({
  spec: input,
  time,
  motionMode = 'normal',
  viewport = null,
  textureWidth = 540,
  renderSlide,
  style,
}) => {
  const spec = useMemo(() => normalizeSlideWall(input), [input]);
  const state = useMemo(
    () => slideWallStateAt(spec, time, {motionMode, viewport: viewport as any}),
    [spec, time, motionMode, viewport],
  );
  const focusedId = state.mode === 'slide'
    ? spec.timeline[state.segmentIndex].slide
    : state.mode === 'move' && state.progress === 1
      ? spec.timeline[state.segmentIndex].to.slide
      : null;

  return (
    <AbsoluteFill
      data-slide-wall-id={spec.id}
      style={{background: brandHex(spec.backgroundRole), overflow: 'hidden', ...style}}
    >
      {state.slides.filter((item: any) => item.visible).map((item: any) => {
        const {slide} = item;
        const width = textureWidth;
        const height = Math.max(1, Math.round(textureWidth * slide.size[1] / slide.size[0]));
        const matrix = slideHomography(width, height, item.front);
        const surface = brandHex(slide.surfaceRole);
        const edge = brandHex(slide.edgeRole);
        return (
          <AbsoluteFill key={slide.id} data-slide-id={slide.id} style={{pointerEvents: 'none'}}>
            <svg
              width={spec.canvas.w}
              height={spec.canvas.h}
              viewBox={`0 0 ${spec.canvas.w} ${spec.canvas.h}`}
              style={{position: 'absolute', inset: 0, overflow: 'visible'}}
            >
              {item.faces.filter((face: any) => !face.cull).map((face: any) => (
                <polygon
                  key={face.idx.join('-')}
                  points={face.points.map((p: number[]) => `${p[0]},${p[1]}`).join(' ')}
                  fill={face.role === 'front' ? surface : edge}
                />
              ))}
            </svg>
            <div
              data-slide-face={slide.id}
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                width,
                height,
                transformOrigin: '0 0',
                transform: cssMatrix(matrix),
                background: surface,
                overflow: 'hidden',
                backfaceVisibility: 'hidden',
              }}
            >
              {renderSlide(slide, {width, height, focused: focusedId === slide.id})}
            </div>
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );
};
