<!-- Video Motion · mandatory guidance before rendering Arabic text. -->
# Arabic typography in motion

Arabic is a joined, right-to-left script whose letters change shape with their neighbours. Most motion techniques from Latin tutorials silently break it. Read this guide whenever a frame contains Arabic, and use `templates/render/lib/arabic.js` in code.

## 1. Hard rules (never break)
1. **Never draw Arabic letter by letter.** One `fillText`/`strokeText` call per word (or per line). Separate calls produce isolated letter forms: «م ر ح ب ا» instead of «مرحبا».
2. **No per-letter effects on Arabic:** no per-letter stagger, character typewriter, glyph scramble/decode, per-letter colour, or per-letter physics. They all split the word.
3. **No letter-spacing / tracking on Arabic.** `ctx.letterSpacing`, CSS `letter-spacing` and "tracking collapse" insert gaps inside joined letters. Keep it `0px`.
4. **Set direction.** `ctx.direction = 'rtl'` for Arabic runs. With `textAlign = 'right'` the anchor is the start of the line.
5. **Keep the dots.** Letters differ only by their dots (ب ت ث ن ي، ج ح خ، ر ز، س ش، ص ض، ط ظ، ع غ، ف ق). Clip rects, masks, outlines and crops must include the full ink box plus padding (`measureText().actualBoundingBoxAscent/Descent` + 15 %). A cut dot changes the word.
6. **No decorative dots or periods near Arabic words.** A bullet, full stop or design dot placed just above or below a word reads as a letter dot and changes the word. Keep decorative marks at least 0.4 em away from the ink.
7. **Never break a word across lines** and never hyphenate. Break at phrase boundaries.
8. **Load the real font files before frame 0** (`FontFace` + `await document.fonts.ready`), then render a test still. Headless Chromium on a clean machine may have no Arabic fallback at all (empty boxes) or a different one than the user's browser.

## 2. Safe kinetic vocabulary (Arabic)
| Effect | How |
|---|---|
| Word pop / rise / blur-in | Whole word: scale 0.85→1, y +24→0, blur 12→0 px, opacity 0→1, 180–260 ms, easeOutCubic. Stagger by word, 60–120 ms |
| **Typewriter feel** | Draw the whole shaped word inside a clip rect that grows **from right to left** (`wipeReveal` in `lib/arabic.js`). A cursor rides the left edge of the clip |
| Karaoke highlight | The spoken word changes colour/weight on its VO onset (word timings from `beats.json`) |
| Highlight bar / underline | A bar or hand-drawn underline sweeps right→left under or behind the word |
| Word swap in one slot | Cross-fade or slide-swap whole words («وقت» → «فلوس»). This replaces glyph scramble |
| Weight morph | Variable `wght` axis (Kufam, Alexandria, Readex Pro, Cairo): animate weight on a whole word |
| Outline → fill | `strokeText` the whole word, then fade in `fillText` |
| Slam with echo | Scale 1.4→1 ease-out-expo 0.25 s with 3–5 fading echo copies of the whole word |
| Mask reveal by line | Reveal a full line with a rectangular or shaped mask moving right→left |
| 3D / extrude | Render the whole word to a canvas texture, then extrude or map it in 3D |

## 3. Layout
- **Reading flow is right to left.** For Arabic audiences, progress bars, timelines and "next" motion usually travel right→left. UI mock-ups of LTR apps stay LTR. Choose per scene and keep it consistent.
- **Word order in word-by-word layout:** the first word sits at the right. Use `layoutWords` in `lib/arabic.js`; it measures each word and the space in the same font.
- **Mixed Arabic + Latin + numbers:** draw a full mixed line in one call with `direction='rtl'` so the bidi algorithm orders the runs. When animating word by word, Latin words keep their internal LTR shape automatically.
- **Line height 1.4–1.7.** Arabic ascenders and descenders (ل ك ط، ي ع ج ح خ م ر ز و) need room. Caption boxes need more vertical padding than Latin.
- **Optical size:** Arabic looks smaller than Latin at the same px. Scale Arabic up 10–20 % when pairing.
- **Captions:** 2–4 words per group for shorts, one keyword per group, keep short prepositions («في»، «من»، «على») with the next word.
- **Safe zones (9:16):** same as `visual-design.md`. Arabic is right-aligned or centred; keep the right edge clear of platform buttons (≈140 px).

