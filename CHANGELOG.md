# Changelog

## Unreleased — 2026-11-10 (hybrid: Engine K finds its own browser)

**A hybrid reel no longer needs a pre-configured shell.** `render_hybrid.py` now resolves the
toolkit and bundled Chromium itself when `MEDO_TOOLKIT`/`MEDO_CHROMIUM` are unset: it uses
`tools/toolkit` when `playwright-core` is installed there and asks `tools/chromium.mjs --json` for
the browser path, which only unpacks the npm package on disk — it downloads nothing. A caller that
already set the variables is left untouched, a broken or missing helper is not fatal (the K render
still reports its own error), and a plan with no K layer never probes the browser at all.

Before this, a hybrid reel with a K overlay run from a clean shell died inside Node with
`Cannot find module 'playwright-core'` while `pipeline.py` worked — the same plan behaving
differently depending on who started it. Verified from a clean shell
(`env -u MEDO_TOOLKIT -u MEDO_CHROMIUM -u LD_LIBRARY_PATH`): a masked K overlay renders and the
plan reports `HYBRID OK · 1 layered, 1 K overlay(s) (1 masked) · 30 frames` in 31 s.
`tests/test_hybrid_env.py` (6: needs-k detection, fill rules, caller wins, broken helper, no
subprocess when the helper is absent).

## Unreleased — 2026-11-10 (hybrid v2.2: several K overlays)

**Up to four transparent Engine-K overlays above one base, stacked in plan order.** One K project
holds one scene tree, so two overlays need a way to be two different pictures: each overlay now
names the scenes it owns (`"scenes": ["title"]`). `render.js --only a,b` validates the ids in Node
before the browser opens (an unknown id used to stall the page for its 30 s timeout), and `main.js`
draws only those scenes, leaving every other moment transparent. A scene belongs to exactly one
overlay; once a segment has more than one overlay, an overlay without `scenes` is a plan error
rather than a silent duplicate of its neighbour.

**One encode for the whole stack.** Overlays are composited in a single FFmpeg pass (each PNG
sequence is an input, each layer gets its own `overlay` link, masks included), because a per-layer
pass would be another CRF-13 generation and a four-layer reel would soften visibly.

Verified on a real project with two overlays (`scenes: ["example"]` and `["arabic-example"]`, mask
on the upper one): the first overlay covers 100% of the frame at t=0.5 s and 0% at t=2.5 s, the
second is the exact inverse, and the 90-frame file comes out in one encode.
`tests/test_hybrid_stack.py` (17) + `tests/test_hybrid_layers.py` +4 (two-colour stack, mask on the
top layer, a real `--only` Chromium render, unknown-id rejection). `CAPABILITIES` swaps
`single_overlay` for `multi_overlay` + `overlay_scene_filter`, marked in both contracts.

## Unreleased — 2026-11-10 (hybrid v2.1: masked overlay)

**Type can now pass *behind* a presenter instead of over his face.** A v2 overlay accepts a static
`mask` where **white keeps the base**, so the renderer hands exactly those pixels back to the P
footage:

```json
{"engine": "k", "alpha": true,
 "mask": {"type": "rect", "x": 0.34, "y": 0.42, "w": 0.32, "h": 0.58, "feather": 10}}
```

`rect` takes canvas fractions plus a pixel feather (realised as a `gblur` on the matte, so the edge
ramps instead of stepping); `image` takes a project-relative 1080×1920 matte, converted to gray and
read as a third FFmpeg input. Absolute paths and paths that leave the project are plan errors, a
missing matte fails **before** the base is touched, and a mask anywhere but a transparent overlay
is rejected rather than silently ignored.

**The maths is a subtraction, not a redraw:** `alpha(K) × (1 − mask)` via
`alphaextract → blend=multiply → alphamerge` before the overlay. Verified on a real hybrid project
(same scene, mask vs no mask): pixels inside the rectangle differ by 57.5 on average, pixels
outside differ by **0.0** — the overlay was removed from the requested area and nothing else moved.
`tests/test_hybrid_masks.py` (24, new: plan contract + graph shape + matte safety),
`tests/test_hybrid_layers.py` +4 (real rect, feathered edge ramp, matte image, missing matte
leaves the base byte-identical), and `CAPABILITIES` grew `overlay_masking`/`mask_rect`/
`mask_image`, marked in `AGENTS.md` and `HYBRID.md` and enforced by `tests/test_capability_contract.py`.

