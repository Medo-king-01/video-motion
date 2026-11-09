# Changelog — Video Motion

## 2026-11-09 — Looks مقفولة + وصفات المشاهد + سكيما beats.json
The «Move the intelligence into the system» slice, completed after the network went green.
Weak/cheap models now state a `look` (or a `recipe`) instead of improvising art direction —
two locked, machine-checked layers on top of `medo-motion/looks/shortlist.json`:

- **`medo-motion/looks/looks.json`** — six locked named Looks (`house` default, `tech-dark`,
  `explain-paper`, `kinetic-hook`, `swiss-data`, `warm-story`). Each bundles: a style reference
  (`styles.json` id or `medo-motion/styles/*.md`), a font pair **from the curated shortlist**
  (display/body Arabic + Latin ± mono), 3–8 signature technique ids, catalog transitions, a
  catalogued background and one music preset (all six presets used, one look each). **A Look
  carries no palette and no colors** — brand v2.6 Muted stays the only color authority
  (`tests/test_looks.py` walks every look and fails on any palette/color/hex key — the brand
  lock is now mechanical). Style references are creative direction only; `README.md` rewritten
  to document the two-layer system (shortlist → looks).
- **`medo-motion/recipes/recipes.json`** — eight named scene recipes (`tech-demo-ui`,
  `machine-explainer`, `kinetic-hook`, `list-steps`, `counter-proof`, `one-take`, `slide-wall`,
  `presenter-overlay`): preferred engine (+ proven fallbacks), `plan/` files required, the
  validators that gate the scene, recommended looks and signature techniques, playable arc,
  `ui` flag mirroring beats.json. `tests/test_recipes.py` resolves every id, every validator
  path and every doc — a recipe cannot rot silently.
- **`medo-motion/schema/beats.schema.json`** — the first official schema (JSON Schema draft
  2020-12) for the studio's oldest plan file, with `medo-motion/schema/README.md`. Documented
  contract for editors/external tooling; enforced in-repo by **`tools/beats_check.py`**
  (stdlib-only — no jsonschema dependency), which adds the cross-field invariants a schema
  cannot express: bounds↔scenes↔duration agreement, `frames == round(duration × fps)` at both
  levels, index sequence 1..N, contiguity, event containment, duplicate-id detection. Codes
  `B01`–`B07`. **The reel still has no target length** — anything other than the two legal
  states (`duration: null` draft / measured) fails. `tests/test_beats_schema.py` holds schema
  ↔ checker in lockstep and covers the fixtures, the VO round-trip (writer output must pass),
  and a 23-case negative matrix. The `bad` craft fixture passes the schema by design — craft
  failures stay with `reel_lint.py`.
- **`tools/vo_length.py`**: a missing `ffprobe` binary now falls back to the wave-module
  measurement instead of crashing (mirrors the non-zero-exit fallback; `ffmpeg` paths unchanged).
- Fast CI now also runs `tests/test_beats_schema.py`, `tests/test_looks.py`, `tests/test_recipes.py`.

## 2026-11-09 — full green network + technique-library contracts + import-order isolation
Follows the merged fonts P0 (`7ab90c9`, PR #42). The 19 pre-existing suite failures are gone —
fourteen were environment (missing `tools/bin/ffmpeg`+`ffprobe` shim and `tools/toolkit` node
modules — both produced by `bash tools/setup.sh`, now present), and the rest were real bugs or
stale tests that this change fixes:

- **`tools/sfx_kit.py`**: `audio_duration()` discovered ffprobe with its own `shutil.which`
  instead of `tools/lib/media_bin.py` — broke in any shell without `tools/bin` on PATH. Now uses
  the shared precedence (env override → `tools/bin/ffprobe` shim → PATH), like every other tool.
- **`medo-motion/templates/procedural-reels/run_all.py`**: same unification for its ffmpeg/ffprobe
  discovery (was inline `shutil.which` chains).
- **`tests/test_techniques.py` — the library's three authoring contracts** (the 59-studio-move
  assertions could never pass on the 2,239-entry merged library): studio-authored entries must
  still name a real studio API; the 616 opus + 1,375 Alansari rewritten imports must carry a
  measured build step (> 60 chars) plus summary/timing/use_when (`evidence` is a 0–9 score and is
  never falsy-tested); the 189 gl-transitions must reference a shader that really ships in
  `assets/gl-transitions/` with a `uniforms` list. 19/19 pass.
- **`docs/techniques.md` regenerated** from the library via `tools/techniques.py --markdown`
  (27,439 lines; `--check` = OK).
- **`tests/test_workflow.py::test_one_engine_p_frame_has_brand_size`**: no longer depends on
  suite import order — puts `ENGINE_P` ahead of `tools/` and drops a stale CLI binding before
  importing the scene (the rule every tool applies deliberately; `conftest.py`'s targeted
  `audio_mix` claim and `test_import_precedence.py` are untouched).
