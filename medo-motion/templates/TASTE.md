# TASTE – <project name>
<!--
  TASTE MEMORY of this motion-graphics project. Written and kept up to date by the AI agent.
  PURPOSE: a brand-new chat (any agent, any model) must be able to read ONLY this file
  (+ PROGRESS.md) and continue making scenes that look, move and sound exactly like the
  approved ones — same theme, same concept, same design system, same feel.
  The studio-wide design system reference is DESIGN_SYSTEM.md at the repo root; this file
  records the project-specific approved values on top of it.
  RULES FOR THE AI:
   - Fill it as soon as a decision is approved (style board, preview, feedback). Never leave "TBD" for something already decided.
   - Write concrete, buildable values (hex codes, font files, px sizes, ms timings, easing names, dB levels, file paths), not vague words.
   - Overwrite sections 1–8 when a decision changes (note the old value in §10). Section 9 (feedback rules) is append-only.
   - Read this file BEFORE planning, before building any new scene, and first thing in every new chat.
-->
Updated: YYYY-MM-DD HH:mm · by: <agent> · current version: v<N> → renders/final/<name>_v<N>.mp4
Status of this file: draft | approved style (locked) ← only "approved" values may be reused without asking
**BRAND LOCK (Medo):** §3, §5, §6 and §8 below are pre-filled from `brand/BRAND.md`. They are locked: do not re-ask Medo about colours, fonts, safe zones, loudness or dialect. Only the project-specific parts (§1, §2 mood, §4 devices, §7) are filled per video.
Visual version for the user: plan/design.html (same values as §2–§5 — always update both together)

## 1. Brief, concept & story (what we are making and why)
- **One-line concept:** <e.g. "A pixel-art founder fights a giant 'busywork' monster; words decode from binary">
- **Video type / platform / format:** <e.g. Instagram Reel, 9:16 1080×1920, 30 fps> · **length = the VO duration** (measure it: `tools/vo_length.py`; never plan a target length) · no series name / title / episode number unless the user explicitly asks
- **Audience & goal / CTA:** <who, what they should do>
- **Inputs (only these):** script (beats) · scene direction · VO audio · Medo poses · **use:** <personal | client/commercial (licences!)> · **deadline:** <…>
- **No logo / no default series name / no episode chip.** Never ask for them, never invent or suggest them, never reserve a circle for one. A name/title/episode number goes on screen only when the user asks, worded by him.
- **Story world & characters:** <setting, characters + personality, recurring props, what each character looks like (link model sheet: assets/…)>
- **Narrative structure:** <hook → problem → solution → proof → CTA, with seconds>
- **Pipeline:** <A code-drawn / B mixed AI assets / C footage edit, per scene if mixed (§2c)>

## 2. Theme & feel (the "sense" of the video)
- **Mood words (3–5):** <e.g. playful · techy · retro-arcade · confident>
- **Theme / visual world:** <e.g. dark 8-bit pixel world with teal-binary tech overlays, CRT grain>
- **Intensity level:** <1–5 (§4)> · **pacing:** <cut every X s, hold on hero words Y s>
- **Feels like (references):** <file in assets/refs/ or link — what exactly to copy from it (technique, timing, sound)>
- **Must NOT feel like:** <e.g. corporate stock template, glossy 3D, trailer-style>

## 3. Visual design system
- **Palette (hex + role, 60-30-10) [LOCKED brand, palette v2 — exactly 12 colours]:** background `#0A0A0A`→`#030303` dark / `#F3F2F1`→`#D8D7D5` light (alternate per scene) · primary `red #CB271B` (+ `red_deep #9F0803`, `red_bright #CB0801` on light only) · ink `#0A0A0A` · secondary `ink_soft #71717A` · soft accents `salmon #D97F68` (numbers/keywords on dark) and `blush #D5AEA6` (highlight chips) · neutrals `gray_1 #D8D7D5` · `gray_2 #C9C5C2` · `gray_3 #BFBAB7` · `gray_4 #A3A2A0` (large text on dark only) · text `paper #F3F2F1` on dark / `ink #0A0A0A` on light. **No yellow, no green, no blue.** Positive emphasis = paper white + ✓ glyph. Never red text on dark (2.01:1) — use salmon. Source: `brand/brand.json`.
- **Typography [agent-chosen]:** the agent picks the most fitting face per scene/element from `assets/fonts/fonts.json` (21 OFL families) and records it in `plan/text-direction.json` (`fontStyles`/`fontElements`). No forced default; Cairo/Inter are only a system-chrome fallback. Captions **unboxed** (no plate/border/panel), max width 970, whole words only · min sizes: card label 44, chip 40, icon 128 (animated icon layer: `icons/`).
- **Arabic (if any):** display <family + weight + file> · text <family> · numerals Western 0–9 (locked) · language <Egyptian dialect (ar-EG) — LOCKED> · line-height <1.4–1.7> · rules: whole words only, RTL, no tracking (`<skill>/reference/arabic-typography.md`)
- **Style preset:** <name from <skill>/styles/ or "custom"> · changes from the preset: <…>
- **Text treatment:** <fill, outline px, offset shadow (x,y,color), glow, backing rule for contrast>
- **Type [allowed set, agent-chosen]:** any family from `assets/fonts/fonts.json` (all SIL OFL 1.1, see `docs/fonts.md`), chosen per scene/element with a rationale · prefer an Arabic↔Latin pair with the same feel · headline family / caption family / mono family — never three at once without a recorded reason.
- **Layout [LOCKED brand]:** canvas 1080×1920 @30 · content y 200–1350 · caption centre y≈1455 · nothing important below y≈1500 · margin 40px · progress bar y≈64 (no chip)· character ground y≈1380–1400 · no vertical gap >300px
- **Textures & finish:** <grain %, scanlines, halftone, vignette, grade/LUT file>
- **Illustration / asset style:** <pixel size (e.g. 6 px grid), line weight, shading style, character proportions, AI-image prompt + style-sheet file for pipeline B>
- **Backgrounds & environments:** <…>

