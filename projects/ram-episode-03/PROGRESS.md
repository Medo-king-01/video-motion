# PROGRESS — RAM Episode 03

| Stage | State | Evidence |
|---|---|---|
| Script + visual direction | ✅ | Approved by Medo |
| VO measurement | ✅ | 70.520 s, 24 kHz, 2116 frames @ 30 FPS |
| 10-scene editorial map | 🟡 | Grouped from silence midpoints; not word-level alignment |
| K engine scaffold | ✅ | Copied from current repository template |
| S01 prototype code | ✅ | Rendered successfully in GitHub Actions |
| Repository CI | ✅ | Static checks, unit tests, lint fixtures, brand audits, and P/K/R/Hybrid real renders passed in run 41487395015 |
| S01 render | ✅ | 0–12.358 s, 30 FPS, 0.5 scale; render step passed in run 41487395114 |
| S01 contact sheet | ✅ | Generated and uploaded as artifact `ram-episode-03-s01-preview` (artifact 13162427862) |
| S01 visual review | 🟡 | 8GB → 16GB → 32GB sequence is readable; composition remains sparse and mostly static. Needs visual refinement and Medo's approval |
| Word-level VO alignment tool | 🟡 | Added an open-source WhisperX Arabic transcription + forced-alignment CLI; actual WAV processing is pending a safe execution/transfer path |
| Caption renderer | 🟡 | Added reusable one-word renderer, exclusive word timing, overlap/order validation, and S01 integration; actual timeline remains empty pending measured alignment |
| Caption unit tests | ✅ | Local Node test passed; preview workflow runs the caption tests and WhisperX output-parser unit tests |
| Technique draw + project-specific lint | ⬜ | Not independently run for this episode project |
| S02–S10 | ⬜ | Wait for S01 visual direction approval |
| Full render / mix / QC | ⬜ | Not started |

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
- Offline alignment fallback (`aeneas`) did **not** install cleanly in this sandbox (C-extension build failure); espeak-ng also absent. Word-level alignment still pending — recommended path remains running `tools/align_audio.py` on a machine with Hugging Face access.

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
