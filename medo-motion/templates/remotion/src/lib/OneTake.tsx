import React, {useMemo} from 'react';
import {AbsoluteFill} from 'remotion';
import {DirectedText} from './DirectedText';
import {normalizeOneTake, oneTakeStateAt} from './one-take.js';
import {brandHex} from './stage.js';

export type OneTakeWindow = {x: number; y: number; w: number; h: number; r?: number};

type OneTakeProps = {
  spec: any;
  time: number;
  direction?: any;
  motionMode?: 'normal' | 'reduced';
  viewport?: OneTakeWindow | null;
  style?: React.CSSProperties;
};

/** Native Remotion adapter. Element faces remain real DOM; the shared core owns every transform. */
export const OneTake: React.FC<OneTakeProps> = ({
  spec: input,
  time,
  direction = null,
  motionMode = 'normal',
  viewport = null,
  style,
}) => {
  const spec = useMemo(() => normalizeOneTake(input), [input]);
  const state: any = useMemo(
    () => oneTakeStateAt(spec, time, {motionMode, viewport: viewport as any}),
    [spec, time, motionMode, viewport],
  );
  const win = state.viewport;
  const clipPath = `inset(${win.y}px ${spec.canvas.w - win.x - win.w}px ${spec.canvas.h - win.y - win.h}px ${win.x}px round ${win.r || 0}px)`;

  return (
    <AbsoluteFill
      data-one-take-id={spec.id}
      data-camera-zoom={state.camera.zoom}
      style={{background: brandHex(spec.backgroundRole), overflow: 'hidden', ...style}}
    >
      <AbsoluteFill style={{clipPath}}>
      {state.elements.map((element: any) => {
        const shapeStyle: React.CSSProperties = {
          position: 'absolute', inset: 0,
          background: element.kind === 'text' ? 'transparent' : brandHex(element.role),
          borderRadius: element.kind === 'circle' ? '50%' : Math.min(element.radius, element.w / 2, element.h / 2),
          border: element.kind !== 'text' && element.strokeWidth > 0
            ? `${element.strokeWidth}px solid ${brandHex(element.strokeRole)}` : undefined,
        };
        return (
          <div
            key={element.id}
            data-one-take-element={element.id}
            style={{
              position: 'absolute', left: element.screen.x - element.w / 2, top: element.screen.y - element.h / 2,
              width: element.w, height: element.h, opacity: element.opacity,
              transform: `rotate(${element.screen.rotation}deg) scale(${element.screen.scale})`,
              transformOrigin: 'center center',
            }}
          >
            {element.kind === 'text' ? (
              <DirectedText
                direction={direction}
                scene={element.scene}
                role={element.fontRole}
                elementId={element.id}
                time={1}
                start={0}
                end={1}
                size={element.fontSize}
                color={brandHex(element.role)}
                accent={brandHex(element.accentRole)}
                theme={['ink', 'ink_soft'].includes(element.role) ? 'light' : 'dark'}
                style={{
                  ...shapeStyle,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
                  direction: element.rtl ? 'rtl' : 'ltr', fontSize: element.fontSize,
                  lineHeight: 1.35, whiteSpace: 'pre-line',
                }}
              >
                {element.text}
              </DirectedText>
            ) : <div style={shapeStyle} />}
          </div>
        );
      })}
      {state.cursor && spec.cursor ? (
        <AbsoluteFill style={{pointerEvents: 'none'}}>
          {state.cursor.click ? (() => {
            const click = state.cursor.click;
            const radius = spec.cursor.size * (0.6 + 2 * (1 - (1 - click.progress) ** 3)) * state.camera.zoom;
            return (
              <div
                data-one-take-click={click.index}
                style={{
                  position: 'absolute', left: click.screen.x - radius, top: click.screen.y - radius,
                  width: radius * 2, height: radius * 2, borderRadius: '50%',
                  border: `${Math.max(2, spec.cursor.size / 8)}px solid ${brandHex('red')}`,
                  opacity: click.opacity * spec.cursor.opacity,
                }}
              />
            );
          })() : null}
          <svg
            data-one-take-cursor="1"
            width={spec.cursor.size * 0.8}
            height={spec.cursor.size * 1.25}
            viewBox="0 0 40 62"
            style={{
              position: 'absolute', left: state.cursor.screen.x, top: state.cursor.screen.y,
              opacity: spec.cursor.opacity,
              transform: `scale(${state.camera.zoom * (state.cursor.press ? 0.86 : 1)})`,
              transformOrigin: '0 0', overflow: 'visible',
            }}
          >
            <path
              d="M2 2 L2 53 L15 40 L24 60 L32 56 L23 35 L38 34 Z"
              fill={brandHex('paper')}
              stroke={brandHex('ink')}
              strokeWidth={2.5}
              strokeLinejoin="round"
            />
          </svg>
        </AbsoluteFill>
      ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
