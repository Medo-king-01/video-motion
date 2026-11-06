# Changelog

## Unreleased — 2026-11-06 (Studio readiness pass: licence-safe all-OFL type pool, recalibrated shaping gate, green CI)

Environment + gate repair before the next reel (setup on a clean venv, `doctor` READY, P/K renders
verified by `tools/selftest.py`):

- **Licence safety:** `Permanent Marker` and `Ubuntu` arrived in the type-pool expansion without an
  `OFL.txt` and their upstream licences are not SIL OFL 1.1 (Apache-2.0 / Ubuntu Font Licence), so
  they were removed from the allowed set in `assets/fonts/fonts.json` — the studio ships client work
  on an all-OFL promise and must not claim one it cannot prove.
- **Shaping gate recalibrated (`tests/test_fonts.py`):** the glyph-ink overlap threshold moved
  0.20 → 0.28 because connected Arabic strokes put *healthy* variable fonts at 0.19–0.27 (measured
  per weight, `cache/font-overlap-measured.json`), while eight calligraphic faces measured 0.24–0.50
  **and** failed visual QA (`cache/font-collision-sheet.png`): Jomhuria, Aref Ruqaa, Aref Ruqaa Ink,
  Gulzar, Noto Nastaliq Urdu, Reem Kufi, Reem Kufi Fun, Reem Kufi Ink. Those eight are marked
  `captionSafe: false` in the manifest (display-only, never captions/body) and the gate skips them;
  any future family above 0.28 still fails the build until measured and eyeballed.
- **Docs generated for the expanded pool:** `docs/fonts.md` gains the 102-family pool table, the
  measured-overlap table and the updated rejected list; `assets/CREDITS.md` records every family's
  source + OFL; README counts corrected (123 families: 61 Arabic + 62 Latin, 21 caption core).
- **Technique library contract per source (`tests/test_techniques.py`):** the studio-native 59
  recipes keep the strict rules (`how` > 60 chars naming a real studio API); merged reference
  catalogues are validated by their own shape (Alansari: build steps + Arabic how; Opus: description
  + upstream locator; gl-transitions: shader file present in `assets/gl-transitions/`), and
  `docs/techniques.md` was regenerated from the library (`make techniques-doc`).
- `make ci` (Ruff + pytest + brand/contrast audit) and `tools/selftest.py` (doctor + P/K renders)
  are green again; `drawtext` stays an optional WARN (contact-sheet timestamps fall back).

## Unreleased — 2026-11-04 (Native Machine Explainer workflow & X01–X04 geometric occlusion QA across P/K/R)

Standalone Phase 1 native studio implementation (`docs/machine-explainer.md`, zero new dependencies):

- **Machine Explainer core & 4 parametric hardware cutaway archetypes (`nvme_ssd`, `cpu_package`, `ram_dimm`, `cooling_system`, plus `custom`)**:
  implemented natively in `procedural-reels/machine_kit.py` (Engine **P**), byte-identical shared
  `render/lib/machine-kit.js` + `remotion/src/lib/machine-kit.js`, `render/lib/machine-visual.js`
  (Engine **K** Canvas2D + `protectBox` + `drawDirectedText`), and `remotion/src/lib/MachineDiagram.tsx`
  (Engine **R** `<svg>` + `<DirectedText>`) using only the locked 12-colour `brand.json` v2.6 palette,
  pure deterministic `f(t)` state (`spin`, `packet_flow`, `heat_tint`, `airflow_stream`, `pulse`), and
  dynamic safe envelopes (`layout_p.safe_envelope` / `layout.js:safeEnvelope` / `BRAND.margin`).
