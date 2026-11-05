---
name: video-motion
description: "Video Motion Arabic reel studio (never puts a series name or logo on screen unless the user asks): locked brand palette (red/black/white), agent-chosen fonts + text motion, Egyptian dialect, code-drawn reels + canvas motion, SFX, mixing, MP4. Works with any coding agent."
---

# Video Motion — استوديو ميدو

This is the agent operating guide for the independently developed Video Motion
project. The repository owner maintains the project code, brand, renderers, templates,
and documentation. Third-party components retain their own licences and attribution;
see `LICENSE.md` and the repository-level `assets/CREDITS.md`.

## 0. This toolkit is host-agnostic

The studio contract lives in **`../AGENTS.md`** at the repo root. This folder is not a
standalone install: clone the whole repository and run commands from its root.
**Read the contract first.** It defines
the four inputs, the hard rules (no logo, no series name, VO from Medo), the workflow and
the QA gates. Nothing here depends on Claude Code: any agent with file + shell tools can
use it. Claude Code additionally auto-loads this file as a skill.

Machine readiness: `bash tools/setup.sh` then `python3 tools/doctor.py` (repo root).

## 1. Brand lock (read every session)

1. `brand/BRAND.md` (human) + `brand/brand.json` (machine) are the source of truth.
   Palette, fonts, safe zones, loudness, dialect and signature devices are **locked**.
   Never re-ask Medo about them and never improvise outside them.
   Items marked 🟡 proposed or "no hex" (pistachio, gold-text) are NOT approved.
2. **There is no logo and no default series name.** This is a reel studio: the user says
   what to make. Never ask for a logo/series title, never invent or suggest one, never
   reserve an empty circle for one. If the user asks for a name/title/episode number on
   screen, do exactly what he said. End cards are typographic only.
3. `reference/medo-playbook.md` resolves every conflict and says which engine to use.
4. Default style = `styles/medo-red-circle.md`; default workflow = **Medo contract**
   (ask once, deliver a finished MP4, ≥3 internal visual QA rounds, declare placeholders).
5. Run `python scripts/brand_check.py --project <project>` before delivery.

Act as director, motion designer, editor and sound designer. Read this file once per
session, then load only the guides you need — do not reread the whole manual per reply.

## 2. The four inputs

| Input | Detail |
|---|---|
| Script | narration text, ideally numbered beats + what appears on screen |
| Scene direction | how Medo wants the scenes presented |
| VO audio | Medo's voiceover file — the timing master |
| Backgrounds | 12 catalogued patterns × dark/light (`motion/backgrounds.json`, on-palette, pure functions of time) — pick one per scene, never hand-draw a gradient |
| Medo poses | 49 poses already in `assets/poses/` — cast from `poses.json`; ask only when a beat needs a pose the library does not have |

Everything else is yours: backgrounds, cards, devices, charts, captions, HUD, SFX by code,
music bed, assets via the code → AI → search ladder, plus `CREDITS.md` for anything external.
Ask **once** for whatever is missing, then decide and state the decision.

## 3. Workflow

New project: `python3 tools/new_project.py <slug> [--engine p|k|r|hybrid]` (repo root), then fill
`BRIEF.md`. Full contract in `../AGENTS.md` §5. In short:
intake → analyse the VO (`silencedetect`) → lock `plan/beats.json` → draw the moves
(`tools/techniques.py --draw --from-plan plan/beats.json`) → write `plan/copy.json` → choose the
text motion AND font for EVERY on-screen text element (`tools/text_direction.py <project> --init`,
then fill `plan/text-direction.json` + a `role` for every `plan/copy.json` fragment; no default
style or font) → sync `TASTE.md` / `STYLE.md` / `plan/design.html` (see `../DESIGN_SYSTEM.md`) →
**lint** (`tools/reel_lint.py <project> --scan-code`) → scene prototype (3 stills)
→ contact sheet → assets → engine render (or sequential hybrid render) → mix (−14.5 LUFS) → master (CRF 13 ≥2.5 Mbps)
→ ≥3 visual QC rounds → deliver with an 8–10 line Arabic message.

