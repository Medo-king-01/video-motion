# Changelog

**Scope:** the studio as it ships — engines P/K/R, the hybrid renderer, `tools/`, tests, contracts and
documentation. It starts at **2026-11-09** and is newest-first. The toolkit's own version history
(scaffold 1.0 → 2.7, 2026-11-01 → 11-09) is frozen in `medo-motion/CHANGELOG.md`; new entries belong
**here**, never in both (there is a test for that).

## Unreleased — 2026-11-12 (contract 1.3, engine P adapter, editor, eight methods)

The plan's remaining items 1–5 stopped being prose. What is measured here: a project that carries
Arabic text and clip speed, a migration that only moves forward, a crash-safe autosave, **the first real
render backend**, a local editor page over the same core, eight methods that produce editable projects,
and long renders that can be watched and stopped.

- **Contract 1.3** (`docs/contract-1.3.md`) — `texts[]` + `clip.textId` (`U10`), `clip.speed` as a reduced
  fraction that widens the source range it consumes (`U08`), `asset.streams` for multi-stream media
  (`U09`), and opacity allowed on text tracks. Every 1.3 field is optional: 1.0–1.2 projects stay valid.
- **Migration** (`tools/unified_project_migrate.py`) — forward only. Adds exactly what the newer contract
  requires (`transitions: []` before 1.2), is idempotent, refuses an invalid project (`M01`), an unknown
  or **newer** version (`M02`) and a migration that fails its own re-check (`M03`). `--check` for CI.
- **Recovery** (`tools/unified_project_store.py`) — `autosave`/`recover`/`discard_autosave` write a sibling
  `<project>.autosave.json` carrying `savedAt` and the revision it grew from. A stale candidate is
  reported and **refused**, never written over newer work; an unreadable candidate is an error, not a
  silent delete.
- **Engine P is a real backend** (`tools/adapter_p.py`, `docs/adapter-p.md`) — implements the frozen
  contract (`compile`/`preflight`/`render`/`cancel`) and draws stills, crossfades, Arabic captions and
  opacity offscreen. It refuses speed (`R03`), keyframes (`R04`), video/audio assets (`R02`/`R05`),
  non-crossfade transitions (`R07`), out-of-range frames (`R08`) and overwriting an output folder
  (`R10`) — before a frame is written. Publishing is atomic and cancelling leaves nothing behind.
  Tested claim: **the exported frame is the previewed frame**, by hash.
- **Capabilities** — P now declares `project.read`, `graph.execute`, `range.render`, `alpha.layer`,
  `text.arabic` and `offscreen.render` as supported, `transitions.catalog` as conditional. The phase-0
  guard narrowed instead of disappearing: a backend may claim read/execute only when
  `tools/adapter_<x>.py` exists for it, so K/R/Hybrid stay honest.
- **Local editor** (`tools/editor_server.py` + `editor/index.html`, `docs/editor-ui.md`) — one page, no
  framework, over the same validated core: multi-track timeline, PNG preview, split/trim/ripple,
  undo/redo, caption editing, MP4 export, autosave on every operation, and a banner that shows engine P's
  refusal reasons. Every invalid edit returns HTTP 400 with the core's own message.
- **Eight working methods** (`tools/workflows.py`, `docs/workflows.md`) — Free Edit, Script to Video,
  Talking Head, Montage, Podcast, Explainer, Product Review, Motion Design. Each produces a validating
  schema-1.3 project that engine P can draw; captions are distributed without overlapping and their ink is chosen
  from the measured luminance of the band they sit in (`W03` refuses to invent them, `W01`/`W02`/`W04` cover empty, unknown and self-invalid cases).
- **Progress and cancel** — `video_export.build(..., progress=, cancel=)` and
  `sequence_export.build(..., progress=, cancel=)`. Cancelling raises `M07`/`Q06` and removes the partial
  file or the frames already written, so a stopped render never looks finished.
- Tests added: `test_contract_13.py` 12, `test_migrate_autosave.py` 11, `test_adapter_p.py` 13,
  `test_workflows.py` 25, `test_editor_server.py` 9, `test_progress_cancel.py` 5 — **75 new tests**, and
  three older tests were corrected where the truth changed (1.3 is now a valid version; P's
  `alpha.layer` is supported; the frame dict carries `texts`).
- Still refused, and named: video/audio decoding inside the adapter, keyframes, wipes, speed rendering,
  clips drag-and-drop in the UI, and the two owner decisions (N4 storage, N9 device timing).

## Unreleased — 2026-11-12 (MP4, WAV, OTIO import, crossfades, K/R canvases)

Five gaps closed in one batch, each measured before it was claimed. The earlier "no MP4 is claimed,
because this environment has no encoder" note was **wrong**: there is no `ffmpeg` CLI, but PyAV ships a
full encoder (`libx264`, `h264`, `aac`, `pcm_s16le`), so an H.264 file is producible — and now produced.

- `tools/video_export.py` (new) — project → MP4 through the same `unified_reference_preview` frames the
  timeline uses, encoded by PyAV (`libx264`, `yuv420p`, faststart), with optional AAC audio muxed from a
  `audio_export` WAV. `check --decode` re-decodes and compares picture hashes. Codes M01–M06, 1800-frame
  cap. Determinism is stated correctly: `video.frameRoot` pins the rendered frames and `decode.sha256`
  pins the decoded pictures; the H.264 *bytes* are **not** guaranteed identical between runs (x264 frame
  threading), and the sidecar never pretends otherwise.
- `tools/audio_export.py` (new) — the project's audio tracks mixed to mono PCM16 WAV: `sourceIn` trim,
  `start` placement, per-tick `gain` evaluation, integer summing, saturation, `pcm.sha256` in the sidecar.
  16-bit WAV decodes with no dependency; other formats go through PyAV. Codes A01–A05.
- `tools/otio_import.py` (new) — the reverse of `otio_export`: ticks read from `metadata.medo` (not from
  rounded frames), metadata cross-checked against the OTIO structure, and a foreign timeline refused with
  `N02` instead of being guessed. `roundtrip` proves project and timeline come back byte-identical.
  Codes N01–N06.
- **Crossfades in the model** — `schemaVersion "1.2"` adds `tracks[].transitions`
  (`kind: crossfade`, `fromClipId`, `toClipId`, even `duration` centred on the cut). The checker enforces
  adjacency, evenness, non-overlap, video-only (`U07`); the reference renderer blends with integer maths;
  OTIO writes `Transition.1`/`SMPTE_Dissolve` with half-length offsets and reads them back; EDL writes a
  centred CMX `D` dissolve (both events widened by half the length) and its importer trims that half back.
- **K/R canvas paths** — `tools/canvas_engines.py` (new) turns the existing canvas document into engine K
  `--scale` arguments and engine R's generated `src/canvas.ts`, under the same rule engine P already
  uses: a uniform device downscale of 1080×1920 or a refusal by name (`X02` reshape, `X03` larger,
  `X04` odd/scale mismatch). Engine R's `Root.tsx` now composes at `CANVAS.width/height` and scales the
  1080×1920 stage as a whole.
- Docs: `docs/delivery.md` rewritten around five formats with the O/N/A/M/Q/E10/X code tables, canvas
  section, and an explicit "what is not claimed" list; README index and this file corrected.
- Audio crossfades: a transition on an audio track is a linear gain ramp in the mix (the outgoing clip
  falls to zero as the incoming one rises), reading each side's **handles** outside its own edges; media
  without them is refused with `A06` naming the clip, and EDL writes the same dissolve on the `A` channel.
  The manifest records the window per clip (`fade: {start, end, rising}`).
- Tests: `test_video_export.py` **20**, `test_audio_export.py` **22**, `test_otio_import.py` **17**,
  `test_model_transitions.py` **26**, `test_canvas_engines.py` **18**; `ci_groups` now covers 146 files
  (contracts 50 · unit 49 · render 47).

Measured: the 8 s / 360×640 demo encodes 120 frames in ~0.9 s to a 16 KB MP4 whose decoded fingerprint
re-verifies with `check --decode`; a 4 s audio mix writes 384,000 samples at 48 kHz with `peak 0.366`; a crossfade renders an
exact half-mix on the cut frame and the same project survives OTIO export → import → export unchanged;
`draft-15` resolves to `--scale 0.5` for K and `CANVAS = {width: 540, height: 960, scale: 0.5, fps: 15}`
for R, while `reel-1x1` is refused with "not a uniform scale of 1080×1920".

Still not claimed: byte-identical MP4s between runs, stereo/mp3 audio, wipes or audio crossfades, and engine K's own `ffmpeg` shell-out (the binary is absent here, so that path stays
unexercised — our encoding is PyAV).

## Unreleased — 2026-11-12 (CMX3600 dissolves: transitions now survive EDL too)

