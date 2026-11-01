> Detailed production guidance: load only for the current task. The SKILL.md entrypoint and current user/project instructions take precedence. Section numbers below refer to this production manual; use the entrypoint guide table to locate a different topic. Do not assume any installed tool, private library, universal approval or specific narration provider.

## 13. Reference-video protocol (if the user attaches references, use them)

A reference is **optional**, not a fifth required input. If the user supplies one or asks to match its look, analyze it locally before locking the visual direction. Do not fetch a copyrighted video or ask for a reference the user has not offered. From the project root:

```bash
python3 ../../medo-motion/scripts/analyze_ref.py assets/refs/reference.mp4 \
  --start 0 --dur 15 --fps 4 --frames 3 --out cache/reference-analysis
```

Use another `--start` and a distinct `--out` for another short window. Review `report.md`, the timestamped `sheet_*.jpg` overview, `strip_hook.jpg`, `motion/strip_*.jpg`, and audio diagnostics when present. The report and palette are rough observations—not a finished design or a color prescription. Inspect the actual frames, then complete the project `STYLE.md`: composition, recurring device, type roles, motion entry/hold/exit, pacing, what the selected engine can implement, and what must be omitted. Translate all choices through the locked Medo brand. Reference media stays reference-only; never copy its text, logo, footage, characters or distinctive assets into the reel without documented rights. See `docs/reference-workflow.md`.

## 14. Reverse-engineered reference recipes (build these without seeing the videos)

Four ready recipes built from analysed top-performing videos — A premium talking-head caption reel (9:16), B cinematic storyteller documentary (16:9), C SaaS launch Slack-style, D brand-agency kinetic promo — plus the shared taste behind them. Open `<skill>/reference/recipes.md` when the user's video matches one of them or has no reference, and use its format for your own recipes (§13).

## 15. QA checklist before delivery

- [ ] Plan (design.html) approved, preview approved (logged in PROGRESS.md → Approvals)
- [ ] Hook lands in ≤ 3 s; CTA visible ≥ 2 s
- [ ] VO is the approved final narration (the user's file or approved Eleven v4 takes, never v3); word/transcript diff vs the approved script is clean (or differences approved); no audio tag spoken aloud; chunk seams inaudible and loudness-matched
- [ ] Captions match VO, no typos, inside safe zones, contrast ≥ 4.5:1
- [ ] SFX synced (±1 frame), short and reference-matched (no stray whooshes/risers), audible under actual VO without masking it (no fixed peak-ratio guarantee), source audio muted when requested, no unwanted tails, VO intelligible over any permitted music, −14 LUFS / −1.5 dBTP
- [ ] Every caption word passes the readability pass (§12) on its real background
- [ ] Every feedback point from this round is fixed and written into `TASTE.md`; TASTE.md is complete enough for a new chat to continue in the same style (§11 checklist filled)
- [ ] No halos on cutouts, no flicker, no dropped frames; `ffprobe` duration/fps/resolution correct
- [ ] H.264 yuv420p, AAC 48 kHz, faststart (`-movflags +faststart`)
- [ ] Contact sheets checked over the full duration (§2b), no framing/overlap issues left
- [ ] manifest.json licenses complete (no `reference-only` asset in the final without user OK); LOG.md updated; final saved as new version
- [ ] Font licences saved next to the fonts in `assets/fonts/` and listed in the credits
- [ ] Final render log saved in `renders/logs/` and linked in LOG.md; TASTE.md, design.html, PROGRESS.md and manifest.json are up to date
- [ ] No API key values in any log, manifest, script or rendered credit
- [ ] Vertical/other aspect versions are native re-layouts (not crop/letterbox) and checked with contact sheets
- [ ] PROGRESS.md marked `Phase: DONE` with final file path, specs and credits
- [ ] Offer cleanup: move `cache/` (previews, logs, intermediates, stems) to the OS trash/Recycle Bin — never permanently delete; keep src, assets, renders

## 16. Visual asset hunting with the Playwright MCP (browse any site, grab assets yourself)

Whenever the plan needs an image, texture, footage, icon, mockup or style reference that the API MCPs don't cover: **find it yourself, don't ask the user to search.** Open `<skill>/reference/asset-hunting.md` for the loop (brief → search visually with the Playwright MCP → open candidates → download full-res → verify → contact sheet for approval → log licence in `manifest.json`) and the licence rules (Pinterest/Behance/Dribbble = `reference-only` unless the source licence allows use).


### Reference-helper output ownership
`analyze_ref.py` refreshes only its numbered samples/sheets, hook strip, motion strips, palette, report, JSON and extracted audio/spectrogram. Inputs must live outside that analysis directory. Silent references skip audio/spectrogram/stems. Check `analysis.json` for this run's outputs; existing optional stems from older runs are not current results. FFmpeg/probe errors must not be reported as a successful analysis. Sheets contain at most 30 frames. Palette, brightness, motion and audio-onset numbers are rough signals for human inspection, not verified style values. ImageMagick is not required.
