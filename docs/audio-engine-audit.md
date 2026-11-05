# Audio Engine Audit — target vs. reference

Date: 2026-11-05 · Branch: `arena/f5286bd0-video-motion` (from `main` @ `46e0229`)
Status: **audit before implementation** (no code changed yet)

---

## 1. Working tree and branch

```
branch   arena/f5286bd0-video-motion
main     46e0229 feat: add brand-locked cover and thumbnail generator
status   clean (nothing to commit)
```

`main` is untouched. Work happens on this branch only; nothing is merged.

## 2. What the target already has (measured, not assumed)

| Capability | Where | State |
|---|---|---|
| 15 procedural SFX | `medo-motion/templates/procedural-reels/sfx.py` | `BANK` = pop, blip, click, tick, zip, chime, sparkle, whoosh, swipe, noise, riser, impact, stomp, sub, glitch |
| SFX catalogue (family + base gain + tags) | same file, `CATALOG` | complete and asserted equal to `BANK` by `tests/test_sfx.py` |
| Stereo bus + constant-power pan | `sfx.bus()`, `sfx.place()` | works; `pan` accepts a scalar or a (start, end) glide |
| Cue sheets | `sfx.bus(length, cues)` | `t`, `sfx`, `gain`, `pan`, `seed` |
| Transition-linked cues | `sfx.cues_for_transitions()` + `transitions.json` (14 transitions, each declares `sfx`) | works |
| Rhythm grid cues | `sfx.grid_cues()` | one character per sixteenth, `k h s p z w` |
| VO ducking | `sfx.duck()` + `mix.py` inline | one-pole envelope, depth 0.62 |
| Music bed | `mix.py` **inline only** (Am–F–C–G, 76 BPM, hard-coded) | not a module, not configurable, not reusable |
| Render integration | `mix.py` → `out/final_audio.wav` → mux in `docs/length.md` | works for engine P |
| Loudness | two-pass `loudnorm` → −14.5 ±0.3 LUFS, TP ≤ −1.5 dBTP | works, brand-locked |

Tests already present: `tests/test_sfx.py` (13 tests), `tests/test_transitions.py`,
`tests/test_rhythm.py`, `tests/test_media_qa.py`, `tests/test_stage_gate.py`.

## 3. What the reference (`majedphotos/video-ad-editor`) actually does

Verified by executing it locally, not by reading alone:

```
python3 -c "A.build_bed(tl, music, 16.0, seed=7)"
bed (768000, 2) float64 · finite True · peak 0.828 · rms 0.2067 · deterministic True
whoosh 1.16 s anchor 0.25 · riser 1.50 s anchor 1.50 · impact 1.80 s anchor 0.00
```

Its architecture (`video-ad-editor/motion/audio.py`, 559 lines):

1. **One generator class `SFX`** with 14 types (whoosh, reverse-whoosh, riser, impact, boom,
   sub-drop, glitch, tick, typing, shimmer, pop, swoosh-pass, scratch, slide). Each returns
   `(stereo signal, anchor seconds)`, where `anchor` says *which point of the sound must land
   on the event* (riser/reverse-whoosh **end** there, whoosh/swoosh **peak** there, the rest
   **start** there). That anchor idea is the single most useful thing in the file.
2. **`build_bed(timeline, music, duration, seed)`** — a layered, beat-quantised bed:
   - sections `intro · build · drop · break · outro · stop` with different arrangements;
   - one-shots rendered once (`kick`, `clap`, `hat_c`, `hat_o`, `snare`) then `put()` on a 16th grid;
   - per-bar tonal parts: pad (detuned PolyBLEP saws), bass, arp (with ping-pong delay);
   - **snare roll** whose rate doubles in the last bar of a build;
   - **crash accent** on a `drop` boundary;
   - a **phone layer** (`music.top`): bright pluck 0.4–3 kHz + hat/snap 5–10 kHz, because
     kick/bass/pad below 150 Hz vanish on a phone speaker;
   - **sidechain pump** from the kick list applied to pad/bass/arp (0.55 depth, 0.11 s);
   - **break drums with a low-pass that opens** across the break;
   - `stop` = a true gated silence with 4 ms ramps, reverb tails included.
3. **DSP helpers**: `polyblep_saw` (alias-free saw), block-wise time-varying `sweep()`
   (filter whose cutoff follows a function of time), convolution `reverb()` from a
   decorrelated noise IR, `soft()` tanh saturation, `st()` constant-power pan.
4. **`vo_envelope(vo, look, att, rel)`** — 5 ms hop RMS → threshold at 6% of peak → attack/release
   one-pole → **lookahead shift** so the duck arrives before the word.
5. **`limiter()`** — stereo-linked lookahead peak limiter (`maximum_filter1d` + `minimum_filter1d`
   + release smoothing), and a `loudnorm()` loop that limits *first* so `loudnorm` stays linear.
6. Musical vocabulary: `SCALES` (minor/major/dorian/phrygian), `KEYS`, `deg()` degree→semitone.

## 4. License position

