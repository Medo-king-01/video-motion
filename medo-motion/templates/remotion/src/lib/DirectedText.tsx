import React from 'react';
import {PALETTE} from '../brand';
import {captionTransform} from './caption-motion.js';
import {textStyleFor} from './text-direction.js';

export type DirectedTextProps = {
  /** The agent's plan/text-direction.json (imported by the project root). */
  direction: any;
  scene: number;
  /** hook | title | body | keyword | cta | label | number | ui | quote */
  role: string;
  /** Optional element id for a per-element override in textElements. */
  elementId?: string;
  /** Absolute scene-local seconds. */
  time: number;
  /** Onset/offset of this text block (scene bounds or a measured copy event). */
  start: number;
  end: number;
  children: React.ReactNode;
  /** Font size in px, used to scale the em-based motion offsets. */
  size?: number;
  color?: string;
  accent?: string;
  theme?: 'dark' | 'light';
  style?: React.CSSProperties;
};

/**
 * Any on-screen text block whose motion is resolved from the agent's explicit
 * direction. Unlike TextMotion (absolute caption placement), this keeps normal
 * document flow so it can wrap titles, bodies, labels, numbers and CTAs.
 * There is no default style: a missing direction/role throws before render.
 */
export const DirectedText: React.FC<DirectedTextProps> = ({
  direction, scene, role, elementId, time, start, end, children,
  size = 64, color = PALETTE.paper, accent = PALETTE.salmon, theme = 'dark', style,
}) => {
  const resolved = textStyleFor(direction, scene, role, elementId ?? null);
  const elapsed = Math.max(0, time - start);
  const dur = Math.max(0.05, end - start);
  const m = captionTransform(resolved, elapsed, dur);
  const acc = theme === 'dark' ? accent : PALETTE.red;
  const base = theme === 'dark' ? PALETTE.paper : PALETTE.ink;

  const karaoke = m.karaokeP >= 0 && typeof children === 'string';
  const pct = Math.round(m.karaokeP * 100);
  const textStyle: React.CSSProperties = karaoke
    ? {
        backgroundImage: `linear-gradient(to left, ${acc} ${pct}%, ${base}61 ${pct}%)`,
        WebkitBackgroundClip: 'text',
        backgroundClip: 'text',
        color: 'transparent',
      }
    : {color};

  return (
    <div
      style={{
        transform: `translate(${m.x * size}px, ${m.y * size}px) rotate(${m.rotate}deg) scale(${m.scale})`,
        opacity: m.opacity,
        filter: m.blur * size > 0.2 ? `blur(${(m.blur * size).toFixed(2)}px)` : undefined,
        direction: 'rtl',
        ...textStyle,
        ...style,
      }}
    >
      {children}
      {m.underlineP > 0 && (
        <div
          style={{
            height: Math.max(4, size * 0.07),
            width: `${Math.round(m.underlineP * 100)}%`,
            margin: '0 auto',
            borderRadius: 999,
            background: acc,
          }}
        />
      )}
    </div>
  );
};
