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

| file | what |
|---|---|
| **`01-six-presets.mp3`** | the six presets **as they are now**, 16 s each, 2 s apart: tech 0:00 · minimal 0:18 · corporate 0:36 · energetic 0:54 · cinematic 1:12 · ambient 1:30 |
| **`05-AB-tech-levelmatched.mp3`** | tech, current vs plan B, level-matched. A 0–16 s · B 17.5–33.5 s |
| `06-AB-energetic.mp3` | energetic, the preset with the largest defect (+5.3 dB pluck), A/B level-matched |
| **`07-VO-mix-AB.mp3`** | full mix with Arabic VO + 6 SFX + ducking, current vs plan B |
| `vo-ar.mp3` | the Arabic VO used in `07` (synthetic stock ad read, not product copy) |

`plan_b_layers.json` and `plan_b_measurements.json` contain every number in this document.

---

## 8. What I need from you

Listen to `01` and `05` (and `07` if you want to judge the VO case), then tell me:

- **apply as planned** — I write the 9 numbers into `music-presets.json`, re-run the audio tests,
  and push to PR #33;
- **apply, but dial something back** — tell me which number and I'll re-measure it;
- **reject** — and say what you heard that the measurements missed.

`PLAN B IS NOT APPLIED.` The repository is untouched, PR #33 is open and unmerged, and all CI is
green on `d6cd5c4`.
