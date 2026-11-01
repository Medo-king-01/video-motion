# Narration scripting, generation and timing

Recorded speech or any user-chosen TTS provider is acceptable. When ElevenLabs is the provider, this guide is the rule set: **Eleven v4 only** (§10.1). Final timing always comes from the delivered audio, never from word-count estimates.

> Detailed production guidance: load only for the current task. The SKILL.md entrypoint and current user/project instructions take precedence. Section numbers below refer to this production manual; use the entrypoint guide table to locate a different topic. Do not assume any installed tool, private library, universal approval or specific narration provider.

> Narration guide: written for Eleven v4 from ElevenLabs' documentation and launch material plus reported user experience (Sources at the end). ElevenLabs states that model behaviour can change after release, so re-check the docs when results drift.

## 10. ElevenLabs voiceover (Eleven v4)

### 10.1 Model policy (hard rule)
| Use | `model_id` | When |
|---|---|---|
| Every delivered narration, dialogue or approved take | `eleven_v4` | Default. Up to 10,000 characters per request, 90+ languages including Arabic, audio tags, IPA, request stitching, Text to Dialogue. |
| Quick preview only | `eleven_v4_turbo` | A very short sample, a voice audition or "show me how this line would sound". Never the delivered take. About half of v4's list price per character. |

- Never use `eleven_v3` (previous generation), Multilingual v2, Flash or Turbo v2/v2.5 for narration, not even as a fallback. If v4 is unavailable or failing, stop and report; never switch model or provider silently.
- Always send `model_id` explicitly: Text to Dialogue falls back to `eleven_v3` when it is omitted.
- If `eleven_v4_turbo` is not offered for HTTP text-to-speech on the account (`can_do_text_to_speech` in `GET /v1/models`), preview with `eleven_v4` on a short excerpt instead.

### 10.2 Settings that exist on v4 (and ones that don't)
- v4 has only **Stability** and **Similarity**. **Style and Speed are not available, and SSML (including `<break>`) is not supported.** Pacing is written into the text (§10.4), not set with a slider.
- **Stability** (API default 0.5): lower = wider emotional range and more take-to-take variation; higher = steadier, can become monotonous. Start at 0.5. Energetic sales/UGC read: try 0.4–0.5 and go lower only if the read stays flat (one guide reports random variation below ~0.4). Calm, trust-first read (health, finance, B2B): 0.55–0.7.
- **Similarity** (API default 0.75): higher = closer to the source voice, but can reduce naturalness and copies a clone's recording flaws. Lower it slightly if a clone sounds harsh or noisy.
- **Seed** (0–4294967295) gives best-effort repeatability. Record seed and settings for every approved take so one line can be regenerated in the same performance.
- **Output:** `mp3_44100_192` (Creator tier and above) by default; `mp3_44100_128` works on every tier. WAV/PCM output needs a higher tier (44.1 kHz requires Pro); prefer `wav_48000` when the account allows it, because the video ships AAC 48 kHz.

