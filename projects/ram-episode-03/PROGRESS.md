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
| Word-level VO alignment | ⬜ | Blocked: no speech-alignment runtime/service is available in this execution environment; no estimated timestamps will be committed |
| Caption renderer | 🟡 | Added reusable one-word renderer, exclusive word timing, overlap/order validation, and S01 integration; actual timeline remains empty pending measured alignment |
| Caption unit tests | ✅ | Local Node test passed; preview workflow now runs the same test before rendering |
| Technique draw + project-specific lint | ⬜ | Not independently run for this episode project |
| S02–S10 | ⬜ | Wait for S01 visual direction approval |
| Full render / mix / QC | ⬜ | Not started |

## Validation notes

- Latest S01 preview run 41487395114 completed successfully, including dependency installation, Chromium resolution, frame rendering, contact-sheet generation, and artifact upload.
- Latest full renderer validation run 41487395015 completed successfully.
- Latest validated commit: `ba0df718875465cc7f425bc3b0fb033ac9007c59`.
- The source WAV is intentionally not committed. Place it locally at `assets/vo/episode-03-ram.wav`.
- Scene boundaries remain provisional editorial groupings from silence midpoints, not word-level alignment.
- A successful render proves technical execution, not final visual approval.
- Captions must be timed from word-level alignment against the actual WAV; do not estimate word timing from scene boundaries or silence midpoints.
- S01 now calls the caption renderer, but `captions-s01.js` intentionally contains no words until measured timestamps are available. The source WAV remains local and is not uploaded to GitHub.
- The caption renderer draws one RTL word directly over the scene with shadow for contrast; it creates no border, panel, pill, or background box.
