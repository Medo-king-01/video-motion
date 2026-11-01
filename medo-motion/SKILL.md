---
name: medo-motion
description: "Medo (Kodo Medo) Arabic reel studio: locked brand (red/black/white, Cairo), Egyptian dialect, code-drawn reels + canvas motion, SFX, mixing, MP4. Works with any coding agent."
---

# Medo Motion «موشن ميدو» — v1.1 (private fork of Khaam Motion v1.4.1)

Khaam Motion by Khaam (@khaam.hq), edited by Rashed Alhazmi, **plus Medo's brand layer
and his procedural-reels engine**. Private copy for Medo only: the licence forbids
republishing a modified/renamed version (`LICENSE.md`). See `CHANGELOG.md`.

## 0. This toolkit is host-agnostic

The studio contract lives in **`../AGENTS.md`** at the repo root (or, on a machine where
only this folder was installed, right next to your project). **Read it first.** It defines
the four inputs, the hard rules (no logo, no series name, VO from Medo), the workflow and
the QA gates. Nothing here depends on Claude Code: any agent with file + shell tools can
use it. Claude Code additionally auto-loads this file as a skill.

Machine readiness: `bash tools/setup.sh` then `python3 tools/doctor.py` (repo root).

## 1. Brand lock (read every session)

1. `brand/BRAND.md` (human) + `brand/brand.json` (machine) are the source of truth.
   Palette, fonts, safe zones, loudness, dialect and signature devices are **locked**.
   Never re-ask Medo about them and never improvise outside them.
   Items marked 🟡 proposed or "no hex" (pistachio, gold-text) are NOT approved.
2. **There is no logo and no series name.** This is a reel studio: Medo says what to make.
   Never ask for a logo/series title, never invent one, never reserve an empty circle for
   one. End cards are typographic only.
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
| Medo poses | 2–4 images (wave / think / point) |

Everything else is yours: backgrounds, cards, devices, charts, captions, HUD, SFX by code,
music bed, assets via the code → AI → search ladder, plus `CREDITS.md` for anything external.
Ask **once** for whatever is missing, then decide and state the decision.

## 3. Workflow

New project: `python3 tools/new_project.py <slug> [--engine p|k]` (repo root), then fill
`BRIEF.md`. Full contract in `../AGENTS.md` §5. In short:
intake → analyse the VO (`silencedetect`) → lock `plan/beats.json` → scene prototype (3 stills)
→ contact sheet → assets → chunked render → mix (−14.5 LUFS) → master (CRF 13 ≥2.5 Mbps)
→ ≥3 visual QC rounds → deliver with an 8–10 line Arabic message.

Optional user gates (only if Medo asks to review the plan/storyboard first): one-message plan,
one storyboard sheet, then the complete preview with sound.

## 4. Engines

| Situation | Engine |
|---|---|
| Explainer/tool reel with Medo's character, cards, devices, captions | **P** — `templates/procedural-reels` (Pillow + OpenCV + FFmpeg chunks) |
| Kinetic Arabic typography, lists, UI, 3D-ish scenes, fast timeline previews | **K** — `templates/render` (Canvas + Playwright) |

One engine per video. Same palette from `brand/brand.json` (K: `lib/brand.js`, P: constants in
`lib.py`; drift is checked by `scripts/brand_check.py --project`). Engine P needs Arabic
shaping: Pillow with libraqm, or the bundled `arabic_shape.py` (HarfBuzz + FreeType) when the
Pillow wheel has no libraqm. `lib.py` picks automatically; never letter-by-letter.

## 5. Arabic typography

`reference/arabic-typography.md` is **mandatory** before any Arabic appears on screen: whole
words only, RTL, real shaping, no letter-spacing, keep the dots, no word broken across lines.
Fonts: Cairo (`python scripts/get_fonts.py "Cairo"`, or `tools/setup.sh` from the repo root).

## 6. Licence and privacy

`LICENSE.md`: free for Medo's personal/business/client videos; the skill itself may not be
republished or resold without written permission from Khaam. Third-party fonts, sounds and
tools keep their own licences. Never print, ask for, or store API keys. TTS (ElevenLabs) is
opt-in only, and always asks for approval before a paid request.

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
| `reference/reference-and-delivery.md` | reference breakdown + final QA |
| `reference/asset-hunting.md`, `fonts.md`, `arabic-fonts.md` | sourcing and licences |
| `reference/free-sfx-openverse.md`, `local-sound-workflow.md`, `elevenlabs-sfx.md` | sound sourcing and mixing |
| `reference/portability.md`, `setup-and-integrations.md`, `installation.md` | machines, paths, tool installs |
| `brand/`, `styles/`, `templates/`, `scripts/` | identity, looks, engine code, tools |

Bundled limits: no fonts, audio or AI weights are shipped; do not claim tools hear like a
human or that every real Foley can be synthesised. Never promise hand animation of the
presenter (poses are static: bob/tilt only).
