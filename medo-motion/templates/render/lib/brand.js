// Medo brand tokens for the Canvas/Playwright engine.
// Source of truth: brand/brand.json (palette v2). Keep in sync; run `python medo-motion/scripts/brand_check.py`.
// 12 brand colours, nothing invented. `inkShadow` is a derived shade (ink darkened 35%), not a 13th brand colour.
export const PALETTE = {
  red:       '#CB271B', // primary: big circle, key words, borders
  redBright: '#CB0801', // strongest emphasis, light backgrounds only
  redDeep:   '#9F0803', // depth / pressed / shadow side of red
  ink:       '#473938', // dark base, text on light, device bodies, caption plate
  inkSoft:   '#8B6765', // secondary large text, device screen bars, dividers
  paper:     '#F3F2F1', // text on dark, top of light background
  gray1:     '#D8D7D5', // bottom of light background, cards
  gray2:     '#C9C5C2', // inactive fills, progress track
  gray3:     '#BFBAB7', // subtle large text on dark, disabled
  gray4:     '#A3A2A0', // secondary text on dark (large sizes only)
  salmon:    '#D97F68', // warm accent: numbers/keywords on dark, glow, warm skin
  blush:     '#D5AEA6', // soft accent: highlight chips, light skin
  inkShadow: '#2E2423', // derived (ink -35%): dark bg bottom, ink shadows
};

export const BRAND = {
  W: 1080, H: 1920, FPS: 30,
  colors: { ...PALETTE,
            // background ramps (brand.json backgrounds)
            bgDarkTop: '#473938', bgDarkBottom: '#2E2423',
            bgLightTop: '#F3F2F1', bgLightBottom: '#D8D7D5' },
  palette: PALETTE,
  font: { ar: 'Cairo', weight: 800 },
  // No logo and no series chip in this studio: the HUD is the progress bar only.
  safe: { margin: 40, contentY: [200, 1350], captionY: 1455, belowIsDead: 1500, progressY: 64, groundY: 1390 },
  caption: { plate: 'rgba(71,57,56,0.91)', border: PALETTE.red, borderPx: 3, sizePx: 58, maxW: 970, maxLines: 2 },
  lufs: -14.5, truePeakMax: -1.5,
};

export default BRAND;
