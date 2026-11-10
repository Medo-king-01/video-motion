# medo-motion — Reel Studio (works with ANY coding agent)

> **Read this file first, every session.** It is the operating contract.
> The unified design reference is `DESIGN_SYSTEM.md` (repo root).
> Tool detail lives in `medo-motion/` (the toolkit: guides, scripts, templates).
> Human-facing Arabic docs: `README.md`, and `medo-motion/brand/BRAND.md` (locked identity).

This repo is not a Claude-only skill. It is a **reel factory**: any agent with file
and shell tools (Claude Code, Codex, Cursor, Gemini CLI, Copilot, Aider, …) can take
four inputs from Medo and deliver a finished vertical MP4.

---

## 1. The four inputs (and nothing else)

| # | Input | What it looks like |
|---|---|---|
| 1 | **Script** | The narration text, numbered beats, plus what should appear on screen |
| 2 | **Scene direction** | How Medo wants the scenes presented (order, feel, what each shot shows) |
| 3 | **VO audio** | Medo's recorded voiceover file (wav/mp3). This is the timing master |
| 4 | **Medo poses** | **already in the repo** — <!-- AUTO:poses -->49<!-- /AUTO --> poses in `assets/poses/` are copied into every project. Ask for an image **only when a scene needs a pose the library does not have** (§1a). |

Ask **once, in a single message**, for whatever is missing. Then decide the rest
yourself and say what you decided. Never run a multi-step interview.

### 1a. The pose library is the fourth input, not a request

Every project starts with the full library (<!-- AUTO:poses -->49<!-- /AUTO --> poses, `assets/poses/poses.json`): standing beats,
motion, seated, props and 19 half-body close-ups. **Read the catalogue before you storyboard** and
cast each beat from it — that is the default, and it needs no message to Medo.

Ask for a pose image **only when the script needs something the library genuinely lacks** — a prop,
an outfit or an action nobody in `poses.json` performs. Then:

1. say **which slug is missing and which beat needs it** (one line, inside the intake message — never
   a separate interview);
2. ask for the image the way the library was built: one character, full body or half body, clean flat
   background, no text, no collage;
3. when it arrives, run it through the same production line as the rest —
   `assets/poses/source/<id>.png` → a row in `tools/lib/pose_catalog.py` → `make poses` (see
   `docs/presenter.md`). Never hand-place a raw image into `assets/poses/`, and never register a
   pose in `poses.json` by hand.

Reusing a pose that is only *close* to the beat, or asking for four images "to be safe", are both
failures of this rule: the first makes the acting lie, the second is the interview we are avoiding.

If the VO is missing you may *offer* a placeholder timing track, but do not build a
finished video on guessed timing without saying so.

## 2. Hard rules — do not deviate

1. **No logo. No default name or title. No episode chip. No empty logo ring.**
   This is a studio, not a named series: the user tells you what to make and you make it.
   **Never ask for a series name, never invent one, never leave a placeholder circle or a
   descriptive chip "for the name/logo".** These are not inputs and the agent has no
   authority to decide them: if the user wants a name, a title or an episode number on
   screen, he says so and you execute it exactly, word for word (C07 then does not apply —
   `approvedByUser` in `plan/copy.json`); if he does not, nothing goes on screen.
   End cards are **typographic only**, built from the copy he approved.
