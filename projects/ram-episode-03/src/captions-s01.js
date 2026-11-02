// S01 word-level timeline — measured with local faster-whisper (Whisper small CT2 int8)
// against assets/vo/episode-03-ram.wav. Source: cache/s01-whisper-vad0.json.
// Onsets that Whisper placed before audible speech were snapped to measured
// silence-end boundaries from the same WAV (ffmpeg silencedetect -38dB).
// Times are scene-local seconds; end exclusive. One spoken word at a time.
export const CAPTIONS_S01_STATUS = 'whisper-small-ct2-int8-measured';
export const CAPTIONS_S01 = [
  { text: 'قبل', start: 0.865, end: 1.040 },
  { text: 'ما', start: 1.040, end: 1.160 },
  { text: 'تشتري', start: 1.160, end: 1.500 },
  { text: 'لابتوب', start: 1.500, end: 2.292 },
  { text: 'أكيد', start: 2.292, end: 2.500 },
  { text: 'شوفت', start: 2.500, end: 2.800 },
  { text: 'أجهزة', start: 2.800, end: 3.140 },
  { text: 'فيها', start: 3.140, end: 3.380 },
  { text: '8', start: 3.380, end: 3.600 },
  { text: 'جيجا', start: 3.600, end: 4.060 },
  { text: 'RAM', start: 4.060, end: 4.602 },
  { text: 'وأجهزة', start: 4.602, end: 5.240 },
  { text: 'فيها', start: 5.240, end: 5.480 },
  { text: '16', start: 5.480, end: 6.450 },
  { text: 'وأجهزة', start: 6.450, end: 6.880 },
  { text: 'فيها', start: 6.880, end: 7.100 },
  { text: '32', start: 7.100, end: 7.700 },
  { text: 'جيجا', start: 7.700, end: 8.080 },
];
