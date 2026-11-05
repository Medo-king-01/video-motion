# Audition pack — procedural music + SFX

Committed so the audio can be listened to straight from the pull request: GitHub renders a player for
`.mp3` in the file view and in review comments, so nothing has to be downloaded.

**These are review artifacts, not a build input.** No code reads this folder; the engine renders its
own audio from `medo-motion/motion/music-presets.json`. Files here are 192 kbit/s MP3 on purpose —
the full-fidelity `.wav` masters are ~8× larger and stay out of Git.

Generated from `arena/f5286bd0-video-motion` at seed 7. Regenerate any of them with:

```bash
python tools/music_kit.py --preview docs/audition/01-six-presets.mp3 --force
bash docs/audition/make.sh          # if you have ffmpeg on PATH
```

---

# Decision record

Listened, compared, and decided on **2026-11-05**. Recorded here so the reasoning survives the
pull request.

| question | decision |
|---|---|
| default music level | **keep `level_db` = −3.0.** The 2 dB cut was auditioned and **rejected as a default**. |
| the −5 dB variant | kept in this folder and documented below as a **reference measurement**, not applied |
| layer rebalance (Plan B) | measured and documented, **not applied** |
| audio engine, presets, SFX | **unchanged** — see the verification at the bottom |

**What this means in code:** `music.level_db` remains `-3.0`
(`audio_mix.py:250` is the only default; `from_storyboard()` does not override it). Nothing in
`medo-motion/templates/procedural-reels/` or `medo-motion/motion/` was edited to produce the −5 dB
rendition — it exists only as a cue-sheet value inside `make.sh`'s A/B generator.

**Why keep the file:** the 8.0 → 10.0 dB VO-separation number is the useful part. If a future video
has a heavier voice-over or a denser script, `−5 dB` is now a **measured** option rather than a guess,
and `08-music-level-AB.mp3` is the reference for what it sounds like.

---

# Music level A/B — flat 2 dB cut, nothing else touched

**Requested:** lower the music bed by 2 dB, keep it clearly audible behind the VO, keep the VO in
front, **do not** change the SFX, the layer balance, the presets, or the audio engine.

**Done:** `music.level_db` from **−3.0 → −5.0** in the cue sheet. That is the single documented knob
for bed level; nothing else in the sheet moved. Ducking is untouched at
`amount 0.45 · attack 80 ms · release 320 ms · lookahead 40 ms`.

## The control that matters

| | A (music −3 dB) | B (music −5 dB) | change |
|---|---|---|---|
| music stem, pre-master | −25.43 dBFS | −27.43 dBFS | **−2.000 dB** (sample-exact ratio 0.794328) |
| SFX stem, pre-master | −13.47 dBFS | −13.47 dBFS | **0.00 — bit-identical** (`array_equal` = True) |
| VO stem | −20.68 dBFS | −20.68 dBFS | **0.00** |
| **music-to-VO ratio in the finished master** | −4.75 dB | −6.75 dB | **−2.00 dB** |
| **VO-to-music separation during speech** | 8.0 dB | **10.0 dB** | **+2.0 dB** |
| finished loudness | −14.80 LUFS | −14.80 LUFS | **0.00** |

That last pair is the one to read carefully:

- **8.0 dB** separation is tight — the bed is competing with the narrator.
- **10.0 dB** is inside the normal 8–14 dB range for a bed under speech: the words are clearly in
  front and the music is still present, not ducked into a background wash.
- It is **not** a "muffled/remote" setting. The bed is still the same arrangement, the same layers,
  the same brightness — only 2 dB further back.

## Listening

`08-music-level-AB.mp3` — A (music −3 dB) 0:00–0:20 · B (music −5 dB) 0:21.5–0:41.5. Both halves are
mastered to **−14.80 LUFS** so the quieter bed cannot win or lose on loudness alone.

## Status: rejected as a default, retained as a reference

`music-presets.json`, the layer levels, the presets, `music.py`, `audio_mix.py` and the SFX engine are
**unchanged**. The −5 dB setting exists only inside the A/B renders and this documentation.

`-3.0` remains the default in `audio_mix.mix()`; `from_storyboard()` does not set `level_db` at all,
so every generated sheet keeps the −3.0 default. If a specific video needs the quieter bed, set
`music.level_db: -5.0` on that one sheet — that is the supported way to use this measurement.

---

# Plan B — layer rebalance, measured but **not applied**

Status: **`music-presets.json` is byte-identical to commit `d6cd5c4`.** Nothing in this document has
been written to the repo. It is pending your listen.

---

## 1. Your five conditions, and where each one landed

