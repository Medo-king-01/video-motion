import beats from '../plan/beats.json';

export type BeatScene = {index?: number; start: number; end: number; dur?: number};
export type Timeline = {duration: number | null; fps?: number; scenes: BeatScene[]};

export const TIMELINE = beats as Timeline;
export const PREVIEW_SECONDS = 8;
export const DURATION_SECONDS = Number.isFinite(TIMELINE.duration) && (TIMELINE.duration ?? 0) > 0
  ? TIMELINE.duration as number
  : PREVIEW_SECONDS;
export const DURATION_IN_FRAMES = Math.max(1, Math.round(DURATION_SECONDS * 30));
export const IS_PREVIEW_TIMELINE = !(Number.isFinite(TIMELINE.duration) && (TIMELINE.duration ?? 0) > 0);

// Replace these placeholders with the approved on-screen copy for each beat.
// Timing always comes from plan/beats.json, produced from the measured voice-over.
export const STORY = [
  {eyebrow: 'فكرة تتحرك', title: 'اكتب عنوان المشهد', body: 'حط هنا الجملة الأساسية اللي عايز المشاهد يفتكرها.'},
  {eyebrow: 'ببساطة', title: 'حوّلها لصورة', body: 'استخدم شكلًا أو رقمًا أو واجهة تخدم معنى الكلام.'},
  {eyebrow: 'الخلاصة', title: 'كل تفصيلة لها سبب', body: 'الحركة والإيقاع بيساعدوا الفكرة توصل بوضوح.'},
];