## Unreleased — 2026-11-10 (batch 3, part 3: draft preview for engine P)

**`--draft` now covers engine P too.** `pipeline.py <project> --draft` on a P project runs
`run_all.py` with `REEL_DRAFT=1` and returns `out/draft.mp4` (540×960 @ 15fps) without touching
the master: chunks land in `out/draft_chunks/`, the log is `out_log-draft.txt`, and
`out/video_only.mp4` plus its own chunks are left exactly as they were. Preview frame `i` is
source frame `2i`, so the timeline is identical to the master — the preview is the same 55 seconds,
sampled every other frame and encoded at half size (CRF 13 kept: a review copy should not look
worse than the film).

**The saving is temporal, and it is real.** P still *renders* at 1080×1920 and downscales on the
way to the encoder, so the win comes from half the frames, not from a canvas knob. Measured here on
the demo timeline (55.2 s, 2 vCPU, no GPU): master 1,656 frames in **429 s** (33.7 MB) vs draft
828 frames in **227 s** (9.5 MB) — **1.89× faster, 3.5× smaller**. K's draft still wins more
(≈3×) because Chromium renders fewer pixels; the honest comparison is in `docs/preview.md`.

**Preview and master never share cache.** `build_signature(..., draft=True)` mixes a
`draft-preview` marker into the hash, so a half-size chunk can never be served to a master (or the
reverse) even though both are built from the same source files; a master run on an unchanged tree
still reuses its chunks (verified: two consecutive master runs, no invalidation), and a draft run
leaves them alone. `tests/test_engine_p_chunks.py` +1 (draft ≠ master signature, draft stable),
`tests/test_pipeline.py` +3 (P draft runs through `run_all` with `REEL_DRAFT`/`REEL_DIR`/binaries
and never muxes, missing preview fails loudly, master path stays free of `REEL_DRAFT`), and the
old "engine K only" rejection test now asserts the P-and-K message on an R project.

## Unreleased — 2026-11-10 (tool contracts · binary attributes · graceful optional dependency)

**The seven untested tools now have contracts.** `tests/test_tool_contracts.py` (18 tests) pins
what a CLI owes its caller, not its internals: every one of `fonts_preview`, `itshover_import`,
`transitions_sheet`, `visual_verify`, `whisper_align` and `whisper_fetch` answers `--help` and
rejects unknown flags with exit `2`; `ffprobe_shim` answers the exact subset the studio uses
(`format=duration`, stream `codec_name`/`sample_rate` on a real WAV) and fails loudly on a missing
file; `fonts_preview` writes a sheet at the requested width; `transitions_sheet --only <name>`
renders one cell; `itshover_import --list` prints the registry.

**`whisper_align` no longer explodes on import.** It imported `faster_whisper` at module level, so
`--help` — and any test that imports the file — died with `ModuleNotFoundError` instead of saying
what to install. The dependency is now loaded at call time and a missing one exits `2` with
`pip install faster-whisper` and the fetch hint; the contract test asserts that message and that no
traceback is printed. Everything else in the studio already runs without it.

**`.gitattributes` — binaries stay binary, text stays LF.** There is deliberately **no Git LFS**:
history is ~112MB, LFS would add a dependency to every clone and to CI, and the real decision
(whether the repo is shared widely) belongs to the owner. What is pinned instead: `* text=auto`,
`binary` for fonts/images/audio/video, `text eol=lf` for code and docs. `tests/test_repo_hygiene.py`
(7 tests) checks it through `git check-attr`, so deleting or narrowing the file fails the suite
rather than silently rewriting a font.

## Unreleased — 2026-11-10 (contract↔capability guard · deterministic render group · coverage floor)