### 10.3 Audio tags: direct the performance
Tags are square-bracket cues inside the text; the same syntax works on v4 and v4 Turbo. They are followed more reliably than on earlier models, but ElevenLabs still calls them "not yet perfect", so audition every tagged line.
- **Placement:** put the tag immediately before the words it changes. The delivery carries forward, so add a new tag only where the delivery changes, at most one per clause. Contrasting tags on the same words blur the performance.
- **Combine** inside one bracket with commas: `[whispering, playful]`, `[nervous, trying to sound confident]`.
- **Free-form direction works:** `[like a sports commentator, speeding up]`, `[tired, trying to sound cheerful]`.
- **Palette** (from ElevenLabs' v4 tag list):
  - Emotion: `[excited]` `[playful]` `[amazed]` `[proud]` `[curious]` `[thoughtful]` `[trusting]` `[peaceful]` `[confused]` `[anxious]` `[tired]`
  - Delivery and volume (raise or lower the voice): `[whispers]` `[softly]` `[quietly]` `[hushed]` `[barely audible]` `[low]` `[booming]` `[shouts]` `[disbelief]`
  - Pacing: `[slowly]` `[drawn out]` `[rushed]` `[snappy]` `[pause]` `[long pause]`
  - Reactions: `[laughs]` `[sighs]` `[gasps]` `[clears throat]` `[gulp]`
  - Accents: `[British accent]` etc. are inconsistent across voices; test before relying on them.
- **Describe the voice, not a noise.** v4 can also generate sound effects, so a vague one-word tag may come out as a sound. Write `[low, gravelly voice]`, not `[gravelly]`. Keep SFX tags (`[applause]`, `[door creaking]`) out of narration; SFX are produced and mixed separately (`reference/elevenlabs-sfx.md`).
- **Stay inside the voice's range.** A calm narrator will not shout convincingly and a whispery voice will not boom. If a tag does nothing, change the voice or the tag; do not stack more tags.
- **Audit reused scripts:** tags that older models ignored can now fire. Search for stray brackets before generating.
- Example: `[warmly] Most teams lose hours every week… [curious] but what if that just — stopped? [excited] Meet Flow.`

### 10.4 Pacing, pauses and emphasis (no speed slider)
- Line breaks and short sentences = breaths. `…` = hesitation or short beat, `—` = quick beat, `[pause]` / `[long pause]` = a real gap (test with the chosen voice). Empty line = section break.
- CAPS on one word = emphasis (at most one per section). Exclamation marks lift energy without a tag.
- **Too fast** (users report v4 can read fast): shorter sentences, more commas or `…`, `[slowly]` before the line, or split a long sentence. Last resort in post: FFmpeg `atempo=0.95` to `0.97` on the VO stem (keeps pitch); keep the change small.
- **Too theatrical** for a restrained read: raise Stability, remove emotion tags, write plainer sentences, or choose a calmer voice (some voices cannot be made monotone).

### 10.5 Pronunciation, numbers and Arabic
- **IPA:** v4 reads IPA wrapped in forward slashes inside the text: `Niamh /niːv/`. Include stress marks (ˈ ˌ), use it only on words that need it, and test with 2–3 takes. SSML phoneme tags do not apply to v4. Alias respelling ("NOH-shun") remains a fallback.
- **Write as spoken:** numbers, prices, dates, times, units, symbols, short forms like "Dr." and URLs ("forty-two dollars and fifty cents", "one hundred percent", "Doctor", "dot com"). Acronyms read letter by letter (SEO, GPT) are not spelled out: keep them in English capitals (see Arabic below). Text normalization is on by default but is the usual source of misreads.
- **Arabic:** write the script in Arabic, in the dialect you want spoken (the model takes the language from the text). Use a voice whose native accent is that dialect, such as a clone of a Saudi speaker for Saudi delivery: v4 keeps the source accent in the same language but switches to a native accent in other languages. Unvowelled Arabic is ambiguous for TTS, so when a word is misread, add tashkeel to that word only and regenerate. Write numbers as Arabic words. `language_code: "ar"` can enforce the language and its normalization.
  - **English acronyms and words inside an Arabic script** (the text sent to ElevenLabs only, not the on-screen captions): (1) acronyms read letter by letter (SEO, CEO, CES, GPT…) are always written in English capitals, never in Arabic letters («سيو» was read as "Co" instead of SEO). When an acronym is joined to a word, write the whole name in English with a space: `Chat GPT`. (2) English words and names read as ordinary words are written in Arabic letters as they are pronounced, because they sound better that way: «قوقل»، «كلود كود». (3) AI works either way: «إيه آي» or `AI`. Examples: «صاروا يسألون Chat GPT وقوقل إيه آي.» «عشان كذا جمعت لك دليل AI SEO.» «تحطّه في كلود كود.» «أو اكتب كلمة SEO، وأرسله لك على طول.»

### 10.6 Length, chunking and continuity
- v4 accepts up to 10,000 characters per request, but generate **per scene or paragraph**: retakes are cheaper, and ElevenLabs' troubleshooting guide says accent and quality are most consistent under ~800–900 characters per generation. Avoid tiny fragments; v4 performs better with context.
- Keep voice, model, Stability, Similarity and seed identical for every chunk of one video.
- **Continuity:** pass the previous chunk's `request-id` (response header) as `previous_request_ids` (max 3, no older than two hours; ElevenLabs says stitching is significantly more reliable on v4), or pass `previous_text` / `next_text`. Still listen across every seam.
- Splice only on a pause, trim leading and trailing silence, match the integrated loudness of all chunks before the mix, and use a short crossfade at the cut.

### 10.7 Voice from an attached sample (the user's normal route)
When the user names a voice and attaches an audio sample:
1. **Ask once which case it is.** (a) An ElevenLabs library voice: find it with the helper's `voices --search "<name>"` and use its `voice_id`; no clone is needed (if a Voice Library voice does not appear in the results, the user adds it to My Voices in the ElevenLabs app first). (b) A voice the user owns or has the speaker's permission to clone: Instant Voice Clone (IVC). Never clone without the user explicitly confirming the right and the speaker's consent (ElevenLabs requires this confirmation). If they cannot confirm, offer a similar library voice, their own recording, or getting permission.
2. **Check the sample locally** with the helper's `clone` pre-check or ffprobe/ffmpeg (nothing is uploaded). Ideal: 1–2 minutes of one speaker, no music, reverb or background noise, consistent tone and an energy that matches the target read (a flat sample gives a flat clone). Avoid more than ~3 minutes. MP3 at 128 kbps or higher (192 preferred; WAV does not improve clones). About −23 to −18 dB RMS with true peak ≤ −3 dB. v4 reproduces recording flaws (clipping, plosives, uneven EQ, volume jumps), so fix or replace a bad sample rather than blaming the model. ElevenLabs says a v4 IVC can work from ~10 s, but 1–2 minutes remains its recommendation.
3. Use `remove_background_noise` only when the sample really contains noise; on clean audio it can make the clone worse.
4. **Create the clone once** (helper `clone`, explicit approval), then store `voice_id`, sample file name and SHA-256 in TASTE.md §6 and reuse it. Each clone made from the same audio sounds slightly different; keep the original samples. Accent and tone cannot be changed after creation, only by changing the samples.
5. Professional Voice Clones must be retrained for v4 in the ElevenLabs app (My Voices → "+" next to Eleven v4). IVCs need no extra training step. Designed voices may sound less expressive on v4; prefer library voices or clones for final reads.
6. **Approve the voice on a short preview** (Turbo, or a short v4 excerpt) before generating the whole script.

### 10.8 Interviews and multi-speaker dialogue
- Use Text to Dialogue with `model_id: eleven_v4` (set it explicitly). Up to 10 distinct voices per request; keep the total text at or under 2,000 characters per request (split longer interviews into exchanges and join them on pauses); give speakers clearly different voices.
- Tag each turn separately. End a cut-off line with a hyphen (`Is this seat-`) and start the interruption with `[jumping in]`; use `...` for a trailing or hesitant line.
- The with-timestamps response includes `voice_segments` (who speaks when); use them for cuts, split-screen switches and lower thirds.

### 10.9 Known problems and verified fixes
| Problem | Fix |
|---|---|
| Tag read aloud or turned into a sound | Describe the voice in plain words (`[low, gravelly voice]`); put the tag directly before its words; keep SFX tags out of VO. |
| Tag has no effect | The voice cannot perform it: choose a voice whose range includes it; try slightly lower Stability. |
| Inconsistent takes | Generate 2–3 takes per scene and pick the best; give more context; fix the seed. |
| Reads too fast | §10.4. |
| Over-acting | Raise Stability, use fewer tags, choose a calmer voice. |
| Accent drift or wrong accent | Script in the target language; native voice or clone for that dialect; ≤ ~900 characters per generation; accent tags only after testing. |
| Glitch, muffled patch or sharp breath between paragraphs | Regenerate that chunk; if it sits at a paragraph boundary, regenerate the paragraph before it. |
| Volume or mood jump at a seam | Request stitching with identical settings and seed; loudness-match chunks; splice on a pause. |
| Clone noisy, harsh or unlike the speaker | Clean, consistent 1–2 minute sample; noise removal only for noisy audio; slightly lower Similarity; re-clone from better audio. |
| Name or brand mispronounced | IPA in slashes on that word, or an alias respelling; test 2–3 takes. |
| Numbers or dates misread | Write them as words. |
| Approved voice sounds different weeks later | Models are updated: keep the approved take, settings and seed, and re-audition before a new batch. |

### 10a. Writing the script (deliverable before any build)

**Length → word budget** (estimate for English; natural VO ≈ 2.3–2.6 words/s; leave ≈ 1.5 s at the end for logo/CTA hold). Rates vary by voice and language and v4 can read faster, so measure the first approved take and recalibrate:
| Video | Words (VO) | Lines |
|---|---|---|
| 15 s | 30–38 | 4–6 |
| 30 s | 65–75 | 8–12 |
| 45 s | 100–110 | 12–16 |
| 60 s | 135–150 | 16–22 |
| 90 s | 200–220 | 24–32 |
Count the words in the paste block (tags excluded) and state the estimate: `≈ 142 words ≈ 58 s at 2.45 w/s`.

**Writing rules**
- One idea per line; short sentences (≤ 14 words). Line breaks = natural breath pauses; `…` = hesitation; `—` = short beat. Empty line = longer pause between sections.
- Hook in the first line (≤ 3 s, ≤ 8 words). CTA = last line, word-for-word what appears on screen.
- Write numbers, units, symbols and URLs **as spoken**: "twenty-four seven", "three x faster", "dot com". No emojis, hashtags, markdown, bullets or stage directions in the paste block, and no SSML.
- Tags: only where the delivery changes, at most one per clause, matched to the voice's character (§10.3). CAPS on one word per section at most.
- Brand names and odd words: follow the acronym rule in §10.5 first (letter-by-letter acronyms in English capitals, names read as ordinary words in Arabic letters as spoken). If a word is still mispronounced after that, fall back to v4 IPA `/ˈnoʊʃən/` or an alias respelling ("Notion" → "NOH-shun"); list them under pronunciation notes.
- Keep on-screen keywords (for kinetic type) in a separate list, not in the paste block.
- Split the script into chunks per scene (§10.6) and save each chunk's exact text as UTF-8 in `plan/vo/<scene>.txt`.

**Deliver exactly this format:**
````
## VO script – <project> (v1)
Target: 60 s · ≈ 142 words ≈ 58 s (estimate; final timing comes from the audio)
Model: Eleven v4 (eleven_v4) · previews only: Eleven v4 Turbo (eleven_v4_turbo)
Voice: <library voice name + voice_id> | <IVC from assets/vo/voices/<sample file>, rights and consent confirmed by the user on YYYY-MM-DD>
Settings: Stability 0.5 · Similarity 0.75 · Seed <n> (Style and Speed do not exist on v4)
Language: <en | ar, dialect …> · Output: mp3_44100_192 (or wav_48000 if the plan allows)
Chunks: scene01 ≈ 420 chars · scene02 ≈ 380 chars … · takes per chunk: 2

--- PASTE INTO ELEVENLABS (copy everything between the lines) ---
[thoughtful] Nobody drew this.
Not one line… not one frame.

[curious] So where did it come from?
…
[warmly] Start yours today — link below.
--- END ---

On-screen keywords: NOBODY · DREW · THIS · …
Pronunciation notes: <word → /IPA/ or respelling>
Alt hook (variant B): …
````
Also give a **variant B** of the hook (and CTA if useful) so the user can A/B pick.

### 10b. Producing the narration
The script and the voice must be approved first. Approval for narration does not authorize voice cloning, SFX, music or other paid calls; each needs its own approval.

**Route A: API helper (default when `ELEVENLABS_API_KEY` is configured).** Run from the project folder with the selected Python:
1. Offline check, no network: `python "<skill>/scripts/gen_tts_elevenlabs.py" plan --text-file plan/vo/scene01.txt` (characters, words, tags, estimate, SSML/digit/bracket warnings, key configured yes/no).
2. Free checks when needed: `... models` (v4 availability, limits, Arabic) and `... voices --search "<name>"`.
3. Ask the user to approve: model, voice, characters per chunk and in total, takes per chunk, and the credit budget. Use Turbo only for a short preview.
4. One paid request per invocation, no automatic retries, never overwrites:
   `python "<skill>/scripts/gen_tts_elevenlabs.py" generate --allow-paid-request --voice-id <id> --text-file plan/vo/scene01.txt --output "assets/vo/scene01 take1.mp3" [--seed 1234] [--stability 0.45] [--previous-request-id <id>] [--language-code ar]`
   Interviews: `... dialogue --allow-paid-request --inputs-file plan/vo/interview01.json --output "assets/vo/interview01 take1.mp3"` with `[{"voice_id": "...", "text": "..."}, ...]`.
   Clone from a sample (after the confirmations in §10.7): `... clone --allow-voice-clone --confirm-rights-and-consent --name "<voice name>" --sample "assets/vo/voices/<sample>.mp3"`; without the flags it only runs the local sample check.
5. Each take writes the audio, a `.json` provenance sidecar (model, voice, settings, seed, request-id, reported character cost, SHA-256, exact text) and `.words.json` word timings from ElevenLabs' alignment with tags removed. Use the word timings for `plan/beats.json`; still transcribe and diff when the read deviates, or when IPA or numbers are involved.
6. Listen to every take in full (no spoken tags, pronunciation, seams, no clipping) before calling it approved.

**Route B: manual, in the ElevenLabs app.** The user opens elevenlabs.io → Text to Speech → model **Eleven v4** → the approved voice → Stability/Similarity as in the script header → pastes the block → generates 2–3 takes → downloads the best as MP3 (or WAV) → sends it / puts it in `assets/vo/vo_v1.mp3`. If one line sounds wrong, regenerate only that line with the same settings and send it as `vo_line07_fix.mp3`; it will be spliced on a pause.

Don't edit the text after approval without telling the user (timing and captions come from it).

### Sources checked (2026-10-18)
- ElevenLabs docs: Models · Eleven v4 overview · Text to Speech best practices · Troubleshooting · Instant Voice Cloning · Request stitching · Text to Dialogue · API reference (create speech with timestamps, create dialogue with timestamps, create IVC voice, list models, list voices) · Help center: audio tags with v3 and v4.
- ElevenLabs blog: Eleven v4 launch post · Audio tags list for Eleven v4.
- Reported experience (secondary): eesel.ai "Eleven v4 explained" (user reports of fast reads, theatrical delivery, accent bleed) · raxxo.shop (tags that now fire, seams) · morphic.com v4 prompt guide (Turbo drafts, multiple takes) · layer3labs.io (stability range).
- Arabic diacritics and TTS ambiguity: Communications of the ACM, "Unlocking the Potential of Arabic Voice Generation Technologies".
