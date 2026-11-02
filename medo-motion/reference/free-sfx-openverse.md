<!-- Video Motion · sourcing free sound effects and recording attribution. -->
# Free sound effects: Openverse

**Default route for sound effects when the user has no paid audio service.** Openverse (run by WordPress) indexes millions of openly licensed sounds, many from Freesound. No account or key is needed for normal use.

## Commands (run from the project folder)
```
python "<skill>/scripts/openverse_sfx.py" search "whoosh" --n 8 --max-seconds 3
python "<skill>/scripts/openverse_sfx.py" get <id> --name whoosh-soft-01
```
`get` saves into `assets/sfx/`: the audio, `<name>.source.json` (full provenance), a credit line in `assets/sfx/ATTRIBUTION.md` when the licence is CC BY, and a `manifest.json` entry.

## Licence rules (enforced by the script)
| Licence | Allowed | What you must do |
|---|---|---|
| CC0, Public Domain Mark | ✅ | Nothing. Keep the source file for the record |
| CC BY | ✅ | **Credit the creator** in the post caption or end credits. The text is in `ATTRIBUTION.md` |
| CC BY-NC (non-commercial) | ❌ excluded | Not allowed in monetised/brand content |
| CC BY-ND (no derivatives) | ❌ excluded | Trimming or processing would break it |
| CC BY-SA (share-alike) | ❌ excluded | Syncing it to video can force the video's licence |

Use `--cc0-only` when the user wants zero credits. Tell the user plainly when a chosen sound needs a credit.

## How to search well
- English keywords work best: `whoosh`, `swoosh`, `click`, `ui click`, `pop`, `impact`, `thud`, `ding`, `riser`, `glitch`, `typing`, `paper`, `water drop`, `cassette`, `tv switch on`, `8-bit`, `marimba`.
- Each preset in `styles/` lists its own query hints.
- Search once per sound role, pick 2–3 candidates, download, and **audition** them (waveform/peak check with FFmpeg, then the mixed preview). A title is not proof of how it sounds.
- Many Freesound files arrive as high-quality MP3 previews. Fine for social video; label them honestly and don't call them lossless.
- Anonymous use is rate limited. Search sparingly; reuse sounds across scenes.

## Where it fits
1. The user's own licensed library (`assets/sfx`, catalog) → 2. **Openverse (free)** → 3. procedural sounds (`scripts/procedural_sfx.py`) → 4. ElevenLabs generation if the user has a key and approves the cost (`reference/elevenlabs-sfx.md`).
Placement, layering and mixing rules stay in `reference/local-sound-workflow.md`.

## Optional extra tools (not bundled)
- **Earshot** (MIT, CPU-only): an open-source audio toolkit for coding agents that can describe, match and synthesise sounds and build sound kits. It needs about 1.4 GB of models. Install only from its official repository after the user approves; the PyPI package named `earshot` is an unrelated project. Not tested with this skill.

Source checks: Openverse API queried 2026-10-26 (`/v1/audio/?q=whoosh&license=cc0,by&length=short` returned CC0 Freesound results with ready attribution text). Earshot: https://alphasignal.ai/news/earshot-gives-coding-agents-an-open-source-audio-feedback-loop
