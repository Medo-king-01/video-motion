---
name: video-motion-remotion
description: >
  Remotion/React guidance for Engine R of the Video Motion studio, adapted from the
  remotion-dev/skills agent-skill pack (upstream v4.0.541). Defers to AGENTS.md and
  medo-motion/SKILL.md; it never replaces them. Covers scaffolding, markup, Studio
  preview, rendering, captions, maps, interactivity, SaaS, licensing, upgrades and
  docs lookup — filtered through the studio's offline, VO-timed, brand-locked contract.
---

# Video Motion — Remotion (Engine R) Playbook

> **What this is.** An optional add-on skill of the Video Motion studio for work on
> **Engine R** (`medo-motion/templates/remotion/` — Remotion + React + TypeScript).
> The operating contract is `AGENTS.md` at the repository root and the core skill
> `medo-motion/SKILL.md`; this skill specializes **how to use Remotion well inside
> that contract** and never replaces, edits, or bypasses them. It touches no engine
> code: it selects, composes, and maintains from the engine's real, tested capabilities.
>
> **Paths below are relative to the repository root.**
>
> **Provenance.** Adapted 2026-11-09 from the upstream agent-skill pack
> `remotion-dev/skills` v4.0.541 (commit `a2824c6`, pushed 2026-11-05; 13 skills).
> Upstream is a reference, not a dependency: this file is original writing, no upstream
> file is redistributed, and the studio contract wins wherever the two disagree
> (see §3). The upstream skills repository declares no license; Remotion itself is
> source-available under the custom Remotion License — see
> `docs/remotion-skill.md` for the full audit. When documentation conflicts with code,
> manifests, or tests, the code wins. `tests/test_remotion_skill.py` fails if this
> file's pinned claims drift.

## 1. Scope and authority

1. `AGENTS.md` (inputs, hard rules, engines, QA gates) > `medo-motion/SKILL.md`
   (core studio skill) > **this add-on**. The core skill does not depend on this one.
2. Engine R is **optional**, chosen for React component reuse, data-driven scenes, or
   interactive Studio review — it is not a drop-in K replacement and is not
   automatically faster (AGENTS.md §6). Engine P handles talking reels with Medo.
3. R renders from Chromium like K, shares `plan/beats.json` (VO-derived) and the
   tested `lib/motion.js` source. R does **not** inherit P/K's animated-icon catalog
   or the transition catalog: R gets hard cuts plus `SceneEffects` (AGENTS.md §6,
   `docs/remotion.md`).
4. This skill applies to projects scaffolded from `medo-motion/templates/remotion/`.
   Never edit the template in place; edit the project's copy.

## 2. The studio R path (commands that are allowed and expected)

From the repository root, scaffold and work inside the project — never in the template:

```bash
python3 tools/new_project.py my-reel --engine r   # scaffolds projects/my-reel with pinned deps
cd projects/my-reel
npm ci                                            # exact pins: remotion 4.0.539, react 19.3.1
npm run typecheck                                 # tsc --noEmit — run after every edit
npm run studio                                    # validated launcher (see below)
npm run stills                                    # 4 review frames by default
npm run stills -- 3 7.5                           # review frames at exact seconds
python3 ../../tools/vo_length.py out/vo24.wav --json plan/beats.json   # from the project root (docs/remotion.md); from the repo root drop the ../../
npm run render -- --audio out/vo24.wav            # only after plan/beats.json carries the measured VO
```

Hard rules for these commands:

- **`npm run studio`, not `npx remotion studio`.** The scaffolded script is
  `node scripts/launch-remotion.mjs studio src/index.ts --no-open`. It first validates
  `plan/text-direction.json` (every visible text element carries an agent-chosen motion
  style), `plan/stage.json`, `plan/slide-wall.json` and `plan/one-take.json` when they
  exist, then launches against the **shared Chromium** from `tools/chromium.mjs`.
  `npx remotion studio` skips the plan gates and can pull a browser from
  remotion.media — both are against studio policy (`docs/remotion.md`). The launcher
  prints the URL; open it when the user asks or when mirroring upstream's
  preview-first workflow, and verify the composition's video preview loads. Studio may
  stay running while you work so the user can steer.
- **`npm run render`, never a bare `npx remotion render`.** It refuses to render until
  `plan/beats.json` has the measured VO timeline, checks FPS/duration/PCM-WAV audio and
  duration match, then muxes the soundtrack. `--silent` exists for visual QA only — it
  is not a delivery path. The Studio UI's render button is fine as an interactive
  alternative once the VO gate passes.
