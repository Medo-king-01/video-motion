# PROGRESS — RAM Episode 03

| Stage | State | Evidence |
|---|---|---|
| Script + visual direction | ✅ | Approved by Medo |
| VO measurement | ✅ | 70.520 s, 24 kHz, 2116 frames @ 30 FPS |
| 10-scene editorial map | ✅ | All 10 bounds from measured Whisper word alignment + silence-midpoint cuts (`src/data.js`, `plan/beats.json`) |
| K engine scaffold | ✅ | Copied from current repository template |
| S01 (approved v6) | ✅ | Measured sync + SFX + style approved by Medo; frozen, untouched |
| Word-level VO alignment tool | ✅ | Local faster-whisper (Whisper small CT2 int8, npm weights) run on the real WAV; all 10 scenes measured (149 words) |
| Caption renderer + tests | ✅ | One-word unboxed renderer; `validateWordTimeline` passes for all 10 scenes; checked in rendered frames |
| S02–S10 scenes | ✅ | 9 new modules built on shared `ramkit.js`, alternating light/dark, word-timed reveals; 0 page errors |
| Full SFX mix | ✅ | 63 global cues (`plan/full-sfx-cues.json`), duck 0.30, two-pass loudnorm |
| Full render / mix / QC | ✅ | `artifacts/episode-03-full-final.mp4` — 2116 frames, all QA gates pass (see below) |

## Full episode — FINAL (2026-11-02)

**Deliverable:** `artifacts/episode-03-full-final.mp4` (33.6 MB). Caption-check sheet: `artifacts/episode-03-caption-check.jpg`.

Medo approved S01 v6 ("يا سلام بقا مظبوط الحمد لله كمل يا بطل") and asked to continue. S02–S10 were built with the same measured-sync pipeline and the approved visual language, then the whole episode was rendered, mixed, and QC'd.

**Measured scene map** (`src/data.js`, regenerated `plan/beats.json`, 149 words total):

| Scene | Module | Span (s) | Words | Theme |
|---|---|---|---|---|
| S01 | ram-intro | 0 – 8.433 | 18 | dark |
| S02 | ram-question | 8.433 – 12.358 | 9 | light |
| S03 | ram-explain | 12.358 – 19.951 | 17 | dark |
| S04 | ram-choose | 19.951 – 22.042 | 5 | light |
| S05 | ram-8gb | 22.042 – 33.44 | 23 | dark |
| S06 | ram-16gb | 33.44 – 45.254 | 19 | light |
| S07 | ram-32gb | 45.254 – 57.469 | 26 | dark |
| S08 | ram-bigger | 57.469 – 62.41 | 12 | light |
| S09 | ram-budget | 62.41 – 67.0 | 11 | dark |
| S10 | ram-cta | 67.0 – 70.52 | 9 | light |

**Alignment:** per-scene faster-whisper runs (`vad_filter=False`, repetition penalty, DP-align onto the BRIEF script), onsets silence-snapped to the speech envelope. S06/S07 needed a no-prompt retry (the exact-script prompt made Whisper skip slice openings). S09/S10 cut corrected to 67.0 s (the old 68.386 cut landed inside S10 speech). S05 word order sorted + strict-monotonic guard. S01 timeline frozen from the approved v6 (`artifacts/s01-v6-measured-words.json`) — not re-snapped.

**Visuals:** shared `src/lib/ramkit.js` (identical RAM module design across all scenes; brand mesh + per-scene grid + 30 dust; one impact per scene kept above the caption safe line). Card/element reveals baked at measured spoken-word times. Layout fixes from contact-sheet review: capacity labels kept on the red circle (white) with a correctly scaled label gap; S06 headline/cards/subline de-collided; S08 grow-pulse removed so its label never leaves the circle; S10 headline raised clear of the circle.

**Audio:** 63 global SFX cues mixed under the VO (`tools/sfx_kit.mix`, duck 0.30). The original VO WAV has a non-standard header that scipy rejects, so it was re-encoded to `out/vo24.wav` for mixing. Two-pass loudnorm master `cache/full-mix-final.wav` (−14.52 LUFS / −1.49 dBTP). AAC encoding raised the true peak, so the final audio was re-mastered with a true-peak limiter (TP target −1.8) and the audio stream re-encoded (video copied) → `cache/full-mix-tp2.wav`.

**Final QC (all gates pass):**
- Duration **70.533 s = 2116 frames @ 30 FPS** (VO length; ceil(70.52×30), same convention as approved S01).
- Resolution **1080×1920**, H.264 + AAC 48 kHz stereo.
- Integrated loudness **−14.54 LUFS** (gate −14.5 ± 0.3). ✅
- True peak **−1.64 dBTP** (gate ≤ −1.5). ✅
- Video bitrate **3.61 Mbps** (gate ≥ 2.5). ✅
- Burned-in Arabic captions: one spoken word at a time, unboxed, Cairo 76 @ y1455, theme-correct color; verified against the WAV in 10 rendered frames (`artifacts/episode-03-caption-check.jpg`). ✅
- No logo / series text / chip. ✅
- Smoke test: 30 frames + fix-checks rendered with **0 page errors**; all 10 scene modules import + draw. ✅

