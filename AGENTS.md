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
   `medo-motion/brand/BRAND.md` + `brand/brand.json` are the source of truth. Never
   re-ask about colours/fonts and never improvise outside the palette.
3. **VO is Medo's.** Never generate TTS unless Medo explicitly asks for it. If he does,
   `medo-motion/scripts/gen_tts_elevenlabs.py` is there — and it asks for approval
   before any paid request.
4. **Egyptian Arabic** in replies and on screen; code, filenames and comments in English.
   Technical terms stay in English.
5. **Arabic typography rules are mandatory** before any Arabic appears on screen:
   `medo-motion/reference/arabic-typography.md`. Whole words only, RTL, real shaping.
   Never letter-by-letter, never `arabic_reshaper`.
6. **Never print, ask for, or store API keys** in chat or in files.

## 3. What YOU produce

Medo gives you words, timing, voice and poses. Everything visual and audible is yours:

| Element | Source order |
|---|---|
| Backgrounds, cards, devices, charts, icons, transitions, captions, HUD | **Code** first (this is the default and the cheapest) |
| Hero objects the code can't draw well | **AI image generation**, one session per video, deck-locked prompt in `medo-playbook.md` §4 |
| Real footage / textures / photos | **Search** CC0/PD/OFL only, download into `projects/<slug>/assets/`, log in `CREDITS.md` |
| Sound effects | **Procedural** (`sfx.py`) first → Openverse CC0 → ElevenLabs SFX only with approval |
| Music bed | Generated Am–F–C–G, 76 BPM, ducked under VO (see brand §8) |
| Captions, word timings, scene boundaries | Derived from Medo's VO (`silencedetect` + script) |

## 4. First run on a machine

```bash
bash tools/setup.sh          # installs python + node deps, ffmpeg, fonts, chromium
python3 tools/doctor.py      # prints READY / BLOCKED for every capability
```

Then start a project:

```bash
python3 tools/new_project.py laptop-series-ep1
```

`doctor.py` is the only readiness check you need; `preflight.py` inside the toolkit
is the portable inventory it extends. Do not install anything else "just in case".

## 5. Workflow (the default path)

1. **Intake** — fill `projects/<slug>/BRIEF.md` from the four inputs; copy the VO into
   `assets/vo/`, the poses into `assets/poses/`, the script into `plan/script.md`.
2. **Timing** — analyse the VO (`silencedetect`), align beats to the real audio, write
   `plan/beats.json`. Scene boundaries = midpoint of silences; duration = VO duration.
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

## 8. Delivery message

8–10 short lines of Egyptian Arabic: file name + measured specs · scene-by-scene in one
line each · what you are unsure about (inferred boundaries, temporary font, placeholder
presenter) · assets used + licence line · 2–3 next improvements. **Never mention a logo
or a series title** — there is none.

## 9. Environment notes (this sandbox)

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
tools/                 ← setup.sh, doctor.py, new_project.py, ffprobe_shim.py, chromium.mjs
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