- **`npm run stills`** is the studio equivalent of upstream's "render a few frames as
  images" — use it for review frames before any full render.
- Delivery still passes the full AGENTS.md §7 gates: 1080×1920 · 30 fps · −14.5 ± 0.3
  LUFS · true peak ≤ −1.5 dBTP · ≥ 2.5 Mbps · faststart · `brand_check.py` clean ·
  `media_qa.py` on the master · at least three visual QA rounds with contact sheets.

## 3. Where upstream and the studio disagree (studio wins)

Upstream (remotion-dev/skills v4.0.541) is written for generic Remotion projects.
Rows below are the conflicts that matter; everything else in §5–§10 applies as adapted.

| Upstream says / teaches | Studio rule (wins) |
|---|---|
| Scaffold with `npx create-video@latest` | `python3 tools/new_project.py <slug> --engine r` — pinned deps, R contract files, `public/fonts/` + `public/assets/poses/` generated, plan validation wired into scripts |
| `npx remotion studio` (or let Studio pick a browser) | `npm run studio` — validated launcher + shared Chromium; never a remotion.media browser download |
| `npx remotion render` for export | `npm run render -- --audio …` after the measured VO gate; `npm run stills` for frames; render only on explicit user request, never by default |
| Google Fonts via `@remotion/google-fonts` at runtime | **Local OFL fonts only.** `public/fonts/` is generated at scaffold; `assets/fonts/fonts.json` is the manifest; no network during render; Cairo is the system-chrome fallback |
| AI voiceover via ElevenLabs TTS + `calculateMetadata` | **Rejected for studio deliveries.** VO is Medo's recording; `tools/vo_length.py` sets the duration; `calculateMetadata()` may size only from the measured `plan/beats.json`, never invent a duration |
| `<Typography>` scale from 1080px web defaults | Safe zones and brand sizes from `medo-motion/brand/brand.json` / DESIGN_SYSTEM.md; Arabic rules from `medo-motion/reference/arabic-typography.md` (mandatory reading before any text) |
| Interactivity: `Interactive.*`, `InteractivitySchema`, Studio edits code (upstream 4.0.541) | Scaffold pins **remotion 4.0.539**; the API is **unverified there**. Reference-only until an explicit, reviewed upgrade (§8); never part of a delivery path. Do not add Interactivity to a reel to "make it nicer" |
| Maps: Mapbox / MapLibre / MapTiler / CesiumJS flythroughs | No network/tiles/keys in the render path by default. A map is essential only with the user's explicit approval and rights-cleared assets (drawn SVG/GeoJSON with `assets/CREDITS.md` entries); user-approved Mapbox/MapTiler keys live in `.env`, never in the repo. Static 9:16 compositions, not 16:9 web embeds |
| Captions: `@remotion/captions` + `@remotion/whisper-webgpu` transcription | Studio pipeline: `tools/vo_length.py` → `plan/word-timings.json` → `tools/caption_align.py` / `tools/whisper_align.py` → `DirectedText`/`TextMotion`. Phrase chunks of 2–4 words (`groupCaptionChunks`). An imported `.srt` is content reference only — VO timing stays authoritative |
| Effects: `@remotion/effects` (`vignette()`, `lut()`, …) on `<HtmlInCanvas>` | Not installed. R-native first: `SceneEffects` (`lightSweep`, `whipPan`, `particleDissolve` in `src/lib/effects.js`) plus `WhipPan`, `LightSweep`, `ParticleDissolve` components. Installing `@remotion/effects` is a deliberate decision (§8), not a default |
| Mediabunny in the browser for metadata/trimming | Studio measures and probes with `tools/ffprobe_shim.py`, `tools/vo_length.py`, ffmpeg — authoritative, offline. Mediabunny stays a reference for interactive web builds only |
| `npx skills add remotion-dev/skills` as the install | This add-on **is** the studio's curated integration. Do not install upstream into agent-specific directories; do not vendor upstream into this repository |
| `npx skills update …` to refresh skills | Not applicable — nothing is vendored. Refresh by re-auditing upstream and updating this file + `tests/test_remotion_skill.py` (see `docs/remotion-skill.md`) |
| Remotion 4.0.541 APIs as available | Scaffold is exact-pinned to **4.0.539**; treat any 4.0.540+/4.0.541-only API as absent until `npm ls remotion` and a full `selftest --remotion` say otherwise |