**Tests:** `node test/captions.test.js`, `validateWordTimeline` for all 10 scenes, and `python3 test/test_align_audio.py` passed.

## Local sandbox readiness — 2026-11-02

- `tools/setup.sh` + `tools/doctor.py`: **READY** (Pillow/numpy/scipy/OpenCV/PyAV/HarfBuzz/FreeType, ffmpeg + ffprobe shim via `tools/bin` on PATH, Chromium 138 via `tools/chromium.mjs`, Cairo fonts, brand lock).
- Full repo regression suite: **259 pytest tests passed** locally.
- Project tests: `node test/captions.test.js` and `python3 test/test_align_audio.py` passed locally.
- S01 rendered locally with engine K: 371 frames @ 30 FPS, 0.5 scale (`cache/s01/`), contact sheet `artifacts/s01-contact-sheet.jpg` + silent motion preview `artifacts/s01-preview-silent.mp4` (12.37 s, no VO, no captions — review artefacts only, not a deliverable). Both are git-ignored.
- Visual state matches the earlier CI review: 8→16→32 sequence readable; composition still sparse and mostly static. **S01 visual approval still pending.**
- Alignment-model availability, measured this session (not assumed):
  - `huggingface.co` — TLS connect fails (blocked).
  - GitHub release assets (`objects.githubusercontent.com`) — blocked (302 → TLS fail).
  - Git LFS (`media.githubusercontent.com`) — blocked.
  - Reachable: `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`.
  - Every `ggml-*.bin` Whisper weight found in public GitHub repos is a 133–134-byte **LFS pointer**, not real weights.
  - ⇒ WhisperX / faster-whisper / whisper.cpp model weights **cannot be fetched in this sandbox**.
  - Sandbox compute: 2 vCPU, ~3 GB RAM, ~18 GB free disk; gcc 12 + make present; cmake/espeak not installed (installable from PyPI / source).
  - Viable word-alignment paths: **(A, recommended)** Medo runs `tools/align_audio.py` on a machine with Hugging Face access and uploads the aligned JSON + the WAV; **(B, offline fallback to attempt)** build espeak-ng from GitHub source + `aeneas` (PyPI) for DTW forced alignment against the known script — a real measured alignment, but lower accuracy for Egyptian dialect, so it must be validated against the audio before any caption is accepted.
- **VO received + verified (2026-11-02):** Medo uploaded the recording wrapped as base64 JSON (`audio_data.json`, original `one.wav`). Decoded to `assets/vo/episode-03-ram.wav` — `pcm_s16le`, mono, 24000 Hz, **70.520 s**, an exact match to `plan/beats.json` (2116 frames, 10 scenes). Master `out/vo24.wav` prepared. The WAV itself stays local / git-ignored (not committed), per the privacy rule.
- **Preview delivery fix:** the review artefacts were git-ignored, so they never reached Medo (only the tracked `PROGRESS.md` did). Force-added + committed `artifacts/s01-contact-sheet.jpg` and `artifacts/s01-preview-silent.mp4` (commit `3479adf`) and pushed the branch so the S01 preview is now deliverable.
- **WhisperX — empirically confirmed blocked (2026-11-02):** `whisperx 3.8.6` installs fine from PyPI, but running `tools/align_audio.py` on the real WAV fails at model download: `SSLError … huggingface.co … TLS/SSL connection has been closed (EOF)`. So the package works; the Hugging Face model weights are unreachable here.
- **Offline alignment path BUILT from source and running (2026-11-02):** to satisfy "try another path here", assembled a fully offline forced-alignment stack using only allowed hosts: CPython 3.11 headers (codeload) → generated `pyconfig.h` via `configure`; built **espeak-ng 1.52.0** with CMake (shared lib + Arabic phoneme data); installed **aeneas 1.7.3** (patched `wavfile.py` `fromstring`→`frombuffer` for NumPy 2.x; added `Language.ARA→ar` to the espeak-ng TTS map); wrote an ffprobe shim wrapper for aeneas. Driver: `/tmp/aeneas_align.py` (aeneas API, `tts=espeak-ng`, voice `ar`).
- **Alignment quality — honest caveat:** aeneas+espeak-ng DTW produces word timings, and S01–S03 land reasonably, but there is **cumulative drift** over the 70.5 s audio (later scenes compress toward the end; 42/149 words near-zero). It also exposed that `plan/beats.json` silence-midpoint scene bounds are inaccurate. So this is a **draft**, not a validated caption track.
- **S01 v3 (2026-11-02):** module reveals re-synced to the spoken numbers ("8"≈4.96 s, "16"≈7.72 s, "32"≈9.64 s); `src/captions-s01.js` populated from the aeneas draft (status `aeneas-draft-pending-validation`); rendered `artifacts/s01-v3-synced-preview.mp4` **with the VO + captions** for Medo to judge sync. Caption timeline passes `validateWordTimeline`.
- **Recommended reliable path remains:** run `tools/align_audio.py` (WhisperX) on a machine with Hugging Face access for accurate word timing; the aeneas draft is a stopgap for visual review only.