- **Source locator, unified VO timing & polygon coverage-mask occlusion gates (`tools/machine_explainer.py`, `tools/reel_lint.py`, `make machine-check`)**:
  enforces `X01` (verifiable `sources[]` + structured `locator: {kind, value}` + supporting quote, or
  explicit `illustrative` disclaimer + on-screen label without unverified spec numbers), `X02` (unified
  `visual_direction.measured_words` anchor + explicit `revealWindow.unit` `vo_seconds`/`scene_seconds`),
  `X03` (painter-ordered 2D face-polygon coverage-mask occlusion with foreground alpha transmittance and
  configurable `--max-occlusion` / `qa.maxOcclusion` / `step.maxOcclusion`), and `X04` (safe-zone &
  `PLATFORM_RIGHT_RAIL` envelope check).

## Unreleased — 2026-11-04 (Arabic kashida & mixed-run typography, phrase captions, isometric cutaway kit, shutter blur & mobile/ASR QA)

Native clean-room studio upgrades distilled from the MIT-licensed `majedphotos/video-ad-editor`
(`v6.3.0`) review (`docs/video-ad-editor-fit.md`, attributed in `assets/CREDITS.md`, zero third-party
runtime dependencies added):

- **Unicode-safe Arabic kashida, mixed RTL/LTR phrase order & slot ticker (`lib/arabic.js`, `arabic_shape.py`)**:
  fixes multi-word English/number run reversal inside RTL sentences (`visualWordOrder` / `visual_word_order`
  and UAX #9 `N1` neutral-run merging in `arabic_shape.py:_runs`), adds `kashidaSlots` / `insertKashida` /
  `stretchKashida` / `drawKashida` (`K`) and `kashida_slots` / `insert_kashida` / `stretch_kashida` /
  `draw_kashida` (`P`) respecting right-only letters, harakat clusters, and `لا` ligatures, plus
  `fixRuqaaTaaMarbuta` and vertical masked `drawTextSlot` / `draw_text_slot`.
- **Phrase-chunk captions (`lib/captions.js`, `procedural-reels/captions.py`)**: `groupCaptionChunks` /
  `group_caption_chunks` groups measured VO words into `2–4` word unboxed RTL phrases without orphaning
  Arabic glue particles (`في`, `من`, `على`, `مش`, `اللي`...), rendered via `drawPhraseCaption` /
  `draw_phrase_caption` with active-word brand highlight, calm `still` mode, and `hideRanges` hero-text
  suppression windows.
- **Brand-locked Isometric Cutaway "How It Works" Kit (`iso_kit.py` + byte-identical `iso-kit.js` for K/R)**,
  **3D Extruded Explainer Icon/Symbol Tiles (`tile3d.py` + byte-identical `tile3d.js` & `three-tile3d.js` for K/R)**,
  and **Temporal Shutter Motion Blur (`lib.py:shutter_blur` + byte-identical `shutter-blur.js` for K/R)**:
  deterministic 3-layer cutaway hardware/system diagrams (`slab`, `cylinder`, `ring`, `coil`, `wire`),
  perspective-warped 3D beveled icon/symbol tiles with animated diagonal specular gloss sweeps, and
  windowed sub-frame shutter averaging.
- **Repository-only visual header (`docs/assets/studio-banner.svg`, `docs/assets/studio-mark.svg`)**:
  aesthetic GitHub documentation emblem crafted strictly from the locked 12-colour v2.6 palette (never
  stamped onto rendered videos).
- **`tools/phone_preview.py` (`make phone-preview`), opt-in `L04` (`--platform-ui`), and `tools/asr_check.py`
  (`make asr-check` + `stage_gate.py` `G02`)**: renders a 4-panel mobile preview sheet (`9:16` Reels/TikTok
  HUD + right-rail buttons, `3:4` profile grid, `1:1` square, and `13.5%` real grid tile), audits right-rail
  RTL text collisions (`x940..1080, y1100..1500`), and catches Whisper hallucinations, stutter loops, bad
  word bounds, and untranscribed voiced speech gaps.

## Unreleased — 2026-11-04 (post-render media QA, Engine P layout audit, stage gates & doctor JSON)

Clean-room post-render verification and stage-gate capabilities inspired by the architecture review of
`calesthio/openmontage` (`docs/openmontage-fit.md`, zero external code or dependencies added):

- **`tools/media_qa.py` + `make qa` + `render_hybrid.py --qa`**: single post-render MP4/AAC acceptance
  gate enforcing `AGENTS.md §7` on real encoded media (`Q00` container/codec/`yuv420p`/`moov < mdat`
  faststart, `Q01` `1080×1920 @ 30fps` + VO/beats duration & frame sync, `Q02` master bitrate floor,
  `Q03` non-blank frame `0` & black-frame dropout scan, `Q04` `> 2.5s` static-hold freeze detection,
  `Q05` AAC + EBU R128 `-14.5 ± 0.3 LUFS` / `TP <= -1.5 dBTP` / PCM clipping / dead silence, plus
  contact-sheet export via `--sheet`). `render_hybrid.py --qa` validates the assembled temporary MP4
  before atomically publishing it.
- **`templates/procedural-reels/layout_p.py` + `tools/layout_audit_p.py` + `make layout-p`**: brings
  Engine K's `L00`–`L03` safe-zone, text-collision, presenter face-box protection (`face_box` /
  `face_boxes` across `presenter.draw` and `PoseTrack.draw`), camera-zoom box projection, `#CB271B`
  annotated failure PNGs, and `--replay` (`R01`/`R02`) reverse-order determinism audit to Engine P.