The last hole in the transitions story was the EDL: the exporter refused any project carrying a crossfade
(`E10`) rather than dropping it silently. Now it writes the CMX dissolve the project actually means.

- `tools/edl_export.py` — a `D <frames>` event centred on the cut: the outgoing event is widened by `d/2`
  at its tail (`recordOut`, `sourceOut`) and the incoming one by `d/2` at its head (`recordIn`, and
  `sourceIn` for real media; a still only moves its record position because it is held from source zero).
  Overlap on a channel is allowed only up to the declared dissolve (`E06` otherwise).
- `tools/edl_import.py` — reads `D`, requires the event overlap to equal the dissolve length, trims `d/2`
  back off both neighbours and records the `transitions` entry with `schemaVersion "1.2"`. A mismatch is
  `I06`: the cut would be a guess.
- `E10` keeps its name but now means what it should: a dissolve that cannot be expressed — half a frame, or
  media without enough handle — and the message names the clip and the missing ticks.
- Tests: `test_model_transitions.py` **26** (dissolve export, exact round trip through `edl_import`,
  handle refusal, overlap mismatch refusal); `test_edl_export.py` 44 · `test_edl_import.py` 16 ·
  `test_delivery_loop.py` 20 stay green.

Measured: the 4 s two-shot demo exports as `001 … C …` + `002 … D    10 …` with `recordOut 520000` /
`recordIn 440000`, and importing that EDL returns clips at `(0, 480000)` and `(480000, 480000)` with a
`80000`-tick crossfade — the re-exported event lines are identical.

## Unreleased — 2026-11-12 (three delivery formats, three honest limits)

Delivery now covers what a project actually holds: cuts (EDL), cuts plus effects/keyframes (OTIO), and a
rendered frame sequence with a manifest that can be re-verified. No MP4 was claimed at this point,
because this environment has no `ffmpeg` binary — later the same day PyAV turned out to encode H.264
fine, and that claim was corrected above.

- `tools/otio_export.py` — `build`/`check` for OpenTimelineIO JSON: `Timeline.1` → `Stack.1` → `Track.1`
  → `Clip.1`, `RationalTime` at the timeline rate, effects and keyframe curves carried in
  `metadata.medo`, disabled tracks preserved as `enabled: false`, the project hash on the stack, and
  transitions named as `not modelled`. Codes O01–O05.
- `tools/sequence_export.py` — PNG frames through the same `unified_reference_preview` the timeline uses,
  plus `sequence.json` with pixel and file hashes; `check` re-reads the files (an edited or missing frame
  fails). Codes Q01–Q05, 900-frame cap, `--frames` selection.
- `medo-motion/motion/profiles.json` — three new profiles: `reel-4x5`, `reel-1x1`, `reel-16x9`. The
  unified path renders them; engine P refuses a non-9:16 canvas by name (its design space is fixed).
- `docs/delivery.md` — which format carries what, both code tables, the size limits, and what is not
  claimed. README/map/profiles updated.
- Tests: `test_otio_export.py` **23**, `test_sequence_export.py` **22**, plus profile updates in
  `test_profiles.py`/`test_profile_render.py`.

Measured: the 8 s demo exports 4 clips / 3 tracks to OTIO; an 8×8 four-frame project exports 4 PNGs whose
hashes verify; `reel-1x1` renders a 1080×1080 sequence while `canvas --profile reel-1x1` is refused by the
engine with "not a uniform scale of 1080×1920".

Not claimed: no video encoding, no audio export, no OTIO import, and no transitions (the project model has
none).

## Unreleased — 2026-11-12 (a smaller canvas, not a different one: the device scale follows the profile)

The previous step wired only the frame rate and refused any size change. Engine P already separates a fixed
1080×1920 design space from the device buffer (`REEL_SCALE`), so a declared 540×960 draft maps onto that
existing mechanism instead of being refused.

- `canvas_profile.py` — `size_scale`/`plan`: a 9:16 size becomes a device scale (540×960 → 0.5), the same
  size is 1.0, and a reshaped (other aspect) or larger-than-master request is refused by name. `describe`
  now prints profile, device size, rate and scale.
- `run_all.py` sets `REEL_SCALE` from the plan before importing `lib`, and refuses when the resulting
  `DW/DH` does not match the declared canvas (e.g. `REEL_DRAFT=1` mixed with a profile) instead of logging
  a lie.
- `layout_p.py` scales its safe zones with the device size: draft-15 gives W×H 540×960, content zone
  100..675, margin 20, while keeping the proportions of the brand layout.
- `tests/test_profile_render.py` grew to **31**: half-size plan, reshaped refusal, oversize refusal, the
  design default, describe output, and a subprocess run proving layout is 540×960 @ 15 fps for draft-15.

Measured: `REEL_CANVAS=canvas-draft-15.json` → `layout_p` 540×960 @ 15 fps and `lib` `DW×DH` 540×960 with
`REEL_SCALE=0.5`; without an override both stay 1080×1920 @ 30.

Not claimed: no other aspect ratios (4:5, 1:1, 16:9 are refused, not implemented), no upscale, and K/R
still have their own canvas paths.

## Unreleased — 2026-11-12 (the EDL comes back: import with real media, no invented data)

`edl_export` could hand a timeline out; this closes the loop and brings one back. An EDL has reels and
timecodes only, so the importer resolves them against real files, hashes them, and refuses to guess.

- `tools/edl_import.py` — `build edl --media DIR -o project.json`. The rate comes from our own sidecar
  (`*.edl.json`) or an explicit `--fps`; each reel is matched to a file by the same rule the exporter used
  (`SHOT_A` ↔ `shot-a.png`), then hashed with its duration probed. Stills stay images with source 0, audio
  becomes an audio track, gaps stay where they were, overlaps on a track are refused. Codes I01 shape, I02
  no rate, I03 missing reel/media, I04 overlap or invalid result, I05 contradiction (rate/profile, frame ≥
  fps, unsupported channel, still not at zero), I06 PyAV missing.
- Durations are max(last event, sidecar `totals.durationTc`) so the project's tail is not truncated.
- `tests/test_edl_import.py` — **16 tests**: full round trip (same clip geometry, same event lines), audio +
  stills, gaps, opening the result in `timeline_session`, and every refusal plus the CLI.

Measured on the B5 demo: project → EDL (3 events) → imported project with identical
`start/duration/sourceIn`, and the EDL rebuilt from it matches the original event lines exactly.

Not claimed: no AAF/OTIO, no transitions or keyframes (the format cannot carry them), no timecode-rate
conversion (a 25 fps EDL into a 30 fps profile is refused, not resampled), and no audio beyond one clip per
channel.

## Unreleased — 2026-11-12 (a profile now reaches the renderer — the rate, explicitly)

Until now the declared profiles described a project but the Python engine still rendered at 30. The rate is
now carried into engine P, through one explicit document, and the canvas **size** is refused loudly rather
than silently mis-rendered.

- `tools/profiles.py canvas` — `--profile <id>` or `--project <file>` writes `{profile, w, h, fps, note}` for
  `$REEL_CANVAS`. `motion-film-60` still needs `--approval` (exit 3 otherwise); a project block also reports
  `"declared": true/false` against the registry. New code `P07` for a non-integer rate.
- `templates/procedural-reels/canvas_profile.py` — one small helper: `env_fps`, `check_size`, `describe`.
  Unreadable or absent overrides fall back to 30 silently; a size that differs from the renderer's canvas
  stops `run_all.py` before the first frame with the reason.
- `layout_p.py` and `run_all.py` read the override; `run_all.py` logs `canvas: profile … · WxH · N fps`.
- `tests/test_profile_render.py` — **28 tests**: blocks per profile, approval gate, project blocks, a
  non-integer rate, garbage overrides, the size refusal, and real subprocess runs proving `layout_p.FPS` is
  30 by default and 60 / 12 / 15 with the corresponding canvas file.

Measured: `REEL_CANVAS=out/c60.json` → `layout_p.FPS == 60`; `draft-15`'s 540×960 is refused by the engine
(`width 540 requested but the renderer draws 1080`) while its rate 15 still applies to the layout.

Not claimed: engine P still cannot change canvas size (its safe zones come from `brand.json`), K/R are
untouched, and nothing reads the project file automatically during a render — the wiring is explicit.

## Unreleased — 2026-11-12 (the delivery loop: edit or review, then export the EDL)

The exporter existed but had to be called on a file. Both real doors now open onto it, so the EDL always
describes the current edit rather than a copy that someone remembered to update.

- `timeline_session.Session.to_edl/export_edl` — the B5 session can hand out its own edit as CMX3600; CLI
  `export project -o reel.edl` and `script … --edl out.edl` (export after the edit is saved). A refusal
  surfaces as session code `T06` carrying the EDL code (e.g. `E05` for an enabled text track).
