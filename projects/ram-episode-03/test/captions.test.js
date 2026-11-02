import assert from 'node:assert/strict';
import { activeWordAt, validateWordTimeline } from '../src/lib/captions.js';

const words = [
  { text: 'قبل', start: 0.12, end: 0.38 },
  { text: 'ما', start: 0.38, end: 0.51 },
  { text: 'تشتري', start: 0.51, end: 0.92 },
];
assert.equal(validateWordTimeline(words), true);
assert.equal(activeWordAt(words, 0.11), null);
assert.equal(activeWordAt(words, 0.12).text, 'قبل');
assert.equal(activeWordAt(words, 0.40).text, 'ما');
assert.equal(activeWordAt(words, 0.92), null);
assert.throws(() => validateWordTimeline([{ text: 'x', start: 1, end: 2 }, { text: 'y', start: 1.5, end: 3 }]), /overlaps/);
console.log('caption timeline tests passed');
