# `majedphotos/video-ad-editor`: fit for the Medo Motion studio

**Reviewed:** 2026-11-04 · **Upstream:** [`majedphotos/video-ad-editor`](https://github.com/majedphotos/video-ad-editor) (`v6.3.0`, commit `a69492df61c2bd3d3e8c85af16266c70304ace0a`, **MIT License** © 2026 Majed Alzaabi).

## Executive summary

`majedphotos/video-ad-editor` is an MIT-licensed Arabic video and motion-graphics plugin for Claude Code built around two pipelines:
1. **A talking-head / podcast / montage editor** (`scripts/00..41`, Whisper transcription, jump-cut silence removal, face-tracking Swift binaries, CapCut export, and multi-cam layouts).
2. **A Canvas2D + Three.js motion-graphics engine** (`motion/engine.js`) with strong Arabic typography rules, phrase-chunk captions, isometric cutaway hardware/machine explainers (`iso-kit`), shutter-window motion blur, and real-scale mobile grid preview QA.

**Architectural decision:** Do **not** install `video-ad-editor` as a plugin, do **not** add its `puppeteer-core` / `engine.js` runtime as a fourth engine, and do **not** import its talking-head jump-cut or macOS-only Swift scripts. Instead, extract the **six genuinely net-new capabilities** that strengthen Medo's explainer/tech/presenter reels and implement them natively across our existing **P / K / R** engines and `tools/` under clean MIT attribution (`assets/CREDITS.md`).

---

## 1. What `video-motion` already had (and keeps stronger)

| Area | `video-motion` native capability | Why we keep ours |
|---|---|---|
| Render engines | **P** (Python/OpenCV/HarfBuzz), **K** (Canvas2D + Playwright), **R** (Remotion/React), and sequential **Hybrid** (`tools/render_hybrid.py`) | Already covers procedural presenter reels, kinetic Canvas, and React scenes under one `1080×1920` contract without adding `puppeteer-core`. |
| Script-to-VO alignment | `tools/caption_align.py` (`faster-whisper` + dynamic-programming `dp_align` + `speech_regions` + `snap_and_hold`) | Aligns ASR timestamps directly to the approved Arabic script words instead of trusting raw ASR spelling on screen. |
| Brand & contrast lock | `medo-motion/brand/brand.json` (12 locked colours + `ink_shadow`), `brand_check.py`, `contrast.py` | Enforces WCAG contrast and forbids off-palette hexes across all three engines. |
| Type & presenter kit | 21 OFL font families (`assets/fonts/`), 49 presenter poses (`assets/poses/`), 275 animated icons, 15 procedural SFX, 14 transitions, 12 backgrounds | Already verified offline and wired into `reel_lint.py` and `stage_gate.py`. |
| Post-render & layout QA | `tools/media_qa.py`, `tools/layout_audit.mjs` (K), `tools/layout_audit_p.py` (P), `tools/stage_gate.py` | Enforces `-14.5 ± 0.3 LUFS`, `-1.5 dBTP`, `faststart`, frame-0 presence, safe zones (`L00`–`L03`), and reverse-seek determinism (`R01`/`R02`). |

---

## 2. Six native studio upgrades adopted from `video-ad-editor`

### Upgrade 1 — Unicode-Safe Arabic Kashida, Mixed English Run Order & Word-Slot Ticker (`K` + `P`)
- **Fixed multi-word Latin/number ordering inside RTL lines:**
  - Previously, `layoutWords` (`templates/render/lib/arabic.js`) stepped every space-split word right-to-left, turning `"جرّب Claude Code النهاردة"` into `"Code Claude"` visually, and `arabic_shape.py:_runs` gave spaces between two English words `base_rtl=True`, reversing multi-word English phrases in Engine P as well.
  - Added Unicode UAX #9 `N1` neutral-run merging in `arabic_shape.py:_runs` plus `visualWordOrder` (`lib/arabic.js`) and `visual_word_order` (`arabic_shape.py`), keeping `"Claude Code 2.0"` or `"DDR5 16GB"` in natural left-to-right visual order inside RTL lines while preserving `logicalIndex` for spoken-order staggers.
- **Unicode `ArabicShaping` Kashida (`kashidaSlots`, `insertKashida`, `stretchKashida`, `drawKashida` in `K`; `kashida_slots`, `insert_kashida`, `stretch_kashida`, `draw_kashida` in `P`):**
  - Inserts tatweel (`ـ`, `U+0640`) **only** after dual-joining letters (`Joining_Type=D`), **never** after right-only letters (`ا أ إ آ د ذ ر ز و ؤ ة ء ى`), **never** between a base letter and its harakat/shadda (`تحـــرّك`, never `تحرّـــك`), and **never** inside mandatory Lam-Alef ligatures (`لا / لأ / لإ / لآ`).
  - Pairs integer tatweel steps with a capped residual `scaleX <= 1.06` so animated kashida stretches glide smoothly without discrete width jumps.
  - Added `fixRuqaaTaaMarbuta` / `fix_ruqaa_taa_marbuta` (`ZWJ` before isolated `ة` after right-only letters for calligraphic Ruqaa faces).
- **Masked Vertical Word-Slot Ticker (`drawTextSlot` in `captions.js`, `draw_text_slot` in `captions.py`):**
  - Fixed-window slot where outgoing words slide upward inside a dot-padded clip box while incoming words rise in on beat cues, instrumented for layout audit.

### Upgrade 2 — Phrase-Chunk Captions (`2–4` words), Glue-Word Cohesion, Calm `still` Mode & `hideRanges` (`K` + `P`)
- **`groupCaptionChunks` (`captions.js`) / `group_caption_chunks` (`captions.py`):**
  - Groups measured VO word timings into `2–4` word single-line RTL phrases, splitting on pauses `> 0.45s` or punctuation while **never orphaning Arabic glue particles** (`في`, `من`, `على`, `إلى`, `عن`, `مع`, `مش`, `اللي`, `عشان`, etc.) at the end of a chunk.
- **`drawPhraseCaption` / `draw_phrase_caption`:**
  - Keeps Medo's **unboxed** brand-caption contract (rejecting `video-ad-editor`'s default rounded capsule box), highlights the active spoken word in brand accent (`salmon` on dark, `red` on light), dims upcoming words in the phrase (`0.56` alpha), supports `still: true` calm fade-only mode, and supports `hideRanges` / `hide_ranges` (`[[start, end], ...]`) so captions automatically step aside whenever hero kinetic typography already displays the spoken words on screen.