- **`AGENTS.md`**: "K-only Three bridge" → "Optional Three bridge for K and R (`ThreeCanvas`,
  phase 9)" — matches `docs/motion-three.md` and the Remotion template.
- **`docs/scene-director-skill.md`**: drift findings #2 (technique tests), #3 (Three bridge
  wording), #4 (workflow-test isolation) marked resolved.
- **CI**: Fast CI now also runs `tests/test_techniques.py` and `tests/test_file_safety.py`
  (stdlib-only, < 2 s each).
- Also verified the whole suite end-to-end: **1279 passed, 20 skipped** (Python 3.11, Node 22),
  including the previously order-dependent and environment-dependent replays.

## 2026-11-09 — type system: 125 families, licence correction, curated shortlist (P0 `p0_fonts`)
- **Manifest is now the truth:** `assets/fonts/fonts.json` — 125 families (61 Arabic + 64 Latin),
  each with `status` (`ok` / `review`) + a `status_note` for the review set.
- **Licence correction (was mislabelled):** Permanent Marker is **Apache-2.0** (Font Diner, 2010), not
  OFL — now ships `assets/fonts/Permanent Marker/LICENSE.txt`. **Ubuntu** is **UFL-1.0** (Canonical,
  2011) — now ships `assets/fonts/Ubuntu/UFL.txt` (from google/fonts). Manifest, tests and docs declare
  the real licences; `test_every_family_carries_its_licence` checks per declared licence.
- **15 Arabic families measured ≥ 0.20** outline/advance collision on «النهاردة» @ 54px (HarfBuzz +
  FreeType, 2026-11-09): Jomhuria, Aref Ruqaa, Noto Nastaliq Urdu, Aref Ruqaa Ink, Gulzar, Noto Sans
  Arabic, Estedad, Reem Kufi, Reem Kufi Fun, Mirza, Reem Kufi Ink, Noto Naskh Arabic, Noto Kufi Arabic,
  Katibeh, Fustat. They stay in the manifest (`status: "review"`) and are documented in `docs/fonts.md` —
  they are deliberately absent from the shortlist, never used for body text. No families were deleted.
- **New curated shortlist for weak models:** `medo-motion/looks/shortlist.json` (8 Arabic + 5 Latin,
  every pick `status: "ok"` and pairing recorded) + `medo-motion/looks/README.md` — first layer of the
  proposed "locked Looks" system. Enforced by `test_looks_shortlist_is_manifest_backed`.
- **Tests:** `tests/test_fonts.py` rewritten to pin the 125 count, the full manifest/files/licence
  agreement (size budget raised 12 MB → 120 MB, documented), status coverage of every family and the
  exact review set; both-direction honesty (a review family that now passes must flip back to `ok`).
  **194/194 pass.** `docs/scene-director-skill.md` drift finding marked resolved.
