<!-- Khaam Motion · reference file, loaded on demand from SKILL.md. Directing system for explainer / tool / list reels. -->
# Explainer reel system — a director's grammar

Use this for reels that **explain, teach, list or sell an idea**: tools, tips, "4 plugins you need", "how I made this", product demos. It is a **format, not a look**: it works with the user's own style or any example in `styles/`. Code components live in `templates/render/lib/kit.js`.

The grammar comes from analysing high-performing faceless explainer reels: one consistent frame, one idea per beat, a literal visual for every spoken phrase, constant small motion, and a comment-keyword ending.

## 1. Script skeleton (write this before any visuals)

**Length is never fixed:** the reel is exactly as long as the voice-over. The seconds below are one
worked example for a 55 s VO — stretch or compress them proportionally to the real VO duration
(`tools/vo_length.py`).
| Beat | Time (scale to the VO) | Job | Arabic pattern |
|---|---|---|---|
| **Hook** | 0–3 s | A number/result claim, or a warning | «كبّرت هالحساب لـ ٤٠ ألف في ٥ أسابيع…» / «لا تبدأ [س] قبل ما تثبّت هذي الـ٤» |
| **Stakes** | 3–10 s | Why now: urgency, a gap, a cost | «بعد ٣ شهور السوق بيمتلي…» |
| **Proof** | 10–20 s | Evidence on screen: numbers, screenshots, results | «والدليل…» + counter + screenshot |
| **Mechanism / list** | 20–45 s | Items 1…N. Each: name → what it does → one concrete example | «الأولى…»، «الثانية…» |
| **How easy** | inside the list | Show the actual tool/UI doing it | «كل اللي تسويه…» |
| **CTA** | last 4–6 s | Comment keyword → you send it | «علّق [كلمة] وأرسلها لك» |

- **Hook:** follow `reference/hooks.md` (research, 3 options, first 3 seconds built and approved first).
- One sentence per beat. Numbers are concrete («٢٢١ ملف»، «٣٠٠ ألف نجمة»), never vague.
- **Pace:** the references run 215–240 English words per minute. Arabic words are longer: aim for about 150–170 words per minute and set pace at voice generation (never time-stretch afterwards).
- Write the visual for each line in the same table (Audio | Visual). If a line has no visual idea, rewrite the line.

## 2. The persistent frame (HUD)
Every shot shares the same frame so the reel feels like one product.
| Element | Where (9:16, RTL) | Kit |
|---|---|---|
| **Section label** «// 02 · النظام» or a tape sticker | top-right (top-left for LTR) | `sectionLabel` |
| **Progress device**: «٢/٥» pips, or a metaphor tied to the topic (sockets that get plugged for "plugins", boxes that tick) | top-left (top-right for LTR) | `progressPips`, `slotStrip` |
| **Caption system**: pick ONE per video (see §3) | top block or bottom keycaps | `captionBlock`, `keycaps` |
| **Hero zone**: one visual per beat | centre, about y 520–1450 | — |
| **Handle watermark** small, 30–40 % opacity, near the hero (harder to crop out) | mid-frame edge | `handleTag` |
Numbers in labels: use Western digits («02») or no leading zero; the Arabic-Indic zero «٠» is a dot and reads like the separator.
Keep platform safe zones: nothing important in the top ≈ 220 px, bottom ≈ 420 px, right ≈ 140 px.

## 3. Caption systems
- **A · Editorial top caption:** the spoken clause builds word by word at the top; the **keyword switches font and colour** (Latin: serif italic in red; Arabic: a calligraphic face such as Aref Ruqaa, Amiri or El Messiri in the accent colour). Black text, one accent. Clears at each new clause.
- **B · Keycaps:** 1–3 words at the bottom, each on a keyboard-key pill with depth; the spoken word turns accent yellow; keywords can be inverted (dark key). Groups change on clause boundaries.
Both are **word-level**, so they suit Arabic. Timings come from `plan/beats.json` (VO word timestamps).

## 4. Visual vocabulary
**Rule: every spoken phrase gets a literal visual.** Say it, show it.
| Spoken | Literal visual |
|---|---|
| «السوق بيزحم» | crowd of simple figures holding phones, then a «زحمة» stamp |
| «اللي بدأ أول» | podium «١» with a spotlight; a small figure labelled «تأخر» |
| «أغلب المحتوى ضعيف» | grid of identical thumbnails + a «ضعيف» stamp slammed on top |
| «مجلد واحد» | a folder card with file tabs sticking out + a chip «٢٢١ ملف» |
| «تحطه في Claude Code» | an app window; the folder drops into it |
| «٣٠٠ ألف نجمة» | a repository card with a rolling star counter |
| «يكتب، يسجّل، يحرّك، يرندر» | a checklist panel whose steps tick one by one beside a phone preview |
| «علّق الكلمة» | comment field typing the keyword → DM card arriving |

Device library (all in `kit.js`): phone mock-up, app/terminal window, checklist, card, folder, stamp, chip, rolling counter, slot strip, comment CTA, burst lines, hand-drawn circle highlight, halftone image.

**Real-looking UI beats illustration.** Profile cards with follower counts, terminals, repo cards and checklists are cheap to draw in code and read instantly. Use the user's own screenshots inside phone/app frames whenever possible.

