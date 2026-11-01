# medo-motion — Reel Studio (works with ANY coding agent)

> **Read this file first, every session.** It is the operating contract.
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
| 4 | **Medo poses** | 2–4 PNG/JPEG images (wave / think / point) on a clean background |

Ask **once, in a single message**, for whatever is missing. Then decide the rest
yourself and say what you decided. Never run a multi-step interview.

If the VO is missing you may *offer* a placeholder timing track, but do not build a
finished video on guessed timing without saying so.

## 2. Hard rules — do not deviate

1. **No logo. No series name. No episode chip. No empty logo ring.**
   This is a studio, not a named series: Medo tells you what to make and you make it.
   Never ask for a logo or a series title, never invent one, never leave a placeholder
   circle "for the logo" on screen. End cards are **typographic only**.
2. **The brand is locked** (palette, Cairo, safe zones, loudness, Egyptian dialect).
   `medo-motion/brand/BRAND.md` + `brand/brand.json` are the source of truth: **exactly 12
   colours** (palette v2) plus the derived `ink_shadow`. Never re-ask about colours/fonts and
   never improvise outside the palette — `brand_check.py` fails the build if you do.
   **Type:** `assets/fonts/fonts.json` is the whole allowed set — 14 families, all SIL OFL 1.1
   (free, commercial, no on-screen attribution). Cairo stays the default for on-screen Arabic and
   Inter for Latin; every other family is a *role* (hook, telemetry, quote…) and at most two families
   share a scene. `docs/fonts.md`; `make fonts` installs, `make fonts-sheet` shows them.
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
   `medo-motion/motion/easings.json`, keyframe timelines played by `lib/motion.js` (K) or
   `motion.py` (P). The same timeline JSON must render identically in both engines —
   `tests/test_motion.py` enforces it. `docs/motion.md` maps motion.dev recipes onto it and
   `tools/theatre_import.py` converts a Theatre.js state export.
8. **Medo is a pose library, not a PNG per scene**: use `presenter.py` (P) / `lib/presenter.js` (K)
   with the slugs from `assets/poses/poses.json` (`neutral`, `explain`, `point`, `welcome`, `wave`,
   `clap`, `like`, `thinking`, `thinking-deep`, `puzzled`, `sad`, `shocked`, `walk`, `run`, `waiting`,
   `warm`, `phone`, `unfold`, `point-up`, `seated-talk`, plus the close-ups `close-neutral`,
   `close-explain`, `close-point`, `close-thinking` — full shots anchor on the ground line, close-ups
   on the top guide, so a cut between them is a camera push-in). Never edit
   the cut-out PNGs by hand — rebuild with `make poses`. `docs/presenter.md`.
9. **Cuts and sound are catalogue-driven**: scene changes use `transition.py` / `lib/transition.js`
   (`medo-motion/motion/transitions.json`) and every hit comes from `sfx.py` (`BANK` + `CATALOG`) via a
   cue sheet — never a hand-rolled mask or an unlicensed audio file. `docs/transitions.md` and
   `docs/audio.md` are the references; `make transitions` and `make sfx` produce the QA artefacts.