- **`tools/stage_gate.py` + `make gate`**: cumulative stage checkpoints (`intake → plan → render →
  deliver`, `G01`–`G06`) with content-addressed SHA-256 staleness verification in
  `<project>/cache/stage-gate.json`, external asset attribution check against `CREDITS.md`, and
  unapproved `CHIP`/series guard.
- **`tools/doctor.py --json`**: deterministic JSON capability envelope reporting `READY` / `DEGRADED` /
  `BLOCKED` overall and per engine (`P`, `K`, `R`, `Hybrid`) alongside active Arabic shaping backend.

## Unreleased — 2026-11-03 (animated backgrounds)

Twelve animated backgrounds, re-coloured to the brand, now live in all three engines.

- **`medo-motion/motion/backgrounds.json` (new catalogue)**: 12 patterns (`iso-grid`, `grid-2d`,
  `paper`, `aura`, `orbital`, `orbit-mono`, `frames`, `organic`, `perspective`, `glyphs`, `pulse`,
  `wash`) × dark/light. Every colour is a brand ROLE (`ink`, `paper`, `red`, `red_deep`, `salmon`,
  `blush`, `gray_1..4`) resolved against `brand/brand.json` — no hex appears in a pattern, and a test
  checks that every rendered pixel is a mix of two palette colours.
- **`templates/render/lib/backgrounds.js`** (K and R share one byte-identical file) and
  **`templates/procedural-reels/backgrounds.py`** (P, numpy): the same pure function of `t`, so a
  frame is identical whether the render walks forward, jumps or renders chunks in parallel.
- **`tools/backgrounds_sheet.py` + `make backgrounds`**: contact sheet, plus `--compare` which
  rasterises every pattern in K (real Canvas) beside P and reports the per-pattern difference.
  All 24 variants are currently within Δ11; the test fails above Δ16.
- Patterns that were outside the palette were converted, not dropped: the katakana `matrix` became
  `glyphs` (Arabic letters + Arabic-Indic digits), the green ECG `pulse` became brand red, the violet
  `pastel` became `aura` (blush + red_deep), and `crimson` folded into `grid-2d`.
- **Fixed a real rendering bug found by the parity check**: Canvas interpolates gradients in
  premultiplied alpha, so fading a colour to `transparent` (transparent *black*) darkened the middle
  of every glow. Both engines now fade to the same hue at alpha 0.