### Upgrade 3 — Brand-Locked Isometric Cutaway "How It Works" Kit (`P` + `K` + `R`)
- **`medo-motion/templates/procedural-reels/iso_kit.py` (P)** and **byte-identical `medo-motion/templates/render/lib/iso-kit.js` + `medo-motion/templates/remotion/src/lib/iso-kit.js` (K & R):**
  - Built specifically for Medo's hardware/laptop/tech explainers (CPU, RAM, SSD, cooling fans, USB-C PD chargers, routers, pipelines).
  - Provides deterministic 2:1 / `30°` isometric projection (`isoProject` / `iso_project`), 3-layer cutaway sorting (`back` housing → `mid` internal active parts → `front` cutaway lip), `slab`, `cylinder`, `ring` (with animated rotor blades), `coil`, and `wire` (with animated signal/heat pulse `flowP`), progressive ink-stroke reveal (`reveal = 0..1`), and semantic roles mapped **exclusively** to the 12 locked `brand.json` colours.

### Upgrade 4 — Deterministic Shutter-Angle Temporal Motion Blur (`P` + `K` + `R`)
- **`shutter_blur` (`procedural-reels/lib.py`)** and **byte-identical `shutter-blur.js` (`render/lib/` & `remotion/src/lib/`):**
  - Evaluates symmetric sub-frame exposures across `[t - shutter/(2*fps), t + shutter/(2*fps)]` inside explicit fast-camera `windows` (`[(start, end), ...]`), leaving calm frames at `1×` cost and keeping every frame a pure stateless function of `t` (so chunked rendering and `--replay` determinism pass unchanged).

### Upgrade 5 — Mobile Grid & Platform Chrome Preview (`tools/phone_preview.py`), Right-Rail `L04` Audit, and ASR Sanity Auditor (`tools/asr_check.py`)
- **`tools/phone_preview.py` (`make phone-preview`):**
  - Generates a `1360×920` retina QA sheet from any rendered MP4 or cover PNG showing: (1) `9:16` Reels/TikTok player with translucent HUD + right-rail button column (`x: 940..1080, y: 1100..1500`) + bottom scrub chrome (`y: 1500..1920`), (2) `3:4` profile grid crop (`y: 240..1680`), (3) `1:1` square feed crop (`y: 420..1500`), and (4) true `13.5%` mobile 3-column grid tile (`146×195`) with quantitative Sobel edge-intrusion diagnostics (`P01`–`P03`).