| Repo | License | Consequence |
|---|---|---|
| target `Medo-king-01/video-motion` | **no OSI licence**; `medo-motion/LICENSE.md` — reuse needs separate permission | this work is for the owner |
| reference `majedphotos/video-ad-editor` | **MIT**, © 2026 Majed Alzaabi | adaptation is legal **with attribution** |

The target has an established policy for exactly this (`docs/video-ad-editor-fit.md`,
`assets/CREDITS.md` line 31): MIT ideas from this repo are **re-written natively against the
studio's own contracts** and credited. `tests/test_video_ad_editor_upgrades.py` already enforces
that attribution. This work follows the same rule: the *algorithms and architecture* are adapted,
the reference file is not vendored, and every adopted idea is credited in `CREDITS.md`.

## 5. Adopt vs. re-implement

**Adopt (as algorithms, re-written for this codebase):**

- the `anchor` concept for SFX (event timing precision);
- section-driven bed (`intro/build/drop/break/outro/stop`) with per-section arrangement rules;
- one-shot rendered once → placed on a 16th grid (cheap + deterministic);
- per-bar pad / bass / arp generation from a key + scale + progression;
- the **phone/top layer** idea (a reel is watched on a phone speaker);
- kick-driven **sidechain pump**;
- low-pass that opens across a break; snare roll into a transition; crash on the drop;
- `vo_envelope` with attack/release **and lookahead**;
- stereo lookahead **limiter** and "limit before loudnorm so it stays linear".

**Do not adopt:**

- its I/O (`project.json` / `timeline.json` / `sfx.json` schema) — this studio has
  `plan/beats.json`, `plan/copy.json`, cue sheets and `transitions.json`; a second timeline is
  explicitly forbidden by the task;
- forcing 48 kHz and hard-erroring on any other rate (this studio's kit runs at 44.1 kHz and the
  VO master is 24 kHz);
- 24-bit-only writing, `SystemExit`-style error handling, and the script-style `main()`.

## 6. Defects found in the target (each measured, each fixed in this PR)

1. **`bus()` silently truncates** a cue longer than the requested length
   (impact is 0.70 s, `bus(0.2)` returns 0.20 s with no warning) → you lose a transient and only
   notice by ear.
2. **`duck()` returns a shorter array than it was given.** `bus` 2.00 s + VO 1.00 s → 1.00 s.
   Any caller that assumes `len(out) == len(bus_buf)` gets a misaligned mix.
3. **Ducking is normalised by the global peak of the whole VO**, so once the reel contains one
   loud word every quieter line under-ducks. Measured: a 0.05-peak word ducks only **6%** instead
   of 62% → speech leaks over the music.
4. **No lookahead and no separate attack** — the gain only starts falling *after* the first sample
   of speech. Attack is whatever the one-pole gives.
5. **Sample rate is a module constant** (`SR = 44100`) baked into every filter (`butter(..., SR/2)`),
   so 48 kHz output is impossible without changing global state mid-flight (measured: after
   `sfx.SR = 48000` the filters silently use the new rate while existing buffers do not).
6. **No music engine at all** — the only music is ~35 hard-coded lines inside `mix.py` that are
   tied to one episode (`import scenes`, `PT`, fixed Am–F–C–G, fixed 76 BPM).
7. **`mix.py` writes fixed filenames** (`out/final_audio.wav`, `out/final_audio_lim.wav`,
   `out/final_audio_trim.wav`) and `os.replace`s them — a second concurrent run in the same project
   overwrites the first.
8. **`tools/sfx_kit.py --demo`** takes a path and converts to mp3, deleting the WAV — fine — but
   `--bank` and `--cues` also write into whatever path is given with no "already exists" guard.

## 7. Plan for this PR

```
medo-motion/templates/procedural-reels/audio_engine.py   NEW  shared DSP core (sample-rate safe)
medo-motion/templates/procedural-reels/music.py          NEW  procedural music engine (7 layers, 6 presets)
medo-motion/templates/procedural-reels/sfx.py            EDIT keep BANK/CATALOG/bus API, add
                                                              anchor, sr-aware filters, duck fix, layering
medo-motion/motion/music-presets.json                    NEW  presets + section shapes (data, not code)
tools/music_kit.py                                       NEW  CLI: render / preview / presets / validate
tools/sfx_kit.py                                         EDIT add --sr / --music, existing flags unchanged
tools/audio_mix.py                                       NEW  one audio timeline: VO + music + SFX + duck + loudnorm
docs/audio.md                                            EDIT current architecture + examples
tests/test_music.py, tests/test_audio_engine.py          NEW  determinism, BPM, SR, ducking, mixing, CLI
```

Backward compatibility is a hard requirement: every existing name (`BANK`, `CATALOG`, `bus`,
`duck`, `place`, `render_bank`, `cues_for_transitions`, `grid_cues`, `write_wav`, `SR`) keeps its
current behaviour for existing callers, and `tests/test_sfx.py` must pass unmodified.

---

# 8. What was actually shipped (and what the measurements say now)

Every defect in §5 has a regression test. The numbers below come from this branch, not from intent.