## 4. The upstream pack, skill by skill (all 13)

Disposition legend: **adapted** = guidance absorbed here, rewritten for the studio ·
**reference-only** = knowledge worth knowing, not applicable to studio deliveries unless
the contract changes (the voiceover/TTS path inside upstream's markup skill is rejected
outright — see §3).

| # | Upstream skill | What it teaches | Disposition |
|---|---|---|---|
| 1 | `remotion-best-practices` | Router for the pack; preview-before-build, render only on explicit ask | **adapted** — becomes this file's structure; the preview-first and render-only-when-explicit rules are kept |
| 2 | `remotion-create` | Scaffold a new project; design a video; layout rules | **adapted** — studio scaffolder rules (§2); video-layout minimums honored as loose guidance under brand/safe-zone rules: keep key text ≥ 80 px from sides, ≥ 100 px from top/bottom, headline ≈ 84 px minimum at 1080 px width — scaled to the reel canvas |
| 3 | `remotion-markup` | React markup rules: frame-driven animation, inline `interpolate()`, assets, media, sequences, effects, measuring text, fonts | **adapted** — §5 (and §6 for Arabic); effects/fonts/media rows moved to §3/§8 |
| 4 | `remotion-studio` | Launch Remotion Studio; `--no-open`, ports, logging flags | **adapted** — `npm run studio` only (§2) |
| 5 | `remotion-render` | `npx remotion render`/`still`/`render --frames`; transparent videos | **adapted** — `npm run stills` + the VO-gated render (§2). Transparent-background reels: only for explicit overlay deliverables, via Remotion's transparent-video recipe; never for standard Medo reels |
| 6 | `remotion-maps` | Static maps, Mapbox/MapLibre/MapTiler, Cesium flyovers | **reference-only** — external providers, keys, network; see §9 |
| 7 | `remotion-captions` | `Caption` JSON type; display/transcribe/SRT-import recipes | **adapted** — studio caption pipeline (§7); the `Caption` shape (`text/startMs/endMs/timestampMs/confidence`) is understood, `@remotion/captions` is not installed |
| 8 | `remotion-saas` | `<Player>`, Lambda/Vercel/Cloudflare/Express rendering, templates, Vue/Angular/Svelte | **reference-only** — studio deliveries are MP4 masters, not apps. Only if the user explicitly asks for an interactive/web deliverable, which is a different brief |
| 9 | `remotion-interactivity` | `Interactive.*`, schema fields, Studio keyframing that writes back to code | **reference-only** — unverified on scaffold pin 4.0.539; see §3 and §8. Never for deliveries |
| 10 | `remotion-multimedia` | Mediabunny for browser-side metadata/trim/crop | **reference-only** — studio probes with ffprobe/ffmpeg offline (§3) |
| 11 | `remotion-license` | Where to read Remotion license/FAQ/terms; buy at remotion.pro | **adapted** — kept as pointer; Remotion's license is independent of this repository's license and of OFL font terms; see §8 and `docs/remotion-skill.md` |
| 12 | `remotion-upgrade` | Bump Remotion + skills coherently | **adapted** — studio upgrade procedure (§8) |
| 13 | `remotion-docs` | Search Algolia; fetch any docs page as Markdown via `.md` suffix | **adapted** — adopted as-is (network required). Always verify against the installed 4.0.539 rather than remembered APIs |

## 5. Markup essentials (adapted from remotion-markup)

Everything here stays inside the deterministic contract: **frame is the only clock**.
No CSS `transition`/`animation`, no Tailwind animation classes, no `Math.random()`,
no wall-clock state. Per `docs/remotion.md`, the same scene must render identically
in all three engines.

- **Where frame lives.** Call `useCurrentFrame()` in the smallest component that needs
  it; extract frame-bound leaves (volume envelopes, per-word overlays) rather than
  subscribing the whole composition. Keep editable interpolations inline on the item's
  own props. Ports of existing P/K scenes must not change frame coordinates —
  `lib/motion.js` in R is the tested shared source; treat its API as stable.
- **fps from config.** Take `fps` (and `durationInFrames`) from `useVideoConfig()` for
  every seconds→frames conversion — never a hardcoded 30 in new helper code (the brand
  contract is 30 fps, but helpers must stay honest).