2. **The brand is locked** (palette, safe zones, loudness, Egyptian dialect) — but **the font is
   your creative choice**. `medo-motion/brand/BRAND.md` + `brand/brand.json` are the source of truth:
   **exactly 12 colours** (palette v2) plus the derived `ink_shadow`. Never improvise outside the
   palette — `brand_check.py` fails the build if you do.
   **Type:** `assets/fonts/fonts.json` is the whole allowed set — <!-- AUTO:fonts -->125<!-- /AUTO --> families (<!-- AUTO:fonts_arabic -->61<!-- /AUTO --> Arabic + <!-- AUTO:fonts_latin -->64<!-- /AUTO --> Latin); <!-- AUTO:fonts_ofl -->123<!-- /AUTO --> SIL OFL 1.1 + Permanent Marker (Apache-2.0) + Ubuntu (UFL-1.0)
   (free, commercial, no on-screen attribution). **There is no forced default:** you pick the most
   attractive, reel-fitting face (Arabic or Latin) per scene/element and record it in
   `plan/text-direction.json` (`fontStyles`/`fontElements`, rule 11). Cairo/Inter are only a
   last-resort fallback for system chrome. Prefer an Arabic↔Latin pair with the same feel; at most
   two families per scene unless a reason is recorded. `docs/fonts.md`; `make fonts` installs,
   `make fonts-sheet` shows them.
3. **VO is Medo's.** Never generate TTS unless Medo explicitly asks for it. If he does,
   `medo-motion/scripts/gen_tts_elevenlabs.py` is there — and it asks for approval
   before any paid request.
4. **Egyptian Arabic** in replies and on screen; code, filenames and comments in English.
   Technical terms stay in English.
5. **Arabic typography rules are mandatory** before any Arabic appears on screen:
   `medo-motion/reference/arabic-typography.md`. Whole words only, RTL, real shaping.
   Never letter-by-letter, never `arabic_reshaper`.
6. **Never print, ask for, or store API keys** in chat or in files.
7. **Motion comes from the studio grammar**, not ad-hoc maths: easings/springs in
   `medo-motion/motion/easings.json`, keyframe timelines played by `lib/motion.js` (K/R) or
   `motion.py` (P). Remotion receives the same tested `lib/motion.js` source. The same timeline JSON must render identically in all three engines —
   `tests/test_motion.py` enforces the shared easing/math implementation. `docs/motion.md` maps motion.dev recipes onto it and
   `tools/theatre_import.py` converts a Theatre.js state export.
8. **Medo is a pose library, not a PNG per scene**: use `presenter.py` (P) / `lib/presenter.js` (K) / `MedoPresenter` (R)
   with the slugs from `assets/poses/poses.json` — <!-- AUTO:poses -->49<!-- /AUTO --> poses: `neutral`, `arms-crossed`, `smile-calm`,
   `open-hands`, `explain`, `point`, `point-viewer`, `point-up`, `welcome`, `wave`, `wave-goodbye`, `clap`,
   `clap-excited`, `celebrate`, `like`, `discovery`, `confused-choice`, `thinking`, `think-hands`, `sad`,
   `shocked`, `surprised`, `warning`, `walk`, `run`, `seated-talk`, `seated-reflect`, `laptop-work`,
   `phone`, `document` (full shots, anchored on the ground line) plus the half-body close-ups `angry`,
   `hide-face`, `laptop-hold`, `listen`, `shh`, `point-self`, `point-down`, `point-aside`, `relaxed`,
   `searching`, `shrug`, `head-scratch`, `coat-look`, `watch`, `phone-show`, `coffee`, `sigh`,
   `close-explain`, `close-thinking` (anchored on the top guide — a cut between the two framings is a
   camera push-in). Never edit the cut-out PNGs or `poses.json` by hand — edit
   `tools/lib/pose_catalog.py` and rebuild with `make poses`. `docs/presenter.md`.
9. **Backgrounds are catalogue-driven, and on-palette**: pick from `medo-motion/motion/backgrounds.json`
   (<!-- AUTO:backgrounds -->12<!-- /AUTO --> pure-function patterns × dark/light) with `backgrounds.py` (P) / `lib/backgrounds.js` (K+R) —
   never a hand-drawn gradient, never a colour outside `brand/brand.json`. Each background is a pure
   function of `t`, so it stays frame-exact in chunks and in parallel rendering. State the id and why
   in `plan/design.json`; review with `make backgrounds`. `docs/backgrounds.md`.