| # | your condition | how it was handled |
|---|---|---|
| 1 | calibrate each preset independently | every preset was measured and corrected on its own; no global target was imposed |
| 2 | keep each preset's character, no forcing one spectrum | `hat` was lifted **only** in the three presets whose written intent promises crispness. `minimal`, `cinematic`, `ambient` keep their soft top on purpose |
| 3 | `LAYER_TARGETS` is not musical truth | **I stopped using it.** The new reference is *the balance the six presets already agree on among themselves* (§3) |
| 4 | A/B same seed/arrangement, ≤ 0.2 LUFS | **level-matched to 0.00 LUFS** with the EBU R128 meter, not raw RMS (§5) |
| 5 | test with Arabic VO + SFX, not music alone | built a 20 s mix: music + 6 SFX + your language VO + ducking; A and B both mastered to −14.50 LUFS (§6) |

**Your point 4 caught a real flaw in what I sent you last time.** The earlier A/B was
A = −18.88 dBFS RMS vs B = −21.35 dBFS — a **2.4 dB** bias, so the louder version would have won on
loudness alone. That file is discarded; `05-AB-tech-levelmatched` replaces it.

---

## 2. What actually changed in my thinking

I was wrong to treat this as "the high end is missing". Two findings reframed it:

**a. The drums are not broken.** Measured against the kick, the presets already agree:

| | clap | hat | bass |
|---|---|---|---|
| tech | −12.7 | −9.6 | −8.0 |
| corporate | −12.7 | −10.5 | −7.9 |
| energetic | −12.4 | −9.5 | −8.4 |

That is a coherent, conventional drum balance. There is nothing to "fix" in it.

**b. The pluck is above the kick.** That is the actual defect:

| preset | pluck − kick |
|---|---|
| tech | **+4.1 dB** |
| energetic | **+5.3 dB** |
| minimal | **+3.0 dB** |
| corporate | **+2.3 dB** |
| cinematic | −6.1 dB |
| ambient | no drums |

An arpeggio sitting 2–5 dB *above* the kick drum is wrong in every genre the brief names. This alone
explains most of the "dull" reading: the arpeggio's energy is concentrated in one octave
(**95.5 % between 500–1000 Hz**), so it dominates the midrange while contributing almost nothing
above 6 kHz — pushing everything else down in relative terms.

**c. `cinematic`'s clap is silent by intent, not by fault.** Its groove is `clap: "off"`, so the
0.18 level never sounds. I had flagged it as a −34.5 dB defect; it is not a defect. Left alone.

---

## 3. The method

1. Reference = kick. Measure every layer solo against the kick, per preset.
2. `pluck` gets a per-preset target *below* the kick, chosen from that preset's own `why` text.
3. `hat` is multiplied **only** where the intent says bright; the soft presets are untouched.
4. No other layer moves. Tempo, key, scale, progression, sections, grooves, tone: **all untouched.**

---

## 4. The plan — 6 presets, 9 numbers

| preset | change | why |
|---|---|---|
| **tech** | `pluck` 0.72 → **0.22** | was +4.1 over kick; intent says "bright saw pluck", i.e. a colour |
| | `hat` 0.60 → **0.78** | intent says "bright … product demo"; ×1.30 |
| **minimal** | `pluck` 0.28 → **0.06** | was +3.0 over kick; intent says "almost nothing" |
| | hat unchanged | intent says "leaves the VO room" |
| **corporate** | `pluck` 0.62 → **0.27** | was +2.3 over kick |
| | `hat` 0.42 → **0.63** | intent says "confident", not "soft"; ×1.50 (its quarter-note pattern needs more level than 16ths to read) |
| **energetic** | `pluck` 0.80 → **0.24** | was +5.3 over kick — the worst offender |
| | `hat` 0.78 → **1.05** | intent says "a hook that has to grab"; ×1.35 |
| **cinematic** | `pluck` 0.16 → **0.11** | −6.1 over kick is already fine; a small trim only |
| | hat unchanged | intent says "weight instead of a beat" |
| **ambient** | `pluck` 0.30 → **0.14** | no drums; the pluck must stay under the pad bed |
| | hat unchanged | no drums at all in this preset |

Loudness targets and every other control are untouched — the per-preset `levelTrimDb` master step
already normalises the finished bed, so this plan does not change how loud anything ends up.

---

## 5. Measured result of the plan

| preset | energy > 6 kHz before | after | change |
|---|---|---|---|
| tech | 2.57 % | **7.97 %** | 3.1× |
| minimal | 1.52 % | 2.52 % | 1.7× — stays soft by design |
| corporate | 1.35 % | **5.72 %** | 4.2× |
| energetic | 2.74 % | **11.01 %** | 4.0× |
| cinematic | 2.66 % | 2.66 % | unchanged — weight preset |
| ambient | 6.26 % | 6.57 % | essentially unchanged — no drums |