## 4. Writing
- **Numerals:** pick Western digits (0–9) or Arabic-Indic (٠–٩) once per project and keep it. Medo uses Western digits (0–9).
- **Punctuation:** Arabic comma «،», question mark «؟», semicolon «؛». Brackets and quotes mirror in RTL; check them in a still.
- **Diacritics (تشكيل):** only to remove ambiguity or for a stylistic hero word. They need extra line height and a font that positions them well.
- **Dialect vs MSA:** on-screen text follows the narration. Egyptian dialect VO → natural Egyptian spelling («إيه»، «ليه»، «دلوقتي»، «عايز»). Formal topics → MSA. Spell the same word the same way everywhere.
- **Hamza and taa marbuta:** keep «أ إ» and «ة» correct in headlines; they are hero words that people screenshot.
- **Kashida (ـ):** avoid as a stretching trick unless the font is designed for it.

## 5. Fonts
Pick from `reference/arabic-fonts.md`. Download free (OFL) families with `scripts/get_fonts.py`; it saves the licence beside the files and records them in `manifest.json`. Max 2 Arabic families per video: one display, one text.

## 6. QA checklist for every Arabic frame
Zoom a still to 100 % and check:
- [ ] every word is joined correctly; no isolated letter forms
- [ ] all dots present and not cropped by masks or the frame edge
- [ ] descenders not clipped (ي ع ج ح خ م ر ز و)
- [ ] word order right→left; mixed lines ordered correctly
- [ ] numerals consistent; punctuation and brackets mirrored correctly
- [ ] the intended font is used (no fallback shapes, no empty boxes)
- [ ] no decorative dot touching or close to a word
- [ ] text inside safe zones with contrast ≥ 4.5:1 against what is behind it

## 7. Code pattern
```js
import { loadFont, setArabic, layoutWords, wipeReveal } from './lib/arabic.js';
// init(): await loadFont('Kufam', '/assets/fonts/Kufam/Kufam[wght].ttf');
setArabic(ctx, { family: 'Kufam', size: 140, weight: 900 });
const words = layoutWords(ctx, 'صوّر خام والباقي علينا', { x: W / 2, y: H * 0.45, maxWidth: W * 0.8, lineHeight: 1.5 });
words.forEach((w, i) => {
  const p = clamp01((t - w.logicalIndex * 0.1) / 0.25);   // spoken-order timing even with embedded English
  ctx.globalAlpha = p; ctx.fillText(w.text, w.x, w.y + 24 * (1 - easeOut(p)));
});
wipeReveal(ctx, () => ctx.fillText('خام', W / 2, H * 0.6), bbox, progress);   // right→left typewriter
```

## 6. Unicode-Safe Kashida, Mixed English Runs & Phrase Chunks

1. **Kashida (`ـ` U+0640) follows Unicode `ArabicShaping` joining grammar (`kashidaSlots`, `drawKashida` in `lib/arabic.js`; `kashida_slots`, `draw_kashida` in `arabic_shape.py` / `lib.py`):**
   - Insert tatweel **only** after a dual-joining letter (`ب ت ث ج ح خ س ش ص ض ط ظ ع غ ف ق ك ل م ن ه ي ئ`) when followed by a right-capable letter.
   - **Never** insert after right-only letters (`ا أ إ آ د ذ ر ز و ؤ ة ء ى`) — `تحرّـــك` detaches; `تحـــرّك` joins cleanly.
   - **Never** split a base letter from its harakat/shadda (`[\u064B-\u065F\u0670]`) — place tatweel **after** the diacritic cluster.
   - **Never** insert between `ل` and `ا/أ/إ/آ/ٱ` (breaks the mandatory `لا` ligature).
   - Combine integer tatweel steps with a capped residual `scaleX <= 1.06` so animated kashida stretches never snap visibly between glyph counts.
2. **Multi-word English/number phrases inside RTL lines (`visualWordOrder` / `visual_word_order`):**
   - Contiguous Latin/numeric tokens (`"Claude Code 2.0"`, `"DDR5 16GB"`, `"VS Code"`) must stay left-to-right visually inside an RTL sentence while preserving `logicalIndex` for spoken-order staggers.
3. **Phrase-chunk captions (`drawPhraseCaption` / `draw_phrase_caption`):**
   - Group measured VO words into `2–4` word single-line RTL phrases (`groupCaptionChunks` / `group_caption_chunks`), never orphaning Arabic glue particles (`في`, `من`, `على`, `إلى`, `عن`, `مع`, `مش`, `اللي`...) at a chunk boundary.
   - Pass `hideRanges` (`[[start, end], ...]`) whenever hero kinetic typography already displays the spoken words on screen so captions never duplicate hero text.
   - Keep right-aligned Arabic clear of the social right-rail action column (`x: 940..1080, y: 1100..1500`; opt-in `L04` via `--platform-ui` or `tools/phone_preview.py`).