**The operating contract can no longer drift from the renderer.** Hybrid v2 shipped while
`AGENTS.md` and `templates/HYBRID.md` (the copy every hybrid project receives) still said
simultaneous layers were out of scope — a feature no doc-driven agent would use. Both contracts
now describe v1 *and* v2, every capability they describe carries a marker
(`<!-- CAP:alpha_layer -->`), and `tools/render_hybrid.py` declares the same list as
`CAPABILITIES`. `tests/test_capability_contract.py` (14 tests) compares the sets **in both
directions** — an implemented-but-unmarked capability fails, and a marked capability that no
longer exists fails too — plus it rejects unknown markers anywhere in the docs and checks that
each name has code evidence (e.g. `alpha_layer` → `--alpha`). Removing the `alpha_layer` marker
today reproduces the historical drift as a red test.

**`--dist loadgroup` makes the Remotion marks real.** `@pytest.mark.xdist_group` is inert under
xdist's default `load` scheduling, which is why the earlier grouping did not stop the webpack
bundle race. The CI render job now runs `-n 2 --dist loadgroup`, so the four bundling tests share
one worker; the one-shot retry on the transient 404 stays as a second line of defence.

**Coverage floor, raised deliberately.** The coverage job is no longer informational: it runs with
`--cov-fail-under=30` and a failing coverage run now blocks a PR (`make coverage` uses the same
floor). The number starts below the measured total (32.7% on the fast loop) so the gate can only
move up; raising it is an explicit edit, not a drift.

## Unreleased — 2026-11-10 (CI: Remotion bundlers no longer race)

**Remotion render tests are pinned to one xdist worker.** The two real-render tests in
`test_machine_explainer.py` and the two bundling tests in `test_three_remotion.py` now carry
`@pytest.mark.xdist_group("remotion-bundler")` (registered in `pyproject.toml`). Under
`pytest -n 2 $(tools/ci_groups.py render)` they occasionally collided on a webpack bundle and one
failed with `The requested path (/tmp/remotion-webpack-bundle-…/index.html) could not be found`;
the same tests pass solo and serially. Grouping removes the first race without slowing the cheap
tests in those files (only the four bundling ones are pinned), and the shared `_run_remotion`
helper retries **once** when the launcher reports that exact bundler 404 — never on a layout or
render assertion, so a real failure still fails the first time.

Checked while chasing that flake and **left as designed**: `templates/remotion/package.json`
forces `overrides: {"zod": "^4.6.7"}`, which makes every R render log
`Version mismatch: zod: installed 4.6.7, required 4.5.4`. That override is deliberate — it is
pinned by `tests/test_remotion_skill.py`, explained in `docs/remotion-skill.md` and
`medo-motion/skills/remotion/SKILL.md` (kept until Remotion supports Zod 4.6.x natively), and the
warning does not stop a render: the failure above was a missing webpack bundle directory, and the
retry rebuilt it. Removing the override would silence the warning at the cost of a documented
upgrade policy, so it stays.

## Unreleased — 2026-11-10 (batch 3, part 3: per-scene cache)

**`tools/render_scenes.py` + `pipeline.py --scene-cache` — editing one scene costs one scene.**
Engine K already renders an absolute range, so each scene is encoded once into
`cache/scenes/<id>-<hash>.mp4`. The key is the shared layer (`data.js`, `main.js`, `render.js`,
`index.html`, every `src/lib/*.js`, fps/scale/crf) plus that scene's own module and timing — so
touching `outro.js` leaves `intro`'s key, file, and mtime untouched. Hits are re-verified with
ffprobe (1080×1920 and exact frame count); the final file is a `-c copy` concat of identical
encoder settings, with the soundtrack muxed once at the end. `cache/scenes/manifest.json` records
hit/miss and seconds per scene, and the output is never overwritten without `--force`. P caches
whole chunks and R has no range API, so `--scene-cache` on those exits `2` instead of pretending.
Measured on a two-scene project: first run 0 miss→2, second run all hits (~0.3 s), after editing
one scene `hits=1 misses=1`. `tests/test_render_scenes.py` (7, one real acceptance render) and
`tests/test_pipeline.py` +2.

## Unreleased — 2026-11-10 (batch 3, part 2: draft preview)

