// RAM Episode 03 — measured scene map (local Whisper word alignment + silence-midpoint cuts).
export const W=1080,H=1920,FPS=30;
export const scenes=[
  {id:'ram-intro',start:0.0,end:8.433},
  {id:'ram-question',start:8.433,end:12.358},
  {id:'ram-explain',start:12.358,end:19.951},
  {id:'ram-choose',start:19.951,end:22.042},
  {id:'ram-8gb',start:22.042,end:33.44},
  {id:'ram-16gb',start:33.44,end:45.254},
  {id:'ram-32gb',start:45.254,end:57.469},
  {id:'ram-bigger',start:57.469,end:62.41},
  {id:'ram-budget',start:62.41,end:67.0},
  {id:'ram-cta',start:67.0,end:70.52},
];
export const DURATION=scenes.at(-1).end;
export const ARABIC_FONT={family:'Cairo',urls:['/assets/fonts/Cairo/Cairo_800ExtraBold.ttf'],descriptors:{weight:'800'}};