- `tools/motion_studio.html` paints its stage with the real background (`?bg=orbital&theme=light`),
  `AGENTS.md` gains hard rule 9, `docs/backgrounds.md` documents the catalogue and the gotchas, and
  `new_project.py` asks which background a scene uses instead of leaving it to chance.

## Unreleased — 2026-11-03 (pose library v2)

The presenter library was replaced: **24 hand-cut poses → 49 poses of one character**, sourced from
Medo's personal library (`Medo-king-01/Medo-s-Personal-Library`, 30 full-body + 19 half-body, RGBA).

- **New intake rule (changed, not removed).** "Ask for 2–4 images at the start" is gone. The library
  *is* the fourth input: the agent reads the catalogue and casts every beat from it, and asks for an
  image **only when a scene needs a pose the library does not have** — then names the missing slug and
  the beat in the same intake message. `AGENTS.md` §1/§1a, `SKILL.md`, `START-HERE.md`,
  `templates/TASTE.md`, the `new_project.py` brief, `docs/presenter.md`; pinned by
  `tests/test_workflow.py::test_poses_are_asked_for_only_when_the_library_cannot_cast_the_beat`.
- **`tools/lib/pose_catalog.py` (new).** Slug, Arabic label, English search word, tags, facing, note,
  framing (`full`/`bust`), `SCALE`, `ALIASES` and `SOURCE_ID` (which source file each slug came from).
  The catalogue, not the manifest, is the thing you edit.
- **`tools/presenter_build.py`** now takes transparent cut-outs (`assets/poses/source/<id>.png`) and
  only trims + normalises (1200 px full / 1180 px half, 8 px margin); `cutout()` and the JPEG `raw/`
  folder are gone, and a source without an alpha channel fails loudly instead of shipping a grey box.
- **Framing**: 30 full shots anchored on the ground line (1390), 19 half-body on the top guide (190),
  so a cut between them stays a clean camera push-in.
- **Aliases** cover the whole previous library (`warm → open-hands`, `puzzled → shrug`, `waiting →
  neutral`, `close-point → point-aside`, …) and every `medo_*` name, so older scene code still
  resolves; both engines' embedded fallback tables are generated from the catalogue.
- `assets/poses/`: 49 normalised PNGs + `poses.json` (geometry now includes the `source` id), and
  `assets/poses/source/` keeps the untouched originals. `docs/presenter.md` rewritten, `README.md` and
  `docs/README.md` counts corrected.

## Unreleased — 2026-11-03 (refactor pass)

Structure-only: **no rendered pixel, lint verdict or CLI output changed**. Every claim below is
pinned by a test (`tests/test_refactor_contracts.py`) and was checked against golden snapshots of
the previous behaviour (transition geometry ×14 kinds ×51 steps, `composite` pixels, lint reports
for the good/bad fixtures, scaffold tree, doctor report).

- `transition.py`: the 83-line / 11-deep `layer()` is now a dispatch table of one builder per kind
  (`_build_reveal`, `_build_blinds`, …); magic numbers are named constants; an unknown `kind` now
  raises instead of silently rendering an empty mask. `composite()` reuses one `_blend()` helper.
- `tools/lib/media_bin.py` (new): one precedence rule for ffmpeg/ffprobe (`*_BIN` → PATH → bundled
  static → installed shim) replaces four different lookups across seven files.
- `doctor.py`: module-level script → importable checks returning `Finding` records, with a pure
  `verdict()`/`render()`; one failing capability can no longer abort the report, and silent
  `except: pass` blocks are gone.
- `new_project.py`: 138-line / depth-6 `main()` split into `slugify`, `resolve_target`,
  `write_plan_files`, `copy_assets`, `install_engine`, `scaffold`.
- `text_direction.validate()` (141 lines → 45) and `visual_direction._validate()` (112/depth-6 → 47)
  split per concern (caption/style/element/font/coverage), each returning error strings.