**`pipeline.py --draft` — a review copy in a fraction of the render time.** Engine K renders at
`--scale 0.5 --fps 15 --crf 30` straight from the same scene code into `out/draft.mp4`
(540×960); the temporary `Draft.mp4` is renamed, so `out/` never holds two copies. A draft runs
the `render` step only — there is no master to mux, no QA against it, and no delivery gate, and
the timing still lands in `cache/pipeline-timings.json` so preview-vs-final is two numbers.
`--draft` on P/R/hybrid exits `2` with a reason: those templates have no scale knob, and
rendering at full quality then downscaling would be a lie. Measured here on a 2-second K scene:
4.3 s master → 1.4 s draft. `tests/test_pipeline.py` +4 (command shape, rename, missing-output
failure, one real 540×960 render).

## Unreleased — 2026-11-10 (batch 3: alpha layers · HTML QA report · time to first video · doctor fixes)

**Hybrid v2 — a transparent K layer over a P/R base.** `plan/hybrid.json` version 2 replaces
"one engine owns the whole frame" with `layers`: an opaque base plus at most one K layer rendered
with `--alpha`. `render/main.js` clears the canvas instead of filling it black when
`params.alpha=1`; `render/render.js --alpha` writes a transparent PNG sequence (refuses `--jpg`,
forces 30 fps, no encoder); `tools/render_hybrid.py` composites with
`[0:v][1:v]overlay=format=auto` and `-frames:v` from the frame delta (not `-shortest`), writes
through a temp file plus `os.replace`, and reports `overlays` under `--profile`. v1 plans are
normalised on read, so no existing project breaks; `engine`+`layers` together, an alpha P/R base,
or two overlays are explicit errors. Pinned by `tests/test_hybrid.py` (25) and
`tests/test_hybrid_layers.py` (3 real-FFmpeg renders).

**`tools/qa_report.py` — the QA page a human can actually read.** One self-contained HTML page
(RTL Arabic) with the status, the media facts, the contact sheet, every Final Media QA item, the
`reel_lint` findings, the thresholds that were applied, and the raw JSON. The sheet is embedded as
base64, so the page has no network references and works from `file://`. It never overwrites an
existing report without `--force`, and exits `0` when the page was written even if the video failed
QA — the failure belongs on the page, not in the exit code. `tests/test_qa_report.py` (4).

**`tools/time_to_first_video.py` — "time to first video" is a number now.** Scaffolds a real K
project from nothing, times the five phases separately (toolkit deps, scaffold, plan, Chromium
render, ffprobe verification), and refuses to call a run successful unless the produced MP4 has the
requested duration. The documented target is 180 s on the reference laptop (Quadro M3000M, 4 GB,
2 vCPU) — `docs/ttfv.md` states it, `docs/metrics/ttfv.json` carries the measured runs, and
`tests/test_ttfv.py` keeps the prose equal to `TARGET_SECONDS` and exercises one real render.

**`make doctor` now suggests the repair.** Every `Finding` carries a `fix` command (pip package,
`make fonts`, `npm ci --prefix tools/toolkit`, `bash tools/setup.sh`, `nvm install 20`, …). The
report prints `fix:` under each capability that is not OK, then one deduplicated numbered
"Suggested fixes" list; `--json` exposes `fix` per finding plus a top-level `fixes` array;
`--fix` prints the commands only (no prose) and exits non-zero while anything is BLOCKED. Nothing
is executed: the doctor stays read-only. `tests/test_doctor.py` (6) and a rename of the R
capability to `engine R scaffold`.

## Unreleased — 2026-11-10 (one copy of the shared JS · skips instead of red tests · coverage · smaller functions)

**A5 — one copy of the shared JS.** 27 libraries (7,277 lines) were byte-identical copies in
`templates/render/lib` and `templates/remotion/src/lib`; one forgotten copy meant silent
divergence. `shared/js/` is now the only editable copy, `tools/sync_shared_libs.py --write`
(`make sync-libs`) refreshes both engines, and `--check` (`make check-libs`, wired into
`tools/ci.sh`) fails on a missing copy, a drifted copy, or a file that appears in both engines
but not in `shared/js`. `tests/test_shared_libs.py` pins it with 35 tests, including one `cmp`
per shared file. No bundler, no build step: both engines still ship real, self-contained files.