10. **Draw the moves; then lint them.** Do not choose transitions/camera moves from memory — that is
   how every reel ends up with the same fade-up and push-in. Draw from the measured library into the
   project: `python3 tools/techniques.py --draw --from-plan plan/beats.json --json plan/techniques.json`
   (`assets/techniques.json`, 41 moves, each written against this studio's own primitives). Build what
   the concept can carry, reroll at most twice, never add a move the draw did not give you.
   Before a render, the plan must pass `python3 tools/reel_lint.py projects/<slug> --scan-code`
   (letters/words on screen, dwell per word, grid-locked cuts, text-free stretch, banned looks).
   Rules, numbers and the conflicts we resolved: `docs/craft.md`. Library: `docs/techniques.md`.

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

## 4. First run on a machine

```bash
bash tools/setup.sh          # installs python + node deps, ffmpeg, fonts, chromium
python3 tools/doctor.py      # prints READY / BLOCKED for every capability
python3 tools/selftest.py    # doctor + unit tests + a few real frames (the real proof)
```

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
   `assets/vo/`, the poses into `assets/poses/`, the script into `plan/script.md`.
   Then prepare the two files the engines expect:

   ```bash
   # VO master: 24 kHz mono PCM16 (mix.py reads out/vo24.wav)
   ffmpeg -y -i assets/vo/<voice>.mp3 -ac 1 -ar 24000 -c:a pcm_s16le out/vo24.wav
   ffprobe -v error -show_entries format=duration -of json out/vo24.wav   # duration = video duration

   # Poses -> cutouts named exactly medo_wave / medo_think / medo_point
   UPLOADS=assets/poses python cutout.py white <wave.png> medo_wave
   UPLOADS=assets/poses python cutout.py green <think.png> medo_think
   UPLOADS=assets/poses python cutout.py white <point.png> medo_point
   ```

   Until the poses exist, engine P draws a silhouette marked `PLACEHOLDER` — that is
   allowed for a prototype, but declare it in the delivery.
2. **Timing — there is no target length.** The video is exactly as long as the voice-over, and
   every number derives from it. Measure it, don't guess it:

   ```bash
   python3 tools/vo_length.py out/vo24.wav --json plan/beats.json   # duration + scene bounds
   python3 tools/vo_length.py out/vo24.wav --check projects/<slug>  # must print OK before rendering
   ```

   Scene boundaries = midpoint of silences; `DURATION` (engine K, `src/data.js`) and `B` (engine P,
   `scenes.py`) end exactly on the VO's duration; the SFX bus and the mix are cut to it.
   `tests/test_vo_length.py` fails if any doc or template reintroduces a fixed length.
3. **Engine choice** — see §6. One engine per video.
4. **Scenes** — build one scene, render 3 stills, then a 4–8 frame contact sheet.
   Do not go to "production" from the first attempt.
5. **Assets** — code → AI → search, respect the ladder and the licence log.
6. **Render** — chunked (engine P) or Playwright (engine K), then mix, then master.
7. **QC** — ≥3 visual rounds (contact sheets), probe the MP4, check loudness, check the
   Arabic with your eyes, run `brand_check.py`.
8. **Deliver** — the master MP4 + an 8–10 line Arabic message (§8).

## 6. Which engine

| Situation | Engine |
|---|---|
| Explainer/tool/laptop reel with Medo's character, cards, devices, captions | **P** — `medo-motion/templates/procedural-reels` (Pillow + OpenCV + FFmpeg chunks) |
| Kinetic Arabic typography, lists, UI, 3D-ish, fast timeline previews | **K** — `medo-motion/templates/render` (Canvas + Playwright) |

Engine P is the default for talking reels because it composites Medo's poses cheaply
and reliably. Copy the template into the project, never edit the toolkit in place.

## 7. QA gates before delivery

- 1080×1920 · 30 fps · duration = VO duration · H.264 high + AAC · faststart
- **−14.5 ± 0.3 LUFS**, true peak ≤ −1.5 dBTP (two-pass loudnorm)
- Master ≥ 2.5 Mbps (`-crf 13 -tune animation`); anything under ~2 Mbps is rejected
- Arabic joined and correct **in every scene, checked visually**
- One impact per scene, no static hold > 2.5 s, HUD drawn after the camera move
- No text over a face, nothing important outside y 200–1350, captions at y≈1455
- Every placeholder declared, every external asset in `assets/CREDITS.md`
- `python3 medo-motion/scripts/brand_check.py --project <project>` is clean
- `python3 tools/selftest.py` still passes after your changes (it is the regression net)

## 8. Delivery message

8–10 short lines of Egyptian Arabic: file name + measured specs · scene-by-scene in one
line each · what you are unsure about (inferred boundaries, temporary font, placeholder
presenter) · assets used + licence line · 2–3 next improvements. **Never mention a logo
or a series title** — there is none.

## 9. Environment notes (this sandbox)

- If `ffmpeg` is not on PATH, the engines honour `FFMPEG_BIN=/path/to/ffmpeg`.
- `ffmpeg` = static build from `imageio-ffmpeg`; there is no `ffprobe` binary, so
  `tools/ffprobe_shim.py` is installed as `ffprobe` (ffprobe-compatible JSON subset).
- Chromium for engine K comes from `@sparticuz/chromium` (npm) because the Playwright
  CDN is blocked; `tools/chromium.mjs --env` exports `KHAAM_CHROMIUM` + `LD_LIBRARY_PATH`.
- Pillow here is built **without** libraqm. Engine P detects that and shapes Arabic with
  `arabic_shape.py` (HarfBuzz + FreeType). This is real shaping, not presentation forms.
  `doctor.py` reports which backend is active; both are acceptable.
- Fonts: Cairo lives in `assets/fonts/Cairo/` (OFL). Chromium picks it up from the page
  (`/assets/fonts/...`), engine P picks it up from the project's `assets/fonts/`.

## 10. Map

```
AGENTS.md              ← this contract (any agent)
README.md              ← Arabic overview
assets/                ← shared inputs: fonts/, poses/, sfx/
projects/<slug>/       ← one video: BRIEF.md, plan/, assets/, out/, PROGRESS.md
tools/                 ← setup.sh · doctor.py · selftest.py · new_project.py · ffprobe_shim.py · chromium.mjs
tests/                 ← pytest: Arabic shaping invariants, brand lock, scaffold, one real frame
docs/                  ← analysis + conventions (docs/README.md)
medo-motion/           ← the toolkit
  SKILL.md             ← entry point (Claude Code reads this; it defers to AGENTS.md)
  brand/               ← locked identity (human + machine)
  reference/           ← on-demand guides (Arabic typography, hooks, voiceover, …)
  styles/              ← looks; default = medo-red-circle
  templates/           ← engine P + engine K + TASTE.md
  scripts/             ← fonts, SFX, TTS, preflight, brand guard, preview
```

## 11. Never do this

- Ask for a logo, a series name, an episode number, or "your brand colours".
- Add a second display font, a colour outside the palette, or a random stock clip.
- Ship a preview with motion but no sound as if it were the deliverable.
- Claim capabilities you did not verify (`doctor.py` output is your evidence).
- Promise hand animation of the presenter (poses are static: bob/tilt only).
