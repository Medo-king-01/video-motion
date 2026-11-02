import React from 'react';
import {PALETTE} from '../brand';
import {captionTransform} from './caption-motion.js';

export type TextMotionProps = {
  text: string;
  /** Absolute scene-local seconds. */
  time: number;
  /** Measured onset/offset of this word or fragment (never estimated here). */
  start: number;
  end: number;
  /** REQUIRED: explicit, agent-chosen style from plan/text-direction.json. */
  style: string;
  size?: number;
  x?: number;
  y?: number;
  color?: string;
  accent?: string;
  theme?: 'dark' | 'light';
  weight?: number;
};

/** Unboxed, brand-safe animated text for engine R. No default style. */
export const TextMotion: React.FC<TextMotionProps> = ({
  text, time, start, end, style, size = 76, x = 0, y = 0,
  color = PALETTE.paper, accent = PALETTE.salmon, theme = 'dark', weight = 800,
}) => {
  const elapsed = Math.max(0, time - start);
  const dur = Math.max(0.05, end - start);
  const m = captionTransform(style, elapsed, dur);
  const acc = theme === 'dark' ? accent : PALETTE.red;
  const base = theme === 'dark' ? PALETTE.paper : PALETTE.ink;

  const karaoke = m.karaokeP >= 0;
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
        position: 'absolute',
        left: `calc(50% + ${x + m.x * size}px)`,
        top: y + m.y * size,
        transform: `translate(-50%, -50%) rotate(${m.rotate}deg) scale(${m.scale})`,
        opacity: m.opacity,
        filter: m.blur * size > 0.2 ? `blur(${(m.blur * size).toFixed(2)}px)` : undefined,
        fontFamily: 'Cairo, sans-serif',
        fontWeight: weight,
        fontSize: size,
        lineHeight: 1.2,
        direction: 'rtl',
        textAlign: 'center',
        whiteSpace: 'nowrap',
        ...textStyle,
      }}
    >
      {text}
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