For reference, contemporary pop/hip-hop masters typically sit around **5–15 %** of energy above 6 kHz.
`minimal` and `cinematic` deliberately stay under that: they are the "under the words" presets, and
forcing them bright would violate your condition 2.

### A/B level matching (your condition 4)

| file | A (current) | B (plan) | delta |
|---|---|---|---|
| `05-AB-tech-levelmatched` | −18.00 LUFS, TP −4.0 | −18.00 LUFS, TP −2.0 | **0.00 LUFS** |
| `06-AB-energetic` | −18.00 LUFS | −18.00 LUFS | **0.00 LUFS** |
| `07-VO-mix-AB` (with VO + SFX) | −14.50 LUFS | −14.50 LUFS | **0.00 LUFS** |

Measured with ffmpeg's `ebur128` reference meter, the same meter the master step uses.

---

## 6. The VO + SFX test (your condition 5)

`07-VO-mix-AB.mp3` — 20 s cue sheet at −14.50 LUFS, built through the real `audio_mix.mix()` path:

```
music:   tech, seed 7, level −3 dB
SFX:     riser 0.0s · whoosh 3.0s · swipe 7.0s · impact 11.0s · chime 15.0s · pop 19.0s
VO:      Arabic, 17.53 s, starts at 1.2 s
ducking: 0.45 (−7 dB), attack 80 ms, release 320 ms, 40 ms lookahead
```

A = 0–20 s (current layers). B = 21.5–41.5 s (plan B). Both were re-mastered to the identical
−14.50 LUFS afterwards, so the only difference you can hear is the balance.

The VO is synthetic (`generate_speech`, a stock ad read, not your product copy) — it exists to test
whether the bed stays out of the way of Arabic speech, not to be final narration.

---

## 7. Files to listen to

| file | what | status |
|---|---|---|
| **`01-six-presets.mp3`** | the six presets as shipped, 16 s each: tech 0:00 · minimal 0:18 · corporate 0:36 · energetic 0:54 · cinematic 1:12 · ambient 1:30 | reference |
| **`08-music-level-AB.mp3`** | music −3 dB (0:00–0:20) vs −5 dB (0:21.5–0:41.5), level-matched, VO + SFX identical | **decided: −3 dB stays default** |
| `07-VO-mix-AB.mp3` | full mix, Arabic VO + 6 SFX + ducking, current vs Plan B | reference |
| `05-AB-tech-levelmatched.mp3` | tech, current vs Plan B, level-matched | plan, not applied |
| `06-AB-energetic.mp3` | energetic (largest Plan B defect, +5.3 dB pluck), A/B level-matched | plan, not applied |
| `vo-ar.mp3` | the Arabic VO used in `07` and `08` (synthetic stock ad read, not product copy) | input |

`plan_b_layers.json` and `plan_b_measurements.json` hold every Plan B number.

---

## 8. Verification — nothing was applied

Executable, not prose: `bash docs/audition/verify.sh` (exit 0 = clean). Check 5 delegates to
`check_plan_b.py`, which compares the plan and the presets **as numbers with a tolerance** — the first
version compared JSON as strings, so a plan value of `0.224` vs a hand edit of `0.22` reported
"not applied" while the file had moved.

```
  PASS  audio_mix.py default level_db is -3.0                    1
  PASS  no 'level_db: -5' anywhere in engine/presets/tools       0
  PASS  from_storyboard() does not set level_db                  0
  PASS  music-presets.json identical to 82d8c3e                  identical
  PASS  Plan B layer values                                      not applied
```

The same facts, spelled out:

| check | result |
|---|---|
| `music.level_db` default in `audio_mix.py` | **−3.0** (line 250, unchanged) |
| `from_storyboard()` sets `level_db` | **no** — generated sheets inherit −3.0 |
| any `level_db: -5` in engine / presets / tools | **none** |
| `music-presets.json` vs `d6cd5c4` | **byte-identical** |
| `medo-motion/templates/procedural-reels/` vs `d6cd5c4` | **unchanged** |
| `ruff check .` | clean |
| audio test suites (`test_audio_engine`, `test_music`, `test_sfx_engine`, `test_audio_mix`) | **70 passed** |

Plan B and the −5 dB cut are both **proposals recorded as measurements**. Neither is in the codebase;
both can be recalled from this folder if a future project needs them.

---

## 9. Open item

Plan B (the layer rebalance: `pluck` down in all six presets, `hat` up in the three whose own
description promises brightness) is **still awaiting a verdict**. It is independent of the level
decision above — it changes the *internal balance* of the bed, not its level in the mix. See §3–§5 and
`05` / `06` if you want to judge it later.