10. **Cuts and sound are catalogue-driven**: P/K transitions use `transition.py` / `lib/transition.js`
   (`medo-motion/motion/transitions.json`) and every hit comes from `sfx.py` (`BANK` + `CATALOG`) via a
   cue sheet — never a hand-rolled mask or an unlicensed audio file. R currently supports hard scene cuts;
   if the concept needs a catalog transition, choose P/K until that primitive is ported and tested. All
   engines use the shared SFX/mix pipeline. `docs/transitions.md` and `docs/audio.md` are the references;
   `make transitions` and `make sfx` produce the QA artefacts.
11. **Draw the moves; then lint them.** Do not choose transitions/camera moves from memory — that is
   how every reel ends up with the same fade-up and push-in. Draw from the measured library into the
   project: `python3 tools/techniques.py --draw --from-plan plan/beats.json --json plan/techniques.json`
   (`assets/techniques.json`, <!-- AUTO:techniques -->2,239<!-- /AUTO --> moves across <!-- AUTO:technique_categories -->44<!-- /AUTO --> families — including
   the <!-- AUTO:techniques_studio -->59<!-- /AUTO --> studio moves that sit in <!-- AUTO:focus_techniques -->13<!-- /AUTO --> families, the UI / product-demo /
   numbers / micro-interaction moves for screen scenes — each written against this studio's primitives). Build what
   the concept can carry, reroll at most twice, never add a move the draw did not give you.
   Before a render, the plan must pass `python3 tools/reel_lint.py projects/<slug> --scan-code`
   (letters/words on screen, dwell per word, grid-locked cuts, text-free stretch, banned looks).
   Rules, numbers and the conflicts we resolved: `docs/craft.md`. Library: `docs/techniques.md`.
12. **Text motion is your creative decision for EVERY on-screen text element — never a default.**
   This is not caption-only: titles, hooks, keywords, numbers/counters, CTAs, labels and text inside
   cards/UI all get an explicit motion style **and font** in `plan/text-direction.json`
   (`captionStyle`, `textStyles`/`fontStyles` per role, optional per-element `textElements`/
   `fontElements` overrides, and a short rationale). You also choose the most attractive,
   reel-fitting typeface (Arabic or Latin) from the manifest — there is no forced font default. List every
   visible fragment in `plan/copy.json` with a `role` (and an `id` when it needs its own motion).
   Initialise with `python3 tools/text_direction.py projects/<slug> --init`, then choose from the
   caption-safe catalog (`docs/text-animations.md`) to fit the mood/energy of each beat, and vary it
   across the reel (a repeated motif needs a `motifReason`). Draw text only through the directed
   helpers (`drawDirectedText` K, `draw_directed_text` P, `DirectedText` R); raw `fillText`/`text_sprite`
   is lint error T04. There is no fallback look: the render gates and lint fail closed if any text
   has no chosen style. Timing still comes from the measured VO/scene bounds; the style only shapes
   how the element moves. Keep it unboxed, whole-word Arabic, brand colors. A broad brief with a weak model may state a locked `look: <id>` (`medo-motion/looks/looks.json`) or a scene `recipe: <id>` (`medo-motion/recipes/recipes.json`) instead of improvising every choice; neither bypasses the lint.

13. **The studio is a tool, not a video archive.** The studio's memory is this toolkit —
    `assets/` inputs, `templates/`, `brand/`, `tools/`. `projects/` is not: it is a scratch
    working area for the video being made *right now*, ignored by Git, and every scaffold
    writes its own `.gitignore` with `*`. A delivered video leaves the repository with its
    folder: never keep finished projects, old renders, episode folders or old scripts in the
    repo as memory, never use a past video as the starting point of a new one, and never add
    a per-project CI workflow that renders a specific past video. Need to keep the work?
    `--out` a folder outside the repo (next to the user's own video files). Each new video
    starts from the four inputs and the toolkit, nothing else.

14. **Plan meaning, then verify geometry.** New projects include draft `plan/visual-direction.json`.
    After measuring VO beats/words, choose presenter/overlay/cover per beat, a concrete rationale,
    element/copy IDs and measured word anchors; mark ready with `decidedBy`. `reel_lint.py` enforces
    V01 when this plan exists. Never invent word times or reveal a fact before its spoken anchor.
    Native comparison/timeline/counter primitives share a deterministic K/R data model; require
    units, source and explicit label/number text direction, and human-check factual correctness.
    For K run `node tools/layout_audit.mjs --project ... --out <fresh-directory>` at every frame;
    inspect issue screenshots/report AND rendered frames. Add `--replay` to verify observed
    reverse-seek RGBA/layout reproducibility (R01/R02), not loop continuity or cross-browser parity.
    For a continuous app-window shell, K `drawSharedPanel` / R `SharedPanel` keeps one identity
    and defers details until `contentAt`; still gate facts with measured VO and explicit directed text.
    Source selection and limits: `docs/charlie-motion-review.md`. Register measured per-pose `faceBox`
    fractions; no guessed face bounds. Missing capture/resources is not PASS. This is conservative
    main-canvas text QA, not pixel/vision proof or an R/P audit. `docs/visual-data-qa.md`.

### Motion expansion scope

The user selected render capabilities, excluding a new interactive authoring UI. Track the staged
work in `medo-motion/motion/rollout.json` and `docs/motion-rollout.md`; partial/planned is NOT shipped.
Use native `motion-plan.js` (K/R) / `motion_plan.py` (P) for portable sequences, advanced stagger,
finite cycles and paths. Use `motion-state.js` / `motion_state.py` for tested analytic springs, finite inertia,
authored retarget/follow logs, hierarchical variants and JSON-derived values (not live callbacks). Do not install Motion/Motion Studio, authoring gestures or paid services
by default. For authored group snapshots, measured text and bounded shape bindings see `docs/motion-geometry.md`;
these do not cover arbitrary DOM/CSS/SVG or prove VO gates. For bounded SVG preprocessing see `docs/motion-svg.md`;
for opt-in reduced decorative motion and resource/profiling limits see `docs/motion-render.md`.
For bounded nested timelines and compatible multi-contour morph see `docs/motion-nested-morph.md`;
never treat polygon checks as a universal SVG/topology guarantee. GPU feasibility and licensing are documented in
`docs/motion-gpu-feasibility.md`; a local API pass is not proof of hardware or Three/vgpu compatibility. Optional Three bridge for K and R (`ThreeCanvas`, see
`docs/motion-three.md` phase 9) and
resource ownership: `docs/motion-three.md`; do not claim general P, hardware GPU or vgpu support. Keep VO word gates, palette, directed text and frame-replay verification intact.

## 3. What YOU produce

Medo gives you words, timing, voice and poses. Everything visual and audible is yours:

| Element | Source order |
|---|---|
| Backgrounds, cards, devices, charts, transitions, captions, HUD | **Code** first (this is the default and the cheapest) |
| Animated icons | **`medo-motion/icons/`** — 275 icons (house set + the full itshover library, Apache-2.0) already wired into both engines (`drawIcon` / `draw_icon`, see `docs/icons.md`); never drop in a random icon pack, and never use a `group: "brand"` icon as identity |
| Hero objects the code can't draw well | **AI image generation**, one session per video, deck-locked prompt in `medo-playbook.md` §4 |
| Real footage / textures / photos | **Search** CC0/PD/OFL only, download into `projects/<slug>/assets/`, log in `CREDITS.md` |
| Sound effects | **Procedural** (`sfx.py`) first → Openverse CC0 → ElevenLabs SFX only with approval |
| Music bed | Generated Am–F–C–G, 76 BPM, ducked under VO (see brand §8) |
| Captions, word timings, scene boundaries | Derived from Medo's VO (`silencedetect` + script) |
| User-provided reference video | **Reference-only**: analyze locally, write `STYLE.md`, do not reuse its content/assets without rights |

## 4. First run on a machine

```bash
bash tools/setup.sh --dev    # Python >=3.10 + Node >=20.11 must already be installed; use a venv
                            # installs Python runtime/test deps, Node deps, ffmpeg shim, fonts, Chromium
python3 tools/doctor.py      # prints READY / BLOCKED for every capability (--json for machine envelope)
python3 tools/selftest.py    # doctor + unit tests + a few real frames (the real proof)
```

For a clean-machine walkthrough and dependency policy, see `docs/development.md`.

`make setup`, `make doctor`, `make selftest`, `make test`, `make new SLUG=…` are the
same commands in short form.

Then start a project:

```bash
python3 tools/new_project.py laptop-series-ep1
```

`doctor.py` is the only readiness check you need; `preflight.py` inside the toolkit
is the portable inventory it extends. Do not install anything else "just in case".

## 5. Workflow (the default path)

1. **Intake** — fill `projects/<slug>/BRIEF.md` from the four inputs; copy the VO into
   `assets/vo/`, the script into `plan/script.md`. `new_project.py` already copied the whole pose
   library (49 PNGs + `poses.json`) into the project, so pose work starts from the catalogue, not
   from a request. Then prepare the two files the engines expect:

   ```bash
   # VO master: 24 kHz mono PCM16 (mix.py reads out/vo24.wav)
   ffmpeg -y -i assets/vo/<voice>.mp3 -ac 1 -ar 24000 -c:a pcm_s16le out/vo24.wav
   ffprobe -v error -show_entries format=duration -of json out/vo24.wav   # duration = video duration

   # Poses: nothing to prepare — the project already has all 49. Read the catalogue, then cast:
   python3 -c "import sys; sys.path.insert(0,'tools/lib'); import pose_catalog as c; \
     [print(p[0], '·', p[1], '·', p[2], '·', ', '.join(p[3])) for p in c.POSES]"
   # Only when a beat needs a pose the library lacks (AGENTS.md §1a), add it through the line:
   #   assets/poses/source/<id>.png → a row in tools/lib/pose_catalog.py → make poses
   ```

   Engine P draws a silhouette marked `PLACEHOLDER` only if a project arrives without the library;
   declare that in the delivery.

   **Optional reference (only when the user supplies or requests one):** keep it in
   `assets/refs/` and inspect it before locking the visual direction. From the project root,
   run `python3 ../../medo-motion/scripts/analyze_ref.py assets/refs/<file> --dur 15 --frames 3 --out cache/reference-analysis`
   (repeat with a different `--start` for another short window). Review the report, sheets,
   motion strips and palette; record the *adapted* technique in `STYLE.md`. Treat measurements
   and sampled colours as clues, not instructions: the Medo brand remains locked. Reference
   assets stay reference-only unless their use rights are separately documented.
2. **Timing — there is no target length.** The video is exactly as long as the voice-over, and
   every number derives from it. Measure it, don't guess it:

   ```bash
   python3 tools/vo_length.py out/vo24.wav --json plan/beats.json   # duration + scene bounds
   python3 tools/vo_length.py out/vo24.wav --check projects/<slug>  # must print OK before rendering
   ```

   Scene boundaries = midpoint of silences; `DURATION` (K, `src/data.js`), `B` (P, `scenes.py`),
   and `DURATION_IN_FRAMES` (R, from `plan/beats.json`) end exactly on the VO duration; the SFX bus
   and mix are cut to it.
   `tests/test_vo_length.py` fails if any doc or template reintroduces a fixed length.
3. **Engine choice** — see §6. A reel may use the validated hybrid renderer for sequential full-frame
   segments **and**, since v2, for one transparent Engine-K layer composited over an opaque base.
4. **Scenes** — first choose the motion for EVERY on-screen text element:
   `python3 tools/text_direction.py projects/<slug> --init`, then fill `captionStyle` / `textStyles` /
   `textElements` per scene with a rationale, and give every `plan/copy.json` fragment a `role`
   (rule 11). Build one scene, render 3 stills, then a 4–8 frame contact sheet. Do not go to
   "production" from the first attempt.
5. **Assets** — code → AI → search, respect the ladder and the licence log.
6. **Render** — use P, K, or R individually, or render sequential P/K/R segments with `tools/render_hybrid.py`; then mix/master as specified by that workflow.
   For a review copy, `pipeline.py <project> --draft` renders 540×960 / 15 fps into
   `out/draft.mp4` (engine K or P) or `out/hybrid-draft.mp4` (engine hybrid, same plan and layer
   order, P bases `--draft`, K bases/overlays `--fps 15 --scale 0.5`, masks on the 540×960 canvas).
   A draft is the one documented exception to the 30 fps lock: it never muxes, never passes a QA
   gate, never overwrites a master, and R has no draft path at all. See `docs/preview.md`.
7. **QC** — ≥3 visual rounds (contact sheets), probe the MP4, check loudness, check the
   Arabic with your eyes, run `brand_check.py`.
8. **Deliver** — the master MP4 + an 8–10 line Arabic message (§8).

## 6. Which engine

| Situation | Engine |
|---|---|
| Explainer/tool/laptop reel with Medo's character, cards, devices, captions | **P** — `medo-motion/templates/procedural-reels` (Pillow + OpenCV + FFmpeg chunks) |
| Kinetic Arabic typography, lists, UI, 3D-ish, fast timeline previews | **K** — `medo-motion/templates/render` (Canvas + Playwright) |
| React/TypeScript-driven scenes, reusable UI/data visualisations, rich compositions and interactive Studio review | **R** — `medo-motion/templates/remotion` (Remotion + React + TypeScript) |

Engine P is the default for talking reels because it composites Medo's poses cheaply
and reliably. Choose R when its React component reuse or Remotion Studio materially helps;
it is not automatically faster than K. Copy the selected template into the project, never edit
the toolkit in place. For R, install the scaffolded npm dependencies inside the project and
render only after `plan/beats.json` has the measured VO timeline. R currently has hard cuts
and a basic pose component; it does not inherit P/K's animated icon or transition catalogs.

When a concept genuinely needs multiple strengths in one reel, scaffold `--engine hybrid`.
`HYBRID.md` and `tools/render_hybrid.py` define the frame/audio contract, validation, and
assembly; neither engine's features are transferred into another.

- **v1 — sequential segments** <!-- CAP:sequence -->: one engine owns each half-open frame range,
  full frame.
- **v2 — transparent overlays** <!-- CAP:layers -->: a segment may carry `layers` = an opaque
  base plus Engine-K layers rendered with alpha, so kinetic type or UI can sit **over** presenter
  footage <!-- CAP:alpha_layer -->. Up to 4 overlays, stacked bottom-up in plan order
  <!-- CAP:multi_overlay -->, and only K may be transparent <!-- CAP:alpha_k_only -->. Once there
  is more than one overlay, each must name the K scenes it draws (`"scenes": ["title"]`)
  <!-- CAP:overlay_scene_filter --> — a scene belongs to exactly one overlay, and a scene named
  twice is a plan error. v1 plans are normalised on read, so no project breaks
  <!-- CAP:v1_normalised -->.
- **v2.1 — masked overlay** <!-- CAP:overlay_masking -->: an overlay may carry a static `mask`
  where **white keeps the base**, so Engine-K type passes *behind* a P presenter instead of over
  his face. The mask is a fractional rectangle with optional feather
  (`{"type": "rect", "x": .34, "y": .42, "w": .32, "h": .58, "feather": 10}`)
  <!-- CAP:mask_rect --> or a 1080×1920 matte inside the project
  (`{"type": "image", "path": "assets/presenter-matte.png"}`) <!-- CAP:mask_image -->. Masks are
  static for the whole segment, paper over one overlay, and only a transparent overlay can carry
  one — a mask anywhere else is a plan error, never a silent no-op.

The runner fails closed on gaps, overlaps, dimensions, frame counts, frame rate, or duration
errors <!-- CAP:frame_exact --> and adds the single soundtrack once, after picture assembly
<!-- CAP:audio_after_picture -->. There is no pre-render approval gate.

## 7. QA gates before delivery

- 1080×1920 · 30 fps · duration = VO duration · H.264 high + AAC · faststart
- **−14.5 ± 0.3 LUFS**, true peak ≤ −1.5 dBTP (two-pass loudnorm)
- Master ≥ 2.5 Mbps (`-crf 13 -tune animation`); anything under ~2 Mbps is rejected
- Arabic joined and correct **in every scene, checked visually**
- One impact per scene, no static hold > 2.5 s, HUD drawn after the camera move
- No text over a face, nothing important outside y 200–1350, captions at y≈1455
- Every placeholder declared, every external asset in `assets/CREDITS.md`
- No series name, title, episode number or logo invented by you: on screen only if the user
  asked, worded by him
- `python3 medo-motion/scripts/brand_check.py --project <project>` is clean
- Layout audit passes for K (`node tools/layout_audit.mjs --project <project> --out <fresh-dir>`) or P (`python3 tools/layout_audit_p.py --project <project> --out <fresh-dir>`)
- Final master passes `python3 tools/media_qa.py <master.mp4> --mode master --vo <project>/out/vo24.wav --beats <project>/plan/beats.json` (and cumulative `python3 tools/stage_gate.py <project> --stage deliver --media <master.mp4>`)
- `python3 tools/selftest.py` still passes after your changes (regression net); when changing R, also run `python3 tools/selftest.py --remotion`

## 8. Delivery message

8–10 short lines of Egyptian Arabic: file name + measured specs · scene-by-scene in one
line each · what you are unsure about (inferred boundaries, temporary font, placeholder
presenter) · assets used + licence line · 2–3 next improvements. **Never mention a logo
or a series title** — there is none, and never suggest adding one. Say where the project
folder is, and remind the user it is a working folder (outside the repo history).

## 8a. Repository weight

Tracked assets are 165 MB of a 1,899-file tree (81.7 MB fonts, 64.4 MB images, 35.6 MB of
`assets/poses/source`). There is **no Git LFS** on purpose: a filter would tax every clone and CI
job, and rewriting history is an owner decision. `tools/repo_weight.py --check` is the gate instead
— total weight may not grow more than 2 MB past `docs/repo-weight-baseline.json`, and any tracked
file of 3 MB or more has to be named in that baseline. A new heavy asset therefore needs a
deliberate `--update`, which prints the delta so the diff shows the weight change. Details and the
LFS recipe (if that decision ever flips): `docs/repository-weight.md`.

## 9. Environment notes (this sandbox)

- If `ffmpeg` is not on PATH, the engines honour `FFMPEG_BIN=/path/to/ffmpeg`.
- `ffmpeg` = static build from `imageio-ffmpeg`; there is no `ffprobe` binary, so
  `tools/ffprobe_shim.py` is installed as `ffprobe` (ffprobe-compatible JSON subset). It is a
  **fallback**: when a real `ffprobe` is on PATH (or named by `MEDO_REAL_FFPROBE`) the shim execs it,
  so every other option works; `MEDO_FFPROBE_SHIM_ONLY=1` forces the PyAV path. It never delegates to
  `tools/bin/ffprobe` or to itself. `python3 tools/ffprobe_shim.py --supported` prints the fields the
  fallback promises, and `tests/test_tool_contracts.py` keeps that list honest.
- Chromium for engine K comes from `@sparticuz/chromium` (npm) because the Playwright
  CDN is blocked; `tools/chromium.mjs --env` resolves the Chromium executable and prepares the required shared-library environment.
- Engine R uses the Remotion packages pinned in the project scaffold (`npm install` inside
  `projects/<slug>/`); it reads the same measured `plan/beats.json`, the local font manifest,
  and pose assets.
- Pillow here is built **without** libraqm. Engine P detects that and shapes Arabic with
  `arabic_shape.py` (HarfBuzz + FreeType). This is real shaping, not presentation forms.
  `doctor.py` reports which backend is active; both are acceptable.
- Fonts: the font manifest (<!-- AUTO:fonts -->125<!-- /AUTO --> families: <!-- AUTO:fonts_ofl -->123<!-- /AUTO --> SIL OFL 1.1 + Permanent Marker Apache-2.0 + Ubuntu UFL-1.0) lives in `assets/fonts/fonts.json`. The agent chooses
  faces per scene/element in `plan/text-direction.json`; Cairo/Inter are only a system-chrome
  fallback. Chromium picks fonts from the page (`/assets/fonts/...`), engine P from the
  project's `assets/fonts/`, and R from `public/fonts/` + generated `@font-face`.

## 10. Map

```
AGENTS.md              ← this contract (any agent)
DESIGN_SYSTEM.md       ← unified design system reference
README.md              ← Arabic overview
assets/                ← shared inputs: fonts/, poses/, sfx/
projects/<slug>/       ← scratch folder for one video (Git-ignored, not an archive)
tools/                 ← setup.sh · doctor.py · selftest.py · new_project.py · render_hybrid.py · media_qa.py · repo_weight.py · layout_audit.mjs · layout_audit_p.py · stage_gate.py · ffprobe_shim.py · chromium.mjs
tests/                 ← pytest: Arabic shaping invariants, brand lock, scaffold, one real frame
                         (≤900 lines per module; shared builders in `<feature>_support.py`, fixtures in conftest.py)
docs/                  ← analysis + conventions + Skillry fit review (docs/README.md)
medo-motion/           ← the toolkit
  SKILL.md             ← entry point (Claude Code reads this; it defers to AGENTS.md)
  brand/               ← locked identity (human + machine)
  reference/           ← on-demand guides (Arabic typography, hooks, voiceover, …)
  styles/              ← reusable style inspiration (no forced default)
  templates/           ← engine P + engine K + engine R (Remotion) + TASTE.md
  scripts/             ← fonts, SFX, TTS, preflight, brand guard, preview
```

## 10a. Recording what changed

Every behavioural change ends with **one entry in `CHANGELOG.md`** (newest first, under `Unreleased`
with the date): what was wrong, what the evidence is, and how it is guarded. `medo-motion/CHANGELOG.md`
is a **frozen archive** of the toolkit's own 1.0 → 2.7 history — never add to it, and never write the
same entry in both places (`tests/test_changelogs.py` enforces that). Numbers you cite must come from a
run you can repeat; if you did not run it, say so in the entry.

## 11. Never do this

- Ask for a logo, a series name, an episode number, or "your brand colours". The name/
  title/episode slot belongs to the user: if he wants one he says it; you never propose it.
- Keep a finished video as a project folder in the repo, or add a CI workflow for a past
  video. The studio is a tool, not an archive — deliver, then let the folder go.
- Add a font outside the manifest, a colour outside the palette, or a random stock clip.
- Ship a preview with motion but no sound as if it were the deliverable.
- Claim capabilities you did not verify (`doctor.py` output is your evidence).
- Install or vendor a third-party Agent Skill before inspecting its complete package, license, commands, network use, dependencies, and provider costs; see `docs/skillry-fit.md`.
- Promise hand animation of the presenter (poses are static: bob/tilt only).