- **Opt-in `L04` Right-Rail Platform UI Audit (`--platform-ui` in `layout_audit.mjs` & `layout_audit_p.py`):**
  - Flags right-aligned RTL `content` or `caption` ink intruding into the social action button rail (`x: 940..1080, y: 1100..1500`).
- **`tools/asr_check.py` (`make asr-check`, integrated into `tools/stage_gate.py` `G02`):**
  - Audits `plan/word-timings.json` or `cache/scene-measurements.json` against `out/vo24.wav` and `plan/script.md` for known Arabic/English Whisper silence hallucinations (`A01`), `4×` word stutter loops / `compression_ratio > 2.4` (`A02`), inverted/overlapping/stretched word bounds (`A03`), and `>= 1.0s` gaps containing `>= 0.6s` of untranscribed voiced audio (`A04`).

### Upgrade 6 — 3D Extruded Explainer Icon & Symbol Tiles (`tile3d` across `P` + `K` + `R` + Three.js r187)
- Generalized from `logo3d.html` + `41_logo3d.js` into a **brand-locked explainer visual primitive** for icons, hardware/tool badges, protocols, and user-supplied symbols (never an unrequested channel/studio watermark per `AGENTS.md` Rule 1):
  - **`medo-motion/templates/procedural-reels/tile3d.py` (`sample_tile_pose`, `draw_tile3d`)**: evaluates keyframed 3D position/tilt (`rx, ry, rz`) + sinusoidal idle float + periodic diagonal specular gloss sweep as a pure function of `t`, painter-sorts extruded rounded bevel quads with directional + `salmon` rim shading, and warps the front icon/symbol sprite via OpenCV perspective homography (`cv2.getPerspectiveTransform` + `cv2.warpPerspective`).
  - **Byte-identical `tile3d.js` (`render/lib/` & `remotion/src/lib/`)**: zero-WebGL 2D-Canvas perspective extruded tile renderer with exact numeric pose parity to Python (`sampleTilePose`).
  - **Byte-identical `three-tile3d.js` (`render/lib/` & `remotion/src/lib/`)**: optional WebGL Three.js r187 PBR `ExtrudeGeometry` tile scene builder plugging directly into `createThreeLayer` (`three-layer.js`) with synchronous `update(t)` and deterministic `ResourceScope` disposal.

---

## 3. What we intentionally rejected (and why)

| Upstream item | Reason rejected |
|---|---|
| macOS Swift Vision binaries (`facetrack.swift`, `handpose.swift`, `personmask.swift`, `hdr2sdr.swift`) | Apple-only (`Vision.framework` / `CoreImage`); breaks Linux & CI portability. |
| Talking-head jump-cut editor (`03_cut_plan.py`), 16:9 multi-cam podcast (`36_multicam.py`), CapCut exporter (`40_capcut.py`) | Outside Medo's vertical procedural/kinetic/presenter studio scope (`1080×1920 @ 30fps`). |
| Unrequested channel/brand watermarks (vs `tile3d` explainer symbols) | `logo3d.html` was adapted strictly as `tile3d` for **in-scene explainer icons/symbols**; `AGENTS.md` Rule 1 still forbids inventing an on-screen channel/studio logo (our repo emblem in `docs/assets/studio-{banner,mark}.svg` is GitHub UI chrome only). |
| Kuwaiti dialect copy & `#F0EBE0` / `#D97757` Claude palette defaults + `60fps` render clock | Violates `AGENTS.md` Rule 2 (Egyptian Arabic), the locked 12-colour `brand.json` palette, and the locked `30fps` timeline contract. |
| Boxed capsule `card` / `chunk` caption backgrounds | Conflicts with Medo's unboxed brand-caption rule (`captions.js` / `captions.py`). |
| Bundled `moves/previews/*.mp4` preview archive & mixed-license move inspirations (`CREDITS.md` entries referencing Remotion License / Hippocratic 2.1) | Violates `.gitignore` (`*.mp4`), `AGENTS.md` Rule 13 ("studio is a tool, not a video archive"), and our strict OFL/MIT/Apache-2.0 clean-room licensing policy. |