- **`interpolate()` inline, props-side.** Keep calls in the `style` prop with explicit
  `extrapolateLeft`/`extrapolateRight: "clamp"` and `Easing.bezier` / `Easing.spring()`.
  Use `scale`/`translate`/`rotate` CSS properties rather than the `transform` shorthand;
  for `scale` animations prefer `output: 'perceptual-scale'`.
- **Assets.** Files live in the scaffold-generated `public/` (`fonts/`,
  `assets/poses/`); reference them with `staticFile()`. Remote URLs are allowed for
  user-supplied, rights-cleared media — never for hotlinking random assets.
- **Media.** The scaffold has **no** media packages: `<Video>`/`<Audio>` from
  `@remotion/media` are absent until `npx remotion add @remotion/media` (§8). For the
  standard talking reel, picture is drawn, not composited from footage, and the VO is
  muxed by `npm run render -- --audio`. If the user supplies footage, that is an
  explicit footage brief — confirm the tool path before wiring it in.
- **Sequencing.** Use `<Sequence from durationInFrames>` with values derived from
  `plan/beats.json` (measured), never from guesswork. Preserve frame coordinates when
  extracting children across timing boundaries. `<Series>`/`<Loop>` are fine when
  genuinely simpler.
- **Components and stills.** Register compositions/stills with inline metadata (`id`,
  `durationInFrames`, `fps`, `width`, `height`, `defaultProps` inline object literal, no
  type assertions) so Studio's Props editor can write back. `calculateMetadata()` only
  for genuinely dynamic parts — for this studio, width/height/fps/duration come from
  the brand contract and the measured beats, i.e. basically never dynamic.
- **Multi-scene work.** `plan/beats.json` is the single timing source; scenes are
  `<Sequence>` blocks anchored to measured beats; transitions are R's hard cuts plus
  `SceneEffects` — do not reach for the P/K catalog. For distinct reusable timelines,
  use connected compositions only after checking Studio's read-back behavior.
- **Measuring.** Use the studio's `src/lib/text-measure.js` for text measurement and
  `src/lib/text-direction.js` for directed-text validation rather than ad-hoc DOM reads.
- **Lottie / GIFs / animated images.** Only with user-supplied, rights-cleared JSON or
  images, logged in `assets/CREDITS.md`; prefer native SVG/`SvgArt` recipes otherwise.
- **Effects.** Reach for R-native `SceneEffects` and `effects.js` primitives before any
  package install (§3). An effect belongs on the element that supports `effects`
  directly; ordinary DOM wrappers need `<HtmlInCanvas>` to accept post-processing —
  use it sparingly and verify Chromium support in the shared build before relying on it.

## 6. Arabic and RTL (upstream arabic-text.md, studio rules)

Upstream's Arabic guidance and this studio agree; `medo-motion/reference/arabic-typography.md`
is the authority.

- Put `dir="rtl"` and `lang="ar"` on the element holding Arabic text.
- Animate **words or lines**, never raw letters. If letter-level units are unavoidable,
  split into join-safe units: harakat stay with their letter, `لا` stays one unit,
  digit/Latin runs stay one unit, ZWJ (`\u200D`) padding on internal/external joins.
  Chrome (our render path) joins those units correctly; the `<Player>` in Safari can
  mix typefaces per ZWJ letter — another reason the render, not the Player, is the QA
  target.
- **No `letterSpacing`, no `textTransform`** on Arabic. Ever.
- Count words, not first letters, when direction must be inferred from props
  (mixed Arabic/Latin lines are common in Egyptian tech content).
- Load Arabic faces from the local manifest (IBM Plex Sans Arabic, Alexandria,
  Noto/Cairo peers — the manifest `assets/fonts/fonts.json` wins over any doc listing).
  A Latin-only face falls back to whatever the machine has — that is how reels end up
  with four substituted fonts in one line.
- Shaping must survive the lint and the eyeball: `reel_lint.py` for plan-level rules,
  stills at real 1080×1920 for the actual rendering.

## 7. Captions in the studio pipeline

1. The VO is the master. `tools/vo_length.py` produces `plan/beats.json`;
   `plan/word-timings.json` holds measured word boundaries. Never invent boundaries.