**A2 — the absolute-path migration scripts are archived.** `add_variants`, `merge_alansari`,
`merge_opus`, `merge_gl_transitions`, `extract_styles` and `generate_techniques_docs` all read
`/home/user/video-motion/...` (four also read `/tmp/...`) and none is referenced by code, tests
or CI. They now live in `tools/dev/_archive/` with a README mapping each script to the asset it
produced and to the test that guards that asset today; README and `docs/ALANSARI_INTEGRATION.md`
point at the archive instead of implying they run.

**A7 — a Python-only checkout skips the browser tests instead of failing them.** Eight tests
turned red on a machine that had installed only the Python side, because they launched Chromium
without a guard. `conftest.py` now exposes `requires_toolkit` (node + `tools/toolkit`'s
playwright-core and bundled Chromium) and the eight tests carry it; the opt-in Render-Smoke
helpers use `pytest.skip` with the install command instead of `pytest.fail`. Result: `8 skipped`
with an actionable reason, not a red build.

**A12 — `inspect_media` is 159 lines, not 454.** Split into eleven helpers
(`_check_faststart`, `_probe_streams`, `_scan_frames`, `_check_durations`, `_check_bitrate`,
`_check_frame_zero`, `_report_black_runs`, `_report_freeze_runs`, `_check_audio`, `_write_sheet`,
`_verdict`) around one orchestrator. Behaviour is pinned: reports for eight scenarios (master,
preview, video-only, black first frame, short clip, strict, missing file, bad mode) are
byte-identical before and after (`diff` = 0), and `tests/test_media_qa.py` still passes.

**A11 — the palette says what it is.** `lib.py` defines `BLUSH/MAUVE/SALMON` and keeps
`EMER/TEAL/YEL` as documented aliases; `scenes.py` aliases `GOLD` to `BLUSH` (same colour, honest
name). `tests/test_brand.py` checks the descriptive names against `brand.json` and asserts the
aliases still resolve.

**Tests — `audio_generate.py` has contracts now.** 45 tests for the 565-line SFX/bed generator:
48 kHz constant, dB helper, constant-power pan, 24-bit WAV round-trip, the sample-rate guard,
every documented SFX kind (stereo, finite, ≤ 1.0, deterministic per seed, anchor ≥ 0), bed length
and reproducibility, every `resolve_at` cue form, the limiter ceiling, and the `--audition` CLI
path. Writing them found a real bug: `read_wav` decoded 24-bit files — the exact format
`write_wav` produces — as if they were 32-bit, so a round-trip lost half the frames. Fixed, and
both WAV helpers now accept `Path` objects.

**Coverage — a number, not a gate.** `pytest-cov` is in `tools/requirements-dev.txt`
(pinned in `constraints.txt`), `make coverage` writes a terminal report plus `coverage.xml`, and
a non-blocking CI job keeps the XML. No `fail_under`: this first full run measures
**60% (7,763 of 19,346 statements missed)**. The gap is concentrated in tools nobody exercises
(`gen_tts_elevenlabs` 0%, `selftest` 0%, `beats_check` 0%, `music_kit` 0%), `reel_lint` at 19%,
and `scenes.py` at 38%; subprocess-only tools (`brand_check`) read as 0% because coverage does
not follow children.

## Unreleased — 2026-11-10 (docs numbers are generated · PRs run the whole suite · explicit license)

**A1 — one source for every documented count.** `tools/sync_docs_numbers.py` measures the
libraries on disk (techniques and their four sources, fonts and their licences, poses, icons,
styles, GLSL transitions, catalog transitions, text animations, backgrounds, looks, recipes,
SFX, music presets) and writes the value between named `AUTO` slots (small HTML comments) in
the docs. `--check` is a CI gate; `tests/test_docs_numbers.py` (9 tests) fails on drift, on an
unknown key, on a deleted slot, and on the four historic technique totals coming back as
hand-written numbers. Wired into `make docs-numbers` / `make docs-sync` and `tools/ci.sh`.
The stale values are gone: README said 1,434 in one place and 2,239 in another, AGENTS.md and
DESIGN_SYSTEM.md said 59, the legacy `generate_techniques_docs.py` said 334 — the real library
is **2,239 techniques in 44 categories**. The SFX row was also wrong (15 → 20).
`tools/README.md` no longer claims `make test` takes "~3 seconds" (measured: ~9 minutes serial).

