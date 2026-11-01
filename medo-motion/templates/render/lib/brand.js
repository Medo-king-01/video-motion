// Medo brand tokens for the Canvas/Playwright engine. Source of truth: brand/brand.json (keep in sync; run scripts/brand_check.py).
export const BRAND = {
  W: 1080, H: 1920, FPS: 30,
  colors: { red: '#E5262B', redDark: '#96141A', black: '#0A0A0C', ink: '#18161A', ink2: '#342A2C', white: '#F6F3ED',
            yellow: '#F4C430', gold: '#CD8C0A', emerald: '#14B88A', teal: '#1F8A8A',
            bgDarkTop: '#100F13', bgDarkBottom: '#070709',   // brand.json backgrounds.dark
            bgLightTop: '#F7F5F3', bgLightBottom: '#E7E4E2' },
  font: { ar: 'Cairo', weight: 800 },
  // No logo and no series chip in this studio: the HUD is the progress bar only.
  safe: { margin: 40, contentY: [200, 1350], captionY: 1455, belowIsDead: 1500, progressY: 64, groundY: 1390 },
  caption: { plate: 'rgba(48,38,40,0.91)', border: '#E5262B', borderPx: 3, sizePx: 58, maxW: 970, maxLines: 2 },
  lufs: -14.5, truePeakMax: -1.5,
};