- `cut_plan.py edl` — kept cuts only, assembled gaplessly on one video channel, seconds rounded once to
  the nearest frame (`round(seconds × fps)`); a range that collapses to zero frames is refused (`E04`).
  A plan that fails `validate` exits 1 without writing anything.
- Stills: an `image` asset on a video track exports as a `STILL` event (`source 0 → duration`) with a
  comment, since a still has no source duration. Audio-on-video (and the reverse) stays `E03`.
- `tests/test_delivery_loop.py` — **20 tests** across both doors (edit changes the EDL, refusals, CLI
  round trips, determinism, the 999-event cap, plan rounding). `test_edl_export.py` grew to **44** with
  the still cases. `test_delivery_loop` joins the `contracts` CI group.

Measured: the B5 demo (4 s, three still clips) exports 3 `STILL` events, `00:00:04:00`; the B4 demo plan
(6 s, 4 cuts, one rejected) exports 3 events, record length `00:00:04:15`; both parse and re-validate.

Not claimed: still no transitions/keyframes in the EDL, no import direction, and no profile-to-engine
adapter — the EDL describes cuts and timecodes only.

## Unreleased — 2026-11-12 (owner decisions recorded; EDL delivery lands)

The owner answered the three open questions from `exploitation-map.md` §8: 60 fps stays **experimental, on
request only**; delivery to edit tools is **EDL first**; and the studio keeps **one identity** (Medo's) —
no per-client brand files. Two of those are decisions, the third needed code.

- `tools/edl_export.py` — CMX3600 export from the unified project, so a timeline can be handed to another
  editor without a project file or a render. One event per enabled clip (`V` first, then `A`/`A2`), reels
  from asset names, ASCII `TITLE` with the real name preserved in a comment, and a `*.edl.json` sidecar that
  can be re-checked. Codes E01 invalid project, E02 non-integer/drop-frame fps, E03 asset mismatch, E04
  off-frame or out-of-range ticks, E05 unrepresentable/empty, E06 channel overlap, E07 >999 events, E08
  unreadable text, E09 manifest drift.
- `medo-motion/motion/profiles.json` — `motion-film-60.use` now says "experimental, on request only" and
  `reel-30.use` records it as the single default; the `requiresApproval` gate is unchanged.
- `docs/edl.md` — shape, codes, sidecar, measured 4-event 8 s export, and what EDL cannot carry (effects,
  keyframes, transitions, speed).
- `tests/test_edl_export.py` — **42 tests**: timecodes per profile, reels, ordering, disabled tracks, two
  audio channels, refusals for every code, 1000-event cap, parse round trip, manifest drift, CLI.
- Docs updated: exploitation map (delivery rows and decision table now dated), profiles/subtitles "next",
  development status, README index.

Measured: an 8 s project (1,920,000 ticks, 30 fps) exports 4 events (c1/c2/c3 on `V`, m1 on `A`), duration
`00:00:08:00`; rebuilding twice yields the same EDL text and manifest; `check --edl` passes and catches a
manifest/EDL count mismatch as E09.

Not claimed: no CapCut/DaVinci native project, no import direction, no transitions (every event is `C`), and
no per-editor compatibility guarantee beyond the format tests.

## Unreleased — 2026-11-12 (B6 complete: declared delivery profiles, 12/15/30/60 fps, SRT/VTT)

Owner order: ابدأ. The last batch on the map. A project can now be sampled at four declared rates without
its timing moving one tick, and its on-screen copy becomes subtitle files — with 60 fps still requiring the
owner's explicit approval rather than becoming a quiet default.

- `medo-motion/motion/profiles.json` — one registry, `timebase 240000`: `reel-30` (default, 8000 ticks/frame),
  `motion-film-60` (4000, `requiresApproval: true`), `stop-motion-12` (20000), `draft-15` (16000, 540×960).
- `tools/profiles.py` — `list` / `check` / `apply --approval --dry-run`. Codes P01 shape, P02 id/default,
  P03 numbers, P04 approval missing (exit 3), P05 invalid project or foreign timebase, P06 fps that does not
  divide the timebase. Applying deep-copies, changes only the four `profile` fields, and validates before and
  after; `duration`, `tracks` and `timebase` are untouched.
- `tools/subtitles.py` — `copy.json` → SRT + VTT + `subtitles.json`. Sorted, non-overlapping cues, 0.04 s gap,
  0.6 s minimum reading time, two lines of 42 characters, VTT markup escaping. Codes S01 shape, S02 order/
  overlap/id, S03 timing, S04 text, S05 totals, S06 settings. `check` re-validates the manifest on its own.
- `tests/test_profiles.py` + `tests/test_subtitles.py` — **54 tests**: registry contract, frame counts,
  approval gate, determinism, both text formats, manifest mutations, CLI round trips and exit codes.

Measured: 4 s project (960,000 ticks) → 120 / 240 / 48 / 60 frames at 30 / 60 / 12 / 15 fps, duration
unchanged; `motion-film-60` without `--approval` exits 3. The reel fixture yields 11 cues ending 23.20 s, and
two runs produce byte-identical SRT, VTT and JSON.

Not claimed: `layout_p.py` still defaults to `FPS = 30` (wiring a profile into an engine needs an adapter),
no 4:5 / 1:1 / 16:9 profiles (the gates only measure 9:16), no burned-in subtitles, and no render-time
guarantee. The exploitation map is now closed; what remains is owner decisions, not another batch.

## Unreleased — 2026-11-12 (B5 complete: a timeline session that re-renders identically)

Owner order: continue. The project core, history, store, snap and reference preview already existed;
B5 connects them into one session and closes the loop the phase was defined by.

- `tools/timeline_session.py` — `Session.open` / `apply` / `save` / `render` / `status` over a replayable
  command list (`trim`, `split`, `move`, `ripple`, `snap`, `undo`, `redo`). Codes T01 unknown op, T02
  shape, T03 value, T04 nothing to undo/redo, T05 save conflict; a failed command changes nothing.
- Save is revision-checked (`unified_project_store`), autosave runs per command, and saving to a new
  path is create-only. History is deliberately per-session, not persisted.
- Rendering goes through `unified_reference_preview`; identity is `pixelSha256` (raw RGBA), with
  `fileSha256` reported for inspection and `graphDigest` for the compiled plan.
- CLI: `check`, `status`, `frame`, `script` (writes the edited project plus `*.frames.json` with per-frame
  hashes). Exit 0/1/2.
- `tests/test_timeline_mvp.py` — **28 tests**: edits, undo/redo, refusals, revision conflict, render
  identity before/after reopen, CLI round trip and autosave. Added to the `contracts` CI group.

Measured on the 4s / 120-frame demo: trim + ripple + split + move changes frames 70/80/110 and leaves
0/30 untouched; reopening the saved file reproduces every `pixelSha256`; two CLI runs are byte-identical
for both the project and the frame manifest.

Not claimed: no editor UI, no video export, no multi-track preview (the reference preview accepts one
enabled video track), and no persisted undo stack.

## Unreleased — 2026-11-12 (B4 complete: video ingest and a reviewable cut plan, no executor)

Owner order: start B4 in one push. A clip can now be read once, turned into shots, and handed back as
a plan a human edits — and the tool refuses to cut anything itself.

- `tools/video_ingest.py` — PyAV ingest to `media-report.json`: sha256, size, fps, frames, duration,
  codec, VFR flag, and one **visual delta** per frame pair from a 16×9 **RGB** grid. Luma alone missed a
  green→red cut during development, so colour is part of the signature; the frame cap is 7200.
- `tools/cut_plan.py` — `build` (threshold + minShot, short shots merged, last cut pinned to the measured
  duration), `check` (codes C00–C06, including totals recomputation), `review`, `set id=keep|reject`,
  `preview` (deterministic SVG timeline + HTML table), and `render` → **exit 3** on purpose.
- `medo-motion/schema/cut-plan.schema.json` — structural reference; the semantic contract is Python.
- `docs/cut-plan.md` documents the pipeline, the maths and the declared limits.
- `tests/test_video_ingest.py` (15) and `tests/test_cut_plan.py` (35) — the clip is synthesised in the
  test, so no media asset enters the repository; both files are in the `contracts` CI group.

Measured on a 6.00s / 180-frame clip: 4 shots (1.50 · 2.00 · 1.50 · 1.00), cut scores 75.84 / 88.26 /
63.16; rejecting one shot moves totals to keep 4.50s · reject 1.50s while the sum stays 6.00s.

Not claimed: audio analysis, semantic scene understanding, VFR re-timing, thumbnails, or execution —
`render` refuses by design until B5.

## Unreleased — 2026-11-12 (B3 complete: exploded views over the machine kit)

Owner order: start B3 in one push. The machine explainer could reveal and highlight parts; it could
not take them apart. It can now, deterministically, and reassemble to the exact same geometry.

- `shared/js/machine-kit.js` gains `explodeProgressAt`, `explodeMachineModel`, `EXPLODE_LIMITS` and a
  validation block for `spec.explode` (amount 0..1, window inside the spec, hold 0..0.9, spread 0..240,
  focus must match a part tag). Copied byte-for-byte to K and R by `sync_shared_libs`.
- The explosion is a 3D transform applied **before** iso projection: radial direction from the model
  centre, per-id FNV jitter, layer + rank lift, optional `focus` tag that holds still. Part ids and
  order are untouched.
- `procedural-reels/machine_kit.py` mirrors it (same rounding, same hash), so P draws the same frame.
- `medo-motion/motion/examples/exploded-nvme.json` is the reference spec (NVMe, `focus: pcb`).
- `tools/machine_explode_preview.mjs` records `drawMachineGeometry` into six SVG frames with one
  union viewBox; byte-identical per run.
- `docs/explode.md` documents the contract, the schedule maths and the declared limits.
- `tests/test_machine_explode.py` — **18 tests** (schedule, both validators rejecting the same broken
  config, identity/order, determinism, bounds growth and exact reassembly, focus hold, P↔K parity,
  preview determinism); added to the `contracts` CI group.

Measured: bounds width 406.86 closed → 659.21 open (×1.62) → back to 406.86 at `end`, with the same
`partId` order and the same vertices as a spec without `explode`. Not claimed: BOM labels, per-part
stagger, camera moves or a real video render.

## Unreleased — 2026-11-12 (B2 complete: a scene is data, not scene code)

Owner order: finish B2 in one push. A board is now a single JSON file with six element kinds and one
interpreter; anything outside the studio's vocabulary is refused with a code, never ignored.

- `medo-motion/schema/board.schema.json` — structural reference (root, stage, scene, element, move).
- `tools/board_check.py` — the real validator: structural + semantic, codes `B00` (root/version/duration),
  `B01` (unknown/missing field), `B02` (stage), `B03` (scenes/ids/overlap/duplicates/64-element cap),
  `B04` (element fields, per-kind requirements), `B05` (moves, `at` inside the scene), `B06` (brand role),
  `B07` (pose catalog), `B09` (unsafe image path). CLI exits 0/1/2, `--json` returns counts.
- `shared/js/board.js` — `boardFrame(board, time)` samples the active scene to z-sorted draw ops plus a
  centre-scaled camera; `drawBoardFrame(ctx, frame, assets)` paints them with `save`/`restore` per op and
  throws (never blanks) when a `person`/`image` has no asset. Copied byte-identically to K and R.
- `medo-motion/motion/boards/explainer-sample.json` — two scenes, 7 s, all six kinds, camera push plus
  parallax; `python3 tools/board_check.py` → `Valid board: data=1 · draw=1 · image=1 · person=1 · shape=1 · text=2`.
- `tools/board_preview.mjs` — four SVG frames, byte-identical per run.
- `tests/test_board.py` — **30 tests**; added to the `contracts` CI group.
- **Fix (found in the preview):** a `person` op carried `h` but no `w`, so the SVG preview emitted
  `width="NaN"` and `drawImage` got an undefined width. `boardFrame` now defaults person width to
  `0.62 × h` (explicit `w` allowed and validated), the preview no longer prints NaN, and a test pins it.
  The sample board also opens on a visible presenter instead of an empty first frame.

Not claimed: no video render (no Chromium here), no audio, no interactive timeline — those are B5/B6.
R carries the interpreter but no Canvas adapter, so its capability stays `conditional`.

## Unreleased — 2026-11-12 (B1b complete: ten element moves, with P/R honesty corrected)

Owner order: finish B1b. The catalog now carries **78 executable moves** (51 caption entrances,
3 element effects, 14 transitions, 10 element moves), and the ten element moves are new code, not
inventory.

- `shared/js/moves.js` gains `orbitItem`, `wordPathItem`, `explodePart`, `maskWipe`, `dataCount`,
  `cardStackItem`, `cameraPush`, `particleBurst` next to `pixelListItem`/`parallaxLayer`/`cameraProgress`.
  Pure functions only: bad arguments throw, `particleBurst` uses the same integer hash as the other
  effects (no `Math.random`), and `maskWipe` has four directions.
- `procedural-reels/moves.py` mirrors all ten; K↔P parity is measured on a sampled grid (≤1e-9),
  including half-up rounding for `dataCount`.
- `render/lib/moves-render.js` adds nine Canvas adapters plus `drawDataCount`; transforms are pinned
  through a fake context (save/restore balance, clip/rotate counts, centre-scaled camera).
- `tools/moves_preview.mjs` now writes **40 SVG frames** for all ten moves, byte-identical per run.
- `tests/test_moves_b1b.py` grows from 21 to **37 tests**.
- **Correction:** `element-moves` previously claimed P "supported" on pure functions alone. P and R
  are now `conditional` (pure library, no draw adapter); K is `supported`. The catalog must not call
  a pure function a rendered move.

Not claimed: no real render happened here (no Chromium/toolkit in the sandbox); the K adapter's
frame parity arrives with B5. `feather` stays a declared-but-unimplemented parameter.

## Unreleased — 2026-11-12 (B1b: the first two new moves, not just a catalog of the old ones)

Owner order: continue B1. `pixel-list` and `parallax` now exist as real element moves, so the catalog
grew from 68 to **70 executable moves** and no longer only records inherited families.

- `shared/js/moves.js` (pure, no RNG, no state) copied to K and R by `sync_shared_libs`:
  `pixelListItem(index, elapsed, …)` returns opacity/x/y/scale with the offset snapped to whole
  pixels of the font size, and `parallaxLayer(depth, progress, …)` pins depth 0 and follows the
  camera fully at depth 1; `cameraProgress` clamps and eases absolute time. Bad arguments throw.
- `procedural-reels/moves.py` mirrors it for engine P with the same numbers (half-up rounding
  expressed as `floor(v*fs+0.5)` so JS and Python agree).
- `render/lib/moves-render.js` (K) adds `drawPixelList` (per-row opacity + pixel-snapped translate)
  and `drawParallax` (translate + scale about the frame centre).
- Preview: `node tools/moves_preview.mjs out.html` writes eight SVG frames with no timestamps, and
  the test asserts two runs are byte-identical.
- `tests/test_moves_b1b.py` (21 tests): start/settle boundaries, pixel snapping, rejection rules,
  K↔P numeric parity on a sampled grid, exact adapter transforms through a fake Canvas2D context,
  and the preview's determinism.
- `moves.json` gains the `element-moves` family (K/P supported, R conditional: the pure functions
  ship but no R component consumes them yet); `docs/moves.md` documents the two moves and the
  remaining eight of B1b.

Not claimed: this is not a rendered scene test (no Chromium in this sandbox). The adapter transforms
are pinned with a fake context; a real frame comparison arrives with the K adapter in B5.

## Unreleased — 2026-11-12 (B1: the executable motion catalog, and what is only prose)

Owner order: start executing the exploitation map. B1 is the catalog contract, not a new animation.
`medo-motion/motion/moves.json` now answers "how many moves can this studio actually run?" in one
place: **68 executable** (51 caption entrances on P/K/R, 3 element effects on K/P with R conditional,
14 scene transitions on K/P with R unsupported) and **2,239 descriptive units** that are explicitly
*not* moves. `tools/moves.py --check` fails when a family's declared count differs from its source,
when a supported engine names a missing file or a symbol that is not in it, when evidence is absent
or outside the tree, when a `conditional` has no condition, when a `descriptive` family claims an
engine, or when an `executable` family supports no engine. `tests/test_moves.py` (20 tests) guards
the contract. `docs/moves.md` documents the rule and the next step (B1b: new families with a real
function, a frame test and a preview — not another description).

Why it matters: the technique library was about to be read as a move bank. It is not, and the
regression is now a failing test rather than a review comment. Nothing here renders or claims new
capability; every positive state points at code and evidence that already existed at `4cd725c`.

## Unreleased — 2026-11-12 (exploitation map: what to build, adapt, defer or reject)

Documentation only; no engine, tool or contract changed. `docs/exploitation-map.md` turns the owner's
system map (Hojas Studio + Video Ad Editor) into decisions against the tree at `4cd725c`. It corrects
six premises before any plan is built on them: the (AUTO:techniques) technique library is descriptive
(10 `primitive` categories, 58 entries with evidence, no function reference); the "102 moves" upstream
mixes timing rules with draw functions (already measured in `docs/editor-source-review.md`); only 17
of the 163 styles are adapted from Majed Video; the Board gap is a declarative layer, not drawing
(Machine Explainer / Slide Wall / One-Take / Fixed Stage already draw); Smart Cut's missing half is
ingest and cutting raw video, not speech understanding; and 60fps is a new profile with its own gates,
not a flag. Then: per-system status with evidence, build/adapt/defer/reject decisions, batches B1–B6
with acceptance criteria, and six owner decisions (identity per client, project library, 60fps,
CapCut/EDL export, TTS/AI adapter, mobile review). Linked from `editor-architecture.md` §9 and
`docs/README.md`. No performance numbers were measured here.

## Unreleased — 2026-11-12 (phase-0 architecture: the contract and an honest capability manifest)

Owner order: build the architecture before the Timeline UI. Two deliverables, no engine, no editor:

- **`docs/editor-architecture.md`** — the binding phase-0 specification: the six layers and their
  dependency direction, the time model (integer ticks only, half-open ranges, keyframes relative to
  the clip), Project/Timeline/Media/Effect models with a named 1.2 delta list, the rendered-backend
  adapter contract, the capability states, the reuse boundary for `hojas-studio` (PolyForm
  Noncommercial: ideas only) and `video-ad-editor` (MIT code, per-asset CREDITS still reviewed), the
  phase 0–6 map with exit criteria, and a checklist of what is implemented versus proposed. It
  changes no behaviour and claims no capability that the tree cannot back up.
- **`medo-motion/schema/backend-capabilities.json` + `tools/backend_capabilities.py --check`** —
  11 features × P/K/R/Hybrid, each with a state (`supported|conditional|unsupported|unknown`),
  conditions when conditional and repo-relative evidence for every positive claim. The checker fails
  on a missing answer, an invalid state, a conditional without a condition, a claim without existing
  evidence, a duplicate JSON key, or any backend claiming `project.read`/`graph.execute` before an
  adapter exists. `tests/test_backend_capabilities.py` (18 tests); the manifest is listed in the
  `contracts` CI group.
- **`tools/render_backend.py`** — the adapter contract frozen in code rather than prose: a
  `RenderBackend` protocol (`capabilities`, `compile`, `preflight`, `render(graph, frames, out,
  options)`, `cancel`), `conformance_problems()` that rejects a backend missing a method, answering
  fewer features than the manifest or contradicting it at runtime, and a `NullAdapter` per backend
  that returns `unsupported`/`R01` and raises on `render`. `tests/test_render_backend_contract.py`
  (23 tests) freezes the signatures.

Not measured: nothing here was benchmarked. The matrix is read from the code and tests that exist at
`4cd725c` plus this change.

## Unreleased — 2026-11-12 (one page to follow the development plan)

Documentation only; no engine, tool or contract changed. `docs/development-plan-status.md` merges the
three plans that were tracked separately — the unified-editor roadmap, the second studio review's risk
plan, and the P/K/R unification path — into one dated status page. Every status row was read back from
the tree at `4cd725c` (no adapters for the unified project, no visual editor, no migration; review
wave 1 closed except N9 and the owner's N4 decision; engine-unification stages 1–3 done, 4–5 never
requested). Also records that `.github/workflows/` is gone, so verification is `bash tools/ci.sh` and
`make` by hand. Listed in `docs/README.md`. Nothing here was measured; the performance numbers stay
in `docs/studio-review-2026-11-10.md` with their dates.

## Unreleased — 2026-11-11 (hosted workflows removed)

Owner decision: all six GitHub Actions workflows are deleted (`ci.yml`, `dependency-audit.yml`,
`engine-p-chunks.yml`, `full-renderers.yml`, `remotion-effects-smoke.yml`, `remotion-typecheck.yml`)
so that editing and experimenting on the repository is lighter. Nothing runs on push, on a pull
request or nightly any more. What is lost: the automatic Python 3.10/3.12 matrix, the coverage
floor, the nightly full P + K + R + Hybrid render, the Remotion typecheck and the weekly dependency
audit. What remains: `bash tools/ci.sh` and the `make` targets, run by hand. Tests, tools and
engines are unchanged; to restore the workflows, `git revert` this change.

## Unreleased — 2026-11-11 (unification path, stages 1–3: proof, drawn sprites on K, shared audio library)

Owner order: stages 1–3 of `docs/engine-inventory.md` only. No default changed, no engine retired;
P is still the default for talking reels.

- **Drawn sprites on K** — `medo-motion/templates/render/lib/art.js` (new, K only): engine P's
  `laptop`, `desktop`, part icons, `person` (7 poses, 7 expressions), `paper_spec`, `follow_button`,
  `cursor`, `sparkle`, `pill`, `bill`, `checkmark`, `crossmark`, `bubble`, with the same
  coordinates, sizes and palette. `drawArt(ctx, name, cx, cy, options, place)` mirrors P's `paste`.
- **Proof** — `tools/art_parity.py` (+ `art_parity.mjs`) draws 41 sprite cases and three typical
  1080×1920 frames with both engines and measures them: identical sizes, outlines within one pixel
  in 41/41, mean colour difference 0.28–3.54 of 255, five Arabic lines within one pixel of width.
  `--check` exits 1 on drift. Reference sheets in `docs/assets/art-parity/`. Static frames only:
  motion, transitions and animated captions were not compared.
- **Shared audio library** — `shared/py/` is now the one editable copy of `audio_engine.py`,
  `audio_mix.py`, `music.py`, `sfx.py`, `beat.py`; tools import from it. The P template keeps a
  byte-identical copy (scaffolded projects stay self-contained), gated by
  `tools/sync_shared_py.py --check` in `tools/ci.sh`, the workflow and `make check-libs`.
  `music.py` finds its presets by walking up; `sfx.py` reads a transition's sound from
  `motion/transitions.json` when engine P's `transition.py` is not importable. `mix.py`,
  `text_direction.py`, `arabic_shape.py`, `text_measure.py`, `media_tools.py` were not moved.
- Tests: `tests/test_art_parity.py`, `tests/test_shared_py.py`.

## Unreleased — 2026-11-11 (engine inventory: what P and R do that K does not)

Documentation only; no engine, contract or default changes. `docs/engine-inventory.md` answers the
owner's question about three engines versus one: the capability matrix read from the code, the gaps
K would have to close (drawn primitives in `art.py`/`lib.py`, browserless rendering, the 21 tools
that depend on Python modules living in the P template), a measured P/K frame time on the template
scenes (about 241 vs 29 ms per frame here; different scene content, so a direction, not a verdict),
and a staged path whose first three steps delete nothing. R speed and any P/K visual parity were
not measured.

## Unreleased — 2026-11-11 (optional free tools: Whisper, Demucs, HyperFrames)

Owner request: make FFmpeg, Whisper, Demucs and HyperFrames installable from the repository.
FFmpeg was already provided by `tools/setup.sh`; the other three stay optional and outside the
base render path.

- `tools/setup_extras.sh whisper|demucs|hyperframes|all` installs them; `--check` is a read-only
  inventory of all four.
- `tools/requirements-stems.txt` (new): `demucs==4.0.1`, `torch`/`torchaudio` `<2.6` and `soundfile` as the WAV
  backend. `analyze_ref.py --stems` called Demucs before, but nothing declared it.
- `tools/optional-hyperframes/` (new): `hyperframes@0.9.9` pinned with a lockfile, isolated like
  `tools/optional-three/`. `tools/hyperframes.sh` runs it with the studio Chromium and FFmpeg and
  with telemetry and skill auto-install off. It is still not an engine and not a base dependency;
  `docs/hyperframes-fit.md` records the update.
- `tools/stems.py` (new): Demucs as a studio tool — any audio/video in, `vocals`/`no_vocals` or the
  four stems out, plus `stems.json`. Windowing (`--start/--dur`), `--segment` for low memory,
  `--weights DIR` for offline machines; a missing dependency or an unreachable weights host is
  reported as a sentence, not a traceback. `docs/alignment.md` describes aligning captions on the
  `vocals` stem when a recording has music under it.
- `tools/html_scene.py` (new): the supported way to use HyperFrames. `new` scaffolds one offline
  HTML/CSS scene (fonts copied from `assets/fonts/`, colours generated from `brand.json`, CSS
  animation, no GSAP/CDN/registry); `check` rejects network URLs (H01), off-palette colours (H02),
  a wrong canvas or a duration that is not a whole number of frames (H03) and HyperFrames lint
  errors (H04); `render` verifies 1080x1920, 30 fps and the exact frame count. The clip is not
  wired into `render_hybrid.py`.
- Pin fix found while testing: Demucs 4.0.1 cannot load its checkpoints on PyTorch >= 2.6
  (`weights_only` default), so `requirements-stems.txt` pins `torch`/`torchaudio` `<2.6`.
- Neither upstream repository is copied into this one: both are consumed as pinned packages, so
  their licences, updates and size stay upstream (`NOTICE` §3).
- Not verified here: a real `htdemucs` separation — the weights host was unreachable. `stems.py`
  was run end to end through the Demucs CLI with a local, untrained checkpoint, which proves the
  plumbing and says nothing about separation quality.

## Unreleased — 2026-11-11 (hybrid draft: one sampling rule for P, K and the overlay)

A hybrid draft expected `end // 2 - start // 2` frames per segment, which is what engine P rendered,
but asked engine K (base and alpha overlay) for `--from start/30 --to end/30 --fps 15`, which renders
`ceil((end - start) / 2)`. Any K segment of odd length stopped the draft: `[0,3)` gave 2 frames for
an expected 1, `[30,61)` 16 for 15, and an overlay failed with "produced 2 frame(s), expected 1".

- Rule, for P, K and the overlay alike: a draft of `[start, end)` shows source frames `start`,
  `start+2`, … stopping before `end // 2 * 2` — `end // 2 - start // 2` frames, all inside the
  segment (`render_hybrid.draft_samples`, `render_p_segment.draft_source_frames`).
- Engine P's draft used to start at `start // 2 * 2`, one frame *before* a segment that starts on an
  odd frame; it now starts at `start`. Draft path only.
- Behaviour change, drafts only: at a cut on an odd frame the samples on either side are 1 or 3
  source frames apart instead of 2, and an odd-start P segment shows frames one later than before.
  The master path is unchanged; its commands are pinned by a test.
- `techniques.py --draw` never picks from the `gl-transition` category (reference shaders no engine
  renders); `--draw --category gl-transition` exits 2 and says so. The library, ids, order and
  counts are unchanged. A seeded draw that used to include one of them now returns a different plan.

## Unreleased — 2026-11-11 (audit_projects: see what the hardening will stop, before it does)

`tools/audit_projects.py` reads every folder under `projects/` (or the paths it is given) and
reports, without writing or running anything in them: scene ids outside the allowlist that
`render_scenes.py` enforces, an `out/final_audio.wav` with no `final_audio.mix.json` record, and a
symlinked `cache/`. Ids are read from the text of `src/data.js`; `--node` imports it instead.
Also: `tests/test_hybrid_draft.py` pins the master (non-draft) engine commands.

## Unreleased — 2026-11-11 (gl-transitions: notices, a manifest, and catalogue wording)

Follow-up to the entry below; still no licence decision and no loader.

- `assets/gl-transitions/THIRD_PARTY.md`: the full BSD notice of `InvertedPageCurl.glsl` and
  `StereoViewer.glsl`, copied from the files, plus the upstream `LICENSE` file as observed on
  2026-11-11 (labelled as observed, not as applied).
- `assets/gl-transitions/MANIFEST.json`: one entry per shader with its sha256 and declared licence.
  The commit the files were copied from is not known and is written as "غير معروف".
- The 30 files listed for review are marked "غير صالح لإعادة التوزيع قبل مراجعة" in the table, the
  manifest, `NOTICE` and `docs/GL_TRANSITIONS.md`.
- `assets/techniques.json`: the 189 `gl-transitions` entries no longer say "When you need a
  GPU-accelerated transition"; they say the shader is a reference that no engine loads. Counts,
  ids and order are unchanged; `docs/techniques.md` regenerated.
- `docs/scene-cache.md` states the warm-run time (≈560–590 ms) and what it is made of.

## Unreleased — 2026-11-11 (README agrees with .gitignore and pyproject.toml)

- README said a project's `BRIEF.md`, `plan/` and code "can be tracked by Git". `.gitignore` ignores
  `projects/*` and every new project gets a `.gitignore` of `*`. README now says nothing under
  `projects/` is tracked here and that a backup belongs in a separate place (its own repository, or
  `--out`).
- README said "install Python 3.12". The supported minimum is 3.10 (`pyproject.toml`, `setup.sh`);
  README now says 3.10+ supported, 3.12 recommended. The minimum itself did not change.
- `sync_docs_numbers.py --check` now also fails on these two contradictions (`claim_problems`).

## Unreleased — 2026-11-11 (gl-transitions: documented as a reference store, licences listed per file)

`docs/GL_TRANSITIONS.md` described 189 "GPU transitions ready to use", with a `"type": "gl-Cube"`
plan example, a `load_shader()` call, a GPU/FFmpeg-OpenGL requirement and a CPU fallback. None of it
exists: no engine and no tool loads a `.glsl` file (the search is recorded in
`tests/test_gl_transitions.py`). 19 of the 59 names in its tables were not files in the store. It also
said "License: MIT" for the whole set, while `InvertedPageCurl.glsl` declares BSD 3 Clause and
`StereoViewer.glsl` BSD 2 Clause.

- `docs/GL_TRANSITIONS.md` rewritten: reference store, not wired to the render path; the 14
  transitions in `medo-motion/motion/transitions.json` are the supported set. `README.md` and
  `docs/transitions.md` follow.
- `tools/gl_headers.py` reads every shader header and generates `docs/gl-transitions-headers.md`
  (file, author, declared licence, other origin named); `--check` runs in the tests.
- `NOTICE` names the two BSD files and marks the licence question undecided. No licence decision
  was made and no loader was built.

No behaviour change: nothing rendered through these files before either.

## Unreleased — 2026-11-11 (render_scenes: no shell, an allowlist for scene ids, paths kept in the cache)

`render_scenes.py` built `eval "$(node chromium.mjs --env)" && node src/render.js … --name <id>-<key>`
and ran it with `bash -c`, and only checked that a scene id was non-empty. A scene id of
`x;touch pwned` (with a matching module file) created `pwned-<key>` in the project — reproduced by a
test, not inferred. Now: scene ids must match `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` and are checked as
soon as `data.js` is read; every process is started from an argv list; the browser environment is
parsed from `chromium.mjs --json`; the scene module, `cache/`, `cache/scenes/` and each segment must
be real paths inside the project (no symlinks) before anything is unlinked or written; the ffconcat
list escapes `'`.

This is hardening, not isolation: engine K executes the project's JavaScript. Behaviour changes: a
scene id with a space, a dot, non-ASCII letters, or a leading `_`/`-` is now rejected by
`render_scenes.py` (`render.js` itself still accepts it); a symlinked `cache/` is refused. The output
is also measured once instead of twice, on the temporary file just before it replaces the target.

## Unreleased — 2026-11-11 (the pipeline stops on a stale audio mix)

`pipeline.py` kept `out/final_audio.wav` whenever it existed, so a re-recorded VO or an edited cue
sheet shipped with the previous mix. The mix step now writes `out/final_audio.mix.json` (hashes of the
VO, the cue sheet's values, the music/SFX/mix code, loudnorm availability, and the WAV itself) and
keeps an existing mix only while that record matches. Otherwise the step fails with `STALE: <what
changed>` and touches nothing; `--remix` rebuilds, `--keep-mix` records an explicit acceptance.

Refusal was chosen over an automatic re-mix: re-mixing overwrites a file that may have been edited by
hand. Behaviour change: a project that already has `final_audio.wav` **and** a cue sheet but no record
(mixed before this change) fails the mix step once, until `--keep-mix` or `--remix`. A mix without a
cue sheet is still kept, and the note now says it is unchecked. See `docs/audio.md`.

## Unreleased — 2026-11-11 (the scene-cache mux refuses a mix that does not fit the picture)

`render_scenes.py` muxed with `-shortest`: one second of picture plus half a second of audio wrote a
13-frame file and printed success. The mix and the picture are now measured before the mux; a
difference above half a frame is refused with both lengths in the message and nothing is written.
`--audio-fit pad|trim` is the explicit alternative (pad only lengthens the audio, trim only shortens
it; the picture is never cut). The joined picture and the muxed file are measured (frames, duration,
audio stream) before they replace the output, and the manifest records the measurement.

Behaviour change: a project whose `out/final_audio.wav` differs from the summed scene frames by more
than half a frame used to get a silently cut master from `render_scenes.py` / `pipeline.py
--scene-cache`; it now fails until the timing is fixed or `--audio-fit` is passed to `render_scenes.py`.

## Unreleased — 2026-11-11 (the K scene cache hashes every input a frame can read)

`tools/render_scenes.py` keyed a scene on four files under `src/`, `src/lib/**/*.js` and the scene's
module. Plans, assets, any other file under `src/`, the assets override and the motion mode were not
in the key, so editing `plan/stage.json` or replacing an image reported `hits=2` and shipped the old
MP4s. The key is now built from one table (`shared_inputs`): all of `src/` except the listed scene
modules, the seven plans `render.js` serves, everything under the **resolved** assets root except
audio, the package files that stand in for `node_modules`, and the resolved motion mode (now passed
to `render.js` explicitly). Paths are hashed with the content, so add/remove/rename invalidates.
`KEY_VERSION` is v2: segments cached before this change miss once.

Trade-off, deliberate: a plan or asset edit re-renders **every** scene — nothing proves such a file
belongs to one scene. Warm run on a scaffolded project (490 asset files, 116 MB): ~290 ms → ~445 ms.
Behaviour changes: a symlink under `src/` or the assets root that leaves that root now stops the run;
`--motion-mode` and `--hash-audio FILE` are new. See `docs/scene-cache.md`.

## Unreleased — 2026-11-11 (every parallel pytest run keeps its xdist groups)

The coverage, contracts and unit jobs and `make coverage` ran `pytest -n 2` without
`--dist loadgroup`, which leaves the `xdist_group("remotion-bundler")` marks inert.
`tools/ci_groups.py --check` now fails on any parallel pytest run without it.

## Unreleased — 2026-11-10 (engine P renders drafts into a real 540x960 buffer)

Engine P drew every frame in one 1080x1920 canvas and shrank it before the encoder: the draft paid
for pixels the encoder throw away. The design space is now separated from the device buffer.
`lib.SCALE` (0.5 under `REEL_DRAFT=1`, overridable with `REEL_SCALE` for tests; invalid values are
refused, never clamped) converts every buffer write — `paste`, `fill_rect`, the direct `cv2.line`
underlines and `speed_lines`, the `camera` warpAffine, the full-canvas backgrounds — while sprites,
fonts and layout math stay in the design space. The sprite cache is shared with the master, so the
master path is byte-identical (verified on 10 timeline points), and `chunk.py` /
`render_p_segment.py --draft` feed the encoder the 540x960 buffer directly (the shrink step is gone).

Measurements on the fixture reel at `REEL_SS=1`, same session: **109 ms/frame** against **163 ms** for
the old render-then-shrink draft (**1.49x**), with the picture matching the shrunk master at
MAE 0.4-1.6/255, PSNR 33-41 dB across the timeline (the Fixed Stage path: MAE 0.9-1.5/255, PSNR
32-37 dB). `tests/test_p_draft_buffer.py` (12 tests) pins the validation, the buffer shape, the
picture parity, the stage window geometry under scale, and the chunk output.

## Unreleased — 2026-11-10 (the real-Remotion suite stops failing only when it runs in parallel)

`pytest -n 2` over the modules that do real Remotion renders failed about one run in two, with either
`The requested path (/tmp/remotion-webpack-bundle-.../index.html) could not be found` or `Error: The
bundler completed without emitting bundle.js`. Both are one collision: Remotion derives its bundle
work directory from the **entry point** (`src/index.ts`) under the shared OS temp root, and every
scaffolded project has the same relative entry, so two workers building at the same instant resolve
to the same directory — one cleans up while the other is still writing or serving it. The retry
wrapper added earlier treated the symptom.

`tests/conftest.py` now gives each test process its own `TMPDIR` (`remotion_env()`), which Remotion
and webpack both honour; every Remotion subprocess in the suite receives it. Evidence: **2 failures
in 3 parallel runs before, 0 in 5 after**. `tests/test_remotion_isolation.py` guards the property —
stable within a process, different across processes, and actually present in the environment handed
to the renderer — so replacing `mkdtemp` with a fixed path fails loudly.

Deliberately scoped to tests: isolating every render process also throws away Remotion's bundle reuse
between consecutive renders of the same project, which is a speed feature the product relies on.

## Unreleased — 2026-11-10 (the soft glow stops blurring pixels the halo cannot show)

Profiling a master engine-P chunk (8 frames, `REEL_SS=3`) put `gaussian_blur` at **3.07 s of 8.34 s**
and `resize` at another 20%. The cause was `lib.circle_spr`: the halo behind a disc was drawn on the
whole supersampled canvas and blurred there — a 600 px radius with a 40 px glow is a 4104x4104 canvas
blurred with sigma 96. A sigma-96 Gaussian carries no detail finer than 96 px, so ~60x more pixels
were processed than the result could show, once per frame (the radius animates, so the sprite cache
never hit).

The halo is now drawn on the coarsest grid that still resolves its gradient (sigma ~= 4 px), blurred
there, upscaled with BILINEAR, and composited **under** the disc at logical size (1368x1368 instead
of 4104x4104). Measurements on the same material:

| | before | after |
|---|---|---|
| 9-frame master chunk, `REEL_SS=3` | 9.19-9.65 s | **4.96-5.20 s** (1.85x) |
| draft pipeline, 30 frames, `SS=3` | 22.8 s | **13.4 s** (1.70x) |
| draft pipeline, 30 frames, `SS=1` | 7.5 s | 7.3 s (unchanged: drafts never paid this) |
| `circle_spr(600, RED, 40)` alone | 1224 ms | **453 ms** (2.7x) |

Quality on a real 1080x1920 master frame: MAE 0.477/255, PSNR 42.0 dB, and the difference sits on the
halo feather (largest alpha delta 25/255 at the rim) — see `previews/glow-edge.png`.
`tests/test_glow_sprite.py` guards it: the blur must see a canvas at least 8x smaller than the sprite
(so going back to full-canvas blurring fails), the sprite keeps its bbox and solid core against an
exact reference blur, it stays deterministic and cached, and the halo survives every `REEL_SS` value.

## Unreleased — 2026-11-10 (the two monster test files, split without losing a test)

`tests/test_fixed_stage.py` was 2,434 lines and `tests/test_machine_explainer.py` 1,558; changing one
category meant scrolling past four others, and a failing line number told you nothing about which
engine phase it belonged to. Both are now split along the categories they already had:

| was | now |
|---|---|
| `test_fixed_stage.py` 2,434 | `test_fixed_stage.py` 591 (A–D geometry/clipping/audits) · `_remotion.py` 441 (E1–E2) · `_scaffold.py` 813 (E3–E5) · `_determinism.py` 430 (F–G) · `fixed_stage_support.py` |
| `test_machine_explainer.py` 1,558 | `test_machine_explainer.py` (X01–X03) · `_parity.py` (X04, P/K/R parity, archetypes, CLI) · `_remotion.py` (2 real renders) · `machine_explainer_support.py` |

Nothing was deleted, rewritten or re-marked: the Fixed Stage suite still collects exactly 18 tests and
the Machine Explainer suite exactly 13, and both were re-run green (18 in 235 s, 13 in 73 s). The
Chromium/Remotion fixtures moved to `tests/conftest.py` and became session-scoped — splitting one
module into three must not buy three `npm ci` runs and three browser boots per CI job.

Two new guards in `tests/test_test_layout.py` (in the fast `contracts` CI group): no test module past
900 lines (largest today is 813), and no `test_` function inside a `*_support.py` file — pytest never
collects those, so such a test fails silently forever. CI groups are now 104 files (contracts 33 ·
unit 26 · render 45).

## Unreleased — 2026-11-10 (N4 decided with measurements, not taste)

**The Git LFS question finally has numbers behind it.** Current `.git`: 111.5 MiB pack, 17 commits.
Every blob in history: 166.5 MB, of which **152.3 MB (91.5%) is binary** — 81.7 MB of fonts in 314
blobs for ~314 files, 63.9 MB of images in 98 blobs for 100 files. That ratio is the answer: 314
blobs for 314 files means history holds almost no duplicate binary versions, and LFS deduplicates at
the blob level, so migrating would **move** 152 MB into a second store rather than save it. A clone
that renders still downloads the assets; a clone that only wants code already has a dependency-free
answer, measured here — `--filter=blob:none` ships 0.26 MB of commit/tree graph instead of a 112 MB
pack, against lazy blob fetch.

So: no migration now, and `docs/repository-weight.md` states why, with the table, plus the recipe if
that flips (cheap to run today with 17 commits, which is exactly why the decision is recorded now).
The remaining lever is the owner's: purging `assets/poses/source` (35.6 MB) from history saves that
much in the pack and loses the master art `make poses` rebuilds cut-outs from.
`tests/test_repo_weight.py` now fails if `.gitattributes` ever gains `filter=lfs` while the doc still
says there is none — or if the decision loses its measurements.

## Unreleased — 2026-11-10 (a P draft stops supersampling pixels the encoder throws away)

**Engine P's draft was saving frames but not pixels.** A P frame is dominated by sprite work: `lib.D`
draws every shape `SS`x larger (3x), blurs it and LANCZOS-downsamples it. A draft is delivered at
540x960 — half the buffer — so the third supersample never survives, and the draft was paying for it
anyway. `REEL_SS` (1-4, validated, refused rather than clamped) makes that a knob; `--draft` asks for
`SS=1` while a caller-set value still wins, both in `render_p_segment.py` and in `run_all.py` (before
`import scenes`, which is where the factor is read).

Measured on the fixture reel: **874 -> 215 ms per frame**, a 30-source-frame segment **14.0 s -> 4.1 s**
(3.4x), the pipeline's chunk path **23.8 s -> 7.7 s** (3.1x), and a full master/draft comparison of
**27.2 s -> 4.1 s (6.6x)** for the same timeline. The picture is the same preview: MAE < 1/255 and
36-38 dB PSNR between the SS=1 and SS=3 drafts of the same frames, and the sprite itself keeps its
size and its solid pixels while only the feathering moves (tested structurally, not by eyeballing).

**A cache bug fell out of the same knob:** `build_signature` keyed chunks on source, plan, mode and
draft — not on supersampling — so a preview chunk could have been served for a render at another
factor. The key now carries `supersample`, and `tests/test_engine_p_chunks.py` fails if two factors
collide. `tests/test_p_draft_supersample.py` (12) pins the validation, the sprite geometry, and both
render paths.

What this does **not** do: a real 540x960 buffer. Engine P still composes at 1080x1920 and shrinks.
That needs the design space (1080x1920, with absolute pixel typography) separated from the device
buffer across 41 modules — scoped in `docs/preview.md`, still open.

## Unreleased — 2026-11-10 (the weights Git does not see)

**First run needs a network and ~1.5 GB of untracked state; nothing said so.** `tools/toolkit/node_modules`
is 85 MB, `.venv` 648 MB, `.git` 114 MB, and an Engine-R project another ~400 MB — all correctly
ignored by Git, none of them documented, so a fresh clone looked like it should render immediately.
`docs/repository-weight.md` now carries that table with how each piece is obtained, why the answer is
**not** to vendor a cache in Git (that would recreate the exact weight problem the ratchet measures),
and what `--prefer-offline` / the pip cache buy you on the second run.

## Unreleased — 2026-11-10 (R renders ranges — the contract said otherwise)

**"R has no range API" was false in three places.** `tools/render_scenes.py`'s docstring,
`pipeline.py`'s `--scene-cache` refusal and `docs/scene-cache.md` all told an agent that Remotion
cannot render a partial timeline, and refused the engine on that basis. `scripts/render.mjs` has
`--from-frame`/`--to-frame` (half-open, validated against the locked 30 fps timeline *before* a
browser opens) — and `render_hybrid.py` had been rendering R segments through it all along. The
capability existed and the contract denied it, which is the same class of drift as N1.

The statements are corrected, and the capability is now pinned by behavior rather than prose:
`tests/test_remotion_range.py` proves an empty range and an out-of-timeline range are refused with
sentences, and that a valid range gets past range validation into the next gate (text direction)
without drawing a frame — no Chromium, no `npm ci`.

**Why R still has no per-scene cache** is now stated with evidence instead of the wrong reason: the
scaffold has one composition (`RemotionRoot.tsx` + 46 files under `src/lib/`) that reads
`plan/beats.json` and draws every scene, so a key built from "that scene's own code" is the whole
project — every edit would invalidate every segment, and a cache that never hits is worse than none.
If the scaffold is ever split into per-scene modules, the cache becomes possible; the doc says so.

## Unreleased — 2026-11-10 (the two changelogs are consecutive, and now say so)

**`CHANGELOG.md` and `medo-motion/CHANGELOG.md` were read as duplicates — they are not.** Comparing
them section by section: 27 and 22 headings, **zero** shared, and the split is chronological — the
toolkit's own scaffold 1.0 → 2.7 (2026-11-01 → 11-09) against the studio log that starts 2026-11-09.
Merging would rewrite a versioned archive, so instead the boundary is explicit and enforced: the root
log is the live one, `medo-motion/CHANGELOG.md` is marked a frozen archive that points here,
`AGENTS.md` §10a tells an agent to write exactly one entry and never in both, and
`tests/test_changelogs.py` fails on a shared heading, an `Unreleased` section in the archive, or a
missing scope banner. The docs index names both files and their scope.

The 6.3 MB of `docs/audition` MP3s stay: they are the listening evidence for the mixes, and the new
weight ratchet (`tools/repo_weight.py`) is what stops them from growing.

## Unreleased — 2026-11-10 (N7, measured: the zod warning is the price of a patched zod)

**The zod override is not laziness, and now the numbers say so.** Every Engine-R render logs
`Version mismatch: zod: installed 4.6.7, required 4.5.4` because Remotion 4.0.539 pins `zod@4.5.4`
exactly (`@remotion/studio-shared`'s `extraPackages`), and the scaffold overrides it to `^4.6.7`.
Removing the override does silence the warning — `npx remotion versions` then prints
`All packages have the correct version.` — but the same swap re-opens a high advisory:

| scaffold | `npm audit` | `npx remotion versions` |
|---|---|---|
| `overrides: zod ^4.6.7` (current) | **0 vulnerabilities** | `zod: installed 4.6.7, required 4.5.4` |
| no override (4.5.4) | **10 high** — zod "can exhaust memory while validating oversized constrained collections" plus nine Remotion packages | `All packages have the correct version.` |

Both rows were measured here with `npm ci` on the same template, so the trade-off is evidence rather
than an assumption. The override stays; `tests/test_remotion_skill.py` now asserts it is present,
that the lockfile actually resolves zod ≥ 4.6.7 (an override that never reached the lock would leave
4.5.4 installed), and that `docs/remotion.md` still explains why. That doc carries the table, and
`medo-motion/skills/remotion/SKILL.md` tells the next upgrade to keep the override until Remotion
requires a patched zod — instead of "fixing" the warning.

## Unreleased — 2026-11-10 (repository weight has a gate, and ffprobe stops being a subset)

**Nothing noticed when the repository got heavier.** 165 MB of tracked assets (81.7 MB fonts,
64.4 MB images, 35.6 MB of `assets/poses/source`) sat behind a `.git` of ~112 MB and only a review
ever looked. `tools/repo_weight.py --check` now guards it in CI with two rules: total tracked weight
may not exceed `docs/repo-weight-baseline.json` by more than 2 MB, and any tracked file of 3 MB or
more must be named in that baseline. A new heavy asset therefore needs a deliberate `--update`,
which prints the delta so the weight change appears in the same diff as the code that caused it.
No Git LFS was added, and `docs/repository-weight.md` says why plus the exact migration recipe if
that decision ever flips. `tests/test_repo_weight.py` (7: categories, ratchet, heavy-file rule,
update-then-check, missing baseline, and the committed baseline still matching the tree).

**`tools/ffprobe_shim.py` is a fallback again, not a ceiling.** It only understood the option
subset the studio used by hand; anything else (`-of csv`, `-read_intervals`, `-show_packets`) was
silently ignored. It now execs a real `ffprobe` when one is on PATH (or named by
`MEDO_REAL_FFPROBE`) and keeps the PyAV path only as the fallback — never delegating to
`tools/bin/ffprobe` or to itself, which would loop forever. `--supported` prints the field
catalogue the fallback promises, `MEDO_FFPROBE_SHIM_ONLY=1` pins the fallback, and
`tests/test_tool_contracts.py` proves delegation, the no-self-delegation rule, the escape hatch, and
that every emitted field is declared.

## Unreleased — 2026-11-10 (hybrid: a real draft preview, and a shim that survives any cwd)

**A hybrid reel can be previewed in half the time.** `pipeline.py <project> --draft` now accepts
`--engine hybrid` (it used to exit 2) and writes `out/hybrid-draft.mp4` at 540×960 / 15 fps from the
same `plan/hybrid.json`: P bases take `--draft` (every other source frame), K bases and K overlays
take `--fps 15 --scale 0.5`, and masks are generated on the 540×960 canvas (`drawbox` coordinates
scaled, `color=540x960:r=15`). Draft frame `k` is source frame `2k`, so the reel keeps its duration
to the millisecond and the soundtrack would still line up if you went back to the master. An R base
is refused before rendering, and a draft refuses `--qa`/`--qa-report`/`--audio` and any segment
shorter than two source frames. Measured on a 60-frame (2.000 s) plan — P base plus a masked K
overlay — the master took 42.1 s and 516 KB, the draft 23.5 s and 177 KB (**1.79×**), with matching
picture: frame 0 mean brightness 35.0 (master) vs 35.1 (draft) and draft frame 15 identical to
master frame 30.

**`tools/bin/ffprobe` no longer depends on where you stand.** `setup.sh` wrote the shim with
`$(command -v "$PY")`, which is relative when setup is run as `.venv/bin/python`; every tool it
launched from a project directory then died with `.venv/bin/python: not found` — exactly how the
hybrid renderer is invoked. The shim now bakes in an absolute interpreter, and
`tests/test_repo_hygiene.py` proves it answers from a foreign working directory.

Contract updated in both directions: `AGENTS.md` step 6 and `medo-motion/templates/HYBRID.md` name
the draft path and its 15 fps exception, `docs/preview.md` and `docs/hybrid.md` carry the numbers.
`tests/test_hybrid_draft.py` (15: canvas, frame anchoring, every engine's flags, mask canvas, stack
rate, and the three guards) plus two pipeline tests (routing, and one real half-size render).

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