## S01 v6 — measured Whisper sync + SFX (2026-11-02)

- **OpenAI Whisper attempt (as requested):** cloned/installed `openai-whisper` from the GitHub project. The Python package imports, but `whisper.load_model('tiny')` fails with `URLError: TLS/SSL connection has been closed (EOF)` because model weights are fetched from `openaipublic.azureedge.net`, which is blocked here. So the official OpenAI model CDN is not usable in this sandbox.
- **Working local ASR path found:** npm hosts a real CTranslate2 int8 conversion of Whisper small split across four packages: `@skillninja/shortmovie-telop-model-p0` … `p3`. Downloaded all four tarballs from `registry.npmjs.org`, reassembled `model.bin`, and verified SHA-256 `ca732cb1379efc49417d028465f543d83a39de2c61f3027678de103dc404ce73`. Added reproducible fetcher: `tools/fetch_whisper_ct2_npm.py`.
- **Measured alignment:** installed `faster-whisper==1.2.1` + `ctranslate2`, loaded the local model with `local_files_only=True`, and transcribed the real VO with `word_timestamps=True`. Added `tools/align_whisper_local.py`. S01 was measured separately with the approved S01 text as prompt; the transcript matched the 18 script words.
- **Aeneas draft rejected:** the previous aeneas/espeak timings were not used. They placed words over silence and were rejected in review.
- **S01 corrected timing:** spoken numbers are approximately `8` @ 3.38s, `16` @ 5.48s, `32` @ 7.10s. S01 speech ends around 8.08s; scene cut moved from the old 12.358s to 8.433s, inside the measured silence before S02. Module reveals, captions, impact, scan, and SFX cues now use these measured onsets.
- **Caption safety:** first-word onset snapped to measured silence-end (0.865s) instead of Whisper's early 0.74s. Impact ring radius limited so it does not cross the caption safe line.
- **SFX:** procedural kit mixed under VO with lighter ducking (`duck=0.30`): sub/whoosh open, pop on each module reveal, impact at 7.70s, zip at 8.08s. Cue sheet: `plan/s01-sfx-cues.json`.
- **Final S01 preview:** `artifacts/s01-v6-final-preview.mp4` — 1080×1920, 30fps, 253 frames, 8.433s, VO+SFX, burned-in one-word Arabic captions. QC: integrated loudness **-14.51 LUFS**, true peak **-1.53 dBTP**, bitrate **≈4.07 Mbps**. Caption check sheet: `artifacts/s01-v6-caption-check.jpg`. Measured word JSON: `artifacts/s01-v6-measured-words.json`.
- **Tests:** `node test/captions.test.js`, S01 `validateWordTimeline`, and `python3 test/test_align_audio.py` passed.
- **Next:** Medo reviews v6 sync. If approved, apply the same measured Whisper path to S02–S10 and re-derive all scene bounds before full render.

## Validation notes

- Latest S01 preview run 41487395114 completed successfully, including dependency installation, Chromium resolution, frame rendering, contact-sheet generation, and artifact upload.
- Latest full renderer validation run 41487395015 completed successfully.
- Latest validated commit: `ba0df718875465cc7f425bc3b0fb033ac9007c59`.
- The source WAV is intentionally not committed. Place it locally at `assets/vo/episode-03-ram.wav`.
- Scene boundaries remain provisional editorial groupings from silence midpoints, not word-level alignment.
- A successful render proves technical execution, not final visual approval.
- Captions must be timed from word-level alignment against the actual WAV; do not estimate word timing from scene boundaries or silence midpoints.
- S01 now calls the caption renderer, but `captions-s01.js` intentionally contains no words until measured timestamps are available. The source WAV remains local and is not uploaded to GitHub.
- Added `tools/align_audio.py`, `tools/requirements-align.txt`, and `tools/README.md`. The CLI uses WhisperX Arabic ASR + forced alignment, CPU/int8 by default, and emits measured word intervals as JSON.
- Added parser/timeline unit tests. These validate result handling only; they do not execute WhisperX or prove recognition/alignment accuracy.
- No cloud workflow currently transfers the WAV. GitHub `workflow_dispatch` cannot accept a binary audio attachment, and the audio must not be placed in a public repository artifact or exposed through a public URL. A secure transfer mechanism must be chosen before remote CI can process the source recording.
- The caption renderer draws one RTL word directly over the scene with shadow for contrast; it creates no border, panel, pill, or background box. Its anchor is set to the brand caption safe line (Y=1455) and uses the brand paper token.