2. Caption content is chunked into **2–4 word unboxed RTL phrases** without orphaning
   Arabic glue particles (`groupCaptionChunks` in `render/lib/captions.js` is the K
   equivalent; R uses the same word timings through `DirectedText`/`TextMotion`).
3. Entrances come from the directed-text/caption style ids
   (`src/lib/caption-styles.js`, `src/lib/caption-motion.js`), chosen per scene in
   `plan/text-direction.json` — not typed inline at the JSX call site.
4. `@remotion/captions`'s `Caption` type (`text`, `startMs`, `endMs`, `timestampMs`,
   `confidence`, optional `pageBreakAfter`) is understood as an interchange shape only.
   No package is installed; no transcription model runs inside a studio delivery.
5. Local transcription for timing alignment, when the VO has no timings, is
   `tools/whisper_align.py` (studio tool) — not `@remotion/whisper-webgpu`, which needs
   a GPU, a model download, and a memory budget this offline pipeline does not have.
6. An `.srt` supplied by the user is treated as content; its timings are re-checked
   against the measured VO before burning captions in.

## 8. Adding packages and upgrading (adapted from remotion-upgrade)

**Adding a package** (`@remotion/*`, `mediabunny`, `zod`, …):

1. Confirm the need against the built-ins (`SceneEffects`, `SvgArt`,
   `DirectedText`, …). The scaffold deliberately ships core Remotion only.
2. `npx remotion add <pkg>` inside the **project** — it aligns the version with the
   installed Remotion. Never `npm install` an unaligned `@remotion/*`.
3. Record it: lockfile diff reviewed, `assets/CREDITS.md` entry if it ships creative
   assets, and `python3 tools/selftest.py --remotion` green.

**Upgrading Remotion itself:**

1. Read `package.json` and `package-lock.json` — the scaffold pins exact versions
   (`remotion` = `4.0.539`, `@remotion/cli`/`@remotion/renderer` = `4.0.539`,
   react `19.3.1`, `typescript` `5.9.3`, and a deliberate `zod: ^4.6.7` override). The override
   exists because Remotion pins `zod 4.5.4`, which carries a high memory-exhaustion advisory; with
   the override `npm audit` is clean, and the price is Remotion's own warning
   *"zod: installed 4.6.7, required 4.5.4"* on every render. Do not "fix" the warning — dropping
   the override re-opens the advisory for zod and nine Remotion packages.
2. With `@remotion/cli` present, `npx remotion upgrade` is the supported path (it also
   tries to update agent skills — harmless here, this repo vendors none). The
   upstream-only `npx skills update` step is **not** used in this repository.
3. Manual path otherwise: `npm view remotion version`; bump **every** `remotion` and
   `@remotion/*` to that one version; align `mediabunny`/`zod`/
   `@huggingface/transformers` with `npm view @remotion/studio@<version> dependencies
   --json`; keep the `zod` override on the newest 4.6.x until the required version is itself
   patched (see the trade-off in `docs/remotion.md`), then refresh the lockfile with the project's
   package manager and confirm `npm audit` is still clean.
4. Verify: `npm run typecheck` → `npm run stills` (visual unchanged) →
   `python3 tools/selftest.py --remotion`. Review the full lockfile diff; never mix
   Remotion versions across workspace packages.
5. Never upgrade mid-reel. Upgrades are their own reviewed change on a quiet tree.

**License (remotion-license).** Read before commercial use or redistribution:
https://www.remotion.dev/docs/license.md · …/license/faq.md · …/terms.md ·
buy at https://www.remotion.pro/license. Remotion's license is separate from this
repository's license and from the OFL fonts. The studio's pinned scaffold is used
locally for rendering; any commercial distribution of Remotion-based tooling follows
Remotion's terms, not ours.

## 9. Maps and external providers

Default: **no maps**. If a beat genuinely needs one:

1. Prefer a **static, rights-cleared** map: user-supplied image, or an SVG/GeoJSON
   drawing with the data source and license logged in `assets/CREDITS.md`. Draw it
   into the composition as vector shapes; it survives the offline render and the
   brand lock.
2. Provider APIs (Mapbox, MapLibre tiles, MapTiler, CesiumJS) are live network calls
   with keys — incompatible with the offline render path, the 9:16 crop (their defaults
   target web embeds), and key hygiene (no keys in the repo, ever). They are allowed
   only with explicit user approval, a documented provider, and a static-export plan
   (pre-rendered image committed as a rights-cleared asset) rather than live tiles at
   render time. Cesium terrain flythroughs are effectively never appropriate here.