| # | Defect (before) | Fix | Test that pins it |
|---|---|---|---|
| 1 | `bus()` silently cut a 0.70 s impact into a 0.20 s buffer | the buffer is exactly `length` (a mixer's timeline is authoritative), and `bus.last_truncated` / `bus.last_clipped` report what did not fit instead of dropping it | `test_sfx_engine::test_truncation_is_reported_instead_of_silently_eaten`, `::test_an_early_riser_is_clipped_not_reported_as_truncated` |
| 2 | `duck()` returned `min(len(vo), len(bus))` → everything after the voice ended was lost | returns the bus length; the voice is zero-padded | `test_sfx_engine::test_duck_keeps_the_bus_length_and_ducks_quiet_audio` |
| 3 | no lookahead in the ducking envelope | `duck_gain` looks ahead 40 ms — the bed is down *before* the word starts | `test_audio_engine::test_duck_gain_has_lookahead_and_no_steps` |
| 4 | envelope divided by the loudest peak → a quiet line ducked 6 % | absolute dBFS gate; a 0.05-peak line now ducks as hard as a loud one | `test_audio_engine::test_duck_gain_is_absolute_not_normalised_by_the_loudest_word`, `test_audio_mix::test_ducking_actually_lowers_the_bed_under_the_voice` |
| 5 | `sfx.SR` was baked into `bp()` at import time | every generator takes `sr=`; filters are built from the rate being rendered | `test_sfx_engine::test_generators_render_natively_at_48k`, `test_audio_engine::test_engine_has_no_module_level_rate_constant_in_filters` |
| 6 | no music module — 35 hard-coded lines inside `mix.py` | `music.py` + `motion/music-presets.json`; `mix.py` untouched for existing projects | `test_music` (20 tests) |
| 7 | fixed output filenames → concurrent runs clobbered each other | every writer refuses to overwrite unless `overwrite=True` / `--force` | `test_sfx_engine::test_render_bank_never_overwrites_by_accident`, `test_music::test_cli_refuses_to_overwrite` |

Defects found **while** fixing the seven above (each is now a test):

8. **`audio_engine.true_peak()` under-read by up to 13 dB** on negative-only / symmetric stereo —
   `x.max(axis=1)` collapses a symmetric L/R pair to 0 (measured: a −0.9 signal read as 0.2), and the
   oversampler assumed silence past the last sample (a loud-ending file read **+1.1 dB** over its real
   peak). Now magnitude-collapsed and edge-reflected: `test_audio_engine::test_true_peak_sees_negative_and_asymmetric_material`.
9. **`tools/ffprobe_shim.py` reported the wrong audio length** — it divided `stream.duration` by a
   hard-coded `1e6` instead of multiplying by the stream time base: an 8.0 s WAV read as **0.384 s**.
   Fixed and verified for WAV and H.264.
10. **Peak normalisation was doing the mixing.** Every layer solo was normalised to the same peak, so
    "turn the hats down" made the hats *louder* (measured: kick solo −15.6 dBFS vs full bed −20.5).
    Now a fixed `MASTER_GAIN`: a solo layer is always quieter than the arrangement
    (`test_music::test_layers_are_independently_mixable`).
11. **Presets were 15 dB apart in loudness** (`energetic` −14.6 vs `ambient` −30.1 dBFS), so changing
    preset changed the volume, not the music. `levelTrimDb` is a *measured* per-preset correction; all
    six now sit within 4 dB (`test_music::test_presets_are_level_matched_by_the_measured_trim`).
12. **A music change was a hole** — two fades meeting at the same instant (measured −48.8 dBFS at the
    change). Now a 0.45 s cross-fade with the incoming segment at full level on the beat
    (`test_audio_mix::test_a_music_change_is_a_cut_not_a_hole`).
13. **Fixed 1.2 s fades ate short segments** (a 5 s sting lost a quarter of its music). Fades are
    proportional to the segment (`test_music::test_a_short_bed_does_not_fade_itself_away`).
14. **`loudnorm` and `ebur128` disagree** by 0.3 LUFS on the same master. The report now quotes the
    reference meter and trims the residue within ±2 dB, yielding to the true-peak ceiling.
    Verified end-to-end: **−14.5 LUFS / −1.7 dBTP** on a 20 s reel with narration
    (`test_audio_mix::test_the_report_quotes_a_measured_master`).

## Backward compatibility (checked, not assumed)

`tests/test_sfx.py` (13 tests) and `tests/test_rhythm.py` pass **unmodified**. That file pinned two
things this work had to respect: `bus()` must return exactly the requested length, and cue times must
mean "the buffer starts here". Both are now explicit contracts, and event anchoring is opt-in
(`anchored=True`), documented in `docs/audio.md`.

## What was deliberately NOT taken from the reference

- Its `project.json` / `timeline.json` schema (this repo already has a plan/beat contract).
- Forcing 48 kHz (the repo is 44.1 kHz end-to-end; both are now first-class).
- Its 24-bit writer (the pipeline is 16-bit PCM and the mux re-encodes anyway).
- Its licence header as *code*: the algorithms were re-written against this repo's interface, with
  attribution in `assets/CREDITS.md` and the reasoning here. This matches the repo's established
  policy (`docs/video-ad-editor-fit.md`).
