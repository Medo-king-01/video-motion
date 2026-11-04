// Mirrors brand/brand.json. brand_check.py verifies these values against the source of truth.
export const PALETTE = {
  red: '#CB271B',
  redBright: '#CB0801',
  redDeep: '#9F0803',
  ink: '#0A0A0A',
  inkSoft: '#71717A',
  paper: '#F3F2F1',
  gray1: '#D8D7D5',
  gray2: '#C9C5C2',
  gray3: '#BFBAB7',
  gray4: '#A3A2A0',
  salmon: '#D97F68',
  blush: '#D5AEA6',
  inkShadow: '#030303',
  bgDarkTop: '#0A0A0A',
  bgDarkBottom: '#030303',
  bgLightTop: '#F3F2F1',
  bgLightBottom: '#D8D7D5',
} as const;

export const BRAND = {
  width: 1080,
  height: 1920,
  fps: 30,
  font: 'Cairo',
  margin: 40,
  progressY: 64,
  contentY: [200, 1350] as const,
  captionY: 1455,
  belowIsDead: 1560,
} as const;