Optional user gates (only if Medo asks to review the plan/storyboard first): one-message plan,
one storyboard sheet, then the complete preview with sound.

## 4. Engines

| Situation | Engine |
|---|---|
| Explainer/tool reel with Medo's character, cards, devices, captions | **P** — `templates/procedural-reels` (Pillow + OpenCV + FFmpeg chunks) |
| Kinetic Arabic typography, lists, UI, 3D-ish scenes, fast timeline previews | **K** — `templates/render` (Canvas + Playwright) |
| Reusable React/TypeScript scenes, data-driven graphics, Remotion Studio review | **R** — `templates/remotion` (Remotion + React) |
| A reel whose different sections genuinely need P, K, and/or R | **Hybrid** — sequential full-frame segments via `tools/render_hybrid.py`; no simultaneous engine layers |

For hybrid, each segment uses exactly one renderer; P/K features do not become R features without a deliberate, tested port. See `templates/HYBRID.md` and `docs/hybrid.md`. For persistent framing use `../docs/fixed-stage.md`; for native multi-slide 3D camera moves inside its CONTENT use `../docs/slide-wall.md` and the scaffolded `examples/slide-wall` project. Three.js remains optional for both. Same palette from `brand/brand.json` (K: `lib/brand.js`, R: `src/brand.ts`, P: constants in
`lib.py`; drift is checked by `scripts/brand_check.py --project`). Engine P needs Arabic
shaping: Pillow with libraqm, or the bundled `arabic_shape.py` (HarfBuzz + FreeType) when the
Pillow wheel has no libraqm. `lib.py` picks automatically; never letter-by-letter.

## 5. Arabic typography

`reference/arabic-typography.md` is **mandatory** before any Arabic appears on screen: whole
words only, RTL, real shaping, no letter-spacing, keep the dots, no word broken across lines.
Fonts: the agent chooses from the 21-family OFL manifest (`assets/fonts/fonts.json`) per scene/element
and records it in `plan/text-direction.json` — no forced default. Install with `tools/fonts_install.py`
(or `tools/setup.sh`); preview with `tools/fonts_preview.py`.

## 6. Ownership, licences and privacy

The project-specific code, documentation, brand materials and templates are maintained
as part of Video Motion. No blanket open-source licence is assigned to those first-party
materials at present. Third-party fonts, icons, sounds and tools retain their own licences;
keep their notices and review `../assets/CREDITS.md` before redistribution. See
`LICENSE.md` for the project's licence status. Never print, ask for, or store API keys.
TTS (ElevenLabs) is opt-in only, and always asks for approval before a paid request.

## 7. Resources

| Path | What |
|---|---|
| `reference/arabic-typography.md` | **mandatory** Arabic text rules + safe kinetic vocabulary |
| `reference/medo-playbook.md` | conflict table, Medo contract, engine choice, composition rules, real bugs |
| `reference/explainer-reel-system.md` | explainer/list/tool reels: script skeleton, HUD, captions, CTA |
| `reference/hooks.md` | hook families and first-3-seconds motion (advisory when Medo wrote the script) |
| `reference/voiceover.md` | narration rules when Medo asks for TTS |
| `reference/visual-design.md`, `recipes.md`, `inspiration.md` | design craft and motion recipes |
| `reference/planning-and-tracking.md` | project structure, TASTE memory, gates |
| `../docs/skillry-fit.md` | public Skillry review, relevant workflow patterns, adoption decision and third-party Skill safety checks |
| `reference/reference-and-delivery.md` | reference breakdown + final QA |
| `reference/asset-hunting.md`, `fonts.md`, `arabic-fonts.md` | sourcing and licences |
| `reference/free-sfx-openverse.md`, `local-sound-workflow.md`, `elevenlabs-sfx.md` | sound sourcing and mixing |
| `reference/portability.md`, `setup-and-integrations.md`, `installation.md` | machines, paths, tool installs |
| `brand/`, `styles/`, `templates/`, `scripts/` | identity, looks, engine code, tools |

Bundled limits: no fonts, audio or AI weights are shipped; do not claim tools hear like a
human or that every real Foley can be synthesised. Never promise hand animation of the
presenter (poses are static: bob/tilt only).