## 5. Rhythm and motion
- A new visual event every **0.8–1.5 s**. Within a section elements **accumulate** (build-up), then everything resets at the section change.
- Entrances: scale 0.8→1 with `outBack`, or slide 60–120 px with `outCubic`, 0.25–0.4 s. Cards settle at a slight rotation (±2–4°).
- Every number **counts up** (`rolling`), never appears static.
- Emphasis: burst lines, a hand-drawn circle around the key item, a red underline, or a stamp slam (scale 1.6→1, `outExpo`, 0.25 s, 2–3 px shake).
- Typing: code/Latin types per character; **Arabic is revealed by a right→left wipe**, never per letter.
- Hold the final state of each beat at least 0.4 s so it can be read.

## 6. Transitions
- **Chapter change:** halftone dot wipe (`halftoneWipe`): dots grow from an origin to cover the frame (0.25 s), the scene swaps under full cover, dots shrink to reveal the next (0.3 s). Or a **colour-world switch**: each section owns a flat colour family (background, desk, labels) and the whole world recolours on the cut.
- **Within a chapter:** push/pop of the hero device, cards sliding in from the edge, the phone screen changing content.
- No generic cross-dissolves.

## 7. Texture and finish
- Paper base with grain 6–8 % (`paperTile`), or flat colour worlds with a subtle dot grid.
- Halftone shading unifies mixed sources: run screenshots and photos through `halftoneImage` so they look printed.
- Soft drop shadows (y 12–20 px, blur 30–40 px, 15–20 % black). Stickers get a thick outline.
- Palette: a neutral base (paper `#F2EFE8`, ink `#141414`) + **one accent** (e.g. red `#E8322B`), 60-30-10. Colour worlds use one hue family per section.
- Type roles: clean sans for captions (Alexandria, IBM Plex Sans Arabic), calligraphic accent for keywords (Aref Ruqaa, El Messiri), heavy condensed for stamps (Kufam 900, Jomhuria, Badeen Display), mono for labels and UI (JetBrains Mono).

## 8. Sound
- VO master around −14 LUFS, music bed 18–22 dB under the voice, or no music.
- Soft pop on each element entrance, whoosh on chapter wipes, ticks on counters, a thud on stamps, key clicks on typing, a notification chime on the CTA DM.
- Openverse queries: `pop`, `ui pop`, `whoosh`, `tick`, `stamp`, `typing`, `notification`. Keep SFX short and dry; never one sound on every frame.

## 9. CTA end card (always)
4–6 s: the keyword big on screen, a comment field typing it, the comment posts, then a DM card slides in («وصلتك الرسالة») holding the promised thing (folder/file/link). Use `commentCTA`. Repeat the keyword in the caption. It must match the comment-to-DM automation.

## 10. Assets without image generators
Everything above is code-drawn. For a phrase that needs a complex picture, prefer in order: (1) the user's own screenshot/photo (framed + halftone), (2) a UI or data metaphor, (3) a typographic metaphor (stamp, giant number), (4) a simple code-drawn figure (circles + rounded rectangles, like the crowd), (5) only then ask the user for an image. AI image/video generation is optional and outside this skill.

## 11. Kit quick reference (`templates/render/lib/kit.js`)
| Function | Draws |
|---|---|
| `paperTile(seed, opts)` + `drawPaper(ctx, W, H, tile, base)` | paper base with grain (tile made once in `init`) |
| `halftoneWipe(ctx, W, H, p, opts)` | chapter transition overlay, p 0→1 (swap the scene at p = 0.5) |
| `halftoneImage(ctx, img, x, y, w, h, opts)` | printed-dot version of a screenshot/photo |
| `sectionLabel`, `progressPips`, `slotStrip`, `handleTag` | the HUD |
| `captionBlock(ctx, words, t, opts)` | editorial top caption with keyword switch |
| `keycaps(ctx, words, t, opts)` | bottom keycap captions |
| `phone(ctx, x, y, w, drawScreen, opts)` | phone mock-up; draws your screen inside a clip |
| `appWindow(ctx, x, y, w, h, opts)` | app/terminal window; `opts.body` draws inside |
| `typeLines(ctx, lines, t, opts)` | terminal typing (Arabic lines wipe) |
| `checklist(ctx, items, t, opts)` | steps: pending → spinner → tick |
| `card`, `folder`, `chip`, `stamp`, `burst`, `circleMark` | devices and emphasis |
| `rolling(from, to, p, opts)` | counter text (Western or Arabic-Indic digits) |
| `commentCTA(ctx, t, opts)` | the comment → DM end card |
| `ease`, `seg`, `rng` | easing, local progress, seeded random |
`templates/render/scenes/explainer-example.js` shows them together in Arabic.

## 12. Pre-render checklist
- [ ] Script table: every line has a literal visual
- [ ] HUD identical on every shot; label and progress update at each section
- [ ] One caption system for the whole reel, word-timed
- [ ] A visual event every 0.8–1.5 s; every number counts up
- [ ] Chapter transitions consistent (halftone or colour world)
- [ ] CTA end card with the same keyword as the automation
- [ ] Arabic QA checklist passed (`reference/arabic-typography.md` §6)