3. Upstream's per-provider notes (globe at low zoom, 3D buildings, MapLibre being
   free, MapTiler annotations, render-stability guidance) stay in the upstream pack as
   reference for that exceptional case — not as an invitation.

## 10. QA loop for R work

1. `npm run typecheck` after every change.
2. `tools/reel_lint.py --project <project>` on the plan (engine-agnostic).
3. `npm run stills` at hook / dense-text / data-scene times; check Arabic shaping at
   real size, safe zones, brand palette only.
4. Render only with the VO gate green; then `python3 tools/media_qa.py <master.mp4>
   --mode master --vo <project>/out/vo24.wav --beats <project>/plan/beats.json` and
   `python3 medo-motion/scripts/brand_check.py --project <project>`.
5. At least three visual QA rounds with contact sheets (AGENTS.md §7). A clean
   typecheck proves nothing about the picture.
6. If the delivery changes R code itself: `python3 tools/selftest.py --remotion`.

## 11. Known limits (honest boundaries)

- No P/K transition catalog, no animated icons in R — hard cuts + `SceneEffects` only.
- No media pipelines from footage: `<Video>`/`<Audio>` need `@remotion/media` (not
  installed); the standard reel draws its picture and muxes the VO at render.
- Interactivity API unverified on scaffold pin 4.0.539 (upstream documents 4.0.541).
- Studio preview is for steering, not for final QC — the render (or stills) is the QC.
- Maps, TTS voiceover, live transcription, WebGL/MapLibre tiles: unavailable offline
  by design.
- `ThreeCanvas` (opt-in, `three@0.187.0` pinned in `tools/optional-three/`) is the only
  3D path and stays optional; prefer `MachineDiagram`/`iso-kit` first.

## Appendix — provenance and reality checks

Upstream: https://github.com/remotion-dev/skills — v4.0.541, commit `a2824c6`
(pushed 2026-11-05), audited 2026-11-09. Upstream's repository declares **no license**;
Remotion itself ships under the custom Remotion License. This add-on is original
writing; the upstream pack informed the API knowledge and the routing, and no upstream
file is copied or redistributed. Full audit: `docs/remotion-skill.md`.

Pinned claims this skill relies on (verified 2026-11-09; `tests/test_remotion_skill.py`
pins them):

| Claim | Verified against |
|---|---|
| Scaffold pins `remotion`/`@remotion/cli`/`@remotion/renderer` = `4.0.539`, react `19.3.1`, zod override `^4.6.7` | `medo-motion/templates/remotion/package.json` |
| R scripts: `studio` = validated launcher (plan gates + shared Chromium, `--no-open`), `render` = VO-gated mux, `stills`, `typecheck` | `medo-motion/templates/remotion/scripts/launch-remotion.mjs`, `render.mjs`, `stills.mjs`, `package.json` scripts |
| R template ships core Remotion only — no `@remotion/media`, `@remotion/effects`, `@remotion/captions`, `@remotion/gif`, `@remotion/lottie` | `medo-motion/templates/remotion/package.json` |
| R source ships `DirectedText`, `MachineDiagram`, `SlideWall`, `OneTake`, `FixedStage`, `SceneEffects`, `TextMotion`, `SvgArt`, `ThreeCanvas` (opt-in) | `medo-motion/templates/remotion/src/lib/` |
| R has no animated-icon layer and no transition catalog (hard cuts + `SceneEffects`) | `src/lib/` listing; AGENTS.md §6 |
| Three.js pinned `three@0.187.0` for optional integration only | `tools/optional-three/package.json` + `package-lock.json`, `docs/motion-three.md` |
| Upstream pack: 13 skills, v4.0.541, no declared license | `gh api repos/remotion-dev/skills`, upstream `skills/*/SKILL.md` frontmatter |
| Word-level RTL Arabic rules and the ZWJ/Safari caveat | upstream `remotion-markup/arabic-text.md` vs `medo-motion/reference/arabic-typography.md` — studio rules win |
| Studio VO pipeline: `vo_length.py` → `word-timings.json` → `caption_align.py` / `whisper_align.py` | `tools/`, `docs/length.md`, `docs/alignment.md` |
| 2–4 word phrase captions (`groupCaptionChunks`) | `medo-motion/templates/render/lib/captions.js` |