**A14 — a real quick loop.** The `slow` marker was decorative (it skipped 25 of 1,394 tests and
saved a minute). The heavy render/synthesis/Chromium modules are now marked at module level:
`pytest -m 'not slow'` runs **938 tests in ~32s**, and `pytest -m slow` keeps the 553 rendering
tests for when you want them. The marker stays local — CI ignores it and runs every group.

**A3 — pull requests run all 1,394 tests, in three parallel groups.** `tools/ci_groups.py`
splits the suite into `contracts` (28 files: docs, schemas, brand, fonts, lint policy, skills),
`unit` (17: Arabic shaping, audio DSP, motion maths, icons) and `render` (35: Chromium, FFmpeg,
media QA), with unassigned files defaulting to `render`. `--check` fails if a test file is
unassigned, listed twice, or missing, and if `ci.yml` stops running a group.
`tests/test_ci_groups.py` (9 tests) guards the split. `ci.yml` is now four jobs — static
contracts, contracts, unit, render-smoke — all installing `tools/requirements-dev.txt` and
running with `pytest-xdist -n 2`; the render job also keeps the 3-frame Engine-P smoke render.
Measured on this machine: contracts 12s, unit 29s, render 5m31s (full suite was 8m49s serial
and the PR job ran only 12 of 78 files). `pytest-xdist==3.8.0` + `execnet==2.1.2` pinned in
`tools/constraints.txt`.

**A6 + A15 — CI hygiene.** The dead `feat/deterministic-motion-effects` push triggers are gone
(`full-renderers` is nightly/manual only, the two Remotion workflows push on `main`), every
action is pinned to a commit SHA, the fast job installs the pinned requirements instead of
unversioned packages, and Node caches now include both lockfiles.

**A9 — explicit licence.** Root `LICENSE` (proprietary, all rights reserved, Arabic + English)
and `NOTICE` (bundled assets, adapted methodologies, runtime dependencies, trademarks) make the
posture visible without changing it; `medo-motion/LICENSE.md` and `assets/CREDITS.md` stay the
detailed records.

**Fix found by the parallel run:** `new_project.py` copied a template's `node_modules` into the
new project when a developer had installed the R dependencies inside the template, which made
scaffolds huge and collided with the test fixture's staged `node_modules`. `_copy_template()`
now ignores `node_modules`, `out`, `cache`, `.remotion`, `dist`, `__pycache__` and `*.mp4`.

## Unreleased — 2026-11-09 (deterministic pipeline runner — option 3 of the stage-gate discussion)

- **`tools/pipeline.py` (new) + `make pipeline P=projects/<slug>`**: the deterministic steps of a reel run end-to-end with fail-fast and per-step timing — `vo` (vo_length --check) → `lint` → `brand` → `mix` (audio_mix.py; skipped when `out/final_audio.wav` exists, SKIP note when no `plan/cues.json`) → `render` (engine dispatch: P = `run_all.py` with `REEL_DIR`; K = `src/render.js --crf 13` the full `plan/beats.json` timeline with optional `--audio`; R = `npm ci` when needed + the VO-gated `npm run render -- --audio <vo> --out out/master.mp4`; Hybrid = `tools/render_hybrid.py`) → `mux` (P only, the documented `-map 0:v -map 1:a -shortest +faststart` ffmpeg line into `out/master.mp4`) → `qa` (`media_qa.py`; master mode with audio, honest video-only mode without) → `gate` (`stage_gate.py --stage deliver --media <master>`; pass `LAYOUT=report.json` for the layout audit). **No creative decisions are made anywhere** — looks, recipes, styles, fonts, copy remain agent/human choices upstream.
- Engine auto-detection replicates the scaffold layout (hybrid first, then R, P, K); `--engine` overrides. `--from STEP` resumes, `--steps` selects a subset, `--dry-run` prints the plan, and **every run writes `<project>/cache/pipeline-timings.json`** (per-step wall ms + total + notes) — the numbers decide whether a human-stopped runner (option 2) is worth building.
- K render passes `--crf 13` (master contract) instead of the template's preview-oriented default 18; R render keeps the documented VO-gated command (its gate enforces the measured VO timing — fold any music/SFX bed into the VO upstream or mix afterwards).
- `tests/test_pipeline.py` (11 tests): engine detection incl. hybrid precedence, step ordering, fail-fast abort semantics, timings report structure, `--dry-run` runs nothing, unknown steps rejected, full PU-run sequence with a fake ffmpeg. Fast CI runs it.
- Verified end-to-end on a bounded real run (REEL_MAXFRAMES=6, throwaway engine-P copy in /tmp): render 5.9s / mux (no-audio SKIP, video-only QA PASS) — container `projects/` untouched.