- `reel_lint.lint_copy()` split into fragment/timing/visibility/coverage checks; `scenes.py` and
  the S03 lint message is fixed (it no longer claims "carries no copy" for a fragment that has copy).
- `_common.append_asset_entry()` replaces the duplicated manifest writer in `get_fonts.py` and
  `openverse_sfx.py`; `render_hybrid.executable()` no longer hides a bad override.
- Removed dead code: an always-false palette assertion in `brand_check.py` and a tautological
  `or` in `test_transitions.py`.

## Unreleased — 2026-11-03 (studio scope)

- **The studio is a tool, not a video archive.** `projects/*` is now ignored by Git (only
  `projects/README.md` is tracked), every scaffold writes its own `*` `.gitignore`, and
  `tools/new_project.py` gained `--out` so a video can live outside the repository. Past
  project folders and per-video CI workflows are not kept: the finished episode project that
  was left behind and its preview workflow were removed (the studio does not name or archive
  videos). AGENTS rule 12, `tests/test_studio_not_archive.py`.
- **The name/title/episode slot belongs to the user.** The agent never asks for, invents or
  suggests a series name; if the user asks for one on screen, it is executed word-for-word.
  The archived working name was removed from `brand.json` (`studio_name` + explicit
  `on_screen_name_rule`), `BRAND.md`, `SKILL.md`, TASTE and START-HERE.
- Engine P template no longer draws a default episode chip or captions that talk about
  "the series" (`CHIP` gates the chip; two demo captions rewritten).
- Follow-up pass: the name slot is explicitly the user's (`approvedByUser` skips C07 only for
  copy he asked for, `docs/craft.md`), the archived master brief lost its copyable script /
  palette / chip recipe (inventory only), `brand.json` no longer describes itself as "Medo's"
  studio, AGENTS rule 12 now says what the studio's memory *is* (the toolkit), and engine-P
  workflows no longer target the dead `fix/engine-p-chunk-integrity` branch.

## Unreleased — 2026-11-03

- Project scaffolds are trackable by Git; only generated output/caches/secrets are ignored.
- Setup has explicit Python/Node prerequisites, a read-only inventory mode, strict failures,
  an optional development dependency set, and reviewed Python constraints / npm lockfile installs.
- Private atomic `.env` creation; symlink/path preflight on scaffold, reference analysis,
  font downloads and caption output. P segments use unique temporary files.
- Caption schema: script `words` are strings; frozen `final` contains scene-local timings.
  Mono PCM16 WAV is required; missing ASR anchors and invalid scene bounds fail clearly.
  JavaScript values are JSON-encoded.
- Font readiness checks every expected family, weight and file; npm font downloads have
  version/integrity pins. Existing bundled assets and licensing are unchanged.
- Added Python 3.10/3.12 quality matrix and scheduled/manual dependency auditing.
- Start from the full repository; see `docs/development.md` for setup and migration details.

Engine contracts and templates are unchanged: P/K/R still use the shared motion/font/brand
interfaces; Hybrid remains sequential full-frame segments with one soundtrack (`HYBRID.md`).
Local validation on Python 3.11: `bash tools/ci.sh` and
`python3 tools/selftest.py --remotion --hybrid` passed (P, K, R and Hybrid real renders).
GitHub matrix results must be checked after the workflow runs; they are not implied by local success.

Additional local checks: 373 tests passed; real `setup.sh --dev --check` left the complete
repository tree unchanged; one real pinned font package passed SHA-512 verification/extraction.
`pip-audit` (base/development Python baseline on 3.11) and production npm audits
(toolkit + Remotion template lockfiles) reported no known vulnerabilities. Optional ASR
dependencies and the legacy Python 3.10 Pillow baseline are not covered by that clean audit.

Remote-matrix follow-up: keep test helper paths after the standard library so Python 3.10
`wave` does not import the renderer CLI `chunk.py`. Added a cold-process WAV regression
check, plus per-version CI log artifacts and bounded failure annotations.