- **Docs:** `docs/fonts.md` (full 125-family index + quarantine table + shortlist section + lock-file
  gap note), `assets/CREDITS.md` (all 125 credited with real licences), AGENTS.md, README.md,
  DESIGN_SYSTEM.md, docs/README.md, docs/text-animations.md, docs/video-ad-editor-fit.md,
  medo-motion/{SKILL.md, reference/*, templates/TASTE.md, brand/*}, tools/{README.md, new_project.py},
  brand.json type_system — all counts updated with licence nuance.
- **Known gap (not fixed here):** `tools/font-packages.lock.json` pins only the original 21 npm
  `@expo-google-fonts/*` packages; the 104 Alansari additions are unpinned (documented in docs/fonts.md).

## 2026-11-02 — documentation correction
- Replaced obsolete project-origin and licensing statements that had accumulated during iterative AI-assisted editing.
- Aligned the root guide, toolkit guides, setup instructions and renderer playbook with the current Video Motion repository.
- Preserved third-party licence files and attribution records; clarified that project materials and third-party components have separate rights.

## 2.7 — 2026-11-05 — procedural music engine + audio mix
- **New**: `audio_engine.py` — one shared DSP core (rate-explicit filters, PolyBLEP saw, cached IR
  reverb, ADSR, absolute-gate ducking with lookahead, limiter, true-peak meter, WAV I/O).
- **New**: `music.py` + `motion/music-presets.json` — 8 independently mixable layers, 6 presets that
  differ in key/scale/groove (tech, minimal, corporate, energetic, cinematic, ambient), a
  section model (intro/build/drop/break/outro/stop) snapped to whole bars, sidechain pump, snare roll,
  crash, a phone-speaker "top" layer, and exact requested length at 44.1k or 48k.
- **New**: `audio_mix.py` — ONE cue sheet for music + SFX + voice (sample-locked resolution, music
  changes, two-stage ducking, stems, report, ffmpeg loudnorm); `tools/music_kit.py` and
  `tools/audio_mix.py` CLIs.
- **Fixed in `sfx.py`** (all backward compatible, `tests/test_sfx.py` unchanged): sample rate is a
  parameter instead of a module constant, event anchors, `bus.last_truncated` instead of silent
  truncation, `duck()` keeps the bus length and uses an absolute dBFS gate (a quiet line now ducks),
  layered cues, overwrite guards on every writer. 5 sounds added for real gaps (snap, page, coin,
  heartbeat, vinyl) — the 15 originals are untouched.
- **Fixed** `ffprobe_shim.py`: stream `duration` was divided by a hard-coded 1e6 instead of the
  stream time base, reporting 0.384 s for an 8 s WAV.
- **Fixed** `audio_engine.true_peak()`: collapsed channels with `max(axis=1)` (0 for symmetric stereo)
  and over-read +1.1 dB on signals ending loud; now magnitude-collapsed and edge-reflected.
- Docs: `docs/music.md` (architecture, presets, controls, CLI, integration, outputs, troubleshooting,
  one full example), `docs/audio.md` updated, attribution in `assets/CREDITS.md`, audit in
  `docs/audio-engine-audit.md`. Tests: `test_audio_engine` (13), `test_music` (20), `test_sfx_engine`
  (17), `test_audio_mix` (15).

## 2.6 — 2026-11-02 — Palette v2.6 Muted
- Locked palette v2.6 (given by Medo): the brown inks of v2 are replaced by deep black
  `ink #0A0A0A` and sharp neutral gray `ink_soft #71717A`; derived `ink_shadow` locks at `#030303`.
  Red (`#CB271B`/`#CB0801`/`#9F0803`), paper and the four grays, salmon and blush are unchanged.
- All engines, tools, icons and style recipes updated to the new values; contrast notes recomputed
  (e.g. paper on ink 17.71:1, red on ink 3.63:1 — still never red text on dark, use salmon).

## 2.4 — 2026-11-01 — Remotion engine R
- Added an optional React/TypeScript Remotion renderer as engine R, scaffolded with `--engine r`.
- The Composition reads the shared VO-derived `plan/beats.json`, loads local Cairo/Inter and Medo pose assets, and keeps frame evaluation deterministic.
- Added Studio, still-preview, typecheck and render commands; final rendering validates the measured WAV/timeline and reuses the installed Chromium from `tools/setup.sh`.
- R shares the exact tested easing/timeline module with K. Animated icon and transition/SFX catalogs remain P/K-only until explicitly ported and tested.
- Remotion packages are pinned with a lockfile; a Zod override addresses the current high-severity npm advisory (see `docs/remotion.md` for the upstream version warning and license caveat).
- `npm run stills -- 3 7.5` can now render review frames at exact requested seconds.
- Expanded local reference analysis with timestamped visual samples, motion strips, approximate palette/pace/audio metrics and `report.md`; each project gets `assets/refs/` and a brand-safe `STYLE.md` recipe. This adapts the workflow idea from [motalim-ai/motion-starter-kit](https://github.com/motalim-ai/motion-starter-kit) without importing its styles, assets or renderer.

## 2.3 — 2026-11-01 — the screen families: UI, product demo, numbers, micro-interaction
- **Library grew 41 → 58 moves** across 13 families. The four new families cover scenes that show a
  screen: `ui_choreography` (state change on the tap frame, row insert that makes room, checklist on
  the grid, sheet over a dimmed screen, focus ring that snaps), `product_demo` (phone in Medo's hand
  inheriting the pose's bob, cursor-led demo, window that builds itself, before/after cut not faded),
  `data_and_numbers` (counter rolling onto the beat, bar then label, one number full bleed, unit
  arriving after the digits) and `micro_interaction` (press depth without overshoot, toggle knob,
  self-drawing check, caret that only blinks when idle).
- **Built, never captured**: every recipe names the studio's own art layer — `kit.phone`,
  `appWindow`, `card`, `checklist`, `rolling`, `typeLines` (K) and `art.laptop`, `desktop`,
  `follow_button`, `paper_spec`, `cursor`, `lib.text_sprite` (P). `tests/test_techniques.py` fails a
  UI recipe that does not, and a new test proves a 40 s draw reaches the UI families.
- **Reel order extended** with the four families (after `layout`, before `pacing`) so an insert is
  drawn where a film actually cuts to a screen, and the plan can now hold 17 moves.
- **`U01` lint rule** — a scene flagged `"ui": true` must declare its interaction (`events[]`) and
  run at least 1.2 s; a screen that never changes is a mock, not a scene.
- **`docs/craft.md` §3b** — what we build and what we refuse to fake: no screenshots, no UI kits,
  no fake metrics, one accent with one meaning, dim and scale instead of glass/glow, and the
  presenter stays the anchor.

## 2.2 — 2026-11-01 — craft gates: a measured technique library and a pre-render lint
- **`assets/techniques.json` — 41 moves**, adapted from **cinetic** (MIT, © 2026 Leonxlnx) and
  rewritten against this studio's primitives (`beat`, `space3d`, `blur_steps`/`drawBlurred`,
  `presenter`, `transition`, `sfx`). Nine categories in the reel's order of need: hook, typography,
  transition, camera, pacing, layout, depth, finish, sound. Every entry carries `how` (a build step,
  not a mood), `timing`, `use_when`, `avoid_when`, `evidence`. No React, no Remotion, no GSAP:
  `tests/test_techniques.py` fails if a recipe drifts back.
- **`tools/techniques.py`** — a reproducible draw (`--draw --from-plan plan/beats.json`,
  `--energy`, `--seed`, `--category`, `--exclude`, `--json plan/techniques.json`), plus `--list`,
  `--show`, `--validate` and `--markdown docs/techniques.md --check`. Weighted by role × evidence ×
  energy fit, filled in the format's order, with a signature budget; a calm reel never draws a slam.
  Seconds come from the VO (`vo_length.py`), never from a target length. `make techniques`.
- **`tools/reel_lint.py`** — the pre-render gate, 21 rules in four groups: structure (`S01–S05`:
  bounds, short scenes, long scenes with no picture event, grid drift), copy (`C00–C11`: words per
  fragment, visible at once, dwell per word, copy rate, coverage, text-free stretch, banned words,
  sentence dumps, scene links, grid arrivals), moves (`M00–M02`: variety, signature budget) and an
  opt-in code scan (`K01`: sparkle/confetti/particle/lens flare/RGB split/crossfade/shake, with
  `# lint: allow`). `--strict`, `--json`. `make lint`.
- **`docs/craft.md`** — the measured numbers (shot length, dwell, copy rate, blur trigger, grid
  lock) plus **the conflicts and who wins** (serif/italic ban vs the Arabic brand type, 1.1 s holds
  vs the 0.5 s house ban, 60 fps vs our 30 fps delivery, the format length table vs "the VO decides").
- **`docs/techniques.md`** — generated from the JSON, freshness-checked in CI.
- `tools/new_project.py` now scaffolds `plan/copy.json`; CI validates the library, checks the docs
  are regenerated, and asserts the good fixture passes while the bad one fails. `pytest` 206 passed.

## 2.1 — 2026-11-01 — the free type system (14 families, SIL OFL 1.1)
- **14 families in `assets/fonts/`** — Arabic: Cairo (brand default), Tajawal, Alexandria, Kufam,
  El Messiri, IBM Plex Sans Arabic, Almarai, Amiri. Latin: Inter (default), Space Grotesk,
  IBM Plex Sans, IBM Plex Mono, Anton, Instrument Serif. 5.4 MB of TTF, every family with its
  `OFL.txt`; free for commercial use, no on-screen attribution.
- **`tools/fonts_install.py`** — pulls the TTFs from `@expo-google-fonts/*` on npm (the same binaries
  Google serves) and writes `assets/fonts/fonts.json`: role, pairing, weights, licence, source.
  `--only`, `--force`, `--list`. `make fonts`.
- **`tools/fonts_preview.py`** / `make fonts-sheet` — a specimen sheet (cache/fonts-sheet.png) with all
  families and 7 Arabic×Latin pairings, rendered through `arabic_shape` so it matches engine P exactly.
- **Both engines read the manifest**: `lib.font(size, family, weight)` (P) and `lib/fonts.js`
  (`useFont`/`family`, lazy FontFace registration) (K). `tools/new_project.py` ships the whole set.
  Fix: engine P's default font was `Cairo_400Regular` (glob order) — it is now Cairo **800**, the
  brand weight, as `brand.json` always said.
- **Rejected with evidence**: Reem Kufi (npm statics have advances narrower than their outlines →
  words collide under HarfBuzz: 0.27 overlap vs ≤0.14 for every shipped family). `tests/test_fonts.py`
  now fails any family above 0.20, so this cannot come back.
- `docs/fonts.md` (roles, pairings, usage, how to add), `assets/CREDITS.md` licences, `brand.json`
  `typography.type_system`, AGENTS rule 2, TASTE type line. `pytest` 181 passed.

## 2.0 — 2026-11-01 — rhythm, space and velocity blur (from the programmatic-motion doctrine)
- **`beat.py` / `lib/beat.js`** — a tempo grid both engines compute identically: `grid`, `quantize`
  (nearest/floor/ceil), `offset_of`, `ping`, `swell`, `ladder`, `on_grid`, `snap_bounds`,
  `bar_seconds`. Pure functions, so a frame still renders the same at any fps.
- **`space3d.py` / `lib/space3d.js`** — meshes (`box`, `prism`), an orbiting pinhole `camera`, `project`,
  `sorted_faces` (painter's algorithm), flat `shade` with hex or RGB, `draw_mesh`/`drawMesh` with
  back-face culling. A scene can now *turn* into the next composition instead of cutting to it.
- **Velocity blur** — `motion.velocity()` + `motion.blur_steps()` (P) and `velocity()`/`blurSteps()`/
  `drawBlurred()` (K): displacement = v · shutter, clamped, weights summing to 1, one sharp step at
  zero velocity.
- **`sfx.grid_cues()`** and `tools/sfx_kit.py --grid` (+ `make grid`): a cue sheet generated one
  character per sixteenth, tiled to a 16-step bar, so hits cannot drift off the beat.
- **`vo_length.py --bpm/--snap-div/--snap-tol`**: cut points snap to the tempo grid while the VO's
  start and end stay exactly where the voice is.
- **`scenes/kinetic-example.js`** (31.4–35.4 s of the demo reel): a real usage of all three — a 3D plate
  turning with the beat, Arabic type sliding on a quarter-note cycle and blurred by its own velocity,
  live `beat/phase/velocity` readouts. QA'd as a 16-frame contact sheet.
- Docs: new `docs/rhythm.md` (what was adopted, what was refused and why), AGENTS rule 10, README,
  `docs/README.md` index. Tests: `tests/test_rhythm.py` (9) + `tests/test_space3d.py` (10) + a snapping
  case in `tests/test_vo_length.py` — `pytest` 153 passed, ruff clean, `make ci` PASS, selftest OK.

## 1.9 — 2026-11-01 — length comes from the VO (no target length anywhere)
- **Rule, stated and enforced**: the reel is exactly as long as the voice-over. There is no target
  duration, no "45–60 s typical", no padding/trimming to hit a number.
- New `tools/vo_length.py` (+ `make length VO=…`): measures the VO with `ffprobe`, cuts scene bounds
  at the midpoint of each silence (`--min-gap`), merges scenes shorter than `--min-scene`, writes
  `plan/beats.json`, and gates a project with `--check` (fails on any mismatch with the VO length).
- `mix.py` (engine P) now reads `TOTAL` from the VO and warns when `scenes.B` disagrees, instead of
  trusting `B[-1]`; `run_all.py` takes the frame count from `out/vo24.wav` the same way; engine K's
  `render.js` warns when `--audio` isn't the length of the render window. The SFX bus in
  `tools/sfx_kit.py` defaults to the VO length instead of "last cue + 2 s".
- `docs/length.md` documents the A/V mux with `-shortest` (the mix keeps a 0.3 s decay tail, so the
  master is trimmed to the video, i.e. the VO).
- Docs corrected: `brand.json` export duration, `TASTE.md` intake, `styles/editorial-explainer.md`,
  `reference/explainer-reel-system.md` (seconds are a worked example, scaled to the real VO),
  `docs/audio.md`, `docs/motion.md`; new `docs/length.md`; AGENTS §5 step 2 now says *measure, don't guess*.
- Tests: `tests/test_vo_length.py` — duration/bounds from a synthetic VO, the `--check` gate, the
  bus length defaulting to the VO, and a scan that fails if any doc or template reintroduces a fixed
  length. `pytest` 133 passed.

## 1.8 — 2026-11-01 — pose library batch 2 (24 poses, two framings)
- **Ten new poses**: `waiting` (hands in pockets), `warm` (hand on chest), `phone`, `unfold`
  (script/paper), `point-up`, `seated-talk` — all normalised like the first batch (1200 px figure,
  soles on 1390).
- **Four close-ups** (`close-neutral`, `close-explain`, `close-point`, `close-thinking`) with a new
  *framing* concept: `bust` cut-outs are normalised to 1180 px and anchored on the **top guide (190)**
  instead of the ground line. Cutting from a full shot to a close-up therefore reads as a camera
  push-in (same hair line, same face position) instead of a jump.
- `poses.json` now carries `framing` and `place` per pose; `presenter.py` / `lib/presenter.js` honour
  `place` (`feet` vs `top`) with `ground=1390` and `top=190` overridable.
- **Bug fixed (engine K)**: `PoseTrack` resolved cue names in its constructor, i.e. before
  `loadPoses()` had fetched `poses.json`, so any pose outside the embedded fallback silently
  degraded to `neutral` — a close-up cue rendered as a plain wide shot. Resolution is now deferred
  to `at()` in **both** engines, and the embedded JS fallback carries all 24 poses with `place`.
- Tests: framing/anchor invariants, close-ups start at the guide and never touch the caption zone,
  full shots land on the ground line, and a regression test for deferred cue resolution in K.
- `presenter-example` now ends on a push-in to `close-explain` (28.2–31.4 s) as the live demo.
- Verified: `ruff` clean, `pytest` 127 passed, engine-K render of the push-in inspected, sheet
  rebuilt for 24 poses.

## 1.7 — 2026-11-01 — Medo's pose library (14 cut-outs, both engines)
- **`assets/poses/`**: 14 presenter poses delivered as light-background JPEGs, rebuilt into trimmed
  transparent PNGs (figure height normalised to 1200 px, feet on one baseline) + `poses.json`
  (Arabic/English label, tags, facing, per-pose scale, feet anchor). Originals kept in `raw/`.
- **`tools/presenter_build.py`**: background removal tuned for studio art — pure-white background and
  grey contact shadow out, enclosed *shaded* whites (the t-shirt) filled, enclosed *pure-white* gaps
  (between stool legs / limbs) punched out, JPEG rim de-haloed, then normalised. `make poses` also
  renders a contact sheet on the brand background.
- **Both engines got the presenter module**: `templates/procedural-reels/presenter.py` and
  `templates/render/lib/presenter.js` — `draw`/`drawPresenter`, `PoseTrack` (shaped cross-fade,
  0.12 s), idle life (breathe 0.8 %, bob, sway, per-pose lean/pulse) with identical numbers, and the
  ground-line anchor. Old `medo_*` sprite names resolve to the new poses, so existing scenes picked up
  the real art instead of the placeholder silhouette.
- **`scenes/presenter-example.js`** (28.2–31.4 s): greet → explain → point over the brand circle.
- `new_project.py` copies `assets/poses/` + the manifest into every new project.
- Docs: `docs/presenter.md`; README/AGENTS/docs index/tools README/Makefile/CREDITS updated.
- Verified: 14 poses inspected on the dark background, `ruff` clean, `pytest` 123 passed, JS↔Python
  pose-transform parity asserted.

## 1.6 — 2026-11-01 — transitions + a procedural sound kit
- **Transition catalogue** (`motion/transitions.json`, 14 entries): wipe, wipeUp, diagonal, iris,
  irisClose, slide, cover, blinds, checker, bands, dissolve, zoom, glitch, flash. Every entry declares
  its `kind`, easing and the sound it pairs with. Names/kinds are inspired by the MIT gl-transitions
  collection; the maths is vector/CPU so nothing depends on a GPU or on real time.
- **One geometry, two engines**: `templates/render/lib/transition.js` (`transitionLayer`,
  `makeLayer`, `compositeTransition`) and `templates/procedural-reels/transition.py` (`layer`,
  `composite`). Masks are normalised, so the same numbers paint the same picture;
  `tests/test_transitions.py` compares JS↔Python sample by sample and checks endpoint/invert behaviour.
- **Sound kit** (`templates/procedural-reels/sfx.py`): 15 synthesised, deterministic sounds with a
  `CATALOG` (family + base gain), a cue-sheet `bus()`, `duck()` for voice-over, `cues_for_transitions()`
  (cuts → hits via the transition catalogue) and `render_bank()` for editor imports.
- **Tools**: `tools/sfx_kit.py` (`--list`, `--bank`, `--demo`, `--cues … --vo … --out …`) and
  `tools/transitions_sheet.py` (contact sheet + preview clip with the matched sounds). `make sfx`,
  `make sfx-bank`, `make transitions`.
- **Equation easings**: `motion/easings.json` gained the Penner `formulas` family (elastic, bounce,
  quad/cubic/quart/quint, sine, expo, smoothstep) — names that don't collide with the bezier
  vocabulary, identical in both engines.
- **Engine K demo**: `scenes/transition-example.js` (25–28.2 s) cuts between two scenes through the
  catalogue; the reel template's duration is now 28.2 s.
- Docs: `docs/transitions.md`, `docs/audio.md`, motion doc updated; README/AGENTS/docs index/tools
  README/Makefile wired.
- Verified: `ruff` clean · `pytest` 113 passed · `make ci` OK · `selftest` PASS · sheet + clip inspected.

## 1.5 — 2026-11-01 — motion grammar (motion.dev + Theatre.js, without their runtimes)
- **`medo-motion/motion/easings.json`**: 12 named cubic-beziers with motion.dev's control points
  (easeIn/Out/InOut, circ…, back…, anticipate) + 5 spring presets + the brand's locked timings.
- **Deterministic motion module in both engines**: `templates/render/lib/motion.js` and
  `templates/procedural-reels/motion.py` — `ease`, closed-form `spring` (stiffness/damping/mass,
  overshoot included), `springDuration`, `keyframes`, `timeline().at(t)`, `stagger`, `reveal`.
  Same numbers in JS and Python (asserted numerically by the tests).
- **Timeline JSON format** (+ `motion/examples/card-entrance.json`): keyframe tracks with per-segment
  easing, colour interpolation, clamping outside the range.
- **Theatre.js bridge**: `tools/theatre_import.py` converts a Studio state export into our timeline
  (bezier handles → cubic-bezier, `--offset`, `--sheet`, `--list`).
- **Offline motion studio**: `tools/motion_studio.html` (JSON editor, scrub, play, live values,
  download) — imports the engine's module, so what you preview is exactly what renders. `make studio`.
- **Engine K demo**: `scenes/motion-example.js` (22–25 s) driven entirely by a timeline; visible in
  `make selftest` renders and the palette audit stays clean.
- Docs: `docs/motion.md` (what we took, what we deliberately skipped, recipes, limits),
  `motion/README.md`, README/AGENTS/docs index/tools README updated.
- Verified: `ruff check .` clean · `pytest` 87 passed · `make ci` OK · `selftest` all PASS.

## 1.4 — 2026-11-01 — the whole itshover library, inside both engines
- **Vendored itshover** (Apache-2.0, `itshover/itshover` on GitHub) into `icons/itshover/tsx/`
  with its LICENSE and upstream registry — 263 components, the complete set behind
  https://itshover.com/icons. The site itself is blocked from the sandbox, GitHub is not.
- **Importer** `tools/itshover_import.py`: reads each component's `<svg>` (path / rect / circle /
  ellipse / line / polyline / polygon, `fill`, `transform`, plus the JSX-array cases) and emits
  `icons/itshover/registry.json`. `--list` searches it, `--promote <id>` moves one icon into the
  house registry for Arabic labelling and hand edits.
- **Full SVG path support in the builder**: an SVG path parser/flattener (M L H V C S Q T A Z, arcs
  via endpoint→centre, packed arc flags) so curves, rounded rects and ellipses look identical in
  SVG, Canvas (native `Path2D`) and Pillow (flattened polylines). Filled shapes supported.
- **275 icons total** (12 house + 263 itshover, 41 of them third-party brand marks flagged
  `group: "brand"`), all palette-locked at draw time, all in `lib/icons.js`, `icons.py` and `svg/`.
- Fixed the engine-K painter origin (icons were drawn from the centre instead of centred) and
  scoped per-part transforms with save/restore.
- Docs: `docs/icons.md` rewritten (what is identical, what is intentionally different, commands),
  `assets/CREDITS.md` created with the Apache-2.0 attribution, README/AGENTS/CHANGELOG updated.
- Verified: `ruff check .` clean · `pytest` 76 passed · `icons --check` in sync.

## 1.3 — 2026-11-01 — palette v2 + animated icon layer
- **Palette v2 (from Medo):** the 12 supplied colours replace the old red/black/yellow/teal set;
  one derived shade `ink_shadow #2E2423` (ink −35%). `brand/brand.json`, `brand/BRAND.md`,
  `templates/TASTE.md`, `styles/medo-red-circle.md` rewritten; ~150 colour literals remapped in
  engine P (`lib.py`, `art.py`, `scenes.py`) and engine K (`lib/brand.js`, `lib/kit.js`, scenes).
  No yellow/green/blue left: positive emphasis is paper white + ✓.
- **Brand guard rewritten:** contrast pairs now measured on the real surfaces (paper-on-ink 9.83,
  red-on-paper 4.88, blush-on-ink 5.46) and forbidden pairs asserted low (red-on-ink 2.01).
  `brand_check.py --project medo-motion/templates` also fails on any off-palette literal in either
  engine — the check runs in `make ci` and in the tests.
- **Animated icon layer (`medo-motion/icons/`):** one `registry.json` (12 icons, Arabic labels,
  primitives on a 24×24 grid) generates animated SVGs, `templates/render/lib/icons.js` (canvas
  `drawIcon`) and `templates/procedural-reels/icons.py` (Pillow `draw_icon`). Colours are passed at
  draw time, so icons cannot leave the palette. `examples/PlugConnectedIcon.jsx` + `components.json`
  document the itshover/`shadcn add` path (itshover.com is unreachable from the sandbox).
- **QA tooling:** `tools/icons_sheet.py` (engine P sheet), `tools/icons_preview.mjs` (engine K sheet
  via Chromium), `make icons`, `icons --check` in CI, `tests/test_icons.py`.
- **Engine K demo:** `scenes/icons-example.js` (18.5–22 s) shows the six laptop-part icons animating.
- Verified: `ruff check .` clean · `pytest` 60 passed · `tools/selftest.py` all PASS · `make ci` OK.

## 1.2 — 2026-11-01 — clean-code pass
- **Tests:** `tests/` with 26 pytest cases — Arabic shaping invariants (joined forms,
  visual run order, number separators, ink-tight sprites, strokes keeping counters,
  determinism, anchor centring), the brand lock (tokens, no-logo rule, JS↔JSON sync,
  contrast), the scaffold, and one real 1080×1920 engine-P frame.
- **Self test:** `tools/selftest.py` (doctor → tests → engine P render → engine K render)
  and a `Makefile` (`make setup|doctor|test|selftest|new|brand|clean`).
- **Lint:** `pyproject.toml` with ruff (E4/E9/F/I/UP/B), documented per-file ignores for
  the vendored engines' compact style. `ruff check .` is clean.
- **Code cleanups:** removed dead imports/locals in `art.py`, `scenes.py`, `mix.py`,
  `brand_check.py`; `lib.py` gained `_shaper()` instead of duplicated backend guards;
  `arabic_shape.py` got named constants (`BIDI_MARKS`, `NUMBER_SEPARATORS`), typed run
  splitting, `__all__` and a context-managed font read; `doctor.py` de-duplicated.
- **Repo hygiene:** `docs/` (analysis + conventions), `tools/README.md`,
  `tools/requirements.txt`, `.editorconfig`, `.github/workflows/ci.yml`, and a
  `.gitignore` that covers render output, caches and secrets.
- Verified: `ruff check .` clean · `pytest` 26 passed · `tools/selftest.py` all PASS.

## 1.1 — 2026-11-01 — agent-agnostic studio + new contract
- **Works with any coding agent.** The operating contract moved to `AGENTS.md` at the
  repo root; `SKILL.md` now defers to it and no longer assumes Claude Code.
  Added `tools/setup.sh`, `tools/doctor.py`, `tools/new_project.py`.
- **Contract changed to four inputs:** script · scene direction · Medo's VO · Medo poses.
  Everything else (visuals, SFX, music, timing, assets) is produced by the agent.
- **Removed the logo and the series name everywhere.** No chip, no episode number, no
  reserved logo circle in `scenes.py`; `brand.json` (`logo: null`, `logo_rule`),
  `BRAND.md` §1/§6/§10, `TASTE.md`, `medo-playbook.md` §1/§7 updated. End cards are
  typographic only. The ElevenLabs onboarding flow was dropped: VO comes from Medo,
  TTS is opt-in only.
- **New Arabic shaping fallback** `templates/procedural-reels/arabic_shape.py`
  (HarfBuzz shaping + FreeType rasterising) for Pillow builds without libraqm.
  Verified: joins, RTL run ordering, mixed Latin/digits, 25,000 / 12:30, strokes
  composited behind the glyphs, ink-tight sprites so caption layout is unchanged.
- **Engine K rebranded:** `data.js` loads Cairo, `lib/kit.js` FONTS default to Cairo,
  `explainer-example.js` loads Cairo only; `#E8322B` → brand `#E5262B`.
- `lib/brand.js`: background gradients (`bgDarkTop/Bottom`, `bgLightTop/Bottom`),
  `chipY` removed. `brand_check.py --project` now also audits `lib/brand.js`
  (colours, gradients, font, safe zones) and finds `src/lib` copies.
- `preflight.py`: the `medo` block no longer collapses to an error when Pillow is
  missing; it reports `arabic_shaping: raqm | harfbuzz-fallback | NONE`.
- `render.js`: accepts `playwright-core` (works with the bundled Chromium).
- **Loudness hardened** (`mix.py`): loudnorm aims at TP −2.0 (it overshoots its own
  target by ~0.2–0.4 dB), a limiter acts as the hard ceiling, and a final deterministic
  trim lands inside −14.5 ±0.3 LUFS while never exceeding −1.5 dBTP. Measured on a test
  mix: was −1.3 dBTP → now −14.7 LUFS / −1.5 dBTP.
- Engines honour `FFMPEG_BIN` when ffmpeg is not on PATH.
- Verified here: engine P 8-frame chunk + contact sheet with correct Arabic captions and
  a 90-frame master (1080×1920, H.264+AAC, 4.5 Mbps, faststart); engine K 12 frames
  through Chromium 153; mix + two-pass loudnorm; `brand_check` PASS; `doctor.py` READY
  except the optional drawtext filter.

## 1.0 — 2026-11-01 — initial Video Motion baseline
- Established the Video Motion repository structure, project brand layer, shared references and reusable styles.
- Added the initial procedural renderer (P), Canvas/Playwright renderer (K), and their project templates.
- Added setup and environment checks, project scaffolding, Arabic typography safeguards and brand validation.
- Recorded the initial render workflow and known environment limitations as development history.