## Unreleased — 2026-11-09 (npm download lock covers the Alansari type-system families)

- **`tools/font-packages.lock.json` now pins 121 packages** (was 21): the 100 Alansari-added families that `@expo-google-fonts` publishes are pinned with the registry's `dist.integrity` (SHA-512) and version, merged alphabetically with the original 21 (which are byte-identical in value). The pins were sanity-checked by `npm pack` + tarball SHA-512 for four sampled packages (baloo-bhaijaan-2, noto-nastaliq-urdu, permanent-marker, ubuntu — all MATCH). **No embedded font file changed** — the lock is an install-time verification input only.
- **Documented exceptions:** the four Alansari families with **no `@expo-google-fonts` package** (verified 404 on 2026-11-09) — **Firjar**, **Thabit**, **Noto Naskh Arabic UI**, **Noto Sans Arabic UI** — are pinned nowhere by design; they ship with their specimen sources and OFL licence files on disk. Recorded in `tools/fonts_install.py` (`LOCK_EXCEPTIONS`) and `docs/fonts.md`.
- **`tools/fonts_install.py --verify-lock`** (new, read-only): audits the lock against the manifest and disk — every managed family pinned, every published Alansari family pinned, no stale entries, exceptions neither pinned nor forgotten, every locked/excepted Alansari family on a declared free licence (OFL-1.1 / Apache-2.0 / UFL-1.0) with its licence file present. A licence review is still required to *add* a family or *change* a pin — the audit enforces bookkeeping, not provenance.
- **`tests/test_fonts_lock.py`** (new, 7 tests) + `tests/test_fonts_install.py` updated (the lock now legitimately covers more than the 21 managed families; tarball fixtures now patch the `LOCK` path), wired into Fast CI together with `--verify-lock`. Full fonts gate re-run after the lock refresh: `--check` OK (125 families), `tests/test_fonts.py` green, `--verify-lock` green.
- Docs updated: `docs/fonts.md` (lock coverage + exceptions + post-refresh OFL review note), `assets/CREDITS.md` (125-family licence summary), `CHANGELOG.md`.

## Unreleased — 2026-11-09 (Remotion agent skills integrated as an adapted optional add-on)

- **`medo-motion/skills/remotion/SKILL.md` (optional add-on for Engine R)**: audited and adapted the official `remotion-dev/skills` pack (v4.0.541, commit `a2824c6`, 13 skills; upstream declares no license — Remotion itself is source-available under the Remotion License) into a studio-native playbook: the studio R path (`tools/new_project.py --engine r` → `npm ci` → `typecheck` / `npm run studio` / `npm run stills` → VO-gated `npm run render -- --audio`), explicit studio-wins overrides of upstream defaults (local OFL fonts only — no Google Fonts during render; Medo's VO is the single timing master; `npm run studio` + shared Chromium instead of `npx remotion studio`; no `@remotion/*` packages installed without a deliberate aligned decision; the Interactivity API flagged unverified on the scaffold's `remotion` 4.0.539 pin), and a per-skill disposition table covering all 13 upstream skills (adapted / reference-only). No upstream file is copied or redistributed; the add-on is original writing.
- **Drift guards** (`tests/test_remotion_skill.py`, 14 tests) pin the scaffold versions, the allowed command path, the 13-skill disposition coverage, the provenance tokens, the absence of vendored upstream files, and the report's completeness; wired into Fast CI. Integration report in `docs/remotion-skill.md`; attribution in `assets/CREDITS.md`; indexed in `docs/README.md`.

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