## 4. Motion language
- **Easing family:** back/elastic pops, slide+fade cards, stagger 0.14–0.6 s (register A, intensity 4) · register B (intensity 2): slow ≥0.8 s eases, no shake/flash
- **Text animation:** chosen by the agent for EVERY on-screen text element in `plan/text-direction.json` (captionStyle + textStyles/textElements + rationale) — captions, titles, keywords, numbers, CTAs, labels, card/UI text. No default look; vary with the mood/energy. Draw only via `drawDirectedText` (K) / `draw_directed_text` (P) / `DirectedText` (R). Whole-word only, measured VO/scene timing, unboxed, brand colors. Catalog: `docs/text-animations.md`.
- **Signature devices [LOCKED brand]:** big red circle (80–95 % width) behind the hero + ground shadow · red wipe with white edge 0.4 s between scenes · camera zoom 1.00↔1.04 + drift ±14px · one impact per scene (ring + speed lines + 6–12px shake + 1–2 frame flash) · HUD (progress bar only) drawn AFTER the camera
- **Transitions:** <hard cut on beat / pixel wipe / zoom-through…>
- **Camera:** <static / slow push 2 %/s / shake on impact (amp px, duration)>
- **Character acting rules:** <idle bob, blink rate, how gestures read, no frozen poses > 1 s>

## 5. Sound identity
- **Text SFX:** <type (soft dry ticks/pops), 40–150 ms, one per word, level vs VO (e.g. −7 dB)>, files: <assets/sfx/…>
- **Hero / impact sounds:** <…> · **decode ticks:** <…> · **transitions:** <…>
- **Foley:** <cloth rustle on arm moves, footsteps, creature chirps…>
- **Music:** <track/file, BPM, licence, level under VO>
- **Mix targets [LOCKED brand]:** SFX ≈0.40× VO peak · music bed Am–F–C–G 76 BPM ducked 62 % under VO (~0.17×) · loudness −14.5 ±0.3 LUFS · TP ≤ −1.5 dBTP (two-pass loudnorm)
- **Banned sounds:** <e.g. long whooshes, risers, jet/thruster swooshes on text>

## 6. Voice
- **VO [LOCKED brand: Egyptian ar-EG; Medo's own wav wins, else ≥2 TTS rounds and he chooses; then one voice + fixed atempo 1.15–1.22×]:** <voice name + voice_id; source: library voice | Instant Voice Clone from <sample file> (SHA-256, rights and consent confirmed by the user on YYYY-MM-DD)>, model `eleven_v4` (previews `eleven_v4_turbo`; never v3), Stability <0.5>, Similarity <0.75>, seed <n>, language/dialect <…>, output <mp3_44100_192 | wav_48000>, tone <…>, files <assets/vo/…>
- **Script style:** <short punchy lines, approved audio tags, pronunciation list (word → /IPA/ or respelling)>

## 7. Technical setup (so a new chat can render immediately)
- **Render:** `<command>` (CLI contract §2) · preview: `node scripts/preview.mjs <from> <to>`
- **Key code files:** <src/scenes/…, src/fx/…, timing in plan/beats.json / src/data.js>
- **Reusable modules that define the look:** <e.g. src/fx/fx5.py = hero-word effects; src/pixel_chars.py = character renderer>
- **Assets that must be reused:** <fonts, sprites, LUT, SFX set folder>

## 8. Do / Don't (quick rules)
- DO: alternate light/dark scenes with a different grid each · one big hero per scene · declare every placeholder (temporary font, presenter pose) in the delivery message · check contact sheets ≥3 rounds · master ≥2.5 Mbps
- DON'T: white/yellow text on light · colours outside the palette · static element >2.5 s · anything below y≈1500 · promise hand animation · put the unconfirmed brand name on screen

## 9. Feedback rules log (append-only — the user's taste, learned round by round)
| Date | Version | User said | Rule we keep from now on |
|---|---|---|---|
| YYYY-MM-DD | v1 | "<quote/paraphrase>" | <general rule, e.g. "every caption word ≥ 4.5:1 contrast on its real background"> |

## 10. Decision history (what changed and why)
- YYYY-MM-DD · v2 · <old value> → <new value> · because <reason>

## 11. Continue-in-a-new-chat checklist (for the next AI)
1. Read this file fully, then PROGRESS.md (next step) and the tail of LOG.md.
2. Open plan/design.html (screenshot it) + the latest approved render / contact sheets (renders/previews/) to SEE the style before writing code.
3. Reuse the modules/assets in §7 — don't rebuild the look from scratch, don't change fonts/palette/SFX set.
4. Any new scene must pass: palette only from §3 · fonts only from §3 · motion devices from §4 · sounds from §5 · all §9 rules.
5. If something new is needed that this file doesn't cover, propose it to the user in the same style, then add it here once approved.
