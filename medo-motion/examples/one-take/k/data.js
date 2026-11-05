// One absolute VO scene and one uninterrupted visual environment; no scene-to-scene transitions.
export const W = 1080;
export const H = 1920;
export const FPS = 30;
export const DURATION = 8;
export const scenes = [
  { index: 1, id: 'one-take', start: 0, end: 8, dur: 8, frames: 240, theme: 'light' },
];
export const beats = { duration: 8, fps: FPS, frames: 240, scenes };
