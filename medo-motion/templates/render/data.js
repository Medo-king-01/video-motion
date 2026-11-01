// Design dimensions and absolute scene timing. Replace the examples with approved scenes.
export const W = 1080, H = 1920, FPS = 30;
export const scenes = [
  { id: 'example', start: 0, end: 2 },
  { id: 'arabic-example', start: 2, end: 7 },
  { id: 'explainer-example', start: 7, end: 18.5 },   // explainer-reel kit demo (lib/kit.js)
  { id: 'icons-example', start: 18.5, end: 22 },       // animated icon layer demo (lib/icons.js)
  { id: 'motion-example', start: 22, end: 25 },        // keyframe timeline demo (lib/motion.js)
  { id: 'transition-example', start: 25, end: 28.2 },  // mask/transition demo (lib/transition.js)
  { id: 'presenter-example', start: 28.2, end: 31.4 }, // Medo poses demo (lib/presenter.js)
  { id: 'kinetic-example', start: 31.4, end: 35.4 },   // beat grid + 3D + velocity blur (lib/beat|space3d|motion)
];
// The reel has no target length: DURATION is whatever the VO measures. Build `scenes` from
// `python3 tools/vo_length.py <vo> --json plan/beats.json` and keep the last end == VO duration.
export const DURATION = scenes.at(-1).end;
// Arabic display font = brand lock (Cairo). Put it in the project:
//   python <skill>/scripts/get_fonts.py "Cairo"     (or copy your own Cairo*.ttf)
// Falls back to a system font if the file is missing, which is NOT brand-safe.
export const ARABIC_FONT = {
  family: 'Cairo',
  urls: ['/assets/fonts/Cairo/Cairo_800ExtraBold.ttf',
         '/assets/fonts/Cairo/Cairo[wght].ttf',
         '/assets/fonts/Cairo/Cairo-Bold.ttf'],
  descriptors: { weight: '800' },
};
