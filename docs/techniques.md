# Technique library

**334 techniques** — 59 original studio techniques + 275 motions from [Alansari Motion Library](https://github.com/alansariteach/motion-library).

Draw a plan with `python3 tools/techniques.py --draw --from-plan plan/beats.json`.
This page is generated from `assets/techniques.json`, so edit the JSON, not this file.

---

## 🎬 Studio Techniques (Original)

59 hand-crafted techniques with full studio integration.

### Opening Hook (خطافات البداية)

#### `oh-cold-open-mid-move` — Cold open mid-move

*workhorse · any · timeline · evidence 5 · first change ≤ 0.10 s; first readable word ≈ 0.40 s*

No fade from black, no title card. Frame 1 is already in motion: the camera is mid-push, a word is half-built, the grid is already crawling. The first visible change lands inside 0.10 s.

**How:** Draw local time as t + 0.35 s into every entrance so nothing starts at rest: P `lib.prog(t+0.35,a,b)` / K `seg(t + 0.35, start, dur)`. Never call a fade at t=0; the paper flood, the pose and the HUD all exist on the first frame.

**Use when:** Always. It is the cheapest way to read as directed instead of generated.

**Avoid when:** Never — the only exception is a deliberate cold open on a still, which must then slam within 0.4 s.

#### `oh-question-then-first-cut` — Question, then the first hard cut answers it

*signature · medium · timeline · evidence 2 · answer at 1.1–1.6 s, on the scene bound*

The opening fragment is the question the viewer already has; the first hard cut (median 1.3 s in) lands the answer as a picture, not a caption.

**How:** Put the question as one 2–4 word fragment in scene 1, and make scene 1 end exactly where the VO's first silence starts (`plan/beats.json` bounds). The answer is the close-up pose (`presenter.draw(fr, 'close-explain', t)`) or the 3D object arriving on the cut, with the `sfx` hit on that frame — never another line of type.

**Use when:** A VO whose first sentence is a premise or a problem.

**Avoid when:** The VO opens with a personal greeting — then open on the pose instead.

#### `oh-word-arrives-with-the-move` — The first word arrives with the move, not before it

*workhorse · any · type · evidence 4 · 18–24 f settle at 30 fps, 4–10 f between words*

Nothing sits still waiting to be read. The first word enters at 40% ink and settles over 18–24 frames while the camera is still travelling.

**How:** P: `paste(sp, y+rise*(1-e_out(p)), alpha=0.4+0.6*e_out(p))` with rise 25 px over 0.6 s; K: `enter(t, start, {dur:0.62, from:0.4, rise:25})`. The camera keeps creeping (`cam-living-hold-creep`) underneath.

**Use when:** Every title, every fragment.

**Avoid when:** Never pair it with a scale start above 1.17× — that reads as a zoom, not a settle.

#### `oh-one-beat-of-still-then-slam` — One beat of still, then the slam

*accent · high · timeline · evidence 3 · still 0.4–0.5 s, slam settles over 0.7 s*

A single deliberate empty beat (≤0.5 s in this studio) buys the first slam its weight. Used once per film, on the key claim.

**How:** Hold the pose and the paper still for 12–15 f, keep breathing only (`presenter.breathe`), then land the word at 1.4–2.1× scale with 2–4 f of `blur_steps` smear and settle in 20 f.

**Use when:** Once, on the line the film is actually about.

**Avoid when:** Twice in one reel, or anywhere the VO is still talking over it.

### Typography (الخطوط والطباعة)

#### `ty-masked-baseline-rise` — Masked baseline rise

*workhorse · calm · type · evidence 4 · 10–12 f per word, 8 f apart (30 fps)*

Each word rises out of its own clipped line box, darkening from grey to ink. Whole words only — the mask is per word, never per letter.

**How:** P: build a sprite per word with `lib.text_sprite`, paste through a clip box whose height grows with `e_out(p)`; colour lerps `gray_4 → ink` over the same p. K: `ctx.save(); ctx.beginPath(); ctx.rect(x, lineTop, w, lineH*e); ctx.clip(); drawWord(...)`. Words 8 f apart, 10–12 f each.

**Use when:** The default entrance for Arabic headlines — it respects shaping because the clip never cuts a letter.

**Avoid when:** On a word that must be readable in under 0.4 s (a hook word) — use the settle instead.

#### `ty-inplace-light-up-on-beats` — In-place light-up on the beat

*workhorse · calm · grid · evidence 4 · 1 step per word at 100–120 BPM, ramp 4 f, recency 12–24 f*

The finished line is laid out first; words light from `gray_2` to ink on successive grid steps, so the type follows the tempo without moving.

**How:** Lay the whole line at final positions, then per word pick a step from `beat.grid(bpm)` (`on_grid`) and ramp colour over 4 f. The newest word may take `red` for 12–24 f then settle to ink — once per card, not per word.

**Use when:** Long Arabic lines where motion would fight readability.

**Avoid when:** More than 8 words visible — the line becomes a scan.

#### `ty-recentre-line-build` — Re-centring line build

*workhorse · medium · type · evidence 6 · 24–38 f re-centre, words 6–9 f apart*

Words arrive right-to-left (Arabic reading order) and the line re-centres once per word on an expo-out, never per letter.

**How:** Compute the final line width once; after each word lands, tween the line origin to `0.5 - width/2` with `e_out` over 24–38 f. Keep the vertical baseline fixed so only x breathes.

**Use when:** A short claim that grows to most of the frame width.

**Avoid when:** RTL is on and the words contain punctuation-only tokens — group them with the previous word first.

#### `ty-staggered-word-roll` — Staggered word roll

*workhorse · medium · type · evidence 4 · 5–6 f per word, 20 f settle*

The outgoing word rises and blurs out while the incoming word comes up from below — a vertical roller inside one line, 5–6 f per word.

**How:** Two sprites per slot: outgoing at `y - 20*e`, `blur_steps` 6 px, alpha out over 10 f; incoming from `y + 24` settling in 20 f. Drive the slot changes from `beat` steps so it never drifts.

**Use when:** A list of three to five short Arabic terms that share a grammar.

**Avoid when:** Words longer than ~10 characters — the roll outruns the eye.

#### `ty-reading-order-exit` — Reading-order exit

*workhorse · any · type · evidence 3 · exit finished 2 f before the cut*

Text rarely fades on its own. It leaves on the cut, or word by word in reading order, each rising 10–20 px and gone in 2–3 f.

**How:** Trigger the exit 6–8 f before the scene bound from `plan/beats.json`, front to back (Arabic: right to left), with the background already accelerating out (`transition` velocity curve).

**Use when:** Every fragment that does not die with its whole scene.

**Avoid when:** A hero line — it goes with the cut instead, never a slow fade.

#### `ty-oversize-blur-slide-in` — Oversize word with velocity blur

*signature · high · blur · evidence 3 · sharp within 0.33 s, readable by 0.5 s*

One word at 15–30% of frame height travels in fast with directional blur, then goes pin-sharp within 10 f and is legible by 0.5 s.

**How:** Speed from the timeline (`velocity`), smear with `blur_steps(vx, vy)` (P) / `drawBlurred` (K), then draw the crisp pass once the speed drops under ~12 px/f. Blur lives only on the fast frames.

**Use when:** A two-word punchline in the middle act.

**Avoid when:** On a word the VO is also saying slowly — the two rhythms fight.

#### `ty-pose-occlusion-title-reveal` — Title behind Medo, then reveal

*accent · medium · type · short punch settles before the VO-aligned cut; title holds unchanged for ≥0.5 s after the pose exits*

A short, oversized Arabic title sits behind Medo’s transparent pose. At a VO-aligned hard cut, omit the pose but keep the same title layer, size and baseline; the cutout has been masking the title, and the cut reveals the full phrase without reflow or a duplicate title.

**How:** P: create one shaped title sprite with `lib.text_sprite`, paste it first, then draw the alpha pose with `presenter.draw(fr, pose, t)` above it. K: draw the full title with `arabic.setArabic` + `fillText` first, then `presenter.drawPresenter(ctx, pose, t)`; at the cut stop drawing the pose and keep the title coordinates/font unchanged. Use existing Medo pose PNG alpha only; keep the phrase short, RTL-shaped and out of the caption-safe band. Check face/text overlap and frames immediately before/on/after the cut. This is a P/K recipe; do not assume an R port.

**Use when:** One verified, high-value 1–3-word claim can be set behind a Medo pose and then read clearly on its own.

**Avoid when:** Long copy, dense diagrams, subtitles, or when the title crosses the face/important pose details; skip if the Arabic shaping or final hold is not clean.

#### `ty-scaled-echo-extrusion` — Scaled echo extrusion

*accent · medium · type · evidence 2 · static, revealed with the word (0.4 s)*

A word is repeated behind itself at stepped scales and descending opacity, reading as depth without a gradient or a glow.

**How:** Draw the sprite 4–7 times at `scale = 1 + i*0.06`, alpha `0.30 * (1 - i/n)`, offset 2–4 px per step, in `ink_shadow`; the front copy is full ink. Cheap, flat, and on-palette.

**Use when:** The one word that should feel monumental.

**Avoid when:** Small type, or over a textured background — the echoes turn to mush.

#### `ty-vertical-word-stack` — Vertical word stack

*workhorse · medium · layout · evidence 1 · 6–8 f per line at 100 BPM*

Words stack down the 9:16 frame like a column, one per line, each landing on its own step — it turns the vertical format into an advantage.

**How:** One word per line at 12–16% of frame height, line pitch 1.15×, each arriving 6–8 f after the last on `e_out`, stacked from the top safe line downward; measure every word with `lib.text_sprite` first so a long word cannot overflow the 40 px margin, and give the last line the accent.

**Use when:** Three to five short terms, or a list that must fill the tall frame.

**Avoid when:** Words longer than the frame width at that size — check with the measured sprite width first.

#### `ty-scramble-decode-latin-only` — Scramble decode (Latin readouts only)

*accent · medium · type · evidence 3 · 12–18 f, always shorter than the word it decorates*

A mono readout resolves from random glyphs, one character at a time. It is a Latin/mono device: Arabic is banned from it.

**How:** For HUD numbers and mono labels only (`IBM Plex Mono`), seed a `rng(seed)` and reveal left to right in 12–18 f. Arabic never uses it — per-letter reveal breaks shaping and the studio rules.

**Use when:** A counter, a timestamp, a version tag.

**Avoid when:** Any Arabic word, any word the viewer must read.

### Transitions (الانتقالات)

#### `tr-velocity-handoff-cut` — Velocity handoff cut

*workhorse · any · transition · evidence 9 · exit accel 10–18 f, decay τ ≈ 12 f*

The outgoing shot accelerates over its last 0.3–0.6 s and the next shot starts at exactly that speed, so the cut is felt as one move.

**How:** Before a bound: ease in to the exit (`x = e_in(p)`), peak 25–45 px/f at 1080-wide, and start the next scene with the same velocity decaying (`*0.92` per frame, τ ≈ 12 f at 30 fps). Keep the camera vector identical across the cut.

**Use when:** The default cut — it is the highest-evidence move in the library.

**Avoid when:** Between two static cards; with no speed to hand over it just looks like a jolt.

#### `tr-scale-through-cut` — Scale-through cut

*signature · high · transition · evidence 6 · 14–18 f each way at 30 fps*

A shape (a word, a pill, the pose's silhouette) grows past the frame, and the next shot is revealed inside the same shape at the same scale rate.

**How:** Animate a mask rect/rounded-rect from 0.2× to 3× with `e_in` over 14–18 f, swap the plate at the peak, then continue outward from 3× to rest. `transition.layer()` masks already support this.

**Use when:** Act changes, or when a word becomes a container.

**Avoid when:** Twice in a row — it reads as a template.

#### `tr-polarity-flip-cut` — Polarity flip cut

*accent · high · transition · evidence 6 · instant, on the scene bound*

Paper becomes ink (or the reverse) on the frame of the cut, with type and pose re-coloured instantly. No dissolve, no fade.

**How:** Flip the `THEME` flag on the cut frame and swap the two role colours (`paper ↔ ink`, `ink_shadow ↔ gray_1`); the pose sprite is re-tinted by its alpha mask, and the SFX hit lands on the same frame. It is a hard cut that changes world.

**Use when:** Acts that must feel like chapters.

**Avoid when:** More than twice — the film starts to strobe.

#### `tr-shape-match-cut` — Shape match cut

*workhorse · medium · transition · evidence 4 · the match holds for 2–4 f around the cut*

Something in shot A (a circle, a bar, the mouth of a cup) is in the same place, size and colour as something in shot B, so the eye carries the object across.

**How:** Choose the match object once per film (the dot, the bar, the ring) and reuse it as the carrier — `lc-one-centred-subject` and `tr-dot-relay` both depend on it. Match centre within 6 px and radius within 4%.

**Use when:** When the film has a story device (it should).

**Avoid when:** Two diagonal compositions — the eye has no anchor to match.

#### `tr-dot-relay` — Dot relay into the next scene

*signature · medium · transition · evidence 3 · 10 f collapse, 12–16 f growth*

Everything collapses to one dot, the dot travels, and the next scene grows out of it. The device the film owns is the thing that survives the cut.

**How:** Fade the composition to the accent dot over 8–10 f (`e_in`), carry the dot along a 40–70 px/f path across the cut, then scale the next scene from 0.05× around the dot in 12–16 f.

**Use when:** Mid-film, to link two unrelated pictures.

**Avoid when:** Collapsing to a dot that then means nothing — the relay must be the same object.

#### `tr-subtract-reveal` — Reveal by subtraction

*workhorse · medium · transition · evidence 4 · 18–24 f, one direction only*

The frame is over-full, then everything that is not the point is removed in one move, leaving one object, one word, one pose.

**How:** Start with 3–5 layered props (`lc-one-centred-subject` inverse), then run a single scale-and-delete pass over 18–24 f in one direction, keeping the hero element exactly in place.

**Use when:** The moment the film makes its single point.

**Avoid when:** As a habit — it costs a whole scene to earn.

### Camera (الكاميرا)

#### `cam-living-hold-creep` — Living hold creep

*workhorse · calm · camera · evidence 5 · continuous, one direction change per 6–9 s*

Nothing is ever locked. A held shot creeps 1.5–3 px/f with one direction change, so the frame is alive while the eye reads.

**How:** `z = 1 + 0.02*e_io(p)` plus `tx = 6*sin(2πt/T)` with T = 6–9 s, under any readable text. Cap the speed at 3 px/f — faster and the type stops being sharp.

**Use when:** Every shot longer than 1 s.

**Avoid when:** Nowhere — a locked camera is the tell that the sheet is generated.

#### `cam-punch-in-insert` — Punch-in insert

*workhorse · medium · camera · evidence 5 · 6–8 f punch, settle 12 f*

At the cut, the same plate punches in 1.25–1.6× and lands a beat later — the cheapest way to make one scene feel like two.

**How:** Because Medo ships `full` and `bust` framings of the same pose (`assets/poses/poses.json`), cut from `explain` to `close-explain` and add 1.15–1.3× scale over 6 f so the face lands at the same size. Pure crop, no new art.

**Use when:** Emphasis on a single sentence, inside one VO scene.

**Avoid when:** More than once per scene — it stops meaning 'listen'.

#### `cam-isolating-push` — Isolating push

*workhorse · medium · camera · evidence 3 · 0.7–1.0 s push*

A slow push toward the one object that matters while the rest of the frame drifts out of the safe area.

**How:** `z: 1 → 1.18` over 20–30 f with `e_io`, target = the object's centre, plus a matched push on the type layer at half the amount so the parallax reads as depth.

**Use when:** Before a reveal or a number.

**Avoid when:** When the push would move the caption out of the safe margin.

#### `cam-parallax-truck` — Layered parallax truck

*workhorse · calm · camera · evidence 1 · continuous, 0.8–1.5 px/f*

Background, pose and type move at different rates. The depth comes from speed, not from blur or shadow.

**How:** Offset each layer by `k` px/f with k = 0.35 / 1.0 / 1.8 for bg / presenter / type, each layer padded 8% so nothing pops at the edges. Works in both engines with a translate.

**Use when:** A quiet explanation beat that still has to breathe.

**Avoid when:** Over a busy paper texture — the layers stop separating.

#### `cam-pull-lands-event` — Pull-back that lands an event

*workhorse · calm · camera · evidence 2 · 18 f pull, event on the last 2 f*

The camera pulls out and the thing it reveals lands exactly on the last frame of the move — the move causes the event.

**How:** `z: 1.4 → 1.0` with `e_out` over 18 f, and put the word/object arrival on the final 2 f, with the SFX on that frame.

**Use when:** An end-of-sentence payoff.

**Avoid when:** If the reveal is larger than the frame — it will pop.

#### `cam-crane-push` — Crane down with a delayed push

*accent · calm · camera · evidence 1 · 24 f crane, push offset 8 f*

A vertical crane (the format's own axis) with the push starting 6–8 f later, so two moves read as one gesture.

**How:** `ty: +40 → 0` on `e_io` over 24 f; the push `z: 1 → 1.1` starts 8 f in on the same curve family. In 9:16 the vertical axis is the one with the most room, so this is the house crane.

**Use when:** Scene openings between two VO sentences.

**Avoid when:** Two cranes back to back.

#### `cam-hero-push-with-turn` — Hero push with a 3D turn

*signature · high · depth · evidence 1 · 1.0–1.3 s*

The camera pushes while the object turns — the one move that makes the 3D layer worth having.

**How:** `space3d.camera(dist, yaw, pitch)` with yaw sweeping −35° → +35° over 30–40 f while `dist` drops 12%; keep `sorted_faces` + `shade` on, back-face cull on `dot(n, cam.pos − face_centre) ≤ 0`.

**Use when:** The single 3D hero moment of the reel.

**Avoid when:** Yaw beyond ±80° (the cull breaks) or more than one per film.

### Depth & 3D (العمق والثلاثي الأبعاد)

#### `d3-extruded-slab-orbit` — Object on a thick extruded slab

*workhorse · medium · depth · evidence 1 · orbit 25–35 f, ±30°*

A flat thing (a card, a word plate) gets real thickness and a slow orbit, so it casts its own edge shadow in-palette.

**How:** `space3d.prism(poly2d, depth)` with depth 6–10% of width, cap role `paper`, side role `gray_2`, plus a 2 px hairline in `ink` on the front cap and the floor shadow as a squashed `ink_shadow` ellipse.

**Use when:** Turning a flat prop into the film's object.

**Avoid when:** Depth above 12% — it reads as a crate.

#### `d3-coin-edge-to-face` — Edge-on sliver snaps face-on

*accent · medium · depth · evidence 2 · 10 f to face-on, 20 f settle*

The object starts as a 1-pixel-thin sliver seen edge-on, then rotates to face the camera in 10 f — a reveal with no fade anywhere.

**How:** `yaw = 90° → 8°` with front-loaded easing (35% of the rotation in the first frame, blurred: `blur_steps`), `shade` ramping as the normal turns toward the light.

**Use when:** Revealing the key word-plate or the closing statement.

**Avoid when:** Twice in one act.

#### `d3-flip-face-swap` — 3D flip that swaps the state

*workhorse · medium · depth · evidence 2 · 10 f flip, no overshoot*

A 180° flip hides the swap: the back face is already the new word/picture when it lands.

**How:** Rotate the plate about y with `space3d`, cull the back face, and swap the texture at 90°; 2–3 f of `blur_steps` at the fastest frame. The flip is 10 f and never bounces.

**Use when:** A before/after pair, or two opposite words.

**Avoid when:** Any overshoot or spring on the landing.

#### `d3-spotlit-tilted-object` — Tilted object on a spotlit ground

*workhorse · calm · depth · evidence 2 · static hold with the camera creep*

The ground is a pool of light and everything else is darkness; the object sits tilted inside it, lit from one side.

**How:** `shade(color, normal, light=[0.35,0.75,0.55])` with ambient 0.45 gives the ramp with zero gradient code; the pool is a hard-edged `paper` ellipse under the object, and the rest of the stage is `ink`.

**Use when:** A quiet beat that still needs weight.

**Avoid when:** Over the light theme — the pool has nothing to contrast against.

### Pacing (الإيقاع)

#### `ps-beat-quantized-chunks` — Phrase chunks on the grid

*workhorse · medium · grid · evidence 2 · hero events within ±1 f of a step; everything within ±40 ms*

Every picture event lands on a grid step, and the VO's phrases are cut into chunks that map onto bars — so the edit and the tempo are the same object.

**How:** `beat.grid(bpm)` gives the steps; `vo_length.py --bpm` snaps the scene bounds onto them first, then place events at `on_grid(bpm, bar, step)`. A cut that drifts 110 ms off the grid reads as layered, not composed.

**Use when:** Always — this is the spine the other moves hang from.

**Avoid when:** Never; if the VO has no tempo, pick 100 BPM and snap within 0.12 s.

#### `ps-breath-envelope` — Breath envelope per card

*workhorse · medium · timeline · evidence 7 · burst 0.3–0.5 s, plateau 1–3 s, exit 0.27 s*

Each card opens on a burst, decays into a reading plateau, and hands its energy to the next card — a sawtooth, not a flat line.

**How:** Per scene: the first 20–25% of the frames carry the entrance (`prog` on an `e_out` curve), the rest is a cruise at 1.5–3 px/f, and the last 8–10 f accelerate into the cut. Take the scene's own bounds from `plan/beats.json`, and its length in beats from `beat.bar_seconds`.

**Use when:** Every scene longer than 1.2 s.

**Avoid when:** Very short punctuation scenes — they are all burst.

#### `ps-luma-act-map` — Light and dark as chapters

*workhorse · any · layout · evidence 5 · per act (2–4 per reel)*

The reel's acts are separated by the stage's luminance, not by a label: paper act, ink act, paper act. It gives structure with zero on-screen furniture.

**How:** Assign `THEME` per act from the VO's own structure (question, proof, close). The light act is `drawPaper` with `paperTile`, the dark one the paper inverse; flip on a scene bound with `tr-polarity-flip-cut` and keep the accent's meaning constant across the flip.

**Use when:** Reels longer than ~25 s.

**Avoid when:** Alternating every scene — that is a strobe, not a structure.

#### `ps-machine-grid-human-gaps` — Machine on the grid, hands off it

*workhorse · medium · grid · evidence 3 · grid ±0 f, human layer ±80 ms*

The geometric layer is rigidly quantised; the presenter and the hand-made props are deliberately not. The contrast is the personality.

**How:** Grid, HUD and type land on `beat` steps to the frame; the pose bobs/sways on `presenter.bob` and `presenter.sway` with a phase offset, and the paper texture is fixed to the world, not to the beat.

**Use when:** Any reel where Medo is on screen — that is all of them.

**Avoid when:** Nothing. Do not quantise the presenter.

### Sound (الصوت)

#### `ps-silence-first` — Silence as the default bed

*signature · calm · sound · evidence 4 · hole 12–15 f before the hero cut*

There is no music under the voice. The soundtrack is the VO plus hits that are caused by something on screen — and one deliberate hole before the biggest moment.

**How:** `sfx.py` events are keyed to picture events (a cut, a landing, a flip), never to a bar counter alone. Before the key claim, drop the sub for 12–15 f and release it on the cut. Target −14.5 ± 0.3 LUFS integrated, TP ≤ −1.5 dBTP after the mux.

**Use when:** Always — the voice is the score.

**Avoid when:** Medo explicitly asks for a music bed.

#### `sn-hit-on-visible-event` — Every hit is caused by something you can see

*workhorse · any · sound · evidence 5 · cue frame = landing frame (±0 f)*

An SFX fires only on the frame where a visible thing lands. No ambient ticking, no filler whooshes, no sound for a cut nobody sees.

**How:** Drive `sfx.py` from the same event list the picture uses (`grid_cues` / the scene's event table), with the cue on the exact frame of the landing. One sound per event, and the kit is synthesized (`tools/sfx_kit.py`).

**Use when:** Every sound in the reel.

**Avoid when:** Never — an unattributed sound is the audio version of filler text.

### Finish (اللمسات الأخيرة)

#### `tx-speed-gated-motion-blur` — Speed-gated motion blur

*workhorse · any · blur · evidence 6 · per frame, from the real velocity*

Blur appears only above ~20–40 px/f and only on the fast frames; everything settled is pin-sharp. It is physics, not a filter.

**How:** `velocity(t)` → if `speed > 20`: `blur_steps(vx, vy, n=6)` (P) or `drawBlurred` (K) with 6–16 px of smear; below that draw crisp. Never blur a whole scene or a still.

**Use when:** Slams, whips, flips, scale-throughs.

**Avoid when:** Slow type or a delivered still — blur there reads as a cheap filter.

#### `tx-paper-grain-and-edges` — Paper grain and hairline edges

*workhorse · any · finish · evidence 3 · static texture, rebuilt per frame with a frame-keyed seed*

The texture that sells the material: frame-keyed paper grain, hairlines on the objects, and one key shadow — no vignette bloom, no gradient overlays.

**How:** K: `paperTile(seed)` + `drawPaper`; P: the existing `make_bg` grid + grain. Hairline = 2 px `ink` at 20–35% alpha, shadow = `ink_shadow` at 18% offset 14 px with a 36 px blur, both from `kit.withShadow`.

**Use when:** Always, both engines — it is what makes the palette look printed.

**Avoid when:** Never animate the grain; a crawling texture reads as noise.

### UI Choreography (حركة الواجهات)

#### `ui-state-change-on-tap` — The state changes on the tap frame

*workhorse · any · layout · evidence 5 · ring 4-6 f, swap instant, settle 8 f*

A screen is only worth its runtime if it changes. The tap lands, the ring blooms for four frames, and the state swaps on that exact frame — never a crossfade between two states.

**How:** K: draw the screen inside `phone(ctx, x, y, w, drawScreen)` or `card(...)`, and switch the branch of `drawScreen` on the tap frame (t >= tap); the touch ring is a `circle_spr`-style disc at the touch point for 4-6 f with the `sfx` hit on that frame. P: `art.follow_button(pressed=True)` then `done=True` — two cached sprites, one swap.

**Use when:** Any beat where Medo says 'and then it…' — the picture finishes his sentence.

**Avoid when:** Two state swaps inside one caption; the eye reads change, not menus.

#### `ui-list-row-insert` — A row slides in and the list makes room

*workhorse · medium · layout · evidence 4 · 10-12 f shift, new row lands 2 f later*

Instead of dropping a row on top, the new row arrives from below while the rows under it shift by exactly one pitch — the room-making is the motion.

**How:** Keep the list as data (y, text); on insert animate every y with `e_out` over 10-12 f and give the new row the same `enter()` curve from below. Draw rows with `kit.card` (K) or `fill_rect` + `lib.text_sprite` (P). Never fade the old rows out.

**Use when:** Lists, results, messages, checklists that grow.

**Avoid when:** More than five visible rows on 9:16 — the pitch drops under the 27 px readable floor.

#### `ui-checklist-ticks-on-beat` — Checklist ticks on the grid

*workhorse · calm · grid · evidence 4 · 1 item per beat, 8-10 f per tick*

A checklist ticks one item per grid step, each tick drawing itself in eight frames — the tempo does the counting.

**How:** K: `checklist(ctx, items, t, {start, step})` with step = one beat. P: pre-render `paper_spec(checks=n)` variants and paste the one whose n matches the step, plus the `checkmark(s)` sprite for the tick. Take the steps from `beat.grid(bpm)` so a cut never lands mid-tick.

**Use when:** Proving a process while the voice-over counts along.

**Avoid when:** Items that cannot be read in one beat (over five words).

#### `ui-sheet-rises-over-screen` — A sheet rises over a dimmed screen

*accent · medium · layout · evidence 3 · 12-14 f up, 6 f settle*

A bottom sheet slides up over the screen and the screen behind drops to 60% — the depth cue is the dim, never a glow or a blur.

**How:** Draw the screen first, then an ink overlay at 0.35 alpha, then `kit.card` from below the frame to its rest position with `e_out` over 12-14 f (`around` handles the translate). Scale the background to 0.92 so the sheet reads as closer.

**Use when:** A detail the wide screen cannot show, or the closing call.

**Avoid when:** A sheet over a sheet; two is a stack nobody reads.

#### `ui-focus-ring-travels` — The focus ring travels, and snaps

*accent · medium · grid · evidence 2 · 8 f travel, colour flip at 4 f*

The active outline jumps between options in eight frames and the colour flips at mid-travel instead of tweening — a decision, not a gradient.

**How:** Two fixed ring positions from the layout; interpolate `e_io` over 8 f, and switch the stroke from `gray_1` to `red` at p = 0.5 (`rr()` + strokeStyle in K, `rrect(..., outline=...)` in P). The colour is chosen by p, never interpolated.

**Use when:** Choosing between two or three options on a screen.

**Avoid when:** Long menus or lists — the ring reads as flicker.

### Product Demo (عروض المنتج)

#### `pd-phone-in-hand` — Phone in Medo's hand

*signature · calm · layout · evidence 3 · as long as the scene*

The prop is attached to the presenter, not floating: the phone inherits the pose's bob and sway and its screen runs its own animation inside.

**How:** Draw `presenter.draw(fr, 'phone', t)` (or 'seated-talk') and place the device at the pose's hand anchor; apply the same `presenter.bob(t)` and `presenter.sway(t)` offsets to the device, never an independent float. K: `poseFrame(...)` then `phone(ctx, ...)` with those two offsets added.

**Use when:** Any beat where the product lives on a phone — the default for this studio.

**Avoid when:** A full-body pose whose hand is out of frame; check the anchor before committing.

#### `pd-cursor-does-the-demo` — The cursor does the demo

*workhorse · medium · layout · evidence 4 · travel 12-20 f, press 3 f*

The viewer watches a hand: the cursor travels at reading speed, presses, and the interface answers. One action per sentence.

**How:** `art.cursor(s)` in P, the same path in K: travel 30-60 px/f, `blur_steps` above 20 px/f, a 3 f press dip, then the state change via `ui-state-change-on-tap`. One cursor only, and it never leaves the 40 px safe margin.

**Use when:** Explaining a flow that lives on a screen.

**Avoid when:** Two cursors, or a cursor moving while the VO talks about something else.

#### `pd-app-window-builds` — The window builds itself

*workhorse · medium · layout · evidence 3 · 3 steps x 8-10 f inside one 1.2 s scene*

Frame, then content, then result: the window assembles in three steps on consecutive beats instead of appearing finished.

**How:** K: `appWindow(ctx, x, y, w, h, {title, body})` and reveal the body progressively (rows after 8 f, result after 16 f). P: `art.laptop()` or `art.desktop()` as the frame, with `fill_rect` rows over it. One accent for the result only. For a continuous K shell, use `drawSharedPanel` (shared geometry also available in R): move the same header once, and gate the body with contentAt after arrival; use measured scene-local timing, never an automatic loop under VO.

**Use when:** Introducing a tool or a screen for the first time.

**Avoid when:** Rebuilding the same window later in the reel — reuse the render.

#### `pd-before-after-hard-swap` — Before and after, cut not faded

*accent · medium · transition · evidence 3 · cut on the grid, no blend*

The same screen in two states, swapped on a hard cut with the layout identical — the eye can compare because nothing else moves.

**How:** Render the same layout twice — the same `card(...)` / `phone(ctx, ...)` body with different data — and cut on the grid, keeping every element's position fixed so only the values change. One element may move: then use `d3-flip-face-swap` instead of a dissolve.

**Use when:** Proving a change with one variable.

**Avoid when:** Both states cluttered — the comparison dies.

### Data & Numbers (البيانات والأرقام)

#### `dn-counter-rolls-on-beat` — The counter rolls and lands on the beat

*workhorse · medium · grid · evidence 5 · 8-14 f roll, lock 2 f before the step*

A number rolls from its old value to its new one and locks two frames before the step — the number is part of the tempo.

**How:** K: `rolling(from, to, p, {digits})` with p from `prog(t, start, start + dur)`. P: draw the digits from the same easing (`e_out`), one sprite per value band. Arabic digits when the VO says the number in Arabic, Latin mono when the voice says it in English.

**Use when:** Every number whose value the voice-over states.

**Avoid when:** Values that are not in the script — a fake metric is filler.

#### `dn-bar-grows-to-value` — The bar grows, then the label lands

*workhorse · calm · layout · evidence 4 · 14-18 f bar, label +8 f*

The bar reaches its value first and the number arrives eight frames later — two arrivals read as causality, one arrival reads as a slide.

**How:** `fill_rect` (P) or `rr` + fill (K) from 0 to the value with `e_out` over 14-18 f; the track is `gray_1`, the bar `red`, no gradient; then draw the label with the settle from `oh-word-arrives-with-the-move`.

**Use when:** Comparisons, progress, growth.

**Avoid when:** More than three bars; the frame becomes a chart nobody asked for.

#### `dn-one-number-full-bleed` — One number, full bleed

*signature · high · type · evidence 4 · 0.8-1.5 s on screen*

A single number at 30-40% of the frame height with everything else deleted — if the reel has one memorable figure, this is where it is spent.

**How:** One `lib.font(size, 'Anton', 900)` sprite (Cairo 900 for Arabic digits), optical centre at y around 0.46 H, no outline and no glow; the unit is a small `IBM Plex Mono` line eight frames later. Once per reel.

**Use when:** The one figure the film exists to say.

**Avoid when:** A second time, or a decimal nobody needs.

#### `dn-unit-arrives-after` — The unit arrives after the digits

*workhorse · calm · type · evidence 2 · 6-8 f after the digits*

EGP, %, /day comes in six to eight frames after the digits settle, at 30% opacity, and tightens into place.

**How:** Separate sprite, `enter()` with from 0.3, rise 8 px, starting 6-8 f after the number settles. In Arabic keep the unit as its own word (RTL) so shaping never crosses the digits.

**Use when:** Every number that needs a unit to mean anything.

**Avoid when:** The unit repeats the number — pick one word.

### Micro Interaction (التفاعلات الصغيرة)

#### `mi-press-has-depth` — A press has depth, a release has none

*workhorse · calm · layout · evidence 3 · press 4 f, release 6 f*

Pressing scales the control to 0.97 and drops its shadow by 2 px; releasing returns on a straight ease with no overshoot.

**How:** `kit.around(ctx, cx, cy, {s}, ...)` with s = 1 - 0.03 * press; the shadow (`withShadow`, 14 px) drops to 12 px. Release uses `e_out` at the same duration — no spring, because `e_back` here reads as a bounce.

**Use when:** Any tappable thing that is actually tapped on screen.

**Avoid when:** Anything that is not pressed — a bobbing card is decoration.

#### `mi-toggle-knob-travels` — The knob travels, the colour flips

*accent · calm · layout · evidence 2 · 10 f, flip at 5 f*

A switch: the knob covers most of the track in ten frames while the track colour swaps at the midpoint.

**How:** Track `gray_1` to `red`, knob `paper` positioned by `e_io(p)`; at p >= 0.5 the track switches instantly (no tween) and the knob takes a 1 px ink hairline. `kit.rr` in K, `lib.rrect` in P.

**Use when:** On/off states the voice-over names.

**Avoid when:** A toggle that toggles nothing on screen afterwards.

#### `mi-check-draws-itself` — The check draws itself

*workhorse · calm · finish · evidence 3 · 8-10 f, after the row settles*

The tick is stroked, not popped: two segments, eight to ten frames, after the row it belongs to has landed.

**How:** P: `checkmark(s)` gives the shape; draw it in two passes clipped by p (long stroke, then short). K: stroke a two-segment path the same way. Colour from the palette (`blush` on dark, `red` on light) — the green check is gone.

**Use when:** Completion, validation, done.

**Avoid when:** Twelve ticks at once; pick the three that matter.

#### `mi-caret-blinks-when-idle` — Typing, and a caret that only blinks when idle

*accent · medium · type · evidence 4 · cps 22-45, caret 1 s cycle*

Text types at a stated speed and the caret blinks only in the gaps; Arabic is revealed right to left as whole shaped lines.

**How:** K: `typeLines(ctx, lines, t, {cps})` time-boxes the reveal and clips Arabic instead of splitting letters. P: the same with `text_sprite` and a clip that grows by whole words. Caret = 3 px ink bar, 0.5 Hz blink, hidden while the character count is changing.

**Use when:** A prompt, a command, a message being composed.

**Avoid when:** Typing anything longer than about 60 characters; time-box it or cut it.

### Layout (التخطيط)

#### `lc-negative-space-caption` — Caption in the subject's negative space

*workhorse · calm · layout · evidence 1 · as long as the VO phrase*

The caption lives in the part of the frame the pose leaves empty, so the presenter and the type never fight.

**How:** `presenter.draw(..., x=0.62)` puts the pose right; the caption block sits left of its bounding box at 58 px Cairo, on the 40 px margin. Mirror it (x=0.38) on the next scene to keep the frame from settling into one template.

**Use when:** Every sentence that runs while Medo is on screen.

**Avoid when:** The pose is centred and large — then use `lc-one-centred-subject` instead.

#### `lc-one-centred-subject` — One huge centred subject

*workhorse · any · layout · evidence 2 · one scene*

Exactly one thing in the middle of the frame, at 40–70% of its height, with everything else empty paper.

**How:** Choose the object or the pose, place it on the optical centre (y ≈ 0.46 H, not the geometric centre), and delete every other element. The caption, if any, goes above or below on the margin, never both.

**Use when:** The claim, the number, the turn.

**Avoid when:** Two scenes in a row — the film stops moving.

#### `lc-gap-open-insert` — Words part for an inserted object

*workhorse · medium · layout · evidence 5 · 12 f open, 14 f insert, 12 f close*

A line of type splits at its centre word, the object rises through the gap, and the line closes again — the insertion is the transition.

**How:** Measure the line, split it into two sprites, offset them apart by `gap = 0.25 * wordWidth * e_io(p)` over 12 f, run the object through on the vertical axis, close over 12 f.

**Use when:** A demonstration that needs to interrupt a sentence.

**Avoid when:** A line wider than the safe area once split.

---

## 🎨 Alansari Motion Library (Integrated)

275 motions from [Alansari Motion Library](https://github.com/alansariteach/motion-library) — adapted for this studio.
Each motion has an Arabic and English description, with easing and timing specs.

### Text In (دخول النصوص) — 125 motions

#### `al-txt-001` — Fade Up
**ظهور من تحت**

*workhorse · any · timeline · easing: easeOutCubic · 0.45s in · 0.3s out*

*Original: M-001*

The simplest entrance for any title or line.

**Spec (EN):** Text starts 40px below its final position at opacity 0, rises into place while fading to 1 over 0.45s (easeOutCubic). Holds. Exit: fade to 0 while drifting up 12px over 0.3s.

**Spec (AR):** النص يبدأ تحت مكانه بـ 40px وشفافيته 0، ويطلع لمكانه وهو يظهر خلال 0.45 ثانية (easeOutCubic). يثبت، وبعدين يختفي وهو يرتفع 12px خلال 0.3 ثانية.

**When to use:**
- EN: The simplest entrance for any title or line.
- AR: أبسط دخول لأي عنوان أو جملة.

#### `al-txt-002` — Typewriter
**آلة كاتبة**

*workhorse · any · timeline · easing: steps (one char per step) · ~0.07s per character*

*Original: M-002*

When text should type out letter by letter, like code or a prompt.

**Spec (EN):** Characters appear one at a time at a constant rate (about 14 chars/sec), with a blinking caret (0.6s blink) at the writing edge. For Arabic, reveal right-to-left by word or by clipping from the left. Hold, then erase or cut.

**Spec (AR):** الحروف تطلع وحدة وحدة بسرعة ثابتة (تقريباً 14 حرف بالثانية)، ومؤشر كتابة يومض كل 0.6 ثانية عند آخر حرف. بالعربي اكشف النص من اليمين لليسار كلمة كلمة أو بقناع. يثبت، وبعدين ينمسح أو ينقص.

**When to use:**
- EN: When text should type out letter by letter, like code or a prompt.
- AR: لما تبي النص ينكتب حرف حرف، مثل كود أو برومبت.

#### `al-txt-003` — Letter Cascade
**حروف تتساقط**

*workhorse · high · timeline · easing: easeOutBack · 0.5s per letter · 0.07s stagger*

*Original: M-003*

A short English word that should grab attention.

**Spec (EN):** Each letter drops from 60px above with a -14° rotation and opacity 0, landing in place over 0.5s (easeOutBack). Letters are staggered 0.07s apart. Use on Latin words; for Arabic use word-level stagger to keep letters joined.

**Spec (AR):** كل حرف ينزل من فوق بـ 60px مايل -14 درجة وشفافيته 0، ويستقر بمكانه خلال 0.5 ثانية (easeOutBack). بين كل حرف والثاني 0.07 ثانية. استخدمها للكلمات الإنجليزية، وبالعربي خل التأخير على مستوى الكلمة عشان الحروف تبقى متصلة.

**When to use:**
- EN: A short English word that should grab attention.
- AR: كلمة إنجليزية قصيرة تبيها تلفت النظر.

#### `al-txt-004` — Mask Slide
**انزلاق من قناع**

*workhorse · any · depth · easing: easeInOutQuart · 0.55s in · 0.45s out*

*Original: M-004*

Elegant, cinematic titles.

**Spec (EN):** The text sits inside an invisible box with overflow hidden. It slides up from 110% below the box edge into place over 0.55s, holds, then continues upward out of the box over 0.45s. No fading.

**Spec (AR):** النص داخل صندوق مخفي الأطراف (overflow hidden). يطلع من تحت حافة الصندوق بـ 110% لمكانه خلال 0.55 ثانية، يثبت، وبعدين يكمل لفوق ويطلع من الصندوق خلال 0.45 ثانية. بدون تلاشي.

**When to use:**
- EN: Elegant, cinematic titles.
- AR: عناوين أنيقة وسينمائية.

#### `al-txt-005` — Blur In
**ظهور من ضبابية**

*workhorse · any · blur · easing: easeOutQuad · 0.7s in · 0.5s out*

*Original: M-005*

Calm lines or the opening of a video.

**Spec (EN):** Text starts at scale 1.3, blur 30px, opacity 0 and settles to scale 1, blur 0, opacity 1 over 0.7s. Exit by blurring to 20px while fading out over 0.5s.

**Spec (AR):** النص يبدأ بحجم 130% وضبابية 30px وشفافية 0، ويستقر على 100% واضح خلال 0.7 ثانية. وبالخروج يتضبب لـ 20px ويختفي خلال 0.5 ثانية.

**When to use:**
- EN: Calm lines or the opening of a video.
- AR: جمل هادئة أو بداية فيديو.

#### `al-txt-041` — Slide In Right
**انزلاق من اليمين**

*workhorse · any · timeline · easing: easeOutCubic · 0.4s in · 0.3s out*

*Original: M-041*

A quick title entrance from the right.

**Spec (EN):** Text enters from 70% of its width to the right, fading 0 to 1 over 0.4s, holds, then exits to the left with a fade over 0.3s.

**Spec (AR):** النص يدخل من اليمين بمسافة 70% من عرضه وهو يظهر من 0 لـ 1 خلال 0.4 ثانية، يثبت، وبعدين يطلع لليسار وهو يختفي خلال 0.3 ثانية.

**When to use:**
- EN: A quick title entrance from the right.
- AR: دخول عنوان بسيط وسريع من جهة اليمين.

#### `al-txt-042` — Slide In Left
**انزلاق من اليسار**

*workhorse · any · timeline · easing: easeOutCubic · 0.4s in · 0.3s out*

*Original: M-042*

An entrance from the left, good for English text or lists.

**Spec (EN):** Text enters from 70% of its width to the left, fading in over 0.4s, holds, then exits to the right with a fade over 0.3s.

**Spec (AR):** النص يدخل من اليسار بمسافة 70% من عرضه وهو يظهر خلال 0.4 ثانية، يثبت، وبعدين يطلع لليمين وهو يختفي خلال 0.3 ثانية.

**When to use:**
- EN: An entrance from the left, good for English text or lists.
- AR: دخول من اليسار، يناسب الكلام الإنجليزي أو القوائم.

#### `al-txt-043` — Drop In
**سقوط من فوق**

*workhorse · high · depth · easing: easeOutBounce · 0.5s*

*Original: M-043*

A title falls from above and bounces, playful.

**Spec (EN):** Text drops from 160% above its place, overshoots 8% down, bounces back 4% up and settles over 0.5s. Exit by fading out.

**Spec (AR):** النص يطيح من فوق مكانه بـ 160%، ينزل تحت مكانه 8%، يرتد 4% لفوق ويستقر خلال 0.5 ثانية. ويطلع بتلاشي.

**When to use:**
- EN: A title falls from above and bounces, playful.
- AR: عنوان يطيح من فوق ويرتد، حركة مرحة.

#### `al-txt-044` — Zoom In Text
**تكبير من صغير**

*workhorse · any · timeline · easing: easeOutExpo · 0.5s*

*Original: M-044*

A word grows from a dot to full size.

**Spec (EN):** Text scales from 20% to 100% while fading in over 0.5s (easeOutExpo). Exit by scaling to 110% and fading out.

**Spec (AR):** النص يكبر من 20% لـ 100% وهو يظهر خلال 0.5 ثانية (easeOutExpo). وبالخروج يكبر لـ 110% ويختفي.

**When to use:**
- EN: A word grows from a dot to full size.
- AR: كلمة تطلع من نقطة صغيرة وتكبر لحجمها.

#### `al-txt-045` — Zoom Out Text
**تصغير من كبير**

*workhorse · any · blur · easing: easeOutQuart · 0.45s*

*Original: M-045*

A strong word slams onto the screen.

**Spec (EN):** Text starts at 240% scale and opacity 0 and shrinks to 100% while fading in over 0.45s, like it lands on the screen. Pair with a low "boom".

**Spec (AR):** النص يبدأ بحجم 240% وشفافية 0، ويصغر لـ 100% وهو يظهر خلال 0.45 ثانية كأنه نزل على الشاشة. حط معاه صوت "بوم" غليظ.

**When to use:**
- EN: A strong word slams onto the screen.
- AR: كلمة قوية تنزل على الشاشة كأنها ضربة.

#### `al-txt-046` — Flip In
**قلب ثلاثي الأبعاد**

*workhorse · high · depth · easing: easeOutBack · 0.5s in · 0.4s out*

*Original: M-046*

A title flips in on the horizontal axis like a sign.

**Spec (EN):** Text rotates from 90° to 0° around the X axis with perspective while fading in over 0.5s. Exit by rotating to -90°.

**Spec (AR):** النص يلف من 90 درجة لـ 0 على المحور الأفقي مع عمق 3D وهو يظهر خلال 0.5 ثانية. وبالخروج يلف لـ -90 درجة.

**When to use:**
- EN: A title flips in on the horizontal axis like a sign.
- AR: عنوان يقلب على المحور الأفقي مثل اللوحة.

#### `al-txt-047` — Rotate In
**دخول بدوران**

*workhorse · high · depth · easing: easeOutBack · 0.5s*

*Original: M-047*

A word spins in, good for "turnaround" moments.

**Spec (EN):** Text rotates from -90° and 60% scale to 0° and 100% while fading in over 0.5s. Exit with a small 30° turn and fade.

**Spec (AR):** النص يلف من -90 درجة وحجم 60% لين 0 درجة و100% وهو يظهر خلال 0.5 ثانية. ويطلع بلفة 30 درجة وتلاشي.

**When to use:**
- EN: A word spins in, good for "turnaround" moments.
- AR: كلمة تدخل وهي تلف، تناسب التحويلات.

#### `al-txt-048` — Word Stagger
**كلمات ورا بعض**

*workhorse · any · depth · easing: easeOutCubic · 0.45s per word · 0.2s stagger*

*Original: M-048*

A short line where each word follows the one before.

**Spec (EN):** Each word rises 40px and fades in over 0.45s, starting 0.2s after the previous word. Hold the full line, then fade all out together.

**Spec (AR):** كل كلمة تطلع لفوق 40px وتظهر خلال 0.45 ثانية، وتبدأ بعد اللي قبلها بـ 0.2 ثانية. السطر كامل يثبت، وبعدين كله يختفي مع بعض.

**When to use:**
- EN: A short line where each word follows the one before.
- AR: جملة قصيرة كل كلمة تطلع بعد اللي قبلها.

#### `al-txt-049` — Elastic Pop
**نطة مطاطية**

*workhorse · any · timeline · easing: elastic · 0.6s*

*Original: M-049*

A word pops with a rubbery squash and stretch.

**Spec (EN):** Text scales from 0 to a squash (130% wide, 80% tall), then a stretch (85% wide, 115% tall), then settles at 100% over about 0.6s.

**Spec (AR):** النص يكبر من 0 لشكل مضغوط (130% عرض و80% طول)، وبعدين ممطوط (85% عرض و115% طول)، ويستقر على 100% خلال تقريباً 0.6 ثانية.

**When to use:**
- EN: A word pops with a rubbery squash and stretch.
- AR: كلمة تنط بشكل مطاطي، تناسب المحتوى الخفيف.

#### `al-txt-050` — Split Reveal
**النص ينقسم ويتجمع**

*workhorse · any · depth · easing: easeOutQuart · 0.5s*

*Original: M-050*

A title split in two halves that meet in the middle.

**Spec (EN):** The top half of the text slides down from 70% above and the bottom half slides up from 70% below, meeting at the line over 0.5s.

**Spec (AR):** النص الفوقاني من الكلمة ينزل من فوق بـ 70% والنص التحتاني يطلع من تحت بـ 70%، ويتجمعون على السطر خلال 0.5 ثانية.

**When to use:**
- EN: A title split in two halves that meet in the middle.
- AR: عنوان مقسوم نصين يتجمعون بالنص.

#### `al-txt-051` — Scramble Decode
**فك الشفرة**

*workhorse · calm · timeline · easing: linear · ~1s decode*

*Original: M-051*

English text resolves from random characters, great for cyber topics.

**Spec (EN):** Each character cycles through random symbols (A–Z, 0–9, #%&) every 2 frames, then locks to its final letter from left to right over about 1s.

**Spec (AR):** كل حرف يتبدل بين رموز عشوائية (A–Z و 0–9 و #%&) كل فريمين، وبعدين يثبت على حرفه الصحيح من اليسار لليمين خلال تقريباً ثانية.

**When to use:**
- EN: English text resolves from random characters, great for cyber topics.
- AR: نص إنجليزي يطلع من حروف عشوائية، يناسب الأمن السيبراني.

#### `al-txt-052` — Wave Text
**موجة حروف**

*workhorse · calm · depth · easing: easeInOutSine · loop · 0.08s stagger*

*Original: M-052*

English letters ripple in a wave.

**Spec (EN):** Each letter moves up 28% and back in a smooth wave, each starting 0.08s after the previous one, so a ripple runs across the word.

**Spec (AR):** كل حرف يطلع 28% لفوق ويرجع بموجة ناعمة، وكل حرف يبدأ بعد اللي قبله بـ 0.08 ثانية، فتمشي موجة على الكلمة.

**When to use:**
- EN: English letters ripple in a wave.
- AR: كلمة إنجليزية حروفها تتموج، تجذب العين.

#### `al-txt-053` — Outline to Fill
**حدود ثم تعبئة**

*workhorse · any · timeline · easing: easeInOutCubic · 0.8s outline · 0.4s fill*

*Original: M-053*

A title draws as an outline, then fills in.

**Spec (EN):** The text first appears as an accent outline only, revealed from the reading-start side over 0.8s, then the fill color fades in over 0.4s.

**Spec (AR):** النص يطلع أول كحدود بلون الهوية بس، وتنكشف من جهة بداية القراءة خلال 0.8 ثانية، وبعدين لون التعبئة يظهر خلال 0.4 ثانية.

**When to use:**
- EN: A title draws as an outline, then fills in.
- AR: عنوان يطلع حدوده أول وبعدين يتعبى.

#### `al-txt-054` — Spotlight Reveal
**ضوء يكشف النص**

*workhorse · calm · blur · easing: easeInOutSine · 1.4s sweep*

*Original: M-054*

Hidden text revealed by a passing spotlight.

**Spec (EN):** The text sits at 12% opacity. A soft circular spotlight (radius about 13% of the width) sweeps across it and shows the text at full brightness where it passes.

**Spec (AR):** النص باهت بشفافية 12%. ضوء دائري ناعم (نصف قطره تقريباً 13% من العرض) يمر عليه، ووين ما يمر يطلع النص بكامل وضوحه.

**When to use:**
- EN: Hidden text revealed by a passing spotlight.
- AR: نص مخفي بالظلام وضوء يمر عليه ويكشفه.

#### `al-txt-055` — Gradient Wipe Text
**تدرج يمسح النص**

*workhorse · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-055*

A word changes color with a soft wipe.

**Spec (EN):** A two-color gradient (accent and white) is clipped to the text and slides across it over 0.8s, so the word changes color with a soft edge.

**Spec (AR):** تدرج بلونين (لون الهوية والأبيض) داخل حروف النص، ويتحرك عليه خلال 0.8 ثانية، فالكلمة يتغير لونها بحافة ناعمة.

**When to use:**
- EN: A word changes color with a soft wipe.
- AR: كلمة يتغير لونها بمسحة ناعمة.

#### `al-txt-056` — Neon Flicker
**نيون يرمش**

*workhorse · any · blur · easing: steps · 0.8s flicker*

*Original: M-056*

A neon sign title that flickers on.

**Spec (EN):** The text has a white core and an accent glow (two text shadows). It turns on with 3–4 quick flickers (opacity 12% to 100%) in the first 0.8s, then stays lit.

**Spec (AR):** النص بقلب أبيض وتوهج بلون الهوية (ظلين للنص). يشتغل بـ 3 إلى 4 رمشات سريعة (شفافية من 12% لـ 100%) أول 0.8 ثانية، وبعدين يبقى شغال.

**When to use:**
- EN: A neon sign title that flickers on.
- AR: عنوان نيون يشتغل وهو يرمش مثل اللوحات.

#### `al-txt-057` — Stretch In
**تمدد**

*workhorse · any · blur · easing: easeOutExpo · 0.4s*

*Original: M-057*

A wide, fast entrance with energy.

**Spec (EN):** Text starts squashed to 300% width and 20% height at opacity 0 and snaps to normal over 0.4s. Exit by stretching tall and thin.

**Spec (AR):** النص يبدأ ممطوط بعرض 300% وطول 20% وشفافية 0، ويرجع لشكله الطبيعي خلال 0.4 ثانية. ويطلع وهو يتمدد طولي ورفيع.

**When to use:**
- EN: A wide, fast entrance with energy.
- AR: دخول عريض وسريع، يناسب الرياضة والطاقة.

#### `al-txt-058` — Skew Slide
**انزلاق مايل**

*workhorse · high · timeline · easing: easeOutBack · 0.5s*

*Original: M-058*

A fast slanted slide, like it is flying in.

**Spec (EN):** Text slides in from 60% to the right with a -30° skew, overshoots to +10° skew and straightens over 0.5s. Exit to the left skewing the other way.

**Spec (AR):** النص ينزلق من اليمين بـ 60% مايل -30 درجة، يتعدى لميلان +10 درجة ويستقيم خلال 0.5 ثانية. ويطلع لليسار مايل بالعكس.

**When to use:**
- EN: A fast slanted slide, like it is flying in.
- AR: دخول سريع بميلان كأنه يطير.

#### `al-txt-059` — Kinetic Stack
**كلمات تتكدس**

*workhorse · high · depth · easing: easeOutBounce · 0.5s per word · 0.3s stagger*

*Original: M-059*

A three-word line stacking up in different sizes.

**Spec (EN):** Each word drops in from above (M-043 style) one under the other, 0.3s apart, each in a different size and weight, forming a tight stacked block.

**Spec (AR):** كل كلمة تطيح من فوق (مثل M-043) وحدة تحت الثانية، وبينهم 0.3 ثانية، وكل كلمة بحجم ووزن مختلف، فيطلع شكل مكدس ومتراص.

**When to use:**
- EN: A three-word line stacking up in different sizes.
- AR: جملة من 3 كلمات تتكدس فوق بعض بأحجام مختلفة.

#### `al-txt-060` — Slot Machine
**حروف مثل السلوت**

*workhorse · any · timeline · easing: easeOutQuart · 0.9s · 0.15s stagger*

*Original: M-060*

Letters spin like a slot machine and land on the word.

**Spec (EN):** Each letter sits in a one-row window and scrolls through a column of 5 random letters before landing on its final letter over 0.9s. Letters stop 0.15s apart from left to right.

**Spec (AR):** كل حرف داخل نافذة بارتفاع سطر واحد، ويمر على عمود من 5 حروف عشوائية قبل ما يوقف على حرفه خلال 0.9 ثانية. والحروف توقف ورا بعض كل 0.15 ثانية من اليسار لليمين.

**When to use:**
- EN: Letters spin like a slot machine and land on the word.
- AR: حروف تدور مثل آلة الحظ وتوقف على الكلمة.

#### `al-txt-001-fast` — Fade Up · Fast
**ظهور من تحت · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.45s in · 0.3s out*

*Original: M-001*

Variant of M-001: أسرع بـ 40%

**Spec (EN):** Text starts 40px below its final position at opacity 0, rises into place while fading to 1 over 0.45s (easeOutCubic). Holds. Exit: fade to 0 while drifting up 12px over 0.3s.

**Spec (AR):** النص يبدأ تحت مكانه بـ 40px وشفافيته 0، ويطلع لمكانه وهو يظهر خلال 0.45 ثانية (easeOutCubic). يثبت، وبعدين يختفي وهو يرتفع 12px خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-001.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-001.

#### `al-txt-001-slow` — Fade Up · Slow
**ظهور من تحت · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.45s in · 0.3s out*

*Original: M-001*

Variant of M-001: أبطأ بـ 60%

**Spec (EN):** Text starts 40px below its final position at opacity 0, rises into place while fading to 1 over 0.45s (easeOutCubic). Holds. Exit: fade to 0 while drifting up 12px over 0.3s.

**Spec (AR):** النص يبدأ تحت مكانه بـ 40px وشفافيته 0، ويطلع لمكانه وهو يظهر خلال 0.45 ثانية (easeOutCubic). يثبت، وبعدين يختفي وهو يرتفع 12px خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-001.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-001.

#### `al-txt-001-gold` — Fade Up · Gold
**ظهور من تحت · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.45s in · 0.3s out*

*Original: M-001*

Variant of M-001: نسخة ذهبية فاخرة

**Spec (EN):** Text starts 40px below its final position at opacity 0, rises into place while fading to 1 over 0.45s (easeOutCubic). Holds. Exit: fade to 0 while drifting up 12px over 0.3s.

**Spec (AR):** النص يبدأ تحت مكانه بـ 40px وشفافيته 0، ويطلع لمكانه وهو يظهر خلال 0.45 ثانية (easeOutCubic). يثبت، وبعدين يختفي وهو يرتفع 12px خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-001.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-001.

#### `al-txt-001-boxed` — Fade Up · Boxed
**ظهور من تحت · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.45s in · 0.3s out*

*Original: M-001*

Variant of M-001: النص داخل صندوق ملون

**Spec (EN):** Text starts 40px below its final position at opacity 0, rises into place while fading to 1 over 0.45s (easeOutCubic). Holds. Exit: fade to 0 while drifting up 12px over 0.3s.

**Spec (AR):** النص يبدأ تحت مكانه بـ 40px وشفافيته 0، ويطلع لمكانه وهو يظهر خلال 0.45 ثانية (easeOutCubic). يثبت، وبعدين يختفي وهو يرتفع 12px خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-001.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-001.

#### `al-txt-002-fast` — Typewriter · Fast
**آلة كاتبة · سريع**

*accent · any · timeline · easing: steps (one char per step) · ~0.07s per character*

*Original: M-002*

Variant of M-002: أسرع بـ 40%

**Spec (EN):** Characters appear one at a time at a constant rate (about 14 chars/sec), with a blinking caret (0.6s blink) at the writing edge. For Arabic, reveal right-to-left by word or by clipping from the left. Hold, then erase or cut.

**Spec (AR):** الحروف تطلع وحدة وحدة بسرعة ثابتة (تقريباً 14 حرف بالثانية)، ومؤشر كتابة يومض كل 0.6 ثانية عند آخر حرف. بالعربي اكشف النص من اليمين لليسار كلمة كلمة أو بقناع. يثبت، وبعدين ينمسح أو ينقص.

**When to use:**
- EN: Use when you need a fast version of M-002.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-002.

#### `al-txt-002-slow` — Typewriter · Slow
**آلة كاتبة · بطيء**

*accent · any · timeline · easing: steps (one char per step) · ~0.07s per character*

*Original: M-002*

Variant of M-002: أبطأ بـ 60%

**Spec (EN):** Characters appear one at a time at a constant rate (about 14 chars/sec), with a blinking caret (0.6s blink) at the writing edge. For Arabic, reveal right-to-left by word or by clipping from the left. Hold, then erase or cut.

**Spec (AR):** الحروف تطلع وحدة وحدة بسرعة ثابتة (تقريباً 14 حرف بالثانية)، ومؤشر كتابة يومض كل 0.6 ثانية عند آخر حرف. بالعربي اكشف النص من اليمين لليسار كلمة كلمة أو بقناع. يثبت، وبعدين ينمسح أو ينقص.

**When to use:**
- EN: Use when you need a slow version of M-002.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-002.

#### `al-txt-002-gold` — Typewriter · Gold
**آلة كاتبة · ذهبي**

*accent · any · timeline · easing: steps (one char per step) · ~0.07s per character*

*Original: M-002*

Variant of M-002: نسخة ذهبية فاخرة

**Spec (EN):** Characters appear one at a time at a constant rate (about 14 chars/sec), with a blinking caret (0.6s blink) at the writing edge. For Arabic, reveal right-to-left by word or by clipping from the left. Hold, then erase or cut.

**Spec (AR):** الحروف تطلع وحدة وحدة بسرعة ثابتة (تقريباً 14 حرف بالثانية)، ومؤشر كتابة يومض كل 0.6 ثانية عند آخر حرف. بالعربي اكشف النص من اليمين لليسار كلمة كلمة أو بقناع. يثبت، وبعدين ينمسح أو ينقص.

**When to use:**
- EN: Use when you need a gold version of M-002.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-002.

#### `al-txt-002-boxed` — Typewriter · Boxed
**آلة كاتبة · صندوق**

*accent · any · timeline · easing: steps (one char per step) · ~0.07s per character*

*Original: M-002*

Variant of M-002: النص داخل صندوق ملون

**Spec (EN):** Characters appear one at a time at a constant rate (about 14 chars/sec), with a blinking caret (0.6s blink) at the writing edge. For Arabic, reveal right-to-left by word or by clipping from the left. Hold, then erase or cut.

**Spec (AR):** الحروف تطلع وحدة وحدة بسرعة ثابتة (تقريباً 14 حرف بالثانية)، ومؤشر كتابة يومض كل 0.6 ثانية عند آخر حرف. بالعربي اكشف النص من اليمين لليسار كلمة كلمة أو بقناع. يثبت، وبعدين ينمسح أو ينقص.

**When to use:**
- EN: Use when you need a boxed version of M-002.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-002.

#### `al-txt-003-fast` — Letter Cascade · Fast
**حروف تتساقط · سريع**

*accent · any · timeline · easing: easeOutBack · 0.5s per letter · 0.07s stagger*

*Original: M-003*

Variant of M-003: أسرع بـ 40%

**Spec (EN):** Each letter drops from 60px above with a -14° rotation and opacity 0, landing in place over 0.5s (easeOutBack). Letters are staggered 0.07s apart. Use on Latin words; for Arabic use word-level stagger to keep letters joined.

**Spec (AR):** كل حرف ينزل من فوق بـ 60px مايل -14 درجة وشفافيته 0، ويستقر بمكانه خلال 0.5 ثانية (easeOutBack). بين كل حرف والثاني 0.07 ثانية. استخدمها للكلمات الإنجليزية، وبالعربي خل التأخير على مستوى الكلمة عشان الحروف تبقى متصلة.

**When to use:**
- EN: Use when you need a fast version of M-003.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-003.

#### `al-txt-003-slow` — Letter Cascade · Slow
**حروف تتساقط · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.5s per letter · 0.07s stagger*

*Original: M-003*

Variant of M-003: أبطأ بـ 60%

**Spec (EN):** Each letter drops from 60px above with a -14° rotation and opacity 0, landing in place over 0.5s (easeOutBack). Letters are staggered 0.07s apart. Use on Latin words; for Arabic use word-level stagger to keep letters joined.

**Spec (AR):** كل حرف ينزل من فوق بـ 60px مايل -14 درجة وشفافيته 0، ويستقر بمكانه خلال 0.5 ثانية (easeOutBack). بين كل حرف والثاني 0.07 ثانية. استخدمها للكلمات الإنجليزية، وبالعربي خل التأخير على مستوى الكلمة عشان الحروف تبقى متصلة.

**When to use:**
- EN: Use when you need a slow version of M-003.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-003.

#### `al-txt-003-gold` — Letter Cascade · Gold
**حروف تتساقط · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.5s per letter · 0.07s stagger*

*Original: M-003*

Variant of M-003: نسخة ذهبية فاخرة

**Spec (EN):** Each letter drops from 60px above with a -14° rotation and opacity 0, landing in place over 0.5s (easeOutBack). Letters are staggered 0.07s apart. Use on Latin words; for Arabic use word-level stagger to keep letters joined.

**Spec (AR):** كل حرف ينزل من فوق بـ 60px مايل -14 درجة وشفافيته 0، ويستقر بمكانه خلال 0.5 ثانية (easeOutBack). بين كل حرف والثاني 0.07 ثانية. استخدمها للكلمات الإنجليزية، وبالعربي خل التأخير على مستوى الكلمة عشان الحروف تبقى متصلة.

**When to use:**
- EN: Use when you need a gold version of M-003.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-003.

#### `al-txt-003-boxed` — Letter Cascade · Boxed
**حروف تتساقط · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.5s per letter · 0.07s stagger*

*Original: M-003*

Variant of M-003: النص داخل صندوق ملون

**Spec (EN):** Each letter drops from 60px above with a -14° rotation and opacity 0, landing in place over 0.5s (easeOutBack). Letters are staggered 0.07s apart. Use on Latin words; for Arabic use word-level stagger to keep letters joined.

**Spec (AR):** كل حرف ينزل من فوق بـ 60px مايل -14 درجة وشفافيته 0، ويستقر بمكانه خلال 0.5 ثانية (easeOutBack). بين كل حرف والثاني 0.07 ثانية. استخدمها للكلمات الإنجليزية، وبالعربي خل التأخير على مستوى الكلمة عشان الحروف تبقى متصلة.

**When to use:**
- EN: Use when you need a boxed version of M-003.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-003.

#### `al-txt-004-fast` — Mask Slide · Fast
**انزلاق من قناع · سريع**

*accent · any · depth · easing: easeInOutQuart · 0.55s in · 0.45s out*

*Original: M-004*

Variant of M-004: أسرع بـ 40%

**Spec (EN):** The text sits inside an invisible box with overflow hidden. It slides up from 110% below the box edge into place over 0.55s, holds, then continues upward out of the box over 0.45s. No fading.

**Spec (AR):** النص داخل صندوق مخفي الأطراف (overflow hidden). يطلع من تحت حافة الصندوق بـ 110% لمكانه خلال 0.55 ثانية، يثبت، وبعدين يكمل لفوق ويطلع من الصندوق خلال 0.45 ثانية. بدون تلاشي.

**When to use:**
- EN: Use when you need a fast version of M-004.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-004.

#### `al-txt-004-slow` — Mask Slide · Slow
**انزلاق من قناع · بطيء**

*accent · any · depth · easing: easeInOutQuart · 0.55s in · 0.45s out*

*Original: M-004*

Variant of M-004: أبطأ بـ 60%

**Spec (EN):** The text sits inside an invisible box with overflow hidden. It slides up from 110% below the box edge into place over 0.55s, holds, then continues upward out of the box over 0.45s. No fading.

**Spec (AR):** النص داخل صندوق مخفي الأطراف (overflow hidden). يطلع من تحت حافة الصندوق بـ 110% لمكانه خلال 0.55 ثانية، يثبت، وبعدين يكمل لفوق ويطلع من الصندوق خلال 0.45 ثانية. بدون تلاشي.

**When to use:**
- EN: Use when you need a slow version of M-004.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-004.

#### `al-txt-004-gold` — Mask Slide · Gold
**انزلاق من قناع · ذهبي**

*accent · any · depth · easing: easeInOutQuart · 0.55s in · 0.45s out*

*Original: M-004*

Variant of M-004: نسخة ذهبية فاخرة

**Spec (EN):** The text sits inside an invisible box with overflow hidden. It slides up from 110% below the box edge into place over 0.55s, holds, then continues upward out of the box over 0.45s. No fading.

**Spec (AR):** النص داخل صندوق مخفي الأطراف (overflow hidden). يطلع من تحت حافة الصندوق بـ 110% لمكانه خلال 0.55 ثانية، يثبت، وبعدين يكمل لفوق ويطلع من الصندوق خلال 0.45 ثانية. بدون تلاشي.

**When to use:**
- EN: Use when you need a gold version of M-004.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-004.

#### `al-txt-004-boxed` — Mask Slide · Boxed
**انزلاق من قناع · صندوق**

*accent · any · depth · easing: easeInOutQuart · 0.55s in · 0.45s out*

*Original: M-004*

Variant of M-004: النص داخل صندوق ملون

**Spec (EN):** The text sits inside an invisible box with overflow hidden. It slides up from 110% below the box edge into place over 0.55s, holds, then continues upward out of the box over 0.45s. No fading.

**Spec (AR):** النص داخل صندوق مخفي الأطراف (overflow hidden). يطلع من تحت حافة الصندوق بـ 110% لمكانه خلال 0.55 ثانية، يثبت، وبعدين يكمل لفوق ويطلع من الصندوق خلال 0.45 ثانية. بدون تلاشي.

**When to use:**
- EN: Use when you need a boxed version of M-004.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-004.

#### `al-txt-005-fast` — Blur In · Fast
**ظهور من ضبابية · سريع**

*accent · calm · blur · easing: easeOutQuad · 0.7s in · 0.5s out*

*Original: M-005*

Variant of M-005: أسرع بـ 40%

**Spec (EN):** Text starts at scale 1.3, blur 30px, opacity 0 and settles to scale 1, blur 0, opacity 1 over 0.7s. Exit by blurring to 20px while fading out over 0.5s.

**Spec (AR):** النص يبدأ بحجم 130% وضبابية 30px وشفافية 0، ويستقر على 100% واضح خلال 0.7 ثانية. وبالخروج يتضبب لـ 20px ويختفي خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-005.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-005.

#### `al-txt-005-slow` — Blur In · Slow
**ظهور من ضبابية · بطيء**

*accent · calm · blur · easing: easeOutQuad · 0.7s in · 0.5s out*

*Original: M-005*

Variant of M-005: أبطأ بـ 60%

**Spec (EN):** Text starts at scale 1.3, blur 30px, opacity 0 and settles to scale 1, blur 0, opacity 1 over 0.7s. Exit by blurring to 20px while fading out over 0.5s.

**Spec (AR):** النص يبدأ بحجم 130% وضبابية 30px وشفافية 0، ويستقر على 100% واضح خلال 0.7 ثانية. وبالخروج يتضبب لـ 20px ويختفي خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-005.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-005.

#### `al-txt-005-gold` — Blur In · Gold
**ظهور من ضبابية · ذهبي**

*accent · calm · blur · easing: easeOutQuad · 0.7s in · 0.5s out*

*Original: M-005*

Variant of M-005: نسخة ذهبية فاخرة

**Spec (EN):** Text starts at scale 1.3, blur 30px, opacity 0 and settles to scale 1, blur 0, opacity 1 over 0.7s. Exit by blurring to 20px while fading out over 0.5s.

**Spec (AR):** النص يبدأ بحجم 130% وضبابية 30px وشفافية 0، ويستقر على 100% واضح خلال 0.7 ثانية. وبالخروج يتضبب لـ 20px ويختفي خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-005.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-005.

#### `al-txt-005-boxed` — Blur In · Boxed
**ظهور من ضبابية · صندوق**

*accent · calm · blur · easing: easeOutQuad · 0.7s in · 0.5s out*

*Original: M-005*

Variant of M-005: النص داخل صندوق ملون

**Spec (EN):** Text starts at scale 1.3, blur 30px, opacity 0 and settles to scale 1, blur 0, opacity 1 over 0.7s. Exit by blurring to 20px while fading out over 0.5s.

**Spec (AR):** النص يبدأ بحجم 130% وضبابية 30px وشفافية 0، ويستقر على 100% واضح خلال 0.7 ثانية. وبالخروج يتضبب لـ 20px ويختفي خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-005.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-005.

#### `al-txt-041-fast` — Slide In Right · Fast
**انزلاق من اليمين · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.4s in · 0.3s out*

*Original: M-041*

Variant of M-041: أسرع بـ 40%

**Spec (EN):** Text enters from 70% of its width to the right, fading 0 to 1 over 0.4s, holds, then exits to the left with a fade over 0.3s.

**Spec (AR):** النص يدخل من اليمين بمسافة 70% من عرضه وهو يظهر من 0 لـ 1 خلال 0.4 ثانية، يثبت، وبعدين يطلع لليسار وهو يختفي خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-041.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-041.

#### `al-txt-041-slow` — Slide In Right · Slow
**انزلاق من اليمين · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.4s in · 0.3s out*

*Original: M-041*

Variant of M-041: أبطأ بـ 60%

**Spec (EN):** Text enters from 70% of its width to the right, fading 0 to 1 over 0.4s, holds, then exits to the left with a fade over 0.3s.

**Spec (AR):** النص يدخل من اليمين بمسافة 70% من عرضه وهو يظهر من 0 لـ 1 خلال 0.4 ثانية، يثبت، وبعدين يطلع لليسار وهو يختفي خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-041.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-041.

#### `al-txt-041-gold` — Slide In Right · Gold
**انزلاق من اليمين · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.4s in · 0.3s out*

*Original: M-041*

Variant of M-041: نسخة ذهبية فاخرة

**Spec (EN):** Text enters from 70% of its width to the right, fading 0 to 1 over 0.4s, holds, then exits to the left with a fade over 0.3s.

**Spec (AR):** النص يدخل من اليمين بمسافة 70% من عرضه وهو يظهر من 0 لـ 1 خلال 0.4 ثانية، يثبت، وبعدين يطلع لليسار وهو يختفي خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-041.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-041.

#### `al-txt-041-boxed` — Slide In Right · Boxed
**انزلاق من اليمين · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.4s in · 0.3s out*

*Original: M-041*

Variant of M-041: النص داخل صندوق ملون

**Spec (EN):** Text enters from 70% of its width to the right, fading 0 to 1 over 0.4s, holds, then exits to the left with a fade over 0.3s.

**Spec (AR):** النص يدخل من اليمين بمسافة 70% من عرضه وهو يظهر من 0 لـ 1 خلال 0.4 ثانية، يثبت، وبعدين يطلع لليسار وهو يختفي خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-041.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-041.

#### `al-txt-042-fast` — Slide In Left · Fast
**انزلاق من اليسار · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.4s in · 0.3s out*

*Original: M-042*

Variant of M-042: أسرع بـ 40%

**Spec (EN):** Text enters from 70% of its width to the left, fading in over 0.4s, holds, then exits to the right with a fade over 0.3s.

**Spec (AR):** النص يدخل من اليسار بمسافة 70% من عرضه وهو يظهر خلال 0.4 ثانية، يثبت، وبعدين يطلع لليمين وهو يختفي خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-042.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-042.

#### `al-txt-042-slow` — Slide In Left · Slow
**انزلاق من اليسار · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.4s in · 0.3s out*

*Original: M-042*

Variant of M-042: أبطأ بـ 60%

**Spec (EN):** Text enters from 70% of its width to the left, fading in over 0.4s, holds, then exits to the right with a fade over 0.3s.

**Spec (AR):** النص يدخل من اليسار بمسافة 70% من عرضه وهو يظهر خلال 0.4 ثانية، يثبت، وبعدين يطلع لليمين وهو يختفي خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-042.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-042.

#### `al-txt-042-gold` — Slide In Left · Gold
**انزلاق من اليسار · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.4s in · 0.3s out*

*Original: M-042*

Variant of M-042: نسخة ذهبية فاخرة

**Spec (EN):** Text enters from 70% of its width to the left, fading in over 0.4s, holds, then exits to the right with a fade over 0.3s.

**Spec (AR):** النص يدخل من اليسار بمسافة 70% من عرضه وهو يظهر خلال 0.4 ثانية، يثبت، وبعدين يطلع لليمين وهو يختفي خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-042.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-042.

#### `al-txt-042-boxed` — Slide In Left · Boxed
**انزلاق من اليسار · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.4s in · 0.3s out*

*Original: M-042*

Variant of M-042: النص داخل صندوق ملون

**Spec (EN):** Text enters from 70% of its width to the left, fading in over 0.4s, holds, then exits to the right with a fade over 0.3s.

**Spec (AR):** النص يدخل من اليسار بمسافة 70% من عرضه وهو يظهر خلال 0.4 ثانية، يثبت، وبعدين يطلع لليمين وهو يختفي خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-042.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-042.

#### `al-txt-043-fast` — Drop In · Fast
**سقوط من فوق · سريع**

*accent · any · depth · easing: easeOutBounce · 0.5s*

*Original: M-043*

Variant of M-043: أسرع بـ 40%

**Spec (EN):** Text drops from 160% above its place, overshoots 8% down, bounces back 4% up and settles over 0.5s. Exit by fading out.

**Spec (AR):** النص يطيح من فوق مكانه بـ 160%، ينزل تحت مكانه 8%، يرتد 4% لفوق ويستقر خلال 0.5 ثانية. ويطلع بتلاشي.

**When to use:**
- EN: Use when you need a fast version of M-043.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-043.

#### `al-txt-043-slow` — Drop In · Slow
**سقوط من فوق · بطيء**

*accent · any · depth · easing: easeOutBounce · 0.5s*

*Original: M-043*

Variant of M-043: أبطأ بـ 60%

**Spec (EN):** Text drops from 160% above its place, overshoots 8% down, bounces back 4% up and settles over 0.5s. Exit by fading out.

**Spec (AR):** النص يطيح من فوق مكانه بـ 160%، ينزل تحت مكانه 8%، يرتد 4% لفوق ويستقر خلال 0.5 ثانية. ويطلع بتلاشي.

**When to use:**
- EN: Use when you need a slow version of M-043.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-043.

#### `al-txt-043-gold` — Drop In · Gold
**سقوط من فوق · ذهبي**

*accent · any · depth · easing: easeOutBounce · 0.5s*

*Original: M-043*

Variant of M-043: نسخة ذهبية فاخرة

**Spec (EN):** Text drops from 160% above its place, overshoots 8% down, bounces back 4% up and settles over 0.5s. Exit by fading out.

**Spec (AR):** النص يطيح من فوق مكانه بـ 160%، ينزل تحت مكانه 8%، يرتد 4% لفوق ويستقر خلال 0.5 ثانية. ويطلع بتلاشي.

**When to use:**
- EN: Use when you need a gold version of M-043.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-043.

#### `al-txt-043-boxed` — Drop In · Boxed
**سقوط من فوق · صندوق**

*accent · any · depth · easing: easeOutBounce · 0.5s*

*Original: M-043*

Variant of M-043: النص داخل صندوق ملون

**Spec (EN):** Text drops from 160% above its place, overshoots 8% down, bounces back 4% up and settles over 0.5s. Exit by fading out.

**Spec (AR):** النص يطيح من فوق مكانه بـ 160%، ينزل تحت مكانه 8%، يرتد 4% لفوق ويستقر خلال 0.5 ثانية. ويطلع بتلاشي.

**When to use:**
- EN: Use when you need a boxed version of M-043.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-043.

#### `al-txt-044-fast` — Zoom In Text · Fast
**تكبير من صغير · سريع**

*accent · any · timeline · easing: easeOutExpo · 0.5s*

*Original: M-044*

Variant of M-044: أسرع بـ 40%

**Spec (EN):** Text scales from 20% to 100% while fading in over 0.5s (easeOutExpo). Exit by scaling to 110% and fading out.

**Spec (AR):** النص يكبر من 20% لـ 100% وهو يظهر خلال 0.5 ثانية (easeOutExpo). وبالخروج يكبر لـ 110% ويختفي.

**When to use:**
- EN: Use when you need a fast version of M-044.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-044.

#### `al-txt-044-slow` — Zoom In Text · Slow
**تكبير من صغير · بطيء**

*accent · any · timeline · easing: easeOutExpo · 0.5s*

*Original: M-044*

Variant of M-044: أبطأ بـ 60%

**Spec (EN):** Text scales from 20% to 100% while fading in over 0.5s (easeOutExpo). Exit by scaling to 110% and fading out.

**Spec (AR):** النص يكبر من 20% لـ 100% وهو يظهر خلال 0.5 ثانية (easeOutExpo). وبالخروج يكبر لـ 110% ويختفي.

**When to use:**
- EN: Use when you need a slow version of M-044.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-044.

#### `al-txt-044-gold` — Zoom In Text · Gold
**تكبير من صغير · ذهبي**

*accent · any · timeline · easing: easeOutExpo · 0.5s*

*Original: M-044*

Variant of M-044: نسخة ذهبية فاخرة

**Spec (EN):** Text scales from 20% to 100% while fading in over 0.5s (easeOutExpo). Exit by scaling to 110% and fading out.

**Spec (AR):** النص يكبر من 20% لـ 100% وهو يظهر خلال 0.5 ثانية (easeOutExpo). وبالخروج يكبر لـ 110% ويختفي.

**When to use:**
- EN: Use when you need a gold version of M-044.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-044.

#### `al-txt-044-boxed` — Zoom In Text · Boxed
**تكبير من صغير · صندوق**

*accent · any · timeline · easing: easeOutExpo · 0.5s*

*Original: M-044*

Variant of M-044: النص داخل صندوق ملون

**Spec (EN):** Text scales from 20% to 100% while fading in over 0.5s (easeOutExpo). Exit by scaling to 110% and fading out.

**Spec (AR):** النص يكبر من 20% لـ 100% وهو يظهر خلال 0.5 ثانية (easeOutExpo). وبالخروج يكبر لـ 110% ويختفي.

**When to use:**
- EN: Use when you need a boxed version of M-044.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-044.

#### `al-txt-045-fast` — Zoom Out Text · Fast
**تصغير من كبير · سريع**

*accent · any · blur · easing: easeOutQuart · 0.45s*

*Original: M-045*

Variant of M-045: أسرع بـ 40%

**Spec (EN):** Text starts at 240% scale and opacity 0 and shrinks to 100% while fading in over 0.45s, like it lands on the screen. Pair with a low "boom".

**Spec (AR):** النص يبدأ بحجم 240% وشفافية 0، ويصغر لـ 100% وهو يظهر خلال 0.45 ثانية كأنه نزل على الشاشة. حط معاه صوت "بوم" غليظ.

**When to use:**
- EN: Use when you need a fast version of M-045.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-045.

#### `al-txt-045-slow` — Zoom Out Text · Slow
**تصغير من كبير · بطيء**

*accent · any · blur · easing: easeOutQuart · 0.45s*

*Original: M-045*

Variant of M-045: أبطأ بـ 60%

**Spec (EN):** Text starts at 240% scale and opacity 0 and shrinks to 100% while fading in over 0.45s, like it lands on the screen. Pair with a low "boom".

**Spec (AR):** النص يبدأ بحجم 240% وشفافية 0، ويصغر لـ 100% وهو يظهر خلال 0.45 ثانية كأنه نزل على الشاشة. حط معاه صوت "بوم" غليظ.

**When to use:**
- EN: Use when you need a slow version of M-045.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-045.

#### `al-txt-045-gold` — Zoom Out Text · Gold
**تصغير من كبير · ذهبي**

*accent · any · blur · easing: easeOutQuart · 0.45s*

*Original: M-045*

Variant of M-045: نسخة ذهبية فاخرة

**Spec (EN):** Text starts at 240% scale and opacity 0 and shrinks to 100% while fading in over 0.45s, like it lands on the screen. Pair with a low "boom".

**Spec (AR):** النص يبدأ بحجم 240% وشفافية 0، ويصغر لـ 100% وهو يظهر خلال 0.45 ثانية كأنه نزل على الشاشة. حط معاه صوت "بوم" غليظ.

**When to use:**
- EN: Use when you need a gold version of M-045.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-045.

#### `al-txt-045-boxed` — Zoom Out Text · Boxed
**تصغير من كبير · صندوق**

*accent · any · blur · easing: easeOutQuart · 0.45s*

*Original: M-045*

Variant of M-045: النص داخل صندوق ملون

**Spec (EN):** Text starts at 240% scale and opacity 0 and shrinks to 100% while fading in over 0.45s, like it lands on the screen. Pair with a low "boom".

**Spec (AR):** النص يبدأ بحجم 240% وشفافية 0، ويصغر لـ 100% وهو يظهر خلال 0.45 ثانية كأنه نزل على الشاشة. حط معاه صوت "بوم" غليظ.

**When to use:**
- EN: Use when you need a boxed version of M-045.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-045.

#### `al-txt-046-fast` — Flip In · Fast
**قلب ثلاثي الأبعاد · سريع**

*accent · any · depth · easing: easeOutBack · 0.5s in · 0.4s out*

*Original: M-046*

Variant of M-046: أسرع بـ 40%

**Spec (EN):** Text rotates from 90° to 0° around the X axis with perspective while fading in over 0.5s. Exit by rotating to -90°.

**Spec (AR):** النص يلف من 90 درجة لـ 0 على المحور الأفقي مع عمق 3D وهو يظهر خلال 0.5 ثانية. وبالخروج يلف لـ -90 درجة.

**When to use:**
- EN: Use when you need a fast version of M-046.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-046.

#### `al-txt-046-slow` — Flip In · Slow
**قلب ثلاثي الأبعاد · بطيء**

*accent · any · depth · easing: easeOutBack · 0.5s in · 0.4s out*

*Original: M-046*

Variant of M-046: أبطأ بـ 60%

**Spec (EN):** Text rotates from 90° to 0° around the X axis with perspective while fading in over 0.5s. Exit by rotating to -90°.

**Spec (AR):** النص يلف من 90 درجة لـ 0 على المحور الأفقي مع عمق 3D وهو يظهر خلال 0.5 ثانية. وبالخروج يلف لـ -90 درجة.

**When to use:**
- EN: Use when you need a slow version of M-046.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-046.

#### `al-txt-046-gold` — Flip In · Gold
**قلب ثلاثي الأبعاد · ذهبي**

*accent · any · depth · easing: easeOutBack · 0.5s in · 0.4s out*

*Original: M-046*

Variant of M-046: نسخة ذهبية فاخرة

**Spec (EN):** Text rotates from 90° to 0° around the X axis with perspective while fading in over 0.5s. Exit by rotating to -90°.

**Spec (AR):** النص يلف من 90 درجة لـ 0 على المحور الأفقي مع عمق 3D وهو يظهر خلال 0.5 ثانية. وبالخروج يلف لـ -90 درجة.

**When to use:**
- EN: Use when you need a gold version of M-046.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-046.

#### `al-txt-046-boxed` — Flip In · Boxed
**قلب ثلاثي الأبعاد · صندوق**

*accent · any · depth · easing: easeOutBack · 0.5s in · 0.4s out*

*Original: M-046*

Variant of M-046: النص داخل صندوق ملون

**Spec (EN):** Text rotates from 90° to 0° around the X axis with perspective while fading in over 0.5s. Exit by rotating to -90°.

**Spec (AR):** النص يلف من 90 درجة لـ 0 على المحور الأفقي مع عمق 3D وهو يظهر خلال 0.5 ثانية. وبالخروج يلف لـ -90 درجة.

**When to use:**
- EN: Use when you need a boxed version of M-046.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-046.

#### `al-txt-047-fast` — Rotate In · Fast
**دخول بدوران · سريع**

*accent · any · depth · easing: easeOutBack · 0.5s*

*Original: M-047*

Variant of M-047: أسرع بـ 40%

**Spec (EN):** Text rotates from -90° and 60% scale to 0° and 100% while fading in over 0.5s. Exit with a small 30° turn and fade.

**Spec (AR):** النص يلف من -90 درجة وحجم 60% لين 0 درجة و100% وهو يظهر خلال 0.5 ثانية. ويطلع بلفة 30 درجة وتلاشي.

**When to use:**
- EN: Use when you need a fast version of M-047.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-047.

#### `al-txt-047-slow` — Rotate In · Slow
**دخول بدوران · بطيء**

*accent · any · depth · easing: easeOutBack · 0.5s*

*Original: M-047*

Variant of M-047: أبطأ بـ 60%

**Spec (EN):** Text rotates from -90° and 60% scale to 0° and 100% while fading in over 0.5s. Exit with a small 30° turn and fade.

**Spec (AR):** النص يلف من -90 درجة وحجم 60% لين 0 درجة و100% وهو يظهر خلال 0.5 ثانية. ويطلع بلفة 30 درجة وتلاشي.

**When to use:**
- EN: Use when you need a slow version of M-047.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-047.

#### `al-txt-047-gold` — Rotate In · Gold
**دخول بدوران · ذهبي**

*accent · any · depth · easing: easeOutBack · 0.5s*

*Original: M-047*

Variant of M-047: نسخة ذهبية فاخرة

**Spec (EN):** Text rotates from -90° and 60% scale to 0° and 100% while fading in over 0.5s. Exit with a small 30° turn and fade.

**Spec (AR):** النص يلف من -90 درجة وحجم 60% لين 0 درجة و100% وهو يظهر خلال 0.5 ثانية. ويطلع بلفة 30 درجة وتلاشي.

**When to use:**
- EN: Use when you need a gold version of M-047.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-047.

#### `al-txt-047-boxed` — Rotate In · Boxed
**دخول بدوران · صندوق**

*accent · any · depth · easing: easeOutBack · 0.5s*

*Original: M-047*

Variant of M-047: النص داخل صندوق ملون

**Spec (EN):** Text rotates from -90° and 60% scale to 0° and 100% while fading in over 0.5s. Exit with a small 30° turn and fade.

**Spec (AR):** النص يلف من -90 درجة وحجم 60% لين 0 درجة و100% وهو يظهر خلال 0.5 ثانية. ويطلع بلفة 30 درجة وتلاشي.

**When to use:**
- EN: Use when you need a boxed version of M-047.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-047.

#### `al-txt-048-fast` — Word Stagger · Fast
**كلمات ورا بعض · سريع**

*accent · any · depth · easing: easeOutCubic · 0.45s per word · 0.2s stagger*

*Original: M-048*

Variant of M-048: أسرع بـ 40%

**Spec (EN):** Each word rises 40px and fades in over 0.45s, starting 0.2s after the previous word. Hold the full line, then fade all out together.

**Spec (AR):** كل كلمة تطلع لفوق 40px وتظهر خلال 0.45 ثانية، وتبدأ بعد اللي قبلها بـ 0.2 ثانية. السطر كامل يثبت، وبعدين كله يختفي مع بعض.

**When to use:**
- EN: Use when you need a fast version of M-048.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-048.

#### `al-txt-048-slow` — Word Stagger · Slow
**كلمات ورا بعض · بطيء**

*accent · any · depth · easing: easeOutCubic · 0.45s per word · 0.2s stagger*

*Original: M-048*

Variant of M-048: أبطأ بـ 60%

**Spec (EN):** Each word rises 40px and fades in over 0.45s, starting 0.2s after the previous word. Hold the full line, then fade all out together.

**Spec (AR):** كل كلمة تطلع لفوق 40px وتظهر خلال 0.45 ثانية، وتبدأ بعد اللي قبلها بـ 0.2 ثانية. السطر كامل يثبت، وبعدين كله يختفي مع بعض.

**When to use:**
- EN: Use when you need a slow version of M-048.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-048.

#### `al-txt-048-gold` — Word Stagger · Gold
**كلمات ورا بعض · ذهبي**

*accent · any · depth · easing: easeOutCubic · 0.45s per word · 0.2s stagger*

*Original: M-048*

Variant of M-048: نسخة ذهبية فاخرة

**Spec (EN):** Each word rises 40px and fades in over 0.45s, starting 0.2s after the previous word. Hold the full line, then fade all out together.

**Spec (AR):** كل كلمة تطلع لفوق 40px وتظهر خلال 0.45 ثانية، وتبدأ بعد اللي قبلها بـ 0.2 ثانية. السطر كامل يثبت، وبعدين كله يختفي مع بعض.

**When to use:**
- EN: Use when you need a gold version of M-048.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-048.

#### `al-txt-048-boxed` — Word Stagger · Boxed
**كلمات ورا بعض · صندوق**

*accent · any · depth · easing: easeOutCubic · 0.45s per word · 0.2s stagger*

*Original: M-048*

Variant of M-048: النص داخل صندوق ملون

**Spec (EN):** Each word rises 40px and fades in over 0.45s, starting 0.2s after the previous word. Hold the full line, then fade all out together.

**Spec (AR):** كل كلمة تطلع لفوق 40px وتظهر خلال 0.45 ثانية، وتبدأ بعد اللي قبلها بـ 0.2 ثانية. السطر كامل يثبت، وبعدين كله يختفي مع بعض.

**When to use:**
- EN: Use when you need a boxed version of M-048.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-048.

#### `al-txt-049-fast` — Elastic Pop · Fast
**نطة مطاطية · سريع**

*accent · any · timeline · easing: elastic · 0.6s*

*Original: M-049*

Variant of M-049: أسرع بـ 40%

**Spec (EN):** Text scales from 0 to a squash (130% wide, 80% tall), then a stretch (85% wide, 115% tall), then settles at 100% over about 0.6s.

**Spec (AR):** النص يكبر من 0 لشكل مضغوط (130% عرض و80% طول)، وبعدين ممطوط (85% عرض و115% طول)، ويستقر على 100% خلال تقريباً 0.6 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-049.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-049.

#### `al-txt-049-slow` — Elastic Pop · Slow
**نطة مطاطية · بطيء**

*accent · any · timeline · easing: elastic · 0.6s*

*Original: M-049*

Variant of M-049: أبطأ بـ 60%

**Spec (EN):** Text scales from 0 to a squash (130% wide, 80% tall), then a stretch (85% wide, 115% tall), then settles at 100% over about 0.6s.

**Spec (AR):** النص يكبر من 0 لشكل مضغوط (130% عرض و80% طول)، وبعدين ممطوط (85% عرض و115% طول)، ويستقر على 100% خلال تقريباً 0.6 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-049.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-049.

#### `al-txt-049-gold` — Elastic Pop · Gold
**نطة مطاطية · ذهبي**

*accent · any · timeline · easing: elastic · 0.6s*

*Original: M-049*

Variant of M-049: نسخة ذهبية فاخرة

**Spec (EN):** Text scales from 0 to a squash (130% wide, 80% tall), then a stretch (85% wide, 115% tall), then settles at 100% over about 0.6s.

**Spec (AR):** النص يكبر من 0 لشكل مضغوط (130% عرض و80% طول)، وبعدين ممطوط (85% عرض و115% طول)، ويستقر على 100% خلال تقريباً 0.6 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-049.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-049.

#### `al-txt-049-boxed` — Elastic Pop · Boxed
**نطة مطاطية · صندوق**

*accent · any · timeline · easing: elastic · 0.6s*

*Original: M-049*

Variant of M-049: النص داخل صندوق ملون

**Spec (EN):** Text scales from 0 to a squash (130% wide, 80% tall), then a stretch (85% wide, 115% tall), then settles at 100% over about 0.6s.

**Spec (AR):** النص يكبر من 0 لشكل مضغوط (130% عرض و80% طول)، وبعدين ممطوط (85% عرض و115% طول)، ويستقر على 100% خلال تقريباً 0.6 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-049.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-049.

#### `al-txt-050-fast` — Split Reveal · Fast
**النص ينقسم ويتجمع · سريع**

*accent · any · depth · easing: easeOutQuart · 0.5s*

*Original: M-050*

Variant of M-050: أسرع بـ 40%

**Spec (EN):** The top half of the text slides down from 70% above and the bottom half slides up from 70% below, meeting at the line over 0.5s.

**Spec (AR):** النص الفوقاني من الكلمة ينزل من فوق بـ 70% والنص التحتاني يطلع من تحت بـ 70%، ويتجمعون على السطر خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-050.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-050.

#### `al-txt-050-slow` — Split Reveal · Slow
**النص ينقسم ويتجمع · بطيء**

*accent · any · depth · easing: easeOutQuart · 0.5s*

*Original: M-050*

Variant of M-050: أبطأ بـ 60%

**Spec (EN):** The top half of the text slides down from 70% above and the bottom half slides up from 70% below, meeting at the line over 0.5s.

**Spec (AR):** النص الفوقاني من الكلمة ينزل من فوق بـ 70% والنص التحتاني يطلع من تحت بـ 70%، ويتجمعون على السطر خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-050.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-050.

#### `al-txt-050-gold` — Split Reveal · Gold
**النص ينقسم ويتجمع · ذهبي**

*accent · any · depth · easing: easeOutQuart · 0.5s*

*Original: M-050*

Variant of M-050: نسخة ذهبية فاخرة

**Spec (EN):** The top half of the text slides down from 70% above and the bottom half slides up from 70% below, meeting at the line over 0.5s.

**Spec (AR):** النص الفوقاني من الكلمة ينزل من فوق بـ 70% والنص التحتاني يطلع من تحت بـ 70%، ويتجمعون على السطر خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-050.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-050.

#### `al-txt-050-boxed` — Split Reveal · Boxed
**النص ينقسم ويتجمع · صندوق**

*accent · any · depth · easing: easeOutQuart · 0.5s*

*Original: M-050*

Variant of M-050: النص داخل صندوق ملون

**Spec (EN):** The top half of the text slides down from 70% above and the bottom half slides up from 70% below, meeting at the line over 0.5s.

**Spec (AR):** النص الفوقاني من الكلمة ينزل من فوق بـ 70% والنص التحتاني يطلع من تحت بـ 70%، ويتجمعون على السطر خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-050.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-050.

#### `al-txt-051-fast` — Scramble Decode · Fast
**فك الشفرة · سريع**

*accent · calm · timeline · easing: linear · ~1s decode*

*Original: M-051*

Variant of M-051: أسرع بـ 40%

**Spec (EN):** Each character cycles through random symbols (A–Z, 0–9, #%&) every 2 frames, then locks to its final letter from left to right over about 1s.

**Spec (AR):** كل حرف يتبدل بين رموز عشوائية (A–Z و 0–9 و #%&) كل فريمين، وبعدين يثبت على حرفه الصحيح من اليسار لليمين خلال تقريباً ثانية.

**When to use:**
- EN: Use when you need a fast version of M-051.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-051.

#### `al-txt-051-slow` — Scramble Decode · Slow
**فك الشفرة · بطيء**

*accent · calm · timeline · easing: linear · ~1s decode*

*Original: M-051*

Variant of M-051: أبطأ بـ 60%

**Spec (EN):** Each character cycles through random symbols (A–Z, 0–9, #%&) every 2 frames, then locks to its final letter from left to right over about 1s.

**Spec (AR):** كل حرف يتبدل بين رموز عشوائية (A–Z و 0–9 و #%&) كل فريمين، وبعدين يثبت على حرفه الصحيح من اليسار لليمين خلال تقريباً ثانية.

**When to use:**
- EN: Use when you need a slow version of M-051.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-051.

#### `al-txt-051-gold` — Scramble Decode · Gold
**فك الشفرة · ذهبي**

*accent · calm · timeline · easing: linear · ~1s decode*

*Original: M-051*

Variant of M-051: نسخة ذهبية فاخرة

**Spec (EN):** Each character cycles through random symbols (A–Z, 0–9, #%&) every 2 frames, then locks to its final letter from left to right over about 1s.

**Spec (AR):** كل حرف يتبدل بين رموز عشوائية (A–Z و 0–9 و #%&) كل فريمين، وبعدين يثبت على حرفه الصحيح من اليسار لليمين خلال تقريباً ثانية.

**When to use:**
- EN: Use when you need a gold version of M-051.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-051.

#### `al-txt-051-boxed` — Scramble Decode · Boxed
**فك الشفرة · صندوق**

*accent · calm · timeline · easing: linear · ~1s decode*

*Original: M-051*

Variant of M-051: النص داخل صندوق ملون

**Spec (EN):** Each character cycles through random symbols (A–Z, 0–9, #%&) every 2 frames, then locks to its final letter from left to right over about 1s.

**Spec (AR):** كل حرف يتبدل بين رموز عشوائية (A–Z و 0–9 و #%&) كل فريمين، وبعدين يثبت على حرفه الصحيح من اليسار لليمين خلال تقريباً ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-051.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-051.

#### `al-txt-052-fast` — Wave Text · Fast
**موجة حروف · سريع**

*accent · calm · depth · easing: easeInOutSine · loop · 0.08s stagger*

*Original: M-052*

Variant of M-052: أسرع بـ 40%

**Spec (EN):** Each letter moves up 28% and back in a smooth wave, each starting 0.08s after the previous one, so a ripple runs across the word.

**Spec (AR):** كل حرف يطلع 28% لفوق ويرجع بموجة ناعمة، وكل حرف يبدأ بعد اللي قبله بـ 0.08 ثانية، فتمشي موجة على الكلمة.

**When to use:**
- EN: Use when you need a fast version of M-052.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-052.

#### `al-txt-052-slow` — Wave Text · Slow
**موجة حروف · بطيء**

*accent · calm · depth · easing: easeInOutSine · loop · 0.08s stagger*

*Original: M-052*

Variant of M-052: أبطأ بـ 60%

**Spec (EN):** Each letter moves up 28% and back in a smooth wave, each starting 0.08s after the previous one, so a ripple runs across the word.

**Spec (AR):** كل حرف يطلع 28% لفوق ويرجع بموجة ناعمة، وكل حرف يبدأ بعد اللي قبله بـ 0.08 ثانية، فتمشي موجة على الكلمة.

**When to use:**
- EN: Use when you need a slow version of M-052.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-052.

#### `al-txt-052-gold` — Wave Text · Gold
**موجة حروف · ذهبي**

*accent · calm · depth · easing: easeInOutSine · loop · 0.08s stagger*

*Original: M-052*

Variant of M-052: نسخة ذهبية فاخرة

**Spec (EN):** Each letter moves up 28% and back in a smooth wave, each starting 0.08s after the previous one, so a ripple runs across the word.

**Spec (AR):** كل حرف يطلع 28% لفوق ويرجع بموجة ناعمة، وكل حرف يبدأ بعد اللي قبله بـ 0.08 ثانية، فتمشي موجة على الكلمة.

**When to use:**
- EN: Use when you need a gold version of M-052.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-052.

#### `al-txt-052-boxed` — Wave Text · Boxed
**موجة حروف · صندوق**

*accent · calm · depth · easing: easeInOutSine · loop · 0.08s stagger*

*Original: M-052*

Variant of M-052: النص داخل صندوق ملون

**Spec (EN):** Each letter moves up 28% and back in a smooth wave, each starting 0.08s after the previous one, so a ripple runs across the word.

**Spec (AR):** كل حرف يطلع 28% لفوق ويرجع بموجة ناعمة، وكل حرف يبدأ بعد اللي قبله بـ 0.08 ثانية، فتمشي موجة على الكلمة.

**When to use:**
- EN: Use when you need a boxed version of M-052.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-052.

#### `al-txt-053-fast` — Outline to Fill · Fast
**حدود ثم تعبئة · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.8s outline · 0.4s fill*

*Original: M-053*

Variant of M-053: أسرع بـ 40%

**Spec (EN):** The text first appears as an accent outline only, revealed from the reading-start side over 0.8s, then the fill color fades in over 0.4s.

**Spec (AR):** النص يطلع أول كحدود بلون الهوية بس، وتنكشف من جهة بداية القراءة خلال 0.8 ثانية، وبعدين لون التعبئة يظهر خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-053.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-053.

#### `al-txt-053-slow` — Outline to Fill · Slow
**حدود ثم تعبئة · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.8s outline · 0.4s fill*

*Original: M-053*

Variant of M-053: أبطأ بـ 60%

**Spec (EN):** The text first appears as an accent outline only, revealed from the reading-start side over 0.8s, then the fill color fades in over 0.4s.

**Spec (AR):** النص يطلع أول كحدود بلون الهوية بس، وتنكشف من جهة بداية القراءة خلال 0.8 ثانية، وبعدين لون التعبئة يظهر خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-053.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-053.

#### `al-txt-053-gold` — Outline to Fill · Gold
**حدود ثم تعبئة · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.8s outline · 0.4s fill*

*Original: M-053*

Variant of M-053: نسخة ذهبية فاخرة

**Spec (EN):** The text first appears as an accent outline only, revealed from the reading-start side over 0.8s, then the fill color fades in over 0.4s.

**Spec (AR):** النص يطلع أول كحدود بلون الهوية بس، وتنكشف من جهة بداية القراءة خلال 0.8 ثانية، وبعدين لون التعبئة يظهر خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-053.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-053.

#### `al-txt-053-boxed` — Outline to Fill · Boxed
**حدود ثم تعبئة · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.8s outline · 0.4s fill*

*Original: M-053*

Variant of M-053: النص داخل صندوق ملون

**Spec (EN):** The text first appears as an accent outline only, revealed from the reading-start side over 0.8s, then the fill color fades in over 0.4s.

**Spec (AR):** النص يطلع أول كحدود بلون الهوية بس، وتنكشف من جهة بداية القراءة خلال 0.8 ثانية، وبعدين لون التعبئة يظهر خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-053.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-053.

#### `al-txt-054-fast` — Spotlight Reveal · Fast
**ضوء يكشف النص · سريع**

*accent · calm · blur · easing: easeInOutSine · 1.4s sweep*

*Original: M-054*

Variant of M-054: أسرع بـ 40%

**Spec (EN):** The text sits at 12% opacity. A soft circular spotlight (radius about 13% of the width) sweeps across it and shows the text at full brightness where it passes.

**Spec (AR):** النص باهت بشفافية 12%. ضوء دائري ناعم (نصف قطره تقريباً 13% من العرض) يمر عليه، ووين ما يمر يطلع النص بكامل وضوحه.

**When to use:**
- EN: Use when you need a fast version of M-054.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-054.

#### `al-txt-054-slow` — Spotlight Reveal · Slow
**ضوء يكشف النص · بطيء**

*accent · calm · blur · easing: easeInOutSine · 1.4s sweep*

*Original: M-054*

Variant of M-054: أبطأ بـ 60%

**Spec (EN):** The text sits at 12% opacity. A soft circular spotlight (radius about 13% of the width) sweeps across it and shows the text at full brightness where it passes.

**Spec (AR):** النص باهت بشفافية 12%. ضوء دائري ناعم (نصف قطره تقريباً 13% من العرض) يمر عليه، ووين ما يمر يطلع النص بكامل وضوحه.

**When to use:**
- EN: Use when you need a slow version of M-054.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-054.

#### `al-txt-054-gold` — Spotlight Reveal · Gold
**ضوء يكشف النص · ذهبي**

*accent · calm · blur · easing: easeInOutSine · 1.4s sweep*

*Original: M-054*

Variant of M-054: نسخة ذهبية فاخرة

**Spec (EN):** The text sits at 12% opacity. A soft circular spotlight (radius about 13% of the width) sweeps across it and shows the text at full brightness where it passes.

**Spec (AR):** النص باهت بشفافية 12%. ضوء دائري ناعم (نصف قطره تقريباً 13% من العرض) يمر عليه، ووين ما يمر يطلع النص بكامل وضوحه.

**When to use:**
- EN: Use when you need a gold version of M-054.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-054.

#### `al-txt-054-boxed` — Spotlight Reveal · Boxed
**ضوء يكشف النص · صندوق**

*accent · calm · blur · easing: easeInOutSine · 1.4s sweep*

*Original: M-054*

Variant of M-054: النص داخل صندوق ملون

**Spec (EN):** The text sits at 12% opacity. A soft circular spotlight (radius about 13% of the width) sweeps across it and shows the text at full brightness where it passes.

**Spec (AR):** النص باهت بشفافية 12%. ضوء دائري ناعم (نصف قطره تقريباً 13% من العرض) يمر عليه، ووين ما يمر يطلع النص بكامل وضوحه.

**When to use:**
- EN: Use when you need a boxed version of M-054.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-054.

#### `al-txt-055-fast` — Gradient Wipe Text · Fast
**تدرج يمسح النص · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-055*

Variant of M-055: أسرع بـ 40%

**Spec (EN):** A two-color gradient (accent and white) is clipped to the text and slides across it over 0.8s, so the word changes color with a soft edge.

**Spec (AR):** تدرج بلونين (لون الهوية والأبيض) داخل حروف النص، ويتحرك عليه خلال 0.8 ثانية، فالكلمة يتغير لونها بحافة ناعمة.

**When to use:**
- EN: Use when you need a fast version of M-055.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-055.

#### `al-txt-055-slow` — Gradient Wipe Text · Slow
**تدرج يمسح النص · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-055*

Variant of M-055: أبطأ بـ 60%

**Spec (EN):** A two-color gradient (accent and white) is clipped to the text and slides across it over 0.8s, so the word changes color with a soft edge.

**Spec (AR):** تدرج بلونين (لون الهوية والأبيض) داخل حروف النص، ويتحرك عليه خلال 0.8 ثانية، فالكلمة يتغير لونها بحافة ناعمة.

**When to use:**
- EN: Use when you need a slow version of M-055.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-055.

#### `al-txt-055-gold` — Gradient Wipe Text · Gold
**تدرج يمسح النص · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-055*

Variant of M-055: نسخة ذهبية فاخرة

**Spec (EN):** A two-color gradient (accent and white) is clipped to the text and slides across it over 0.8s, so the word changes color with a soft edge.

**Spec (AR):** تدرج بلونين (لون الهوية والأبيض) داخل حروف النص، ويتحرك عليه خلال 0.8 ثانية، فالكلمة يتغير لونها بحافة ناعمة.

**When to use:**
- EN: Use when you need a gold version of M-055.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-055.

#### `al-txt-055-boxed` — Gradient Wipe Text · Boxed
**تدرج يمسح النص · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-055*

Variant of M-055: النص داخل صندوق ملون

**Spec (EN):** A two-color gradient (accent and white) is clipped to the text and slides across it over 0.8s, so the word changes color with a soft edge.

**Spec (AR):** تدرج بلونين (لون الهوية والأبيض) داخل حروف النص، ويتحرك عليه خلال 0.8 ثانية، فالكلمة يتغير لونها بحافة ناعمة.

**When to use:**
- EN: Use when you need a boxed version of M-055.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-055.

#### `al-txt-056-fast` — Neon Flicker · Fast
**نيون يرمش · سريع**

*accent · any · blur · easing: steps · 0.8s flicker*

*Original: M-056*

Variant of M-056: أسرع بـ 40%

**Spec (EN):** The text has a white core and an accent glow (two text shadows). It turns on with 3–4 quick flickers (opacity 12% to 100%) in the first 0.8s, then stays lit.

**Spec (AR):** النص بقلب أبيض وتوهج بلون الهوية (ظلين للنص). يشتغل بـ 3 إلى 4 رمشات سريعة (شفافية من 12% لـ 100%) أول 0.8 ثانية، وبعدين يبقى شغال.

**When to use:**
- EN: Use when you need a fast version of M-056.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-056.

#### `al-txt-056-slow` — Neon Flicker · Slow
**نيون يرمش · بطيء**

*accent · any · blur · easing: steps · 0.8s flicker*

*Original: M-056*

Variant of M-056: أبطأ بـ 60%

**Spec (EN):** The text has a white core and an accent glow (two text shadows). It turns on with 3–4 quick flickers (opacity 12% to 100%) in the first 0.8s, then stays lit.

**Spec (AR):** النص بقلب أبيض وتوهج بلون الهوية (ظلين للنص). يشتغل بـ 3 إلى 4 رمشات سريعة (شفافية من 12% لـ 100%) أول 0.8 ثانية، وبعدين يبقى شغال.

**When to use:**
- EN: Use when you need a slow version of M-056.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-056.

#### `al-txt-056-gold` — Neon Flicker · Gold
**نيون يرمش · ذهبي**

*accent · any · blur · easing: steps · 0.8s flicker*

*Original: M-056*

Variant of M-056: نسخة ذهبية فاخرة

**Spec (EN):** The text has a white core and an accent glow (two text shadows). It turns on with 3–4 quick flickers (opacity 12% to 100%) in the first 0.8s, then stays lit.

**Spec (AR):** النص بقلب أبيض وتوهج بلون الهوية (ظلين للنص). يشتغل بـ 3 إلى 4 رمشات سريعة (شفافية من 12% لـ 100%) أول 0.8 ثانية، وبعدين يبقى شغال.

**When to use:**
- EN: Use when you need a gold version of M-056.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-056.

#### `al-txt-056-boxed` — Neon Flicker · Boxed
**نيون يرمش · صندوق**

*accent · any · blur · easing: steps · 0.8s flicker*

*Original: M-056*

Variant of M-056: النص داخل صندوق ملون

**Spec (EN):** The text has a white core and an accent glow (two text shadows). It turns on with 3–4 quick flickers (opacity 12% to 100%) in the first 0.8s, then stays lit.

**Spec (AR):** النص بقلب أبيض وتوهج بلون الهوية (ظلين للنص). يشتغل بـ 3 إلى 4 رمشات سريعة (شفافية من 12% لـ 100%) أول 0.8 ثانية، وبعدين يبقى شغال.

**When to use:**
- EN: Use when you need a boxed version of M-056.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-056.

#### `al-txt-057-fast` — Stretch In · Fast
**تمدد · سريع**

*accent · any · blur · easing: easeOutExpo · 0.4s*

*Original: M-057*

Variant of M-057: أسرع بـ 40%

**Spec (EN):** Text starts squashed to 300% width and 20% height at opacity 0 and snaps to normal over 0.4s. Exit by stretching tall and thin.

**Spec (AR):** النص يبدأ ممطوط بعرض 300% وطول 20% وشفافية 0، ويرجع لشكله الطبيعي خلال 0.4 ثانية. ويطلع وهو يتمدد طولي ورفيع.

**When to use:**
- EN: Use when you need a fast version of M-057.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-057.

#### `al-txt-057-slow` — Stretch In · Slow
**تمدد · بطيء**

*accent · any · blur · easing: easeOutExpo · 0.4s*

*Original: M-057*

Variant of M-057: أبطأ بـ 60%

**Spec (EN):** Text starts squashed to 300% width and 20% height at opacity 0 and snaps to normal over 0.4s. Exit by stretching tall and thin.

**Spec (AR):** النص يبدأ ممطوط بعرض 300% وطول 20% وشفافية 0، ويرجع لشكله الطبيعي خلال 0.4 ثانية. ويطلع وهو يتمدد طولي ورفيع.

**When to use:**
- EN: Use when you need a slow version of M-057.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-057.

#### `al-txt-057-gold` — Stretch In · Gold
**تمدد · ذهبي**

*accent · any · blur · easing: easeOutExpo · 0.4s*

*Original: M-057*

Variant of M-057: نسخة ذهبية فاخرة

**Spec (EN):** Text starts squashed to 300% width and 20% height at opacity 0 and snaps to normal over 0.4s. Exit by stretching tall and thin.

**Spec (AR):** النص يبدأ ممطوط بعرض 300% وطول 20% وشفافية 0، ويرجع لشكله الطبيعي خلال 0.4 ثانية. ويطلع وهو يتمدد طولي ورفيع.

**When to use:**
- EN: Use when you need a gold version of M-057.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-057.

#### `al-txt-057-boxed` — Stretch In · Boxed
**تمدد · صندوق**

*accent · any · blur · easing: easeOutExpo · 0.4s*

*Original: M-057*

Variant of M-057: النص داخل صندوق ملون

**Spec (EN):** Text starts squashed to 300% width and 20% height at opacity 0 and snaps to normal over 0.4s. Exit by stretching tall and thin.

**Spec (AR):** النص يبدأ ممطوط بعرض 300% وطول 20% وشفافية 0، ويرجع لشكله الطبيعي خلال 0.4 ثانية. ويطلع وهو يتمدد طولي ورفيع.

**When to use:**
- EN: Use when you need a boxed version of M-057.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-057.

#### `al-txt-058-fast` — Skew Slide · Fast
**انزلاق مايل · سريع**

*accent · any · timeline · easing: easeOutBack · 0.5s*

*Original: M-058*

Variant of M-058: أسرع بـ 40%

**Spec (EN):** Text slides in from 60% to the right with a -30° skew, overshoots to +10° skew and straightens over 0.5s. Exit to the left skewing the other way.

**Spec (AR):** النص ينزلق من اليمين بـ 60% مايل -30 درجة، يتعدى لميلان +10 درجة ويستقيم خلال 0.5 ثانية. ويطلع لليسار مايل بالعكس.

**When to use:**
- EN: Use when you need a fast version of M-058.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-058.

#### `al-txt-058-slow` — Skew Slide · Slow
**انزلاق مايل · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.5s*

*Original: M-058*

Variant of M-058: أبطأ بـ 60%

**Spec (EN):** Text slides in from 60% to the right with a -30° skew, overshoots to +10° skew and straightens over 0.5s. Exit to the left skewing the other way.

**Spec (AR):** النص ينزلق من اليمين بـ 60% مايل -30 درجة، يتعدى لميلان +10 درجة ويستقيم خلال 0.5 ثانية. ويطلع لليسار مايل بالعكس.

**When to use:**
- EN: Use when you need a slow version of M-058.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-058.

#### `al-txt-058-gold` — Skew Slide · Gold
**انزلاق مايل · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.5s*

*Original: M-058*

Variant of M-058: نسخة ذهبية فاخرة

**Spec (EN):** Text slides in from 60% to the right with a -30° skew, overshoots to +10° skew and straightens over 0.5s. Exit to the left skewing the other way.

**Spec (AR):** النص ينزلق من اليمين بـ 60% مايل -30 درجة، يتعدى لميلان +10 درجة ويستقيم خلال 0.5 ثانية. ويطلع لليسار مايل بالعكس.

**When to use:**
- EN: Use when you need a gold version of M-058.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-058.

#### `al-txt-058-boxed` — Skew Slide · Boxed
**انزلاق مايل · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.5s*

*Original: M-058*

Variant of M-058: النص داخل صندوق ملون

**Spec (EN):** Text slides in from 60% to the right with a -30° skew, overshoots to +10° skew and straightens over 0.5s. Exit to the left skewing the other way.

**Spec (AR):** النص ينزلق من اليمين بـ 60% مايل -30 درجة، يتعدى لميلان +10 درجة ويستقيم خلال 0.5 ثانية. ويطلع لليسار مايل بالعكس.

**When to use:**
- EN: Use when you need a boxed version of M-058.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-058.

#### `al-txt-059-fast` — Kinetic Stack · Fast
**كلمات تتكدس · سريع**

*accent · any · depth · easing: easeOutBounce · 0.5s per word · 0.3s stagger*

*Original: M-059*

Variant of M-059: أسرع بـ 40%

**Spec (EN):** Each word drops in from above (M-043 style) one under the other, 0.3s apart, each in a different size and weight, forming a tight stacked block.

**Spec (AR):** كل كلمة تطيح من فوق (مثل M-043) وحدة تحت الثانية، وبينهم 0.3 ثانية، وكل كلمة بحجم ووزن مختلف، فيطلع شكل مكدس ومتراص.

**When to use:**
- EN: Use when you need a fast version of M-059.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-059.

#### `al-txt-059-slow` — Kinetic Stack · Slow
**كلمات تتكدس · بطيء**

*accent · any · depth · easing: easeOutBounce · 0.5s per word · 0.3s stagger*

*Original: M-059*

Variant of M-059: أبطأ بـ 60%

**Spec (EN):** Each word drops in from above (M-043 style) one under the other, 0.3s apart, each in a different size and weight, forming a tight stacked block.

**Spec (AR):** كل كلمة تطيح من فوق (مثل M-043) وحدة تحت الثانية، وبينهم 0.3 ثانية، وكل كلمة بحجم ووزن مختلف، فيطلع شكل مكدس ومتراص.

**When to use:**
- EN: Use when you need a slow version of M-059.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-059.

#### `al-txt-059-gold` — Kinetic Stack · Gold
**كلمات تتكدس · ذهبي**

*accent · any · depth · easing: easeOutBounce · 0.5s per word · 0.3s stagger*

*Original: M-059*

Variant of M-059: نسخة ذهبية فاخرة

**Spec (EN):** Each word drops in from above (M-043 style) one under the other, 0.3s apart, each in a different size and weight, forming a tight stacked block.

**Spec (AR):** كل كلمة تطيح من فوق (مثل M-043) وحدة تحت الثانية، وبينهم 0.3 ثانية، وكل كلمة بحجم ووزن مختلف، فيطلع شكل مكدس ومتراص.

**When to use:**
- EN: Use when you need a gold version of M-059.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-059.

#### `al-txt-059-boxed` — Kinetic Stack · Boxed
**كلمات تتكدس · صندوق**

*accent · any · depth · easing: easeOutBounce · 0.5s per word · 0.3s stagger*

*Original: M-059*

Variant of M-059: النص داخل صندوق ملون

**Spec (EN):** Each word drops in from above (M-043 style) one under the other, 0.3s apart, each in a different size and weight, forming a tight stacked block.

**Spec (AR):** كل كلمة تطيح من فوق (مثل M-043) وحدة تحت الثانية، وبينهم 0.3 ثانية، وكل كلمة بحجم ووزن مختلف، فيطلع شكل مكدس ومتراص.

**When to use:**
- EN: Use when you need a boxed version of M-059.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-059.

#### `al-txt-060-fast` — Slot Machine · Fast
**حروف مثل السلوت · سريع**

*accent · any · timeline · easing: easeOutQuart · 0.9s · 0.15s stagger*

*Original: M-060*

Variant of M-060: أسرع بـ 40%

**Spec (EN):** Each letter sits in a one-row window and scrolls through a column of 5 random letters before landing on its final letter over 0.9s. Letters stop 0.15s apart from left to right.

**Spec (AR):** كل حرف داخل نافذة بارتفاع سطر واحد، ويمر على عمود من 5 حروف عشوائية قبل ما يوقف على حرفه خلال 0.9 ثانية. والحروف توقف ورا بعض كل 0.15 ثانية من اليسار لليمين.

**When to use:**
- EN: Use when you need a fast version of M-060.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-060.

#### `al-txt-060-slow` — Slot Machine · Slow
**حروف مثل السلوت · بطيء**

*accent · any · timeline · easing: easeOutQuart · 0.9s · 0.15s stagger*

*Original: M-060*

Variant of M-060: أبطأ بـ 60%

**Spec (EN):** Each letter sits in a one-row window and scrolls through a column of 5 random letters before landing on its final letter over 0.9s. Letters stop 0.15s apart from left to right.

**Spec (AR):** كل حرف داخل نافذة بارتفاع سطر واحد، ويمر على عمود من 5 حروف عشوائية قبل ما يوقف على حرفه خلال 0.9 ثانية. والحروف توقف ورا بعض كل 0.15 ثانية من اليسار لليمين.

**When to use:**
- EN: Use when you need a slow version of M-060.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-060.

#### `al-txt-060-gold` — Slot Machine · Gold
**حروف مثل السلوت · ذهبي**

*accent · any · timeline · easing: easeOutQuart · 0.9s · 0.15s stagger*

*Original: M-060*

Variant of M-060: نسخة ذهبية فاخرة

**Spec (EN):** Each letter sits in a one-row window and scrolls through a column of 5 random letters before landing on its final letter over 0.9s. Letters stop 0.15s apart from left to right.

**Spec (AR):** كل حرف داخل نافذة بارتفاع سطر واحد، ويمر على عمود من 5 حروف عشوائية قبل ما يوقف على حرفه خلال 0.9 ثانية. والحروف توقف ورا بعض كل 0.15 ثانية من اليسار لليمين.

**When to use:**
- EN: Use when you need a gold version of M-060.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-060.

#### `al-txt-060-boxed` — Slot Machine · Boxed
**حروف مثل السلوت · صندوق**

*accent · any · timeline · easing: easeOutQuart · 0.9s · 0.15s stagger*

*Original: M-060*

Variant of M-060: النص داخل صندوق ملون

**Spec (EN):** Each letter sits in a one-row window and scrolls through a column of 5 random letters before landing on its final letter over 0.9s. Letters stop 0.15s apart from left to right.

**Spec (AR):** كل حرف داخل نافذة بارتفاع سطر واحد، ويمر على عمود من 5 حروف عشوائية قبل ما يوقف على حرفه خلال 0.9 ثانية. والحروف توقف ورا بعض كل 0.15 ثانية من اليسار لليمين.

**When to use:**
- EN: Use when you need a boxed version of M-060.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-060.

### Emphasis (الإبراز) — 125 motions

#### `al-emp-006` — Highlight Sweep
**تظليل الكلمة**

*workhorse · any · timeline · easing: easeInOutCubic · 0.5s sweep*

*Original: M-006*

Highlights a key word like a marker pen.

**Spec (EN):** A solid accent-colored box grows behind the word from 0% to 100% width over 0.5s (from the reading-start side: right for Arabic). The word color switches to dark for contrast. The box shrinks back on exit.

**Spec (AR):** مربع بلون الهوية يكبر ورا الكلمة من 0% لـ 100% من عرضها خلال 0.5 ثانية، من جهة بداية القراءة (اليمين بالعربي). لون الكلمة يصير غامق عشان يبين. وبالخروج المربع يصغر ويرجع.

**When to use:**
- EN: Highlights a key word like a marker pen.
- AR: تبرز كلمة مهمة في الجملة كأنها بقلم فسفوري.

#### `al-emp-007` — Underline Draw
**خط ينرسم تحت الكلمة**

*workhorse · any · timeline · easing: easeInOutQuint · 0.6s draw*

*Original: M-007*

A quiet emphasis on one word.

**Spec (EN):** A rounded accent line (about 8% of the font size thick) draws under the word from the reading-start side to the end over 0.6s, holds, then retracts toward the far side.

**Spec (AR):** خط بلون الهوية بزوايا دائرية (سماكته تقريباً 8% من حجم الخط) ينرسم تحت الكلمة من بداية القراءة لآخرها خلال 0.6 ثانية، يثبت، وبعدين ينسحب للجهة الثانية.

**When to use:**
- EN: A quiet emphasis on one word.
- AR: تأكيد هادي على كلمة.

#### `al-emp-008` — Scale Punch
**ضربة تكبير**

*workhorse · high · timeline · easing: easeOutBack · 0.15s punch · 0.25s settle*

*Original: M-008*

A strong word that needs a hit on the beat or a sound effect.

**Spec (EN):** On the exact spoken frame the word jumps to 150% scale in 0.15s and turns accent color, then settles to 125% over 0.25s and holds. Return to 100% at the end. Pair it with a short "boom" or "pop" sound effect.

**Spec (AR):** بنفس فريم نطق الكلمة، تكبر لـ 150% خلال 0.15 ثانية ويصير لونها لون الهوية، وبعدين تستقر على 125% خلال 0.25 ثانية وتثبت. ترجع 100% بالنهاية. حط معها صوت "بوم" أو "بوب" قصير.

**When to use:**
- EN: A strong word that needs a hit on the beat or a sound effect.
- AR: كلمة قوية تبي لها ضربة مع الإيقاع أو المؤثر الصوتي.

#### `al-emp-009` — Word Shake
**اهتزاز الكلمة**

*workhorse · calm · depth · easing: linear (damped) · 0.6s shake*

*Original: M-009*

Surprise, anger or a warning.

**Spec (EN):** The word shakes horizontally with ±6% offsets and ±4° rotation, alternating every 0.04–0.05s for about 0.6s, with the amplitude damping toward zero.

**Spec (AR):** الكلمة تهتز يمين ويسار بإزاحة ±6% ودوران ±4 درجات، تتبدل كل 0.04 إلى 0.05 ثانية لمدة تقريباً 0.6 ثانية، والهزة تخف تدريجياً لين توقف.

**When to use:**
- EN: Surprise, anger or a warning.
- AR: مفاجأة أو غضب أو تحذير.

#### `al-emp-010` — Glitch Text
**جلتش**

*workhorse · any · timeline · easing: steps · 0.6s glitch burst*

*Original: M-010*

Tech, AI and hacking topics.

**Spec (EN):** For about 0.6s, two copies of the text (cyan #3FE0FF and red #FF3F6C) jitter ±5% offset and show through random horizontal slice masks, changing every 2–3 frames, while the main text skews ±8°. Then everything snaps back clean.

**Spec (AR):** لمدة تقريباً 0.6 ثانية، نسختين من النص (سماوي #3FE0FF وأحمر #FF3F6C) ترجف بإزاحة ±5% وتطلع من شرائح أفقية عشوائية تتغير كل 2 إلى 3 فريمات، والنص الأساسي يميل ±8 درجات. بعدها كل شي يرجع نظيف مرة وحدة.

**When to use:**
- EN: Tech, AI and hacking topics.
- AR: مواضيع التقنية والذكاء الاصطناعي والهكر.

#### `al-emp-061` — Circle Around
**دائرة حول الكلمة**

*workhorse · any · timeline · easing: easeInOutCubic · 0.6s draw*

*Original: M-061*

Circles a key word as if drawn with a pen.

**Spec (EN):** A hand-drawn accent ellipse strokes around the word over 0.6s (animated stroke), holds, then erases. Slightly uneven so it feels hand-made.

**Spec (AR):** دائرة مرسومة باليد بلون الهوية تنرسم حول الكلمة خلال 0.6 ثانية، تثبت، وبعدين تنمسح. وتكون مو منتظمة شوي عشان تبين مرسومة باليد.

**When to use:**
- EN: Circles a key word as if drawn with a pen.
- AR: تدوير كلمة مهمة كأنك رسمت عليها بقلم.

#### `al-emp-062` — Strike Through
**شطب الكلمة**

*workhorse · any · timeline · easing: easeInOutQuint · 0.5s*

*Original: M-062*

Crosses out a wrong or old word before the right one.

**Spec (EN):** An accent line draws through the middle of the word from the reading-start side over 0.5s, holds, then retracts.

**Spec (AR):** خط بلون الهوية ينرسم بنص الكلمة من جهة بداية القراءة خلال 0.5 ثانية، يثبت، وبعدين ينسحب.

**When to use:**
- EN: Crosses out a wrong or old word before the right one.
- AR: تشطب كلمة غلط أو قديمة قبل الصح.

#### `al-emp-063` — Box Outline Draw
**مربع ينرسم حول الكلمة**

*workhorse · any · depth · easing: easeInOutCubic · 0.6s draw*

*Original: M-063*

Frames a word inside a drawn box.

**Spec (EN):** A rounded accent rectangle strokes itself around the word, starting from the top-right corner, over 0.6s. Holds, then erases.

**Spec (AR):** مستطيل بزوايا دائرية بلون الهوية ينرسم حول الكلمة من الزاوية الفوق يمين خلال 0.6 ثانية. يثبت، وبعدين ينمسح.

**When to use:**
- EN: Frames a word inside a drawn box.
- AR: تحط كلمة داخل إطار مثل الملاحظة.

#### `al-emp-064` — Color Pulse
**نبض لون**

*workhorse · calm · timeline · easing: easeInOutSine · loop · 1.6s*

*Original: M-064*

A word gently pulses between two colors.

**Spec (EN):** The word color eases from white to the accent color and back in a 1.6s loop while it is on screen.

**Spec (AR):** لون الكلمة يتحول بنعومة من الأبيض للون الهوية ويرجع كل 1.6 ثانية طول ما هي على الشاشة.

**When to use:**
- EN: A word gently pulses between two colors.
- AR: كلمة يتغير لونها بنبض هادي.

#### `al-emp-065` — Glow Pulse
**توهج نابض**

*workhorse · calm · timeline · easing: easeInOutSine · loop · 1.6s*

*Original: M-065*

A word breathes with a soft glow.

**Spec (EN):** An accent glow (text shadow, blur up to 6% of the width) grows and fades around the word in a 1.6s loop.

**Spec (AR):** توهج بلون الهوية (ظل للنص يوصل ضبابيته لـ 6% من العرض) يكبر ويخف حول الكلمة كل 1.6 ثانية.

**When to use:**
- EN: A word breathes with a soft glow.
- AR: كلمة تتوهج وكأنها تشع.

#### `al-emp-066` — Wiggle
**تمايل**

*workhorse · calm · depth · easing: easeInOutSine · 0.8s*

*Original: M-066*

A word wiggles to grab attention.

**Spec (EN):** The word rotates quickly ±8° and back several times with decreasing angle over about 0.8s, then rests.

**Spec (AR):** الكلمة تلف بسرعة ±8 درجات وترجع كم مرة والزاوية تقل خلال تقريباً 0.8 ثانية، وبعدين توقف.

**When to use:**
- EN: A word wiggles to grab attention.
- AR: كلمة تتمايل تجذب الانتباه، مثل "انتبه".

#### `al-emp-067` — Bounce Word
**الكلمة تنط**

*workhorse · any · depth · easing: easeOutQuad · 0.6s*

*Original: M-067*

A word hops twice, light and fun.

**Spec (EN):** The word jumps up 35% of its height and lands, then a second smaller jump of 14%, over about 0.6s.

**Spec (AR):** الكلمة تنط لفوق 35% من طولها وتنزل، وبعدها نطة ثانية أصغر 14%، خلال تقريباً 0.6 ثانية.

**When to use:**
- EN: A word hops twice, light and fun.
- AR: كلمة تنط مرتين، حركة خفيفة ومرحة.

#### `al-emp-068` — Arrow Point
**سهم يأشر**

*workhorse · calm · timeline · easing: easeInOutSine · loop · 1s*

*Original: M-068*

An arrow points at a word or an object on screen.

**Spec (EN):** An accent arrow sits beside the target and nudges toward it by 30% of its length and back in a 1s loop.

**Spec (AR):** سهم بلون الهوية جنب الهدف، يتحرك ناحيته 30% من طوله ويرجع كل ثانية.

**When to use:**
- EN: An arrow points at a word or an object on screen.
- AR: سهم يأشر على كلمة أو شي بالشاشة.

#### `al-emp-069` — Zoom Blur Word
**زوم مع ضبابية للكلمة**

*workhorse · any · blur · easing: easeOutExpo · 0.3s*

*Original: M-069*

A fast zoom hit on a single word.

**Spec (EN):** The word jumps to 160% with a 1.5% blur in 0.2s, then settles at 120% sharp over 0.3s. Return to 100% at the end.

**Spec (AR):** الكلمة تكبر لـ 160% مع ضبابية 1.5% خلال 0.2 ثانية، وبعدين تستقر على 120% واضحة خلال 0.3 ثانية. ترجع 100% بالنهاية.

**When to use:**
- EN: A fast zoom hit on a single word.
- AR: ضربة زوم سريعة على كلمة وحدة.

#### `al-emp-070` — Rubber Band
**مطاطية**

*workhorse · any · timeline · easing: easeOut · 0.7s*

*Original: M-070*

A word squashes and stretches like rubber.

**Spec (EN):** The word scales to 125%×75%, then 75%×125%, then smaller swings until it settles at 100% over 0.7s.

**Spec (AR):** الكلمة تصير 125%×75%، وبعدين 75%×125%، وبعدين تذبذبات أصغر لين تستقر على 100% خلال 0.7 ثانية.

**When to use:**
- EN: A word squashes and stretches like rubber.
- AR: كلمة تنضغط وتتمدد مثل المطاط.

#### `al-emp-071` — Jello
**هلامي**

*workhorse · any · timeline · easing: easeOut · 0.9s*

*Original: M-071*

A word wobbles like jelly.

**Spec (EN):** The word skews on both axes by -12°, then +6°, -3°, +1.5° and settles over 0.9s.

**Spec (AR):** الكلمة تميل على المحورين -12 درجة، وبعدين +6، و-3، و+1.5، وتستقر خلال 0.9 ثانية.

**When to use:**
- EN: A word wobbles like jelly.
- AR: كلمة تهتز مثل الجيلي.

#### `al-emp-072` — Heartbeat
**نبض قلب**

*workhorse · any · sound · easing: easeInOut · loop · 1.4s*

*Original: M-072*

A word pulses like a heartbeat.

**Spec (EN):** Two quick pulses to 130% scale and back (like a heartbeat), then a pause, in a 1.4s loop.

**Spec (AR):** نبضتين سريعة لـ 130% وترجع (مثل دقة القلب)، وبعدين وقفة، كل 1.4 ثانية.

**When to use:**
- EN: A word pulses like a heartbeat.
- AR: كلمة تنبض مثل القلب، تناسب الحب أو التوتر.

#### `al-emp-073` — Marker Scribble
**خربشة تحت الكلمة**

*workhorse · any · timeline · easing: easeInOutCubic · 0.6s draw*

*Original: M-073*

A zigzag scribble under a word like a marker.

**Spec (EN):** A loose zigzag accent stroke draws under the word from the reading-start side over 0.6s, holds, then erases.

**Spec (AR):** خط متعرج حر بلون الهوية ينرسم تحت الكلمة من جهة بداية القراءة خلال 0.6 ثانية، يثبت، وبعدين ينمسح.

**When to use:**
- EN: A zigzag scribble under a word like a marker.
- AR: خط متعرج تحت الكلمة مثل قلم التحديد.

#### `al-emp-074` — Spotlight Dim
**تعتيم ما حول الكلمة**

*workhorse · any · timeline · easing: easeInOutCubic · 0.5s in*

*Original: M-074*

Everything dims except the word or face.

**Spec (EN):** A dark overlay (about 80% black) fades in over 0.5s with a soft circular hole around the subject, so only the subject stays lit. Fade out to release.

**Spec (AR):** طبقة غامقة (تقريباً 80% أسود) تظهر خلال 0.5 ثانية وفيها فتحة دائرية ناعمة حول الهدف، فيبقى الهدف بس مضيء. وتختفي بتلاشي.

**When to use:**
- EN: Everything dims except the word or face.
- AR: كل شي يغمق إلا الكلمة أو الوجه.

#### `al-emp-075` — Letter Spacing
**تباعد الحروف**

*workhorse · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-075*

An English word spreads its letters for a premium feel.

**Spec (EN):** The letter spacing grows smoothly from 0 to 0.35em over 0.8s while the word stays centered. Reverse at exit.

**Spec (AR):** المسافة بين الحروف تكبر بنعومة من 0 لـ 0.35em خلال 0.8 ثانية والكلمة تبقى بالنص. وبالخروج ترجع.

**When to use:**
- EN: An English word spreads its letters for a premium feel.
- AR: كلمة إنجليزية تتمدد حروفها بشكل فخم.

#### `al-emp-076` — Flash Hit
**وميض أبيض**

*workhorse · any · blur · easing: easeOut · 0.15s*

*Original: M-076*

A quick white flash on a strong word or cut.

**Spec (EN):** A full-screen white flash rises to 90% opacity in 1–2 frames and fades out over 0.15s, exactly on the beat or word.

**Spec (AR):** وميض أبيض يغطي الشاشة يوصل 90% شفافية خلال فريم أو فريمين ويختفي خلال 0.15 ثانية، بالضبط على الإيقاع أو الكلمة.

**When to use:**
- EN: A quick white flash on a strong word or cut.
- AR: وميض سريع مع كلمة قوية أو قص.

#### `al-emp-077` — Sparkle Stars
**نجوم تلمع**

*workhorse · calm · depth · easing: easeInOutSine · loop · 1.2s*

*Original: M-077*

Sparkles around a word or product for a "fresh" feel.

**Spec (EN):** Three to five small four-point stars pop in around the word at random spots, scale 0 to 100% while rotating 90°, then shrink away, staggered by 0.3s.

**Spec (AR):** من 3 إلى 5 نجوم صغيرة بأربع رؤوس تطلع حول الكلمة بأماكن عشوائية، تكبر من 0 لـ 100% وهي تلف 90 درجة، وبعدين تصغر وتختفي، وبينهم 0.3 ثانية.

**When to use:**
- EN: Sparkles around a word or product for a "fresh" feel.
- AR: لمعة حول كلمة أو منتج، تعطي إحساس "جديد ونظيف".

#### `al-emp-078` — Swing
**تأرجح**

*workhorse · any · depth · easing: easeOut · 1s*

*Original: M-078*

A hanging word swings like a sign.

**Spec (EN):** The word swings from its top edge: +16°, -11°, +7°, -4°, +2° and settles over about 1s.

**Spec (AR):** الكلمة تتأرجح من حافتها الفوق: +16، -11، +7، -4، +2 درجة وتستقر خلال تقريباً ثانية.

**When to use:**
- EN: A hanging word swings like a sign.
- AR: كلمة معلقة تتأرجح مثل اللوحة.

#### `al-emp-079` — Tilt Pop
**ميلان مع تكبير**

*workhorse · high · timeline · easing: easeOutBack · 0.3s*

*Original: M-079*

A word grows with a small tilt, sticker style.

**Spec (EN):** The word scales to 130% while rotating -8° in 0.3s, settles at 120% and -5°, holds, then returns.

**Spec (AR):** الكلمة تكبر لـ 130% وهي تميل -8 درجات خلال 0.3 ثانية، تستقر على 120% و-5 درجات، تثبت، وبعدين ترجع.

**When to use:**
- EN: A word grows with a small tilt, sticker style.
- AR: كلمة تكبر وتميل شوي، ستايل الملصقات.

#### `al-emp-080` — Chromatic Split
**انقسام الألوان**

*workhorse · any · timeline · easing: easeOut · 0.5s*

*Original: M-080*

A word splits into red and cyan channels, tech style.

**Spec (EN):** Red and cyan copies of the word slide out sideways by 1.5% of the width and back in over 0.5s, like an RGB lens split.

**Spec (AR):** نسخة حمرا ونسخة سماوية من الكلمة يطلعون على الجنبين بمسافة 1.5% من العرض ويرجعون خلال 0.5 ثانية، مثل انقسام ألوان العدسة.

**When to use:**
- EN: A word splits into red and cyan channels, tech style.
- AR: كلمة تنفصل ألوانها أحمر وأزرق، ستايل تقني.

#### `al-emp-006-fast` — Highlight Sweep · Fast
**تظليل الكلمة · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.5s sweep*

*Original: M-006*

Variant of M-006: أسرع بـ 40%

**Spec (EN):** A solid accent-colored box grows behind the word from 0% to 100% width over 0.5s (from the reading-start side: right for Arabic). The word color switches to dark for contrast. The box shrinks back on exit.

**Spec (AR):** مربع بلون الهوية يكبر ورا الكلمة من 0% لـ 100% من عرضها خلال 0.5 ثانية، من جهة بداية القراءة (اليمين بالعربي). لون الكلمة يصير غامق عشان يبين. وبالخروج المربع يصغر ويرجع.

**When to use:**
- EN: Use when you need a fast version of M-006.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-006.

#### `al-emp-006-slow` — Highlight Sweep · Slow
**تظليل الكلمة · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.5s sweep*

*Original: M-006*

Variant of M-006: أبطأ بـ 60%

**Spec (EN):** A solid accent-colored box grows behind the word from 0% to 100% width over 0.5s (from the reading-start side: right for Arabic). The word color switches to dark for contrast. The box shrinks back on exit.

**Spec (AR):** مربع بلون الهوية يكبر ورا الكلمة من 0% لـ 100% من عرضها خلال 0.5 ثانية، من جهة بداية القراءة (اليمين بالعربي). لون الكلمة يصير غامق عشان يبين. وبالخروج المربع يصغر ويرجع.

**When to use:**
- EN: Use when you need a slow version of M-006.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-006.

#### `al-emp-006-gold` — Highlight Sweep · Gold
**تظليل الكلمة · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.5s sweep*

*Original: M-006*

Variant of M-006: نسخة ذهبية فاخرة

**Spec (EN):** A solid accent-colored box grows behind the word from 0% to 100% width over 0.5s (from the reading-start side: right for Arabic). The word color switches to dark for contrast. The box shrinks back on exit.

**Spec (AR):** مربع بلون الهوية يكبر ورا الكلمة من 0% لـ 100% من عرضها خلال 0.5 ثانية، من جهة بداية القراءة (اليمين بالعربي). لون الكلمة يصير غامق عشان يبين. وبالخروج المربع يصغر ويرجع.

**When to use:**
- EN: Use when you need a gold version of M-006.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-006.

#### `al-emp-006-boxed` — Highlight Sweep · Boxed
**تظليل الكلمة · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.5s sweep*

*Original: M-006*

Variant of M-006: النص داخل صندوق ملون

**Spec (EN):** A solid accent-colored box grows behind the word from 0% to 100% width over 0.5s (from the reading-start side: right for Arabic). The word color switches to dark for contrast. The box shrinks back on exit.

**Spec (AR):** مربع بلون الهوية يكبر ورا الكلمة من 0% لـ 100% من عرضها خلال 0.5 ثانية، من جهة بداية القراءة (اليمين بالعربي). لون الكلمة يصير غامق عشان يبين. وبالخروج المربع يصغر ويرجع.

**When to use:**
- EN: Use when you need a boxed version of M-006.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-006.

#### `al-emp-007-fast` — Underline Draw · Fast
**خط ينرسم تحت الكلمة · سريع**

*accent · any · timeline · easing: easeInOutQuint · 0.6s draw*

*Original: M-007*

Variant of M-007: أسرع بـ 40%

**Spec (EN):** A rounded accent line (about 8% of the font size thick) draws under the word from the reading-start side to the end over 0.6s, holds, then retracts toward the far side.

**Spec (AR):** خط بلون الهوية بزوايا دائرية (سماكته تقريباً 8% من حجم الخط) ينرسم تحت الكلمة من بداية القراءة لآخرها خلال 0.6 ثانية، يثبت، وبعدين ينسحب للجهة الثانية.

**When to use:**
- EN: Use when you need a fast version of M-007.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-007.

#### `al-emp-007-slow` — Underline Draw · Slow
**خط ينرسم تحت الكلمة · بطيء**

*accent · any · timeline · easing: easeInOutQuint · 0.6s draw*

*Original: M-007*

Variant of M-007: أبطأ بـ 60%

**Spec (EN):** A rounded accent line (about 8% of the font size thick) draws under the word from the reading-start side to the end over 0.6s, holds, then retracts toward the far side.

**Spec (AR):** خط بلون الهوية بزوايا دائرية (سماكته تقريباً 8% من حجم الخط) ينرسم تحت الكلمة من بداية القراءة لآخرها خلال 0.6 ثانية، يثبت، وبعدين ينسحب للجهة الثانية.

**When to use:**
- EN: Use when you need a slow version of M-007.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-007.

#### `al-emp-007-gold` — Underline Draw · Gold
**خط ينرسم تحت الكلمة · ذهبي**

*accent · any · timeline · easing: easeInOutQuint · 0.6s draw*

*Original: M-007*

Variant of M-007: نسخة ذهبية فاخرة

**Spec (EN):** A rounded accent line (about 8% of the font size thick) draws under the word from the reading-start side to the end over 0.6s, holds, then retracts toward the far side.

**Spec (AR):** خط بلون الهوية بزوايا دائرية (سماكته تقريباً 8% من حجم الخط) ينرسم تحت الكلمة من بداية القراءة لآخرها خلال 0.6 ثانية، يثبت، وبعدين ينسحب للجهة الثانية.

**When to use:**
- EN: Use when you need a gold version of M-007.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-007.

#### `al-emp-007-boxed` — Underline Draw · Boxed
**خط ينرسم تحت الكلمة · صندوق**

*accent · any · timeline · easing: easeInOutQuint · 0.6s draw*

*Original: M-007*

Variant of M-007: النص داخل صندوق ملون

**Spec (EN):** A rounded accent line (about 8% of the font size thick) draws under the word from the reading-start side to the end over 0.6s, holds, then retracts toward the far side.

**Spec (AR):** خط بلون الهوية بزوايا دائرية (سماكته تقريباً 8% من حجم الخط) ينرسم تحت الكلمة من بداية القراءة لآخرها خلال 0.6 ثانية، يثبت، وبعدين ينسحب للجهة الثانية.

**When to use:**
- EN: Use when you need a boxed version of M-007.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-007.

#### `al-emp-008-fast` — Scale Punch · Fast
**ضربة تكبير · سريع**

*accent · any · timeline · easing: easeOutBack · 0.15s punch · 0.25s settle*

*Original: M-008*

Variant of M-008: أسرع بـ 40%

**Spec (EN):** On the exact spoken frame the word jumps to 150% scale in 0.15s and turns accent color, then settles to 125% over 0.25s and holds. Return to 100% at the end. Pair it with a short "boom" or "pop" sound effect.

**Spec (AR):** بنفس فريم نطق الكلمة، تكبر لـ 150% خلال 0.15 ثانية ويصير لونها لون الهوية، وبعدين تستقر على 125% خلال 0.25 ثانية وتثبت. ترجع 100% بالنهاية. حط معها صوت "بوم" أو "بوب" قصير.

**When to use:**
- EN: Use when you need a fast version of M-008.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-008.

#### `al-emp-008-slow` — Scale Punch · Slow
**ضربة تكبير · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.15s punch · 0.25s settle*

*Original: M-008*

Variant of M-008: أبطأ بـ 60%

**Spec (EN):** On the exact spoken frame the word jumps to 150% scale in 0.15s and turns accent color, then settles to 125% over 0.25s and holds. Return to 100% at the end. Pair it with a short "boom" or "pop" sound effect.

**Spec (AR):** بنفس فريم نطق الكلمة، تكبر لـ 150% خلال 0.15 ثانية ويصير لونها لون الهوية، وبعدين تستقر على 125% خلال 0.25 ثانية وتثبت. ترجع 100% بالنهاية. حط معها صوت "بوم" أو "بوب" قصير.

**When to use:**
- EN: Use when you need a slow version of M-008.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-008.

#### `al-emp-008-gold` — Scale Punch · Gold
**ضربة تكبير · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.15s punch · 0.25s settle*

*Original: M-008*

Variant of M-008: نسخة ذهبية فاخرة

**Spec (EN):** On the exact spoken frame the word jumps to 150% scale in 0.15s and turns accent color, then settles to 125% over 0.25s and holds. Return to 100% at the end. Pair it with a short "boom" or "pop" sound effect.

**Spec (AR):** بنفس فريم نطق الكلمة، تكبر لـ 150% خلال 0.15 ثانية ويصير لونها لون الهوية، وبعدين تستقر على 125% خلال 0.25 ثانية وتثبت. ترجع 100% بالنهاية. حط معها صوت "بوم" أو "بوب" قصير.

**When to use:**
- EN: Use when you need a gold version of M-008.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-008.

#### `al-emp-008-boxed` — Scale Punch · Boxed
**ضربة تكبير · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.15s punch · 0.25s settle*

*Original: M-008*

Variant of M-008: النص داخل صندوق ملون

**Spec (EN):** On the exact spoken frame the word jumps to 150% scale in 0.15s and turns accent color, then settles to 125% over 0.25s and holds. Return to 100% at the end. Pair it with a short "boom" or "pop" sound effect.

**Spec (AR):** بنفس فريم نطق الكلمة، تكبر لـ 150% خلال 0.15 ثانية ويصير لونها لون الهوية، وبعدين تستقر على 125% خلال 0.25 ثانية وتثبت. ترجع 100% بالنهاية. حط معها صوت "بوم" أو "بوب" قصير.

**When to use:**
- EN: Use when you need a boxed version of M-008.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-008.

#### `al-emp-009-fast` — Word Shake · Fast
**اهتزاز الكلمة · سريع**

*accent · calm · depth · easing: linear (damped) · 0.6s shake*

*Original: M-009*

Variant of M-009: أسرع بـ 40%

**Spec (EN):** The word shakes horizontally with ±6% offsets and ±4° rotation, alternating every 0.04–0.05s for about 0.6s, with the amplitude damping toward zero.

**Spec (AR):** الكلمة تهتز يمين ويسار بإزاحة ±6% ودوران ±4 درجات، تتبدل كل 0.04 إلى 0.05 ثانية لمدة تقريباً 0.6 ثانية، والهزة تخف تدريجياً لين توقف.

**When to use:**
- EN: Use when you need a fast version of M-009.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-009.

#### `al-emp-009-slow` — Word Shake · Slow
**اهتزاز الكلمة · بطيء**

*accent · calm · depth · easing: linear (damped) · 0.6s shake*

*Original: M-009*

Variant of M-009: أبطأ بـ 60%

**Spec (EN):** The word shakes horizontally with ±6% offsets and ±4° rotation, alternating every 0.04–0.05s for about 0.6s, with the amplitude damping toward zero.

**Spec (AR):** الكلمة تهتز يمين ويسار بإزاحة ±6% ودوران ±4 درجات، تتبدل كل 0.04 إلى 0.05 ثانية لمدة تقريباً 0.6 ثانية، والهزة تخف تدريجياً لين توقف.

**When to use:**
- EN: Use when you need a slow version of M-009.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-009.

#### `al-emp-009-gold` — Word Shake · Gold
**اهتزاز الكلمة · ذهبي**

*accent · calm · depth · easing: linear (damped) · 0.6s shake*

*Original: M-009*

Variant of M-009: نسخة ذهبية فاخرة

**Spec (EN):** The word shakes horizontally with ±6% offsets and ±4° rotation, alternating every 0.04–0.05s for about 0.6s, with the amplitude damping toward zero.

**Spec (AR):** الكلمة تهتز يمين ويسار بإزاحة ±6% ودوران ±4 درجات، تتبدل كل 0.04 إلى 0.05 ثانية لمدة تقريباً 0.6 ثانية، والهزة تخف تدريجياً لين توقف.

**When to use:**
- EN: Use when you need a gold version of M-009.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-009.

#### `al-emp-009-boxed` — Word Shake · Boxed
**اهتزاز الكلمة · صندوق**

*accent · calm · depth · easing: linear (damped) · 0.6s shake*

*Original: M-009*

Variant of M-009: النص داخل صندوق ملون

**Spec (EN):** The word shakes horizontally with ±6% offsets and ±4° rotation, alternating every 0.04–0.05s for about 0.6s, with the amplitude damping toward zero.

**Spec (AR):** الكلمة تهتز يمين ويسار بإزاحة ±6% ودوران ±4 درجات، تتبدل كل 0.04 إلى 0.05 ثانية لمدة تقريباً 0.6 ثانية، والهزة تخف تدريجياً لين توقف.

**When to use:**
- EN: Use when you need a boxed version of M-009.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-009.

#### `al-emp-010-fast` — Glitch Text · Fast
**جلتش · سريع**

*accent · any · timeline · easing: steps · 0.6s glitch burst*

*Original: M-010*

Variant of M-010: أسرع بـ 40%

**Spec (EN):** For about 0.6s, two copies of the text (cyan #3FE0FF and red #FF3F6C) jitter ±5% offset and show through random horizontal slice masks, changing every 2–3 frames, while the main text skews ±8°. Then everything snaps back clean.

**Spec (AR):** لمدة تقريباً 0.6 ثانية، نسختين من النص (سماوي #3FE0FF وأحمر #FF3F6C) ترجف بإزاحة ±5% وتطلع من شرائح أفقية عشوائية تتغير كل 2 إلى 3 فريمات، والنص الأساسي يميل ±8 درجات. بعدها كل شي يرجع نظيف مرة وحدة.

**When to use:**
- EN: Use when you need a fast version of M-010.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-010.

#### `al-emp-010-slow` — Glitch Text · Slow
**جلتش · بطيء**

*accent · any · timeline · easing: steps · 0.6s glitch burst*

*Original: M-010*

Variant of M-010: أبطأ بـ 60%

**Spec (EN):** For about 0.6s, two copies of the text (cyan #3FE0FF and red #FF3F6C) jitter ±5% offset and show through random horizontal slice masks, changing every 2–3 frames, while the main text skews ±8°. Then everything snaps back clean.

**Spec (AR):** لمدة تقريباً 0.6 ثانية، نسختين من النص (سماوي #3FE0FF وأحمر #FF3F6C) ترجف بإزاحة ±5% وتطلع من شرائح أفقية عشوائية تتغير كل 2 إلى 3 فريمات، والنص الأساسي يميل ±8 درجات. بعدها كل شي يرجع نظيف مرة وحدة.

**When to use:**
- EN: Use when you need a slow version of M-010.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-010.

#### `al-emp-010-gold` — Glitch Text · Gold
**جلتش · ذهبي**

*accent · any · timeline · easing: steps · 0.6s glitch burst*

*Original: M-010*

Variant of M-010: نسخة ذهبية فاخرة

**Spec (EN):** For about 0.6s, two copies of the text (cyan #3FE0FF and red #FF3F6C) jitter ±5% offset and show through random horizontal slice masks, changing every 2–3 frames, while the main text skews ±8°. Then everything snaps back clean.

**Spec (AR):** لمدة تقريباً 0.6 ثانية، نسختين من النص (سماوي #3FE0FF وأحمر #FF3F6C) ترجف بإزاحة ±5% وتطلع من شرائح أفقية عشوائية تتغير كل 2 إلى 3 فريمات، والنص الأساسي يميل ±8 درجات. بعدها كل شي يرجع نظيف مرة وحدة.

**When to use:**
- EN: Use when you need a gold version of M-010.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-010.

#### `al-emp-010-boxed` — Glitch Text · Boxed
**جلتش · صندوق**

*accent · any · timeline · easing: steps · 0.6s glitch burst*

*Original: M-010*

Variant of M-010: النص داخل صندوق ملون

**Spec (EN):** For about 0.6s, two copies of the text (cyan #3FE0FF and red #FF3F6C) jitter ±5% offset and show through random horizontal slice masks, changing every 2–3 frames, while the main text skews ±8°. Then everything snaps back clean.

**Spec (AR):** لمدة تقريباً 0.6 ثانية، نسختين من النص (سماوي #3FE0FF وأحمر #FF3F6C) ترجف بإزاحة ±5% وتطلع من شرائح أفقية عشوائية تتغير كل 2 إلى 3 فريمات، والنص الأساسي يميل ±8 درجات. بعدها كل شي يرجع نظيف مرة وحدة.

**When to use:**
- EN: Use when you need a boxed version of M-010.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-010.

#### `al-emp-061-fast` — Circle Around · Fast
**دائرة حول الكلمة · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.6s draw*

*Original: M-061*

Variant of M-061: أسرع بـ 40%

**Spec (EN):** A hand-drawn accent ellipse strokes around the word over 0.6s (animated stroke), holds, then erases. Slightly uneven so it feels hand-made.

**Spec (AR):** دائرة مرسومة باليد بلون الهوية تنرسم حول الكلمة خلال 0.6 ثانية، تثبت، وبعدين تنمسح. وتكون مو منتظمة شوي عشان تبين مرسومة باليد.

**When to use:**
- EN: Use when you need a fast version of M-061.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-061.

#### `al-emp-061-slow` — Circle Around · Slow
**دائرة حول الكلمة · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.6s draw*

*Original: M-061*

Variant of M-061: أبطأ بـ 60%

**Spec (EN):** A hand-drawn accent ellipse strokes around the word over 0.6s (animated stroke), holds, then erases. Slightly uneven so it feels hand-made.

**Spec (AR):** دائرة مرسومة باليد بلون الهوية تنرسم حول الكلمة خلال 0.6 ثانية، تثبت، وبعدين تنمسح. وتكون مو منتظمة شوي عشان تبين مرسومة باليد.

**When to use:**
- EN: Use when you need a slow version of M-061.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-061.

#### `al-emp-061-gold` — Circle Around · Gold
**دائرة حول الكلمة · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.6s draw*

*Original: M-061*

Variant of M-061: نسخة ذهبية فاخرة

**Spec (EN):** A hand-drawn accent ellipse strokes around the word over 0.6s (animated stroke), holds, then erases. Slightly uneven so it feels hand-made.

**Spec (AR):** دائرة مرسومة باليد بلون الهوية تنرسم حول الكلمة خلال 0.6 ثانية، تثبت، وبعدين تنمسح. وتكون مو منتظمة شوي عشان تبين مرسومة باليد.

**When to use:**
- EN: Use when you need a gold version of M-061.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-061.

#### `al-emp-061-boxed` — Circle Around · Boxed
**دائرة حول الكلمة · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.6s draw*

*Original: M-061*

Variant of M-061: النص داخل صندوق ملون

**Spec (EN):** A hand-drawn accent ellipse strokes around the word over 0.6s (animated stroke), holds, then erases. Slightly uneven so it feels hand-made.

**Spec (AR):** دائرة مرسومة باليد بلون الهوية تنرسم حول الكلمة خلال 0.6 ثانية، تثبت، وبعدين تنمسح. وتكون مو منتظمة شوي عشان تبين مرسومة باليد.

**When to use:**
- EN: Use when you need a boxed version of M-061.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-061.

#### `al-emp-062-fast` — Strike Through · Fast
**شطب الكلمة · سريع**

*accent · any · timeline · easing: easeInOutQuint · 0.5s*

*Original: M-062*

Variant of M-062: أسرع بـ 40%

**Spec (EN):** An accent line draws through the middle of the word from the reading-start side over 0.5s, holds, then retracts.

**Spec (AR):** خط بلون الهوية ينرسم بنص الكلمة من جهة بداية القراءة خلال 0.5 ثانية، يثبت، وبعدين ينسحب.

**When to use:**
- EN: Use when you need a fast version of M-062.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-062.

#### `al-emp-062-slow` — Strike Through · Slow
**شطب الكلمة · بطيء**

*accent · any · timeline · easing: easeInOutQuint · 0.5s*

*Original: M-062*

Variant of M-062: أبطأ بـ 60%

**Spec (EN):** An accent line draws through the middle of the word from the reading-start side over 0.5s, holds, then retracts.

**Spec (AR):** خط بلون الهوية ينرسم بنص الكلمة من جهة بداية القراءة خلال 0.5 ثانية، يثبت، وبعدين ينسحب.

**When to use:**
- EN: Use when you need a slow version of M-062.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-062.

#### `al-emp-062-gold` — Strike Through · Gold
**شطب الكلمة · ذهبي**

*accent · any · timeline · easing: easeInOutQuint · 0.5s*

*Original: M-062*

Variant of M-062: نسخة ذهبية فاخرة

**Spec (EN):** An accent line draws through the middle of the word from the reading-start side over 0.5s, holds, then retracts.

**Spec (AR):** خط بلون الهوية ينرسم بنص الكلمة من جهة بداية القراءة خلال 0.5 ثانية، يثبت، وبعدين ينسحب.

**When to use:**
- EN: Use when you need a gold version of M-062.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-062.

#### `al-emp-062-boxed` — Strike Through · Boxed
**شطب الكلمة · صندوق**

*accent · any · timeline · easing: easeInOutQuint · 0.5s*

*Original: M-062*

Variant of M-062: النص داخل صندوق ملون

**Spec (EN):** An accent line draws through the middle of the word from the reading-start side over 0.5s, holds, then retracts.

**Spec (AR):** خط بلون الهوية ينرسم بنص الكلمة من جهة بداية القراءة خلال 0.5 ثانية، يثبت، وبعدين ينسحب.

**When to use:**
- EN: Use when you need a boxed version of M-062.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-062.

#### `al-emp-063-fast` — Box Outline Draw · Fast
**مربع ينرسم حول الكلمة · سريع**

*accent · any · depth · easing: easeInOutCubic · 0.6s draw*

*Original: M-063*

Variant of M-063: أسرع بـ 40%

**Spec (EN):** A rounded accent rectangle strokes itself around the word, starting from the top-right corner, over 0.6s. Holds, then erases.

**Spec (AR):** مستطيل بزوايا دائرية بلون الهوية ينرسم حول الكلمة من الزاوية الفوق يمين خلال 0.6 ثانية. يثبت، وبعدين ينمسح.

**When to use:**
- EN: Use when you need a fast version of M-063.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-063.

#### `al-emp-063-slow` — Box Outline Draw · Slow
**مربع ينرسم حول الكلمة · بطيء**

*accent · any · depth · easing: easeInOutCubic · 0.6s draw*

*Original: M-063*

Variant of M-063: أبطأ بـ 60%

**Spec (EN):** A rounded accent rectangle strokes itself around the word, starting from the top-right corner, over 0.6s. Holds, then erases.

**Spec (AR):** مستطيل بزوايا دائرية بلون الهوية ينرسم حول الكلمة من الزاوية الفوق يمين خلال 0.6 ثانية. يثبت، وبعدين ينمسح.

**When to use:**
- EN: Use when you need a slow version of M-063.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-063.

#### `al-emp-063-gold` — Box Outline Draw · Gold
**مربع ينرسم حول الكلمة · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 0.6s draw*

*Original: M-063*

Variant of M-063: نسخة ذهبية فاخرة

**Spec (EN):** A rounded accent rectangle strokes itself around the word, starting from the top-right corner, over 0.6s. Holds, then erases.

**Spec (AR):** مستطيل بزوايا دائرية بلون الهوية ينرسم حول الكلمة من الزاوية الفوق يمين خلال 0.6 ثانية. يثبت، وبعدين ينمسح.

**When to use:**
- EN: Use when you need a gold version of M-063.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-063.

#### `al-emp-063-boxed` — Box Outline Draw · Boxed
**مربع ينرسم حول الكلمة · صندوق**

*accent · any · depth · easing: easeInOutCubic · 0.6s draw*

*Original: M-063*

Variant of M-063: النص داخل صندوق ملون

**Spec (EN):** A rounded accent rectangle strokes itself around the word, starting from the top-right corner, over 0.6s. Holds, then erases.

**Spec (AR):** مستطيل بزوايا دائرية بلون الهوية ينرسم حول الكلمة من الزاوية الفوق يمين خلال 0.6 ثانية. يثبت، وبعدين ينمسح.

**When to use:**
- EN: Use when you need a boxed version of M-063.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-063.

#### `al-emp-064-fast` — Color Pulse · Fast
**نبض لون · سريع**

*accent · calm · timeline · easing: easeInOutSine · loop · 1.6s*

*Original: M-064*

Variant of M-064: أسرع بـ 40%

**Spec (EN):** The word color eases from white to the accent color and back in a 1.6s loop while it is on screen.

**Spec (AR):** لون الكلمة يتحول بنعومة من الأبيض للون الهوية ويرجع كل 1.6 ثانية طول ما هي على الشاشة.

**When to use:**
- EN: Use when you need a fast version of M-064.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-064.

#### `al-emp-064-slow` — Color Pulse · Slow
**نبض لون · بطيء**

*accent · calm · timeline · easing: easeInOutSine · loop · 1.6s*

*Original: M-064*

Variant of M-064: أبطأ بـ 60%

**Spec (EN):** The word color eases from white to the accent color and back in a 1.6s loop while it is on screen.

**Spec (AR):** لون الكلمة يتحول بنعومة من الأبيض للون الهوية ويرجع كل 1.6 ثانية طول ما هي على الشاشة.

**When to use:**
- EN: Use when you need a slow version of M-064.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-064.

#### `al-emp-064-gold` — Color Pulse · Gold
**نبض لون · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · loop · 1.6s*

*Original: M-064*

Variant of M-064: نسخة ذهبية فاخرة

**Spec (EN):** The word color eases from white to the accent color and back in a 1.6s loop while it is on screen.

**Spec (AR):** لون الكلمة يتحول بنعومة من الأبيض للون الهوية ويرجع كل 1.6 ثانية طول ما هي على الشاشة.

**When to use:**
- EN: Use when you need a gold version of M-064.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-064.

#### `al-emp-064-boxed` — Color Pulse · Boxed
**نبض لون · صندوق**

*accent · calm · timeline · easing: easeInOutSine · loop · 1.6s*

*Original: M-064*

Variant of M-064: النص داخل صندوق ملون

**Spec (EN):** The word color eases from white to the accent color and back in a 1.6s loop while it is on screen.

**Spec (AR):** لون الكلمة يتحول بنعومة من الأبيض للون الهوية ويرجع كل 1.6 ثانية طول ما هي على الشاشة.

**When to use:**
- EN: Use when you need a boxed version of M-064.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-064.

#### `al-emp-065-fast` — Glow Pulse · Fast
**توهج نابض · سريع**

*accent · calm · timeline · easing: easeInOutSine · loop · 1.6s*

*Original: M-065*

Variant of M-065: أسرع بـ 40%

**Spec (EN):** An accent glow (text shadow, blur up to 6% of the width) grows and fades around the word in a 1.6s loop.

**Spec (AR):** توهج بلون الهوية (ظل للنص يوصل ضبابيته لـ 6% من العرض) يكبر ويخف حول الكلمة كل 1.6 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-065.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-065.

#### `al-emp-065-slow` — Glow Pulse · Slow
**توهج نابض · بطيء**

*accent · calm · timeline · easing: easeInOutSine · loop · 1.6s*

*Original: M-065*

Variant of M-065: أبطأ بـ 60%

**Spec (EN):** An accent glow (text shadow, blur up to 6% of the width) grows and fades around the word in a 1.6s loop.

**Spec (AR):** توهج بلون الهوية (ظل للنص يوصل ضبابيته لـ 6% من العرض) يكبر ويخف حول الكلمة كل 1.6 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-065.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-065.

#### `al-emp-065-gold` — Glow Pulse · Gold
**توهج نابض · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · loop · 1.6s*

*Original: M-065*

Variant of M-065: نسخة ذهبية فاخرة

**Spec (EN):** An accent glow (text shadow, blur up to 6% of the width) grows and fades around the word in a 1.6s loop.

**Spec (AR):** توهج بلون الهوية (ظل للنص يوصل ضبابيته لـ 6% من العرض) يكبر ويخف حول الكلمة كل 1.6 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-065.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-065.

#### `al-emp-065-boxed` — Glow Pulse · Boxed
**توهج نابض · صندوق**

*accent · calm · timeline · easing: easeInOutSine · loop · 1.6s*

*Original: M-065*

Variant of M-065: النص داخل صندوق ملون

**Spec (EN):** An accent glow (text shadow, blur up to 6% of the width) grows and fades around the word in a 1.6s loop.

**Spec (AR):** توهج بلون الهوية (ظل للنص يوصل ضبابيته لـ 6% من العرض) يكبر ويخف حول الكلمة كل 1.6 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-065.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-065.

#### `al-emp-066-fast` — Wiggle · Fast
**تمايل · سريع**

*accent · calm · depth · easing: easeInOutSine · 0.8s*

*Original: M-066*

Variant of M-066: أسرع بـ 40%

**Spec (EN):** The word rotates quickly ±8° and back several times with decreasing angle over about 0.8s, then rests.

**Spec (AR):** الكلمة تلف بسرعة ±8 درجات وترجع كم مرة والزاوية تقل خلال تقريباً 0.8 ثانية، وبعدين توقف.

**When to use:**
- EN: Use when you need a fast version of M-066.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-066.

#### `al-emp-066-slow` — Wiggle · Slow
**تمايل · بطيء**

*accent · calm · depth · easing: easeInOutSine · 0.8s*

*Original: M-066*

Variant of M-066: أبطأ بـ 60%

**Spec (EN):** The word rotates quickly ±8° and back several times with decreasing angle over about 0.8s, then rests.

**Spec (AR):** الكلمة تلف بسرعة ±8 درجات وترجع كم مرة والزاوية تقل خلال تقريباً 0.8 ثانية، وبعدين توقف.

**When to use:**
- EN: Use when you need a slow version of M-066.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-066.

#### `al-emp-066-gold` — Wiggle · Gold
**تمايل · ذهبي**

*accent · calm · depth · easing: easeInOutSine · 0.8s*

*Original: M-066*

Variant of M-066: نسخة ذهبية فاخرة

**Spec (EN):** The word rotates quickly ±8° and back several times with decreasing angle over about 0.8s, then rests.

**Spec (AR):** الكلمة تلف بسرعة ±8 درجات وترجع كم مرة والزاوية تقل خلال تقريباً 0.8 ثانية، وبعدين توقف.

**When to use:**
- EN: Use when you need a gold version of M-066.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-066.

#### `al-emp-066-boxed` — Wiggle · Boxed
**تمايل · صندوق**

*accent · calm · depth · easing: easeInOutSine · 0.8s*

*Original: M-066*

Variant of M-066: النص داخل صندوق ملون

**Spec (EN):** The word rotates quickly ±8° and back several times with decreasing angle over about 0.8s, then rests.

**Spec (AR):** الكلمة تلف بسرعة ±8 درجات وترجع كم مرة والزاوية تقل خلال تقريباً 0.8 ثانية، وبعدين توقف.

**When to use:**
- EN: Use when you need a boxed version of M-066.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-066.

#### `al-emp-067-fast` — Bounce Word · Fast
**الكلمة تنط · سريع**

*accent · calm · depth · easing: easeOutQuad · 0.6s*

*Original: M-067*

Variant of M-067: أسرع بـ 40%

**Spec (EN):** The word jumps up 35% of its height and lands, then a second smaller jump of 14%, over about 0.6s.

**Spec (AR):** الكلمة تنط لفوق 35% من طولها وتنزل، وبعدها نطة ثانية أصغر 14%، خلال تقريباً 0.6 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-067.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-067.

#### `al-emp-067-slow` — Bounce Word · Slow
**الكلمة تنط · بطيء**

*accent · calm · depth · easing: easeOutQuad · 0.6s*

*Original: M-067*

Variant of M-067: أبطأ بـ 60%

**Spec (EN):** The word jumps up 35% of its height and lands, then a second smaller jump of 14%, over about 0.6s.

**Spec (AR):** الكلمة تنط لفوق 35% من طولها وتنزل، وبعدها نطة ثانية أصغر 14%، خلال تقريباً 0.6 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-067.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-067.

#### `al-emp-067-gold` — Bounce Word · Gold
**الكلمة تنط · ذهبي**

*accent · calm · depth · easing: easeOutQuad · 0.6s*

*Original: M-067*

Variant of M-067: نسخة ذهبية فاخرة

**Spec (EN):** The word jumps up 35% of its height and lands, then a second smaller jump of 14%, over about 0.6s.

**Spec (AR):** الكلمة تنط لفوق 35% من طولها وتنزل، وبعدها نطة ثانية أصغر 14%، خلال تقريباً 0.6 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-067.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-067.

#### `al-emp-067-boxed` — Bounce Word · Boxed
**الكلمة تنط · صندوق**

*accent · calm · depth · easing: easeOutQuad · 0.6s*

*Original: M-067*

Variant of M-067: النص داخل صندوق ملون

**Spec (EN):** The word jumps up 35% of its height and lands, then a second smaller jump of 14%, over about 0.6s.

**Spec (AR):** الكلمة تنط لفوق 35% من طولها وتنزل، وبعدها نطة ثانية أصغر 14%، خلال تقريباً 0.6 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-067.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-067.

#### `al-emp-068-fast` — Arrow Point · Fast
**سهم يأشر · سريع**

*accent · calm · timeline · easing: easeInOutSine · loop · 1s*

*Original: M-068*

Variant of M-068: أسرع بـ 40%

**Spec (EN):** An accent arrow sits beside the target and nudges toward it by 30% of its length and back in a 1s loop.

**Spec (AR):** سهم بلون الهوية جنب الهدف، يتحرك ناحيته 30% من طوله ويرجع كل ثانية.

**When to use:**
- EN: Use when you need a fast version of M-068.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-068.

#### `al-emp-068-slow` — Arrow Point · Slow
**سهم يأشر · بطيء**

*accent · calm · timeline · easing: easeInOutSine · loop · 1s*

*Original: M-068*

Variant of M-068: أبطأ بـ 60%

**Spec (EN):** An accent arrow sits beside the target and nudges toward it by 30% of its length and back in a 1s loop.

**Spec (AR):** سهم بلون الهوية جنب الهدف، يتحرك ناحيته 30% من طوله ويرجع كل ثانية.

**When to use:**
- EN: Use when you need a slow version of M-068.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-068.

#### `al-emp-068-gold` — Arrow Point · Gold
**سهم يأشر · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · loop · 1s*

*Original: M-068*

Variant of M-068: نسخة ذهبية فاخرة

**Spec (EN):** An accent arrow sits beside the target and nudges toward it by 30% of its length and back in a 1s loop.

**Spec (AR):** سهم بلون الهوية جنب الهدف، يتحرك ناحيته 30% من طوله ويرجع كل ثانية.

**When to use:**
- EN: Use when you need a gold version of M-068.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-068.

#### `al-emp-068-boxed` — Arrow Point · Boxed
**سهم يأشر · صندوق**

*accent · calm · timeline · easing: easeInOutSine · loop · 1s*

*Original: M-068*

Variant of M-068: النص داخل صندوق ملون

**Spec (EN):** An accent arrow sits beside the target and nudges toward it by 30% of its length and back in a 1s loop.

**Spec (AR):** سهم بلون الهوية جنب الهدف، يتحرك ناحيته 30% من طوله ويرجع كل ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-068.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-068.

#### `al-emp-069-fast` — Zoom Blur Word · Fast
**زوم مع ضبابية للكلمة · سريع**

*accent · any · blur · easing: easeOutExpo · 0.3s*

*Original: M-069*

Variant of M-069: أسرع بـ 40%

**Spec (EN):** The word jumps to 160% with a 1.5% blur in 0.2s, then settles at 120% sharp over 0.3s. Return to 100% at the end.

**Spec (AR):** الكلمة تكبر لـ 160% مع ضبابية 1.5% خلال 0.2 ثانية، وبعدين تستقر على 120% واضحة خلال 0.3 ثانية. ترجع 100% بالنهاية.

**When to use:**
- EN: Use when you need a fast version of M-069.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-069.

#### `al-emp-069-slow` — Zoom Blur Word · Slow
**زوم مع ضبابية للكلمة · بطيء**

*accent · any · blur · easing: easeOutExpo · 0.3s*

*Original: M-069*

Variant of M-069: أبطأ بـ 60%

**Spec (EN):** The word jumps to 160% with a 1.5% blur in 0.2s, then settles at 120% sharp over 0.3s. Return to 100% at the end.

**Spec (AR):** الكلمة تكبر لـ 160% مع ضبابية 1.5% خلال 0.2 ثانية، وبعدين تستقر على 120% واضحة خلال 0.3 ثانية. ترجع 100% بالنهاية.

**When to use:**
- EN: Use when you need a slow version of M-069.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-069.

#### `al-emp-069-gold` — Zoom Blur Word · Gold
**زوم مع ضبابية للكلمة · ذهبي**

*accent · any · blur · easing: easeOutExpo · 0.3s*

*Original: M-069*

Variant of M-069: نسخة ذهبية فاخرة

**Spec (EN):** The word jumps to 160% with a 1.5% blur in 0.2s, then settles at 120% sharp over 0.3s. Return to 100% at the end.

**Spec (AR):** الكلمة تكبر لـ 160% مع ضبابية 1.5% خلال 0.2 ثانية، وبعدين تستقر على 120% واضحة خلال 0.3 ثانية. ترجع 100% بالنهاية.

**When to use:**
- EN: Use when you need a gold version of M-069.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-069.

#### `al-emp-069-boxed` — Zoom Blur Word · Boxed
**زوم مع ضبابية للكلمة · صندوق**

*accent · any · blur · easing: easeOutExpo · 0.3s*

*Original: M-069*

Variant of M-069: النص داخل صندوق ملون

**Spec (EN):** The word jumps to 160% with a 1.5% blur in 0.2s, then settles at 120% sharp over 0.3s. Return to 100% at the end.

**Spec (AR):** الكلمة تكبر لـ 160% مع ضبابية 1.5% خلال 0.2 ثانية، وبعدين تستقر على 120% واضحة خلال 0.3 ثانية. ترجع 100% بالنهاية.

**When to use:**
- EN: Use when you need a boxed version of M-069.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-069.

#### `al-emp-070-fast` — Rubber Band · Fast
**مطاطية · سريع**

*accent · any · timeline · easing: easeOut · 0.7s*

*Original: M-070*

Variant of M-070: أسرع بـ 40%

**Spec (EN):** The word scales to 125%×75%, then 75%×125%, then smaller swings until it settles at 100% over 0.7s.

**Spec (AR):** الكلمة تصير 125%×75%، وبعدين 75%×125%، وبعدين تذبذبات أصغر لين تستقر على 100% خلال 0.7 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-070.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-070.

#### `al-emp-070-slow` — Rubber Band · Slow
**مطاطية · بطيء**

*accent · any · timeline · easing: easeOut · 0.7s*

*Original: M-070*

Variant of M-070: أبطأ بـ 60%

**Spec (EN):** The word scales to 125%×75%, then 75%×125%, then smaller swings until it settles at 100% over 0.7s.

**Spec (AR):** الكلمة تصير 125%×75%، وبعدين 75%×125%، وبعدين تذبذبات أصغر لين تستقر على 100% خلال 0.7 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-070.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-070.

#### `al-emp-070-gold` — Rubber Band · Gold
**مطاطية · ذهبي**

*accent · any · timeline · easing: easeOut · 0.7s*

*Original: M-070*

Variant of M-070: نسخة ذهبية فاخرة

**Spec (EN):** The word scales to 125%×75%, then 75%×125%, then smaller swings until it settles at 100% over 0.7s.

**Spec (AR):** الكلمة تصير 125%×75%، وبعدين 75%×125%، وبعدين تذبذبات أصغر لين تستقر على 100% خلال 0.7 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-070.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-070.

#### `al-emp-070-boxed` — Rubber Band · Boxed
**مطاطية · صندوق**

*accent · any · timeline · easing: easeOut · 0.7s*

*Original: M-070*

Variant of M-070: النص داخل صندوق ملون

**Spec (EN):** The word scales to 125%×75%, then 75%×125%, then smaller swings until it settles at 100% over 0.7s.

**Spec (AR):** الكلمة تصير 125%×75%، وبعدين 75%×125%، وبعدين تذبذبات أصغر لين تستقر على 100% خلال 0.7 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-070.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-070.

#### `al-emp-071-fast` — Jello · Fast
**هلامي · سريع**

*accent · any · timeline · easing: easeOut · 0.9s*

*Original: M-071*

Variant of M-071: أسرع بـ 40%

**Spec (EN):** The word skews on both axes by -12°, then +6°, -3°, +1.5° and settles over 0.9s.

**Spec (AR):** الكلمة تميل على المحورين -12 درجة، وبعدين +6، و-3، و+1.5، وتستقر خلال 0.9 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-071.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-071.

#### `al-emp-071-slow` — Jello · Slow
**هلامي · بطيء**

*accent · any · timeline · easing: easeOut · 0.9s*

*Original: M-071*

Variant of M-071: أبطأ بـ 60%

**Spec (EN):** The word skews on both axes by -12°, then +6°, -3°, +1.5° and settles over 0.9s.

**Spec (AR):** الكلمة تميل على المحورين -12 درجة، وبعدين +6، و-3، و+1.5، وتستقر خلال 0.9 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-071.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-071.

#### `al-emp-071-gold` — Jello · Gold
**هلامي · ذهبي**

*accent · any · timeline · easing: easeOut · 0.9s*

*Original: M-071*

Variant of M-071: نسخة ذهبية فاخرة

**Spec (EN):** The word skews on both axes by -12°, then +6°, -3°, +1.5° and settles over 0.9s.

**Spec (AR):** الكلمة تميل على المحورين -12 درجة، وبعدين +6، و-3، و+1.5، وتستقر خلال 0.9 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-071.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-071.

#### `al-emp-071-boxed` — Jello · Boxed
**هلامي · صندوق**

*accent · any · timeline · easing: easeOut · 0.9s*

*Original: M-071*

Variant of M-071: النص داخل صندوق ملون

**Spec (EN):** The word skews on both axes by -12°, then +6°, -3°, +1.5° and settles over 0.9s.

**Spec (AR):** الكلمة تميل على المحورين -12 درجة، وبعدين +6، و-3، و+1.5، وتستقر خلال 0.9 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-071.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-071.

#### `al-emp-072-fast` — Heartbeat · Fast
**نبض قلب · سريع**

*accent · any · sound · easing: easeInOut · loop · 1.4s*

*Original: M-072*

Variant of M-072: أسرع بـ 40%

**Spec (EN):** Two quick pulses to 130% scale and back (like a heartbeat), then a pause, in a 1.4s loop.

**Spec (AR):** نبضتين سريعة لـ 130% وترجع (مثل دقة القلب)، وبعدين وقفة، كل 1.4 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-072.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-072.

#### `al-emp-072-slow` — Heartbeat · Slow
**نبض قلب · بطيء**

*accent · any · sound · easing: easeInOut · loop · 1.4s*

*Original: M-072*

Variant of M-072: أبطأ بـ 60%

**Spec (EN):** Two quick pulses to 130% scale and back (like a heartbeat), then a pause, in a 1.4s loop.

**Spec (AR):** نبضتين سريعة لـ 130% وترجع (مثل دقة القلب)، وبعدين وقفة، كل 1.4 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-072.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-072.

#### `al-emp-072-gold` — Heartbeat · Gold
**نبض قلب · ذهبي**

*accent · any · sound · easing: easeInOut · loop · 1.4s*

*Original: M-072*

Variant of M-072: نسخة ذهبية فاخرة

**Spec (EN):** Two quick pulses to 130% scale and back (like a heartbeat), then a pause, in a 1.4s loop.

**Spec (AR):** نبضتين سريعة لـ 130% وترجع (مثل دقة القلب)، وبعدين وقفة، كل 1.4 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-072.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-072.

#### `al-emp-072-boxed` — Heartbeat · Boxed
**نبض قلب · صندوق**

*accent · any · sound · easing: easeInOut · loop · 1.4s*

*Original: M-072*

Variant of M-072: النص داخل صندوق ملون

**Spec (EN):** Two quick pulses to 130% scale and back (like a heartbeat), then a pause, in a 1.4s loop.

**Spec (AR):** نبضتين سريعة لـ 130% وترجع (مثل دقة القلب)، وبعدين وقفة، كل 1.4 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-072.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-072.

#### `al-emp-073-fast` — Marker Scribble · Fast
**خربشة تحت الكلمة · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.6s draw*

*Original: M-073*

Variant of M-073: أسرع بـ 40%

**Spec (EN):** A loose zigzag accent stroke draws under the word from the reading-start side over 0.6s, holds, then erases.

**Spec (AR):** خط متعرج حر بلون الهوية ينرسم تحت الكلمة من جهة بداية القراءة خلال 0.6 ثانية، يثبت، وبعدين ينمسح.

**When to use:**
- EN: Use when you need a fast version of M-073.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-073.

#### `al-emp-073-slow` — Marker Scribble · Slow
**خربشة تحت الكلمة · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.6s draw*

*Original: M-073*

Variant of M-073: أبطأ بـ 60%

**Spec (EN):** A loose zigzag accent stroke draws under the word from the reading-start side over 0.6s, holds, then erases.

**Spec (AR):** خط متعرج حر بلون الهوية ينرسم تحت الكلمة من جهة بداية القراءة خلال 0.6 ثانية، يثبت، وبعدين ينمسح.

**When to use:**
- EN: Use when you need a slow version of M-073.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-073.

#### `al-emp-073-gold` — Marker Scribble · Gold
**خربشة تحت الكلمة · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.6s draw*

*Original: M-073*

Variant of M-073: نسخة ذهبية فاخرة

**Spec (EN):** A loose zigzag accent stroke draws under the word from the reading-start side over 0.6s, holds, then erases.

**Spec (AR):** خط متعرج حر بلون الهوية ينرسم تحت الكلمة من جهة بداية القراءة خلال 0.6 ثانية، يثبت، وبعدين ينمسح.

**When to use:**
- EN: Use when you need a gold version of M-073.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-073.

#### `al-emp-073-boxed` — Marker Scribble · Boxed
**خربشة تحت الكلمة · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.6s draw*

*Original: M-073*

Variant of M-073: النص داخل صندوق ملون

**Spec (EN):** A loose zigzag accent stroke draws under the word from the reading-start side over 0.6s, holds, then erases.

**Spec (AR):** خط متعرج حر بلون الهوية ينرسم تحت الكلمة من جهة بداية القراءة خلال 0.6 ثانية، يثبت، وبعدين ينمسح.

**When to use:**
- EN: Use when you need a boxed version of M-073.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-073.

#### `al-emp-074-fast` — Spotlight Dim · Fast
**تعتيم ما حول الكلمة · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.5s in*

*Original: M-074*

Variant of M-074: أسرع بـ 40%

**Spec (EN):** A dark overlay (about 80% black) fades in over 0.5s with a soft circular hole around the subject, so only the subject stays lit. Fade out to release.

**Spec (AR):** طبقة غامقة (تقريباً 80% أسود) تظهر خلال 0.5 ثانية وفيها فتحة دائرية ناعمة حول الهدف، فيبقى الهدف بس مضيء. وتختفي بتلاشي.

**When to use:**
- EN: Use when you need a fast version of M-074.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-074.

#### `al-emp-074-slow` — Spotlight Dim · Slow
**تعتيم ما حول الكلمة · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.5s in*

*Original: M-074*

Variant of M-074: أبطأ بـ 60%

**Spec (EN):** A dark overlay (about 80% black) fades in over 0.5s with a soft circular hole around the subject, so only the subject stays lit. Fade out to release.

**Spec (AR):** طبقة غامقة (تقريباً 80% أسود) تظهر خلال 0.5 ثانية وفيها فتحة دائرية ناعمة حول الهدف، فيبقى الهدف بس مضيء. وتختفي بتلاشي.

**When to use:**
- EN: Use when you need a slow version of M-074.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-074.

#### `al-emp-074-gold` — Spotlight Dim · Gold
**تعتيم ما حول الكلمة · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.5s in*

*Original: M-074*

Variant of M-074: نسخة ذهبية فاخرة

**Spec (EN):** A dark overlay (about 80% black) fades in over 0.5s with a soft circular hole around the subject, so only the subject stays lit. Fade out to release.

**Spec (AR):** طبقة غامقة (تقريباً 80% أسود) تظهر خلال 0.5 ثانية وفيها فتحة دائرية ناعمة حول الهدف، فيبقى الهدف بس مضيء. وتختفي بتلاشي.

**When to use:**
- EN: Use when you need a gold version of M-074.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-074.

#### `al-emp-074-boxed` — Spotlight Dim · Boxed
**تعتيم ما حول الكلمة · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.5s in*

*Original: M-074*

Variant of M-074: النص داخل صندوق ملون

**Spec (EN):** A dark overlay (about 80% black) fades in over 0.5s with a soft circular hole around the subject, so only the subject stays lit. Fade out to release.

**Spec (AR):** طبقة غامقة (تقريباً 80% أسود) تظهر خلال 0.5 ثانية وفيها فتحة دائرية ناعمة حول الهدف، فيبقى الهدف بس مضيء. وتختفي بتلاشي.

**When to use:**
- EN: Use when you need a boxed version of M-074.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-074.

#### `al-emp-075-fast` — Letter Spacing · Fast
**تباعد الحروف · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-075*

Variant of M-075: أسرع بـ 40%

**Spec (EN):** The letter spacing grows smoothly from 0 to 0.35em over 0.8s while the word stays centered. Reverse at exit.

**Spec (AR):** المسافة بين الحروف تكبر بنعومة من 0 لـ 0.35em خلال 0.8 ثانية والكلمة تبقى بالنص. وبالخروج ترجع.

**When to use:**
- EN: Use when you need a fast version of M-075.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-075.

#### `al-emp-075-slow` — Letter Spacing · Slow
**تباعد الحروف · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-075*

Variant of M-075: أبطأ بـ 60%

**Spec (EN):** The letter spacing grows smoothly from 0 to 0.35em over 0.8s while the word stays centered. Reverse at exit.

**Spec (AR):** المسافة بين الحروف تكبر بنعومة من 0 لـ 0.35em خلال 0.8 ثانية والكلمة تبقى بالنص. وبالخروج ترجع.

**When to use:**
- EN: Use when you need a slow version of M-075.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-075.

#### `al-emp-075-gold` — Letter Spacing · Gold
**تباعد الحروف · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-075*

Variant of M-075: نسخة ذهبية فاخرة

**Spec (EN):** The letter spacing grows smoothly from 0 to 0.35em over 0.8s while the word stays centered. Reverse at exit.

**Spec (AR):** المسافة بين الحروف تكبر بنعومة من 0 لـ 0.35em خلال 0.8 ثانية والكلمة تبقى بالنص. وبالخروج ترجع.

**When to use:**
- EN: Use when you need a gold version of M-075.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-075.

#### `al-emp-075-boxed` — Letter Spacing · Boxed
**تباعد الحروف · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-075*

Variant of M-075: النص داخل صندوق ملون

**Spec (EN):** The letter spacing grows smoothly from 0 to 0.35em over 0.8s while the word stays centered. Reverse at exit.

**Spec (AR):** المسافة بين الحروف تكبر بنعومة من 0 لـ 0.35em خلال 0.8 ثانية والكلمة تبقى بالنص. وبالخروج ترجع.

**When to use:**
- EN: Use when you need a boxed version of M-075.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-075.

#### `al-emp-076-fast` — Flash Hit · Fast
**وميض أبيض · سريع**

*accent · any · blur · easing: easeOut · 0.15s*

*Original: M-076*

Variant of M-076: أسرع بـ 40%

**Spec (EN):** A full-screen white flash rises to 90% opacity in 1–2 frames and fades out over 0.15s, exactly on the beat or word.

**Spec (AR):** وميض أبيض يغطي الشاشة يوصل 90% شفافية خلال فريم أو فريمين ويختفي خلال 0.15 ثانية، بالضبط على الإيقاع أو الكلمة.

**When to use:**
- EN: Use when you need a fast version of M-076.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-076.

#### `al-emp-076-slow` — Flash Hit · Slow
**وميض أبيض · بطيء**

*accent · any · blur · easing: easeOut · 0.15s*

*Original: M-076*

Variant of M-076: أبطأ بـ 60%

**Spec (EN):** A full-screen white flash rises to 90% opacity in 1–2 frames and fades out over 0.15s, exactly on the beat or word.

**Spec (AR):** وميض أبيض يغطي الشاشة يوصل 90% شفافية خلال فريم أو فريمين ويختفي خلال 0.15 ثانية، بالضبط على الإيقاع أو الكلمة.

**When to use:**
- EN: Use when you need a slow version of M-076.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-076.

#### `al-emp-076-gold` — Flash Hit · Gold
**وميض أبيض · ذهبي**

*accent · any · blur · easing: easeOut · 0.15s*

*Original: M-076*

Variant of M-076: نسخة ذهبية فاخرة

**Spec (EN):** A full-screen white flash rises to 90% opacity in 1–2 frames and fades out over 0.15s, exactly on the beat or word.

**Spec (AR):** وميض أبيض يغطي الشاشة يوصل 90% شفافية خلال فريم أو فريمين ويختفي خلال 0.15 ثانية، بالضبط على الإيقاع أو الكلمة.

**When to use:**
- EN: Use when you need a gold version of M-076.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-076.

#### `al-emp-076-boxed` — Flash Hit · Boxed
**وميض أبيض · صندوق**

*accent · any · blur · easing: easeOut · 0.15s*

*Original: M-076*

Variant of M-076: النص داخل صندوق ملون

**Spec (EN):** A full-screen white flash rises to 90% opacity in 1–2 frames and fades out over 0.15s, exactly on the beat or word.

**Spec (AR):** وميض أبيض يغطي الشاشة يوصل 90% شفافية خلال فريم أو فريمين ويختفي خلال 0.15 ثانية، بالضبط على الإيقاع أو الكلمة.

**When to use:**
- EN: Use when you need a boxed version of M-076.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-076.

#### `al-emp-077-fast` — Sparkle Stars · Fast
**نجوم تلمع · سريع**

*accent · calm · depth · easing: easeInOutSine · loop · 1.2s*

*Original: M-077*

Variant of M-077: أسرع بـ 40%

**Spec (EN):** Three to five small four-point stars pop in around the word at random spots, scale 0 to 100% while rotating 90°, then shrink away, staggered by 0.3s.

**Spec (AR):** من 3 إلى 5 نجوم صغيرة بأربع رؤوس تطلع حول الكلمة بأماكن عشوائية، تكبر من 0 لـ 100% وهي تلف 90 درجة، وبعدين تصغر وتختفي، وبينهم 0.3 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-077.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-077.

#### `al-emp-077-slow` — Sparkle Stars · Slow
**نجوم تلمع · بطيء**

*accent · calm · depth · easing: easeInOutSine · loop · 1.2s*

*Original: M-077*

Variant of M-077: أبطأ بـ 60%

**Spec (EN):** Three to five small four-point stars pop in around the word at random spots, scale 0 to 100% while rotating 90°, then shrink away, staggered by 0.3s.

**Spec (AR):** من 3 إلى 5 نجوم صغيرة بأربع رؤوس تطلع حول الكلمة بأماكن عشوائية، تكبر من 0 لـ 100% وهي تلف 90 درجة، وبعدين تصغر وتختفي، وبينهم 0.3 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-077.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-077.

#### `al-emp-077-gold` — Sparkle Stars · Gold
**نجوم تلمع · ذهبي**

*accent · calm · depth · easing: easeInOutSine · loop · 1.2s*

*Original: M-077*

Variant of M-077: نسخة ذهبية فاخرة

**Spec (EN):** Three to five small four-point stars pop in around the word at random spots, scale 0 to 100% while rotating 90°, then shrink away, staggered by 0.3s.

**Spec (AR):** من 3 إلى 5 نجوم صغيرة بأربع رؤوس تطلع حول الكلمة بأماكن عشوائية، تكبر من 0 لـ 100% وهي تلف 90 درجة، وبعدين تصغر وتختفي، وبينهم 0.3 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-077.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-077.

#### `al-emp-077-boxed` — Sparkle Stars · Boxed
**نجوم تلمع · صندوق**

*accent · calm · depth · easing: easeInOutSine · loop · 1.2s*

*Original: M-077*

Variant of M-077: النص داخل صندوق ملون

**Spec (EN):** Three to five small four-point stars pop in around the word at random spots, scale 0 to 100% while rotating 90°, then shrink away, staggered by 0.3s.

**Spec (AR):** من 3 إلى 5 نجوم صغيرة بأربع رؤوس تطلع حول الكلمة بأماكن عشوائية، تكبر من 0 لـ 100% وهي تلف 90 درجة، وبعدين تصغر وتختفي، وبينهم 0.3 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-077.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-077.

#### `al-emp-078-fast` — Swing · Fast
**تأرجح · سريع**

*accent · any · depth · easing: easeOut · 1s*

*Original: M-078*

Variant of M-078: أسرع بـ 40%

**Spec (EN):** The word swings from its top edge: +16°, -11°, +7°, -4°, +2° and settles over about 1s.

**Spec (AR):** الكلمة تتأرجح من حافتها الفوق: +16، -11، +7، -4، +2 درجة وتستقر خلال تقريباً ثانية.

**When to use:**
- EN: Use when you need a fast version of M-078.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-078.

#### `al-emp-078-slow` — Swing · Slow
**تأرجح · بطيء**

*accent · any · depth · easing: easeOut · 1s*

*Original: M-078*

Variant of M-078: أبطأ بـ 60%

**Spec (EN):** The word swings from its top edge: +16°, -11°, +7°, -4°, +2° and settles over about 1s.

**Spec (AR):** الكلمة تتأرجح من حافتها الفوق: +16، -11، +7، -4، +2 درجة وتستقر خلال تقريباً ثانية.

**When to use:**
- EN: Use when you need a slow version of M-078.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-078.

#### `al-emp-078-gold` — Swing · Gold
**تأرجح · ذهبي**

*accent · any · depth · easing: easeOut · 1s*

*Original: M-078*

Variant of M-078: نسخة ذهبية فاخرة

**Spec (EN):** The word swings from its top edge: +16°, -11°, +7°, -4°, +2° and settles over about 1s.

**Spec (AR):** الكلمة تتأرجح من حافتها الفوق: +16، -11، +7، -4، +2 درجة وتستقر خلال تقريباً ثانية.

**When to use:**
- EN: Use when you need a gold version of M-078.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-078.

#### `al-emp-078-boxed` — Swing · Boxed
**تأرجح · صندوق**

*accent · any · depth · easing: easeOut · 1s*

*Original: M-078*

Variant of M-078: النص داخل صندوق ملون

**Spec (EN):** The word swings from its top edge: +16°, -11°, +7°, -4°, +2° and settles over about 1s.

**Spec (AR):** الكلمة تتأرجح من حافتها الفوق: +16، -11، +7، -4، +2 درجة وتستقر خلال تقريباً ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-078.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-078.

#### `al-emp-079-fast` — Tilt Pop · Fast
**ميلان مع تكبير · سريع**

*accent · any · timeline · easing: easeOutBack · 0.3s*

*Original: M-079*

Variant of M-079: أسرع بـ 40%

**Spec (EN):** The word scales to 130% while rotating -8° in 0.3s, settles at 120% and -5°, holds, then returns.

**Spec (AR):** الكلمة تكبر لـ 130% وهي تميل -8 درجات خلال 0.3 ثانية، تستقر على 120% و-5 درجات، تثبت، وبعدين ترجع.

**When to use:**
- EN: Use when you need a fast version of M-079.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-079.

#### `al-emp-079-slow` — Tilt Pop · Slow
**ميلان مع تكبير · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.3s*

*Original: M-079*

Variant of M-079: أبطأ بـ 60%

**Spec (EN):** The word scales to 130% while rotating -8° in 0.3s, settles at 120% and -5°, holds, then returns.

**Spec (AR):** الكلمة تكبر لـ 130% وهي تميل -8 درجات خلال 0.3 ثانية، تستقر على 120% و-5 درجات، تثبت، وبعدين ترجع.

**When to use:**
- EN: Use when you need a slow version of M-079.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-079.

#### `al-emp-079-gold` — Tilt Pop · Gold
**ميلان مع تكبير · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.3s*

*Original: M-079*

Variant of M-079: نسخة ذهبية فاخرة

**Spec (EN):** The word scales to 130% while rotating -8° in 0.3s, settles at 120% and -5°, holds, then returns.

**Spec (AR):** الكلمة تكبر لـ 130% وهي تميل -8 درجات خلال 0.3 ثانية، تستقر على 120% و-5 درجات، تثبت، وبعدين ترجع.

**When to use:**
- EN: Use when you need a gold version of M-079.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-079.

#### `al-emp-079-boxed` — Tilt Pop · Boxed
**ميلان مع تكبير · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.3s*

*Original: M-079*

Variant of M-079: النص داخل صندوق ملون

**Spec (EN):** The word scales to 130% while rotating -8° in 0.3s, settles at 120% and -5°, holds, then returns.

**Spec (AR):** الكلمة تكبر لـ 130% وهي تميل -8 درجات خلال 0.3 ثانية، تستقر على 120% و-5 درجات، تثبت، وبعدين ترجع.

**When to use:**
- EN: Use when you need a boxed version of M-079.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-079.

#### `al-emp-080-fast` — Chromatic Split · Fast
**انقسام الألوان · سريع**

*accent · any · timeline · easing: easeOut · 0.5s*

*Original: M-080*

Variant of M-080: أسرع بـ 40%

**Spec (EN):** Red and cyan copies of the word slide out sideways by 1.5% of the width and back in over 0.5s, like an RGB lens split.

**Spec (AR):** نسخة حمرا ونسخة سماوية من الكلمة يطلعون على الجنبين بمسافة 1.5% من العرض ويرجعون خلال 0.5 ثانية، مثل انقسام ألوان العدسة.

**When to use:**
- EN: Use when you need a fast version of M-080.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-080.

#### `al-emp-080-slow` — Chromatic Split · Slow
**انقسام الألوان · بطيء**

*accent · any · timeline · easing: easeOut · 0.5s*

*Original: M-080*

Variant of M-080: أبطأ بـ 60%

**Spec (EN):** Red and cyan copies of the word slide out sideways by 1.5% of the width and back in over 0.5s, like an RGB lens split.

**Spec (AR):** نسخة حمرا ونسخة سماوية من الكلمة يطلعون على الجنبين بمسافة 1.5% من العرض ويرجعون خلال 0.5 ثانية، مثل انقسام ألوان العدسة.

**When to use:**
- EN: Use when you need a slow version of M-080.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-080.

#### `al-emp-080-gold` — Chromatic Split · Gold
**انقسام الألوان · ذهبي**

*accent · any · timeline · easing: easeOut · 0.5s*

*Original: M-080*

Variant of M-080: نسخة ذهبية فاخرة

**Spec (EN):** Red and cyan copies of the word slide out sideways by 1.5% of the width and back in over 0.5s, like an RGB lens split.

**Spec (AR):** نسخة حمرا ونسخة سماوية من الكلمة يطلعون على الجنبين بمسافة 1.5% من العرض ويرجعون خلال 0.5 ثانية، مثل انقسام ألوان العدسة.

**When to use:**
- EN: Use when you need a gold version of M-080.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-080.

#### `al-emp-080-boxed` — Chromatic Split · Boxed
**انقسام الألوان · صندوق**

*accent · any · timeline · easing: easeOut · 0.5s*

*Original: M-080*

Variant of M-080: النص داخل صندوق ملون

**Spec (EN):** Red and cyan copies of the word slide out sideways by 1.5% of the width and back in over 0.5s, like an RGB lens split.

**Spec (AR):** نسخة حمرا ونسخة سماوية من الكلمة يطلعون على الجنبين بمسافة 1.5% من العرض ويرجعون خلال 0.5 ثانية، مثل انقسام ألوان العدسة.

**When to use:**
- EN: Use when you need a boxed version of M-080.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-080.

### Captions (الكابشن) — 145 motions

#### `al-cap-011` — Karaoke Highlight
**كابشن كاريوكي**

*workhorse · any · blur · easing: instant (0.08s fade) · synced to each word*

*Original: M-011*

The main Reels caption: each word lights up as it is spoken.

**Spec (EN):** A full caption line is shown in dimmed white (50% opacity). Each word turns accent color exactly at its spoken timestamp (word-level ASR timings) and stays colored. Bold display font about 64px at 1080 wide, centered, inside the safe zone (y 1350–1550).

**Spec (AR):** سطر الكابشن كامل يطلع بأبيض باهت (شفافية 50%). كل كلمة تتلون بلون الهوية بالضبط وقت نطقها (من توقيتات التفريغ كلمة كلمة) وتبقى ملونة. خط عريض تقريباً 64px على عرض 1080، بالنص وداخل المنطقة الآمنة (y من 1350 لين 1550).

**When to use:**
- EN: The main Reels caption: each word lights up as it is spoken.
- AR: الكابشن الأساسي للريلز: الكلمة تتلون وقت ما تنقال.

#### `al-cap-012` — Word Pop
**كلمات تنط**

*workhorse · high · timeline · easing: easeOutBack · 0.18s per word*

*Original: M-012*

A fast, lively caption, word by word.

**Spec (EN):** Each word appears at its spoken timestamp, scaling from 30% to 118% and settling to 100% in 0.18s. Earlier words stay. Clear the line when the sentence ends.

**Spec (AR):** كل كلمة تطلع وقت نطقها، تكبر من 30% لـ 118% وتستقر على 100% خلال 0.18 ثانية. الكلمات اللي قبلها تبقى. امسح السطر لمن تخلص الجملة.

**When to use:**
- EN: A fast, lively caption, word by word.
- AR: كابشن سريع وحيوي، كلمة كلمة.

#### `al-cap-013` — Bounce Caption
**كابشن بارتداد**

*workhorse · any · timeline · easing: spring · 0.55s in*

*Original: M-013*

A whole line drops in at once with a playful move.

**Spec (EN):** The whole caption line enters from 130% below with a spring: overshoot to -14%, rebound to +6%, settle at 0 over about 0.55s. Fade out on exit.

**Spec (AR):** سطر الكابشن كامل يدخل من تحت بـ 130% بحركة نابض: يتعدى لـ -14%، يرتد لـ +6%، ويستقر على 0 خلال تقريباً 0.55 ثانية. ويختفي بتلاشي.

**When to use:**
- EN: A whole line drops in at once with a playful move.
- AR: جملة كاملة تدخل مرة وحدة بحركة مرحة.

#### `al-cap-014` — Boxed Word
**مربع ينقل على الكلمات**

*workhorse · any · depth · easing: easeOutCubic 0.1s · synced to each word*

*Original: M-014*

TikTok-style caption where the box follows your voice.

**Spec (EN):** A rounded accent box sits behind the currently spoken word only, and the word turns dark. When the next word starts, the box jumps to it, with a 6% scale pop. Other words stay white.

**Spec (AR):** مربع بلون الهوية بزوايا دائرية يكون ورا الكلمة اللي تنقال الحين بس، والكلمة تصير غامقة. لمن تبدأ الكلمة اللي بعدها، المربع ينط لها مع تكبير خفيف 6%. باقي الكلمات تبقى بيضا.

**When to use:**
- EN: TikTok-style caption where the box follows your voice.
- AR: كابشن بستايل تيك توك، المربع يمشي مع كلامك.

#### `al-cap-015` — One-Word Caption
**كلمة وحدة كبيرة**

*workhorse · high · depth · easing: easeOutBack · one word at a time*

*Original: M-015*

Fast, punchy talk: one big word in the middle.

**Spec (EN):** Only the current word is on screen, large (about 110px), centered. Each new word replaces the previous one with a quick scale from 60% to 110% to 100% over 0.15s. Optionally color key words in the accent.

**Spec (AR):** كلمة وحدة بس على الشاشة، كبيرة (تقريباً 110px) وبالنص. كل كلمة جديدة تحل محل اللي قبلها بتكبير سريع من 60% لـ 110% لـ 100% خلال 0.15 ثانية. وتقدر تلوّن الكلمات المهمة بلون الهوية.

**When to use:**
- EN: Fast, punchy talk: one big word in the middle.
- AR: كلام سريع ومثير، كلمة وحدة بالنص.

#### `al-cap-081` — Two-Line Caption
**كابشن بسطرين**

*workhorse · any · depth · easing: easeOutCubic · 0.45s per line · 0.4s stagger*

*Original: M-081*

A long sentence split into two lines that appear in turn.

**Spec (EN):** Split the sentence into two balanced lines. Each line rises 40px and fades in over 0.45s, the second starting 0.4s after the first. Keep both inside the safe zone.

**Spec (AR):** قسّم الجملة سطرين متوازنين. كل سطر يطلع لفوق 40px ويظهر خلال 0.45 ثانية، والثاني يبدأ بعد الأول بـ 0.4 ثانية. وخل السطرين داخل المنطقة الآمنة.

**When to use:**
- EN: A long sentence split into two lines that appear in turn.
- AR: جملة طويلة تنقسم سطرين يطلعون ورا بعض.

#### `al-cap-082` — Typewriter Caption
**كابشن آلة كاتبة**

*workhorse · any · timeline · easing: steps · synced to speech*

*Original: M-082*

A caption that types itself out with your voice.

**Spec (EN):** The caption reveals character by character from the reading-start side, paced so it finishes when the sentence ends. No caret.

**Spec (AR):** الكابشن ينكشف حرف حرف من جهة بداية القراءة، وسرعته بحيث يخلص لمن تخلص الجملة. بدون مؤشر كتابة.

**When to use:**
- EN: A caption that types itself out with your voice.
- AR: كابشن ينكتب حرف حرف مع صوتك.

#### `al-cap-083` — Fade Words
**كلمات تظهر بتلاشي**

*workhorse · any · timeline · easing: easeOutQuad · 0.25s per word*

*Original: M-083*

A calm caption, each word fades in.

**Spec (EN):** Each word fades from 0 to 100% opacity over 0.25s at its spoken timestamp. Earlier words stay. Clear the line at the end of the sentence.

**Spec (AR):** كل كلمة تظهر من 0 لـ 100% خلال 0.25 ثانية وقت نطقها. الكلمات اللي قبلها تبقى. وامسح السطر لمن تخلص الجملة.

**When to use:**
- EN: A calm caption, each word fades in.
- AR: كابشن هادي، كل كلمة تظهر بنعومة.

#### `al-cap-084` — Slide-Up Words
**كلمات تطلع من تحت**

*workhorse · any · timeline · easing: easeOutCubic · 0.25s per word*

*Original: M-084*

A lively caption, each word slides up.

**Spec (EN):** Each word slides up from 60% below its line while fading in over 0.25s at its spoken timestamp.

**Spec (AR):** كل كلمة تطلع من تحت سطرها بـ 60% وهي تظهر خلال 0.25 ثانية وقت نطقها.

**When to use:**
- EN: A lively caption, each word slides up.
- AR: كابشن حيوي، كل كلمة تطلع من تحت.

#### `al-cap-085` — Underline Active Word
**خط تحت الكلمة الحالية**

*workhorse · any · timeline · easing: easeOutCubic 0.1s · synced to each word*

*Original: M-085*

A full caption with an underline that follows the spoken word.

**Spec (EN):** The whole line is visible in white. A rounded accent bar sits under the word being spoken and jumps to the next word at its timestamp.

**Spec (AR):** السطر كامل يطلع أبيض. خط بلون الهوية بزوايا دائرية يكون تحت الكلمة اللي تنقال، وينط للكلمة اللي بعدها وقت نطقها.

**When to use:**
- EN: A full caption with an underline that follows the spoken word.
- AR: كابشن كامل وخط يمشي تحت الكلمة اللي تنقال.

#### `al-cap-086` — Scale Active Word
**الكلمة الحالية أكبر**

*workhorse · high · timeline · easing: easeOutBack 0.12s · synced to each word*

*Original: M-086*

The spoken word grows and turns accent.

**Spec (EN):** The word being spoken scales to 125% and turns the accent color; it returns to normal when the next word starts.

**Spec (AR):** الكلمة اللي تنقال تكبر لـ 125% وتصير بلون الهوية، وترجع طبيعية لمن تبدأ الكلمة اللي بعدها.

**When to use:**
- EN: The spoken word grows and turns accent.
- AR: الكلمة اللي تنقال تكبر وتتلون.

#### `al-cap-087` — Color Sweep Line
**لون يمسح السطر**

*workhorse · calm · timeline · easing: linear · sentence length*

*Original: M-087*

A color fill sweeps along the whole line as you speak.

**Spec (EN):** A two-color gradient is clipped to the caption text and slides from the reading-start side to the end over the sentence duration, so spoken parts turn accent.

**Spec (AR):** تدرج بلونين داخل حروف الكابشن، يتحرك من جهة بداية القراءة لآخر السطر على طول مدة الجملة، فالجزء اللي انقال يصير بلون الهوية.

**When to use:**
- EN: A color fill sweeps along the whole line as you speak.
- AR: لون يمشي على السطر كامل مع الكلام.

#### `al-cap-088` — Keyword Color
**كلمة مفتاحية بلون**

*workhorse · high · timeline · easing: easeOutBack · 0.2s*

*Original: M-088*

A plain caption where only the key word lights up.

**Spec (EN):** The caption stays white. Only the key word turns accent and scales to 112% at its timestamp, and stays like that until the line clears.

**Spec (AR):** الكابشن يبقى أبيض. الكلمة المهمة بس تصير بلون الهوية وتكبر لـ 112% وقت نطقها، وتبقى كذا لين يختفي السطر.

**When to use:**
- EN: A plain caption where only the key word lights up.
- AR: كابشن عادي والكلمة المهمة بس تتلون وتكبر.

#### `al-cap-089` — Pill Caption
**كابشن داخل كبسولة**

*workhorse · high · blur · easing: easeOutBack · 0.3s in*

*Original: M-089*

A caption inside a dark pill, readable on any footage.

**Spec (EN):** The caption sits inside a dark rounded pill (85% opacity, generous padding). The pill pops from 60% to 105% to 100% over 0.3s.

**Spec (AR):** الكابشن داخل كبسولة غامقة بزوايا دائرية (شفافية 85% ومسافات داخلية كافية). الكبسولة تنط من 60% لـ 105% لـ 100% خلال 0.3 ثانية.

**When to use:**
- EN: A caption inside a dark pill, readable on any footage.
- AR: كابشن داخل خلفية غامقة، يقرا على أي فيديو.

#### `al-cap-090` — Outline Caption
**كابشن بحدود سودا**

*workhorse · any · timeline · easing: easeOutCubic · 0.45s in*

*Original: M-090*

White caption with a thick black outline, classic and clear.

**Spec (EN):** White bold caption with a black outline about 7% of the font size (stroke painted under the fill), no shadow. Enters with a fade-up.

**Spec (AR):** كابشن أبيض عريض بحدود سودا سماكتها تقريباً 7% من حجم الخط (الحدود تحت التعبئة)، بدون ظل. ويدخل بظهور من تحت.

**When to use:**
- EN: White caption with a thick black outline, classic and clear.
- AR: كابشن أبيض بحدود سودا عريضة، كلاسيكي وواضح.

#### `al-cap-091` — Shadow Pop
**ظل صلب**

*workhorse · high · depth · easing: easeOutBack · 0.3s*

*Original: M-091*

A caption with a solid colored drop shadow that pops, pop-art style.

**Spec (EN):** A solid accent shadow (no blur) grows to 1.2% offset down-right while the text moves 1% up-left, so it looks lifted. Reverse at exit.

**Spec (AR):** ظل صلب بلون الهوية (بدون ضبابية) يبعد 1.2% لتحت يمين والنص يتحرك 1% لفوق يسار، فيبين كأنه مرفوع. وبالخروج يرجع.

**When to use:**
- EN: A caption with a solid colored drop shadow that pops, pop-art style.
- AR: كابشن بظل صلب ملون ينط، ستايل البوب.

#### `al-cap-092` — Blur Words
**كلمات من ضبابية**

*workhorse · any · blur · easing: easeOutQuad · 0.3s per word*

*Original: M-092*

A soft cinematic caption, words resolve from blur.

**Spec (EN):** Each word goes from 2% blur and opacity 0 to sharp and visible over 0.3s at its spoken timestamp.

**Spec (AR):** كل كلمة تتحول من ضبابية 2% وشفافية 0 لواضحة وظاهرة خلال 0.3 ثانية وقت نطقها.

**When to use:**
- EN: A soft cinematic caption, words resolve from blur.
- AR: كابشن ناعم وسينمائي، الكلمات تطلع من ضباب.

#### `al-cap-093` — Drop Words
**كلمات تطيح**

*workhorse · high · timeline · easing: easeOutBack · 0.25s per word*

*Original: M-093*

Each word drops from above with a small bounce.

**Spec (EN):** Each word drops from 80% above its line, overshoots 10% and settles over 0.25s at its spoken timestamp.

**Spec (AR):** كل كلمة تطيح من فوق سطرها بـ 80%، تنزل تحت 10% وتستقر خلال 0.25 ثانية وقت نطقها.

**When to use:**
- EN: Each word drops from above with a small bounce.
- AR: كل كلمة تطيح من فوق مع ارتداد خفيف.

#### `al-cap-094` — Rotate Words
**كلمات بدوران**

*workhorse · high · depth · easing: easeOutBack · 0.3s per word*

*Original: M-094*

Words twist in, lively and playful.

**Spec (EN):** Each word rotates in from -25° and 50% scale to upright and full size over 0.3s at its spoken timestamp.

**Spec (AR):** كل كلمة تدخل وهي تلف من -25 درجة وحجم 50% لين تستقيم بحجمها الكامل خلال 0.3 ثانية وقت نطقها.

**When to use:**
- EN: Words twist in, lively and playful.
- AR: كلمات تدخل وهي تلف، حيوية ومرحة.

#### `al-cap-095` — Highlighter Active
**فسفوري على الكلمة الحالية**

*workhorse · any · timeline · easing: easeOutCubic 0.15s · synced to each word*

*Original: M-095*

A highlighter sweeps over each spoken word.

**Spec (EN):** An accent highlight box grows behind the spoken word from the reading-start side over 0.15s and disappears when the next word starts.

**Spec (AR):** مربع تظليل بلون الهوية يكبر ورا الكلمة اللي تنقال من جهة بداية القراءة خلال 0.15 ثانية، ويختفي لمن تبدأ الكلمة اللي بعدها.

**When to use:**
- EN: A highlighter sweeps over each spoken word.
- AR: الكلمة اللي تنقال يمر عليها قلم فسفوري.

#### `al-cap-096` — Size Mix
**أحجام مختلفة**

*workhorse · high · timeline · easing: easeOutBack · 0.2s per word*

*Original: M-096*

A caption where important words are bigger.

**Spec (EN):** Words pop in one by one (M-012 style), but key words are set 1.6× larger and in the accent color, so the line reads like a poster.

**Spec (AR):** الكلمات تنط وحدة وحدة (مثل M-012)، بس الكلمات المهمة أكبر بـ 1.6 مرة وبلون الهوية، فيصير السطر مثل البوستر.

**When to use:**
- EN: A caption where important words are bigger.
- AR: كابشن فيه كلمات أكبر من غيرها حسب الأهمية.

#### `al-cap-097` — Speaker Label
**اسم المتكلم**

*workhorse · any · timeline · easing: easeOutCubic · 0.3s*

*Original: M-097*

When several people talk, the name tag sits above the caption.

**Spec (EN):** A small accent tag with the speaker name slides in above the caption 0.1s before the line, then the caption fades up under it.

**Spec (AR):** تاق صغير بلون الهوية فيه اسم المتكلم يدخل فوق الكابشن قبل السطر بـ 0.1 ثانية، وبعدين الكابشن يطلع تحته.

**When to use:**
- EN: When several people talk, the name tag sits above the caption.
- AR: لما في أكثر من شخص يتكلم، اسمه يطلع فوق الكابشن.

#### `al-cap-098` — Bottom Bar Caption
**شريط سفلي**

*workhorse · any · timeline · easing: easeOutExpo · 0.4s bar · 0.3s text*

*Original: M-098*

A caption inside a wide bottom bar, like the news.

**Spec (EN):** A dark full-width bar grows from the right edge (0.4s), then the caption fades in inside it (0.3s). Text and bar retract at the end.

**Spec (AR):** شريط غامق بعرض الشاشة يطلع من الحافة اليمين (0.4 ثانية)، وبعدين الكابشن يظهر داخله (0.3 ثانية). والنص والشريط ينسحبون بالنهاية.

**When to use:**
- EN: A caption inside a wide bottom bar, like the news.
- AR: كابشن داخل شريط عريض تحت، مثل الأخبار.

#### `al-cap-099` — Glitch Caption
**كابشن جلتش**

*workhorse · any · timeline · easing: steps · 0.4s glitch*

*Original: M-099*

A tech caption that glitches as it lands.

**Spec (EN):** The caption enters with a 0.4s glitch burst: red and cyan copies jitter through random slice masks, then the line snaps clean (see M-010).

**Spec (AR):** الكابشن يدخل مع رجفة جلتش 0.4 ثانية: نسخة حمرا ونسخة سماوية ترجف داخل شرائح عشوائية، وبعدين السطر يثبت نظيف (شوف M-010).

**When to use:**
- EN: A tech caption that glitches as it lands.
- AR: كابشن تقني يرجف لحظة دخوله.

#### `al-cap-100` — Progress Caption
**كابشن مع شريط تقدم**

*workhorse · calm · timeline · easing: linear · sentence length*

*Original: M-100*

A caption with a thin progress bar filling for the sentence.

**Spec (EN):** Under the caption, a thin rounded accent bar fills from the reading-start side across the sentence duration, showing how long the line lasts.

**Spec (AR):** تحت الكابشن شريط رفيع بلون الهوية يتعبى من جهة بداية القراءة على طول مدة الجملة، فيبين كم باقي على السطر.

**When to use:**
- EN: A caption with a thin progress bar filling for the sentence.
- AR: كابشن وتحته شريط يعبي على طول الجملة.

#### `al-cap-272` — Bilingual Caption
**كابشن بلغتين**

*workhorse · any · timeline · easing: easeOutCubic · synced*

*Original: M-272*

Arabic on top and English below, for a wider audience.

**Spec (EN):** Show the Arabic caption in the main style and its English translation under it in a smaller lighter line; both enter together.

**Spec (AR):** اعرض الكابشن العربي بالستايل الأساسي، وتحته الترجمة الإنجليزية بسطر أصغر وأفتح، والاثنين يدخلون مع بعض.

**When to use:**
- EN: Arabic on top and English below, for a wider audience.
- AR: عربي فوق وإنجليزي تحت، لجمهور أكبر.

#### `al-cap-273` — Text on Path
**نص على مسار**

*workhorse · calm · timeline · easing: linear · loop*

*Original: M-273*

Text flowing along a curved path.

**Spec (EN):** Lay the caption along a curved SVG path and slide its start offset so the words travel along the curve.

**Spec (AR):** حط الكابشن على مسار SVG منحني، وحرّك نقطة بدايته فالكلمات تمشي على المنحنى.

**When to use:**
- EN: Text flowing along a curved path.
- AR: نص يمشي على خط منحني.

#### `al-cap-274` — Full-Screen Kinetic
**كلمات تملا الشاشة**

*workhorse · any · depth · easing: cut · per word*

*Original: M-274*

Huge words that swap and fill the whole screen.

**Spec (EN):** Each word fills most of the frame in a bold display font and replaces the previous one on its timestamp, alternating background and text colors.

**Spec (AR):** كل كلمة تملا أغلب الشاشة بخط عريض، وتحل محل اللي قبلها وقت نطقها، والألوان تتبدل بين الخلفية والنص.

**When to use:**
- EN: Huge words that swap and fill the whole screen.
- AR: كلمات كبيرة تتبدل وتغطي الشاشة كلها.

#### `al-cap-275` — Tagged Caption
**كابشن مع تاق**

*workhorse · high · timeline · easing: easeOutBack · 0.3s*

*Original: M-275*

The first word sits in a colored tag, the rest plain.

**Spec (EN):** The caption pops in (M-089) with its first word inside a small accent box, like a label, followed by the rest of the line.

**Spec (AR):** الكابشن ينط (M-089) وأول كلمة فيه داخل مربع صغير بلون الهوية مثل التاق، وبعدها باقي السطر.

**When to use:**
- EN: The first word sits in a colored tag, the rest plain.
- AR: كلمة أولى داخل مربع ملون والباقي عادي.

#### `al-cap-011-fast` — Karaoke Highlight · Fast
**كابشن كاريوكي · سريع**

*accent · any · blur · easing: instant (0.08s fade) · synced to each word*

*Original: M-011*

Variant of M-011: أسرع بـ 40%

**Spec (EN):** A full caption line is shown in dimmed white (50% opacity). Each word turns accent color exactly at its spoken timestamp (word-level ASR timings) and stays colored. Bold display font about 64px at 1080 wide, centered, inside the safe zone (y 1350–1550).

**Spec (AR):** سطر الكابشن كامل يطلع بأبيض باهت (شفافية 50%). كل كلمة تتلون بلون الهوية بالضبط وقت نطقها (من توقيتات التفريغ كلمة كلمة) وتبقى ملونة. خط عريض تقريباً 64px على عرض 1080، بالنص وداخل المنطقة الآمنة (y من 1350 لين 1550).

**When to use:**
- EN: Use when you need a fast version of M-011.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-011.

#### `al-cap-011-slow` — Karaoke Highlight · Slow
**كابشن كاريوكي · بطيء**

*accent · any · blur · easing: instant (0.08s fade) · synced to each word*

*Original: M-011*

Variant of M-011: أبطأ بـ 60%

**Spec (EN):** A full caption line is shown in dimmed white (50% opacity). Each word turns accent color exactly at its spoken timestamp (word-level ASR timings) and stays colored. Bold display font about 64px at 1080 wide, centered, inside the safe zone (y 1350–1550).

**Spec (AR):** سطر الكابشن كامل يطلع بأبيض باهت (شفافية 50%). كل كلمة تتلون بلون الهوية بالضبط وقت نطقها (من توقيتات التفريغ كلمة كلمة) وتبقى ملونة. خط عريض تقريباً 64px على عرض 1080، بالنص وداخل المنطقة الآمنة (y من 1350 لين 1550).

**When to use:**
- EN: Use when you need a slow version of M-011.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-011.

#### `al-cap-011-gold` — Karaoke Highlight · Gold
**كابشن كاريوكي · ذهبي**

*accent · any · blur · easing: instant (0.08s fade) · synced to each word*

*Original: M-011*

Variant of M-011: نسخة ذهبية فاخرة

**Spec (EN):** A full caption line is shown in dimmed white (50% opacity). Each word turns accent color exactly at its spoken timestamp (word-level ASR timings) and stays colored. Bold display font about 64px at 1080 wide, centered, inside the safe zone (y 1350–1550).

**Spec (AR):** سطر الكابشن كامل يطلع بأبيض باهت (شفافية 50%). كل كلمة تتلون بلون الهوية بالضبط وقت نطقها (من توقيتات التفريغ كلمة كلمة) وتبقى ملونة. خط عريض تقريباً 64px على عرض 1080، بالنص وداخل المنطقة الآمنة (y من 1350 لين 1550).

**When to use:**
- EN: Use when you need a gold version of M-011.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-011.

#### `al-cap-011-boxed` — Karaoke Highlight · Boxed
**كابشن كاريوكي · صندوق**

*accent · any · blur · easing: instant (0.08s fade) · synced to each word*

*Original: M-011*

Variant of M-011: النص داخل صندوق ملون

**Spec (EN):** A full caption line is shown in dimmed white (50% opacity). Each word turns accent color exactly at its spoken timestamp (word-level ASR timings) and stays colored. Bold display font about 64px at 1080 wide, centered, inside the safe zone (y 1350–1550).

**Spec (AR):** سطر الكابشن كامل يطلع بأبيض باهت (شفافية 50%). كل كلمة تتلون بلون الهوية بالضبط وقت نطقها (من توقيتات التفريغ كلمة كلمة) وتبقى ملونة. خط عريض تقريباً 64px على عرض 1080، بالنص وداخل المنطقة الآمنة (y من 1350 لين 1550).

**When to use:**
- EN: Use when you need a boxed version of M-011.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-011.

#### `al-cap-012-fast` — Word Pop · Fast
**كلمات تنط · سريع**

*accent · any · timeline · easing: easeOutBack · 0.18s per word*

*Original: M-012*

Variant of M-012: أسرع بـ 40%

**Spec (EN):** Each word appears at its spoken timestamp, scaling from 30% to 118% and settling to 100% in 0.18s. Earlier words stay. Clear the line when the sentence ends.

**Spec (AR):** كل كلمة تطلع وقت نطقها، تكبر من 30% لـ 118% وتستقر على 100% خلال 0.18 ثانية. الكلمات اللي قبلها تبقى. امسح السطر لمن تخلص الجملة.

**When to use:**
- EN: Use when you need a fast version of M-012.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-012.

#### `al-cap-012-slow` — Word Pop · Slow
**كلمات تنط · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.18s per word*

*Original: M-012*

Variant of M-012: أبطأ بـ 60%

**Spec (EN):** Each word appears at its spoken timestamp, scaling from 30% to 118% and settling to 100% in 0.18s. Earlier words stay. Clear the line when the sentence ends.

**Spec (AR):** كل كلمة تطلع وقت نطقها، تكبر من 30% لـ 118% وتستقر على 100% خلال 0.18 ثانية. الكلمات اللي قبلها تبقى. امسح السطر لمن تخلص الجملة.

**When to use:**
- EN: Use when you need a slow version of M-012.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-012.

#### `al-cap-012-gold` — Word Pop · Gold
**كلمات تنط · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.18s per word*

*Original: M-012*

Variant of M-012: نسخة ذهبية فاخرة

**Spec (EN):** Each word appears at its spoken timestamp, scaling from 30% to 118% and settling to 100% in 0.18s. Earlier words stay. Clear the line when the sentence ends.

**Spec (AR):** كل كلمة تطلع وقت نطقها، تكبر من 30% لـ 118% وتستقر على 100% خلال 0.18 ثانية. الكلمات اللي قبلها تبقى. امسح السطر لمن تخلص الجملة.

**When to use:**
- EN: Use when you need a gold version of M-012.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-012.

#### `al-cap-012-boxed` — Word Pop · Boxed
**كلمات تنط · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.18s per word*

*Original: M-012*

Variant of M-012: النص داخل صندوق ملون

**Spec (EN):** Each word appears at its spoken timestamp, scaling from 30% to 118% and settling to 100% in 0.18s. Earlier words stay. Clear the line when the sentence ends.

**Spec (AR):** كل كلمة تطلع وقت نطقها، تكبر من 30% لـ 118% وتستقر على 100% خلال 0.18 ثانية. الكلمات اللي قبلها تبقى. امسح السطر لمن تخلص الجملة.

**When to use:**
- EN: Use when you need a boxed version of M-012.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-012.

#### `al-cap-013-fast` — Bounce Caption · Fast
**كابشن بارتداد · سريع**

*accent · any · timeline · easing: spring · 0.55s in*

*Original: M-013*

Variant of M-013: أسرع بـ 40%

**Spec (EN):** The whole caption line enters from 130% below with a spring: overshoot to -14%, rebound to +6%, settle at 0 over about 0.55s. Fade out on exit.

**Spec (AR):** سطر الكابشن كامل يدخل من تحت بـ 130% بحركة نابض: يتعدى لـ -14%، يرتد لـ +6%، ويستقر على 0 خلال تقريباً 0.55 ثانية. ويختفي بتلاشي.

**When to use:**
- EN: Use when you need a fast version of M-013.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-013.

#### `al-cap-013-slow` — Bounce Caption · Slow
**كابشن بارتداد · بطيء**

*accent · any · timeline · easing: spring · 0.55s in*

*Original: M-013*

Variant of M-013: أبطأ بـ 60%

**Spec (EN):** The whole caption line enters from 130% below with a spring: overshoot to -14%, rebound to +6%, settle at 0 over about 0.55s. Fade out on exit.

**Spec (AR):** سطر الكابشن كامل يدخل من تحت بـ 130% بحركة نابض: يتعدى لـ -14%، يرتد لـ +6%، ويستقر على 0 خلال تقريباً 0.55 ثانية. ويختفي بتلاشي.

**When to use:**
- EN: Use when you need a slow version of M-013.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-013.

#### `al-cap-013-gold` — Bounce Caption · Gold
**كابشن بارتداد · ذهبي**

*accent · any · timeline · easing: spring · 0.55s in*

*Original: M-013*

Variant of M-013: نسخة ذهبية فاخرة

**Spec (EN):** The whole caption line enters from 130% below with a spring: overshoot to -14%, rebound to +6%, settle at 0 over about 0.55s. Fade out on exit.

**Spec (AR):** سطر الكابشن كامل يدخل من تحت بـ 130% بحركة نابض: يتعدى لـ -14%، يرتد لـ +6%، ويستقر على 0 خلال تقريباً 0.55 ثانية. ويختفي بتلاشي.

**When to use:**
- EN: Use when you need a gold version of M-013.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-013.

#### `al-cap-013-boxed` — Bounce Caption · Boxed
**كابشن بارتداد · صندوق**

*accent · any · timeline · easing: spring · 0.55s in*

*Original: M-013*

Variant of M-013: النص داخل صندوق ملون

**Spec (EN):** The whole caption line enters from 130% below with a spring: overshoot to -14%, rebound to +6%, settle at 0 over about 0.55s. Fade out on exit.

**Spec (AR):** سطر الكابشن كامل يدخل من تحت بـ 130% بحركة نابض: يتعدى لـ -14%، يرتد لـ +6%، ويستقر على 0 خلال تقريباً 0.55 ثانية. ويختفي بتلاشي.

**When to use:**
- EN: Use when you need a boxed version of M-013.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-013.

#### `al-cap-014-fast` — Boxed Word · Fast
**مربع ينقل على الكلمات · سريع**

*accent · any · depth · easing: easeOutCubic 0.1s · synced to each word*

*Original: M-014*

Variant of M-014: أسرع بـ 40%

**Spec (EN):** A rounded accent box sits behind the currently spoken word only, and the word turns dark. When the next word starts, the box jumps to it, with a 6% scale pop. Other words stay white.

**Spec (AR):** مربع بلون الهوية بزوايا دائرية يكون ورا الكلمة اللي تنقال الحين بس، والكلمة تصير غامقة. لمن تبدأ الكلمة اللي بعدها، المربع ينط لها مع تكبير خفيف 6%. باقي الكلمات تبقى بيضا.

**When to use:**
- EN: Use when you need a fast version of M-014.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-014.

#### `al-cap-014-slow` — Boxed Word · Slow
**مربع ينقل على الكلمات · بطيء**

*accent · any · depth · easing: easeOutCubic 0.1s · synced to each word*

*Original: M-014*

Variant of M-014: أبطأ بـ 60%

**Spec (EN):** A rounded accent box sits behind the currently spoken word only, and the word turns dark. When the next word starts, the box jumps to it, with a 6% scale pop. Other words stay white.

**Spec (AR):** مربع بلون الهوية بزوايا دائرية يكون ورا الكلمة اللي تنقال الحين بس، والكلمة تصير غامقة. لمن تبدأ الكلمة اللي بعدها، المربع ينط لها مع تكبير خفيف 6%. باقي الكلمات تبقى بيضا.

**When to use:**
- EN: Use when you need a slow version of M-014.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-014.

#### `al-cap-014-gold` — Boxed Word · Gold
**مربع ينقل على الكلمات · ذهبي**

*accent · any · depth · easing: easeOutCubic 0.1s · synced to each word*

*Original: M-014*

Variant of M-014: نسخة ذهبية فاخرة

**Spec (EN):** A rounded accent box sits behind the currently spoken word only, and the word turns dark. When the next word starts, the box jumps to it, with a 6% scale pop. Other words stay white.

**Spec (AR):** مربع بلون الهوية بزوايا دائرية يكون ورا الكلمة اللي تنقال الحين بس، والكلمة تصير غامقة. لمن تبدأ الكلمة اللي بعدها، المربع ينط لها مع تكبير خفيف 6%. باقي الكلمات تبقى بيضا.

**When to use:**
- EN: Use when you need a gold version of M-014.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-014.

#### `al-cap-014-boxed` — Boxed Word · Boxed
**مربع ينقل على الكلمات · صندوق**

*accent · any · depth · easing: easeOutCubic 0.1s · synced to each word*

*Original: M-014*

Variant of M-014: النص داخل صندوق ملون

**Spec (EN):** A rounded accent box sits behind the currently spoken word only, and the word turns dark. When the next word starts, the box jumps to it, with a 6% scale pop. Other words stay white.

**Spec (AR):** مربع بلون الهوية بزوايا دائرية يكون ورا الكلمة اللي تنقال الحين بس، والكلمة تصير غامقة. لمن تبدأ الكلمة اللي بعدها، المربع ينط لها مع تكبير خفيف 6%. باقي الكلمات تبقى بيضا.

**When to use:**
- EN: Use when you need a boxed version of M-014.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-014.

#### `al-cap-015-fast` — One-Word Caption · Fast
**كلمة وحدة كبيرة · سريع**

*accent · any · depth · easing: easeOutBack · one word at a time*

*Original: M-015*

Variant of M-015: أسرع بـ 40%

**Spec (EN):** Only the current word is on screen, large (about 110px), centered. Each new word replaces the previous one with a quick scale from 60% to 110% to 100% over 0.15s. Optionally color key words in the accent.

**Spec (AR):** كلمة وحدة بس على الشاشة، كبيرة (تقريباً 110px) وبالنص. كل كلمة جديدة تحل محل اللي قبلها بتكبير سريع من 60% لـ 110% لـ 100% خلال 0.15 ثانية. وتقدر تلوّن الكلمات المهمة بلون الهوية.

**When to use:**
- EN: Use when you need a fast version of M-015.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-015.

#### `al-cap-015-slow` — One-Word Caption · Slow
**كلمة وحدة كبيرة · بطيء**

*accent · any · depth · easing: easeOutBack · one word at a time*

*Original: M-015*

Variant of M-015: أبطأ بـ 60%

**Spec (EN):** Only the current word is on screen, large (about 110px), centered. Each new word replaces the previous one with a quick scale from 60% to 110% to 100% over 0.15s. Optionally color key words in the accent.

**Spec (AR):** كلمة وحدة بس على الشاشة، كبيرة (تقريباً 110px) وبالنص. كل كلمة جديدة تحل محل اللي قبلها بتكبير سريع من 60% لـ 110% لـ 100% خلال 0.15 ثانية. وتقدر تلوّن الكلمات المهمة بلون الهوية.

**When to use:**
- EN: Use when you need a slow version of M-015.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-015.

#### `al-cap-015-gold` — One-Word Caption · Gold
**كلمة وحدة كبيرة · ذهبي**

*accent · any · depth · easing: easeOutBack · one word at a time*

*Original: M-015*

Variant of M-015: نسخة ذهبية فاخرة

**Spec (EN):** Only the current word is on screen, large (about 110px), centered. Each new word replaces the previous one with a quick scale from 60% to 110% to 100% over 0.15s. Optionally color key words in the accent.

**Spec (AR):** كلمة وحدة بس على الشاشة، كبيرة (تقريباً 110px) وبالنص. كل كلمة جديدة تحل محل اللي قبلها بتكبير سريع من 60% لـ 110% لـ 100% خلال 0.15 ثانية. وتقدر تلوّن الكلمات المهمة بلون الهوية.

**When to use:**
- EN: Use when you need a gold version of M-015.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-015.

#### `al-cap-015-boxed` — One-Word Caption · Boxed
**كلمة وحدة كبيرة · صندوق**

*accent · any · depth · easing: easeOutBack · one word at a time*

*Original: M-015*

Variant of M-015: النص داخل صندوق ملون

**Spec (EN):** Only the current word is on screen, large (about 110px), centered. Each new word replaces the previous one with a quick scale from 60% to 110% to 100% over 0.15s. Optionally color key words in the accent.

**Spec (AR):** كلمة وحدة بس على الشاشة، كبيرة (تقريباً 110px) وبالنص. كل كلمة جديدة تحل محل اللي قبلها بتكبير سريع من 60% لـ 110% لـ 100% خلال 0.15 ثانية. وتقدر تلوّن الكلمات المهمة بلون الهوية.

**When to use:**
- EN: Use when you need a boxed version of M-015.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-015.

#### `al-cap-081-fast` — Two-Line Caption · Fast
**كابشن بسطرين · سريع**

*accent · any · depth · easing: easeOutCubic · 0.45s per line · 0.4s stagger*

*Original: M-081*

Variant of M-081: أسرع بـ 40%

**Spec (EN):** Split the sentence into two balanced lines. Each line rises 40px and fades in over 0.45s, the second starting 0.4s after the first. Keep both inside the safe zone.

**Spec (AR):** قسّم الجملة سطرين متوازنين. كل سطر يطلع لفوق 40px ويظهر خلال 0.45 ثانية، والثاني يبدأ بعد الأول بـ 0.4 ثانية. وخل السطرين داخل المنطقة الآمنة.

**When to use:**
- EN: Use when you need a fast version of M-081.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-081.

#### `al-cap-081-slow` — Two-Line Caption · Slow
**كابشن بسطرين · بطيء**

*accent · any · depth · easing: easeOutCubic · 0.45s per line · 0.4s stagger*

*Original: M-081*

Variant of M-081: أبطأ بـ 60%

**Spec (EN):** Split the sentence into two balanced lines. Each line rises 40px and fades in over 0.45s, the second starting 0.4s after the first. Keep both inside the safe zone.

**Spec (AR):** قسّم الجملة سطرين متوازنين. كل سطر يطلع لفوق 40px ويظهر خلال 0.45 ثانية، والثاني يبدأ بعد الأول بـ 0.4 ثانية. وخل السطرين داخل المنطقة الآمنة.

**When to use:**
- EN: Use when you need a slow version of M-081.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-081.

#### `al-cap-081-gold` — Two-Line Caption · Gold
**كابشن بسطرين · ذهبي**

*accent · any · depth · easing: easeOutCubic · 0.45s per line · 0.4s stagger*

*Original: M-081*

Variant of M-081: نسخة ذهبية فاخرة

**Spec (EN):** Split the sentence into two balanced lines. Each line rises 40px and fades in over 0.45s, the second starting 0.4s after the first. Keep both inside the safe zone.

**Spec (AR):** قسّم الجملة سطرين متوازنين. كل سطر يطلع لفوق 40px ويظهر خلال 0.45 ثانية، والثاني يبدأ بعد الأول بـ 0.4 ثانية. وخل السطرين داخل المنطقة الآمنة.

**When to use:**
- EN: Use when you need a gold version of M-081.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-081.

#### `al-cap-081-boxed` — Two-Line Caption · Boxed
**كابشن بسطرين · صندوق**

*accent · any · depth · easing: easeOutCubic · 0.45s per line · 0.4s stagger*

*Original: M-081*

Variant of M-081: النص داخل صندوق ملون

**Spec (EN):** Split the sentence into two balanced lines. Each line rises 40px and fades in over 0.45s, the second starting 0.4s after the first. Keep both inside the safe zone.

**Spec (AR):** قسّم الجملة سطرين متوازنين. كل سطر يطلع لفوق 40px ويظهر خلال 0.45 ثانية، والثاني يبدأ بعد الأول بـ 0.4 ثانية. وخل السطرين داخل المنطقة الآمنة.

**When to use:**
- EN: Use when you need a boxed version of M-081.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-081.

#### `al-cap-082-fast` — Typewriter Caption · Fast
**كابشن آلة كاتبة · سريع**

*accent · any · timeline · easing: steps · synced to speech*

*Original: M-082*

Variant of M-082: أسرع بـ 40%

**Spec (EN):** The caption reveals character by character from the reading-start side, paced so it finishes when the sentence ends. No caret.

**Spec (AR):** الكابشن ينكشف حرف حرف من جهة بداية القراءة، وسرعته بحيث يخلص لمن تخلص الجملة. بدون مؤشر كتابة.

**When to use:**
- EN: Use when you need a fast version of M-082.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-082.

#### `al-cap-082-slow` — Typewriter Caption · Slow
**كابشن آلة كاتبة · بطيء**

*accent · any · timeline · easing: steps · synced to speech*

*Original: M-082*

Variant of M-082: أبطأ بـ 60%

**Spec (EN):** The caption reveals character by character from the reading-start side, paced so it finishes when the sentence ends. No caret.

**Spec (AR):** الكابشن ينكشف حرف حرف من جهة بداية القراءة، وسرعته بحيث يخلص لمن تخلص الجملة. بدون مؤشر كتابة.

**When to use:**
- EN: Use when you need a slow version of M-082.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-082.

#### `al-cap-082-gold` — Typewriter Caption · Gold
**كابشن آلة كاتبة · ذهبي**

*accent · any · timeline · easing: steps · synced to speech*

*Original: M-082*

Variant of M-082: نسخة ذهبية فاخرة

**Spec (EN):** The caption reveals character by character from the reading-start side, paced so it finishes when the sentence ends. No caret.

**Spec (AR):** الكابشن ينكشف حرف حرف من جهة بداية القراءة، وسرعته بحيث يخلص لمن تخلص الجملة. بدون مؤشر كتابة.

**When to use:**
- EN: Use when you need a gold version of M-082.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-082.

#### `al-cap-082-boxed` — Typewriter Caption · Boxed
**كابشن آلة كاتبة · صندوق**

*accent · any · timeline · easing: steps · synced to speech*

*Original: M-082*

Variant of M-082: النص داخل صندوق ملون

**Spec (EN):** The caption reveals character by character from the reading-start side, paced so it finishes when the sentence ends. No caret.

**Spec (AR):** الكابشن ينكشف حرف حرف من جهة بداية القراءة، وسرعته بحيث يخلص لمن تخلص الجملة. بدون مؤشر كتابة.

**When to use:**
- EN: Use when you need a boxed version of M-082.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-082.

#### `al-cap-083-fast` — Fade Words · Fast
**كلمات تظهر بتلاشي · سريع**

*accent · calm · timeline · easing: easeOutQuad · 0.25s per word*

*Original: M-083*

Variant of M-083: أسرع بـ 40%

**Spec (EN):** Each word fades from 0 to 100% opacity over 0.25s at its spoken timestamp. Earlier words stay. Clear the line at the end of the sentence.

**Spec (AR):** كل كلمة تظهر من 0 لـ 100% خلال 0.25 ثانية وقت نطقها. الكلمات اللي قبلها تبقى. وامسح السطر لمن تخلص الجملة.

**When to use:**
- EN: Use when you need a fast version of M-083.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-083.

#### `al-cap-083-slow` — Fade Words · Slow
**كلمات تظهر بتلاشي · بطيء**

*accent · calm · timeline · easing: easeOutQuad · 0.25s per word*

*Original: M-083*

Variant of M-083: أبطأ بـ 60%

**Spec (EN):** Each word fades from 0 to 100% opacity over 0.25s at its spoken timestamp. Earlier words stay. Clear the line at the end of the sentence.

**Spec (AR):** كل كلمة تظهر من 0 لـ 100% خلال 0.25 ثانية وقت نطقها. الكلمات اللي قبلها تبقى. وامسح السطر لمن تخلص الجملة.

**When to use:**
- EN: Use when you need a slow version of M-083.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-083.

#### `al-cap-083-gold` — Fade Words · Gold
**كلمات تظهر بتلاشي · ذهبي**

*accent · calm · timeline · easing: easeOutQuad · 0.25s per word*

*Original: M-083*

Variant of M-083: نسخة ذهبية فاخرة

**Spec (EN):** Each word fades from 0 to 100% opacity over 0.25s at its spoken timestamp. Earlier words stay. Clear the line at the end of the sentence.

**Spec (AR):** كل كلمة تظهر من 0 لـ 100% خلال 0.25 ثانية وقت نطقها. الكلمات اللي قبلها تبقى. وامسح السطر لمن تخلص الجملة.

**When to use:**
- EN: Use when you need a gold version of M-083.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-083.

#### `al-cap-083-boxed` — Fade Words · Boxed
**كلمات تظهر بتلاشي · صندوق**

*accent · calm · timeline · easing: easeOutQuad · 0.25s per word*

*Original: M-083*

Variant of M-083: النص داخل صندوق ملون

**Spec (EN):** Each word fades from 0 to 100% opacity over 0.25s at its spoken timestamp. Earlier words stay. Clear the line at the end of the sentence.

**Spec (AR):** كل كلمة تظهر من 0 لـ 100% خلال 0.25 ثانية وقت نطقها. الكلمات اللي قبلها تبقى. وامسح السطر لمن تخلص الجملة.

**When to use:**
- EN: Use when you need a boxed version of M-083.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-083.

#### `al-cap-084-fast` — Slide-Up Words · Fast
**كلمات تطلع من تحت · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.25s per word*

*Original: M-084*

Variant of M-084: أسرع بـ 40%

**Spec (EN):** Each word slides up from 60% below its line while fading in over 0.25s at its spoken timestamp.

**Spec (AR):** كل كلمة تطلع من تحت سطرها بـ 60% وهي تظهر خلال 0.25 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a fast version of M-084.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-084.

#### `al-cap-084-slow` — Slide-Up Words · Slow
**كلمات تطلع من تحت · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.25s per word*

*Original: M-084*

Variant of M-084: أبطأ بـ 60%

**Spec (EN):** Each word slides up from 60% below its line while fading in over 0.25s at its spoken timestamp.

**Spec (AR):** كل كلمة تطلع من تحت سطرها بـ 60% وهي تظهر خلال 0.25 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a slow version of M-084.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-084.

#### `al-cap-084-gold` — Slide-Up Words · Gold
**كلمات تطلع من تحت · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.25s per word*

*Original: M-084*

Variant of M-084: نسخة ذهبية فاخرة

**Spec (EN):** Each word slides up from 60% below its line while fading in over 0.25s at its spoken timestamp.

**Spec (AR):** كل كلمة تطلع من تحت سطرها بـ 60% وهي تظهر خلال 0.25 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a gold version of M-084.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-084.

#### `al-cap-084-boxed` — Slide-Up Words · Boxed
**كلمات تطلع من تحت · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.25s per word*

*Original: M-084*

Variant of M-084: النص داخل صندوق ملون

**Spec (EN):** Each word slides up from 60% below its line while fading in over 0.25s at its spoken timestamp.

**Spec (AR):** كل كلمة تطلع من تحت سطرها بـ 60% وهي تظهر خلال 0.25 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a boxed version of M-084.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-084.

#### `al-cap-085-fast` — Underline Active Word · Fast
**خط تحت الكلمة الحالية · سريع**

*accent · any · timeline · easing: easeOutCubic 0.1s · synced to each word*

*Original: M-085*

Variant of M-085: أسرع بـ 40%

**Spec (EN):** The whole line is visible in white. A rounded accent bar sits under the word being spoken and jumps to the next word at its timestamp.

**Spec (AR):** السطر كامل يطلع أبيض. خط بلون الهوية بزوايا دائرية يكون تحت الكلمة اللي تنقال، وينط للكلمة اللي بعدها وقت نطقها.

**When to use:**
- EN: Use when you need a fast version of M-085.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-085.

#### `al-cap-085-slow` — Underline Active Word · Slow
**خط تحت الكلمة الحالية · بطيء**

*accent · any · timeline · easing: easeOutCubic 0.1s · synced to each word*

*Original: M-085*

Variant of M-085: أبطأ بـ 60%

**Spec (EN):** The whole line is visible in white. A rounded accent bar sits under the word being spoken and jumps to the next word at its timestamp.

**Spec (AR):** السطر كامل يطلع أبيض. خط بلون الهوية بزوايا دائرية يكون تحت الكلمة اللي تنقال، وينط للكلمة اللي بعدها وقت نطقها.

**When to use:**
- EN: Use when you need a slow version of M-085.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-085.

#### `al-cap-085-gold` — Underline Active Word · Gold
**خط تحت الكلمة الحالية · ذهبي**

*accent · any · timeline · easing: easeOutCubic 0.1s · synced to each word*

*Original: M-085*

Variant of M-085: نسخة ذهبية فاخرة

**Spec (EN):** The whole line is visible in white. A rounded accent bar sits under the word being spoken and jumps to the next word at its timestamp.

**Spec (AR):** السطر كامل يطلع أبيض. خط بلون الهوية بزوايا دائرية يكون تحت الكلمة اللي تنقال، وينط للكلمة اللي بعدها وقت نطقها.

**When to use:**
- EN: Use when you need a gold version of M-085.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-085.

#### `al-cap-085-boxed` — Underline Active Word · Boxed
**خط تحت الكلمة الحالية · صندوق**

*accent · any · timeline · easing: easeOutCubic 0.1s · synced to each word*

*Original: M-085*

Variant of M-085: النص داخل صندوق ملون

**Spec (EN):** The whole line is visible in white. A rounded accent bar sits under the word being spoken and jumps to the next word at its timestamp.

**Spec (AR):** السطر كامل يطلع أبيض. خط بلون الهوية بزوايا دائرية يكون تحت الكلمة اللي تنقال، وينط للكلمة اللي بعدها وقت نطقها.

**When to use:**
- EN: Use when you need a boxed version of M-085.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-085.

#### `al-cap-086-fast` — Scale Active Word · Fast
**الكلمة الحالية أكبر · سريع**

*accent · any · timeline · easing: easeOutBack 0.12s · synced to each word*

*Original: M-086*

Variant of M-086: أسرع بـ 40%

**Spec (EN):** The word being spoken scales to 125% and turns the accent color; it returns to normal when the next word starts.

**Spec (AR):** الكلمة اللي تنقال تكبر لـ 125% وتصير بلون الهوية، وترجع طبيعية لمن تبدأ الكلمة اللي بعدها.

**When to use:**
- EN: Use when you need a fast version of M-086.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-086.

#### `al-cap-086-slow` — Scale Active Word · Slow
**الكلمة الحالية أكبر · بطيء**

*accent · any · timeline · easing: easeOutBack 0.12s · synced to each word*

*Original: M-086*

Variant of M-086: أبطأ بـ 60%

**Spec (EN):** The word being spoken scales to 125% and turns the accent color; it returns to normal when the next word starts.

**Spec (AR):** الكلمة اللي تنقال تكبر لـ 125% وتصير بلون الهوية، وترجع طبيعية لمن تبدأ الكلمة اللي بعدها.

**When to use:**
- EN: Use when you need a slow version of M-086.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-086.

#### `al-cap-086-gold` — Scale Active Word · Gold
**الكلمة الحالية أكبر · ذهبي**

*accent · any · timeline · easing: easeOutBack 0.12s · synced to each word*

*Original: M-086*

Variant of M-086: نسخة ذهبية فاخرة

**Spec (EN):** The word being spoken scales to 125% and turns the accent color; it returns to normal when the next word starts.

**Spec (AR):** الكلمة اللي تنقال تكبر لـ 125% وتصير بلون الهوية، وترجع طبيعية لمن تبدأ الكلمة اللي بعدها.

**When to use:**
- EN: Use when you need a gold version of M-086.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-086.

#### `al-cap-086-boxed` — Scale Active Word · Boxed
**الكلمة الحالية أكبر · صندوق**

*accent · any · timeline · easing: easeOutBack 0.12s · synced to each word*

*Original: M-086*

Variant of M-086: النص داخل صندوق ملون

**Spec (EN):** The word being spoken scales to 125% and turns the accent color; it returns to normal when the next word starts.

**Spec (AR):** الكلمة اللي تنقال تكبر لـ 125% وتصير بلون الهوية، وترجع طبيعية لمن تبدأ الكلمة اللي بعدها.

**When to use:**
- EN: Use when you need a boxed version of M-086.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-086.

#### `al-cap-087-fast` — Color Sweep Line · Fast
**لون يمسح السطر · سريع**

*accent · calm · timeline · easing: linear · sentence length*

*Original: M-087*

Variant of M-087: أسرع بـ 40%

**Spec (EN):** A two-color gradient is clipped to the caption text and slides from the reading-start side to the end over the sentence duration, so spoken parts turn accent.

**Spec (AR):** تدرج بلونين داخل حروف الكابشن، يتحرك من جهة بداية القراءة لآخر السطر على طول مدة الجملة، فالجزء اللي انقال يصير بلون الهوية.

**When to use:**
- EN: Use when you need a fast version of M-087.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-087.

#### `al-cap-087-slow` — Color Sweep Line · Slow
**لون يمسح السطر · بطيء**

*accent · calm · timeline · easing: linear · sentence length*

*Original: M-087*

Variant of M-087: أبطأ بـ 60%

**Spec (EN):** A two-color gradient is clipped to the caption text and slides from the reading-start side to the end over the sentence duration, so spoken parts turn accent.

**Spec (AR):** تدرج بلونين داخل حروف الكابشن، يتحرك من جهة بداية القراءة لآخر السطر على طول مدة الجملة، فالجزء اللي انقال يصير بلون الهوية.

**When to use:**
- EN: Use when you need a slow version of M-087.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-087.

#### `al-cap-087-gold` — Color Sweep Line · Gold
**لون يمسح السطر · ذهبي**

*accent · calm · timeline · easing: linear · sentence length*

*Original: M-087*

Variant of M-087: نسخة ذهبية فاخرة

**Spec (EN):** A two-color gradient is clipped to the caption text and slides from the reading-start side to the end over the sentence duration, so spoken parts turn accent.

**Spec (AR):** تدرج بلونين داخل حروف الكابشن، يتحرك من جهة بداية القراءة لآخر السطر على طول مدة الجملة، فالجزء اللي انقال يصير بلون الهوية.

**When to use:**
- EN: Use when you need a gold version of M-087.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-087.

#### `al-cap-087-boxed` — Color Sweep Line · Boxed
**لون يمسح السطر · صندوق**

*accent · calm · timeline · easing: linear · sentence length*

*Original: M-087*

Variant of M-087: النص داخل صندوق ملون

**Spec (EN):** A two-color gradient is clipped to the caption text and slides from the reading-start side to the end over the sentence duration, so spoken parts turn accent.

**Spec (AR):** تدرج بلونين داخل حروف الكابشن، يتحرك من جهة بداية القراءة لآخر السطر على طول مدة الجملة، فالجزء اللي انقال يصير بلون الهوية.

**When to use:**
- EN: Use when you need a boxed version of M-087.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-087.

#### `al-cap-088-fast` — Keyword Color · Fast
**كلمة مفتاحية بلون · سريع**

*accent · any · timeline · easing: easeOutBack · 0.2s*

*Original: M-088*

Variant of M-088: أسرع بـ 40%

**Spec (EN):** The caption stays white. Only the key word turns accent and scales to 112% at its timestamp, and stays like that until the line clears.

**Spec (AR):** الكابشن يبقى أبيض. الكلمة المهمة بس تصير بلون الهوية وتكبر لـ 112% وقت نطقها، وتبقى كذا لين يختفي السطر.

**When to use:**
- EN: Use when you need a fast version of M-088.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-088.

#### `al-cap-088-slow` — Keyword Color · Slow
**كلمة مفتاحية بلون · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.2s*

*Original: M-088*

Variant of M-088: أبطأ بـ 60%

**Spec (EN):** The caption stays white. Only the key word turns accent and scales to 112% at its timestamp, and stays like that until the line clears.

**Spec (AR):** الكابشن يبقى أبيض. الكلمة المهمة بس تصير بلون الهوية وتكبر لـ 112% وقت نطقها، وتبقى كذا لين يختفي السطر.

**When to use:**
- EN: Use when you need a slow version of M-088.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-088.

#### `al-cap-088-gold` — Keyword Color · Gold
**كلمة مفتاحية بلون · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.2s*

*Original: M-088*

Variant of M-088: نسخة ذهبية فاخرة

**Spec (EN):** The caption stays white. Only the key word turns accent and scales to 112% at its timestamp, and stays like that until the line clears.

**Spec (AR):** الكابشن يبقى أبيض. الكلمة المهمة بس تصير بلون الهوية وتكبر لـ 112% وقت نطقها، وتبقى كذا لين يختفي السطر.

**When to use:**
- EN: Use when you need a gold version of M-088.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-088.

#### `al-cap-088-boxed` — Keyword Color · Boxed
**كلمة مفتاحية بلون · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.2s*

*Original: M-088*

Variant of M-088: النص داخل صندوق ملون

**Spec (EN):** The caption stays white. Only the key word turns accent and scales to 112% at its timestamp, and stays like that until the line clears.

**Spec (AR):** الكابشن يبقى أبيض. الكلمة المهمة بس تصير بلون الهوية وتكبر لـ 112% وقت نطقها، وتبقى كذا لين يختفي السطر.

**When to use:**
- EN: Use when you need a boxed version of M-088.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-088.

#### `al-cap-089-fast` — Pill Caption · Fast
**كابشن داخل كبسولة · سريع**

*accent · any · blur · easing: easeOutBack · 0.3s in*

*Original: M-089*

Variant of M-089: أسرع بـ 40%

**Spec (EN):** The caption sits inside a dark rounded pill (85% opacity, generous padding). The pill pops from 60% to 105% to 100% over 0.3s.

**Spec (AR):** الكابشن داخل كبسولة غامقة بزوايا دائرية (شفافية 85% ومسافات داخلية كافية). الكبسولة تنط من 60% لـ 105% لـ 100% خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-089.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-089.

#### `al-cap-089-slow` — Pill Caption · Slow
**كابشن داخل كبسولة · بطيء**

*accent · any · blur · easing: easeOutBack · 0.3s in*

*Original: M-089*

Variant of M-089: أبطأ بـ 60%

**Spec (EN):** The caption sits inside a dark rounded pill (85% opacity, generous padding). The pill pops from 60% to 105% to 100% over 0.3s.

**Spec (AR):** الكابشن داخل كبسولة غامقة بزوايا دائرية (شفافية 85% ومسافات داخلية كافية). الكبسولة تنط من 60% لـ 105% لـ 100% خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-089.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-089.

#### `al-cap-089-gold` — Pill Caption · Gold
**كابشن داخل كبسولة · ذهبي**

*accent · any · blur · easing: easeOutBack · 0.3s in*

*Original: M-089*

Variant of M-089: نسخة ذهبية فاخرة

**Spec (EN):** The caption sits inside a dark rounded pill (85% opacity, generous padding). The pill pops from 60% to 105% to 100% over 0.3s.

**Spec (AR):** الكابشن داخل كبسولة غامقة بزوايا دائرية (شفافية 85% ومسافات داخلية كافية). الكبسولة تنط من 60% لـ 105% لـ 100% خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-089.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-089.

#### `al-cap-089-boxed` — Pill Caption · Boxed
**كابشن داخل كبسولة · صندوق**

*accent · any · blur · easing: easeOutBack · 0.3s in*

*Original: M-089*

Variant of M-089: النص داخل صندوق ملون

**Spec (EN):** The caption sits inside a dark rounded pill (85% opacity, generous padding). The pill pops from 60% to 105% to 100% over 0.3s.

**Spec (AR):** الكابشن داخل كبسولة غامقة بزوايا دائرية (شفافية 85% ومسافات داخلية كافية). الكبسولة تنط من 60% لـ 105% لـ 100% خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-089.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-089.

#### `al-cap-090-fast` — Outline Caption · Fast
**كابشن بحدود سودا · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.45s in*

*Original: M-090*

Variant of M-090: أسرع بـ 40%

**Spec (EN):** White bold caption with a black outline about 7% of the font size (stroke painted under the fill), no shadow. Enters with a fade-up.

**Spec (AR):** كابشن أبيض عريض بحدود سودا سماكتها تقريباً 7% من حجم الخط (الحدود تحت التعبئة)، بدون ظل. ويدخل بظهور من تحت.

**When to use:**
- EN: Use when you need a fast version of M-090.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-090.

#### `al-cap-090-slow` — Outline Caption · Slow
**كابشن بحدود سودا · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.45s in*

*Original: M-090*

Variant of M-090: أبطأ بـ 60%

**Spec (EN):** White bold caption with a black outline about 7% of the font size (stroke painted under the fill), no shadow. Enters with a fade-up.

**Spec (AR):** كابشن أبيض عريض بحدود سودا سماكتها تقريباً 7% من حجم الخط (الحدود تحت التعبئة)، بدون ظل. ويدخل بظهور من تحت.

**When to use:**
- EN: Use when you need a slow version of M-090.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-090.

#### `al-cap-090-gold` — Outline Caption · Gold
**كابشن بحدود سودا · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.45s in*

*Original: M-090*

Variant of M-090: نسخة ذهبية فاخرة

**Spec (EN):** White bold caption with a black outline about 7% of the font size (stroke painted under the fill), no shadow. Enters with a fade-up.

**Spec (AR):** كابشن أبيض عريض بحدود سودا سماكتها تقريباً 7% من حجم الخط (الحدود تحت التعبئة)، بدون ظل. ويدخل بظهور من تحت.

**When to use:**
- EN: Use when you need a gold version of M-090.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-090.

#### `al-cap-090-boxed` — Outline Caption · Boxed
**كابشن بحدود سودا · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.45s in*

*Original: M-090*

Variant of M-090: النص داخل صندوق ملون

**Spec (EN):** White bold caption with a black outline about 7% of the font size (stroke painted under the fill), no shadow. Enters with a fade-up.

**Spec (AR):** كابشن أبيض عريض بحدود سودا سماكتها تقريباً 7% من حجم الخط (الحدود تحت التعبئة)، بدون ظل. ويدخل بظهور من تحت.

**When to use:**
- EN: Use when you need a boxed version of M-090.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-090.

#### `al-cap-091-fast` — Shadow Pop · Fast
**ظل صلب · سريع**

*accent · any · depth · easing: easeOutBack · 0.3s*

*Original: M-091*

Variant of M-091: أسرع بـ 40%

**Spec (EN):** A solid accent shadow (no blur) grows to 1.2% offset down-right while the text moves 1% up-left, so it looks lifted. Reverse at exit.

**Spec (AR):** ظل صلب بلون الهوية (بدون ضبابية) يبعد 1.2% لتحت يمين والنص يتحرك 1% لفوق يسار، فيبين كأنه مرفوع. وبالخروج يرجع.

**When to use:**
- EN: Use when you need a fast version of M-091.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-091.

#### `al-cap-091-slow` — Shadow Pop · Slow
**ظل صلب · بطيء**

*accent · any · depth · easing: easeOutBack · 0.3s*

*Original: M-091*

Variant of M-091: أبطأ بـ 60%

**Spec (EN):** A solid accent shadow (no blur) grows to 1.2% offset down-right while the text moves 1% up-left, so it looks lifted. Reverse at exit.

**Spec (AR):** ظل صلب بلون الهوية (بدون ضبابية) يبعد 1.2% لتحت يمين والنص يتحرك 1% لفوق يسار، فيبين كأنه مرفوع. وبالخروج يرجع.

**When to use:**
- EN: Use when you need a slow version of M-091.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-091.

#### `al-cap-091-gold` — Shadow Pop · Gold
**ظل صلب · ذهبي**

*accent · any · depth · easing: easeOutBack · 0.3s*

*Original: M-091*

Variant of M-091: نسخة ذهبية فاخرة

**Spec (EN):** A solid accent shadow (no blur) grows to 1.2% offset down-right while the text moves 1% up-left, so it looks lifted. Reverse at exit.

**Spec (AR):** ظل صلب بلون الهوية (بدون ضبابية) يبعد 1.2% لتحت يمين والنص يتحرك 1% لفوق يسار، فيبين كأنه مرفوع. وبالخروج يرجع.

**When to use:**
- EN: Use when you need a gold version of M-091.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-091.

#### `al-cap-091-boxed` — Shadow Pop · Boxed
**ظل صلب · صندوق**

*accent · any · depth · easing: easeOutBack · 0.3s*

*Original: M-091*

Variant of M-091: النص داخل صندوق ملون

**Spec (EN):** A solid accent shadow (no blur) grows to 1.2% offset down-right while the text moves 1% up-left, so it looks lifted. Reverse at exit.

**Spec (AR):** ظل صلب بلون الهوية (بدون ضبابية) يبعد 1.2% لتحت يمين والنص يتحرك 1% لفوق يسار، فيبين كأنه مرفوع. وبالخروج يرجع.

**When to use:**
- EN: Use when you need a boxed version of M-091.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-091.

#### `al-cap-092-fast` — Blur Words · Fast
**كلمات من ضبابية · سريع**

*accent · calm · blur · easing: easeOutQuad · 0.3s per word*

*Original: M-092*

Variant of M-092: أسرع بـ 40%

**Spec (EN):** Each word goes from 2% blur and opacity 0 to sharp and visible over 0.3s at its spoken timestamp.

**Spec (AR):** كل كلمة تتحول من ضبابية 2% وشفافية 0 لواضحة وظاهرة خلال 0.3 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a fast version of M-092.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-092.

#### `al-cap-092-slow` — Blur Words · Slow
**كلمات من ضبابية · بطيء**

*accent · calm · blur · easing: easeOutQuad · 0.3s per word*

*Original: M-092*

Variant of M-092: أبطأ بـ 60%

**Spec (EN):** Each word goes from 2% blur and opacity 0 to sharp and visible over 0.3s at its spoken timestamp.

**Spec (AR):** كل كلمة تتحول من ضبابية 2% وشفافية 0 لواضحة وظاهرة خلال 0.3 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a slow version of M-092.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-092.

#### `al-cap-092-gold` — Blur Words · Gold
**كلمات من ضبابية · ذهبي**

*accent · calm · blur · easing: easeOutQuad · 0.3s per word*

*Original: M-092*

Variant of M-092: نسخة ذهبية فاخرة

**Spec (EN):** Each word goes from 2% blur and opacity 0 to sharp and visible over 0.3s at its spoken timestamp.

**Spec (AR):** كل كلمة تتحول من ضبابية 2% وشفافية 0 لواضحة وظاهرة خلال 0.3 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a gold version of M-092.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-092.

#### `al-cap-092-boxed` — Blur Words · Boxed
**كلمات من ضبابية · صندوق**

*accent · calm · blur · easing: easeOutQuad · 0.3s per word*

*Original: M-092*

Variant of M-092: النص داخل صندوق ملون

**Spec (EN):** Each word goes from 2% blur and opacity 0 to sharp and visible over 0.3s at its spoken timestamp.

**Spec (AR):** كل كلمة تتحول من ضبابية 2% وشفافية 0 لواضحة وظاهرة خلال 0.3 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a boxed version of M-092.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-092.

#### `al-cap-093-fast` — Drop Words · Fast
**كلمات تطيح · سريع**

*accent · any · timeline · easing: easeOutBack · 0.25s per word*

*Original: M-093*

Variant of M-093: أسرع بـ 40%

**Spec (EN):** Each word drops from 80% above its line, overshoots 10% and settles over 0.25s at its spoken timestamp.

**Spec (AR):** كل كلمة تطيح من فوق سطرها بـ 80%، تنزل تحت 10% وتستقر خلال 0.25 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a fast version of M-093.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-093.

#### `al-cap-093-slow` — Drop Words · Slow
**كلمات تطيح · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.25s per word*

*Original: M-093*

Variant of M-093: أبطأ بـ 60%

**Spec (EN):** Each word drops from 80% above its line, overshoots 10% and settles over 0.25s at its spoken timestamp.

**Spec (AR):** كل كلمة تطيح من فوق سطرها بـ 80%، تنزل تحت 10% وتستقر خلال 0.25 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a slow version of M-093.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-093.

#### `al-cap-093-gold` — Drop Words · Gold
**كلمات تطيح · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.25s per word*

*Original: M-093*

Variant of M-093: نسخة ذهبية فاخرة

**Spec (EN):** Each word drops from 80% above its line, overshoots 10% and settles over 0.25s at its spoken timestamp.

**Spec (AR):** كل كلمة تطيح من فوق سطرها بـ 80%، تنزل تحت 10% وتستقر خلال 0.25 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a gold version of M-093.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-093.

#### `al-cap-093-boxed` — Drop Words · Boxed
**كلمات تطيح · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.25s per word*

*Original: M-093*

Variant of M-093: النص داخل صندوق ملون

**Spec (EN):** Each word drops from 80% above its line, overshoots 10% and settles over 0.25s at its spoken timestamp.

**Spec (AR):** كل كلمة تطيح من فوق سطرها بـ 80%، تنزل تحت 10% وتستقر خلال 0.25 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a boxed version of M-093.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-093.

#### `al-cap-094-fast` — Rotate Words · Fast
**كلمات بدوران · سريع**

*accent · any · depth · easing: easeOutBack · 0.3s per word*

*Original: M-094*

Variant of M-094: أسرع بـ 40%

**Spec (EN):** Each word rotates in from -25° and 50% scale to upright and full size over 0.3s at its spoken timestamp.

**Spec (AR):** كل كلمة تدخل وهي تلف من -25 درجة وحجم 50% لين تستقيم بحجمها الكامل خلال 0.3 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a fast version of M-094.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-094.

#### `al-cap-094-slow` — Rotate Words · Slow
**كلمات بدوران · بطيء**

*accent · any · depth · easing: easeOutBack · 0.3s per word*

*Original: M-094*

Variant of M-094: أبطأ بـ 60%

**Spec (EN):** Each word rotates in from -25° and 50% scale to upright and full size over 0.3s at its spoken timestamp.

**Spec (AR):** كل كلمة تدخل وهي تلف من -25 درجة وحجم 50% لين تستقيم بحجمها الكامل خلال 0.3 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a slow version of M-094.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-094.

#### `al-cap-094-gold` — Rotate Words · Gold
**كلمات بدوران · ذهبي**

*accent · any · depth · easing: easeOutBack · 0.3s per word*

*Original: M-094*

Variant of M-094: نسخة ذهبية فاخرة

**Spec (EN):** Each word rotates in from -25° and 50% scale to upright and full size over 0.3s at its spoken timestamp.

**Spec (AR):** كل كلمة تدخل وهي تلف من -25 درجة وحجم 50% لين تستقيم بحجمها الكامل خلال 0.3 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a gold version of M-094.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-094.

#### `al-cap-094-boxed` — Rotate Words · Boxed
**كلمات بدوران · صندوق**

*accent · any · depth · easing: easeOutBack · 0.3s per word*

*Original: M-094*

Variant of M-094: النص داخل صندوق ملون

**Spec (EN):** Each word rotates in from -25° and 50% scale to upright and full size over 0.3s at its spoken timestamp.

**Spec (AR):** كل كلمة تدخل وهي تلف من -25 درجة وحجم 50% لين تستقيم بحجمها الكامل خلال 0.3 ثانية وقت نطقها.

**When to use:**
- EN: Use when you need a boxed version of M-094.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-094.

#### `al-cap-095-fast` — Highlighter Active · Fast
**فسفوري على الكلمة الحالية · سريع**

*accent · any · timeline · easing: easeOutCubic 0.15s · synced to each word*

*Original: M-095*

Variant of M-095: أسرع بـ 40%

**Spec (EN):** An accent highlight box grows behind the spoken word from the reading-start side over 0.15s and disappears when the next word starts.

**Spec (AR):** مربع تظليل بلون الهوية يكبر ورا الكلمة اللي تنقال من جهة بداية القراءة خلال 0.15 ثانية، ويختفي لمن تبدأ الكلمة اللي بعدها.

**When to use:**
- EN: Use when you need a fast version of M-095.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-095.

#### `al-cap-095-slow` — Highlighter Active · Slow
**فسفوري على الكلمة الحالية · بطيء**

*accent · any · timeline · easing: easeOutCubic 0.15s · synced to each word*

*Original: M-095*

Variant of M-095: أبطأ بـ 60%

**Spec (EN):** An accent highlight box grows behind the spoken word from the reading-start side over 0.15s and disappears when the next word starts.

**Spec (AR):** مربع تظليل بلون الهوية يكبر ورا الكلمة اللي تنقال من جهة بداية القراءة خلال 0.15 ثانية، ويختفي لمن تبدأ الكلمة اللي بعدها.

**When to use:**
- EN: Use when you need a slow version of M-095.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-095.

#### `al-cap-095-gold` — Highlighter Active · Gold
**فسفوري على الكلمة الحالية · ذهبي**

*accent · any · timeline · easing: easeOutCubic 0.15s · synced to each word*

*Original: M-095*

Variant of M-095: نسخة ذهبية فاخرة

**Spec (EN):** An accent highlight box grows behind the spoken word from the reading-start side over 0.15s and disappears when the next word starts.

**Spec (AR):** مربع تظليل بلون الهوية يكبر ورا الكلمة اللي تنقال من جهة بداية القراءة خلال 0.15 ثانية، ويختفي لمن تبدأ الكلمة اللي بعدها.

**When to use:**
- EN: Use when you need a gold version of M-095.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-095.

#### `al-cap-095-boxed` — Highlighter Active · Boxed
**فسفوري على الكلمة الحالية · صندوق**

*accent · any · timeline · easing: easeOutCubic 0.15s · synced to each word*

*Original: M-095*

Variant of M-095: النص داخل صندوق ملون

**Spec (EN):** An accent highlight box grows behind the spoken word from the reading-start side over 0.15s and disappears when the next word starts.

**Spec (AR):** مربع تظليل بلون الهوية يكبر ورا الكلمة اللي تنقال من جهة بداية القراءة خلال 0.15 ثانية، ويختفي لمن تبدأ الكلمة اللي بعدها.

**When to use:**
- EN: Use when you need a boxed version of M-095.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-095.

#### `al-cap-096-fast` — Size Mix · Fast
**أحجام مختلفة · سريع**

*accent · any · timeline · easing: easeOutBack · 0.2s per word*

*Original: M-096*

Variant of M-096: أسرع بـ 40%

**Spec (EN):** Words pop in one by one (M-012 style), but key words are set 1.6× larger and in the accent color, so the line reads like a poster.

**Spec (AR):** الكلمات تنط وحدة وحدة (مثل M-012)، بس الكلمات المهمة أكبر بـ 1.6 مرة وبلون الهوية، فيصير السطر مثل البوستر.

**When to use:**
- EN: Use when you need a fast version of M-096.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-096.

#### `al-cap-096-slow` — Size Mix · Slow
**أحجام مختلفة · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.2s per word*

*Original: M-096*

Variant of M-096: أبطأ بـ 60%

**Spec (EN):** Words pop in one by one (M-012 style), but key words are set 1.6× larger and in the accent color, so the line reads like a poster.

**Spec (AR):** الكلمات تنط وحدة وحدة (مثل M-012)، بس الكلمات المهمة أكبر بـ 1.6 مرة وبلون الهوية، فيصير السطر مثل البوستر.

**When to use:**
- EN: Use when you need a slow version of M-096.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-096.

#### `al-cap-096-gold` — Size Mix · Gold
**أحجام مختلفة · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.2s per word*

*Original: M-096*

Variant of M-096: نسخة ذهبية فاخرة

**Spec (EN):** Words pop in one by one (M-012 style), but key words are set 1.6× larger and in the accent color, so the line reads like a poster.

**Spec (AR):** الكلمات تنط وحدة وحدة (مثل M-012)، بس الكلمات المهمة أكبر بـ 1.6 مرة وبلون الهوية، فيصير السطر مثل البوستر.

**When to use:**
- EN: Use when you need a gold version of M-096.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-096.

#### `al-cap-096-boxed` — Size Mix · Boxed
**أحجام مختلفة · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.2s per word*

*Original: M-096*

Variant of M-096: النص داخل صندوق ملون

**Spec (EN):** Words pop in one by one (M-012 style), but key words are set 1.6× larger and in the accent color, so the line reads like a poster.

**Spec (AR):** الكلمات تنط وحدة وحدة (مثل M-012)، بس الكلمات المهمة أكبر بـ 1.6 مرة وبلون الهوية، فيصير السطر مثل البوستر.

**When to use:**
- EN: Use when you need a boxed version of M-096.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-096.

#### `al-cap-097-fast` — Speaker Label · Fast
**اسم المتكلم · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.3s*

*Original: M-097*

Variant of M-097: أسرع بـ 40%

**Spec (EN):** A small accent tag with the speaker name slides in above the caption 0.1s before the line, then the caption fades up under it.

**Spec (AR):** تاق صغير بلون الهوية فيه اسم المتكلم يدخل فوق الكابشن قبل السطر بـ 0.1 ثانية، وبعدين الكابشن يطلع تحته.

**When to use:**
- EN: Use when you need a fast version of M-097.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-097.

#### `al-cap-097-slow` — Speaker Label · Slow
**اسم المتكلم · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.3s*

*Original: M-097*

Variant of M-097: أبطأ بـ 60%

**Spec (EN):** A small accent tag with the speaker name slides in above the caption 0.1s before the line, then the caption fades up under it.

**Spec (AR):** تاق صغير بلون الهوية فيه اسم المتكلم يدخل فوق الكابشن قبل السطر بـ 0.1 ثانية، وبعدين الكابشن يطلع تحته.

**When to use:**
- EN: Use when you need a slow version of M-097.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-097.

#### `al-cap-097-gold` — Speaker Label · Gold
**اسم المتكلم · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.3s*

*Original: M-097*

Variant of M-097: نسخة ذهبية فاخرة

**Spec (EN):** A small accent tag with the speaker name slides in above the caption 0.1s before the line, then the caption fades up under it.

**Spec (AR):** تاق صغير بلون الهوية فيه اسم المتكلم يدخل فوق الكابشن قبل السطر بـ 0.1 ثانية، وبعدين الكابشن يطلع تحته.

**When to use:**
- EN: Use when you need a gold version of M-097.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-097.

#### `al-cap-097-boxed` — Speaker Label · Boxed
**اسم المتكلم · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.3s*

*Original: M-097*

Variant of M-097: النص داخل صندوق ملون

**Spec (EN):** A small accent tag with the speaker name slides in above the caption 0.1s before the line, then the caption fades up under it.

**Spec (AR):** تاق صغير بلون الهوية فيه اسم المتكلم يدخل فوق الكابشن قبل السطر بـ 0.1 ثانية، وبعدين الكابشن يطلع تحته.

**When to use:**
- EN: Use when you need a boxed version of M-097.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-097.

#### `al-cap-098-fast` — Bottom Bar Caption · Fast
**شريط سفلي · سريع**

*accent · any · timeline · easing: easeOutExpo · 0.4s bar · 0.3s text*

*Original: M-098*

Variant of M-098: أسرع بـ 40%

**Spec (EN):** A dark full-width bar grows from the right edge (0.4s), then the caption fades in inside it (0.3s). Text and bar retract at the end.

**Spec (AR):** شريط غامق بعرض الشاشة يطلع من الحافة اليمين (0.4 ثانية)، وبعدين الكابشن يظهر داخله (0.3 ثانية). والنص والشريط ينسحبون بالنهاية.

**When to use:**
- EN: Use when you need a fast version of M-098.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-098.

#### `al-cap-098-slow` — Bottom Bar Caption · Slow
**شريط سفلي · بطيء**

*accent · any · timeline · easing: easeOutExpo · 0.4s bar · 0.3s text*

*Original: M-098*

Variant of M-098: أبطأ بـ 60%

**Spec (EN):** A dark full-width bar grows from the right edge (0.4s), then the caption fades in inside it (0.3s). Text and bar retract at the end.

**Spec (AR):** شريط غامق بعرض الشاشة يطلع من الحافة اليمين (0.4 ثانية)، وبعدين الكابشن يظهر داخله (0.3 ثانية). والنص والشريط ينسحبون بالنهاية.

**When to use:**
- EN: Use when you need a slow version of M-098.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-098.

#### `al-cap-098-gold` — Bottom Bar Caption · Gold
**شريط سفلي · ذهبي**

*accent · any · timeline · easing: easeOutExpo · 0.4s bar · 0.3s text*

*Original: M-098*

Variant of M-098: نسخة ذهبية فاخرة

**Spec (EN):** A dark full-width bar grows from the right edge (0.4s), then the caption fades in inside it (0.3s). Text and bar retract at the end.

**Spec (AR):** شريط غامق بعرض الشاشة يطلع من الحافة اليمين (0.4 ثانية)، وبعدين الكابشن يظهر داخله (0.3 ثانية). والنص والشريط ينسحبون بالنهاية.

**When to use:**
- EN: Use when you need a gold version of M-098.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-098.

#### `al-cap-098-boxed` — Bottom Bar Caption · Boxed
**شريط سفلي · صندوق**

*accent · any · timeline · easing: easeOutExpo · 0.4s bar · 0.3s text*

*Original: M-098*

Variant of M-098: النص داخل صندوق ملون

**Spec (EN):** A dark full-width bar grows from the right edge (0.4s), then the caption fades in inside it (0.3s). Text and bar retract at the end.

**Spec (AR):** شريط غامق بعرض الشاشة يطلع من الحافة اليمين (0.4 ثانية)، وبعدين الكابشن يظهر داخله (0.3 ثانية). والنص والشريط ينسحبون بالنهاية.

**When to use:**
- EN: Use when you need a boxed version of M-098.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-098.

#### `al-cap-099-fast` — Glitch Caption · Fast
**كابشن جلتش · سريع**

*accent · any · timeline · easing: steps · 0.4s glitch*

*Original: M-099*

Variant of M-099: أسرع بـ 40%

**Spec (EN):** The caption enters with a 0.4s glitch burst: red and cyan copies jitter through random slice masks, then the line snaps clean (see M-010).

**Spec (AR):** الكابشن يدخل مع رجفة جلتش 0.4 ثانية: نسخة حمرا ونسخة سماوية ترجف داخل شرائح عشوائية، وبعدين السطر يثبت نظيف (شوف M-010).

**When to use:**
- EN: Use when you need a fast version of M-099.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-099.

#### `al-cap-099-slow` — Glitch Caption · Slow
**كابشن جلتش · بطيء**

*accent · any · timeline · easing: steps · 0.4s glitch*

*Original: M-099*

Variant of M-099: أبطأ بـ 60%

**Spec (EN):** The caption enters with a 0.4s glitch burst: red and cyan copies jitter through random slice masks, then the line snaps clean (see M-010).

**Spec (AR):** الكابشن يدخل مع رجفة جلتش 0.4 ثانية: نسخة حمرا ونسخة سماوية ترجف داخل شرائح عشوائية، وبعدين السطر يثبت نظيف (شوف M-010).

**When to use:**
- EN: Use when you need a slow version of M-099.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-099.

#### `al-cap-099-gold` — Glitch Caption · Gold
**كابشن جلتش · ذهبي**

*accent · any · timeline · easing: steps · 0.4s glitch*

*Original: M-099*

Variant of M-099: نسخة ذهبية فاخرة

**Spec (EN):** The caption enters with a 0.4s glitch burst: red and cyan copies jitter through random slice masks, then the line snaps clean (see M-010).

**Spec (AR):** الكابشن يدخل مع رجفة جلتش 0.4 ثانية: نسخة حمرا ونسخة سماوية ترجف داخل شرائح عشوائية، وبعدين السطر يثبت نظيف (شوف M-010).

**When to use:**
- EN: Use when you need a gold version of M-099.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-099.

#### `al-cap-099-boxed` — Glitch Caption · Boxed
**كابشن جلتش · صندوق**

*accent · any · timeline · easing: steps · 0.4s glitch*

*Original: M-099*

Variant of M-099: النص داخل صندوق ملون

**Spec (EN):** The caption enters with a 0.4s glitch burst: red and cyan copies jitter through random slice masks, then the line snaps clean (see M-010).

**Spec (AR):** الكابشن يدخل مع رجفة جلتش 0.4 ثانية: نسخة حمرا ونسخة سماوية ترجف داخل شرائح عشوائية، وبعدين السطر يثبت نظيف (شوف M-010).

**When to use:**
- EN: Use when you need a boxed version of M-099.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-099.

#### `al-cap-100-fast` — Progress Caption · Fast
**كابشن مع شريط تقدم · سريع**

*accent · calm · timeline · easing: linear · sentence length*

*Original: M-100*

Variant of M-100: أسرع بـ 40%

**Spec (EN):** Under the caption, a thin rounded accent bar fills from the reading-start side across the sentence duration, showing how long the line lasts.

**Spec (AR):** تحت الكابشن شريط رفيع بلون الهوية يتعبى من جهة بداية القراءة على طول مدة الجملة، فيبين كم باقي على السطر.

**When to use:**
- EN: Use when you need a fast version of M-100.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-100.

#### `al-cap-100-slow` — Progress Caption · Slow
**كابشن مع شريط تقدم · بطيء**

*accent · calm · timeline · easing: linear · sentence length*

*Original: M-100*

Variant of M-100: أبطأ بـ 60%

**Spec (EN):** Under the caption, a thin rounded accent bar fills from the reading-start side across the sentence duration, showing how long the line lasts.

**Spec (AR):** تحت الكابشن شريط رفيع بلون الهوية يتعبى من جهة بداية القراءة على طول مدة الجملة، فيبين كم باقي على السطر.

**When to use:**
- EN: Use when you need a slow version of M-100.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-100.

#### `al-cap-100-gold` — Progress Caption · Gold
**كابشن مع شريط تقدم · ذهبي**

*accent · calm · timeline · easing: linear · sentence length*

*Original: M-100*

Variant of M-100: نسخة ذهبية فاخرة

**Spec (EN):** Under the caption, a thin rounded accent bar fills from the reading-start side across the sentence duration, showing how long the line lasts.

**Spec (AR):** تحت الكابشن شريط رفيع بلون الهوية يتعبى من جهة بداية القراءة على طول مدة الجملة، فيبين كم باقي على السطر.

**When to use:**
- EN: Use when you need a gold version of M-100.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-100.

#### `al-cap-100-boxed` — Progress Caption · Boxed
**كابشن مع شريط تقدم · صندوق**

*accent · calm · timeline · easing: linear · sentence length*

*Original: M-100*

Variant of M-100: النص داخل صندوق ملون

**Spec (EN):** Under the caption, a thin rounded accent bar fills from the reading-start side across the sentence duration, showing how long the line lasts.

**Spec (AR):** تحت الكابشن شريط رفيع بلون الهوية يتعبى من جهة بداية القراءة على طول مدة الجملة، فيبين كم باقي على السطر.

**When to use:**
- EN: Use when you need a boxed version of M-100.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-100.

#### `al-cap-272-fast` — Bilingual Caption · Fast
**كابشن بلغتين · سريع**

*accent · any · timeline · easing: easeOutCubic · synced*

*Original: M-272*

Variant of M-272: أسرع بـ 40%

**Spec (EN):** Show the Arabic caption in the main style and its English translation under it in a smaller lighter line; both enter together.

**Spec (AR):** اعرض الكابشن العربي بالستايل الأساسي، وتحته الترجمة الإنجليزية بسطر أصغر وأفتح، والاثنين يدخلون مع بعض.

**When to use:**
- EN: Use when you need a fast version of M-272.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-272.

#### `al-cap-272-slow` — Bilingual Caption · Slow
**كابشن بلغتين · بطيء**

*accent · any · timeline · easing: easeOutCubic · synced*

*Original: M-272*

Variant of M-272: أبطأ بـ 60%

**Spec (EN):** Show the Arabic caption in the main style and its English translation under it in a smaller lighter line; both enter together.

**Spec (AR):** اعرض الكابشن العربي بالستايل الأساسي، وتحته الترجمة الإنجليزية بسطر أصغر وأفتح، والاثنين يدخلون مع بعض.

**When to use:**
- EN: Use when you need a slow version of M-272.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-272.

#### `al-cap-272-gold` — Bilingual Caption · Gold
**كابشن بلغتين · ذهبي**

*accent · any · timeline · easing: easeOutCubic · synced*

*Original: M-272*

Variant of M-272: نسخة ذهبية فاخرة

**Spec (EN):** Show the Arabic caption in the main style and its English translation under it in a smaller lighter line; both enter together.

**Spec (AR):** اعرض الكابشن العربي بالستايل الأساسي، وتحته الترجمة الإنجليزية بسطر أصغر وأفتح، والاثنين يدخلون مع بعض.

**When to use:**
- EN: Use when you need a gold version of M-272.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-272.

#### `al-cap-272-boxed` — Bilingual Caption · Boxed
**كابشن بلغتين · صندوق**

*accent · any · timeline · easing: easeOutCubic · synced*

*Original: M-272*

Variant of M-272: النص داخل صندوق ملون

**Spec (EN):** Show the Arabic caption in the main style and its English translation under it in a smaller lighter line; both enter together.

**Spec (AR):** اعرض الكابشن العربي بالستايل الأساسي، وتحته الترجمة الإنجليزية بسطر أصغر وأفتح، والاثنين يدخلون مع بعض.

**When to use:**
- EN: Use when you need a boxed version of M-272.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-272.

#### `al-cap-273-fast` — Text on Path · Fast
**نص على مسار · سريع**

*accent · calm · timeline · easing: linear · loop*

*Original: M-273*

Variant of M-273: أسرع بـ 40%

**Spec (EN):** Lay the caption along a curved SVG path and slide its start offset so the words travel along the curve.

**Spec (AR):** حط الكابشن على مسار SVG منحني، وحرّك نقطة بدايته فالكلمات تمشي على المنحنى.

**When to use:**
- EN: Use when you need a fast version of M-273.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-273.

#### `al-cap-273-slow` — Text on Path · Slow
**نص على مسار · بطيء**

*accent · calm · timeline · easing: linear · loop*

*Original: M-273*

Variant of M-273: أبطأ بـ 60%

**Spec (EN):** Lay the caption along a curved SVG path and slide its start offset so the words travel along the curve.

**Spec (AR):** حط الكابشن على مسار SVG منحني، وحرّك نقطة بدايته فالكلمات تمشي على المنحنى.

**When to use:**
- EN: Use when you need a slow version of M-273.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-273.

#### `al-cap-273-gold` — Text on Path · Gold
**نص على مسار · ذهبي**

*accent · calm · timeline · easing: linear · loop*

*Original: M-273*

Variant of M-273: نسخة ذهبية فاخرة

**Spec (EN):** Lay the caption along a curved SVG path and slide its start offset so the words travel along the curve.

**Spec (AR):** حط الكابشن على مسار SVG منحني، وحرّك نقطة بدايته فالكلمات تمشي على المنحنى.

**When to use:**
- EN: Use when you need a gold version of M-273.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-273.

#### `al-cap-273-boxed` — Text on Path · Boxed
**نص على مسار · صندوق**

*accent · calm · timeline · easing: linear · loop*

*Original: M-273*

Variant of M-273: النص داخل صندوق ملون

**Spec (EN):** Lay the caption along a curved SVG path and slide its start offset so the words travel along the curve.

**Spec (AR):** حط الكابشن على مسار SVG منحني، وحرّك نقطة بدايته فالكلمات تمشي على المنحنى.

**When to use:**
- EN: Use when you need a boxed version of M-273.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-273.

#### `al-cap-274-fast` — Full-Screen Kinetic · Fast
**كلمات تملا الشاشة · سريع**

*accent · any · depth · easing: cut · per word*

*Original: M-274*

Variant of M-274: أسرع بـ 40%

**Spec (EN):** Each word fills most of the frame in a bold display font and replaces the previous one on its timestamp, alternating background and text colors.

**Spec (AR):** كل كلمة تملا أغلب الشاشة بخط عريض، وتحل محل اللي قبلها وقت نطقها، والألوان تتبدل بين الخلفية والنص.

**When to use:**
- EN: Use when you need a fast version of M-274.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-274.

#### `al-cap-274-slow` — Full-Screen Kinetic · Slow
**كلمات تملا الشاشة · بطيء**

*accent · any · depth · easing: cut · per word*

*Original: M-274*

Variant of M-274: أبطأ بـ 60%

**Spec (EN):** Each word fills most of the frame in a bold display font and replaces the previous one on its timestamp, alternating background and text colors.

**Spec (AR):** كل كلمة تملا أغلب الشاشة بخط عريض، وتحل محل اللي قبلها وقت نطقها، والألوان تتبدل بين الخلفية والنص.

**When to use:**
- EN: Use when you need a slow version of M-274.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-274.

#### `al-cap-274-gold` — Full-Screen Kinetic · Gold
**كلمات تملا الشاشة · ذهبي**

*accent · any · depth · easing: cut · per word*

*Original: M-274*

Variant of M-274: نسخة ذهبية فاخرة

**Spec (EN):** Each word fills most of the frame in a bold display font and replaces the previous one on its timestamp, alternating background and text colors.

**Spec (AR):** كل كلمة تملا أغلب الشاشة بخط عريض، وتحل محل اللي قبلها وقت نطقها، والألوان تتبدل بين الخلفية والنص.

**When to use:**
- EN: Use when you need a gold version of M-274.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-274.

#### `al-cap-274-boxed` — Full-Screen Kinetic · Boxed
**كلمات تملا الشاشة · صندوق**

*accent · any · depth · easing: cut · per word*

*Original: M-274*

Variant of M-274: النص داخل صندوق ملون

**Spec (EN):** Each word fills most of the frame in a bold display font and replaces the previous one on its timestamp, alternating background and text colors.

**Spec (AR):** كل كلمة تملا أغلب الشاشة بخط عريض، وتحل محل اللي قبلها وقت نطقها، والألوان تتبدل بين الخلفية والنص.

**When to use:**
- EN: Use when you need a boxed version of M-274.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-274.

#### `al-cap-275-fast` — Tagged Caption · Fast
**كابشن مع تاق · سريع**

*accent · any · timeline · easing: easeOutBack · 0.3s*

*Original: M-275*

Variant of M-275: أسرع بـ 40%

**Spec (EN):** The caption pops in (M-089) with its first word inside a small accent box, like a label, followed by the rest of the line.

**Spec (AR):** الكابشن ينط (M-089) وأول كلمة فيه داخل مربع صغير بلون الهوية مثل التاق، وبعدها باقي السطر.

**When to use:**
- EN: Use when you need a fast version of M-275.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-275.

#### `al-cap-275-slow` — Tagged Caption · Slow
**كابشن مع تاق · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.3s*

*Original: M-275*

Variant of M-275: أبطأ بـ 60%

**Spec (EN):** The caption pops in (M-089) with its first word inside a small accent box, like a label, followed by the rest of the line.

**Spec (AR):** الكابشن ينط (M-089) وأول كلمة فيه داخل مربع صغير بلون الهوية مثل التاق، وبعدها باقي السطر.

**When to use:**
- EN: Use when you need a slow version of M-275.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-275.

#### `al-cap-275-gold` — Tagged Caption · Gold
**كابشن مع تاق · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.3s*

*Original: M-275*

Variant of M-275: نسخة ذهبية فاخرة

**Spec (EN):** The caption pops in (M-089) with its first word inside a small accent box, like a label, followed by the rest of the line.

**Spec (AR):** الكابشن ينط (M-089) وأول كلمة فيه داخل مربع صغير بلون الهوية مثل التاق، وبعدها باقي السطر.

**When to use:**
- EN: Use when you need a gold version of M-275.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-275.

#### `al-cap-275-boxed` — Tagged Caption · Boxed
**كابشن مع تاق · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.3s*

*Original: M-275*

Variant of M-275: النص داخل صندوق ملون

**Spec (EN):** The caption pops in (M-089) with its first word inside a small accent box, like a label, followed by the rest of the line.

**Spec (AR):** الكابشن ينط (M-089) وأول كلمة فيه داخل مربع صغير بلون الهوية مثل التاق، وبعدها باقي السطر.

**When to use:**
- EN: Use when you need a boxed version of M-275.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-275.

### Transitions (Alansari) (الانتقالات) — 150 motions

#### `al-trn-016` — Circle Reveal
**انكشاف دائري**

*workhorse · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-016*

Swap the background or scene from a point, like your finger or face.

**Spec (EN):** The new scene is revealed through a circular mask that grows from a chosen point (e.g. a fingertip) from radius 0 to full-frame diagonal over 0.6s, with a 30px soft edge. A thin accent ring expands just ahead of the edge and fades out.

**Spec (AR):** المشهد الجديد ينكشف من دائرة تكبر من نقطة تختارها (مثل طرف الإصبع) من نصف قطر 0 لين تغطي الشاشة كاملة خلال 0.6 ثانية، وحافتها ناعمة 30px. وحلقة رفيعة بلون الهوية تكبر قدام الحافة شوي وتختفي.

**When to use:**
- EN: Swap the background or scene from a point, like your finger or face.
- AR: تغيير الخلفية أو المشهد من نقطة، مثل إصبعك أو وجهك.

#### `al-trn-017` — Linear Wipe
**مسح خطي**

*workhorse · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-017*

A clear transition between two clips or places.

**Spec (EN):** The new scene wipes in across the frame behind a moving vertical edge over 0.5s. The edge has a white 4px line with an accent glow.

**Spec (AR):** المشهد الجديد يمسح الشاشة ورا حافة عمودية تتحرك خلال 0.5 ثانية. الحافة خط أبيض 4px مع توهج بلون الهوية.

**When to use:**
- EN: A clear transition between two clips or places.
- AR: انتقال واضح بين مقطعين أو مكانين.

#### `al-trn-018` — Light Sweep
**شعاع ضوء يمسح**

*workhorse · calm · timeline · easing: easeInOutSine · 0.7s*

*Original: M-018*

A magic change, like "look how it changed".

**Spec (EN):** A bright warm diagonal light band (about 15% of the frame wide, angled 105°) sweeps across the frame over 0.7s. The scene swaps to the new one exactly as the band passes the center.

**Spec (AR):** شعاع ضوء دافي مايل (عرضه تقريباً 15% من الشاشة وزاويته 105 درجات) يمسح الشاشة خلال 0.7 ثانية، والمشهد يتبدل للجديد بالضبط لمن يعدي الشعاع نص الشاشة.

**When to use:**
- EN: A magic change, like "look how it changed".
- AR: تحوّل سحري، مثل "شوف شلون تغيّرت".

#### `al-trn-019` — Zoom Blur
**زوم مع ضبابية**

*workhorse · any · blur · easing: easeInExpo / easeOutExpo · 0.4s out · 0.4s in*

*Original: M-019*

A fast, punchy cut between two clips.

**Spec (EN):** The outgoing clip scales to 170% with a radial blur of about 10px and fades out over 0.4s (easeInExpo). The incoming clip starts at 160% blurred and settles to 100% sharp over 0.4s (easeOutExpo).

**Spec (AR):** المقطع الطالع يكبر لـ 170% مع ضبابية تقريباً 10px ويختفي خلال 0.4 ثانية (easeInExpo). والمقطع الداخل يبدأ من 160% مضبب ويستقر على 100% واضح خلال 0.4 ثانية (easeOutExpo).

**When to use:**
- EN: A fast, punchy cut between two clips.
- AR: انتقال سريع وقوي بين مقطعين.

#### `al-trn-020` — Whip Pan
**سحبة سريعة**

*workhorse · any · blur · easing: easeInOutQuart · 0.35s*

*Original: M-020*

Cut between two shots as if the camera spun.

**Spec (EN):** The outgoing clip slides out to one side with heavy horizontal motion blur, and the incoming clip slides in from the opposite side over 0.35s total. Add a fast "whoosh" sound.

**Spec (AR):** المقطع الطالع ينسحب لجهة مع ضبابية حركة أفقية قوية، والداخل يدخل من الجهة الثانية، والمجموع 0.35 ثانية. حط معاه صوت "ووش" سريع.

**When to use:**
- EN: Cut between two shots as if the camera spun.
- AR: انتقال بين لقطتين كأن الكاميرا التفتت.

#### `al-trn-101` — Fade Through Black
**تلاشي للأسود**

*workhorse · calm · timeline · easing: easeInOutSine · 0.3s out · 0.3s in*

*Original: M-101*

A calm transition through a moment of black.

**Spec (EN):** The outgoing clip fades to full black over 0.3s, holds black for 2–4 frames, then the new clip fades in from black over 0.3s.

**Spec (AR):** المقطع الطالع يختفي لأسود كامل خلال 0.3 ثانية، يثبت الأسود 2 إلى 4 فريمات، وبعدين المقطع الجديد يظهر من الأسود خلال 0.3 ثانية.

**When to use:**
- EN: A calm transition through a moment of black.
- AR: انتقال هادي بين مشهدين مع لحظة سواد.

#### `al-trn-102` — Cross Dissolve
**ذوبان بين مشهدين**

*workhorse · calm · timeline · easing: linear · 0.5s*

*Original: M-102*

The classic soft blend from one shot into the next.

**Spec (EN):** The new clip fades in on top of the old one from 0 to 100% over 0.5s while both play.

**Spec (AR):** المقطع الجديد يظهر فوق القديم من 0 لـ 100% خلال 0.5 ثانية والاثنين شغالين.

**When to use:**
- EN: The classic soft blend from one shot into the next.
- AR: انتقال ناعم كلاسيكي، المشهد يذوب بالثاني.

#### `al-trn-103` — Slide Push
**دفع المشهد**

*workhorse · any · timeline · easing: easeInOutQuart · 0.45s*

*Original: M-103*

The new shot pushes the old one off screen.

**Spec (EN):** The new clip slides in from the right edge while pushing the old clip out to the left at the same speed over 0.45s.

**Spec (AR):** المقطع الجديد يدخل من الحافة اليمين وهو يدفع القديم لبرا من اليسار بنفس السرعة خلال 0.45 ثانية.

**When to use:**
- EN: The new shot pushes the old one off screen.
- AR: المشهد الجديد يدفع القديم لبرا.

#### `al-trn-104` — Diagonal Wipe
**مسح قطري**

*workhorse · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-104*

A slanted wipe, livelier than a straight one.

**Spec (EN):** The new clip is revealed behind a soft-edged diagonal line (135°) that travels from the top-left corner to the bottom-right over 0.5s.

**Spec (AR):** المقطع الجديد ينكشف ورا خط مايل (135 درجة) بحافة ناعمة يمشي من الزاوية الفوق يسار للزاوية التحت يمين خلال 0.5 ثانية.

**When to use:**
- EN: A slanted wipe, livelier than a straight one.
- AR: مسح مايل بين مشهدين، أكثر حركة من المسح العادي.

#### `al-trn-105` — Iris Close/Open
**دائرة تقفل وتفتح**

*workhorse · any · timeline · easing: easeInOutCubic · 0.4s close · 0.4s open*

*Original: M-105*

A circle closes on one shot and opens on the next, old-film style.

**Spec (EN):** A circular mask shrinks to zero on the face of the outgoing clip (0.4s), then the new clip opens from the same point with a growing circle (0.4s). Black between.

**Spec (AR):** قناع دائري يصغر لين يختفي على وجه المقطع الطالع (0.4 ثانية)، وبعدين المقطع الجديد ينفتح من نفس النقطة بدائرة تكبر (0.4 ثانية). وبينهم أسود.

**When to use:**
- EN: A circle closes on one shot and opens on the next, old-film style.
- AR: دائرة تقفل على المشهد وتفتح على الثاني، ستايل الأفلام القديمة.

#### `al-trn-106` — Clock Wipe
**مسح مثل الساعة**

*workhorse · calm · timeline · easing: easeInOutSine · 0.6s*

*Original: M-106*

The new shot sweeps in like a clock hand.

**Spec (EN):** The new clip is revealed by a radial sweep around the center, starting at 12 o clock and going clockwise a full 360° over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف بمسحة دائرية حول النص، تبدأ من الساعة 12 وتمشي مع عقارب الساعة 360 درجة كاملة خلال 0.6 ثانية.

**When to use:**
- EN: The new shot sweeps in like a clock hand.
- AR: المشهد الجديد يطلع مثل عقرب الساعة.

#### `al-trn-107` — Blinds
**ستائر**

*workhorse · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-107*

The new shot opens through vertical blinds.

**Spec (EN):** The frame is split into 6 vertical strips. Each strip reveals the new clip by growing from its right edge to full width over 0.5s.

**Spec (AR):** الشاشة مقسومة 6 شرائح عمودية. كل شريحة تكشف المقطع الجديد وهي تكبر من حافتها لين تغطي عرضها خلال 0.5 ثانية.

**When to use:**
- EN: The new shot opens through vertical blinds.
- AR: المشهد الجديد يطلع من شرائح مثل الستارة.

#### `al-trn-108` — Split Doors
**أبواب تنفتح**

*workhorse · any · timeline · easing: easeInOutQuart · 0.6s*

*Original: M-108*

The shot splits in half and opens like doors.

**Spec (EN):** The outgoing clip is cut down the middle; the two halves slide apart to the left and right over 0.6s, revealing the new clip behind them.

**Spec (AR):** المقطع الطالع ينقص من النص، والنصين يتحركون يمين ويسار خلال 0.6 ثانية ويكشفون المقطع الجديد وراهم.

**When to use:**
- EN: The shot splits in half and opens like doors.
- AR: المشهد ينقسم نصين وينفتح مثل الباب.

#### `al-trn-109` — Diamond Reveal
**انكشاف ماسي**

*workhorse · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-109*

The new shot opens from a growing diamond.

**Spec (EN):** The new clip is revealed through a diamond-shaped mask that grows from the face point until it covers the frame over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف من قناع بشكل معيّن يكبر من نقطة الوجه لين يغطي الشاشة خلال 0.6 ثانية.

**When to use:**
- EN: The new shot opens from a growing diamond.
- AR: المشهد الجديد يطلع من شكل معين يكبر.

#### `al-trn-110` — Glitch Transition
**انتقال جلتش**

*workhorse · any · timeline · easing: steps · 0.4s*

*Original: M-110*

A glitchy cut, great for cyber content.

**Spec (EN):** For 0.4s the new clip flashes in through random horizontal slices with ±8% offsets, changing every 2 frames, then locks in clean. Add a digital noise sound.

**Spec (AR):** لمدة 0.4 ثانية المقطع الجديد يومض من شرائح أفقية عشوائية بإزاحة ±8% تتغير كل فريمين، وبعدين يثبت نظيف. حط معاه صوت تشويش رقمي.

**When to use:**
- EN: A glitchy cut, great for cyber content.
- AR: انتقال تقني يرجف، يناسب المحتوى السيبراني.

#### `al-trn-111` — Spin Transition
**انتقال بدوران**

*workhorse · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-111*

The old shot spins out, the new one spins in.

**Spec (EN):** The outgoing clip rotates 180° while shrinking to 20% and fading out; the new clip rotates in from -180° and 20% to full size over 0.5s.

**Spec (AR):** المقطع الطالع يلف 180 درجة وهو يصغر لـ 20% ويختفي، والجديد يلف من -180 درجة و20% لين حجمه الكامل خلال 0.5 ثانية.

**When to use:**
- EN: The old shot spins out, the new one spins in.
- AR: المشهد يلف ويختفي والثاني يلف ويدخل.

#### `al-trn-112` — Flash White
**وميض أبيض للانتقال**

*workhorse · any · timeline · easing: easeOut · 0.25s*

*Original: M-112*

A cut hidden in a white flash, bold and sudden.

**Spec (EN):** A full white flash peaks in 2 frames exactly on the cut, then fades over 0.25s to reveal the new clip.

**Spec (AR):** وميض أبيض كامل يوصل قمته خلال فريمين بالضبط عند القص، وبعدين يختفي خلال 0.25 ثانية ويكشف المقطع الجديد.

**When to use:**
- EN: A cut hidden in a white flash, bold and sudden.
- AR: قص بوميض أبيض، قوي ومفاجئ.

#### `al-trn-113` — Color Flash
**وميض بلون الهوية**

*workhorse · any · timeline · easing: easeOut · 0.3s*

*Original: M-113*

A cut hidden in a brand-color flash.

**Spec (EN):** Same as M-112 but the flash is the brand accent color at 90% opacity.

**Spec (AR):** نفس M-112 بس الوميض بلون الهوية وشفافيته 90%.

**When to use:**
- EN: A cut hidden in a brand-color flash.
- AR: قص بوميض بلون البراند.

#### `al-trn-114` — Corner Reveal
**انكشاف من الزاوية**

*workhorse · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-114*

The new shot grows in from a corner.

**Spec (EN):** The new clip is revealed through a circle that grows from the bottom-left corner until it covers the frame over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف من دائرة تكبر من الزاوية التحت يسار لين تغطي الشاشة خلال 0.6 ثانية.

**When to use:**
- EN: The new shot grows in from a corner.
- AR: المشهد الجديد يطلع من زاوية الشاشة.

#### `al-trn-115` — Cube Rotate
**مكعب يلف**

*workhorse · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-115*

The two shots act as faces of a rotating cube.

**Spec (EN):** With 3D perspective, the outgoing clip rotates 90° away on its left edge while the new clip rotates in from -90° on its right edge, like a turning cube, over 0.6s.

**Spec (AR):** مع عمق 3D، المقطع الطالع يلف 90 درجة لبعيد على حافته اليسار، والجديد يلف من -90 درجة على حافته اليمين، مثل مكعب يلف، خلال 0.6 ثانية.

**When to use:**
- EN: The two shots act as faces of a rotating cube.
- AR: المشهدين كأنهم وجهين مكعب يلف.

#### `al-trn-116` — Zoom Through
**زوم داخل المشهد**

*workhorse · any · timeline · easing: easeInExpo / easeOutCubic · 0.5s*

*Original: M-116*

The camera dives into one shot and comes out in the next.

**Spec (EN):** The outgoing clip scales to 400% and fades out quickly (0.3s); the new clip grows from 60% to 100% while fading in (0.3s), overlapping slightly.

**Spec (AR):** المقطع الطالع يكبر لـ 400% ويختفي بسرعة (0.3 ثانية)، والجديد يكبر من 60% لـ 100% وهو يظهر (0.3 ثانية)، ويتداخلون شوي.

**When to use:**
- EN: The camera dives into one shot and comes out in the next.
- AR: الكاميرا كأنها تدخل داخل المشهد وتطلع بالثاني.

#### `al-trn-117` — Strip Slide
**شرائح تنزلق**

*workhorse · any · timeline · easing: easeOutQuart · 0.5s · 0.06s stagger*

*Original: M-117*

The new shot slides in as horizontal strips, one after another.

**Spec (EN):** The new clip is cut into 5 horizontal strips; each strip slides in from the right over 0.5s, starting 0.06s after the one above it.

**Spec (AR):** المقطع الجديد مقسوم 5 شرائح أفقية، وكل شريحة تنزلق من اليمين خلال 0.5 ثانية، وتبدأ بعد اللي فوقها بـ 0.06 ثانية.

**When to use:**
- EN: The new shot slides in as horizontal strips, one after another.
- AR: المشهد الجديد يدخل شرائح أفقية ورا بعض.

#### `al-trn-118` — Light Leak
**تسرب ضوء**

*workhorse · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-118*

A warm light leak washes over the cut, film style.

**Spec (EN):** Warm orange and red light blobs (screen blend) drift across the frame over 0.8s; the cut to the new clip happens at the brightest moment.

**Spec (AR):** بقع ضوء دافية برتقالي وأحمر (دمج screen) تمر على الشاشة خلال 0.8 ثانية، والقص للمقطع الجديد يصير بأكثر لحظة إضاءة.

**When to use:**
- EN: A warm light leak washes over the cut, film style.
- AR: ضوء دافي يمر على الشاشة ويغطي القص، ستايل الأفلام.

#### `al-trn-119` — Smooth Cut
**قص ناعم**

*workhorse · any · timeline · easing: easeOutQuad · 0.3s*

*Original: M-119*

A cut between similar shots that hides the jump.

**Spec (EN):** The new clip fades in over 0.3s while scaling from 105% to 100%, which hides small position jumps between two similar takes.

**Spec (AR):** المقطع الجديد يظهر خلال 0.3 ثانية وهو يصغر من 105% لـ 100%، وهذا يخفي النطة الصغيرة بين لقطتين متشابهتين.

**When to use:**
- EN: A cut between similar shots that hides the jump.
- AR: قص بين لقطتين متشابهتين بدون ما يبين.

#### `al-trn-120` — Swipe Up
**سحب لفوق**

*workhorse · any · depth · easing: easeInOutQuart · 0.4s*

*Original: M-120*

Like swiping a story up to the next clip.

**Spec (EN):** The outgoing clip slides up out of the top edge while the new clip slides up from the bottom edge at the same speed over 0.4s.

**Spec (AR):** المقطع الطالع يطلع لفوق من الحافة الفوق، والجديد يطلع من الحافة التحت بنفس السرعة خلال 0.4 ثانية.

**When to use:**
- EN: Like swiping a story up to the next clip.
- AR: مثل ما تسحب الستوري لفوق للمقطع اللي بعده.

#### `al-trn-267` — Shape Morph
**شكل يتحول**

*workhorse · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-267*

A shape morphs smoothly into another.

**Spec (EN):** Interpolate between shapes (circle → rounded square → leaf) by animating corner radii and rotation, or by morphing matching SVG paths.

**Spec (AR):** انتقل بين الأشكال (دائرة ثم مربع دائري ثم ورقة) بتحريك الزوايا والدوران، أو بتحويل مسارات SVG متطابقة.

**When to use:**
- EN: A shape morphs smoothly into another.
- AR: شكل يتحول لشكل ثاني بنعومة.

#### `al-trn-268` — Liquid Reveal
**انكشاف سائل**

*workhorse · any · timeline · easing: easeInOutCubic · 0.7s*

*Original: M-268*

A liquid blob grows to cover the cut.

**Spec (EN):** An organic blob shape in the accent color grows from the center while its border radius wobbles, covers the frame, then fades to reveal the new clip.

**Spec (AR):** بقعة بشكل طبيعي بلون الهوية تكبر من النص وحوافها تتموج، تغطي الشاشة، وبعدين تختفي وتكشف المقطع الجديد.

**When to use:**
- EN: A liquid blob grows to cover the cut.
- AR: بقعة سائلة تكبر وتغطي المشهد للانتقال.

#### `al-trn-269` — Ink Splash Reveal
**انكشاف بقعة حبر**

*workhorse · any · timeline · easing: easeOutCubic · 0.7s*

*Original: M-269*

The new shot appears through growing ink splashes.

**Spec (EN):** Reveal the new clip through a mask of several overlapping circles (ink splash shape) that scales up from the center to cover the frame.

**Spec (AR):** اكشف المقطع الجديد من قناع فيه كم دائرة متداخلة (شكل بقعة حبر) يكبر من النص لين يغطي الشاشة.

**When to use:**
- EN: The new shot appears through growing ink splashes.
- AR: المشهد الجديد يطلع من بقع حبر تكبر.

#### `al-trn-270` — Film Burn
**حرق فيلم**

*workhorse · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-270*

A hot film-burn flare hides the cut.

**Spec (EN):** A bright white-yellow-orange burn blob expands from one corner (screen blend), peaks at full brightness on the cut, then fades.

**Spec (AR):** بقعة حرق لامعة أبيض وأصفر وبرتقالي تكبر من زاوية (دمج screen)، توصل أقوى إضاءة عند القص، وبعدين تختفي.

**When to use:**
- EN: A hot film-burn flare hides the cut.
- AR: ضوء حارق مثل الأفلام القديمة يغطي القص.

#### `al-trn-271` — Match Cut Slide
**انتقال بنفس الحركة**

*workhorse · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-271*

A movement in one shot continues in the next.

**Spec (EN):** Cut on the motion: the outgoing clip moves out in the direction of the action and the incoming clip continues the same direction and speed.

**Spec (AR):** اقطع على الحركة: المقطع الطالع يطلع باتجاه الحركة، والمقطع الداخل يكمل بنفس الاتجاه ونفس السرعة.

**When to use:**
- EN: A movement in one shot continues in the next.
- AR: حركة يدك بلقطة تكمل باللقطة اللي بعدها.

#### `al-trn-016-fast` — Circle Reveal · Fast
**انكشاف دائري · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-016*

Variant of M-016: أسرع بـ 40%

**Spec (EN):** The new scene is revealed through a circular mask that grows from a chosen point (e.g. a fingertip) from radius 0 to full-frame diagonal over 0.6s, with a 30px soft edge. A thin accent ring expands just ahead of the edge and fades out.

**Spec (AR):** المشهد الجديد ينكشف من دائرة تكبر من نقطة تختارها (مثل طرف الإصبع) من نصف قطر 0 لين تغطي الشاشة كاملة خلال 0.6 ثانية، وحافتها ناعمة 30px. وحلقة رفيعة بلون الهوية تكبر قدام الحافة شوي وتختفي.

**When to use:**
- EN: Use when you need a fast version of M-016.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-016.

#### `al-trn-016-slow` — Circle Reveal · Slow
**انكشاف دائري · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-016*

Variant of M-016: أبطأ بـ 60%

**Spec (EN):** The new scene is revealed through a circular mask that grows from a chosen point (e.g. a fingertip) from radius 0 to full-frame diagonal over 0.6s, with a 30px soft edge. A thin accent ring expands just ahead of the edge and fades out.

**Spec (AR):** المشهد الجديد ينكشف من دائرة تكبر من نقطة تختارها (مثل طرف الإصبع) من نصف قطر 0 لين تغطي الشاشة كاملة خلال 0.6 ثانية، وحافتها ناعمة 30px. وحلقة رفيعة بلون الهوية تكبر قدام الحافة شوي وتختفي.

**When to use:**
- EN: Use when you need a slow version of M-016.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-016.

#### `al-trn-016-gold` — Circle Reveal · Gold
**انكشاف دائري · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-016*

Variant of M-016: نسخة ذهبية فاخرة

**Spec (EN):** The new scene is revealed through a circular mask that grows from a chosen point (e.g. a fingertip) from radius 0 to full-frame diagonal over 0.6s, with a 30px soft edge. A thin accent ring expands just ahead of the edge and fades out.

**Spec (AR):** المشهد الجديد ينكشف من دائرة تكبر من نقطة تختارها (مثل طرف الإصبع) من نصف قطر 0 لين تغطي الشاشة كاملة خلال 0.6 ثانية، وحافتها ناعمة 30px. وحلقة رفيعة بلون الهوية تكبر قدام الحافة شوي وتختفي.

**When to use:**
- EN: Use when you need a gold version of M-016.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-016.

#### `al-trn-016-boxed` — Circle Reveal · Boxed
**انكشاف دائري · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-016*

Variant of M-016: النص داخل صندوق ملون

**Spec (EN):** The new scene is revealed through a circular mask that grows from a chosen point (e.g. a fingertip) from radius 0 to full-frame diagonal over 0.6s, with a 30px soft edge. A thin accent ring expands just ahead of the edge and fades out.

**Spec (AR):** المشهد الجديد ينكشف من دائرة تكبر من نقطة تختارها (مثل طرف الإصبع) من نصف قطر 0 لين تغطي الشاشة كاملة خلال 0.6 ثانية، وحافتها ناعمة 30px. وحلقة رفيعة بلون الهوية تكبر قدام الحافة شوي وتختفي.

**When to use:**
- EN: Use when you need a boxed version of M-016.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-016.

#### `al-trn-017-fast` — Linear Wipe · Fast
**مسح خطي · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-017*

Variant of M-017: أسرع بـ 40%

**Spec (EN):** The new scene wipes in across the frame behind a moving vertical edge over 0.5s. The edge has a white 4px line with an accent glow.

**Spec (AR):** المشهد الجديد يمسح الشاشة ورا حافة عمودية تتحرك خلال 0.5 ثانية. الحافة خط أبيض 4px مع توهج بلون الهوية.

**When to use:**
- EN: Use when you need a fast version of M-017.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-017.

#### `al-trn-017-slow` — Linear Wipe · Slow
**مسح خطي · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-017*

Variant of M-017: أبطأ بـ 60%

**Spec (EN):** The new scene wipes in across the frame behind a moving vertical edge over 0.5s. The edge has a white 4px line with an accent glow.

**Spec (AR):** المشهد الجديد يمسح الشاشة ورا حافة عمودية تتحرك خلال 0.5 ثانية. الحافة خط أبيض 4px مع توهج بلون الهوية.

**When to use:**
- EN: Use when you need a slow version of M-017.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-017.

#### `al-trn-017-gold` — Linear Wipe · Gold
**مسح خطي · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-017*

Variant of M-017: نسخة ذهبية فاخرة

**Spec (EN):** The new scene wipes in across the frame behind a moving vertical edge over 0.5s. The edge has a white 4px line with an accent glow.

**Spec (AR):** المشهد الجديد يمسح الشاشة ورا حافة عمودية تتحرك خلال 0.5 ثانية. الحافة خط أبيض 4px مع توهج بلون الهوية.

**When to use:**
- EN: Use when you need a gold version of M-017.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-017.

#### `al-trn-017-boxed` — Linear Wipe · Boxed
**مسح خطي · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-017*

Variant of M-017: النص داخل صندوق ملون

**Spec (EN):** The new scene wipes in across the frame behind a moving vertical edge over 0.5s. The edge has a white 4px line with an accent glow.

**Spec (AR):** المشهد الجديد يمسح الشاشة ورا حافة عمودية تتحرك خلال 0.5 ثانية. الحافة خط أبيض 4px مع توهج بلون الهوية.

**When to use:**
- EN: Use when you need a boxed version of M-017.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-017.

#### `al-trn-018-fast` — Light Sweep · Fast
**شعاع ضوء يمسح · سريع**

*accent · calm · timeline · easing: easeInOutSine · 0.7s*

*Original: M-018*

Variant of M-018: أسرع بـ 40%

**Spec (EN):** A bright warm diagonal light band (about 15% of the frame wide, angled 105°) sweeps across the frame over 0.7s. The scene swaps to the new one exactly as the band passes the center.

**Spec (AR):** شعاع ضوء دافي مايل (عرضه تقريباً 15% من الشاشة وزاويته 105 درجات) يمسح الشاشة خلال 0.7 ثانية، والمشهد يتبدل للجديد بالضبط لمن يعدي الشعاع نص الشاشة.

**When to use:**
- EN: Use when you need a fast version of M-018.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-018.

#### `al-trn-018-slow` — Light Sweep · Slow
**شعاع ضوء يمسح · بطيء**

*accent · calm · timeline · easing: easeInOutSine · 0.7s*

*Original: M-018*

Variant of M-018: أبطأ بـ 60%

**Spec (EN):** A bright warm diagonal light band (about 15% of the frame wide, angled 105°) sweeps across the frame over 0.7s. The scene swaps to the new one exactly as the band passes the center.

**Spec (AR):** شعاع ضوء دافي مايل (عرضه تقريباً 15% من الشاشة وزاويته 105 درجات) يمسح الشاشة خلال 0.7 ثانية، والمشهد يتبدل للجديد بالضبط لمن يعدي الشعاع نص الشاشة.

**When to use:**
- EN: Use when you need a slow version of M-018.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-018.

#### `al-trn-018-gold` — Light Sweep · Gold
**شعاع ضوء يمسح · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · 0.7s*

*Original: M-018*

Variant of M-018: نسخة ذهبية فاخرة

**Spec (EN):** A bright warm diagonal light band (about 15% of the frame wide, angled 105°) sweeps across the frame over 0.7s. The scene swaps to the new one exactly as the band passes the center.

**Spec (AR):** شعاع ضوء دافي مايل (عرضه تقريباً 15% من الشاشة وزاويته 105 درجات) يمسح الشاشة خلال 0.7 ثانية، والمشهد يتبدل للجديد بالضبط لمن يعدي الشعاع نص الشاشة.

**When to use:**
- EN: Use when you need a gold version of M-018.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-018.

#### `al-trn-018-boxed` — Light Sweep · Boxed
**شعاع ضوء يمسح · صندوق**

*accent · calm · timeline · easing: easeInOutSine · 0.7s*

*Original: M-018*

Variant of M-018: النص داخل صندوق ملون

**Spec (EN):** A bright warm diagonal light band (about 15% of the frame wide, angled 105°) sweeps across the frame over 0.7s. The scene swaps to the new one exactly as the band passes the center.

**Spec (AR):** شعاع ضوء دافي مايل (عرضه تقريباً 15% من الشاشة وزاويته 105 درجات) يمسح الشاشة خلال 0.7 ثانية، والمشهد يتبدل للجديد بالضبط لمن يعدي الشعاع نص الشاشة.

**When to use:**
- EN: Use when you need a boxed version of M-018.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-018.

#### `al-trn-019-fast` — Zoom Blur · Fast
**زوم مع ضبابية · سريع**

*accent · any · blur · easing: easeInExpo / easeOutExpo · 0.4s out · 0.4s in*

*Original: M-019*

Variant of M-019: أسرع بـ 40%

**Spec (EN):** The outgoing clip scales to 170% with a radial blur of about 10px and fades out over 0.4s (easeInExpo). The incoming clip starts at 160% blurred and settles to 100% sharp over 0.4s (easeOutExpo).

**Spec (AR):** المقطع الطالع يكبر لـ 170% مع ضبابية تقريباً 10px ويختفي خلال 0.4 ثانية (easeInExpo). والمقطع الداخل يبدأ من 160% مضبب ويستقر على 100% واضح خلال 0.4 ثانية (easeOutExpo).

**When to use:**
- EN: Use when you need a fast version of M-019.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-019.

#### `al-trn-019-slow` — Zoom Blur · Slow
**زوم مع ضبابية · بطيء**

*accent · any · blur · easing: easeInExpo / easeOutExpo · 0.4s out · 0.4s in*

*Original: M-019*

Variant of M-019: أبطأ بـ 60%

**Spec (EN):** The outgoing clip scales to 170% with a radial blur of about 10px and fades out over 0.4s (easeInExpo). The incoming clip starts at 160% blurred and settles to 100% sharp over 0.4s (easeOutExpo).

**Spec (AR):** المقطع الطالع يكبر لـ 170% مع ضبابية تقريباً 10px ويختفي خلال 0.4 ثانية (easeInExpo). والمقطع الداخل يبدأ من 160% مضبب ويستقر على 100% واضح خلال 0.4 ثانية (easeOutExpo).

**When to use:**
- EN: Use when you need a slow version of M-019.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-019.

#### `al-trn-019-gold` — Zoom Blur · Gold
**زوم مع ضبابية · ذهبي**

*accent · any · blur · easing: easeInExpo / easeOutExpo · 0.4s out · 0.4s in*

*Original: M-019*

Variant of M-019: نسخة ذهبية فاخرة

**Spec (EN):** The outgoing clip scales to 170% with a radial blur of about 10px and fades out over 0.4s (easeInExpo). The incoming clip starts at 160% blurred and settles to 100% sharp over 0.4s (easeOutExpo).

**Spec (AR):** المقطع الطالع يكبر لـ 170% مع ضبابية تقريباً 10px ويختفي خلال 0.4 ثانية (easeInExpo). والمقطع الداخل يبدأ من 160% مضبب ويستقر على 100% واضح خلال 0.4 ثانية (easeOutExpo).

**When to use:**
- EN: Use when you need a gold version of M-019.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-019.

#### `al-trn-019-boxed` — Zoom Blur · Boxed
**زوم مع ضبابية · صندوق**

*accent · any · blur · easing: easeInExpo / easeOutExpo · 0.4s out · 0.4s in*

*Original: M-019*

Variant of M-019: النص داخل صندوق ملون

**Spec (EN):** The outgoing clip scales to 170% with a radial blur of about 10px and fades out over 0.4s (easeInExpo). The incoming clip starts at 160% blurred and settles to 100% sharp over 0.4s (easeOutExpo).

**Spec (AR):** المقطع الطالع يكبر لـ 170% مع ضبابية تقريباً 10px ويختفي خلال 0.4 ثانية (easeInExpo). والمقطع الداخل يبدأ من 160% مضبب ويستقر على 100% واضح خلال 0.4 ثانية (easeOutExpo).

**When to use:**
- EN: Use when you need a boxed version of M-019.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-019.

#### `al-trn-020-fast` — Whip Pan · Fast
**سحبة سريعة · سريع**

*accent · any · blur · easing: easeInOutQuart · 0.35s*

*Original: M-020*

Variant of M-020: أسرع بـ 40%

**Spec (EN):** The outgoing clip slides out to one side with heavy horizontal motion blur, and the incoming clip slides in from the opposite side over 0.35s total. Add a fast "whoosh" sound.

**Spec (AR):** المقطع الطالع ينسحب لجهة مع ضبابية حركة أفقية قوية، والداخل يدخل من الجهة الثانية، والمجموع 0.35 ثانية. حط معاه صوت "ووش" سريع.

**When to use:**
- EN: Use when you need a fast version of M-020.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-020.

#### `al-trn-020-slow` — Whip Pan · Slow
**سحبة سريعة · بطيء**

*accent · any · blur · easing: easeInOutQuart · 0.35s*

*Original: M-020*

Variant of M-020: أبطأ بـ 60%

**Spec (EN):** The outgoing clip slides out to one side with heavy horizontal motion blur, and the incoming clip slides in from the opposite side over 0.35s total. Add a fast "whoosh" sound.

**Spec (AR):** المقطع الطالع ينسحب لجهة مع ضبابية حركة أفقية قوية، والداخل يدخل من الجهة الثانية، والمجموع 0.35 ثانية. حط معاه صوت "ووش" سريع.

**When to use:**
- EN: Use when you need a slow version of M-020.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-020.

#### `al-trn-020-gold` — Whip Pan · Gold
**سحبة سريعة · ذهبي**

*accent · any · blur · easing: easeInOutQuart · 0.35s*

*Original: M-020*

Variant of M-020: نسخة ذهبية فاخرة

**Spec (EN):** The outgoing clip slides out to one side with heavy horizontal motion blur, and the incoming clip slides in from the opposite side over 0.35s total. Add a fast "whoosh" sound.

**Spec (AR):** المقطع الطالع ينسحب لجهة مع ضبابية حركة أفقية قوية، والداخل يدخل من الجهة الثانية، والمجموع 0.35 ثانية. حط معاه صوت "ووش" سريع.

**When to use:**
- EN: Use when you need a gold version of M-020.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-020.

#### `al-trn-020-boxed` — Whip Pan · Boxed
**سحبة سريعة · صندوق**

*accent · any · blur · easing: easeInOutQuart · 0.35s*

*Original: M-020*

Variant of M-020: النص داخل صندوق ملون

**Spec (EN):** The outgoing clip slides out to one side with heavy horizontal motion blur, and the incoming clip slides in from the opposite side over 0.35s total. Add a fast "whoosh" sound.

**Spec (AR):** المقطع الطالع ينسحب لجهة مع ضبابية حركة أفقية قوية، والداخل يدخل من الجهة الثانية، والمجموع 0.35 ثانية. حط معاه صوت "ووش" سريع.

**When to use:**
- EN: Use when you need a boxed version of M-020.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-020.

#### `al-trn-101-fast` — Fade Through Black · Fast
**تلاشي للأسود · سريع**

*accent · calm · timeline · easing: easeInOutSine · 0.3s out · 0.3s in*

*Original: M-101*

Variant of M-101: أسرع بـ 40%

**Spec (EN):** The outgoing clip fades to full black over 0.3s, holds black for 2–4 frames, then the new clip fades in from black over 0.3s.

**Spec (AR):** المقطع الطالع يختفي لأسود كامل خلال 0.3 ثانية، يثبت الأسود 2 إلى 4 فريمات، وبعدين المقطع الجديد يظهر من الأسود خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-101.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-101.

#### `al-trn-101-slow` — Fade Through Black · Slow
**تلاشي للأسود · بطيء**

*accent · calm · timeline · easing: easeInOutSine · 0.3s out · 0.3s in*

*Original: M-101*

Variant of M-101: أبطأ بـ 60%

**Spec (EN):** The outgoing clip fades to full black over 0.3s, holds black for 2–4 frames, then the new clip fades in from black over 0.3s.

**Spec (AR):** المقطع الطالع يختفي لأسود كامل خلال 0.3 ثانية، يثبت الأسود 2 إلى 4 فريمات، وبعدين المقطع الجديد يظهر من الأسود خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-101.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-101.

#### `al-trn-101-gold` — Fade Through Black · Gold
**تلاشي للأسود · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · 0.3s out · 0.3s in*

*Original: M-101*

Variant of M-101: نسخة ذهبية فاخرة

**Spec (EN):** The outgoing clip fades to full black over 0.3s, holds black for 2–4 frames, then the new clip fades in from black over 0.3s.

**Spec (AR):** المقطع الطالع يختفي لأسود كامل خلال 0.3 ثانية، يثبت الأسود 2 إلى 4 فريمات، وبعدين المقطع الجديد يظهر من الأسود خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-101.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-101.

#### `al-trn-101-boxed` — Fade Through Black · Boxed
**تلاشي للأسود · صندوق**

*accent · calm · timeline · easing: easeInOutSine · 0.3s out · 0.3s in*

*Original: M-101*

Variant of M-101: النص داخل صندوق ملون

**Spec (EN):** The outgoing clip fades to full black over 0.3s, holds black for 2–4 frames, then the new clip fades in from black over 0.3s.

**Spec (AR):** المقطع الطالع يختفي لأسود كامل خلال 0.3 ثانية، يثبت الأسود 2 إلى 4 فريمات، وبعدين المقطع الجديد يظهر من الأسود خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-101.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-101.

#### `al-trn-102-fast` — Cross Dissolve · Fast
**ذوبان بين مشهدين · سريع**

*accent · calm · timeline · easing: linear · 0.5s*

*Original: M-102*

Variant of M-102: أسرع بـ 40%

**Spec (EN):** The new clip fades in on top of the old one from 0 to 100% over 0.5s while both play.

**Spec (AR):** المقطع الجديد يظهر فوق القديم من 0 لـ 100% خلال 0.5 ثانية والاثنين شغالين.

**When to use:**
- EN: Use when you need a fast version of M-102.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-102.

#### `al-trn-102-slow` — Cross Dissolve · Slow
**ذوبان بين مشهدين · بطيء**

*accent · calm · timeline · easing: linear · 0.5s*

*Original: M-102*

Variant of M-102: أبطأ بـ 60%

**Spec (EN):** The new clip fades in on top of the old one from 0 to 100% over 0.5s while both play.

**Spec (AR):** المقطع الجديد يظهر فوق القديم من 0 لـ 100% خلال 0.5 ثانية والاثنين شغالين.

**When to use:**
- EN: Use when you need a slow version of M-102.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-102.

#### `al-trn-102-gold` — Cross Dissolve · Gold
**ذوبان بين مشهدين · ذهبي**

*accent · calm · timeline · easing: linear · 0.5s*

*Original: M-102*

Variant of M-102: نسخة ذهبية فاخرة

**Spec (EN):** The new clip fades in on top of the old one from 0 to 100% over 0.5s while both play.

**Spec (AR):** المقطع الجديد يظهر فوق القديم من 0 لـ 100% خلال 0.5 ثانية والاثنين شغالين.

**When to use:**
- EN: Use when you need a gold version of M-102.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-102.

#### `al-trn-102-boxed` — Cross Dissolve · Boxed
**ذوبان بين مشهدين · صندوق**

*accent · calm · timeline · easing: linear · 0.5s*

*Original: M-102*

Variant of M-102: النص داخل صندوق ملون

**Spec (EN):** The new clip fades in on top of the old one from 0 to 100% over 0.5s while both play.

**Spec (AR):** المقطع الجديد يظهر فوق القديم من 0 لـ 100% خلال 0.5 ثانية والاثنين شغالين.

**When to use:**
- EN: Use when you need a boxed version of M-102.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-102.

#### `al-trn-103-fast` — Slide Push · Fast
**دفع المشهد · سريع**

*accent · any · timeline · easing: easeInOutQuart · 0.45s*

*Original: M-103*

Variant of M-103: أسرع بـ 40%

**Spec (EN):** The new clip slides in from the right edge while pushing the old clip out to the left at the same speed over 0.45s.

**Spec (AR):** المقطع الجديد يدخل من الحافة اليمين وهو يدفع القديم لبرا من اليسار بنفس السرعة خلال 0.45 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-103.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-103.

#### `al-trn-103-slow` — Slide Push · Slow
**دفع المشهد · بطيء**

*accent · any · timeline · easing: easeInOutQuart · 0.45s*

*Original: M-103*

Variant of M-103: أبطأ بـ 60%

**Spec (EN):** The new clip slides in from the right edge while pushing the old clip out to the left at the same speed over 0.45s.

**Spec (AR):** المقطع الجديد يدخل من الحافة اليمين وهو يدفع القديم لبرا من اليسار بنفس السرعة خلال 0.45 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-103.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-103.

#### `al-trn-103-gold` — Slide Push · Gold
**دفع المشهد · ذهبي**

*accent · any · timeline · easing: easeInOutQuart · 0.45s*

*Original: M-103*

Variant of M-103: نسخة ذهبية فاخرة

**Spec (EN):** The new clip slides in from the right edge while pushing the old clip out to the left at the same speed over 0.45s.

**Spec (AR):** المقطع الجديد يدخل من الحافة اليمين وهو يدفع القديم لبرا من اليسار بنفس السرعة خلال 0.45 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-103.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-103.

#### `al-trn-103-boxed` — Slide Push · Boxed
**دفع المشهد · صندوق**

*accent · any · timeline · easing: easeInOutQuart · 0.45s*

*Original: M-103*

Variant of M-103: النص داخل صندوق ملون

**Spec (EN):** The new clip slides in from the right edge while pushing the old clip out to the left at the same speed over 0.45s.

**Spec (AR):** المقطع الجديد يدخل من الحافة اليمين وهو يدفع القديم لبرا من اليسار بنفس السرعة خلال 0.45 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-103.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-103.

#### `al-trn-104-fast` — Diagonal Wipe · Fast
**مسح قطري · سريع**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-104*

Variant of M-104: أسرع بـ 40%

**Spec (EN):** The new clip is revealed behind a soft-edged diagonal line (135°) that travels from the top-left corner to the bottom-right over 0.5s.

**Spec (AR):** المقطع الجديد ينكشف ورا خط مايل (135 درجة) بحافة ناعمة يمشي من الزاوية الفوق يسار للزاوية التحت يمين خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-104.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-104.

#### `al-trn-104-slow` — Diagonal Wipe · Slow
**مسح قطري · بطيء**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-104*

Variant of M-104: أبطأ بـ 60%

**Spec (EN):** The new clip is revealed behind a soft-edged diagonal line (135°) that travels from the top-left corner to the bottom-right over 0.5s.

**Spec (AR):** المقطع الجديد ينكشف ورا خط مايل (135 درجة) بحافة ناعمة يمشي من الزاوية الفوق يسار للزاوية التحت يمين خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-104.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-104.

#### `al-trn-104-gold` — Diagonal Wipe · Gold
**مسح قطري · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-104*

Variant of M-104: نسخة ذهبية فاخرة

**Spec (EN):** The new clip is revealed behind a soft-edged diagonal line (135°) that travels from the top-left corner to the bottom-right over 0.5s.

**Spec (AR):** المقطع الجديد ينكشف ورا خط مايل (135 درجة) بحافة ناعمة يمشي من الزاوية الفوق يسار للزاوية التحت يمين خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-104.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-104.

#### `al-trn-104-boxed` — Diagonal Wipe · Boxed
**مسح قطري · صندوق**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-104*

Variant of M-104: النص داخل صندوق ملون

**Spec (EN):** The new clip is revealed behind a soft-edged diagonal line (135°) that travels from the top-left corner to the bottom-right over 0.5s.

**Spec (AR):** المقطع الجديد ينكشف ورا خط مايل (135 درجة) بحافة ناعمة يمشي من الزاوية الفوق يسار للزاوية التحت يمين خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-104.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-104.

#### `al-trn-105-fast` — Iris Close/Open · Fast
**دائرة تقفل وتفتح · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.4s close · 0.4s open*

*Original: M-105*

Variant of M-105: أسرع بـ 40%

**Spec (EN):** A circular mask shrinks to zero on the face of the outgoing clip (0.4s), then the new clip opens from the same point with a growing circle (0.4s). Black between.

**Spec (AR):** قناع دائري يصغر لين يختفي على وجه المقطع الطالع (0.4 ثانية)، وبعدين المقطع الجديد ينفتح من نفس النقطة بدائرة تكبر (0.4 ثانية). وبينهم أسود.

**When to use:**
- EN: Use when you need a fast version of M-105.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-105.

#### `al-trn-105-slow` — Iris Close/Open · Slow
**دائرة تقفل وتفتح · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.4s close · 0.4s open*

*Original: M-105*

Variant of M-105: أبطأ بـ 60%

**Spec (EN):** A circular mask shrinks to zero on the face of the outgoing clip (0.4s), then the new clip opens from the same point with a growing circle (0.4s). Black between.

**Spec (AR):** قناع دائري يصغر لين يختفي على وجه المقطع الطالع (0.4 ثانية)، وبعدين المقطع الجديد ينفتح من نفس النقطة بدائرة تكبر (0.4 ثانية). وبينهم أسود.

**When to use:**
- EN: Use when you need a slow version of M-105.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-105.

#### `al-trn-105-gold` — Iris Close/Open · Gold
**دائرة تقفل وتفتح · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.4s close · 0.4s open*

*Original: M-105*

Variant of M-105: نسخة ذهبية فاخرة

**Spec (EN):** A circular mask shrinks to zero on the face of the outgoing clip (0.4s), then the new clip opens from the same point with a growing circle (0.4s). Black between.

**Spec (AR):** قناع دائري يصغر لين يختفي على وجه المقطع الطالع (0.4 ثانية)، وبعدين المقطع الجديد ينفتح من نفس النقطة بدائرة تكبر (0.4 ثانية). وبينهم أسود.

**When to use:**
- EN: Use when you need a gold version of M-105.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-105.

#### `al-trn-105-boxed` — Iris Close/Open · Boxed
**دائرة تقفل وتفتح · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.4s close · 0.4s open*

*Original: M-105*

Variant of M-105: النص داخل صندوق ملون

**Spec (EN):** A circular mask shrinks to zero on the face of the outgoing clip (0.4s), then the new clip opens from the same point with a growing circle (0.4s). Black between.

**Spec (AR):** قناع دائري يصغر لين يختفي على وجه المقطع الطالع (0.4 ثانية)، وبعدين المقطع الجديد ينفتح من نفس النقطة بدائرة تكبر (0.4 ثانية). وبينهم أسود.

**When to use:**
- EN: Use when you need a boxed version of M-105.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-105.

#### `al-trn-106-fast` — Clock Wipe · Fast
**مسح مثل الساعة · سريع**

*accent · calm · timeline · easing: easeInOutSine · 0.6s*

*Original: M-106*

Variant of M-106: أسرع بـ 40%

**Spec (EN):** The new clip is revealed by a radial sweep around the center, starting at 12 o clock and going clockwise a full 360° over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف بمسحة دائرية حول النص، تبدأ من الساعة 12 وتمشي مع عقارب الساعة 360 درجة كاملة خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-106.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-106.

#### `al-trn-106-slow` — Clock Wipe · Slow
**مسح مثل الساعة · بطيء**

*accent · calm · timeline · easing: easeInOutSine · 0.6s*

*Original: M-106*

Variant of M-106: أبطأ بـ 60%

**Spec (EN):** The new clip is revealed by a radial sweep around the center, starting at 12 o clock and going clockwise a full 360° over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف بمسحة دائرية حول النص، تبدأ من الساعة 12 وتمشي مع عقارب الساعة 360 درجة كاملة خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-106.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-106.

#### `al-trn-106-gold` — Clock Wipe · Gold
**مسح مثل الساعة · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · 0.6s*

*Original: M-106*

Variant of M-106: نسخة ذهبية فاخرة

**Spec (EN):** The new clip is revealed by a radial sweep around the center, starting at 12 o clock and going clockwise a full 360° over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف بمسحة دائرية حول النص، تبدأ من الساعة 12 وتمشي مع عقارب الساعة 360 درجة كاملة خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-106.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-106.

#### `al-trn-106-boxed` — Clock Wipe · Boxed
**مسح مثل الساعة · صندوق**

*accent · calm · timeline · easing: easeInOutSine · 0.6s*

*Original: M-106*

Variant of M-106: النص داخل صندوق ملون

**Spec (EN):** The new clip is revealed by a radial sweep around the center, starting at 12 o clock and going clockwise a full 360° over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف بمسحة دائرية حول النص، تبدأ من الساعة 12 وتمشي مع عقارب الساعة 360 درجة كاملة خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-106.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-106.

#### `al-trn-107-fast` — Blinds · Fast
**ستائر · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-107*

Variant of M-107: أسرع بـ 40%

**Spec (EN):** The frame is split into 6 vertical strips. Each strip reveals the new clip by growing from its right edge to full width over 0.5s.

**Spec (AR):** الشاشة مقسومة 6 شرائح عمودية. كل شريحة تكشف المقطع الجديد وهي تكبر من حافتها لين تغطي عرضها خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-107.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-107.

#### `al-trn-107-slow` — Blinds · Slow
**ستائر · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-107*

Variant of M-107: أبطأ بـ 60%

**Spec (EN):** The frame is split into 6 vertical strips. Each strip reveals the new clip by growing from its right edge to full width over 0.5s.

**Spec (AR):** الشاشة مقسومة 6 شرائح عمودية. كل شريحة تكشف المقطع الجديد وهي تكبر من حافتها لين تغطي عرضها خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-107.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-107.

#### `al-trn-107-gold` — Blinds · Gold
**ستائر · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-107*

Variant of M-107: نسخة ذهبية فاخرة

**Spec (EN):** The frame is split into 6 vertical strips. Each strip reveals the new clip by growing from its right edge to full width over 0.5s.

**Spec (AR):** الشاشة مقسومة 6 شرائح عمودية. كل شريحة تكشف المقطع الجديد وهي تكبر من حافتها لين تغطي عرضها خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-107.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-107.

#### `al-trn-107-boxed` — Blinds · Boxed
**ستائر · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-107*

Variant of M-107: النص داخل صندوق ملون

**Spec (EN):** The frame is split into 6 vertical strips. Each strip reveals the new clip by growing from its right edge to full width over 0.5s.

**Spec (AR):** الشاشة مقسومة 6 شرائح عمودية. كل شريحة تكشف المقطع الجديد وهي تكبر من حافتها لين تغطي عرضها خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-107.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-107.

#### `al-trn-108-fast` — Split Doors · Fast
**أبواب تنفتح · سريع**

*accent · any · timeline · easing: easeInOutQuart · 0.6s*

*Original: M-108*

Variant of M-108: أسرع بـ 40%

**Spec (EN):** The outgoing clip is cut down the middle; the two halves slide apart to the left and right over 0.6s, revealing the new clip behind them.

**Spec (AR):** المقطع الطالع ينقص من النص، والنصين يتحركون يمين ويسار خلال 0.6 ثانية ويكشفون المقطع الجديد وراهم.

**When to use:**
- EN: Use when you need a fast version of M-108.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-108.

#### `al-trn-108-slow` — Split Doors · Slow
**أبواب تنفتح · بطيء**

*accent · any · timeline · easing: easeInOutQuart · 0.6s*

*Original: M-108*

Variant of M-108: أبطأ بـ 60%

**Spec (EN):** The outgoing clip is cut down the middle; the two halves slide apart to the left and right over 0.6s, revealing the new clip behind them.

**Spec (AR):** المقطع الطالع ينقص من النص، والنصين يتحركون يمين ويسار خلال 0.6 ثانية ويكشفون المقطع الجديد وراهم.

**When to use:**
- EN: Use when you need a slow version of M-108.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-108.

#### `al-trn-108-gold` — Split Doors · Gold
**أبواب تنفتح · ذهبي**

*accent · any · timeline · easing: easeInOutQuart · 0.6s*

*Original: M-108*

Variant of M-108: نسخة ذهبية فاخرة

**Spec (EN):** The outgoing clip is cut down the middle; the two halves slide apart to the left and right over 0.6s, revealing the new clip behind them.

**Spec (AR):** المقطع الطالع ينقص من النص، والنصين يتحركون يمين ويسار خلال 0.6 ثانية ويكشفون المقطع الجديد وراهم.

**When to use:**
- EN: Use when you need a gold version of M-108.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-108.

#### `al-trn-108-boxed` — Split Doors · Boxed
**أبواب تنفتح · صندوق**

*accent · any · timeline · easing: easeInOutQuart · 0.6s*

*Original: M-108*

Variant of M-108: النص داخل صندوق ملون

**Spec (EN):** The outgoing clip is cut down the middle; the two halves slide apart to the left and right over 0.6s, revealing the new clip behind them.

**Spec (AR):** المقطع الطالع ينقص من النص، والنصين يتحركون يمين ويسار خلال 0.6 ثانية ويكشفون المقطع الجديد وراهم.

**When to use:**
- EN: Use when you need a boxed version of M-108.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-108.

#### `al-trn-109-fast` — Diamond Reveal · Fast
**انكشاف ماسي · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-109*

Variant of M-109: أسرع بـ 40%

**Spec (EN):** The new clip is revealed through a diamond-shaped mask that grows from the face point until it covers the frame over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف من قناع بشكل معيّن يكبر من نقطة الوجه لين يغطي الشاشة خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-109.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-109.

#### `al-trn-109-slow` — Diamond Reveal · Slow
**انكشاف ماسي · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-109*

Variant of M-109: أبطأ بـ 60%

**Spec (EN):** The new clip is revealed through a diamond-shaped mask that grows from the face point until it covers the frame over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف من قناع بشكل معيّن يكبر من نقطة الوجه لين يغطي الشاشة خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-109.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-109.

#### `al-trn-109-gold` — Diamond Reveal · Gold
**انكشاف ماسي · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-109*

Variant of M-109: نسخة ذهبية فاخرة

**Spec (EN):** The new clip is revealed through a diamond-shaped mask that grows from the face point until it covers the frame over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف من قناع بشكل معيّن يكبر من نقطة الوجه لين يغطي الشاشة خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-109.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-109.

#### `al-trn-109-boxed` — Diamond Reveal · Boxed
**انكشاف ماسي · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-109*

Variant of M-109: النص داخل صندوق ملون

**Spec (EN):** The new clip is revealed through a diamond-shaped mask that grows from the face point until it covers the frame over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف من قناع بشكل معيّن يكبر من نقطة الوجه لين يغطي الشاشة خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-109.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-109.

#### `al-trn-110-fast` — Glitch Transition · Fast
**انتقال جلتش · سريع**

*accent · any · timeline · easing: steps · 0.4s*

*Original: M-110*

Variant of M-110: أسرع بـ 40%

**Spec (EN):** For 0.4s the new clip flashes in through random horizontal slices with ±8% offsets, changing every 2 frames, then locks in clean. Add a digital noise sound.

**Spec (AR):** لمدة 0.4 ثانية المقطع الجديد يومض من شرائح أفقية عشوائية بإزاحة ±8% تتغير كل فريمين، وبعدين يثبت نظيف. حط معاه صوت تشويش رقمي.

**When to use:**
- EN: Use when you need a fast version of M-110.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-110.

#### `al-trn-110-slow` — Glitch Transition · Slow
**انتقال جلتش · بطيء**

*accent · any · timeline · easing: steps · 0.4s*

*Original: M-110*

Variant of M-110: أبطأ بـ 60%

**Spec (EN):** For 0.4s the new clip flashes in through random horizontal slices with ±8% offsets, changing every 2 frames, then locks in clean. Add a digital noise sound.

**Spec (AR):** لمدة 0.4 ثانية المقطع الجديد يومض من شرائح أفقية عشوائية بإزاحة ±8% تتغير كل فريمين، وبعدين يثبت نظيف. حط معاه صوت تشويش رقمي.

**When to use:**
- EN: Use when you need a slow version of M-110.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-110.

#### `al-trn-110-gold` — Glitch Transition · Gold
**انتقال جلتش · ذهبي**

*accent · any · timeline · easing: steps · 0.4s*

*Original: M-110*

Variant of M-110: نسخة ذهبية فاخرة

**Spec (EN):** For 0.4s the new clip flashes in through random horizontal slices with ±8% offsets, changing every 2 frames, then locks in clean. Add a digital noise sound.

**Spec (AR):** لمدة 0.4 ثانية المقطع الجديد يومض من شرائح أفقية عشوائية بإزاحة ±8% تتغير كل فريمين، وبعدين يثبت نظيف. حط معاه صوت تشويش رقمي.

**When to use:**
- EN: Use when you need a gold version of M-110.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-110.

#### `al-trn-110-boxed` — Glitch Transition · Boxed
**انتقال جلتش · صندوق**

*accent · any · timeline · easing: steps · 0.4s*

*Original: M-110*

Variant of M-110: النص داخل صندوق ملون

**Spec (EN):** For 0.4s the new clip flashes in through random horizontal slices with ±8% offsets, changing every 2 frames, then locks in clean. Add a digital noise sound.

**Spec (AR):** لمدة 0.4 ثانية المقطع الجديد يومض من شرائح أفقية عشوائية بإزاحة ±8% تتغير كل فريمين، وبعدين يثبت نظيف. حط معاه صوت تشويش رقمي.

**When to use:**
- EN: Use when you need a boxed version of M-110.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-110.

#### `al-trn-111-fast` — Spin Transition · Fast
**انتقال بدوران · سريع**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-111*

Variant of M-111: أسرع بـ 40%

**Spec (EN):** The outgoing clip rotates 180° while shrinking to 20% and fading out; the new clip rotates in from -180° and 20% to full size over 0.5s.

**Spec (AR):** المقطع الطالع يلف 180 درجة وهو يصغر لـ 20% ويختفي، والجديد يلف من -180 درجة و20% لين حجمه الكامل خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-111.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-111.

#### `al-trn-111-slow` — Spin Transition · Slow
**انتقال بدوران · بطيء**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-111*

Variant of M-111: أبطأ بـ 60%

**Spec (EN):** The outgoing clip rotates 180° while shrinking to 20% and fading out; the new clip rotates in from -180° and 20% to full size over 0.5s.

**Spec (AR):** المقطع الطالع يلف 180 درجة وهو يصغر لـ 20% ويختفي، والجديد يلف من -180 درجة و20% لين حجمه الكامل خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-111.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-111.

#### `al-trn-111-gold` — Spin Transition · Gold
**انتقال بدوران · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-111*

Variant of M-111: نسخة ذهبية فاخرة

**Spec (EN):** The outgoing clip rotates 180° while shrinking to 20% and fading out; the new clip rotates in from -180° and 20% to full size over 0.5s.

**Spec (AR):** المقطع الطالع يلف 180 درجة وهو يصغر لـ 20% ويختفي، والجديد يلف من -180 درجة و20% لين حجمه الكامل خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-111.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-111.

#### `al-trn-111-boxed` — Spin Transition · Boxed
**انتقال بدوران · صندوق**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-111*

Variant of M-111: النص داخل صندوق ملون

**Spec (EN):** The outgoing clip rotates 180° while shrinking to 20% and fading out; the new clip rotates in from -180° and 20% to full size over 0.5s.

**Spec (AR):** المقطع الطالع يلف 180 درجة وهو يصغر لـ 20% ويختفي، والجديد يلف من -180 درجة و20% لين حجمه الكامل خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-111.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-111.

#### `al-trn-112-fast` — Flash White · Fast
**وميض أبيض للانتقال · سريع**

*accent · any · timeline · easing: easeOut · 0.25s*

*Original: M-112*

Variant of M-112: أسرع بـ 40%

**Spec (EN):** A full white flash peaks in 2 frames exactly on the cut, then fades over 0.25s to reveal the new clip.

**Spec (AR):** وميض أبيض كامل يوصل قمته خلال فريمين بالضبط عند القص، وبعدين يختفي خلال 0.25 ثانية ويكشف المقطع الجديد.

**When to use:**
- EN: Use when you need a fast version of M-112.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-112.

#### `al-trn-112-slow` — Flash White · Slow
**وميض أبيض للانتقال · بطيء**

*accent · any · timeline · easing: easeOut · 0.25s*

*Original: M-112*

Variant of M-112: أبطأ بـ 60%

**Spec (EN):** A full white flash peaks in 2 frames exactly on the cut, then fades over 0.25s to reveal the new clip.

**Spec (AR):** وميض أبيض كامل يوصل قمته خلال فريمين بالضبط عند القص، وبعدين يختفي خلال 0.25 ثانية ويكشف المقطع الجديد.

**When to use:**
- EN: Use when you need a slow version of M-112.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-112.

#### `al-trn-112-gold` — Flash White · Gold
**وميض أبيض للانتقال · ذهبي**

*accent · any · timeline · easing: easeOut · 0.25s*

*Original: M-112*

Variant of M-112: نسخة ذهبية فاخرة

**Spec (EN):** A full white flash peaks in 2 frames exactly on the cut, then fades over 0.25s to reveal the new clip.

**Spec (AR):** وميض أبيض كامل يوصل قمته خلال فريمين بالضبط عند القص، وبعدين يختفي خلال 0.25 ثانية ويكشف المقطع الجديد.

**When to use:**
- EN: Use when you need a gold version of M-112.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-112.

#### `al-trn-112-boxed` — Flash White · Boxed
**وميض أبيض للانتقال · صندوق**

*accent · any · timeline · easing: easeOut · 0.25s*

*Original: M-112*

Variant of M-112: النص داخل صندوق ملون

**Spec (EN):** A full white flash peaks in 2 frames exactly on the cut, then fades over 0.25s to reveal the new clip.

**Spec (AR):** وميض أبيض كامل يوصل قمته خلال فريمين بالضبط عند القص، وبعدين يختفي خلال 0.25 ثانية ويكشف المقطع الجديد.

**When to use:**
- EN: Use when you need a boxed version of M-112.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-112.

#### `al-trn-113-fast` — Color Flash · Fast
**وميض بلون الهوية · سريع**

*accent · any · timeline · easing: easeOut · 0.3s*

*Original: M-113*

Variant of M-113: أسرع بـ 40%

**Spec (EN):** Same as M-112 but the flash is the brand accent color at 90% opacity.

**Spec (AR):** نفس M-112 بس الوميض بلون الهوية وشفافيته 90%.

**When to use:**
- EN: Use when you need a fast version of M-113.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-113.

#### `al-trn-113-slow` — Color Flash · Slow
**وميض بلون الهوية · بطيء**

*accent · any · timeline · easing: easeOut · 0.3s*

*Original: M-113*

Variant of M-113: أبطأ بـ 60%

**Spec (EN):** Same as M-112 but the flash is the brand accent color at 90% opacity.

**Spec (AR):** نفس M-112 بس الوميض بلون الهوية وشفافيته 90%.

**When to use:**
- EN: Use when you need a slow version of M-113.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-113.

#### `al-trn-113-gold` — Color Flash · Gold
**وميض بلون الهوية · ذهبي**

*accent · any · timeline · easing: easeOut · 0.3s*

*Original: M-113*

Variant of M-113: نسخة ذهبية فاخرة

**Spec (EN):** Same as M-112 but the flash is the brand accent color at 90% opacity.

**Spec (AR):** نفس M-112 بس الوميض بلون الهوية وشفافيته 90%.

**When to use:**
- EN: Use when you need a gold version of M-113.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-113.

#### `al-trn-113-boxed` — Color Flash · Boxed
**وميض بلون الهوية · صندوق**

*accent · any · timeline · easing: easeOut · 0.3s*

*Original: M-113*

Variant of M-113: النص داخل صندوق ملون

**Spec (EN):** Same as M-112 but the flash is the brand accent color at 90% opacity.

**Spec (AR):** نفس M-112 بس الوميض بلون الهوية وشفافيته 90%.

**When to use:**
- EN: Use when you need a boxed version of M-113.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-113.

#### `al-trn-114-fast` — Corner Reveal · Fast
**انكشاف من الزاوية · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-114*

Variant of M-114: أسرع بـ 40%

**Spec (EN):** The new clip is revealed through a circle that grows from the bottom-left corner until it covers the frame over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف من دائرة تكبر من الزاوية التحت يسار لين تغطي الشاشة خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-114.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-114.

#### `al-trn-114-slow` — Corner Reveal · Slow
**انكشاف من الزاوية · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-114*

Variant of M-114: أبطأ بـ 60%

**Spec (EN):** The new clip is revealed through a circle that grows from the bottom-left corner until it covers the frame over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف من دائرة تكبر من الزاوية التحت يسار لين تغطي الشاشة خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-114.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-114.

#### `al-trn-114-gold` — Corner Reveal · Gold
**انكشاف من الزاوية · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-114*

Variant of M-114: نسخة ذهبية فاخرة

**Spec (EN):** The new clip is revealed through a circle that grows from the bottom-left corner until it covers the frame over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف من دائرة تكبر من الزاوية التحت يسار لين تغطي الشاشة خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-114.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-114.

#### `al-trn-114-boxed` — Corner Reveal · Boxed
**انكشاف من الزاوية · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-114*

Variant of M-114: النص داخل صندوق ملون

**Spec (EN):** The new clip is revealed through a circle that grows from the bottom-left corner until it covers the frame over 0.6s.

**Spec (AR):** المقطع الجديد ينكشف من دائرة تكبر من الزاوية التحت يسار لين تغطي الشاشة خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-114.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-114.

#### `al-trn-115-fast` — Cube Rotate · Fast
**مكعب يلف · سريع**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-115*

Variant of M-115: أسرع بـ 40%

**Spec (EN):** With 3D perspective, the outgoing clip rotates 90° away on its left edge while the new clip rotates in from -90° on its right edge, like a turning cube, over 0.6s.

**Spec (AR):** مع عمق 3D، المقطع الطالع يلف 90 درجة لبعيد على حافته اليسار، والجديد يلف من -90 درجة على حافته اليمين، مثل مكعب يلف، خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-115.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-115.

#### `al-trn-115-slow` — Cube Rotate · Slow
**مكعب يلف · بطيء**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-115*

Variant of M-115: أبطأ بـ 60%

**Spec (EN):** With 3D perspective, the outgoing clip rotates 90° away on its left edge while the new clip rotates in from -90° on its right edge, like a turning cube, over 0.6s.

**Spec (AR):** مع عمق 3D، المقطع الطالع يلف 90 درجة لبعيد على حافته اليسار، والجديد يلف من -90 درجة على حافته اليمين، مثل مكعب يلف، خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-115.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-115.

#### `al-trn-115-gold` — Cube Rotate · Gold
**مكعب يلف · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-115*

Variant of M-115: نسخة ذهبية فاخرة

**Spec (EN):** With 3D perspective, the outgoing clip rotates 90° away on its left edge while the new clip rotates in from -90° on its right edge, like a turning cube, over 0.6s.

**Spec (AR):** مع عمق 3D، المقطع الطالع يلف 90 درجة لبعيد على حافته اليسار، والجديد يلف من -90 درجة على حافته اليمين، مثل مكعب يلف، خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-115.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-115.

#### `al-trn-115-boxed` — Cube Rotate · Boxed
**مكعب يلف · صندوق**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-115*

Variant of M-115: النص داخل صندوق ملون

**Spec (EN):** With 3D perspective, the outgoing clip rotates 90° away on its left edge while the new clip rotates in from -90° on its right edge, like a turning cube, over 0.6s.

**Spec (AR):** مع عمق 3D، المقطع الطالع يلف 90 درجة لبعيد على حافته اليسار، والجديد يلف من -90 درجة على حافته اليمين، مثل مكعب يلف، خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-115.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-115.

#### `al-trn-116-fast` — Zoom Through · Fast
**زوم داخل المشهد · سريع**

*accent · any · timeline · easing: easeInExpo / easeOutCubic · 0.5s*

*Original: M-116*

Variant of M-116: أسرع بـ 40%

**Spec (EN):** The outgoing clip scales to 400% and fades out quickly (0.3s); the new clip grows from 60% to 100% while fading in (0.3s), overlapping slightly.

**Spec (AR):** المقطع الطالع يكبر لـ 400% ويختفي بسرعة (0.3 ثانية)، والجديد يكبر من 60% لـ 100% وهو يظهر (0.3 ثانية)، ويتداخلون شوي.

**When to use:**
- EN: Use when you need a fast version of M-116.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-116.

#### `al-trn-116-slow` — Zoom Through · Slow
**زوم داخل المشهد · بطيء**

*accent · any · timeline · easing: easeInExpo / easeOutCubic · 0.5s*

*Original: M-116*

Variant of M-116: أبطأ بـ 60%

**Spec (EN):** The outgoing clip scales to 400% and fades out quickly (0.3s); the new clip grows from 60% to 100% while fading in (0.3s), overlapping slightly.

**Spec (AR):** المقطع الطالع يكبر لـ 400% ويختفي بسرعة (0.3 ثانية)، والجديد يكبر من 60% لـ 100% وهو يظهر (0.3 ثانية)، ويتداخلون شوي.

**When to use:**
- EN: Use when you need a slow version of M-116.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-116.

#### `al-trn-116-gold` — Zoom Through · Gold
**زوم داخل المشهد · ذهبي**

*accent · any · timeline · easing: easeInExpo / easeOutCubic · 0.5s*

*Original: M-116*

Variant of M-116: نسخة ذهبية فاخرة

**Spec (EN):** The outgoing clip scales to 400% and fades out quickly (0.3s); the new clip grows from 60% to 100% while fading in (0.3s), overlapping slightly.

**Spec (AR):** المقطع الطالع يكبر لـ 400% ويختفي بسرعة (0.3 ثانية)، والجديد يكبر من 60% لـ 100% وهو يظهر (0.3 ثانية)، ويتداخلون شوي.

**When to use:**
- EN: Use when you need a gold version of M-116.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-116.

#### `al-trn-116-boxed` — Zoom Through · Boxed
**زوم داخل المشهد · صندوق**

*accent · any · timeline · easing: easeInExpo / easeOutCubic · 0.5s*

*Original: M-116*

Variant of M-116: النص داخل صندوق ملون

**Spec (EN):** The outgoing clip scales to 400% and fades out quickly (0.3s); the new clip grows from 60% to 100% while fading in (0.3s), overlapping slightly.

**Spec (AR):** المقطع الطالع يكبر لـ 400% ويختفي بسرعة (0.3 ثانية)، والجديد يكبر من 60% لـ 100% وهو يظهر (0.3 ثانية)، ويتداخلون شوي.

**When to use:**
- EN: Use when you need a boxed version of M-116.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-116.

#### `al-trn-117-fast` — Strip Slide · Fast
**شرائح تنزلق · سريع**

*accent · any · timeline · easing: easeOutQuart · 0.5s · 0.06s stagger*

*Original: M-117*

Variant of M-117: أسرع بـ 40%

**Spec (EN):** The new clip is cut into 5 horizontal strips; each strip slides in from the right over 0.5s, starting 0.06s after the one above it.

**Spec (AR):** المقطع الجديد مقسوم 5 شرائح أفقية، وكل شريحة تنزلق من اليمين خلال 0.5 ثانية، وتبدأ بعد اللي فوقها بـ 0.06 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-117.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-117.

#### `al-trn-117-slow` — Strip Slide · Slow
**شرائح تنزلق · بطيء**

*accent · any · timeline · easing: easeOutQuart · 0.5s · 0.06s stagger*

*Original: M-117*

Variant of M-117: أبطأ بـ 60%

**Spec (EN):** The new clip is cut into 5 horizontal strips; each strip slides in from the right over 0.5s, starting 0.06s after the one above it.

**Spec (AR):** المقطع الجديد مقسوم 5 شرائح أفقية، وكل شريحة تنزلق من اليمين خلال 0.5 ثانية، وتبدأ بعد اللي فوقها بـ 0.06 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-117.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-117.

#### `al-trn-117-gold` — Strip Slide · Gold
**شرائح تنزلق · ذهبي**

*accent · any · timeline · easing: easeOutQuart · 0.5s · 0.06s stagger*

*Original: M-117*

Variant of M-117: نسخة ذهبية فاخرة

**Spec (EN):** The new clip is cut into 5 horizontal strips; each strip slides in from the right over 0.5s, starting 0.06s after the one above it.

**Spec (AR):** المقطع الجديد مقسوم 5 شرائح أفقية، وكل شريحة تنزلق من اليمين خلال 0.5 ثانية، وتبدأ بعد اللي فوقها بـ 0.06 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-117.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-117.

#### `al-trn-117-boxed` — Strip Slide · Boxed
**شرائح تنزلق · صندوق**

*accent · any · timeline · easing: easeOutQuart · 0.5s · 0.06s stagger*

*Original: M-117*

Variant of M-117: النص داخل صندوق ملون

**Spec (EN):** The new clip is cut into 5 horizontal strips; each strip slides in from the right over 0.5s, starting 0.06s after the one above it.

**Spec (AR):** المقطع الجديد مقسوم 5 شرائح أفقية، وكل شريحة تنزلق من اليمين خلال 0.5 ثانية، وتبدأ بعد اللي فوقها بـ 0.06 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-117.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-117.

#### `al-trn-118-fast` — Light Leak · Fast
**تسرب ضوء · سريع**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-118*

Variant of M-118: أسرع بـ 40%

**Spec (EN):** Warm orange and red light blobs (screen blend) drift across the frame over 0.8s; the cut to the new clip happens at the brightest moment.

**Spec (AR):** بقع ضوء دافية برتقالي وأحمر (دمج screen) تمر على الشاشة خلال 0.8 ثانية، والقص للمقطع الجديد يصير بأكثر لحظة إضاءة.

**When to use:**
- EN: Use when you need a fast version of M-118.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-118.

#### `al-trn-118-slow` — Light Leak · Slow
**تسرب ضوء · بطيء**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-118*

Variant of M-118: أبطأ بـ 60%

**Spec (EN):** Warm orange and red light blobs (screen blend) drift across the frame over 0.8s; the cut to the new clip happens at the brightest moment.

**Spec (AR):** بقع ضوء دافية برتقالي وأحمر (دمج screen) تمر على الشاشة خلال 0.8 ثانية، والقص للمقطع الجديد يصير بأكثر لحظة إضاءة.

**When to use:**
- EN: Use when you need a slow version of M-118.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-118.

#### `al-trn-118-gold` — Light Leak · Gold
**تسرب ضوء · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-118*

Variant of M-118: نسخة ذهبية فاخرة

**Spec (EN):** Warm orange and red light blobs (screen blend) drift across the frame over 0.8s; the cut to the new clip happens at the brightest moment.

**Spec (AR):** بقع ضوء دافية برتقالي وأحمر (دمج screen) تمر على الشاشة خلال 0.8 ثانية، والقص للمقطع الجديد يصير بأكثر لحظة إضاءة.

**When to use:**
- EN: Use when you need a gold version of M-118.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-118.

#### `al-trn-118-boxed` — Light Leak · Boxed
**تسرب ضوء · صندوق**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-118*

Variant of M-118: النص داخل صندوق ملون

**Spec (EN):** Warm orange and red light blobs (screen blend) drift across the frame over 0.8s; the cut to the new clip happens at the brightest moment.

**Spec (AR):** بقع ضوء دافية برتقالي وأحمر (دمج screen) تمر على الشاشة خلال 0.8 ثانية، والقص للمقطع الجديد يصير بأكثر لحظة إضاءة.

**When to use:**
- EN: Use when you need a boxed version of M-118.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-118.

#### `al-trn-119-fast` — Smooth Cut · Fast
**قص ناعم · سريع**

*accent · calm · timeline · easing: easeOutQuad · 0.3s*

*Original: M-119*

Variant of M-119: أسرع بـ 40%

**Spec (EN):** The new clip fades in over 0.3s while scaling from 105% to 100%, which hides small position jumps between two similar takes.

**Spec (AR):** المقطع الجديد يظهر خلال 0.3 ثانية وهو يصغر من 105% لـ 100%، وهذا يخفي النطة الصغيرة بين لقطتين متشابهتين.

**When to use:**
- EN: Use when you need a fast version of M-119.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-119.

#### `al-trn-119-slow` — Smooth Cut · Slow
**قص ناعم · بطيء**

*accent · calm · timeline · easing: easeOutQuad · 0.3s*

*Original: M-119*

Variant of M-119: أبطأ بـ 60%

**Spec (EN):** The new clip fades in over 0.3s while scaling from 105% to 100%, which hides small position jumps between two similar takes.

**Spec (AR):** المقطع الجديد يظهر خلال 0.3 ثانية وهو يصغر من 105% لـ 100%، وهذا يخفي النطة الصغيرة بين لقطتين متشابهتين.

**When to use:**
- EN: Use when you need a slow version of M-119.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-119.

#### `al-trn-119-gold` — Smooth Cut · Gold
**قص ناعم · ذهبي**

*accent · calm · timeline · easing: easeOutQuad · 0.3s*

*Original: M-119*

Variant of M-119: نسخة ذهبية فاخرة

**Spec (EN):** The new clip fades in over 0.3s while scaling from 105% to 100%, which hides small position jumps between two similar takes.

**Spec (AR):** المقطع الجديد يظهر خلال 0.3 ثانية وهو يصغر من 105% لـ 100%، وهذا يخفي النطة الصغيرة بين لقطتين متشابهتين.

**When to use:**
- EN: Use when you need a gold version of M-119.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-119.

#### `al-trn-119-boxed` — Smooth Cut · Boxed
**قص ناعم · صندوق**

*accent · calm · timeline · easing: easeOutQuad · 0.3s*

*Original: M-119*

Variant of M-119: النص داخل صندوق ملون

**Spec (EN):** The new clip fades in over 0.3s while scaling from 105% to 100%, which hides small position jumps between two similar takes.

**Spec (AR):** المقطع الجديد يظهر خلال 0.3 ثانية وهو يصغر من 105% لـ 100%، وهذا يخفي النطة الصغيرة بين لقطتين متشابهتين.

**When to use:**
- EN: Use when you need a boxed version of M-119.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-119.

#### `al-trn-120-fast` — Swipe Up · Fast
**سحب لفوق · سريع**

*accent · any · depth · easing: easeInOutQuart · 0.4s*

*Original: M-120*

Variant of M-120: أسرع بـ 40%

**Spec (EN):** The outgoing clip slides up out of the top edge while the new clip slides up from the bottom edge at the same speed over 0.4s.

**Spec (AR):** المقطع الطالع يطلع لفوق من الحافة الفوق، والجديد يطلع من الحافة التحت بنفس السرعة خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-120.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-120.

#### `al-trn-120-slow` — Swipe Up · Slow
**سحب لفوق · بطيء**

*accent · any · depth · easing: easeInOutQuart · 0.4s*

*Original: M-120*

Variant of M-120: أبطأ بـ 60%

**Spec (EN):** The outgoing clip slides up out of the top edge while the new clip slides up from the bottom edge at the same speed over 0.4s.

**Spec (AR):** المقطع الطالع يطلع لفوق من الحافة الفوق، والجديد يطلع من الحافة التحت بنفس السرعة خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-120.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-120.

#### `al-trn-120-gold` — Swipe Up · Gold
**سحب لفوق · ذهبي**

*accent · any · depth · easing: easeInOutQuart · 0.4s*

*Original: M-120*

Variant of M-120: نسخة ذهبية فاخرة

**Spec (EN):** The outgoing clip slides up out of the top edge while the new clip slides up from the bottom edge at the same speed over 0.4s.

**Spec (AR):** المقطع الطالع يطلع لفوق من الحافة الفوق، والجديد يطلع من الحافة التحت بنفس السرعة خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-120.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-120.

#### `al-trn-120-boxed` — Swipe Up · Boxed
**سحب لفوق · صندوق**

*accent · any · depth · easing: easeInOutQuart · 0.4s*

*Original: M-120*

Variant of M-120: النص داخل صندوق ملون

**Spec (EN):** The outgoing clip slides up out of the top edge while the new clip slides up from the bottom edge at the same speed over 0.4s.

**Spec (AR):** المقطع الطالع يطلع لفوق من الحافة الفوق، والجديد يطلع من الحافة التحت بنفس السرعة خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-120.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-120.

#### `al-trn-267-fast` — Shape Morph · Fast
**شكل يتحول · سريع**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-267*

Variant of M-267: أسرع بـ 40%

**Spec (EN):** Interpolate between shapes (circle → rounded square → leaf) by animating corner radii and rotation, or by morphing matching SVG paths.

**Spec (AR):** انتقل بين الأشكال (دائرة ثم مربع دائري ثم ورقة) بتحريك الزوايا والدوران، أو بتحويل مسارات SVG متطابقة.

**When to use:**
- EN: Use when you need a fast version of M-267.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-267.

#### `al-trn-267-slow` — Shape Morph · Slow
**شكل يتحول · بطيء**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-267*

Variant of M-267: أبطأ بـ 60%

**Spec (EN):** Interpolate between shapes (circle → rounded square → leaf) by animating corner radii and rotation, or by morphing matching SVG paths.

**Spec (AR):** انتقل بين الأشكال (دائرة ثم مربع دائري ثم ورقة) بتحريك الزوايا والدوران، أو بتحويل مسارات SVG متطابقة.

**When to use:**
- EN: Use when you need a slow version of M-267.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-267.

#### `al-trn-267-gold` — Shape Morph · Gold
**شكل يتحول · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-267*

Variant of M-267: نسخة ذهبية فاخرة

**Spec (EN):** Interpolate between shapes (circle → rounded square → leaf) by animating corner radii and rotation, or by morphing matching SVG paths.

**Spec (AR):** انتقل بين الأشكال (دائرة ثم مربع دائري ثم ورقة) بتحريك الزوايا والدوران، أو بتحويل مسارات SVG متطابقة.

**When to use:**
- EN: Use when you need a gold version of M-267.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-267.

#### `al-trn-267-boxed` — Shape Morph · Boxed
**شكل يتحول · صندوق**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-267*

Variant of M-267: النص داخل صندوق ملون

**Spec (EN):** Interpolate between shapes (circle → rounded square → leaf) by animating corner radii and rotation, or by morphing matching SVG paths.

**Spec (AR):** انتقل بين الأشكال (دائرة ثم مربع دائري ثم ورقة) بتحريك الزوايا والدوران، أو بتحويل مسارات SVG متطابقة.

**When to use:**
- EN: Use when you need a boxed version of M-267.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-267.

#### `al-trn-268-fast` — Liquid Reveal · Fast
**انكشاف سائل · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.7s*

*Original: M-268*

Variant of M-268: أسرع بـ 40%

**Spec (EN):** An organic blob shape in the accent color grows from the center while its border radius wobbles, covers the frame, then fades to reveal the new clip.

**Spec (AR):** بقعة بشكل طبيعي بلون الهوية تكبر من النص وحوافها تتموج، تغطي الشاشة، وبعدين تختفي وتكشف المقطع الجديد.

**When to use:**
- EN: Use when you need a fast version of M-268.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-268.

#### `al-trn-268-slow` — Liquid Reveal · Slow
**انكشاف سائل · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.7s*

*Original: M-268*

Variant of M-268: أبطأ بـ 60%

**Spec (EN):** An organic blob shape in the accent color grows from the center while its border radius wobbles, covers the frame, then fades to reveal the new clip.

**Spec (AR):** بقعة بشكل طبيعي بلون الهوية تكبر من النص وحوافها تتموج، تغطي الشاشة، وبعدين تختفي وتكشف المقطع الجديد.

**When to use:**
- EN: Use when you need a slow version of M-268.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-268.

#### `al-trn-268-gold` — Liquid Reveal · Gold
**انكشاف سائل · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.7s*

*Original: M-268*

Variant of M-268: نسخة ذهبية فاخرة

**Spec (EN):** An organic blob shape in the accent color grows from the center while its border radius wobbles, covers the frame, then fades to reveal the new clip.

**Spec (AR):** بقعة بشكل طبيعي بلون الهوية تكبر من النص وحوافها تتموج، تغطي الشاشة، وبعدين تختفي وتكشف المقطع الجديد.

**When to use:**
- EN: Use when you need a gold version of M-268.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-268.

#### `al-trn-268-boxed` — Liquid Reveal · Boxed
**انكشاف سائل · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.7s*

*Original: M-268*

Variant of M-268: النص داخل صندوق ملون

**Spec (EN):** An organic blob shape in the accent color grows from the center while its border radius wobbles, covers the frame, then fades to reveal the new clip.

**Spec (AR):** بقعة بشكل طبيعي بلون الهوية تكبر من النص وحوافها تتموج، تغطي الشاشة، وبعدين تختفي وتكشف المقطع الجديد.

**When to use:**
- EN: Use when you need a boxed version of M-268.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-268.

#### `al-trn-269-fast` — Ink Splash Reveal · Fast
**انكشاف بقعة حبر · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.7s*

*Original: M-269*

Variant of M-269: أسرع بـ 40%

**Spec (EN):** Reveal the new clip through a mask of several overlapping circles (ink splash shape) that scales up from the center to cover the frame.

**Spec (AR):** اكشف المقطع الجديد من قناع فيه كم دائرة متداخلة (شكل بقعة حبر) يكبر من النص لين يغطي الشاشة.

**When to use:**
- EN: Use when you need a fast version of M-269.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-269.

#### `al-trn-269-slow` — Ink Splash Reveal · Slow
**انكشاف بقعة حبر · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.7s*

*Original: M-269*

Variant of M-269: أبطأ بـ 60%

**Spec (EN):** Reveal the new clip through a mask of several overlapping circles (ink splash shape) that scales up from the center to cover the frame.

**Spec (AR):** اكشف المقطع الجديد من قناع فيه كم دائرة متداخلة (شكل بقعة حبر) يكبر من النص لين يغطي الشاشة.

**When to use:**
- EN: Use when you need a slow version of M-269.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-269.

#### `al-trn-269-gold` — Ink Splash Reveal · Gold
**انكشاف بقعة حبر · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.7s*

*Original: M-269*

Variant of M-269: نسخة ذهبية فاخرة

**Spec (EN):** Reveal the new clip through a mask of several overlapping circles (ink splash shape) that scales up from the center to cover the frame.

**Spec (AR):** اكشف المقطع الجديد من قناع فيه كم دائرة متداخلة (شكل بقعة حبر) يكبر من النص لين يغطي الشاشة.

**When to use:**
- EN: Use when you need a gold version of M-269.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-269.

#### `al-trn-269-boxed` — Ink Splash Reveal · Boxed
**انكشاف بقعة حبر · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.7s*

*Original: M-269*

Variant of M-269: النص داخل صندوق ملون

**Spec (EN):** Reveal the new clip through a mask of several overlapping circles (ink splash shape) that scales up from the center to cover the frame.

**Spec (AR):** اكشف المقطع الجديد من قناع فيه كم دائرة متداخلة (شكل بقعة حبر) يكبر من النص لين يغطي الشاشة.

**When to use:**
- EN: Use when you need a boxed version of M-269.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-269.

#### `al-trn-270-fast` — Film Burn · Fast
**حرق فيلم · سريع**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-270*

Variant of M-270: أسرع بـ 40%

**Spec (EN):** A bright white-yellow-orange burn blob expands from one corner (screen blend), peaks at full brightness on the cut, then fades.

**Spec (AR):** بقعة حرق لامعة أبيض وأصفر وبرتقالي تكبر من زاوية (دمج screen)، توصل أقوى إضاءة عند القص، وبعدين تختفي.

**When to use:**
- EN: Use when you need a fast version of M-270.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-270.

#### `al-trn-270-slow` — Film Burn · Slow
**حرق فيلم · بطيء**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-270*

Variant of M-270: أبطأ بـ 60%

**Spec (EN):** A bright white-yellow-orange burn blob expands from one corner (screen blend), peaks at full brightness on the cut, then fades.

**Spec (AR):** بقعة حرق لامعة أبيض وأصفر وبرتقالي تكبر من زاوية (دمج screen)، توصل أقوى إضاءة عند القص، وبعدين تختفي.

**When to use:**
- EN: Use when you need a slow version of M-270.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-270.

#### `al-trn-270-gold` — Film Burn · Gold
**حرق فيلم · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-270*

Variant of M-270: نسخة ذهبية فاخرة

**Spec (EN):** A bright white-yellow-orange burn blob expands from one corner (screen blend), peaks at full brightness on the cut, then fades.

**Spec (AR):** بقعة حرق لامعة أبيض وأصفر وبرتقالي تكبر من زاوية (دمج screen)، توصل أقوى إضاءة عند القص، وبعدين تختفي.

**When to use:**
- EN: Use when you need a gold version of M-270.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-270.

#### `al-trn-270-boxed` — Film Burn · Boxed
**حرق فيلم · صندوق**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-270*

Variant of M-270: النص داخل صندوق ملون

**Spec (EN):** A bright white-yellow-orange burn blob expands from one corner (screen blend), peaks at full brightness on the cut, then fades.

**Spec (AR):** بقعة حرق لامعة أبيض وأصفر وبرتقالي تكبر من زاوية (دمج screen)، توصل أقوى إضاءة عند القص، وبعدين تختفي.

**When to use:**
- EN: Use when you need a boxed version of M-270.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-270.

#### `al-trn-271-fast` — Match Cut Slide · Fast
**انتقال بنفس الحركة · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-271*

Variant of M-271: أسرع بـ 40%

**Spec (EN):** Cut on the motion: the outgoing clip moves out in the direction of the action and the incoming clip continues the same direction and speed.

**Spec (AR):** اقطع على الحركة: المقطع الطالع يطلع باتجاه الحركة، والمقطع الداخل يكمل بنفس الاتجاه ونفس السرعة.

**When to use:**
- EN: Use when you need a fast version of M-271.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-271.

#### `al-trn-271-slow` — Match Cut Slide · Slow
**انتقال بنفس الحركة · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-271*

Variant of M-271: أبطأ بـ 60%

**Spec (EN):** Cut on the motion: the outgoing clip moves out in the direction of the action and the incoming clip continues the same direction and speed.

**Spec (AR):** اقطع على الحركة: المقطع الطالع يطلع باتجاه الحركة، والمقطع الداخل يكمل بنفس الاتجاه ونفس السرعة.

**When to use:**
- EN: Use when you need a slow version of M-271.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-271.

#### `al-trn-271-gold` — Match Cut Slide · Gold
**انتقال بنفس الحركة · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-271*

Variant of M-271: نسخة ذهبية فاخرة

**Spec (EN):** Cut on the motion: the outgoing clip moves out in the direction of the action and the incoming clip continues the same direction and speed.

**Spec (AR):** اقطع على الحركة: المقطع الطالع يطلع باتجاه الحركة، والمقطع الداخل يكمل بنفس الاتجاه ونفس السرعة.

**When to use:**
- EN: Use when you need a gold version of M-271.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-271.

#### `al-trn-271-boxed` — Match Cut Slide · Boxed
**انتقال بنفس الحركة · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.5s*

*Original: M-271*

Variant of M-271: النص داخل صندوق ملون

**Spec (EN):** Cut on the motion: the outgoing clip moves out in the direction of the action and the incoming clip continues the same direction and speed.

**Spec (AR):** اقطع على الحركة: المقطع الطالع يطلع باتجاه الحركة، والمقطع الداخل يكمل بنفس الاتجاه ونفس السرعة.

**When to use:**
- EN: Use when you need a boxed version of M-271.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-271.

### Camera (Alansari) (الكاميرا) — 125 motions

#### `al-cam-021` — Punch-In
**قفزة زوم**

*workhorse · any · timeline · easing: cut · instant (1 frame)*

*Original: M-021*

Hides cuts between lines, or stresses a line.

**Spec (EN):** The frame jumps instantly from 100% to 125% scale, centered on the face, on a cut or a key word. Hold, then jump back to 100% on the next cut. No easing.

**Spec (AR):** الصورة تنط مرة وحدة من 100% لـ 125% وبالنص على الوجه، عند القص أو كلمة مهمة. تثبت، وبعدين ترجع 100% عند القص اللي بعده. بدون easing.

**When to use:**
- EN: Hides cuts between lines, or stresses a line.
- AR: تخفي القص بين الجمل، أو تأكيد على جملة.

#### `al-cam-022` — Slow Push-In
**زوم بطيء**

*workhorse · calm · timeline · easing: linear / easeInOutSine · whole shot (3–6s)*

*Original: M-022*

A serious moment or a story.

**Spec (EN):** The frame scales smoothly from 100% to about 116% across the whole shot, centered slightly above the face.

**Spec (AR):** الصورة تكبر بنعومة من 100% لـ تقريباً 116% على طول اللقطة كاملة، والمركز فوق الوجه بشوي.

**When to use:**
- EN: A serious moment or a story.
- AR: لحظة جدية أو قصة.

#### `al-cam-023` — Camera Shake
**هزة كاميرا**

*workhorse · any · depth · easing: noise · 0.3–1s*

*Original: M-023*

With a hit, an explosion or a strong word.

**Spec (EN):** Overscale the frame to 108% to hide the edges, then shift it with random ±1.5% offsets and ±0.8° rotation, changing every 2–3 frames. Damp the shake toward the end.

**Spec (AR):** كبّر الصورة لـ 108% عشان الأطراف ما تبين، وبعدين حرّكها بإزاحات عشوائية ±1.5% ودوران ±0.8 درجة تتغير كل 2 إلى 3 فريمات. وخل الهزة تخف بالنهاية.

**When to use:**
- EN: With a hit, an explosion or a strong word.
- AR: مع ضربة أو انفجار أو كلمة قوية.

#### `al-cam-024` — Zoom-Out Card
**الفيديو يصغر لبطاقة**

*workhorse · high · depth · easing: easeInOutCubic + bounce · 0.6s out · 0.5s back*

*Original: M-024*

Like "zoom out", or to show something next to the video.

**Spec (EN):** The whole video shrinks to 60% scale with -3° tilt, about 48px rounded corners and a deep drop shadow over a dark patterned backdrop (0.6s). Hold, then it returns to full frame with a small 104% overshoot (0.5s).

**Spec (AR):** الفيديو كامل يصغر لـ 60% ويميل -3 درجات، وزواياه دائرية تقريباً 48px، مع ظل غامق فوق خلفية مزخرفة غامقة (0.6 ثانية). يثبت، وبعدين يرجع يملأ الشاشة مع تعدي خفيف لـ 104% (0.5 ثانية).

**When to use:**
- EN: Like "zoom out", or to show something next to the video.
- AR: مثل "زوم آوت"، أو لما تبي تعرض شي جنب الفيديو.

#### `al-cam-025` — Ken Burns
**حركة كين برنز**

*workhorse · calm · timeline · easing: easeInOutSine · whole shot (4–8s)*

*Original: M-025*

Bring a still photo to life.

**Spec (EN):** A still image slowly scales from 112% to 132% while panning diagonally by about 10% of the frame across the whole duration.

**Spec (AR):** صورة ثابتة تكبر ببطء من 112% لـ 132% وهي تتحرك قطرياً تقريباً 10% من الشاشة على طول المدة.

**When to use:**
- EN: Bring a still photo to life.
- AR: تحريك صورة ثابتة عشان تبين حية.

#### `al-cam-121` — Dolly Zoom
**زوم فيرتيغو**

*workhorse · calm · depth · easing: easeInOutSine · 1–2s*

*Original: M-121*

The background stretches while you stay put, a shock or realization.

**Spec (EN):** Using the person matte, scale the background layer from 100% to about 150% while scaling the person layer from 100% to about 86% from the bottom center, so the subject seems fixed while the room warps.

**Spec (AR):** باستخدام قناع الشخص، كبّر طبقة الخلفية من 100% لـ تقريباً 150% وصغّر طبقة الشخص من 100% لـ تقريباً 86% من النص تحت، فيبين الشخص ثابت والمكان ينسحب حوله.

**When to use:**
- EN: The background stretches while you stay put, a shock or realization.
- AR: الخلفية تكبر وانت تصغر، إحساس صدمة أو اكتشاف.

#### `al-cam-122` — Pan
**حركة كاميرا أفقية**

*workhorse · calm · timeline · easing: easeInOutSine · 2–4s*

*Original: M-122*

Moves the frame left and right across a shot or photo.

**Spec (EN):** Overscale the frame to 125% and move it horizontally from +8% to -8% of the width across the shot.

**Spec (AR):** كبّر الصورة لـ 125% وحرّكها أفقياً من +8% لـ -8% من العرض على طول اللقطة.

**When to use:**
- EN: Moves the frame left and right across a shot or photo.
- AR: تحريك الكاميرا يمين ويسار على لقطة أو صورة.

#### `al-cam-123` — Tilt Up
**حركة كاميرا عمودية**

*workhorse · calm · timeline · easing: easeInOutSine · 2–4s*

*Original: M-123*

The frame moves bottom to top, like revealing a person or building.

**Spec (EN):** Overscale the frame to 125% and move it vertically from +9% to -7% of the height across the shot.

**Spec (AR):** كبّر الصورة لـ 125% وحرّكها عمودياً من +9% لـ -7% من الطول على طول اللقطة.

**When to use:**
- EN: The frame moves bottom to top, like revealing a person or building.
- AR: الكاميرا تطلع من تحت لفوق، مثل كشف شخص أو مبنى.

#### `al-cam-124` — Rack Focus
**تغيير الفوكس**

*workhorse · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-124*

Focus shifts between the person and the background.

**Spec (EN):** Using the person matte, blur the background from 0 to about 1.2% while the person goes from 1.2% blur to sharp over 0.6s, or the reverse.

**Spec (AR):** باستخدام قناع الشخص، ضبّب الخلفية من 0 لـ تقريباً 1.2% والشخص يتحول من ضبابية 1.2% لواضح خلال 0.6 ثانية، أو العكس.

**When to use:**
- EN: Focus shifts between the person and the background.
- AR: الفوكس ينتقل من الشخص للخلفية أو العكس.

#### `al-cam-125` — Whip Zoom
**زوم خاطف**

*workhorse · any · blur · easing: easeOutExpo · 0.25s*

*Original: M-125*

A quick zoom with motion blur onto the face.

**Spec (EN):** Scale the frame to 150% with about 1.2% motion blur in 0.15s, then settle to 130% and sharp over 0.2s. Pair with a short whoosh.

**Spec (AR):** كبّر الصورة لـ 150% مع ضبابية حركة تقريباً 1.2% خلال 0.15 ثانية، وبعدين تستقر على 130% واضحة خلال 0.2 ثانية. حط معاها صوت ووش قصير.

**When to use:**
- EN: A quick zoom with motion blur onto the face.
- AR: زوم سريع مع ضبابية حركة على الوجه.

#### `al-cam-126` — Handheld Drift
**حركة يد خفيفة**

*workhorse · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-126*

Makes a locked-off shot feel handheld.

**Spec (EN):** Overscale to 108% and drift the frame slowly with small offsets (±1.2%) and rotation (±0.5°) on a smooth 4s path.

**Spec (AR):** كبّر لـ 108% وحرّك الصورة ببطء بإزاحات صغيرة (±1.2%) ودوران (±0.5 درجة) على مسار ناعم كل 4 ثواني.

**When to use:**
- EN: Makes a locked-off shot feel handheld.
- AR: تخلي اللقطة الثابتة تبين كأنها مصورة باليد.

#### `al-cam-127` — Dutch Tilt
**ميلان الكاميرا**

*workhorse · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-127*

Tilting the frame adds tension or unease.

**Spec (EN):** Rotate the frame to -9° while scaling to 120% to hide the corners over 0.5s, hold, then return.

**Spec (AR):** لف الصورة لـ -9 درجات وكبّرها لـ 120% عشان الزوايا ما تبين خلال 0.5 ثانية، ثبّت، وبعدين رجّعها.

**When to use:**
- EN: Tilting the frame adds tension or unease.
- AR: ميلان الكادر يعطي توتر أو غرابة.

#### `al-cam-128` — Snap Zoom Out
**زوم آوت سريع**

*workhorse · any · timeline · easing: easeOutExpo · 0.2s*

*Original: M-128*

Starts close then snaps wide to show the whole scene.

**Spec (EN):** Start at 150% on a detail, then snap out to 100% in about 0.2s on a beat or word.

**Spec (AR):** ابدأ على 150% على تفصيلة، وبعدين ابعد فجأة لـ 100% خلال تقريباً 0.2 ثانية على الإيقاع أو الكلمة.

**When to use:**
- EN: Starts close then snaps wide to show the whole scene.
- AR: تبدأ قريب وفجأة تبعد وتبين المكان كامل.

#### `al-cam-129` — Crash Zoom
**زوم صادم**

*workhorse · any · timeline · easing: easeOutExpo · 0.2s + 0.3s shake*

*Original: M-129*

A hard zoom onto the face with a shake, for surprise.

**Spec (EN):** Snap the frame to about 190% centered on the face in 0.15s, add a short horizontal shake (±1.5%), then hold. Pair with a dramatic hit.

**Spec (AR):** كبّر الصورة لـ تقريباً 190% على الوجه خلال 0.15 ثانية، وحط هزة أفقية قصيرة (±1.5%)، وثبّت. حط معاها ضربة صوت درامية.

**When to use:**
- EN: A hard zoom onto the face with a shake, for surprise.
- AR: زوم قوي جداً على الوجه مع هزة، للمفاجأة.

#### `al-cam-130` — Orbit
**دوران حول الشخص**

*workhorse · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-130*

Feels like the camera is circling you slightly.

**Spec (EN):** Apply a 3D Y-axis rotation of ±14° with perspective and a 112% scale, swinging smoothly every 4s.

**Spec (AR):** طبّق دوران 3D على المحور العمودي ±14 درجة مع عمق وتكبير 112%، يتأرجح بنعومة كل 4 ثواني.

**When to use:**
- EN: Feels like the camera is circling you slightly.
- AR: إحساس إن الكاميرا تدور حولك بخفة.

#### `al-cam-131` — Double Punch
**زوم مرتين**

*workhorse · any · timeline · easing: cut · 2 cuts*

*Original: M-131*

Two punch-ins in a row for strong emphasis.

**Spec (EN):** Jump to 115% on the first beat and to 132% on the second, with no easing, then cut back to 100%.

**Spec (AR):** نط لـ 115% على أول إيقاع ولـ 132% على الثاني، بدون easing، وبعدين ارجع 100% بقص.

**When to use:**
- EN: Two punch-ins in a row for strong emphasis.
- AR: قفزتين زوم ورا بعض للتأكيد القوي.

#### `al-cam-132` — Split Screen
**شاشة مقسومة**

*workhorse · any · timeline · easing: easeOutCubic · 0.5s in*

*Original: M-132*

Shows two shots side by side, like a comparison.

**Spec (EN):** Two clips slide in from the left and right edges into each half of the frame over 0.5s, with a thin gap between them.

**Spec (AR):** مقطعين يدخلون من الحافة اليمين واليسار كل واحد بنص الشاشة خلال 0.5 ثانية، وبينهم فاصل رفيع.

**When to use:**
- EN: Shows two shots side by side, like a comparison.
- AR: تعرض لقطتين جنب بعض، مثل قبل وبعد أو مقارنة.

#### `al-cam-133` — Picture in Picture
**صورة داخل صورة**

*workhorse · high · depth · easing: easeOutBack · 0.4s in*

*Original: M-133*

A small video in the corner, like a reaction cam.

**Spec (EN):** A rounded window with a white border and shadow (about 38% of the width) pops into the top corner from scale 0 over 0.4s and plays the second clip.

**Spec (AR):** نافذة بزوايا دائرية بإطار أبيض وظل (تقريباً 38% من العرض) تنط بالزاوية الفوق من حجم 0 خلال 0.4 ثانية، وتعرض المقطع الثاني.

**When to use:**
- EN: A small video in the corner, like a reaction cam.
- AR: فيديو صغير بزاوية الشاشة، مثل رياكشن.

#### `al-cam-134` — Mirror Flip
**قلب الصورة**

*workhorse · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-134*

The frame flips horizontally, like "the opposite is true".

**Spec (EN):** Flip the frame horizontally (scaleX from 1 to -1) over 0.5s, hold, then flip back.

**Spec (AR):** اقلب الصورة أفقياً (scaleX من 1 لـ -1) خلال 0.5 ثانية، ثبّت، وبعدين رجّعها.

**When to use:**
- EN: The frame flips horizontally, like "the opposite is true".
- AR: الصورة تنقلب أفقياً، مثل "العكس صحيح".

#### `al-cam-135` — Freeze Frame
**تجميد اللقطة**

*workhorse · any · depth · easing: cut · hold 1–2s*

*Original: M-135*

The shot freezes with muted color and a tag.

**Spec (EN):** On the chosen frame, hold the image, desaturate it about 85% with a little more contrast, and pop a small label tag. Resume playback after the hold.

**Spec (AR):** على الفريم المختار، ثبّت الصورة، وخفف ألوانها تقريباً 85% مع تباين أكثر شوي، وطلّع تاق صغير. وكمّل التشغيل بعد التثبيت.

**When to use:**
- EN: The shot freezes with muted color and a tag.
- AR: اللقطة توقف فجأة مع ألوان باهتة وتاق.

#### `al-cam-136` — Slow Motion
**تبطيء الحركة**

*workhorse · any · depth · easing: easeOutCubic · ramp 0.2s*

*Original: M-136*

An important moment slows down so viewers catch it.

**Spec (EN):** Ramp the clip speed from 100% down to about 25% over 0.2s at the key moment (use frame blending or interpolation), hold, then ramp back.

**Spec (AR):** نزّل سرعة المقطع من 100% لـ تقريباً 25% خلال 0.2 ثانية عند اللحظة المهمة (بدمج الفريمات أو توليد فريمات)، ثبّت، وبعدين رجّع السرعة.

**When to use:**
- EN: An important moment slows down so viewers catch it.
- AR: لحظة مهمة تتبطأ عشان المشاهد يشوفها.

#### `al-cam-137` — Speed Ramp
**تسريع وتبطيء**

*workhorse · any · timeline · easing: custom curve · 0.8s*

*Original: M-137*

Motion slows then speeds up suddenly, action style.

**Spec (EN):** Combine a slow push (100% to 104%) with a sudden fast push to 130% in about 0.15s, then ease into a slow drift. Time the fast part to the beat.

**Spec (AR):** ادمج زوم بطيء (100% لـ 104%) مع زوم سريع مفاجئ لـ 130% خلال تقريباً 0.15 ثانية، وبعدين حركة بطيئة ناعمة. وخل الجزء السريع على الإيقاع.

**When to use:**
- EN: Motion slows then speeds up suddenly, action style.
- AR: الحركة تبطّي وبعدين تسرع فجأة، ستايل الأكشن.

#### `al-cam-138` — Letterbox Bars
**أشرطة سينمائية**

*workhorse · any · depth · easing: easeInOutCubic · 0.5s in*

*Original: M-138*

Black bars top and bottom for a film look.

**Spec (EN):** Two black bars slide in from the top and bottom edges over 0.5s, each about 16% of the width tall, and stay during the cinematic part.

**Spec (AR):** شريطين سود يدخلون من الحافة الفوق والتحت خلال 0.5 ثانية، كل واحد ارتفاعه تقريباً 16% من العرض، ويبقون طول الجزء السينمائي.

**When to use:**
- EN: Black bars top and bottom for a film look.
- AR: أشرطة سودا فوق وتحت تعطي إحساس فيلم.

#### `al-cam-139` — Vignette Focus
**تعتيم الأطراف**

*workhorse · calm · timeline · easing: easeInOutSine · 0.6s in*

*Original: M-139*

The edges darken so the eye goes to the face.

**Spec (EN):** Fade in an elliptical dark vignette (transparent center, about 90% black at the edges) over 0.6s around the face.

**Spec (AR):** طبقة تعتيم بيضاوية (النص شفاف والأطراف تقريباً 90% أسود) تظهر خلال 0.6 ثانية حول الوجه.

**When to use:**
- EN: The edges darken so the eye goes to the face.
- AR: أطراف الشاشة تغمق عشان العين تروح للوجه.

#### `al-cam-140` — Bounce Zoom
**زوم بارتداد**

*workhorse · any · timeline · easing: spring · 0.5s*

*Original: M-140*

A zoom that bounces a little before settling.

**Spec (EN):** Zoom to 132%, bounce back to 116%, then 124%, and settle at 122% over about 0.5s.

**Spec (AR):** زوم لـ 132%، يرتد لـ 116%، وبعدين 124%، ويستقر على 122% خلال تقريباً 0.5 ثانية.

**When to use:**
- EN: A zoom that bounces a little before settling.
- AR: زوم سريع يرتد شوي قبل ما يثبت.

#### `al-cam-021-fast` — Punch-In · Fast
**قفزة زوم · سريع**

*accent · any · timeline · easing: cut · instant (1 frame)*

*Original: M-021*

Variant of M-021: أسرع بـ 40%

**Spec (EN):** The frame jumps instantly from 100% to 125% scale, centered on the face, on a cut or a key word. Hold, then jump back to 100% on the next cut. No easing.

**Spec (AR):** الصورة تنط مرة وحدة من 100% لـ 125% وبالنص على الوجه، عند القص أو كلمة مهمة. تثبت، وبعدين ترجع 100% عند القص اللي بعده. بدون easing.

**When to use:**
- EN: Use when you need a fast version of M-021.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-021.

#### `al-cam-021-slow` — Punch-In · Slow
**قفزة زوم · بطيء**

*accent · any · timeline · easing: cut · instant (1 frame)*

*Original: M-021*

Variant of M-021: أبطأ بـ 60%

**Spec (EN):** The frame jumps instantly from 100% to 125% scale, centered on the face, on a cut or a key word. Hold, then jump back to 100% on the next cut. No easing.

**Spec (AR):** الصورة تنط مرة وحدة من 100% لـ 125% وبالنص على الوجه، عند القص أو كلمة مهمة. تثبت، وبعدين ترجع 100% عند القص اللي بعده. بدون easing.

**When to use:**
- EN: Use when you need a slow version of M-021.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-021.

#### `al-cam-021-gold` — Punch-In · Gold
**قفزة زوم · ذهبي**

*accent · any · timeline · easing: cut · instant (1 frame)*

*Original: M-021*

Variant of M-021: نسخة ذهبية فاخرة

**Spec (EN):** The frame jumps instantly from 100% to 125% scale, centered on the face, on a cut or a key word. Hold, then jump back to 100% on the next cut. No easing.

**Spec (AR):** الصورة تنط مرة وحدة من 100% لـ 125% وبالنص على الوجه، عند القص أو كلمة مهمة. تثبت، وبعدين ترجع 100% عند القص اللي بعده. بدون easing.

**When to use:**
- EN: Use when you need a gold version of M-021.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-021.

#### `al-cam-021-boxed` — Punch-In · Boxed
**قفزة زوم · صندوق**

*accent · any · timeline · easing: cut · instant (1 frame)*

*Original: M-021*

Variant of M-021: النص داخل صندوق ملون

**Spec (EN):** The frame jumps instantly from 100% to 125% scale, centered on the face, on a cut or a key word. Hold, then jump back to 100% on the next cut. No easing.

**Spec (AR):** الصورة تنط مرة وحدة من 100% لـ 125% وبالنص على الوجه، عند القص أو كلمة مهمة. تثبت، وبعدين ترجع 100% عند القص اللي بعده. بدون easing.

**When to use:**
- EN: Use when you need a boxed version of M-021.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-021.

#### `al-cam-022-fast` — Slow Push-In · Fast
**زوم بطيء · سريع**

*accent · calm · timeline · easing: linear / easeInOutSine · whole shot (3–6s)*

*Original: M-022*

Variant of M-022: أسرع بـ 40%

**Spec (EN):** The frame scales smoothly from 100% to about 116% across the whole shot, centered slightly above the face.

**Spec (AR):** الصورة تكبر بنعومة من 100% لـ تقريباً 116% على طول اللقطة كاملة، والمركز فوق الوجه بشوي.

**When to use:**
- EN: Use when you need a fast version of M-022.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-022.

#### `al-cam-022-slow` — Slow Push-In · Slow
**زوم بطيء · بطيء**

*accent · calm · timeline · easing: linear / easeInOutSine · whole shot (3–6s)*

*Original: M-022*

Variant of M-022: أبطأ بـ 60%

**Spec (EN):** The frame scales smoothly from 100% to about 116% across the whole shot, centered slightly above the face.

**Spec (AR):** الصورة تكبر بنعومة من 100% لـ تقريباً 116% على طول اللقطة كاملة، والمركز فوق الوجه بشوي.

**When to use:**
- EN: Use when you need a slow version of M-022.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-022.

#### `al-cam-022-gold` — Slow Push-In · Gold
**زوم بطيء · ذهبي**

*accent · calm · timeline · easing: linear / easeInOutSine · whole shot (3–6s)*

*Original: M-022*

Variant of M-022: نسخة ذهبية فاخرة

**Spec (EN):** The frame scales smoothly from 100% to about 116% across the whole shot, centered slightly above the face.

**Spec (AR):** الصورة تكبر بنعومة من 100% لـ تقريباً 116% على طول اللقطة كاملة، والمركز فوق الوجه بشوي.

**When to use:**
- EN: Use when you need a gold version of M-022.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-022.

#### `al-cam-022-boxed` — Slow Push-In · Boxed
**زوم بطيء · صندوق**

*accent · calm · timeline · easing: linear / easeInOutSine · whole shot (3–6s)*

*Original: M-022*

Variant of M-022: النص داخل صندوق ملون

**Spec (EN):** The frame scales smoothly from 100% to about 116% across the whole shot, centered slightly above the face.

**Spec (AR):** الصورة تكبر بنعومة من 100% لـ تقريباً 116% على طول اللقطة كاملة، والمركز فوق الوجه بشوي.

**When to use:**
- EN: Use when you need a boxed version of M-022.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-022.

#### `al-cam-023-fast` — Camera Shake · Fast
**هزة كاميرا · سريع**

*accent · any · depth · easing: noise · 0.3–1s*

*Original: M-023*

Variant of M-023: أسرع بـ 40%

**Spec (EN):** Overscale the frame to 108% to hide the edges, then shift it with random ±1.5% offsets and ±0.8° rotation, changing every 2–3 frames. Damp the shake toward the end.

**Spec (AR):** كبّر الصورة لـ 108% عشان الأطراف ما تبين، وبعدين حرّكها بإزاحات عشوائية ±1.5% ودوران ±0.8 درجة تتغير كل 2 إلى 3 فريمات. وخل الهزة تخف بالنهاية.

**When to use:**
- EN: Use when you need a fast version of M-023.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-023.

#### `al-cam-023-slow` — Camera Shake · Slow
**هزة كاميرا · بطيء**

*accent · any · depth · easing: noise · 0.3–1s*

*Original: M-023*

Variant of M-023: أبطأ بـ 60%

**Spec (EN):** Overscale the frame to 108% to hide the edges, then shift it with random ±1.5% offsets and ±0.8° rotation, changing every 2–3 frames. Damp the shake toward the end.

**Spec (AR):** كبّر الصورة لـ 108% عشان الأطراف ما تبين، وبعدين حرّكها بإزاحات عشوائية ±1.5% ودوران ±0.8 درجة تتغير كل 2 إلى 3 فريمات. وخل الهزة تخف بالنهاية.

**When to use:**
- EN: Use when you need a slow version of M-023.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-023.

#### `al-cam-023-gold` — Camera Shake · Gold
**هزة كاميرا · ذهبي**

*accent · any · depth · easing: noise · 0.3–1s*

*Original: M-023*

Variant of M-023: نسخة ذهبية فاخرة

**Spec (EN):** Overscale the frame to 108% to hide the edges, then shift it with random ±1.5% offsets and ±0.8° rotation, changing every 2–3 frames. Damp the shake toward the end.

**Spec (AR):** كبّر الصورة لـ 108% عشان الأطراف ما تبين، وبعدين حرّكها بإزاحات عشوائية ±1.5% ودوران ±0.8 درجة تتغير كل 2 إلى 3 فريمات. وخل الهزة تخف بالنهاية.

**When to use:**
- EN: Use when you need a gold version of M-023.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-023.

#### `al-cam-023-boxed` — Camera Shake · Boxed
**هزة كاميرا · صندوق**

*accent · any · depth · easing: noise · 0.3–1s*

*Original: M-023*

Variant of M-023: النص داخل صندوق ملون

**Spec (EN):** Overscale the frame to 108% to hide the edges, then shift it with random ±1.5% offsets and ±0.8° rotation, changing every 2–3 frames. Damp the shake toward the end.

**Spec (AR):** كبّر الصورة لـ 108% عشان الأطراف ما تبين، وبعدين حرّكها بإزاحات عشوائية ±1.5% ودوران ±0.8 درجة تتغير كل 2 إلى 3 فريمات. وخل الهزة تخف بالنهاية.

**When to use:**
- EN: Use when you need a boxed version of M-023.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-023.

#### `al-cam-024-fast` — Zoom-Out Card · Fast
**الفيديو يصغر لبطاقة · سريع**

*accent · any · depth · easing: easeInOutCubic + bounce · 0.6s out · 0.5s back*

*Original: M-024*

Variant of M-024: أسرع بـ 40%

**Spec (EN):** The whole video shrinks to 60% scale with -3° tilt, about 48px rounded corners and a deep drop shadow over a dark patterned backdrop (0.6s). Hold, then it returns to full frame with a small 104% overshoot (0.5s).

**Spec (AR):** الفيديو كامل يصغر لـ 60% ويميل -3 درجات، وزواياه دائرية تقريباً 48px، مع ظل غامق فوق خلفية مزخرفة غامقة (0.6 ثانية). يثبت، وبعدين يرجع يملأ الشاشة مع تعدي خفيف لـ 104% (0.5 ثانية).

**When to use:**
- EN: Use when you need a fast version of M-024.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-024.

#### `al-cam-024-slow` — Zoom-Out Card · Slow
**الفيديو يصغر لبطاقة · بطيء**

*accent · any · depth · easing: easeInOutCubic + bounce · 0.6s out · 0.5s back*

*Original: M-024*

Variant of M-024: أبطأ بـ 60%

**Spec (EN):** The whole video shrinks to 60% scale with -3° tilt, about 48px rounded corners and a deep drop shadow over a dark patterned backdrop (0.6s). Hold, then it returns to full frame with a small 104% overshoot (0.5s).

**Spec (AR):** الفيديو كامل يصغر لـ 60% ويميل -3 درجات، وزواياه دائرية تقريباً 48px، مع ظل غامق فوق خلفية مزخرفة غامقة (0.6 ثانية). يثبت، وبعدين يرجع يملأ الشاشة مع تعدي خفيف لـ 104% (0.5 ثانية).

**When to use:**
- EN: Use when you need a slow version of M-024.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-024.

#### `al-cam-024-gold` — Zoom-Out Card · Gold
**الفيديو يصغر لبطاقة · ذهبي**

*accent · any · depth · easing: easeInOutCubic + bounce · 0.6s out · 0.5s back*

*Original: M-024*

Variant of M-024: نسخة ذهبية فاخرة

**Spec (EN):** The whole video shrinks to 60% scale with -3° tilt, about 48px rounded corners and a deep drop shadow over a dark patterned backdrop (0.6s). Hold, then it returns to full frame with a small 104% overshoot (0.5s).

**Spec (AR):** الفيديو كامل يصغر لـ 60% ويميل -3 درجات، وزواياه دائرية تقريباً 48px، مع ظل غامق فوق خلفية مزخرفة غامقة (0.6 ثانية). يثبت، وبعدين يرجع يملأ الشاشة مع تعدي خفيف لـ 104% (0.5 ثانية).

**When to use:**
- EN: Use when you need a gold version of M-024.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-024.

#### `al-cam-024-boxed` — Zoom-Out Card · Boxed
**الفيديو يصغر لبطاقة · صندوق**

*accent · any · depth · easing: easeInOutCubic + bounce · 0.6s out · 0.5s back*

*Original: M-024*

Variant of M-024: النص داخل صندوق ملون

**Spec (EN):** The whole video shrinks to 60% scale with -3° tilt, about 48px rounded corners and a deep drop shadow over a dark patterned backdrop (0.6s). Hold, then it returns to full frame with a small 104% overshoot (0.5s).

**Spec (AR):** الفيديو كامل يصغر لـ 60% ويميل -3 درجات، وزواياه دائرية تقريباً 48px، مع ظل غامق فوق خلفية مزخرفة غامقة (0.6 ثانية). يثبت، وبعدين يرجع يملأ الشاشة مع تعدي خفيف لـ 104% (0.5 ثانية).

**When to use:**
- EN: Use when you need a boxed version of M-024.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-024.

#### `al-cam-025-fast` — Ken Burns · Fast
**حركة كين برنز · سريع**

*accent · calm · timeline · easing: easeInOutSine · whole shot (4–8s)*

*Original: M-025*

Variant of M-025: أسرع بـ 40%

**Spec (EN):** A still image slowly scales from 112% to 132% while panning diagonally by about 10% of the frame across the whole duration.

**Spec (AR):** صورة ثابتة تكبر ببطء من 112% لـ 132% وهي تتحرك قطرياً تقريباً 10% من الشاشة على طول المدة.

**When to use:**
- EN: Use when you need a fast version of M-025.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-025.

#### `al-cam-025-slow` — Ken Burns · Slow
**حركة كين برنز · بطيء**

*accent · calm · timeline · easing: easeInOutSine · whole shot (4–8s)*

*Original: M-025*

Variant of M-025: أبطأ بـ 60%

**Spec (EN):** A still image slowly scales from 112% to 132% while panning diagonally by about 10% of the frame across the whole duration.

**Spec (AR):** صورة ثابتة تكبر ببطء من 112% لـ 132% وهي تتحرك قطرياً تقريباً 10% من الشاشة على طول المدة.

**When to use:**
- EN: Use when you need a slow version of M-025.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-025.

#### `al-cam-025-gold` — Ken Burns · Gold
**حركة كين برنز · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · whole shot (4–8s)*

*Original: M-025*

Variant of M-025: نسخة ذهبية فاخرة

**Spec (EN):** A still image slowly scales from 112% to 132% while panning diagonally by about 10% of the frame across the whole duration.

**Spec (AR):** صورة ثابتة تكبر ببطء من 112% لـ 132% وهي تتحرك قطرياً تقريباً 10% من الشاشة على طول المدة.

**When to use:**
- EN: Use when you need a gold version of M-025.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-025.

#### `al-cam-025-boxed` — Ken Burns · Boxed
**حركة كين برنز · صندوق**

*accent · calm · timeline · easing: easeInOutSine · whole shot (4–8s)*

*Original: M-025*

Variant of M-025: النص داخل صندوق ملون

**Spec (EN):** A still image slowly scales from 112% to 132% while panning diagonally by about 10% of the frame across the whole duration.

**Spec (AR):** صورة ثابتة تكبر ببطء من 112% لـ 132% وهي تتحرك قطرياً تقريباً 10% من الشاشة على طول المدة.

**When to use:**
- EN: Use when you need a boxed version of M-025.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-025.

#### `al-cam-121-fast` — Dolly Zoom · Fast
**زوم فيرتيغو · سريع**

*accent · calm · depth · easing: easeInOutSine · 1–2s*

*Original: M-121*

Variant of M-121: أسرع بـ 40%

**Spec (EN):** Using the person matte, scale the background layer from 100% to about 150% while scaling the person layer from 100% to about 86% from the bottom center, so the subject seems fixed while the room warps.

**Spec (AR):** باستخدام قناع الشخص، كبّر طبقة الخلفية من 100% لـ تقريباً 150% وصغّر طبقة الشخص من 100% لـ تقريباً 86% من النص تحت، فيبين الشخص ثابت والمكان ينسحب حوله.

**When to use:**
- EN: Use when you need a fast version of M-121.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-121.

#### `al-cam-121-slow` — Dolly Zoom · Slow
**زوم فيرتيغو · بطيء**

*accent · calm · depth · easing: easeInOutSine · 1–2s*

*Original: M-121*

Variant of M-121: أبطأ بـ 60%

**Spec (EN):** Using the person matte, scale the background layer from 100% to about 150% while scaling the person layer from 100% to about 86% from the bottom center, so the subject seems fixed while the room warps.

**Spec (AR):** باستخدام قناع الشخص، كبّر طبقة الخلفية من 100% لـ تقريباً 150% وصغّر طبقة الشخص من 100% لـ تقريباً 86% من النص تحت، فيبين الشخص ثابت والمكان ينسحب حوله.

**When to use:**
- EN: Use when you need a slow version of M-121.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-121.

#### `al-cam-121-gold` — Dolly Zoom · Gold
**زوم فيرتيغو · ذهبي**

*accent · calm · depth · easing: easeInOutSine · 1–2s*

*Original: M-121*

Variant of M-121: نسخة ذهبية فاخرة

**Spec (EN):** Using the person matte, scale the background layer from 100% to about 150% while scaling the person layer from 100% to about 86% from the bottom center, so the subject seems fixed while the room warps.

**Spec (AR):** باستخدام قناع الشخص، كبّر طبقة الخلفية من 100% لـ تقريباً 150% وصغّر طبقة الشخص من 100% لـ تقريباً 86% من النص تحت، فيبين الشخص ثابت والمكان ينسحب حوله.

**When to use:**
- EN: Use when you need a gold version of M-121.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-121.

#### `al-cam-121-boxed` — Dolly Zoom · Boxed
**زوم فيرتيغو · صندوق**

*accent · calm · depth · easing: easeInOutSine · 1–2s*

*Original: M-121*

Variant of M-121: النص داخل صندوق ملون

**Spec (EN):** Using the person matte, scale the background layer from 100% to about 150% while scaling the person layer from 100% to about 86% from the bottom center, so the subject seems fixed while the room warps.

**Spec (AR):** باستخدام قناع الشخص، كبّر طبقة الخلفية من 100% لـ تقريباً 150% وصغّر طبقة الشخص من 100% لـ تقريباً 86% من النص تحت، فيبين الشخص ثابت والمكان ينسحب حوله.

**When to use:**
- EN: Use when you need a boxed version of M-121.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-121.

#### `al-cam-122-fast` — Pan · Fast
**حركة كاميرا أفقية · سريع**

*accent · calm · timeline · easing: easeInOutSine · 2–4s*

*Original: M-122*

Variant of M-122: أسرع بـ 40%

**Spec (EN):** Overscale the frame to 125% and move it horizontally from +8% to -8% of the width across the shot.

**Spec (AR):** كبّر الصورة لـ 125% وحرّكها أفقياً من +8% لـ -8% من العرض على طول اللقطة.

**When to use:**
- EN: Use when you need a fast version of M-122.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-122.

#### `al-cam-122-slow` — Pan · Slow
**حركة كاميرا أفقية · بطيء**

*accent · calm · timeline · easing: easeInOutSine · 2–4s*

*Original: M-122*

Variant of M-122: أبطأ بـ 60%

**Spec (EN):** Overscale the frame to 125% and move it horizontally from +8% to -8% of the width across the shot.

**Spec (AR):** كبّر الصورة لـ 125% وحرّكها أفقياً من +8% لـ -8% من العرض على طول اللقطة.

**When to use:**
- EN: Use when you need a slow version of M-122.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-122.

#### `al-cam-122-gold` — Pan · Gold
**حركة كاميرا أفقية · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · 2–4s*

*Original: M-122*

Variant of M-122: نسخة ذهبية فاخرة

**Spec (EN):** Overscale the frame to 125% and move it horizontally from +8% to -8% of the width across the shot.

**Spec (AR):** كبّر الصورة لـ 125% وحرّكها أفقياً من +8% لـ -8% من العرض على طول اللقطة.

**When to use:**
- EN: Use when you need a gold version of M-122.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-122.

#### `al-cam-122-boxed` — Pan · Boxed
**حركة كاميرا أفقية · صندوق**

*accent · calm · timeline · easing: easeInOutSine · 2–4s*

*Original: M-122*

Variant of M-122: النص داخل صندوق ملون

**Spec (EN):** Overscale the frame to 125% and move it horizontally from +8% to -8% of the width across the shot.

**Spec (AR):** كبّر الصورة لـ 125% وحرّكها أفقياً من +8% لـ -8% من العرض على طول اللقطة.

**When to use:**
- EN: Use when you need a boxed version of M-122.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-122.

#### `al-cam-123-fast` — Tilt Up · Fast
**حركة كاميرا عمودية · سريع**

*accent · calm · timeline · easing: easeInOutSine · 2–4s*

*Original: M-123*

Variant of M-123: أسرع بـ 40%

**Spec (EN):** Overscale the frame to 125% and move it vertically from +9% to -7% of the height across the shot.

**Spec (AR):** كبّر الصورة لـ 125% وحرّكها عمودياً من +9% لـ -7% من الطول على طول اللقطة.

**When to use:**
- EN: Use when you need a fast version of M-123.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-123.

#### `al-cam-123-slow` — Tilt Up · Slow
**حركة كاميرا عمودية · بطيء**

*accent · calm · timeline · easing: easeInOutSine · 2–4s*

*Original: M-123*

Variant of M-123: أبطأ بـ 60%

**Spec (EN):** Overscale the frame to 125% and move it vertically from +9% to -7% of the height across the shot.

**Spec (AR):** كبّر الصورة لـ 125% وحرّكها عمودياً من +9% لـ -7% من الطول على طول اللقطة.

**When to use:**
- EN: Use when you need a slow version of M-123.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-123.

#### `al-cam-123-gold` — Tilt Up · Gold
**حركة كاميرا عمودية · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · 2–4s*

*Original: M-123*

Variant of M-123: نسخة ذهبية فاخرة

**Spec (EN):** Overscale the frame to 125% and move it vertically from +9% to -7% of the height across the shot.

**Spec (AR):** كبّر الصورة لـ 125% وحرّكها عمودياً من +9% لـ -7% من الطول على طول اللقطة.

**When to use:**
- EN: Use when you need a gold version of M-123.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-123.

#### `al-cam-123-boxed` — Tilt Up · Boxed
**حركة كاميرا عمودية · صندوق**

*accent · calm · timeline · easing: easeInOutSine · 2–4s*

*Original: M-123*

Variant of M-123: النص داخل صندوق ملون

**Spec (EN):** Overscale the frame to 125% and move it vertically from +9% to -7% of the height across the shot.

**Spec (AR):** كبّر الصورة لـ 125% وحرّكها عمودياً من +9% لـ -7% من الطول على طول اللقطة.

**When to use:**
- EN: Use when you need a boxed version of M-123.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-123.

#### `al-cam-124-fast` — Rack Focus · Fast
**تغيير الفوكس · سريع**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-124*

Variant of M-124: أسرع بـ 40%

**Spec (EN):** Using the person matte, blur the background from 0 to about 1.2% while the person goes from 1.2% blur to sharp over 0.6s, or the reverse.

**Spec (AR):** باستخدام قناع الشخص، ضبّب الخلفية من 0 لـ تقريباً 1.2% والشخص يتحول من ضبابية 1.2% لواضح خلال 0.6 ثانية، أو العكس.

**When to use:**
- EN: Use when you need a fast version of M-124.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-124.

#### `al-cam-124-slow` — Rack Focus · Slow
**تغيير الفوكس · بطيء**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-124*

Variant of M-124: أبطأ بـ 60%

**Spec (EN):** Using the person matte, blur the background from 0 to about 1.2% while the person goes from 1.2% blur to sharp over 0.6s, or the reverse.

**Spec (AR):** باستخدام قناع الشخص، ضبّب الخلفية من 0 لـ تقريباً 1.2% والشخص يتحول من ضبابية 1.2% لواضح خلال 0.6 ثانية، أو العكس.

**When to use:**
- EN: Use when you need a slow version of M-124.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-124.

#### `al-cam-124-gold` — Rack Focus · Gold
**تغيير الفوكس · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-124*

Variant of M-124: نسخة ذهبية فاخرة

**Spec (EN):** Using the person matte, blur the background from 0 to about 1.2% while the person goes from 1.2% blur to sharp over 0.6s, or the reverse.

**Spec (AR):** باستخدام قناع الشخص، ضبّب الخلفية من 0 لـ تقريباً 1.2% والشخص يتحول من ضبابية 1.2% لواضح خلال 0.6 ثانية، أو العكس.

**When to use:**
- EN: Use when you need a gold version of M-124.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-124.

#### `al-cam-124-boxed` — Rack Focus · Boxed
**تغيير الفوكس · صندوق**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-124*

Variant of M-124: النص داخل صندوق ملون

**Spec (EN):** Using the person matte, blur the background from 0 to about 1.2% while the person goes from 1.2% blur to sharp over 0.6s, or the reverse.

**Spec (AR):** باستخدام قناع الشخص، ضبّب الخلفية من 0 لـ تقريباً 1.2% والشخص يتحول من ضبابية 1.2% لواضح خلال 0.6 ثانية، أو العكس.

**When to use:**
- EN: Use when you need a boxed version of M-124.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-124.

#### `al-cam-125-fast` — Whip Zoom · Fast
**زوم خاطف · سريع**

*accent · any · blur · easing: easeOutExpo · 0.25s*

*Original: M-125*

Variant of M-125: أسرع بـ 40%

**Spec (EN):** Scale the frame to 150% with about 1.2% motion blur in 0.15s, then settle to 130% and sharp over 0.2s. Pair with a short whoosh.

**Spec (AR):** كبّر الصورة لـ 150% مع ضبابية حركة تقريباً 1.2% خلال 0.15 ثانية، وبعدين تستقر على 130% واضحة خلال 0.2 ثانية. حط معاها صوت ووش قصير.

**When to use:**
- EN: Use when you need a fast version of M-125.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-125.

#### `al-cam-125-slow` — Whip Zoom · Slow
**زوم خاطف · بطيء**

*accent · any · blur · easing: easeOutExpo · 0.25s*

*Original: M-125*

Variant of M-125: أبطأ بـ 60%

**Spec (EN):** Scale the frame to 150% with about 1.2% motion blur in 0.15s, then settle to 130% and sharp over 0.2s. Pair with a short whoosh.

**Spec (AR):** كبّر الصورة لـ 150% مع ضبابية حركة تقريباً 1.2% خلال 0.15 ثانية، وبعدين تستقر على 130% واضحة خلال 0.2 ثانية. حط معاها صوت ووش قصير.

**When to use:**
- EN: Use when you need a slow version of M-125.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-125.

#### `al-cam-125-gold` — Whip Zoom · Gold
**زوم خاطف · ذهبي**

*accent · any · blur · easing: easeOutExpo · 0.25s*

*Original: M-125*

Variant of M-125: نسخة ذهبية فاخرة

**Spec (EN):** Scale the frame to 150% with about 1.2% motion blur in 0.15s, then settle to 130% and sharp over 0.2s. Pair with a short whoosh.

**Spec (AR):** كبّر الصورة لـ 150% مع ضبابية حركة تقريباً 1.2% خلال 0.15 ثانية، وبعدين تستقر على 130% واضحة خلال 0.2 ثانية. حط معاها صوت ووش قصير.

**When to use:**
- EN: Use when you need a gold version of M-125.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-125.

#### `al-cam-125-boxed` — Whip Zoom · Boxed
**زوم خاطف · صندوق**

*accent · any · blur · easing: easeOutExpo · 0.25s*

*Original: M-125*

Variant of M-125: النص داخل صندوق ملون

**Spec (EN):** Scale the frame to 150% with about 1.2% motion blur in 0.15s, then settle to 130% and sharp over 0.2s. Pair with a short whoosh.

**Spec (AR):** كبّر الصورة لـ 150% مع ضبابية حركة تقريباً 1.2% خلال 0.15 ثانية، وبعدين تستقر على 130% واضحة خلال 0.2 ثانية. حط معاها صوت ووش قصير.

**When to use:**
- EN: Use when you need a boxed version of M-125.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-125.

#### `al-cam-126-fast` — Handheld Drift · Fast
**حركة يد خفيفة · سريع**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-126*

Variant of M-126: أسرع بـ 40%

**Spec (EN):** Overscale to 108% and drift the frame slowly with small offsets (±1.2%) and rotation (±0.5°) on a smooth 4s path.

**Spec (AR):** كبّر لـ 108% وحرّك الصورة ببطء بإزاحات صغيرة (±1.2%) ودوران (±0.5 درجة) على مسار ناعم كل 4 ثواني.

**When to use:**
- EN: Use when you need a fast version of M-126.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-126.

#### `al-cam-126-slow` — Handheld Drift · Slow
**حركة يد خفيفة · بطيء**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-126*

Variant of M-126: أبطأ بـ 60%

**Spec (EN):** Overscale to 108% and drift the frame slowly with small offsets (±1.2%) and rotation (±0.5°) on a smooth 4s path.

**Spec (AR):** كبّر لـ 108% وحرّك الصورة ببطء بإزاحات صغيرة (±1.2%) ودوران (±0.5 درجة) على مسار ناعم كل 4 ثواني.

**When to use:**
- EN: Use when you need a slow version of M-126.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-126.

#### `al-cam-126-gold` — Handheld Drift · Gold
**حركة يد خفيفة · ذهبي**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-126*

Variant of M-126: نسخة ذهبية فاخرة

**Spec (EN):** Overscale to 108% and drift the frame slowly with small offsets (±1.2%) and rotation (±0.5°) on a smooth 4s path.

**Spec (AR):** كبّر لـ 108% وحرّك الصورة ببطء بإزاحات صغيرة (±1.2%) ودوران (±0.5 درجة) على مسار ناعم كل 4 ثواني.

**When to use:**
- EN: Use when you need a gold version of M-126.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-126.

#### `al-cam-126-boxed` — Handheld Drift · Boxed
**حركة يد خفيفة · صندوق**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-126*

Variant of M-126: النص داخل صندوق ملون

**Spec (EN):** Overscale to 108% and drift the frame slowly with small offsets (±1.2%) and rotation (±0.5°) on a smooth 4s path.

**Spec (AR):** كبّر لـ 108% وحرّك الصورة ببطء بإزاحات صغيرة (±1.2%) ودوران (±0.5 درجة) على مسار ناعم كل 4 ثواني.

**When to use:**
- EN: Use when you need a boxed version of M-126.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-126.

#### `al-cam-127-fast` — Dutch Tilt · Fast
**ميلان الكاميرا · سريع**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-127*

Variant of M-127: أسرع بـ 40%

**Spec (EN):** Rotate the frame to -9° while scaling to 120% to hide the corners over 0.5s, hold, then return.

**Spec (AR):** لف الصورة لـ -9 درجات وكبّرها لـ 120% عشان الزوايا ما تبين خلال 0.5 ثانية، ثبّت، وبعدين رجّعها.

**When to use:**
- EN: Use when you need a fast version of M-127.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-127.

#### `al-cam-127-slow` — Dutch Tilt · Slow
**ميلان الكاميرا · بطيء**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-127*

Variant of M-127: أبطأ بـ 60%

**Spec (EN):** Rotate the frame to -9° while scaling to 120% to hide the corners over 0.5s, hold, then return.

**Spec (AR):** لف الصورة لـ -9 درجات وكبّرها لـ 120% عشان الزوايا ما تبين خلال 0.5 ثانية، ثبّت، وبعدين رجّعها.

**When to use:**
- EN: Use when you need a slow version of M-127.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-127.

#### `al-cam-127-gold` — Dutch Tilt · Gold
**ميلان الكاميرا · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-127*

Variant of M-127: نسخة ذهبية فاخرة

**Spec (EN):** Rotate the frame to -9° while scaling to 120% to hide the corners over 0.5s, hold, then return.

**Spec (AR):** لف الصورة لـ -9 درجات وكبّرها لـ 120% عشان الزوايا ما تبين خلال 0.5 ثانية، ثبّت، وبعدين رجّعها.

**When to use:**
- EN: Use when you need a gold version of M-127.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-127.

#### `al-cam-127-boxed` — Dutch Tilt · Boxed
**ميلان الكاميرا · صندوق**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-127*

Variant of M-127: النص داخل صندوق ملون

**Spec (EN):** Rotate the frame to -9° while scaling to 120% to hide the corners over 0.5s, hold, then return.

**Spec (AR):** لف الصورة لـ -9 درجات وكبّرها لـ 120% عشان الزوايا ما تبين خلال 0.5 ثانية، ثبّت، وبعدين رجّعها.

**When to use:**
- EN: Use when you need a boxed version of M-127.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-127.

#### `al-cam-128-fast` — Snap Zoom Out · Fast
**زوم آوت سريع · سريع**

*accent · any · timeline · easing: easeOutExpo · 0.2s*

*Original: M-128*

Variant of M-128: أسرع بـ 40%

**Spec (EN):** Start at 150% on a detail, then snap out to 100% in about 0.2s on a beat or word.

**Spec (AR):** ابدأ على 150% على تفصيلة، وبعدين ابعد فجأة لـ 100% خلال تقريباً 0.2 ثانية على الإيقاع أو الكلمة.

**When to use:**
- EN: Use when you need a fast version of M-128.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-128.

#### `al-cam-128-slow` — Snap Zoom Out · Slow
**زوم آوت سريع · بطيء**

*accent · any · timeline · easing: easeOutExpo · 0.2s*

*Original: M-128*

Variant of M-128: أبطأ بـ 60%

**Spec (EN):** Start at 150% on a detail, then snap out to 100% in about 0.2s on a beat or word.

**Spec (AR):** ابدأ على 150% على تفصيلة، وبعدين ابعد فجأة لـ 100% خلال تقريباً 0.2 ثانية على الإيقاع أو الكلمة.

**When to use:**
- EN: Use when you need a slow version of M-128.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-128.

#### `al-cam-128-gold` — Snap Zoom Out · Gold
**زوم آوت سريع · ذهبي**

*accent · any · timeline · easing: easeOutExpo · 0.2s*

*Original: M-128*

Variant of M-128: نسخة ذهبية فاخرة

**Spec (EN):** Start at 150% on a detail, then snap out to 100% in about 0.2s on a beat or word.

**Spec (AR):** ابدأ على 150% على تفصيلة، وبعدين ابعد فجأة لـ 100% خلال تقريباً 0.2 ثانية على الإيقاع أو الكلمة.

**When to use:**
- EN: Use when you need a gold version of M-128.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-128.

#### `al-cam-128-boxed` — Snap Zoom Out · Boxed
**زوم آوت سريع · صندوق**

*accent · any · timeline · easing: easeOutExpo · 0.2s*

*Original: M-128*

Variant of M-128: النص داخل صندوق ملون

**Spec (EN):** Start at 150% on a detail, then snap out to 100% in about 0.2s on a beat or word.

**Spec (AR):** ابدأ على 150% على تفصيلة، وبعدين ابعد فجأة لـ 100% خلال تقريباً 0.2 ثانية على الإيقاع أو الكلمة.

**When to use:**
- EN: Use when you need a boxed version of M-128.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-128.

#### `al-cam-129-fast` — Crash Zoom · Fast
**زوم صادم · سريع**

*accent · any · timeline · easing: easeOutExpo · 0.2s + 0.3s shake*

*Original: M-129*

Variant of M-129: أسرع بـ 40%

**Spec (EN):** Snap the frame to about 190% centered on the face in 0.15s, add a short horizontal shake (±1.5%), then hold. Pair with a dramatic hit.

**Spec (AR):** كبّر الصورة لـ تقريباً 190% على الوجه خلال 0.15 ثانية، وحط هزة أفقية قصيرة (±1.5%)، وثبّت. حط معاها ضربة صوت درامية.

**When to use:**
- EN: Use when you need a fast version of M-129.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-129.

#### `al-cam-129-slow` — Crash Zoom · Slow
**زوم صادم · بطيء**

*accent · any · timeline · easing: easeOutExpo · 0.2s + 0.3s shake*

*Original: M-129*

Variant of M-129: أبطأ بـ 60%

**Spec (EN):** Snap the frame to about 190% centered on the face in 0.15s, add a short horizontal shake (±1.5%), then hold. Pair with a dramatic hit.

**Spec (AR):** كبّر الصورة لـ تقريباً 190% على الوجه خلال 0.15 ثانية، وحط هزة أفقية قصيرة (±1.5%)، وثبّت. حط معاها ضربة صوت درامية.

**When to use:**
- EN: Use when you need a slow version of M-129.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-129.

#### `al-cam-129-gold` — Crash Zoom · Gold
**زوم صادم · ذهبي**

*accent · any · timeline · easing: easeOutExpo · 0.2s + 0.3s shake*

*Original: M-129*

Variant of M-129: نسخة ذهبية فاخرة

**Spec (EN):** Snap the frame to about 190% centered on the face in 0.15s, add a short horizontal shake (±1.5%), then hold. Pair with a dramatic hit.

**Spec (AR):** كبّر الصورة لـ تقريباً 190% على الوجه خلال 0.15 ثانية، وحط هزة أفقية قصيرة (±1.5%)، وثبّت. حط معاها ضربة صوت درامية.

**When to use:**
- EN: Use when you need a gold version of M-129.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-129.

#### `al-cam-129-boxed` — Crash Zoom · Boxed
**زوم صادم · صندوق**

*accent · any · timeline · easing: easeOutExpo · 0.2s + 0.3s shake*

*Original: M-129*

Variant of M-129: النص داخل صندوق ملون

**Spec (EN):** Snap the frame to about 190% centered on the face in 0.15s, add a short horizontal shake (±1.5%), then hold. Pair with a dramatic hit.

**Spec (AR):** كبّر الصورة لـ تقريباً 190% على الوجه خلال 0.15 ثانية، وحط هزة أفقية قصيرة (±1.5%)، وثبّت. حط معاها ضربة صوت درامية.

**When to use:**
- EN: Use when you need a boxed version of M-129.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-129.

#### `al-cam-130-fast` — Orbit · Fast
**دوران حول الشخص · سريع**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-130*

Variant of M-130: أسرع بـ 40%

**Spec (EN):** Apply a 3D Y-axis rotation of ±14° with perspective and a 112% scale, swinging smoothly every 4s.

**Spec (AR):** طبّق دوران 3D على المحور العمودي ±14 درجة مع عمق وتكبير 112%، يتأرجح بنعومة كل 4 ثواني.

**When to use:**
- EN: Use when you need a fast version of M-130.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-130.

#### `al-cam-130-slow` — Orbit · Slow
**دوران حول الشخص · بطيء**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-130*

Variant of M-130: أبطأ بـ 60%

**Spec (EN):** Apply a 3D Y-axis rotation of ±14° with perspective and a 112% scale, swinging smoothly every 4s.

**Spec (AR):** طبّق دوران 3D على المحور العمودي ±14 درجة مع عمق وتكبير 112%، يتأرجح بنعومة كل 4 ثواني.

**When to use:**
- EN: Use when you need a slow version of M-130.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-130.

#### `al-cam-130-gold` — Orbit · Gold
**دوران حول الشخص · ذهبي**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-130*

Variant of M-130: نسخة ذهبية فاخرة

**Spec (EN):** Apply a 3D Y-axis rotation of ±14° with perspective and a 112% scale, swinging smoothly every 4s.

**Spec (AR):** طبّق دوران 3D على المحور العمودي ±14 درجة مع عمق وتكبير 112%، يتأرجح بنعومة كل 4 ثواني.

**When to use:**
- EN: Use when you need a gold version of M-130.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-130.

#### `al-cam-130-boxed` — Orbit · Boxed
**دوران حول الشخص · صندوق**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-130*

Variant of M-130: النص داخل صندوق ملون

**Spec (EN):** Apply a 3D Y-axis rotation of ±14° with perspective and a 112% scale, swinging smoothly every 4s.

**Spec (AR):** طبّق دوران 3D على المحور العمودي ±14 درجة مع عمق وتكبير 112%، يتأرجح بنعومة كل 4 ثواني.

**When to use:**
- EN: Use when you need a boxed version of M-130.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-130.

#### `al-cam-131-fast` — Double Punch · Fast
**زوم مرتين · سريع**

*accent · any · timeline · easing: cut · 2 cuts*

*Original: M-131*

Variant of M-131: أسرع بـ 40%

**Spec (EN):** Jump to 115% on the first beat and to 132% on the second, with no easing, then cut back to 100%.

**Spec (AR):** نط لـ 115% على أول إيقاع ولـ 132% على الثاني، بدون easing، وبعدين ارجع 100% بقص.

**When to use:**
- EN: Use when you need a fast version of M-131.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-131.

#### `al-cam-131-slow` — Double Punch · Slow
**زوم مرتين · بطيء**

*accent · any · timeline · easing: cut · 2 cuts*

*Original: M-131*

Variant of M-131: أبطأ بـ 60%

**Spec (EN):** Jump to 115% on the first beat and to 132% on the second, with no easing, then cut back to 100%.

**Spec (AR):** نط لـ 115% على أول إيقاع ولـ 132% على الثاني، بدون easing، وبعدين ارجع 100% بقص.

**When to use:**
- EN: Use when you need a slow version of M-131.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-131.

#### `al-cam-131-gold` — Double Punch · Gold
**زوم مرتين · ذهبي**

*accent · any · timeline · easing: cut · 2 cuts*

*Original: M-131*

Variant of M-131: نسخة ذهبية فاخرة

**Spec (EN):** Jump to 115% on the first beat and to 132% on the second, with no easing, then cut back to 100%.

**Spec (AR):** نط لـ 115% على أول إيقاع ولـ 132% على الثاني، بدون easing، وبعدين ارجع 100% بقص.

**When to use:**
- EN: Use when you need a gold version of M-131.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-131.

#### `al-cam-131-boxed` — Double Punch · Boxed
**زوم مرتين · صندوق**

*accent · any · timeline · easing: cut · 2 cuts*

*Original: M-131*

Variant of M-131: النص داخل صندوق ملون

**Spec (EN):** Jump to 115% on the first beat and to 132% on the second, with no easing, then cut back to 100%.

**Spec (AR):** نط لـ 115% على أول إيقاع ولـ 132% على الثاني، بدون easing، وبعدين ارجع 100% بقص.

**When to use:**
- EN: Use when you need a boxed version of M-131.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-131.

#### `al-cam-132-fast` — Split Screen · Fast
**شاشة مقسومة · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.5s in*

*Original: M-132*

Variant of M-132: أسرع بـ 40%

**Spec (EN):** Two clips slide in from the left and right edges into each half of the frame over 0.5s, with a thin gap between them.

**Spec (AR):** مقطعين يدخلون من الحافة اليمين واليسار كل واحد بنص الشاشة خلال 0.5 ثانية، وبينهم فاصل رفيع.

**When to use:**
- EN: Use when you need a fast version of M-132.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-132.

#### `al-cam-132-slow` — Split Screen · Slow
**شاشة مقسومة · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.5s in*

*Original: M-132*

Variant of M-132: أبطأ بـ 60%

**Spec (EN):** Two clips slide in from the left and right edges into each half of the frame over 0.5s, with a thin gap between them.

**Spec (AR):** مقطعين يدخلون من الحافة اليمين واليسار كل واحد بنص الشاشة خلال 0.5 ثانية، وبينهم فاصل رفيع.

**When to use:**
- EN: Use when you need a slow version of M-132.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-132.

#### `al-cam-132-gold` — Split Screen · Gold
**شاشة مقسومة · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.5s in*

*Original: M-132*

Variant of M-132: نسخة ذهبية فاخرة

**Spec (EN):** Two clips slide in from the left and right edges into each half of the frame over 0.5s, with a thin gap between them.

**Spec (AR):** مقطعين يدخلون من الحافة اليمين واليسار كل واحد بنص الشاشة خلال 0.5 ثانية، وبينهم فاصل رفيع.

**When to use:**
- EN: Use when you need a gold version of M-132.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-132.

#### `al-cam-132-boxed` — Split Screen · Boxed
**شاشة مقسومة · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.5s in*

*Original: M-132*

Variant of M-132: النص داخل صندوق ملون

**Spec (EN):** Two clips slide in from the left and right edges into each half of the frame over 0.5s, with a thin gap between them.

**Spec (AR):** مقطعين يدخلون من الحافة اليمين واليسار كل واحد بنص الشاشة خلال 0.5 ثانية، وبينهم فاصل رفيع.

**When to use:**
- EN: Use when you need a boxed version of M-132.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-132.

#### `al-cam-133-fast` — Picture in Picture · Fast
**صورة داخل صورة · سريع**

*accent · any · depth · easing: easeOutBack · 0.4s in*

*Original: M-133*

Variant of M-133: أسرع بـ 40%

**Spec (EN):** A rounded window with a white border and shadow (about 38% of the width) pops into the top corner from scale 0 over 0.4s and plays the second clip.

**Spec (AR):** نافذة بزوايا دائرية بإطار أبيض وظل (تقريباً 38% من العرض) تنط بالزاوية الفوق من حجم 0 خلال 0.4 ثانية، وتعرض المقطع الثاني.

**When to use:**
- EN: Use when you need a fast version of M-133.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-133.

#### `al-cam-133-slow` — Picture in Picture · Slow
**صورة داخل صورة · بطيء**

*accent · any · depth · easing: easeOutBack · 0.4s in*

*Original: M-133*

Variant of M-133: أبطأ بـ 60%

**Spec (EN):** A rounded window with a white border and shadow (about 38% of the width) pops into the top corner from scale 0 over 0.4s and plays the second clip.

**Spec (AR):** نافذة بزوايا دائرية بإطار أبيض وظل (تقريباً 38% من العرض) تنط بالزاوية الفوق من حجم 0 خلال 0.4 ثانية، وتعرض المقطع الثاني.

**When to use:**
- EN: Use when you need a slow version of M-133.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-133.

#### `al-cam-133-gold` — Picture in Picture · Gold
**صورة داخل صورة · ذهبي**

*accent · any · depth · easing: easeOutBack · 0.4s in*

*Original: M-133*

Variant of M-133: نسخة ذهبية فاخرة

**Spec (EN):** A rounded window with a white border and shadow (about 38% of the width) pops into the top corner from scale 0 over 0.4s and plays the second clip.

**Spec (AR):** نافذة بزوايا دائرية بإطار أبيض وظل (تقريباً 38% من العرض) تنط بالزاوية الفوق من حجم 0 خلال 0.4 ثانية، وتعرض المقطع الثاني.

**When to use:**
- EN: Use when you need a gold version of M-133.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-133.

#### `al-cam-133-boxed` — Picture in Picture · Boxed
**صورة داخل صورة · صندوق**

*accent · any · depth · easing: easeOutBack · 0.4s in*

*Original: M-133*

Variant of M-133: النص داخل صندوق ملون

**Spec (EN):** A rounded window with a white border and shadow (about 38% of the width) pops into the top corner from scale 0 over 0.4s and plays the second clip.

**Spec (AR):** نافذة بزوايا دائرية بإطار أبيض وظل (تقريباً 38% من العرض) تنط بالزاوية الفوق من حجم 0 خلال 0.4 ثانية، وتعرض المقطع الثاني.

**When to use:**
- EN: Use when you need a boxed version of M-133.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-133.

#### `al-cam-134-fast` — Mirror Flip · Fast
**قلب الصورة · سريع**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-134*

Variant of M-134: أسرع بـ 40%

**Spec (EN):** Flip the frame horizontally (scaleX from 1 to -1) over 0.5s, hold, then flip back.

**Spec (AR):** اقلب الصورة أفقياً (scaleX من 1 لـ -1) خلال 0.5 ثانية، ثبّت، وبعدين رجّعها.

**When to use:**
- EN: Use when you need a fast version of M-134.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-134.

#### `al-cam-134-slow` — Mirror Flip · Slow
**قلب الصورة · بطيء**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-134*

Variant of M-134: أبطأ بـ 60%

**Spec (EN):** Flip the frame horizontally (scaleX from 1 to -1) over 0.5s, hold, then flip back.

**Spec (AR):** اقلب الصورة أفقياً (scaleX من 1 لـ -1) خلال 0.5 ثانية، ثبّت، وبعدين رجّعها.

**When to use:**
- EN: Use when you need a slow version of M-134.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-134.

#### `al-cam-134-gold` — Mirror Flip · Gold
**قلب الصورة · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-134*

Variant of M-134: نسخة ذهبية فاخرة

**Spec (EN):** Flip the frame horizontally (scaleX from 1 to -1) over 0.5s, hold, then flip back.

**Spec (AR):** اقلب الصورة أفقياً (scaleX من 1 لـ -1) خلال 0.5 ثانية، ثبّت، وبعدين رجّعها.

**When to use:**
- EN: Use when you need a gold version of M-134.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-134.

#### `al-cam-134-boxed` — Mirror Flip · Boxed
**قلب الصورة · صندوق**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-134*

Variant of M-134: النص داخل صندوق ملون

**Spec (EN):** Flip the frame horizontally (scaleX from 1 to -1) over 0.5s, hold, then flip back.

**Spec (AR):** اقلب الصورة أفقياً (scaleX من 1 لـ -1) خلال 0.5 ثانية، ثبّت، وبعدين رجّعها.

**When to use:**
- EN: Use when you need a boxed version of M-134.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-134.

#### `al-cam-135-fast` — Freeze Frame · Fast
**تجميد اللقطة · سريع**

*accent · any · depth · easing: cut · hold 1–2s*

*Original: M-135*

Variant of M-135: أسرع بـ 40%

**Spec (EN):** On the chosen frame, hold the image, desaturate it about 85% with a little more contrast, and pop a small label tag. Resume playback after the hold.

**Spec (AR):** على الفريم المختار، ثبّت الصورة، وخفف ألوانها تقريباً 85% مع تباين أكثر شوي، وطلّع تاق صغير. وكمّل التشغيل بعد التثبيت.

**When to use:**
- EN: Use when you need a fast version of M-135.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-135.

#### `al-cam-135-slow` — Freeze Frame · Slow
**تجميد اللقطة · بطيء**

*accent · any · depth · easing: cut · hold 1–2s*

*Original: M-135*

Variant of M-135: أبطأ بـ 60%

**Spec (EN):** On the chosen frame, hold the image, desaturate it about 85% with a little more contrast, and pop a small label tag. Resume playback after the hold.

**Spec (AR):** على الفريم المختار، ثبّت الصورة، وخفف ألوانها تقريباً 85% مع تباين أكثر شوي، وطلّع تاق صغير. وكمّل التشغيل بعد التثبيت.

**When to use:**
- EN: Use when you need a slow version of M-135.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-135.

#### `al-cam-135-gold` — Freeze Frame · Gold
**تجميد اللقطة · ذهبي**

*accent · any · depth · easing: cut · hold 1–2s*

*Original: M-135*

Variant of M-135: نسخة ذهبية فاخرة

**Spec (EN):** On the chosen frame, hold the image, desaturate it about 85% with a little more contrast, and pop a small label tag. Resume playback after the hold.

**Spec (AR):** على الفريم المختار، ثبّت الصورة، وخفف ألوانها تقريباً 85% مع تباين أكثر شوي، وطلّع تاق صغير. وكمّل التشغيل بعد التثبيت.

**When to use:**
- EN: Use when you need a gold version of M-135.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-135.

#### `al-cam-135-boxed` — Freeze Frame · Boxed
**تجميد اللقطة · صندوق**

*accent · any · depth · easing: cut · hold 1–2s*

*Original: M-135*

Variant of M-135: النص داخل صندوق ملون

**Spec (EN):** On the chosen frame, hold the image, desaturate it about 85% with a little more contrast, and pop a small label tag. Resume playback after the hold.

**Spec (AR):** على الفريم المختار، ثبّت الصورة، وخفف ألوانها تقريباً 85% مع تباين أكثر شوي، وطلّع تاق صغير. وكمّل التشغيل بعد التثبيت.

**When to use:**
- EN: Use when you need a boxed version of M-135.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-135.

#### `al-cam-136-fast` — Slow Motion · Fast
**تبطيء الحركة · سريع**

*accent · any · depth · easing: easeOutCubic · ramp 0.2s*

*Original: M-136*

Variant of M-136: أسرع بـ 40%

**Spec (EN):** Ramp the clip speed from 100% down to about 25% over 0.2s at the key moment (use frame blending or interpolation), hold, then ramp back.

**Spec (AR):** نزّل سرعة المقطع من 100% لـ تقريباً 25% خلال 0.2 ثانية عند اللحظة المهمة (بدمج الفريمات أو توليد فريمات)، ثبّت، وبعدين رجّع السرعة.

**When to use:**
- EN: Use when you need a fast version of M-136.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-136.

#### `al-cam-136-slow` — Slow Motion · Slow
**تبطيء الحركة · بطيء**

*accent · any · depth · easing: easeOutCubic · ramp 0.2s*

*Original: M-136*

Variant of M-136: أبطأ بـ 60%

**Spec (EN):** Ramp the clip speed from 100% down to about 25% over 0.2s at the key moment (use frame blending or interpolation), hold, then ramp back.

**Spec (AR):** نزّل سرعة المقطع من 100% لـ تقريباً 25% خلال 0.2 ثانية عند اللحظة المهمة (بدمج الفريمات أو توليد فريمات)، ثبّت، وبعدين رجّع السرعة.

**When to use:**
- EN: Use when you need a slow version of M-136.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-136.

#### `al-cam-136-gold` — Slow Motion · Gold
**تبطيء الحركة · ذهبي**

*accent · any · depth · easing: easeOutCubic · ramp 0.2s*

*Original: M-136*

Variant of M-136: نسخة ذهبية فاخرة

**Spec (EN):** Ramp the clip speed from 100% down to about 25% over 0.2s at the key moment (use frame blending or interpolation), hold, then ramp back.

**Spec (AR):** نزّل سرعة المقطع من 100% لـ تقريباً 25% خلال 0.2 ثانية عند اللحظة المهمة (بدمج الفريمات أو توليد فريمات)، ثبّت، وبعدين رجّع السرعة.

**When to use:**
- EN: Use when you need a gold version of M-136.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-136.

#### `al-cam-136-boxed` — Slow Motion · Boxed
**تبطيء الحركة · صندوق**

*accent · any · depth · easing: easeOutCubic · ramp 0.2s*

*Original: M-136*

Variant of M-136: النص داخل صندوق ملون

**Spec (EN):** Ramp the clip speed from 100% down to about 25% over 0.2s at the key moment (use frame blending or interpolation), hold, then ramp back.

**Spec (AR):** نزّل سرعة المقطع من 100% لـ تقريباً 25% خلال 0.2 ثانية عند اللحظة المهمة (بدمج الفريمات أو توليد فريمات)، ثبّت، وبعدين رجّع السرعة.

**When to use:**
- EN: Use when you need a boxed version of M-136.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-136.

#### `al-cam-137-fast` — Speed Ramp · Fast
**تسريع وتبطيء · سريع**

*accent · any · timeline · easing: custom curve · 0.8s*

*Original: M-137*

Variant of M-137: أسرع بـ 40%

**Spec (EN):** Combine a slow push (100% to 104%) with a sudden fast push to 130% in about 0.15s, then ease into a slow drift. Time the fast part to the beat.

**Spec (AR):** ادمج زوم بطيء (100% لـ 104%) مع زوم سريع مفاجئ لـ 130% خلال تقريباً 0.15 ثانية، وبعدين حركة بطيئة ناعمة. وخل الجزء السريع على الإيقاع.

**When to use:**
- EN: Use when you need a fast version of M-137.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-137.

#### `al-cam-137-slow` — Speed Ramp · Slow
**تسريع وتبطيء · بطيء**

*accent · any · timeline · easing: custom curve · 0.8s*

*Original: M-137*

Variant of M-137: أبطأ بـ 60%

**Spec (EN):** Combine a slow push (100% to 104%) with a sudden fast push to 130% in about 0.15s, then ease into a slow drift. Time the fast part to the beat.

**Spec (AR):** ادمج زوم بطيء (100% لـ 104%) مع زوم سريع مفاجئ لـ 130% خلال تقريباً 0.15 ثانية، وبعدين حركة بطيئة ناعمة. وخل الجزء السريع على الإيقاع.

**When to use:**
- EN: Use when you need a slow version of M-137.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-137.

#### `al-cam-137-gold` — Speed Ramp · Gold
**تسريع وتبطيء · ذهبي**

*accent · any · timeline · easing: custom curve · 0.8s*

*Original: M-137*

Variant of M-137: نسخة ذهبية فاخرة

**Spec (EN):** Combine a slow push (100% to 104%) with a sudden fast push to 130% in about 0.15s, then ease into a slow drift. Time the fast part to the beat.

**Spec (AR):** ادمج زوم بطيء (100% لـ 104%) مع زوم سريع مفاجئ لـ 130% خلال تقريباً 0.15 ثانية، وبعدين حركة بطيئة ناعمة. وخل الجزء السريع على الإيقاع.

**When to use:**
- EN: Use when you need a gold version of M-137.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-137.

#### `al-cam-137-boxed` — Speed Ramp · Boxed
**تسريع وتبطيء · صندوق**

*accent · any · timeline · easing: custom curve · 0.8s*

*Original: M-137*

Variant of M-137: النص داخل صندوق ملون

**Spec (EN):** Combine a slow push (100% to 104%) with a sudden fast push to 130% in about 0.15s, then ease into a slow drift. Time the fast part to the beat.

**Spec (AR):** ادمج زوم بطيء (100% لـ 104%) مع زوم سريع مفاجئ لـ 130% خلال تقريباً 0.15 ثانية، وبعدين حركة بطيئة ناعمة. وخل الجزء السريع على الإيقاع.

**When to use:**
- EN: Use when you need a boxed version of M-137.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-137.

#### `al-cam-138-fast` — Letterbox Bars · Fast
**أشرطة سينمائية · سريع**

*accent · any · depth · easing: easeInOutCubic · 0.5s in*

*Original: M-138*

Variant of M-138: أسرع بـ 40%

**Spec (EN):** Two black bars slide in from the top and bottom edges over 0.5s, each about 16% of the width tall, and stay during the cinematic part.

**Spec (AR):** شريطين سود يدخلون من الحافة الفوق والتحت خلال 0.5 ثانية، كل واحد ارتفاعه تقريباً 16% من العرض، ويبقون طول الجزء السينمائي.

**When to use:**
- EN: Use when you need a fast version of M-138.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-138.

#### `al-cam-138-slow` — Letterbox Bars · Slow
**أشرطة سينمائية · بطيء**

*accent · any · depth · easing: easeInOutCubic · 0.5s in*

*Original: M-138*

Variant of M-138: أبطأ بـ 60%

**Spec (EN):** Two black bars slide in from the top and bottom edges over 0.5s, each about 16% of the width tall, and stay during the cinematic part.

**Spec (AR):** شريطين سود يدخلون من الحافة الفوق والتحت خلال 0.5 ثانية، كل واحد ارتفاعه تقريباً 16% من العرض، ويبقون طول الجزء السينمائي.

**When to use:**
- EN: Use when you need a slow version of M-138.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-138.

#### `al-cam-138-gold` — Letterbox Bars · Gold
**أشرطة سينمائية · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 0.5s in*

*Original: M-138*

Variant of M-138: نسخة ذهبية فاخرة

**Spec (EN):** Two black bars slide in from the top and bottom edges over 0.5s, each about 16% of the width tall, and stay during the cinematic part.

**Spec (AR):** شريطين سود يدخلون من الحافة الفوق والتحت خلال 0.5 ثانية، كل واحد ارتفاعه تقريباً 16% من العرض، ويبقون طول الجزء السينمائي.

**When to use:**
- EN: Use when you need a gold version of M-138.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-138.

#### `al-cam-138-boxed` — Letterbox Bars · Boxed
**أشرطة سينمائية · صندوق**

*accent · any · depth · easing: easeInOutCubic · 0.5s in*

*Original: M-138*

Variant of M-138: النص داخل صندوق ملون

**Spec (EN):** Two black bars slide in from the top and bottom edges over 0.5s, each about 16% of the width tall, and stay during the cinematic part.

**Spec (AR):** شريطين سود يدخلون من الحافة الفوق والتحت خلال 0.5 ثانية، كل واحد ارتفاعه تقريباً 16% من العرض، ويبقون طول الجزء السينمائي.

**When to use:**
- EN: Use when you need a boxed version of M-138.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-138.

#### `al-cam-139-fast` — Vignette Focus · Fast
**تعتيم الأطراف · سريع**

*accent · calm · timeline · easing: easeInOutSine · 0.6s in*

*Original: M-139*

Variant of M-139: أسرع بـ 40%

**Spec (EN):** Fade in an elliptical dark vignette (transparent center, about 90% black at the edges) over 0.6s around the face.

**Spec (AR):** طبقة تعتيم بيضاوية (النص شفاف والأطراف تقريباً 90% أسود) تظهر خلال 0.6 ثانية حول الوجه.

**When to use:**
- EN: Use when you need a fast version of M-139.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-139.

#### `al-cam-139-slow` — Vignette Focus · Slow
**تعتيم الأطراف · بطيء**

*accent · calm · timeline · easing: easeInOutSine · 0.6s in*

*Original: M-139*

Variant of M-139: أبطأ بـ 60%

**Spec (EN):** Fade in an elliptical dark vignette (transparent center, about 90% black at the edges) over 0.6s around the face.

**Spec (AR):** طبقة تعتيم بيضاوية (النص شفاف والأطراف تقريباً 90% أسود) تظهر خلال 0.6 ثانية حول الوجه.

**When to use:**
- EN: Use when you need a slow version of M-139.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-139.

#### `al-cam-139-gold` — Vignette Focus · Gold
**تعتيم الأطراف · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · 0.6s in*

*Original: M-139*

Variant of M-139: نسخة ذهبية فاخرة

**Spec (EN):** Fade in an elliptical dark vignette (transparent center, about 90% black at the edges) over 0.6s around the face.

**Spec (AR):** طبقة تعتيم بيضاوية (النص شفاف والأطراف تقريباً 90% أسود) تظهر خلال 0.6 ثانية حول الوجه.

**When to use:**
- EN: Use when you need a gold version of M-139.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-139.

#### `al-cam-139-boxed` — Vignette Focus · Boxed
**تعتيم الأطراف · صندوق**

*accent · calm · timeline · easing: easeInOutSine · 0.6s in*

*Original: M-139*

Variant of M-139: النص داخل صندوق ملون

**Spec (EN):** Fade in an elliptical dark vignette (transparent center, about 90% black at the edges) over 0.6s around the face.

**Spec (AR):** طبقة تعتيم بيضاوية (النص شفاف والأطراف تقريباً 90% أسود) تظهر خلال 0.6 ثانية حول الوجه.

**When to use:**
- EN: Use when you need a boxed version of M-139.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-139.

#### `al-cam-140-fast` — Bounce Zoom · Fast
**زوم بارتداد · سريع**

*accent · any · timeline · easing: spring · 0.5s*

*Original: M-140*

Variant of M-140: أسرع بـ 40%

**Spec (EN):** Zoom to 132%, bounce back to 116%, then 124%, and settle at 122% over about 0.5s.

**Spec (AR):** زوم لـ 132%، يرتد لـ 116%، وبعدين 124%، ويستقر على 122% خلال تقريباً 0.5 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-140.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-140.

#### `al-cam-140-slow` — Bounce Zoom · Slow
**زوم بارتداد · بطيء**

*accent · any · timeline · easing: spring · 0.5s*

*Original: M-140*

Variant of M-140: أبطأ بـ 60%

**Spec (EN):** Zoom to 132%, bounce back to 116%, then 124%, and settle at 122% over about 0.5s.

**Spec (AR):** زوم لـ 132%، يرتد لـ 116%، وبعدين 124%، ويستقر على 122% خلال تقريباً 0.5 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-140.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-140.

#### `al-cam-140-gold` — Bounce Zoom · Gold
**زوم بارتداد · ذهبي**

*accent · any · timeline · easing: spring · 0.5s*

*Original: M-140*

Variant of M-140: نسخة ذهبية فاخرة

**Spec (EN):** Zoom to 132%, bounce back to 116%, then 124%, and settle at 122% over about 0.5s.

**Spec (AR):** زوم لـ 132%، يرتد لـ 116%، وبعدين 124%، ويستقر على 122% خلال تقريباً 0.5 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-140.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-140.

#### `al-cam-140-boxed` — Bounce Zoom · Boxed
**زوم بارتداد · صندوق**

*accent · any · timeline · easing: spring · 0.5s*

*Original: M-140*

Variant of M-140: النص داخل صندوق ملون

**Spec (EN):** Zoom to 132%, bounce back to 116%, then 124%, and settle at 122% over about 0.5s.

**Spec (AR):** زوم لـ 132%، يرتد لـ 116%، وبعدين 124%، ويستقر على 122% خلال تقريباً 0.5 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-140.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-140.

### Effects (المؤثرات) — 125 motions

#### `al-fx-026` — Particle Dissolve
**تناثر وتلاشي**

*workhorse · any · depth · easing: easeOutQuad · 1.2s*

*Original: M-026*

A logo or object breaks apart and vanishes, like a finger snap.

**Spec (EN):** The object breaks into 150–400 small particles sampled from its own pixels. Each particle flies outward on a random vector (60–250px) with slight upward drift, shrinks and fades out over 1.2s. The original disappears in the first 0.1s.

**Spec (AR):** العنصر يتفتت لـ 150 إلى 400 جزيء صغير مأخوذة من ألوانه نفسها. كل جزيء يطير لبرا باتجاه عشوائي (60 إلى 250px) مع ميل خفيف لفوق، ويصغر ويختفي خلال 1.2 ثانية. العنصر الأصلي يختفي أول 0.1 ثانية.

**When to use:**
- EN: A logo or object breaks apart and vanishes, like a finger snap.
- AR: شعار أو عنصر يتفتت ويختفي، مثل طقة إصبع.

#### `al-fx-027` — Shockwave
**موجة صدمة**

*workhorse · any · depth · easing: easeOutCubic · 0.8s*

*Original: M-027*

With a finger snap or a tap.

**Spec (EN):** From the tap point, a white flash dot pops in and out (0.25s), then two accent rings expand from 0 to about 3.5x and fade, 0.12s apart. Optionally add a slight refraction on the video under the rings.

**Spec (AR):** من نقطة الضغطة تطلع ومضة بيضا وتختفي (0.25 ثانية)، وبعدها حلقتين بلون الهوية تكبر من 0 لـ تقريباً 3.5 مرات وتختفي، وبينهم 0.12 ثانية. وتقدر تضيف انكسار خفيف للفيديو تحت الحلقات.

**When to use:**
- EN: With a finger snap or a tap.
- AR: مع طقة إصبع أو ضغطة.

#### `al-fx-028` — Pulse Rings
**حلقات نابضة**

*workhorse · calm · depth · easing: linear · loop · 1s per ring*

*Original: M-028*

Behind your head when you talk about something important.

**Spec (EN):** Concentric accent rings spawn behind the person (on the background layer, masked by the person matte) every 1/3 of the loop, expanding from 50% to 300% and fading to 0.

**Spec (AR):** حلقات بلون الهوية تطلع ورا الشخص (على طبقة الخلفية تحت قناع الشخص) كل ثلث دورة، تكبر من 50% لـ 300% وتختفي.

**When to use:**
- EN: Behind your head when you talk about something important.
- AR: خلف الراس لما تتكلم عن شي مهم.

#### `al-fx-029` — Light Rays
**أشعة ورا الراس**

*workhorse · calm · timeline · easing: linear · loop · 8s per turn*

*Original: M-029*

A "wow" moment or a new announcement.

**Spec (EN):** Soft accent-colored rays (conic gradient, 6° rays every 22°) rotate slowly behind the person. A radial mask fades them out at about 45% radius. Place them on the layer behind the person matte.

**Spec (AR):** أشعة ناعمة بلون الهوية (conic gradient، شعاع 6 درجات كل 22 درجة) تدور ببطء ورا الشخص، وقناع دائري يخفيها تدريجياً عند تقريباً 45% من نصف القطر. حطها على الطبقة اللي ورا قناع الشخص.

**When to use:**
- EN: A "wow" moment or a new announcement.
- AR: لحظة "واو" أو إعلان عن شي جديد.

#### `al-fx-030` — Confetti Burst
**انفجار قصاصات**

*workhorse · any · depth · easing: easeOut then gravity · 1.5s*

*Original: M-030*

A celebration, an achievement or a big number.

**Spec (EN):** 40–80 small rectangles in 4 brand colors burst from a point with random velocity (mostly upward, ±60°), spin randomly, then fall with gravity and fade out over 1.5s.

**Spec (AR):** 40 إلى 80 قصاصة مستطيلة صغيرة بـ 4 ألوان من الهوية تنفجر من نقطة بسرعات عشوائية (أغلبها لفوق، ±60 درجة)، تدور عشوائياً، وبعدين تطيح بالجاذبية وتختفي خلال 1.5 ثانية.

**When to use:**
- EN: A celebration, an achievement or a big number.
- AR: احتفال أو إنجاز أو رقم كبير.

#### `al-fx-141` — Sparkle Trail
**أثر لمعة**

*workhorse · calm · timeline · easing: easeInOutSine · 1s*

*Original: M-141*

A glowing point travels and leaves a trail.

**Spec (EN):** A bright warm point moves along a curved path; 10–20 copies follow it with 0.05s delays, each shrinking and fading, forming a sparkle trail.

**Spec (AR):** نقطة لامعة دافية تمشي على مسار منحني، ووراها 10 إلى 20 نسخة متأخرة كل وحدة 0.05 ثانية، وكل وحدة تصغر وتختفي، فيطلع أثر لمعة.

**When to use:**
- EN: A glowing point travels and leaves a trail.
- AR: نقطة لامعة تمشي وتخلي وراها أثر.

#### `al-fx-142` — Dust Burst
**غبار يتطاير**

*workhorse · any · depth · easing: easeOutCubic · 1s*

*Original: M-142*

Dust puffs out when something lands.

**Spec (EN):** From the impact point, 15–30 soft blurred puffs in sand tones spread out and slightly up, growing to 160% and fading over 1s.

**Spec (AR):** من نقطة الاصطدام، 15 إلى 30 نفخة غبار ناعمة ومضببة بلون رملي تنتشر لبرا ولفوق شوي، تكبر لـ 160% وتختفي خلال ثانية.

**When to use:**
- EN: Dust puffs out when something lands.
- AR: غبار يطلع من تحت لمن شي ينزل أو يطيح.

#### `al-fx-143` — Lens Flare
**وهج العدسة**

*workhorse · calm · timeline · easing: linear · 1.5s*

*Original: M-143*

A sun flare drifts across the frame for warmth.

**Spec (EN):** A bright warm core with a soft halo and 3 small colored ghost circles moves diagonally across the frame (screen blend) over about 1.5s.

**Spec (AR):** قلب دافي لامع مع هالة ناعمة و3 دواير ملونة صغيرة يمشون قطرياً على الشاشة (دمج screen) خلال تقريباً 1.5 ثانية.

**When to use:**
- EN: A sun flare drifts across the frame for warmth.
- AR: وهج شمس يمر على الشاشة، يعطي دفا.

#### `al-fx-144` — Scan Line
**خط مسح**

*workhorse · calm · timeline · easing: linear · 1.2s*

*Original: M-144*

A light line scans the frame like a scanner, techy.

**Spec (EN):** A bright mint horizontal line with a wide glow travels from the top to the bottom of the frame over 1.2s.

**Spec (AR):** خط أفقي نعناعي لامع مع توهج عريض يمشي من فوق الشاشة لتحت خلال 1.2 ثانية.

**When to use:**
- EN: A light line scans the frame like a scanner, techy.
- AR: خط ضوء يمسح الشاشة مثل جهاز سكان، يناسب التقنية.

#### `al-fx-145` — Code Rain
**مطر كود**

*workhorse · calm · depth · easing: linear · loop*

*Original: M-145*

Falling code characters, perfect for cyber topics.

**Spec (EN):** Columns of mint monospace characters fall at different speeds behind the person (background layer), each column fading at its tail.

**Spec (AR):** أعمدة من حروف mono نعناعية تنزل بسرعات مختلفة ورا الشخص (طبقة الخلفية)، وكل عمود يختفي من آخره.

**When to use:**
- EN: Falling code characters, perfect for cyber topics.
- AR: حروف كود تنزل مثل الماتريكس، للأمن السيبراني.

#### `al-fx-146` — Hologram
**هولوغرام**

*workhorse · calm · timeline · easing: linear · loop*

*Original: M-146*

The person looks like a futuristic hologram.

**Spec (EN):** Tint the person cyan, add moving horizontal scanlines over them (screen blend) and a subtle opacity flicker every couple of seconds.

**Spec (AR):** لوّن الشخص بسماوي، وحط فوقه خطوط أفقية تتحرك (دمج screen)، ورمشة شفافية خفيفة كل كم ثانية.

**When to use:**
- EN: The person looks like a futuristic hologram.
- AR: الشخص يبين كأنه هولوغرام مستقبلي.

#### `al-fx-147` — Electric Arc
**شرارة كهربا**

*workhorse · any · timeline · easing: steps · 0.6s*

*Original: M-147*

A flickering electric arc for energy moments.

**Spec (EN):** A jagged light-blue zigzag line with a glow flickers on and off 2–3 times between two points; redraw the zigzag randomly each flicker.

**Spec (AR):** خط متعرج أزرق فاتح مع توهج يرمش ويطفي 2 إلى 3 مرات بين نقطتين، وارسم التعرج بشكل عشوائي كل رمشة.

**When to use:**
- EN: A flickering electric arc for energy moments.
- AR: خط كهربا يرمش، يناسب الطاقة أو "شحن".

#### `al-fx-148` — Heat Glow
**توهج دافي**

*workhorse · calm · depth · easing: easeInOutSine · loop · 2s*

*Original: M-148*

A warm pulsing aura behind the person.

**Spec (EN):** A large orange radial glow sits behind the person (background layer) and pulses between 90% and 108% scale every 2s.

**Spec (AR):** توهج دائري برتقالي كبير ورا الشخص (طبقة الخلفية)، ينبض بين 90% و108% كل ثانيتين.

**When to use:**
- EN: A warm pulsing aura behind the person.
- AR: هالة دافية ورا الشخص تنبض، تعطي طاقة.

#### `al-fx-149` — Floating Particles
**جزيئات طافية**

*workhorse · calm · depth · easing: linear · loop*

*Original: M-149*

Small light specks float upward for a calm mood.

**Spec (EN):** Spawn 12–25 small warm glowing dots at random x positions near the bottom; each drifts upward with slight sideways drift over 3–5s and fades.

**Spec (AR):** طلّع من 12 إلى 25 نقطة ضوء دافية صغيرة بأماكن أفقية عشوائية قرب تحت، وكل وحدة تطفو لفوق مع ميل خفيف على الجنب خلال 3 إلى 5 ثواني وتختفي.

**When to use:**
- EN: Small light specks float upward for a calm mood.
- AR: نقاط ضوء صغيرة تطفو لفوق، أجواء هادية.

#### `al-fx-150` — Radial Ripple
**تموج دائري**

*workhorse · any · timeline · easing: easeOutCubic · loop · 1.5s*

*Original: M-150*

Rings spread from a point like touching water.

**Spec (EN):** Thin mint rings spawn at a point every 0.5s, expanding from 30% to 450% and fading out.

**Spec (AR):** دواير نعناعية رفيعة تطلع من نقطة كل 0.5 ثانية، تكبر من 30% لـ 450% وتختفي.

**When to use:**
- EN: Rings spread from a point like touching water.
- AR: دواير تتوسع من نقطة، مثل لمس الماي.

#### `al-fx-151` — Grid Floor
**أرضية شبكة**

*workhorse · calm · timeline · easing: linear · loop · 1s*

*Original: M-151*

A moving 3D grid floor, retro-tech style.

**Spec (EN):** Draw a mint line grid on a plane tilted 60° in perspective at the bottom of the frame, scrolling toward the viewer one cell per second.

**Spec (AR):** ارسم شبكة خطوط نعناعية على مستوى مايل 60 درجة بعمق تحت الشاشة، وتتحرك ناحية المشاهد خانة كل ثانية.

**When to use:**
- EN: A moving 3D grid floor, retro-tech style.
- AR: شبكة ثلاثية الأبعاد تتحرك تحت، ستايل الريترو والتقنية.

#### `al-fx-152` — Spark Burst
**انفجار شرار**

*workhorse · any · timeline · easing: easeOutExpo · 0.5s*

*Original: M-152*

Spark streaks shoot out from a point on a hit or idea.

**Spec (EN):** Twelve thin warm streaks shoot radially outward from a point, stretching as they go and fading over 0.5s.

**Spec (AR):** 12 خط شرار دافي رفيع تنطلق من نقطة بكل الاتجاهات، تتمدد وهي تطلع وتختفي خلال 0.5 ثانية.

**When to use:**
- EN: Spark streaks shoot out from a point on a hit or idea.
- AR: خطوط شرار تنطلق من نقطة، مع ضربة أو فكرة.

#### `al-fx-153` — Orbit Dots
**نقاط تدور**

*workhorse · calm · depth · easing: linear · loop · 3s*

*Original: M-153*

Dots orbit around a logo or word.

**Spec (EN):** Three accent dots travel around a dashed circle centered on the subject, evenly spaced, one full turn every 3s.

**Spec (AR):** ثلاث نقاط بلون الهوية تدور على دائرة متقطعة حول الهدف، المسافة بينهم متساوية، لفة كاملة كل 3 ثواني.

**When to use:**
- EN: Dots orbit around a logo or word.
- AR: نقاط تدور حول شعار أو كلمة.

#### `al-fx-154` — Glow Outline
**توهج حول الشخص**

*workhorse · calm · blur · easing: easeInOutSine · loop · 2s*

*Original: M-154*

A glowing edge around the person makes them pop.

**Spec (EN):** Using the person matte, add an accent outer glow (drop shadow on the matte edge) that pulses from 0 to about 2.5% blur every 2s.

**Spec (AR):** باستخدام قناع الشخص، حط توهج خارجي بلون الهوية (ظل على حافة القناع) ينبض من 0 لـ تقريباً 2.5% ضبابية كل ثانيتين.

**When to use:**
- EN: A glowing edge around the person makes them pop.
- AR: حدود مضيئة حول الشخص تخليه يبرز.

#### `al-fx-155` — VHS Glitch
**تشويش شريط فيديو**

*workhorse · any · depth · easing: steps · loop*

*Original: M-155*

Old videotape look for nostalgia.

**Spec (EN):** Add short horizontal frame jumps (±3%), brief color shifts, and a soft bright noise band that rolls up the frame every couple of seconds.

**Spec (AR):** حط نطات أفقية قصيرة للصورة (±3%)، وتغيّر ألوان لحظي، وشريط تشويش فاتح ناعم يطلع على الشاشة من تحت لفوق كل كم ثانية.

**When to use:**
- EN: Old videotape look for nostalgia.
- AR: ستايل شريط الفيديو القديم، نوستالجيا.

#### `al-fx-156` — Film Grain
**حبيبات فيلم**

*workhorse · any · timeline · easing: steps · loop*

*Original: M-156*

Grain and light flicker for a film feel.

**Spec (EN):** Overlay fine moving noise at about 35% opacity, jumping position every frame, plus a tiny brightness flicker (±10%).

**Spec (AR):** حط طبقة حبيبات ناعمة تتحرك بشفافية تقريباً 35%، تنط مكانها كل فريم، مع رمشة إضاءة خفيفة جداً (±10%).

**When to use:**
- EN: Grain and light flicker for a film feel.
- AR: حبيبات وفليكر خفيف يعطي إحساس الفيلم.

#### `al-fx-157` — Shine Sweep
**لمعة على النص**

*workhorse · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-157*

A shine passes over a word or logo like metal.

**Spec (EN):** A narrow bright diagonal band clipped to the text or logo sweeps across it from one side to the other over 0.8s.

**Spec (AR):** شريط لامع مايل ورفيع داخل حدود النص أو الشعار يمر عليه من جهة للثانية خلال 0.8 ثانية.

**When to use:**
- EN: A shine passes over a word or logo like metal.
- AR: لمعة تمر على كلمة أو شعار كأنه معدن.

#### `al-fx-158` — Bokeh Lights
**أضواء بوكيه**

*workhorse · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-158*

Soft out-of-focus light circles behind the person.

**Spec (EN):** Place 6–10 blurred warm circles of different sizes on the background layer; each drifts a little and gently grows and fades on a 4s loop.

**Spec (AR):** حط من 6 إلى 10 دواير ضوء مضببة دافية بأحجام مختلفة على طبقة الخلفية، وكل وحدة تتحرك شوي وتكبر وتخف بنعومة كل 4 ثواني.

**When to use:**
- EN: Soft out-of-focus light circles behind the person.
- AR: دواير ضوء ناعمة ورا الشخص، أجواء دافية.

#### `al-fx-159` — Speed Lines
**خطوط سرعة**

*workhorse · any · timeline · easing: steps · loop · 0.4s*

*Original: M-159*

Manga speed lines around the face for shock or hype.

**Spec (EN):** Draw thin white radial lines around the subject with a clear center, jittering in angle and scale every few frames.

**Spec (AR):** ارسم خطوط بيضا رفيعة شعاعية حول الهدف والنص فاضي، ترجف بالزاوية والحجم كل كم فريم.

**When to use:**
- EN: Manga speed lines around the face for shock or hype.
- AR: خطوط مانغا حول الوجه للصدمة أو الحماس.

#### `al-fx-160` — Face Tracking Box
**مربع تتبع الوجه**

*workhorse · calm · camera · easing: easeInOutSine · loop*

*Original: M-160*

A box that tracks the face with a score, AI style.

**Spec (EN):** Detect the face and draw four mint corner brackets around it that follow it smoothly, with a small mono label above like "FACE 98%".

**Spec (AR):** اكتشف الوجه وارسم أربع زوايا نعناعية حوله تتبعه بنعومة، وفوقها تاق mono صغير مثل "FACE 98%".

**When to use:**
- EN: A box that tracks the face with a score, AI style.
- AR: مربع يتبع الوجه مع نسبة، ستايل الذكاء الاصطناعي.

#### `al-fx-026-fast` — Particle Dissolve · Fast
**تناثر وتلاشي · سريع**

*accent · calm · depth · easing: easeOutQuad · 1.2s*

*Original: M-026*

Variant of M-026: أسرع بـ 40%

**Spec (EN):** The object breaks into 150–400 small particles sampled from its own pixels. Each particle flies outward on a random vector (60–250px) with slight upward drift, shrinks and fades out over 1.2s. The original disappears in the first 0.1s.

**Spec (AR):** العنصر يتفتت لـ 150 إلى 400 جزيء صغير مأخوذة من ألوانه نفسها. كل جزيء يطير لبرا باتجاه عشوائي (60 إلى 250px) مع ميل خفيف لفوق، ويصغر ويختفي خلال 1.2 ثانية. العنصر الأصلي يختفي أول 0.1 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-026.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-026.

#### `al-fx-026-slow` — Particle Dissolve · Slow
**تناثر وتلاشي · بطيء**

*accent · calm · depth · easing: easeOutQuad · 1.2s*

*Original: M-026*

Variant of M-026: أبطأ بـ 60%

**Spec (EN):** The object breaks into 150–400 small particles sampled from its own pixels. Each particle flies outward on a random vector (60–250px) with slight upward drift, shrinks and fades out over 1.2s. The original disappears in the first 0.1s.

**Spec (AR):** العنصر يتفتت لـ 150 إلى 400 جزيء صغير مأخوذة من ألوانه نفسها. كل جزيء يطير لبرا باتجاه عشوائي (60 إلى 250px) مع ميل خفيف لفوق، ويصغر ويختفي خلال 1.2 ثانية. العنصر الأصلي يختفي أول 0.1 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-026.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-026.

#### `al-fx-026-gold` — Particle Dissolve · Gold
**تناثر وتلاشي · ذهبي**

*accent · calm · depth · easing: easeOutQuad · 1.2s*

*Original: M-026*

Variant of M-026: نسخة ذهبية فاخرة

**Spec (EN):** The object breaks into 150–400 small particles sampled from its own pixels. Each particle flies outward on a random vector (60–250px) with slight upward drift, shrinks and fades out over 1.2s. The original disappears in the first 0.1s.

**Spec (AR):** العنصر يتفتت لـ 150 إلى 400 جزيء صغير مأخوذة من ألوانه نفسها. كل جزيء يطير لبرا باتجاه عشوائي (60 إلى 250px) مع ميل خفيف لفوق، ويصغر ويختفي خلال 1.2 ثانية. العنصر الأصلي يختفي أول 0.1 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-026.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-026.

#### `al-fx-026-boxed` — Particle Dissolve · Boxed
**تناثر وتلاشي · صندوق**

*accent · calm · depth · easing: easeOutQuad · 1.2s*

*Original: M-026*

Variant of M-026: النص داخل صندوق ملون

**Spec (EN):** The object breaks into 150–400 small particles sampled from its own pixels. Each particle flies outward on a random vector (60–250px) with slight upward drift, shrinks and fades out over 1.2s. The original disappears in the first 0.1s.

**Spec (AR):** العنصر يتفتت لـ 150 إلى 400 جزيء صغير مأخوذة من ألوانه نفسها. كل جزيء يطير لبرا باتجاه عشوائي (60 إلى 250px) مع ميل خفيف لفوق، ويصغر ويختفي خلال 1.2 ثانية. العنصر الأصلي يختفي أول 0.1 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-026.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-026.

#### `al-fx-027-fast` — Shockwave · Fast
**موجة صدمة · سريع**

*accent · any · depth · easing: easeOutCubic · 0.8s*

*Original: M-027*

Variant of M-027: أسرع بـ 40%

**Spec (EN):** From the tap point, a white flash dot pops in and out (0.25s), then two accent rings expand from 0 to about 3.5x and fade, 0.12s apart. Optionally add a slight refraction on the video under the rings.

**Spec (AR):** من نقطة الضغطة تطلع ومضة بيضا وتختفي (0.25 ثانية)، وبعدها حلقتين بلون الهوية تكبر من 0 لـ تقريباً 3.5 مرات وتختفي، وبينهم 0.12 ثانية. وتقدر تضيف انكسار خفيف للفيديو تحت الحلقات.

**When to use:**
- EN: Use when you need a fast version of M-027.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-027.

#### `al-fx-027-slow` — Shockwave · Slow
**موجة صدمة · بطيء**

*accent · any · depth · easing: easeOutCubic · 0.8s*

*Original: M-027*

Variant of M-027: أبطأ بـ 60%

**Spec (EN):** From the tap point, a white flash dot pops in and out (0.25s), then two accent rings expand from 0 to about 3.5x and fade, 0.12s apart. Optionally add a slight refraction on the video under the rings.

**Spec (AR):** من نقطة الضغطة تطلع ومضة بيضا وتختفي (0.25 ثانية)، وبعدها حلقتين بلون الهوية تكبر من 0 لـ تقريباً 3.5 مرات وتختفي، وبينهم 0.12 ثانية. وتقدر تضيف انكسار خفيف للفيديو تحت الحلقات.

**When to use:**
- EN: Use when you need a slow version of M-027.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-027.

#### `al-fx-027-gold` — Shockwave · Gold
**موجة صدمة · ذهبي**

*accent · any · depth · easing: easeOutCubic · 0.8s*

*Original: M-027*

Variant of M-027: نسخة ذهبية فاخرة

**Spec (EN):** From the tap point, a white flash dot pops in and out (0.25s), then two accent rings expand from 0 to about 3.5x and fade, 0.12s apart. Optionally add a slight refraction on the video under the rings.

**Spec (AR):** من نقطة الضغطة تطلع ومضة بيضا وتختفي (0.25 ثانية)، وبعدها حلقتين بلون الهوية تكبر من 0 لـ تقريباً 3.5 مرات وتختفي، وبينهم 0.12 ثانية. وتقدر تضيف انكسار خفيف للفيديو تحت الحلقات.

**When to use:**
- EN: Use when you need a gold version of M-027.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-027.

#### `al-fx-027-boxed` — Shockwave · Boxed
**موجة صدمة · صندوق**

*accent · any · depth · easing: easeOutCubic · 0.8s*

*Original: M-027*

Variant of M-027: النص داخل صندوق ملون

**Spec (EN):** From the tap point, a white flash dot pops in and out (0.25s), then two accent rings expand from 0 to about 3.5x and fade, 0.12s apart. Optionally add a slight refraction on the video under the rings.

**Spec (AR):** من نقطة الضغطة تطلع ومضة بيضا وتختفي (0.25 ثانية)، وبعدها حلقتين بلون الهوية تكبر من 0 لـ تقريباً 3.5 مرات وتختفي، وبينهم 0.12 ثانية. وتقدر تضيف انكسار خفيف للفيديو تحت الحلقات.

**When to use:**
- EN: Use when you need a boxed version of M-027.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-027.

#### `al-fx-028-fast` — Pulse Rings · Fast
**حلقات نابضة · سريع**

*accent · calm · depth · easing: linear · loop · 1s per ring*

*Original: M-028*

Variant of M-028: أسرع بـ 40%

**Spec (EN):** Concentric accent rings spawn behind the person (on the background layer, masked by the person matte) every 1/3 of the loop, expanding from 50% to 300% and fading to 0.

**Spec (AR):** حلقات بلون الهوية تطلع ورا الشخص (على طبقة الخلفية تحت قناع الشخص) كل ثلث دورة، تكبر من 50% لـ 300% وتختفي.

**When to use:**
- EN: Use when you need a fast version of M-028.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-028.

#### `al-fx-028-slow` — Pulse Rings · Slow
**حلقات نابضة · بطيء**

*accent · calm · depth · easing: linear · loop · 1s per ring*

*Original: M-028*

Variant of M-028: أبطأ بـ 60%

**Spec (EN):** Concentric accent rings spawn behind the person (on the background layer, masked by the person matte) every 1/3 of the loop, expanding from 50% to 300% and fading to 0.

**Spec (AR):** حلقات بلون الهوية تطلع ورا الشخص (على طبقة الخلفية تحت قناع الشخص) كل ثلث دورة، تكبر من 50% لـ 300% وتختفي.

**When to use:**
- EN: Use when you need a slow version of M-028.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-028.

#### `al-fx-028-gold` — Pulse Rings · Gold
**حلقات نابضة · ذهبي**

*accent · calm · depth · easing: linear · loop · 1s per ring*

*Original: M-028*

Variant of M-028: نسخة ذهبية فاخرة

**Spec (EN):** Concentric accent rings spawn behind the person (on the background layer, masked by the person matte) every 1/3 of the loop, expanding from 50% to 300% and fading to 0.

**Spec (AR):** حلقات بلون الهوية تطلع ورا الشخص (على طبقة الخلفية تحت قناع الشخص) كل ثلث دورة، تكبر من 50% لـ 300% وتختفي.

**When to use:**
- EN: Use when you need a gold version of M-028.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-028.

#### `al-fx-028-boxed` — Pulse Rings · Boxed
**حلقات نابضة · صندوق**

*accent · calm · depth · easing: linear · loop · 1s per ring*

*Original: M-028*

Variant of M-028: النص داخل صندوق ملون

**Spec (EN):** Concentric accent rings spawn behind the person (on the background layer, masked by the person matte) every 1/3 of the loop, expanding from 50% to 300% and fading to 0.

**Spec (AR):** حلقات بلون الهوية تطلع ورا الشخص (على طبقة الخلفية تحت قناع الشخص) كل ثلث دورة، تكبر من 50% لـ 300% وتختفي.

**When to use:**
- EN: Use when you need a boxed version of M-028.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-028.

#### `al-fx-029-fast` — Light Rays · Fast
**أشعة ورا الراس · سريع**

*accent · calm · timeline · easing: linear · loop · 8s per turn*

*Original: M-029*

Variant of M-029: أسرع بـ 40%

**Spec (EN):** Soft accent-colored rays (conic gradient, 6° rays every 22°) rotate slowly behind the person. A radial mask fades them out at about 45% radius. Place them on the layer behind the person matte.

**Spec (AR):** أشعة ناعمة بلون الهوية (conic gradient، شعاع 6 درجات كل 22 درجة) تدور ببطء ورا الشخص، وقناع دائري يخفيها تدريجياً عند تقريباً 45% من نصف القطر. حطها على الطبقة اللي ورا قناع الشخص.

**When to use:**
- EN: Use when you need a fast version of M-029.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-029.

#### `al-fx-029-slow` — Light Rays · Slow
**أشعة ورا الراس · بطيء**

*accent · calm · timeline · easing: linear · loop · 8s per turn*

*Original: M-029*

Variant of M-029: أبطأ بـ 60%

**Spec (EN):** Soft accent-colored rays (conic gradient, 6° rays every 22°) rotate slowly behind the person. A radial mask fades them out at about 45% radius. Place them on the layer behind the person matte.

**Spec (AR):** أشعة ناعمة بلون الهوية (conic gradient، شعاع 6 درجات كل 22 درجة) تدور ببطء ورا الشخص، وقناع دائري يخفيها تدريجياً عند تقريباً 45% من نصف القطر. حطها على الطبقة اللي ورا قناع الشخص.

**When to use:**
- EN: Use when you need a slow version of M-029.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-029.

#### `al-fx-029-gold` — Light Rays · Gold
**أشعة ورا الراس · ذهبي**

*accent · calm · timeline · easing: linear · loop · 8s per turn*

*Original: M-029*

Variant of M-029: نسخة ذهبية فاخرة

**Spec (EN):** Soft accent-colored rays (conic gradient, 6° rays every 22°) rotate slowly behind the person. A radial mask fades them out at about 45% radius. Place them on the layer behind the person matte.

**Spec (AR):** أشعة ناعمة بلون الهوية (conic gradient، شعاع 6 درجات كل 22 درجة) تدور ببطء ورا الشخص، وقناع دائري يخفيها تدريجياً عند تقريباً 45% من نصف القطر. حطها على الطبقة اللي ورا قناع الشخص.

**When to use:**
- EN: Use when you need a gold version of M-029.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-029.

#### `al-fx-029-boxed` — Light Rays · Boxed
**أشعة ورا الراس · صندوق**

*accent · calm · timeline · easing: linear · loop · 8s per turn*

*Original: M-029*

Variant of M-029: النص داخل صندوق ملون

**Spec (EN):** Soft accent-colored rays (conic gradient, 6° rays every 22°) rotate slowly behind the person. A radial mask fades them out at about 45% radius. Place them on the layer behind the person matte.

**Spec (AR):** أشعة ناعمة بلون الهوية (conic gradient، شعاع 6 درجات كل 22 درجة) تدور ببطء ورا الشخص، وقناع دائري يخفيها تدريجياً عند تقريباً 45% من نصف القطر. حطها على الطبقة اللي ورا قناع الشخص.

**When to use:**
- EN: Use when you need a boxed version of M-029.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-029.

#### `al-fx-030-fast` — Confetti Burst · Fast
**انفجار قصاصات · سريع**

*accent · any · depth · easing: easeOut then gravity · 1.5s*

*Original: M-030*

Variant of M-030: أسرع بـ 40%

**Spec (EN):** 40–80 small rectangles in 4 brand colors burst from a point with random velocity (mostly upward, ±60°), spin randomly, then fall with gravity and fade out over 1.5s.

**Spec (AR):** 40 إلى 80 قصاصة مستطيلة صغيرة بـ 4 ألوان من الهوية تنفجر من نقطة بسرعات عشوائية (أغلبها لفوق، ±60 درجة)، تدور عشوائياً، وبعدين تطيح بالجاذبية وتختفي خلال 1.5 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-030.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-030.

#### `al-fx-030-slow` — Confetti Burst · Slow
**انفجار قصاصات · بطيء**

*accent · any · depth · easing: easeOut then gravity · 1.5s*

*Original: M-030*

Variant of M-030: أبطأ بـ 60%

**Spec (EN):** 40–80 small rectangles in 4 brand colors burst from a point with random velocity (mostly upward, ±60°), spin randomly, then fall with gravity and fade out over 1.5s.

**Spec (AR):** 40 إلى 80 قصاصة مستطيلة صغيرة بـ 4 ألوان من الهوية تنفجر من نقطة بسرعات عشوائية (أغلبها لفوق، ±60 درجة)، تدور عشوائياً، وبعدين تطيح بالجاذبية وتختفي خلال 1.5 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-030.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-030.

#### `al-fx-030-gold` — Confetti Burst · Gold
**انفجار قصاصات · ذهبي**

*accent · any · depth · easing: easeOut then gravity · 1.5s*

*Original: M-030*

Variant of M-030: نسخة ذهبية فاخرة

**Spec (EN):** 40–80 small rectangles in 4 brand colors burst from a point with random velocity (mostly upward, ±60°), spin randomly, then fall with gravity and fade out over 1.5s.

**Spec (AR):** 40 إلى 80 قصاصة مستطيلة صغيرة بـ 4 ألوان من الهوية تنفجر من نقطة بسرعات عشوائية (أغلبها لفوق، ±60 درجة)، تدور عشوائياً، وبعدين تطيح بالجاذبية وتختفي خلال 1.5 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-030.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-030.

#### `al-fx-030-boxed` — Confetti Burst · Boxed
**انفجار قصاصات · صندوق**

*accent · any · depth · easing: easeOut then gravity · 1.5s*

*Original: M-030*

Variant of M-030: النص داخل صندوق ملون

**Spec (EN):** 40–80 small rectangles in 4 brand colors burst from a point with random velocity (mostly upward, ±60°), spin randomly, then fall with gravity and fade out over 1.5s.

**Spec (AR):** 40 إلى 80 قصاصة مستطيلة صغيرة بـ 4 ألوان من الهوية تنفجر من نقطة بسرعات عشوائية (أغلبها لفوق، ±60 درجة)، تدور عشوائياً، وبعدين تطيح بالجاذبية وتختفي خلال 1.5 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-030.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-030.

#### `al-fx-141-fast` — Sparkle Trail · Fast
**أثر لمعة · سريع**

*accent · calm · timeline · easing: easeInOutSine · 1s*

*Original: M-141*

Variant of M-141: أسرع بـ 40%

**Spec (EN):** A bright warm point moves along a curved path; 10–20 copies follow it with 0.05s delays, each shrinking and fading, forming a sparkle trail.

**Spec (AR):** نقطة لامعة دافية تمشي على مسار منحني، ووراها 10 إلى 20 نسخة متأخرة كل وحدة 0.05 ثانية، وكل وحدة تصغر وتختفي، فيطلع أثر لمعة.

**When to use:**
- EN: Use when you need a fast version of M-141.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-141.

#### `al-fx-141-slow` — Sparkle Trail · Slow
**أثر لمعة · بطيء**

*accent · calm · timeline · easing: easeInOutSine · 1s*

*Original: M-141*

Variant of M-141: أبطأ بـ 60%

**Spec (EN):** A bright warm point moves along a curved path; 10–20 copies follow it with 0.05s delays, each shrinking and fading, forming a sparkle trail.

**Spec (AR):** نقطة لامعة دافية تمشي على مسار منحني، ووراها 10 إلى 20 نسخة متأخرة كل وحدة 0.05 ثانية، وكل وحدة تصغر وتختفي، فيطلع أثر لمعة.

**When to use:**
- EN: Use when you need a slow version of M-141.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-141.

#### `al-fx-141-gold` — Sparkle Trail · Gold
**أثر لمعة · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · 1s*

*Original: M-141*

Variant of M-141: نسخة ذهبية فاخرة

**Spec (EN):** A bright warm point moves along a curved path; 10–20 copies follow it with 0.05s delays, each shrinking and fading, forming a sparkle trail.

**Spec (AR):** نقطة لامعة دافية تمشي على مسار منحني، ووراها 10 إلى 20 نسخة متأخرة كل وحدة 0.05 ثانية، وكل وحدة تصغر وتختفي، فيطلع أثر لمعة.

**When to use:**
- EN: Use when you need a gold version of M-141.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-141.

#### `al-fx-141-boxed` — Sparkle Trail · Boxed
**أثر لمعة · صندوق**

*accent · calm · timeline · easing: easeInOutSine · 1s*

*Original: M-141*

Variant of M-141: النص داخل صندوق ملون

**Spec (EN):** A bright warm point moves along a curved path; 10–20 copies follow it with 0.05s delays, each shrinking and fading, forming a sparkle trail.

**Spec (AR):** نقطة لامعة دافية تمشي على مسار منحني، ووراها 10 إلى 20 نسخة متأخرة كل وحدة 0.05 ثانية، وكل وحدة تصغر وتختفي، فيطلع أثر لمعة.

**When to use:**
- EN: Use when you need a boxed version of M-141.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-141.

#### `al-fx-142-fast` — Dust Burst · Fast
**غبار يتطاير · سريع**

*accent · any · depth · easing: easeOutCubic · 1s*

*Original: M-142*

Variant of M-142: أسرع بـ 40%

**Spec (EN):** From the impact point, 15–30 soft blurred puffs in sand tones spread out and slightly up, growing to 160% and fading over 1s.

**Spec (AR):** من نقطة الاصطدام، 15 إلى 30 نفخة غبار ناعمة ومضببة بلون رملي تنتشر لبرا ولفوق شوي، تكبر لـ 160% وتختفي خلال ثانية.

**When to use:**
- EN: Use when you need a fast version of M-142.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-142.

#### `al-fx-142-slow` — Dust Burst · Slow
**غبار يتطاير · بطيء**

*accent · any · depth · easing: easeOutCubic · 1s*

*Original: M-142*

Variant of M-142: أبطأ بـ 60%

**Spec (EN):** From the impact point, 15–30 soft blurred puffs in sand tones spread out and slightly up, growing to 160% and fading over 1s.

**Spec (AR):** من نقطة الاصطدام، 15 إلى 30 نفخة غبار ناعمة ومضببة بلون رملي تنتشر لبرا ولفوق شوي، تكبر لـ 160% وتختفي خلال ثانية.

**When to use:**
- EN: Use when you need a slow version of M-142.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-142.

#### `al-fx-142-gold` — Dust Burst · Gold
**غبار يتطاير · ذهبي**

*accent · any · depth · easing: easeOutCubic · 1s*

*Original: M-142*

Variant of M-142: نسخة ذهبية فاخرة

**Spec (EN):** From the impact point, 15–30 soft blurred puffs in sand tones spread out and slightly up, growing to 160% and fading over 1s.

**Spec (AR):** من نقطة الاصطدام، 15 إلى 30 نفخة غبار ناعمة ومضببة بلون رملي تنتشر لبرا ولفوق شوي، تكبر لـ 160% وتختفي خلال ثانية.

**When to use:**
- EN: Use when you need a gold version of M-142.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-142.

#### `al-fx-142-boxed` — Dust Burst · Boxed
**غبار يتطاير · صندوق**

*accent · any · depth · easing: easeOutCubic · 1s*

*Original: M-142*

Variant of M-142: النص داخل صندوق ملون

**Spec (EN):** From the impact point, 15–30 soft blurred puffs in sand tones spread out and slightly up, growing to 160% and fading over 1s.

**Spec (AR):** من نقطة الاصطدام، 15 إلى 30 نفخة غبار ناعمة ومضببة بلون رملي تنتشر لبرا ولفوق شوي، تكبر لـ 160% وتختفي خلال ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-142.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-142.

#### `al-fx-143-fast` — Lens Flare · Fast
**وهج العدسة · سريع**

*accent · calm · timeline · easing: linear · 1.5s*

*Original: M-143*

Variant of M-143: أسرع بـ 40%

**Spec (EN):** A bright warm core with a soft halo and 3 small colored ghost circles moves diagonally across the frame (screen blend) over about 1.5s.

**Spec (AR):** قلب دافي لامع مع هالة ناعمة و3 دواير ملونة صغيرة يمشون قطرياً على الشاشة (دمج screen) خلال تقريباً 1.5 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-143.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-143.

#### `al-fx-143-slow` — Lens Flare · Slow
**وهج العدسة · بطيء**

*accent · calm · timeline · easing: linear · 1.5s*

*Original: M-143*

Variant of M-143: أبطأ بـ 60%

**Spec (EN):** A bright warm core with a soft halo and 3 small colored ghost circles moves diagonally across the frame (screen blend) over about 1.5s.

**Spec (AR):** قلب دافي لامع مع هالة ناعمة و3 دواير ملونة صغيرة يمشون قطرياً على الشاشة (دمج screen) خلال تقريباً 1.5 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-143.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-143.

#### `al-fx-143-gold` — Lens Flare · Gold
**وهج العدسة · ذهبي**

*accent · calm · timeline · easing: linear · 1.5s*

*Original: M-143*

Variant of M-143: نسخة ذهبية فاخرة

**Spec (EN):** A bright warm core with a soft halo and 3 small colored ghost circles moves diagonally across the frame (screen blend) over about 1.5s.

**Spec (AR):** قلب دافي لامع مع هالة ناعمة و3 دواير ملونة صغيرة يمشون قطرياً على الشاشة (دمج screen) خلال تقريباً 1.5 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-143.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-143.

#### `al-fx-143-boxed` — Lens Flare · Boxed
**وهج العدسة · صندوق**

*accent · calm · timeline · easing: linear · 1.5s*

*Original: M-143*

Variant of M-143: النص داخل صندوق ملون

**Spec (EN):** A bright warm core with a soft halo and 3 small colored ghost circles moves diagonally across the frame (screen blend) over about 1.5s.

**Spec (AR):** قلب دافي لامع مع هالة ناعمة و3 دواير ملونة صغيرة يمشون قطرياً على الشاشة (دمج screen) خلال تقريباً 1.5 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-143.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-143.

#### `al-fx-144-fast` — Scan Line · Fast
**خط مسح · سريع**

*accent · calm · timeline · easing: linear · 1.2s*

*Original: M-144*

Variant of M-144: أسرع بـ 40%

**Spec (EN):** A bright mint horizontal line with a wide glow travels from the top to the bottom of the frame over 1.2s.

**Spec (AR):** خط أفقي نعناعي لامع مع توهج عريض يمشي من فوق الشاشة لتحت خلال 1.2 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-144.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-144.

#### `al-fx-144-slow` — Scan Line · Slow
**خط مسح · بطيء**

*accent · calm · timeline · easing: linear · 1.2s*

*Original: M-144*

Variant of M-144: أبطأ بـ 60%

**Spec (EN):** A bright mint horizontal line with a wide glow travels from the top to the bottom of the frame over 1.2s.

**Spec (AR):** خط أفقي نعناعي لامع مع توهج عريض يمشي من فوق الشاشة لتحت خلال 1.2 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-144.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-144.

#### `al-fx-144-gold` — Scan Line · Gold
**خط مسح · ذهبي**

*accent · calm · timeline · easing: linear · 1.2s*

*Original: M-144*

Variant of M-144: نسخة ذهبية فاخرة

**Spec (EN):** A bright mint horizontal line with a wide glow travels from the top to the bottom of the frame over 1.2s.

**Spec (AR):** خط أفقي نعناعي لامع مع توهج عريض يمشي من فوق الشاشة لتحت خلال 1.2 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-144.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-144.

#### `al-fx-144-boxed` — Scan Line · Boxed
**خط مسح · صندوق**

*accent · calm · timeline · easing: linear · 1.2s*

*Original: M-144*

Variant of M-144: النص داخل صندوق ملون

**Spec (EN):** A bright mint horizontal line with a wide glow travels from the top to the bottom of the frame over 1.2s.

**Spec (AR):** خط أفقي نعناعي لامع مع توهج عريض يمشي من فوق الشاشة لتحت خلال 1.2 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-144.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-144.

#### `al-fx-145-fast` — Code Rain · Fast
**مطر كود · سريع**

*accent · calm · depth · easing: linear · loop*

*Original: M-145*

Variant of M-145: أسرع بـ 40%

**Spec (EN):** Columns of mint monospace characters fall at different speeds behind the person (background layer), each column fading at its tail.

**Spec (AR):** أعمدة من حروف mono نعناعية تنزل بسرعات مختلفة ورا الشخص (طبقة الخلفية)، وكل عمود يختفي من آخره.

**When to use:**
- EN: Use when you need a fast version of M-145.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-145.

#### `al-fx-145-slow` — Code Rain · Slow
**مطر كود · بطيء**

*accent · calm · depth · easing: linear · loop*

*Original: M-145*

Variant of M-145: أبطأ بـ 60%

**Spec (EN):** Columns of mint monospace characters fall at different speeds behind the person (background layer), each column fading at its tail.

**Spec (AR):** أعمدة من حروف mono نعناعية تنزل بسرعات مختلفة ورا الشخص (طبقة الخلفية)، وكل عمود يختفي من آخره.

**When to use:**
- EN: Use when you need a slow version of M-145.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-145.

#### `al-fx-145-gold` — Code Rain · Gold
**مطر كود · ذهبي**

*accent · calm · depth · easing: linear · loop*

*Original: M-145*

Variant of M-145: نسخة ذهبية فاخرة

**Spec (EN):** Columns of mint monospace characters fall at different speeds behind the person (background layer), each column fading at its tail.

**Spec (AR):** أعمدة من حروف mono نعناعية تنزل بسرعات مختلفة ورا الشخص (طبقة الخلفية)، وكل عمود يختفي من آخره.

**When to use:**
- EN: Use when you need a gold version of M-145.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-145.

#### `al-fx-145-boxed` — Code Rain · Boxed
**مطر كود · صندوق**

*accent · calm · depth · easing: linear · loop*

*Original: M-145*

Variant of M-145: النص داخل صندوق ملون

**Spec (EN):** Columns of mint monospace characters fall at different speeds behind the person (background layer), each column fading at its tail.

**Spec (AR):** أعمدة من حروف mono نعناعية تنزل بسرعات مختلفة ورا الشخص (طبقة الخلفية)، وكل عمود يختفي من آخره.

**When to use:**
- EN: Use when you need a boxed version of M-145.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-145.

#### `al-fx-146-fast` — Hologram · Fast
**هولوغرام · سريع**

*accent · calm · timeline · easing: linear · loop*

*Original: M-146*

Variant of M-146: أسرع بـ 40%

**Spec (EN):** Tint the person cyan, add moving horizontal scanlines over them (screen blend) and a subtle opacity flicker every couple of seconds.

**Spec (AR):** لوّن الشخص بسماوي، وحط فوقه خطوط أفقية تتحرك (دمج screen)، ورمشة شفافية خفيفة كل كم ثانية.

**When to use:**
- EN: Use when you need a fast version of M-146.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-146.

#### `al-fx-146-slow` — Hologram · Slow
**هولوغرام · بطيء**

*accent · calm · timeline · easing: linear · loop*

*Original: M-146*

Variant of M-146: أبطأ بـ 60%

**Spec (EN):** Tint the person cyan, add moving horizontal scanlines over them (screen blend) and a subtle opacity flicker every couple of seconds.

**Spec (AR):** لوّن الشخص بسماوي، وحط فوقه خطوط أفقية تتحرك (دمج screen)، ورمشة شفافية خفيفة كل كم ثانية.

**When to use:**
- EN: Use when you need a slow version of M-146.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-146.

#### `al-fx-146-gold` — Hologram · Gold
**هولوغرام · ذهبي**

*accent · calm · timeline · easing: linear · loop*

*Original: M-146*

Variant of M-146: نسخة ذهبية فاخرة

**Spec (EN):** Tint the person cyan, add moving horizontal scanlines over them (screen blend) and a subtle opacity flicker every couple of seconds.

**Spec (AR):** لوّن الشخص بسماوي، وحط فوقه خطوط أفقية تتحرك (دمج screen)، ورمشة شفافية خفيفة كل كم ثانية.

**When to use:**
- EN: Use when you need a gold version of M-146.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-146.

#### `al-fx-146-boxed` — Hologram · Boxed
**هولوغرام · صندوق**

*accent · calm · timeline · easing: linear · loop*

*Original: M-146*

Variant of M-146: النص داخل صندوق ملون

**Spec (EN):** Tint the person cyan, add moving horizontal scanlines over them (screen blend) and a subtle opacity flicker every couple of seconds.

**Spec (AR):** لوّن الشخص بسماوي، وحط فوقه خطوط أفقية تتحرك (دمج screen)، ورمشة شفافية خفيفة كل كم ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-146.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-146.

#### `al-fx-147-fast` — Electric Arc · Fast
**شرارة كهربا · سريع**

*accent · any · timeline · easing: steps · 0.6s*

*Original: M-147*

Variant of M-147: أسرع بـ 40%

**Spec (EN):** A jagged light-blue zigzag line with a glow flickers on and off 2–3 times between two points; redraw the zigzag randomly each flicker.

**Spec (AR):** خط متعرج أزرق فاتح مع توهج يرمش ويطفي 2 إلى 3 مرات بين نقطتين، وارسم التعرج بشكل عشوائي كل رمشة.

**When to use:**
- EN: Use when you need a fast version of M-147.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-147.

#### `al-fx-147-slow` — Electric Arc · Slow
**شرارة كهربا · بطيء**

*accent · any · timeline · easing: steps · 0.6s*

*Original: M-147*

Variant of M-147: أبطأ بـ 60%

**Spec (EN):** A jagged light-blue zigzag line with a glow flickers on and off 2–3 times between two points; redraw the zigzag randomly each flicker.

**Spec (AR):** خط متعرج أزرق فاتح مع توهج يرمش ويطفي 2 إلى 3 مرات بين نقطتين، وارسم التعرج بشكل عشوائي كل رمشة.

**When to use:**
- EN: Use when you need a slow version of M-147.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-147.

#### `al-fx-147-gold` — Electric Arc · Gold
**شرارة كهربا · ذهبي**

*accent · any · timeline · easing: steps · 0.6s*

*Original: M-147*

Variant of M-147: نسخة ذهبية فاخرة

**Spec (EN):** A jagged light-blue zigzag line with a glow flickers on and off 2–3 times between two points; redraw the zigzag randomly each flicker.

**Spec (AR):** خط متعرج أزرق فاتح مع توهج يرمش ويطفي 2 إلى 3 مرات بين نقطتين، وارسم التعرج بشكل عشوائي كل رمشة.

**When to use:**
- EN: Use when you need a gold version of M-147.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-147.

#### `al-fx-147-boxed` — Electric Arc · Boxed
**شرارة كهربا · صندوق**

*accent · any · timeline · easing: steps · 0.6s*

*Original: M-147*

Variant of M-147: النص داخل صندوق ملون

**Spec (EN):** A jagged light-blue zigzag line with a glow flickers on and off 2–3 times between two points; redraw the zigzag randomly each flicker.

**Spec (AR):** خط متعرج أزرق فاتح مع توهج يرمش ويطفي 2 إلى 3 مرات بين نقطتين، وارسم التعرج بشكل عشوائي كل رمشة.

**When to use:**
- EN: Use when you need a boxed version of M-147.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-147.

#### `al-fx-148-fast` — Heat Glow · Fast
**توهج دافي · سريع**

*accent · calm · depth · easing: easeInOutSine · loop · 2s*

*Original: M-148*

Variant of M-148: أسرع بـ 40%

**Spec (EN):** A large orange radial glow sits behind the person (background layer) and pulses between 90% and 108% scale every 2s.

**Spec (AR):** توهج دائري برتقالي كبير ورا الشخص (طبقة الخلفية)، ينبض بين 90% و108% كل ثانيتين.

**When to use:**
- EN: Use when you need a fast version of M-148.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-148.

#### `al-fx-148-slow` — Heat Glow · Slow
**توهج دافي · بطيء**

*accent · calm · depth · easing: easeInOutSine · loop · 2s*

*Original: M-148*

Variant of M-148: أبطأ بـ 60%

**Spec (EN):** A large orange radial glow sits behind the person (background layer) and pulses between 90% and 108% scale every 2s.

**Spec (AR):** توهج دائري برتقالي كبير ورا الشخص (طبقة الخلفية)، ينبض بين 90% و108% كل ثانيتين.

**When to use:**
- EN: Use when you need a slow version of M-148.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-148.

#### `al-fx-148-gold` — Heat Glow · Gold
**توهج دافي · ذهبي**

*accent · calm · depth · easing: easeInOutSine · loop · 2s*

*Original: M-148*

Variant of M-148: نسخة ذهبية فاخرة

**Spec (EN):** A large orange radial glow sits behind the person (background layer) and pulses between 90% and 108% scale every 2s.

**Spec (AR):** توهج دائري برتقالي كبير ورا الشخص (طبقة الخلفية)، ينبض بين 90% و108% كل ثانيتين.

**When to use:**
- EN: Use when you need a gold version of M-148.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-148.

#### `al-fx-148-boxed` — Heat Glow · Boxed
**توهج دافي · صندوق**

*accent · calm · depth · easing: easeInOutSine · loop · 2s*

*Original: M-148*

Variant of M-148: النص داخل صندوق ملون

**Spec (EN):** A large orange radial glow sits behind the person (background layer) and pulses between 90% and 108% scale every 2s.

**Spec (AR):** توهج دائري برتقالي كبير ورا الشخص (طبقة الخلفية)، ينبض بين 90% و108% كل ثانيتين.

**When to use:**
- EN: Use when you need a boxed version of M-148.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-148.

#### `al-fx-149-fast` — Floating Particles · Fast
**جزيئات طافية · سريع**

*accent · calm · depth · easing: linear · loop*

*Original: M-149*

Variant of M-149: أسرع بـ 40%

**Spec (EN):** Spawn 12–25 small warm glowing dots at random x positions near the bottom; each drifts upward with slight sideways drift over 3–5s and fades.

**Spec (AR):** طلّع من 12 إلى 25 نقطة ضوء دافية صغيرة بأماكن أفقية عشوائية قرب تحت، وكل وحدة تطفو لفوق مع ميل خفيف على الجنب خلال 3 إلى 5 ثواني وتختفي.

**When to use:**
- EN: Use when you need a fast version of M-149.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-149.

#### `al-fx-149-slow` — Floating Particles · Slow
**جزيئات طافية · بطيء**

*accent · calm · depth · easing: linear · loop*

*Original: M-149*

Variant of M-149: أبطأ بـ 60%

**Spec (EN):** Spawn 12–25 small warm glowing dots at random x positions near the bottom; each drifts upward with slight sideways drift over 3–5s and fades.

**Spec (AR):** طلّع من 12 إلى 25 نقطة ضوء دافية صغيرة بأماكن أفقية عشوائية قرب تحت، وكل وحدة تطفو لفوق مع ميل خفيف على الجنب خلال 3 إلى 5 ثواني وتختفي.

**When to use:**
- EN: Use when you need a slow version of M-149.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-149.

#### `al-fx-149-gold` — Floating Particles · Gold
**جزيئات طافية · ذهبي**

*accent · calm · depth · easing: linear · loop*

*Original: M-149*

Variant of M-149: نسخة ذهبية فاخرة

**Spec (EN):** Spawn 12–25 small warm glowing dots at random x positions near the bottom; each drifts upward with slight sideways drift over 3–5s and fades.

**Spec (AR):** طلّع من 12 إلى 25 نقطة ضوء دافية صغيرة بأماكن أفقية عشوائية قرب تحت، وكل وحدة تطفو لفوق مع ميل خفيف على الجنب خلال 3 إلى 5 ثواني وتختفي.

**When to use:**
- EN: Use when you need a gold version of M-149.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-149.

#### `al-fx-149-boxed` — Floating Particles · Boxed
**جزيئات طافية · صندوق**

*accent · calm · depth · easing: linear · loop*

*Original: M-149*

Variant of M-149: النص داخل صندوق ملون

**Spec (EN):** Spawn 12–25 small warm glowing dots at random x positions near the bottom; each drifts upward with slight sideways drift over 3–5s and fades.

**Spec (AR):** طلّع من 12 إلى 25 نقطة ضوء دافية صغيرة بأماكن أفقية عشوائية قرب تحت، وكل وحدة تطفو لفوق مع ميل خفيف على الجنب خلال 3 إلى 5 ثواني وتختفي.

**When to use:**
- EN: Use when you need a boxed version of M-149.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-149.

#### `al-fx-150-fast` — Radial Ripple · Fast
**تموج دائري · سريع**

*accent · any · timeline · easing: easeOutCubic · loop · 1.5s*

*Original: M-150*

Variant of M-150: أسرع بـ 40%

**Spec (EN):** Thin mint rings spawn at a point every 0.5s, expanding from 30% to 450% and fading out.

**Spec (AR):** دواير نعناعية رفيعة تطلع من نقطة كل 0.5 ثانية، تكبر من 30% لـ 450% وتختفي.

**When to use:**
- EN: Use when you need a fast version of M-150.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-150.

#### `al-fx-150-slow` — Radial Ripple · Slow
**تموج دائري · بطيء**

*accent · any · timeline · easing: easeOutCubic · loop · 1.5s*

*Original: M-150*

Variant of M-150: أبطأ بـ 60%

**Spec (EN):** Thin mint rings spawn at a point every 0.5s, expanding from 30% to 450% and fading out.

**Spec (AR):** دواير نعناعية رفيعة تطلع من نقطة كل 0.5 ثانية، تكبر من 30% لـ 450% وتختفي.

**When to use:**
- EN: Use when you need a slow version of M-150.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-150.

#### `al-fx-150-gold` — Radial Ripple · Gold
**تموج دائري · ذهبي**

*accent · any · timeline · easing: easeOutCubic · loop · 1.5s*

*Original: M-150*

Variant of M-150: نسخة ذهبية فاخرة

**Spec (EN):** Thin mint rings spawn at a point every 0.5s, expanding from 30% to 450% and fading out.

**Spec (AR):** دواير نعناعية رفيعة تطلع من نقطة كل 0.5 ثانية، تكبر من 30% لـ 450% وتختفي.

**When to use:**
- EN: Use when you need a gold version of M-150.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-150.

#### `al-fx-150-boxed` — Radial Ripple · Boxed
**تموج دائري · صندوق**

*accent · any · timeline · easing: easeOutCubic · loop · 1.5s*

*Original: M-150*

Variant of M-150: النص داخل صندوق ملون

**Spec (EN):** Thin mint rings spawn at a point every 0.5s, expanding from 30% to 450% and fading out.

**Spec (AR):** دواير نعناعية رفيعة تطلع من نقطة كل 0.5 ثانية، تكبر من 30% لـ 450% وتختفي.

**When to use:**
- EN: Use when you need a boxed version of M-150.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-150.

#### `al-fx-151-fast` — Grid Floor · Fast
**أرضية شبكة · سريع**

*accent · calm · timeline · easing: linear · loop · 1s*

*Original: M-151*

Variant of M-151: أسرع بـ 40%

**Spec (EN):** Draw a mint line grid on a plane tilted 60° in perspective at the bottom of the frame, scrolling toward the viewer one cell per second.

**Spec (AR):** ارسم شبكة خطوط نعناعية على مستوى مايل 60 درجة بعمق تحت الشاشة، وتتحرك ناحية المشاهد خانة كل ثانية.

**When to use:**
- EN: Use when you need a fast version of M-151.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-151.

#### `al-fx-151-slow` — Grid Floor · Slow
**أرضية شبكة · بطيء**

*accent · calm · timeline · easing: linear · loop · 1s*

*Original: M-151*

Variant of M-151: أبطأ بـ 60%

**Spec (EN):** Draw a mint line grid on a plane tilted 60° in perspective at the bottom of the frame, scrolling toward the viewer one cell per second.

**Spec (AR):** ارسم شبكة خطوط نعناعية على مستوى مايل 60 درجة بعمق تحت الشاشة، وتتحرك ناحية المشاهد خانة كل ثانية.

**When to use:**
- EN: Use when you need a slow version of M-151.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-151.

#### `al-fx-151-gold` — Grid Floor · Gold
**أرضية شبكة · ذهبي**

*accent · calm · timeline · easing: linear · loop · 1s*

*Original: M-151*

Variant of M-151: نسخة ذهبية فاخرة

**Spec (EN):** Draw a mint line grid on a plane tilted 60° in perspective at the bottom of the frame, scrolling toward the viewer one cell per second.

**Spec (AR):** ارسم شبكة خطوط نعناعية على مستوى مايل 60 درجة بعمق تحت الشاشة، وتتحرك ناحية المشاهد خانة كل ثانية.

**When to use:**
- EN: Use when you need a gold version of M-151.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-151.

#### `al-fx-151-boxed` — Grid Floor · Boxed
**أرضية شبكة · صندوق**

*accent · calm · timeline · easing: linear · loop · 1s*

*Original: M-151*

Variant of M-151: النص داخل صندوق ملون

**Spec (EN):** Draw a mint line grid on a plane tilted 60° in perspective at the bottom of the frame, scrolling toward the viewer one cell per second.

**Spec (AR):** ارسم شبكة خطوط نعناعية على مستوى مايل 60 درجة بعمق تحت الشاشة، وتتحرك ناحية المشاهد خانة كل ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-151.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-151.

#### `al-fx-152-fast` — Spark Burst · Fast
**انفجار شرار · سريع**

*accent · any · timeline · easing: easeOutExpo · 0.5s*

*Original: M-152*

Variant of M-152: أسرع بـ 40%

**Spec (EN):** Twelve thin warm streaks shoot radially outward from a point, stretching as they go and fading over 0.5s.

**Spec (AR):** 12 خط شرار دافي رفيع تنطلق من نقطة بكل الاتجاهات، تتمدد وهي تطلع وتختفي خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-152.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-152.

#### `al-fx-152-slow` — Spark Burst · Slow
**انفجار شرار · بطيء**

*accent · any · timeline · easing: easeOutExpo · 0.5s*

*Original: M-152*

Variant of M-152: أبطأ بـ 60%

**Spec (EN):** Twelve thin warm streaks shoot radially outward from a point, stretching as they go and fading over 0.5s.

**Spec (AR):** 12 خط شرار دافي رفيع تنطلق من نقطة بكل الاتجاهات، تتمدد وهي تطلع وتختفي خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-152.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-152.

#### `al-fx-152-gold` — Spark Burst · Gold
**انفجار شرار · ذهبي**

*accent · any · timeline · easing: easeOutExpo · 0.5s*

*Original: M-152*

Variant of M-152: نسخة ذهبية فاخرة

**Spec (EN):** Twelve thin warm streaks shoot radially outward from a point, stretching as they go and fading over 0.5s.

**Spec (AR):** 12 خط شرار دافي رفيع تنطلق من نقطة بكل الاتجاهات، تتمدد وهي تطلع وتختفي خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-152.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-152.

#### `al-fx-152-boxed` — Spark Burst · Boxed
**انفجار شرار · صندوق**

*accent · any · timeline · easing: easeOutExpo · 0.5s*

*Original: M-152*

Variant of M-152: النص داخل صندوق ملون

**Spec (EN):** Twelve thin warm streaks shoot radially outward from a point, stretching as they go and fading over 0.5s.

**Spec (AR):** 12 خط شرار دافي رفيع تنطلق من نقطة بكل الاتجاهات، تتمدد وهي تطلع وتختفي خلال 0.5 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-152.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-152.

#### `al-fx-153-fast` — Orbit Dots · Fast
**نقاط تدور · سريع**

*accent · calm · depth · easing: linear · loop · 3s*

*Original: M-153*

Variant of M-153: أسرع بـ 40%

**Spec (EN):** Three accent dots travel around a dashed circle centered on the subject, evenly spaced, one full turn every 3s.

**Spec (AR):** ثلاث نقاط بلون الهوية تدور على دائرة متقطعة حول الهدف، المسافة بينهم متساوية، لفة كاملة كل 3 ثواني.

**When to use:**
- EN: Use when you need a fast version of M-153.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-153.

#### `al-fx-153-slow` — Orbit Dots · Slow
**نقاط تدور · بطيء**

*accent · calm · depth · easing: linear · loop · 3s*

*Original: M-153*

Variant of M-153: أبطأ بـ 60%

**Spec (EN):** Three accent dots travel around a dashed circle centered on the subject, evenly spaced, one full turn every 3s.

**Spec (AR):** ثلاث نقاط بلون الهوية تدور على دائرة متقطعة حول الهدف، المسافة بينهم متساوية، لفة كاملة كل 3 ثواني.

**When to use:**
- EN: Use when you need a slow version of M-153.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-153.

#### `al-fx-153-gold` — Orbit Dots · Gold
**نقاط تدور · ذهبي**

*accent · calm · depth · easing: linear · loop · 3s*

*Original: M-153*

Variant of M-153: نسخة ذهبية فاخرة

**Spec (EN):** Three accent dots travel around a dashed circle centered on the subject, evenly spaced, one full turn every 3s.

**Spec (AR):** ثلاث نقاط بلون الهوية تدور على دائرة متقطعة حول الهدف، المسافة بينهم متساوية، لفة كاملة كل 3 ثواني.

**When to use:**
- EN: Use when you need a gold version of M-153.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-153.

#### `al-fx-153-boxed` — Orbit Dots · Boxed
**نقاط تدور · صندوق**

*accent · calm · depth · easing: linear · loop · 3s*

*Original: M-153*

Variant of M-153: النص داخل صندوق ملون

**Spec (EN):** Three accent dots travel around a dashed circle centered on the subject, evenly spaced, one full turn every 3s.

**Spec (AR):** ثلاث نقاط بلون الهوية تدور على دائرة متقطعة حول الهدف، المسافة بينهم متساوية، لفة كاملة كل 3 ثواني.

**When to use:**
- EN: Use when you need a boxed version of M-153.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-153.

#### `al-fx-154-fast` — Glow Outline · Fast
**توهج حول الشخص · سريع**

*accent · calm · blur · easing: easeInOutSine · loop · 2s*

*Original: M-154*

Variant of M-154: أسرع بـ 40%

**Spec (EN):** Using the person matte, add an accent outer glow (drop shadow on the matte edge) that pulses from 0 to about 2.5% blur every 2s.

**Spec (AR):** باستخدام قناع الشخص، حط توهج خارجي بلون الهوية (ظل على حافة القناع) ينبض من 0 لـ تقريباً 2.5% ضبابية كل ثانيتين.

**When to use:**
- EN: Use when you need a fast version of M-154.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-154.

#### `al-fx-154-slow` — Glow Outline · Slow
**توهج حول الشخص · بطيء**

*accent · calm · blur · easing: easeInOutSine · loop · 2s*

*Original: M-154*

Variant of M-154: أبطأ بـ 60%

**Spec (EN):** Using the person matte, add an accent outer glow (drop shadow on the matte edge) that pulses from 0 to about 2.5% blur every 2s.

**Spec (AR):** باستخدام قناع الشخص، حط توهج خارجي بلون الهوية (ظل على حافة القناع) ينبض من 0 لـ تقريباً 2.5% ضبابية كل ثانيتين.

**When to use:**
- EN: Use when you need a slow version of M-154.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-154.

#### `al-fx-154-gold` — Glow Outline · Gold
**توهج حول الشخص · ذهبي**

*accent · calm · blur · easing: easeInOutSine · loop · 2s*

*Original: M-154*

Variant of M-154: نسخة ذهبية فاخرة

**Spec (EN):** Using the person matte, add an accent outer glow (drop shadow on the matte edge) that pulses from 0 to about 2.5% blur every 2s.

**Spec (AR):** باستخدام قناع الشخص، حط توهج خارجي بلون الهوية (ظل على حافة القناع) ينبض من 0 لـ تقريباً 2.5% ضبابية كل ثانيتين.

**When to use:**
- EN: Use when you need a gold version of M-154.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-154.

#### `al-fx-154-boxed` — Glow Outline · Boxed
**توهج حول الشخص · صندوق**

*accent · calm · blur · easing: easeInOutSine · loop · 2s*

*Original: M-154*

Variant of M-154: النص داخل صندوق ملون

**Spec (EN):** Using the person matte, add an accent outer glow (drop shadow on the matte edge) that pulses from 0 to about 2.5% blur every 2s.

**Spec (AR):** باستخدام قناع الشخص، حط توهج خارجي بلون الهوية (ظل على حافة القناع) ينبض من 0 لـ تقريباً 2.5% ضبابية كل ثانيتين.

**When to use:**
- EN: Use when you need a boxed version of M-154.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-154.

#### `al-fx-155-fast` — VHS Glitch · Fast
**تشويش شريط فيديو · سريع**

*accent · any · depth · easing: steps · loop*

*Original: M-155*

Variant of M-155: أسرع بـ 40%

**Spec (EN):** Add short horizontal frame jumps (±3%), brief color shifts, and a soft bright noise band that rolls up the frame every couple of seconds.

**Spec (AR):** حط نطات أفقية قصيرة للصورة (±3%)، وتغيّر ألوان لحظي، وشريط تشويش فاتح ناعم يطلع على الشاشة من تحت لفوق كل كم ثانية.

**When to use:**
- EN: Use when you need a fast version of M-155.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-155.

#### `al-fx-155-slow` — VHS Glitch · Slow
**تشويش شريط فيديو · بطيء**

*accent · any · depth · easing: steps · loop*

*Original: M-155*

Variant of M-155: أبطأ بـ 60%

**Spec (EN):** Add short horizontal frame jumps (±3%), brief color shifts, and a soft bright noise band that rolls up the frame every couple of seconds.

**Spec (AR):** حط نطات أفقية قصيرة للصورة (±3%)، وتغيّر ألوان لحظي، وشريط تشويش فاتح ناعم يطلع على الشاشة من تحت لفوق كل كم ثانية.

**When to use:**
- EN: Use when you need a slow version of M-155.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-155.

#### `al-fx-155-gold` — VHS Glitch · Gold
**تشويش شريط فيديو · ذهبي**

*accent · any · depth · easing: steps · loop*

*Original: M-155*

Variant of M-155: نسخة ذهبية فاخرة

**Spec (EN):** Add short horizontal frame jumps (±3%), brief color shifts, and a soft bright noise band that rolls up the frame every couple of seconds.

**Spec (AR):** حط نطات أفقية قصيرة للصورة (±3%)، وتغيّر ألوان لحظي، وشريط تشويش فاتح ناعم يطلع على الشاشة من تحت لفوق كل كم ثانية.

**When to use:**
- EN: Use when you need a gold version of M-155.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-155.

#### `al-fx-155-boxed` — VHS Glitch · Boxed
**تشويش شريط فيديو · صندوق**

*accent · any · depth · easing: steps · loop*

*Original: M-155*

Variant of M-155: النص داخل صندوق ملون

**Spec (EN):** Add short horizontal frame jumps (±3%), brief color shifts, and a soft bright noise band that rolls up the frame every couple of seconds.

**Spec (AR):** حط نطات أفقية قصيرة للصورة (±3%)، وتغيّر ألوان لحظي، وشريط تشويش فاتح ناعم يطلع على الشاشة من تحت لفوق كل كم ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-155.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-155.

#### `al-fx-156-fast` — Film Grain · Fast
**حبيبات فيلم · سريع**

*accent · any · timeline · easing: steps · loop*

*Original: M-156*

Variant of M-156: أسرع بـ 40%

**Spec (EN):** Overlay fine moving noise at about 35% opacity, jumping position every frame, plus a tiny brightness flicker (±10%).

**Spec (AR):** حط طبقة حبيبات ناعمة تتحرك بشفافية تقريباً 35%، تنط مكانها كل فريم، مع رمشة إضاءة خفيفة جداً (±10%).

**When to use:**
- EN: Use when you need a fast version of M-156.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-156.

#### `al-fx-156-slow` — Film Grain · Slow
**حبيبات فيلم · بطيء**

*accent · any · timeline · easing: steps · loop*

*Original: M-156*

Variant of M-156: أبطأ بـ 60%

**Spec (EN):** Overlay fine moving noise at about 35% opacity, jumping position every frame, plus a tiny brightness flicker (±10%).

**Spec (AR):** حط طبقة حبيبات ناعمة تتحرك بشفافية تقريباً 35%، تنط مكانها كل فريم، مع رمشة إضاءة خفيفة جداً (±10%).

**When to use:**
- EN: Use when you need a slow version of M-156.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-156.

#### `al-fx-156-gold` — Film Grain · Gold
**حبيبات فيلم · ذهبي**

*accent · any · timeline · easing: steps · loop*

*Original: M-156*

Variant of M-156: نسخة ذهبية فاخرة

**Spec (EN):** Overlay fine moving noise at about 35% opacity, jumping position every frame, plus a tiny brightness flicker (±10%).

**Spec (AR):** حط طبقة حبيبات ناعمة تتحرك بشفافية تقريباً 35%، تنط مكانها كل فريم، مع رمشة إضاءة خفيفة جداً (±10%).

**When to use:**
- EN: Use when you need a gold version of M-156.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-156.

#### `al-fx-156-boxed` — Film Grain · Boxed
**حبيبات فيلم · صندوق**

*accent · any · timeline · easing: steps · loop*

*Original: M-156*

Variant of M-156: النص داخل صندوق ملون

**Spec (EN):** Overlay fine moving noise at about 35% opacity, jumping position every frame, plus a tiny brightness flicker (±10%).

**Spec (AR):** حط طبقة حبيبات ناعمة تتحرك بشفافية تقريباً 35%، تنط مكانها كل فريم، مع رمشة إضاءة خفيفة جداً (±10%).

**When to use:**
- EN: Use when you need a boxed version of M-156.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-156.

#### `al-fx-157-fast` — Shine Sweep · Fast
**لمعة على النص · سريع**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-157*

Variant of M-157: أسرع بـ 40%

**Spec (EN):** A narrow bright diagonal band clipped to the text or logo sweeps across it from one side to the other over 0.8s.

**Spec (AR):** شريط لامع مايل ورفيع داخل حدود النص أو الشعار يمر عليه من جهة للثانية خلال 0.8 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-157.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-157.

#### `al-fx-157-slow` — Shine Sweep · Slow
**لمعة على النص · بطيء**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-157*

Variant of M-157: أبطأ بـ 60%

**Spec (EN):** A narrow bright diagonal band clipped to the text or logo sweeps across it from one side to the other over 0.8s.

**Spec (AR):** شريط لامع مايل ورفيع داخل حدود النص أو الشعار يمر عليه من جهة للثانية خلال 0.8 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-157.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-157.

#### `al-fx-157-gold` — Shine Sweep · Gold
**لمعة على النص · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-157*

Variant of M-157: نسخة ذهبية فاخرة

**Spec (EN):** A narrow bright diagonal band clipped to the text or logo sweeps across it from one side to the other over 0.8s.

**Spec (AR):** شريط لامع مايل ورفيع داخل حدود النص أو الشعار يمر عليه من جهة للثانية خلال 0.8 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-157.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-157.

#### `al-fx-157-boxed` — Shine Sweep · Boxed
**لمعة على النص · صندوق**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-157*

Variant of M-157: النص داخل صندوق ملون

**Spec (EN):** A narrow bright diagonal band clipped to the text or logo sweeps across it from one side to the other over 0.8s.

**Spec (AR):** شريط لامع مايل ورفيع داخل حدود النص أو الشعار يمر عليه من جهة للثانية خلال 0.8 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-157.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-157.

#### `al-fx-158-fast` — Bokeh Lights · Fast
**أضواء بوكيه · سريع**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-158*

Variant of M-158: أسرع بـ 40%

**Spec (EN):** Place 6–10 blurred warm circles of different sizes on the background layer; each drifts a little and gently grows and fades on a 4s loop.

**Spec (AR):** حط من 6 إلى 10 دواير ضوء مضببة دافية بأحجام مختلفة على طبقة الخلفية، وكل وحدة تتحرك شوي وتكبر وتخف بنعومة كل 4 ثواني.

**When to use:**
- EN: Use when you need a fast version of M-158.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-158.

#### `al-fx-158-slow` — Bokeh Lights · Slow
**أضواء بوكيه · بطيء**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-158*

Variant of M-158: أبطأ بـ 60%

**Spec (EN):** Place 6–10 blurred warm circles of different sizes on the background layer; each drifts a little and gently grows and fades on a 4s loop.

**Spec (AR):** حط من 6 إلى 10 دواير ضوء مضببة دافية بأحجام مختلفة على طبقة الخلفية، وكل وحدة تتحرك شوي وتكبر وتخف بنعومة كل 4 ثواني.

**When to use:**
- EN: Use when you need a slow version of M-158.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-158.

#### `al-fx-158-gold` — Bokeh Lights · Gold
**أضواء بوكيه · ذهبي**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-158*

Variant of M-158: نسخة ذهبية فاخرة

**Spec (EN):** Place 6–10 blurred warm circles of different sizes on the background layer; each drifts a little and gently grows and fades on a 4s loop.

**Spec (AR):** حط من 6 إلى 10 دواير ضوء مضببة دافية بأحجام مختلفة على طبقة الخلفية، وكل وحدة تتحرك شوي وتكبر وتخف بنعومة كل 4 ثواني.

**When to use:**
- EN: Use when you need a gold version of M-158.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-158.

#### `al-fx-158-boxed` — Bokeh Lights · Boxed
**أضواء بوكيه · صندوق**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-158*

Variant of M-158: النص داخل صندوق ملون

**Spec (EN):** Place 6–10 blurred warm circles of different sizes on the background layer; each drifts a little and gently grows and fades on a 4s loop.

**Spec (AR):** حط من 6 إلى 10 دواير ضوء مضببة دافية بأحجام مختلفة على طبقة الخلفية، وكل وحدة تتحرك شوي وتكبر وتخف بنعومة كل 4 ثواني.

**When to use:**
- EN: Use when you need a boxed version of M-158.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-158.

#### `al-fx-159-fast` — Speed Lines · Fast
**خطوط سرعة · سريع**

*accent · any · timeline · easing: steps · loop · 0.4s*

*Original: M-159*

Variant of M-159: أسرع بـ 40%

**Spec (EN):** Draw thin white radial lines around the subject with a clear center, jittering in angle and scale every few frames.

**Spec (AR):** ارسم خطوط بيضا رفيعة شعاعية حول الهدف والنص فاضي، ترجف بالزاوية والحجم كل كم فريم.

**When to use:**
- EN: Use when you need a fast version of M-159.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-159.

#### `al-fx-159-slow` — Speed Lines · Slow
**خطوط سرعة · بطيء**

*accent · any · timeline · easing: steps · loop · 0.4s*

*Original: M-159*

Variant of M-159: أبطأ بـ 60%

**Spec (EN):** Draw thin white radial lines around the subject with a clear center, jittering in angle and scale every few frames.

**Spec (AR):** ارسم خطوط بيضا رفيعة شعاعية حول الهدف والنص فاضي، ترجف بالزاوية والحجم كل كم فريم.

**When to use:**
- EN: Use when you need a slow version of M-159.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-159.

#### `al-fx-159-gold` — Speed Lines · Gold
**خطوط سرعة · ذهبي**

*accent · any · timeline · easing: steps · loop · 0.4s*

*Original: M-159*

Variant of M-159: نسخة ذهبية فاخرة

**Spec (EN):** Draw thin white radial lines around the subject with a clear center, jittering in angle and scale every few frames.

**Spec (AR):** ارسم خطوط بيضا رفيعة شعاعية حول الهدف والنص فاضي، ترجف بالزاوية والحجم كل كم فريم.

**When to use:**
- EN: Use when you need a gold version of M-159.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-159.

#### `al-fx-159-boxed` — Speed Lines · Boxed
**خطوط سرعة · صندوق**

*accent · any · timeline · easing: steps · loop · 0.4s*

*Original: M-159*

Variant of M-159: النص داخل صندوق ملون

**Spec (EN):** Draw thin white radial lines around the subject with a clear center, jittering in angle and scale every few frames.

**Spec (AR):** ارسم خطوط بيضا رفيعة شعاعية حول الهدف والنص فاضي، ترجف بالزاوية والحجم كل كم فريم.

**When to use:**
- EN: Use when you need a boxed version of M-159.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-159.

#### `al-fx-160-fast` — Face Tracking Box · Fast
**مربع تتبع الوجه · سريع**

*accent · calm · camera · easing: easeInOutSine · loop*

*Original: M-160*

Variant of M-160: أسرع بـ 40%

**Spec (EN):** Detect the face and draw four mint corner brackets around it that follow it smoothly, with a small mono label above like "FACE 98%".

**Spec (AR):** اكتشف الوجه وارسم أربع زوايا نعناعية حوله تتبعه بنعومة، وفوقها تاق mono صغير مثل "FACE 98%".

**When to use:**
- EN: Use when you need a fast version of M-160.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-160.

#### `al-fx-160-slow` — Face Tracking Box · Slow
**مربع تتبع الوجه · بطيء**

*accent · calm · camera · easing: easeInOutSine · loop*

*Original: M-160*

Variant of M-160: أبطأ بـ 60%

**Spec (EN):** Detect the face and draw four mint corner brackets around it that follow it smoothly, with a small mono label above like "FACE 98%".

**Spec (AR):** اكتشف الوجه وارسم أربع زوايا نعناعية حوله تتبعه بنعومة، وفوقها تاق mono صغير مثل "FACE 98%".

**When to use:**
- EN: Use when you need a slow version of M-160.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-160.

#### `al-fx-160-gold` — Face Tracking Box · Gold
**مربع تتبع الوجه · ذهبي**

*accent · calm · camera · easing: easeInOutSine · loop*

*Original: M-160*

Variant of M-160: نسخة ذهبية فاخرة

**Spec (EN):** Detect the face and draw four mint corner brackets around it that follow it smoothly, with a small mono label above like "FACE 98%".

**Spec (AR):** اكتشف الوجه وارسم أربع زوايا نعناعية حوله تتبعه بنعومة، وفوقها تاق mono صغير مثل "FACE 98%".

**When to use:**
- EN: Use when you need a gold version of M-160.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-160.

#### `al-fx-160-boxed` — Face Tracking Box · Boxed
**مربع تتبع الوجه · صندوق**

*accent · calm · camera · easing: easeInOutSine · loop*

*Original: M-160*

Variant of M-160: النص داخل صندوق ملون

**Spec (EN):** Detect the face and draw four mint corner brackets around it that follow it smoothly, with a small mono label above like "FACE 98%".

**Spec (AR):** اكتشف الوجه وارسم أربع زوايا نعناعية حوله تتبعه بنعومة، وفوقها تاق mono صغير مثل "FACE 98%".

**When to use:**
- EN: Use when you need a boxed version of M-160.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-160.

### Social (السوشال) — 125 motions

#### `al-soc-031` — Follow Tap
**ضغطة زر متابعة**

*workhorse · any · timeline · easing: easeOutCubic · 1.4s*

*Original: M-031*

When you say "follow me".

**Spec (EN):** A finger tap indicator (white circle with soft halo) glides onto a Follow button, presses it (button scales to 88%), and the button flips from accent "متابعة" to gray "تتابعه ✓". Add a soft click sound.

**Spec (AR):** مؤشر ضغطة (دائرة بيضا بهالة ناعمة) يجي على زر متابعة، يضغطه (الزر يصغر لـ 88%)، والزر يتحول من "متابعة" بلون الهوية لـ "تتابعه ✓" رمادي. حط معاه صوت كليك خفيف.

**When to use:**
- EN: When you say "follow me".
- AR: لمن تقول "تابعني".

#### `al-soc-032` — Comment Typing
**تعليق ينكتب**

*workhorse · any · sound · easing: steps · 1.5s typing*

*Original: M-032*

When you say "write it in the comments".

**Spec (EN):** An Instagram-style comment field shows placeholder text, then the keyword types in letter by letter (right-to-left for Arabic) and the blue send button pulses (scale 75% to 115% to 100%). Follow with M-035 or M-034.

**Spec (AR):** خانة تعليق بستايل إنستغرام فيها نص "أضف تعليقاً…"، وبعدين الكلمة تنكتب حرف حرف (من اليمين لليسار بالعربي) وزر الإرسال الأزرق ينبض (75% ثم 115% ثم 100%). وبعدها تقدر تحط M-035 أو M-034.

**When to use:**
- EN: When you say "write it in the comments".
- AR: لمن تقول "اكتب بالكومنت".

#### `al-soc-033` — Like Burst
**قلب لايك ينفجر**

*workhorse · high · depth · easing: easeOutBack · 0.6s*

*Original: M-033*

Asking for a like, or a sweet moment.

**Spec (EN):** A red heart pops from 0 to 135% and settles at 100% (0.35s). At the same time 8 small dots shoot radially outward 27% of the frame and fade. Optionally show a "+1" floating up.

**Spec (AR):** قلب أحمر ينط من 0 لـ 135% ويستقر على 100% (0.35 ثانية). وبنفس الوقت 8 نقاط صغيرة تنطلق لبرا بشكل دائري بمسافة 27% من الشاشة وتختفي. وتقدر تطلّع "+1" يطير لفوق.

**When to use:**
- EN: Asking for a like, or a sweet moment.
- AR: طلب لايك أو لحظة حلوة.

#### `al-soc-034` — DM Notification
**إشعار رسالة**

*workhorse · any · depth · easing: spring · 0.5s in · 2s hold*

*Original: M-034*

"The prompt will reach you in DMs".

**Spec (EN):** A phone-style notification card (app icon, bold title, one-line preview) drops from above the top edge with a spring (overshoot about 10%), holds about 2s, then slides back up. Add a soft notification chime.

**Spec (AR):** إشعار بستايل الجوال (أيقونة التطبيق، عنوان عريض، وسطر معاينة) ينزل من فوق الشاشة بحركة نابض (يتعدى تقريباً 10%)، يثبت تقريباً ثانيتين، وبعدين يرجع لفوق. حط معاه صوت إشعار ناعم.

**When to use:**
- EN: "The prompt will reach you in DMs".
- AR: "البرومبت بيوصلك بالخاص".

#### `al-soc-035` — Paper Plane
**طيارة ورق**

*workhorse · calm · depth · easing: easeInOutSine · 1.2s*

*Original: M-035*

Sending a message or a comment.

**Spec (EN):** A paper-plane icon flies along a curved path from the lower left to the upper right, rotating to follow the path and shrinking at the end, leaving a dashed trail that draws behind it.

**Spec (AR):** أيقونة طيارة ورق تطير على مسار منحني من تحت يسار لفوق يمين، تلف مع اتجاه المسار وتصغر بالنهاية، وتخلي وراها خط متقطع ينرسم.

**When to use:**
- EN: Sending a message or a comment.
- AR: إرسال رسالة أو تعليق.

#### `al-soc-161` — Bell Ring
**جرس الإشعارات**

*workhorse · any · timeline · easing: easeOutCubic · 0.8s*

*Original: M-161*

When you say "turn on notifications".

**Spec (EN):** A bell icon swings from its top: +22°, -20°, +14°, -10°, +5° over 0.8s, then a red count badge pops on its corner. Add a soft ding.

**Spec (AR):** أيقونة جرس تتأرجح من فوق: +22، -20، +14، -10، +5 درجة خلال 0.8 ثانية، وبعدين شارة حمرا فيها رقم تنط على زاويتها. حط معاها صوت رنة خفيفة.

**When to use:**
- EN: When you say "turn on notifications".
- AR: لمن تقول "فعّل الإشعارات".

#### `al-soc-162` — Share Tap
**ضغطة مشاركة**

*workhorse · high · timeline · easing: easeOutBack · 0.6s*

*Original: M-162*

When you say "share it with your friends".

**Spec (EN):** A tap indicator presses the share (paper plane) icon; the icon squashes to 80% then pops to 120% and settles, with a small burst of dots.

**Spec (AR):** مؤشر ضغطة يضغط أيقونة المشاركة (طيارة ورق)، والأيقونة تنضغط لـ 80% وبعدين تنط لـ 120% وتستقر، مع انفجار نقاط صغيرة.

**When to use:**
- EN: When you say "share it with your friends".
- AR: لمن تقول "شاركه مع ربعك".

#### `al-soc-163` — Save Bookmark
**حفظ المنشور**

*workhorse · any · depth · easing: easeOutCubic · 0.5s*

*Original: M-163*

When you say "save this for later".

**Spec (EN):** A bookmark outline icon fills up from bottom to top with white over 0.5s, then pops to 120% and settles.

**Spec (AR):** أيقونة حفظ بحدود بس تتعبى أبيض من تحت لفوق خلال 0.5 ثانية، وبعدين تنط لـ 120% وتستقر.

**When to use:**
- EN: When you say "save this for later".
- AR: لمن تقول "احفظ الفيديو ترجع له".

#### `al-soc-164` — Story Ring
**حلقة الستوري**

*workhorse · calm · depth · easing: linear · loop · 3s*

*Original: M-164*

A profile photo with a rotating colorful story ring.

**Spec (EN):** A circular avatar sits inside a gradient ring (brand colors) that rotates one full turn every 3s, like an unseen story.

**Spec (AR):** صورة بروفايل دائرية داخل حلقة متدرجة بألوان الهوية، تلف لفة كاملة كل 3 ثواني، مثل الستوري اللي ما انشافت.

**When to use:**
- EN: A profile photo with a rotating colorful story ring.
- AR: صورة البروفايل مع حلقة ستوري ملونة تدور.

#### `al-soc-165` — Swipe Up Arrow
**سهم اسحب لفوق**

*workhorse · any · depth · easing: easeOutCubic · loop · 1.2s*

*Original: M-165*

When you want viewers to swipe up or tap the link.

**Spec (EN):** Two stacked chevrons move up 40% and fade, repeating every 1.2s, above a short label such as "اسحب".

**Spec (AR):** سهمين فوق بعض يطلعون لفوق 40% ويختفون، ويتكررون كل 1.2 ثانية، فوق كلمة قصيرة مثل "اسحب".

**When to use:**
- EN: When you want viewers to swipe up or tap the link.
- AR: لمن تبي الناس تسحب أو تشوف الرابط.

#### `al-soc-166` — Poll Sticker
**ملصق تصويت**

*workhorse · any · timeline · easing: easeOutCubic · 0.8s fill*

*Original: M-166*

A two-option poll whose results fill up.

**Spec (EN):** A light card with a question and two option rows. Accent bars fill each row to its percentage over 0.8s, with the percentages shown.

**Spec (AR):** بطاقة فاتحة فيها سؤال وخيارين. شرائط بلون الهوية تعبي كل خيار لنسبته خلال 0.8 ثانية، والنسب ظاهرة.

**When to use:**
- EN: A two-option poll whose results fill up.
- AR: سؤال بخيارين والنتائج تعبي.

#### `al-soc-167` — Typing Dots
**نقاط يكتب**

*workhorse · calm · timeline · easing: easeInOutSine · loop · 1s*

*Original: M-167*

A chat "typing…" bubble.

**Spec (EN):** A chat bubble with three dots; each dot rises and brightens in turn, 0.15s apart, looping every second.

**Spec (AR):** فقاعة شات فيها ثلاث نقاط، كل نقطة تطلع وتنور بدورها وبينهم 0.15 ثانية، وتتكرر كل ثانية.

**When to use:**
- EN: A chat "typing…" bubble.
- AR: فقاعة "يكتب..." مثل الشات.

#### `al-soc-168` — Chat Bubbles
**فقاعات محادثة**

*workhorse · high · timeline · easing: easeOutBack · 0.25s per bubble*

*Original: M-168*

A conversation appearing message by message.

**Spec (EN):** Message bubbles pop in one at a time from their tail corner (scale 0 to 105% to 100% over 0.25s), alternating sides like a real chat.

**Spec (AR):** فقاعات الرسائل تنط وحدة وحدة من زاوية ذيلها (من 0 لـ 105% لـ 100% خلال 0.25 ثانية)، يمين ويسار بالتناوب مثل المحادثة الحقيقية.

**When to use:**
- EN: A conversation appearing message by message.
- AR: محادثة تطلع رسالة رسالة.

#### `al-soc-169` — Floating Hearts
**قلوب تطير**

*workhorse · any · depth · easing: easeOut · loop*

*Original: M-169*

Hearts float upward like a live stream.

**Spec (EN):** Small hearts spawn near the bottom corner every 0.2–0.4s and float up about 90% of the frame with a gentle sideways sway, growing slightly and fading.

**Spec (AR):** قلوب صغيرة تطلع قرب الزاوية التحت كل 0.2 إلى 0.4 ثانية، وتطير لفوق تقريباً 90% من الشاشة مع تمايل خفيف على الجنب، تكبر شوي وتختفي.

**When to use:**
- EN: Hearts float upward like a live stream.
- AR: قلوب تطلع وتطير لفوق، مثل اللايف.

#### `al-soc-170` — View Counter
**عداد مشاهدات**

*workhorse · any · timeline · easing: easeOutExpo · 1.2s count*

*Original: M-170*

A view count ticking up.

**Spec (EN):** An eye icon with a number counting up from 0 to the target (see M-040), in tabular mono digits.

**Spec (AR):** أيقونة عين مع رقم يعد من 0 لين الرقم المطلوب (شوف M-040)، بأرقام mono متساوية العرض.

**When to use:**
- EN: A view count ticking up.
- AR: عدد المشاهدات يعد قدامك.

#### `al-soc-171` — Profile Card
**بطاقة بروفايل**

*workhorse · any · timeline · easing: spring · 0.5s in*

*Original: M-171*

Introduces your account with a card rising from below.

**Spec (EN):** A light rounded card with avatar, name, handle and a follow button slides up from below the frame with a spring and a 4% overshoot, holds, then slides back.

**Spec (AR):** بطاقة فاتحة بزوايا دائرية فيها الصورة والاسم واليوزر وزر متابعة، تطلع من تحت الشاشة بحركة نابض وتتعدى 4%، تثبت، وبعدين ترجع.

**When to use:**
- EN: Introduces your account with a card rising from below.
- AR: تعريف بحسابك ببطاقة تطلع من تحت.

#### `al-soc-172` — Link Sticker
**ملصق رابط**

*workhorse · high · timeline · easing: easeOutBack · 0.4s + wiggle*

*Original: M-172*

When you say "link in bio".

**Spec (EN):** A white pill sticker with a link icon and the URL pops in (0.4s), then wiggles gently every couple of seconds to invite a tap.

**Spec (AR):** ملصق أبيض على شكل كبسولة فيه أيقونة رابط والرابط، ينط (0.4 ثانية)، وبعدين يتمايل بخفة كل كم ثانية عشان يشجع على الضغط.

**When to use:**
- EN: When you say "link in bio".
- AR: لمن تقول "الرابط بالبايو".

#### `al-soc-173` — Countdown
**عد تنازلي**

*workhorse · high · timeline · easing: easeOutBack · 1s per number*

*Original: M-173*

A 3-2-1 countdown before a big moment.

**Spec (EN):** Big mono digits 3, 2, 1 replace each other every second, each popping from 60% to 110% to 100% and fading out. Add a tick sound per number.

**Spec (AR):** أرقام mono كبيرة 3 و2 و1 تتبدل كل ثانية، كل رقم ينط من 60% لـ 110% لـ 100% ويختفي. حط صوت تكة مع كل رقم.

**When to use:**
- EN: A 3-2-1 countdown before a big moment.
- AR: عد 3، 2، 1 قبل لحظة مهمة.

#### `al-soc-174` — Question Sticker
**ملصق سؤال**

*workhorse · high · timeline · easing: easeOutBack · 0.4s in*

*Original: M-174*

An "ask me a question" box like Stories.

**Spec (EN):** A light card with an accent header "اسألني سؤال" and a text field pops in, then a short question types into the field.

**Spec (AR):** بطاقة فاتحة فوقها عنوان بلون الهوية "اسألني سؤال" وتحته خانة كتابة، تنط، وبعدين سؤال قصير ينكتب في الخانة.

**When to use:**
- EN: An "ask me a question" box like Stories.
- AR: "اسألني سؤال" مثل الستوري.

#### `al-soc-175` — Mention Tag
**تاق منشن**

*workhorse · high · timeline · easing: easeOutBack · 0.3s*

*Original: M-175*

An account tag pops onto a person or object.

**Spec (EN):** A dark rounded tag with a small pointer and the @handle pops from the tagged point (scale 0 to 110% to 100% over 0.3s).

**Spec (AR):** تاق غامق بزوايا دائرية مع سهم صغير واليوزر، ينط من النقطة المحددة (من 0 لـ 110% لـ 100% خلال 0.3 ثانية).

**When to use:**
- EN: An account tag pops onto a person or object.
- AR: تاق باسم حساب يطلع على شخص أو شي.

#### `al-soc-176` — Verified Badge
**علامة التوثيق**

*workhorse · high · depth · easing: easeOutBack · 0.4s*

*Original: M-176*

A blue verified check next to your name.

**Spec (EN):** A blue circular check badge spins in from -180° and 0 scale to a 130% pop and settles next to the name over 0.4s.

**Spec (AR):** علامة توثيق زرقا دائرية تدخل وهي تلف من -180 درجة وحجم 0، تنط لـ 130% وتستقر جنب الاسم خلال 0.4 ثانية.

**When to use:**
- EN: A blue verified check next to your name.
- AR: علامة توثيق زرقا جنب اسمك.

#### `al-soc-177` — Comment Stack
**تعليقات تتكدس**

*workhorse · any · depth · easing: easeOutCubic · 0.3s per comment*

*Original: M-177*

Comments pile up one after another, like audience reactions.

**Spec (EN):** Comment rows (avatar dot + short text) slide up and fade in one by one, 0.5s apart, stacking into a list.

**Spec (AR):** صفوف تعليقات (نقطة صورة ونص قصير) تطلع لفوق وتظهر وحدة وحدة وبينهم 0.5 ثانية، وتتكدس في قائمة.

**When to use:**
- EN: Comments pile up one after another, like audience reactions.
- AR: تعليقات تطلع ورا بعض، مثل رد فعل الناس.

#### `al-soc-178` — Notification Badge
**شارة رقم**

*workhorse · high · depth · easing: easeOutBack · 0.3s*

*Original: M-178*

A red count badge bounces onto an icon.

**Spec (EN):** A red rounded badge with a number pops onto the top corner of an icon (0 to 130% to 100% over 0.3s), then the icon gives a small pop.

**Spec (AR):** شارة حمرا بزوايا دائرية فيها رقم تنط على زاوية الأيقونة الفوق (من 0 لـ 130% لـ 100% خلال 0.3 ثانية)، وبعدين الأيقونة تنط نطة صغيرة.

**When to use:**
- EN: A red count badge bounces onto an icon.
- AR: رقم أحمر ينط على أيقونة.

#### `al-soc-179` — Sound On
**شغّل الصوت**

*workhorse · calm · timeline · easing: easeInOutSine · loop · 1.2s*

*Original: M-179*

When you want viewers to turn the sound on.

**Spec (EN):** A speaker icon with three sound waves that light up one after another, 0.2s apart, looping every 1.2s.

**Spec (AR):** أيقونة سماعة مع ثلاث موجات صوت تنور وحدة ورا الثانية وبينهم 0.2 ثانية، وتتكرر كل 1.2 ثانية.

**When to use:**
- EN: When you want viewers to turn the sound on.
- AR: لمن تبي المشاهد يشغل الصوت.

#### `al-soc-180` — Search Typing
**بحث ينكتب**

*workhorse · any · timeline · easing: steps · 1.2s typing*

*Original: M-180*

When you say "search for…".

**Spec (EN):** A light rounded search bar with a magnifier icon; the query types in letter by letter from the reading-start side.

**Spec (AR):** شريط بحث فاتح بزوايا دائرية فيه أيقونة عدسة، والكلام ينكتب فيه حرف حرف من جهة بداية القراءة.

**When to use:**
- EN: When you say "search for…".
- AR: لمن تقول "ابحث عن…".

#### `al-soc-031-fast` — Follow Tap · Fast
**ضغطة زر متابعة · سريع**

*accent · any · timeline · easing: easeOutCubic · 1.4s*

*Original: M-031*

Variant of M-031: أسرع بـ 40%

**Spec (EN):** A finger tap indicator (white circle with soft halo) glides onto a Follow button, presses it (button scales to 88%), and the button flips from accent "متابعة" to gray "تتابعه ✓". Add a soft click sound.

**Spec (AR):** مؤشر ضغطة (دائرة بيضا بهالة ناعمة) يجي على زر متابعة، يضغطه (الزر يصغر لـ 88%)، والزر يتحول من "متابعة" بلون الهوية لـ "تتابعه ✓" رمادي. حط معاه صوت كليك خفيف.

**When to use:**
- EN: Use when you need a fast version of M-031.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-031.

#### `al-soc-031-slow` — Follow Tap · Slow
**ضغطة زر متابعة · بطيء**

*accent · any · timeline · easing: easeOutCubic · 1.4s*

*Original: M-031*

Variant of M-031: أبطأ بـ 60%

**Spec (EN):** A finger tap indicator (white circle with soft halo) glides onto a Follow button, presses it (button scales to 88%), and the button flips from accent "متابعة" to gray "تتابعه ✓". Add a soft click sound.

**Spec (AR):** مؤشر ضغطة (دائرة بيضا بهالة ناعمة) يجي على زر متابعة، يضغطه (الزر يصغر لـ 88%)، والزر يتحول من "متابعة" بلون الهوية لـ "تتابعه ✓" رمادي. حط معاه صوت كليك خفيف.

**When to use:**
- EN: Use when you need a slow version of M-031.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-031.

#### `al-soc-031-gold` — Follow Tap · Gold
**ضغطة زر متابعة · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 1.4s*

*Original: M-031*

Variant of M-031: نسخة ذهبية فاخرة

**Spec (EN):** A finger tap indicator (white circle with soft halo) glides onto a Follow button, presses it (button scales to 88%), and the button flips from accent "متابعة" to gray "تتابعه ✓". Add a soft click sound.

**Spec (AR):** مؤشر ضغطة (دائرة بيضا بهالة ناعمة) يجي على زر متابعة، يضغطه (الزر يصغر لـ 88%)، والزر يتحول من "متابعة" بلون الهوية لـ "تتابعه ✓" رمادي. حط معاه صوت كليك خفيف.

**When to use:**
- EN: Use when you need a gold version of M-031.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-031.

#### `al-soc-031-boxed` — Follow Tap · Boxed
**ضغطة زر متابعة · صندوق**

*accent · any · timeline · easing: easeOutCubic · 1.4s*

*Original: M-031*

Variant of M-031: النص داخل صندوق ملون

**Spec (EN):** A finger tap indicator (white circle with soft halo) glides onto a Follow button, presses it (button scales to 88%), and the button flips from accent "متابعة" to gray "تتابعه ✓". Add a soft click sound.

**Spec (AR):** مؤشر ضغطة (دائرة بيضا بهالة ناعمة) يجي على زر متابعة، يضغطه (الزر يصغر لـ 88%)، والزر يتحول من "متابعة" بلون الهوية لـ "تتابعه ✓" رمادي. حط معاه صوت كليك خفيف.

**When to use:**
- EN: Use when you need a boxed version of M-031.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-031.

#### `al-soc-032-fast` — Comment Typing · Fast
**تعليق ينكتب · سريع**

*accent · any · sound · easing: steps · 1.5s typing*

*Original: M-032*

Variant of M-032: أسرع بـ 40%

**Spec (EN):** An Instagram-style comment field shows placeholder text, then the keyword types in letter by letter (right-to-left for Arabic) and the blue send button pulses (scale 75% to 115% to 100%). Follow with M-035 or M-034.

**Spec (AR):** خانة تعليق بستايل إنستغرام فيها نص "أضف تعليقاً…"، وبعدين الكلمة تنكتب حرف حرف (من اليمين لليسار بالعربي) وزر الإرسال الأزرق ينبض (75% ثم 115% ثم 100%). وبعدها تقدر تحط M-035 أو M-034.

**When to use:**
- EN: Use when you need a fast version of M-032.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-032.

#### `al-soc-032-slow` — Comment Typing · Slow
**تعليق ينكتب · بطيء**

*accent · any · sound · easing: steps · 1.5s typing*

*Original: M-032*

Variant of M-032: أبطأ بـ 60%

**Spec (EN):** An Instagram-style comment field shows placeholder text, then the keyword types in letter by letter (right-to-left for Arabic) and the blue send button pulses (scale 75% to 115% to 100%). Follow with M-035 or M-034.

**Spec (AR):** خانة تعليق بستايل إنستغرام فيها نص "أضف تعليقاً…"، وبعدين الكلمة تنكتب حرف حرف (من اليمين لليسار بالعربي) وزر الإرسال الأزرق ينبض (75% ثم 115% ثم 100%). وبعدها تقدر تحط M-035 أو M-034.

**When to use:**
- EN: Use when you need a slow version of M-032.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-032.

#### `al-soc-032-gold` — Comment Typing · Gold
**تعليق ينكتب · ذهبي**

*accent · any · sound · easing: steps · 1.5s typing*

*Original: M-032*

Variant of M-032: نسخة ذهبية فاخرة

**Spec (EN):** An Instagram-style comment field shows placeholder text, then the keyword types in letter by letter (right-to-left for Arabic) and the blue send button pulses (scale 75% to 115% to 100%). Follow with M-035 or M-034.

**Spec (AR):** خانة تعليق بستايل إنستغرام فيها نص "أضف تعليقاً…"، وبعدين الكلمة تنكتب حرف حرف (من اليمين لليسار بالعربي) وزر الإرسال الأزرق ينبض (75% ثم 115% ثم 100%). وبعدها تقدر تحط M-035 أو M-034.

**When to use:**
- EN: Use when you need a gold version of M-032.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-032.

#### `al-soc-032-boxed` — Comment Typing · Boxed
**تعليق ينكتب · صندوق**

*accent · any · sound · easing: steps · 1.5s typing*

*Original: M-032*

Variant of M-032: النص داخل صندوق ملون

**Spec (EN):** An Instagram-style comment field shows placeholder text, then the keyword types in letter by letter (right-to-left for Arabic) and the blue send button pulses (scale 75% to 115% to 100%). Follow with M-035 or M-034.

**Spec (AR):** خانة تعليق بستايل إنستغرام فيها نص "أضف تعليقاً…"، وبعدين الكلمة تنكتب حرف حرف (من اليمين لليسار بالعربي) وزر الإرسال الأزرق ينبض (75% ثم 115% ثم 100%). وبعدها تقدر تحط M-035 أو M-034.

**When to use:**
- EN: Use when you need a boxed version of M-032.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-032.

#### `al-soc-033-fast` — Like Burst · Fast
**قلب لايك ينفجر · سريع**

*accent · any · depth · easing: easeOutBack · 0.6s*

*Original: M-033*

Variant of M-033: أسرع بـ 40%

**Spec (EN):** A red heart pops from 0 to 135% and settles at 100% (0.35s). At the same time 8 small dots shoot radially outward 27% of the frame and fade. Optionally show a "+1" floating up.

**Spec (AR):** قلب أحمر ينط من 0 لـ 135% ويستقر على 100% (0.35 ثانية). وبنفس الوقت 8 نقاط صغيرة تنطلق لبرا بشكل دائري بمسافة 27% من الشاشة وتختفي. وتقدر تطلّع "+1" يطير لفوق.

**When to use:**
- EN: Use when you need a fast version of M-033.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-033.

#### `al-soc-033-slow` — Like Burst · Slow
**قلب لايك ينفجر · بطيء**

*accent · any · depth · easing: easeOutBack · 0.6s*

*Original: M-033*

Variant of M-033: أبطأ بـ 60%

**Spec (EN):** A red heart pops from 0 to 135% and settles at 100% (0.35s). At the same time 8 small dots shoot radially outward 27% of the frame and fade. Optionally show a "+1" floating up.

**Spec (AR):** قلب أحمر ينط من 0 لـ 135% ويستقر على 100% (0.35 ثانية). وبنفس الوقت 8 نقاط صغيرة تنطلق لبرا بشكل دائري بمسافة 27% من الشاشة وتختفي. وتقدر تطلّع "+1" يطير لفوق.

**When to use:**
- EN: Use when you need a slow version of M-033.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-033.

#### `al-soc-033-gold` — Like Burst · Gold
**قلب لايك ينفجر · ذهبي**

*accent · any · depth · easing: easeOutBack · 0.6s*

*Original: M-033*

Variant of M-033: نسخة ذهبية فاخرة

**Spec (EN):** A red heart pops from 0 to 135% and settles at 100% (0.35s). At the same time 8 small dots shoot radially outward 27% of the frame and fade. Optionally show a "+1" floating up.

**Spec (AR):** قلب أحمر ينط من 0 لـ 135% ويستقر على 100% (0.35 ثانية). وبنفس الوقت 8 نقاط صغيرة تنطلق لبرا بشكل دائري بمسافة 27% من الشاشة وتختفي. وتقدر تطلّع "+1" يطير لفوق.

**When to use:**
- EN: Use when you need a gold version of M-033.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-033.

#### `al-soc-033-boxed` — Like Burst · Boxed
**قلب لايك ينفجر · صندوق**

*accent · any · depth · easing: easeOutBack · 0.6s*

*Original: M-033*

Variant of M-033: النص داخل صندوق ملون

**Spec (EN):** A red heart pops from 0 to 135% and settles at 100% (0.35s). At the same time 8 small dots shoot radially outward 27% of the frame and fade. Optionally show a "+1" floating up.

**Spec (AR):** قلب أحمر ينط من 0 لـ 135% ويستقر على 100% (0.35 ثانية). وبنفس الوقت 8 نقاط صغيرة تنطلق لبرا بشكل دائري بمسافة 27% من الشاشة وتختفي. وتقدر تطلّع "+1" يطير لفوق.

**When to use:**
- EN: Use when you need a boxed version of M-033.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-033.

#### `al-soc-034-fast` — DM Notification · Fast
**إشعار رسالة · سريع**

*accent · any · depth · easing: spring · 0.5s in · 2s hold*

*Original: M-034*

Variant of M-034: أسرع بـ 40%

**Spec (EN):** A phone-style notification card (app icon, bold title, one-line preview) drops from above the top edge with a spring (overshoot about 10%), holds about 2s, then slides back up. Add a soft notification chime.

**Spec (AR):** إشعار بستايل الجوال (أيقونة التطبيق، عنوان عريض، وسطر معاينة) ينزل من فوق الشاشة بحركة نابض (يتعدى تقريباً 10%)، يثبت تقريباً ثانيتين، وبعدين يرجع لفوق. حط معاه صوت إشعار ناعم.

**When to use:**
- EN: Use when you need a fast version of M-034.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-034.

#### `al-soc-034-slow` — DM Notification · Slow
**إشعار رسالة · بطيء**

*accent · any · depth · easing: spring · 0.5s in · 2s hold*

*Original: M-034*

Variant of M-034: أبطأ بـ 60%

**Spec (EN):** A phone-style notification card (app icon, bold title, one-line preview) drops from above the top edge with a spring (overshoot about 10%), holds about 2s, then slides back up. Add a soft notification chime.

**Spec (AR):** إشعار بستايل الجوال (أيقونة التطبيق، عنوان عريض، وسطر معاينة) ينزل من فوق الشاشة بحركة نابض (يتعدى تقريباً 10%)، يثبت تقريباً ثانيتين، وبعدين يرجع لفوق. حط معاه صوت إشعار ناعم.

**When to use:**
- EN: Use when you need a slow version of M-034.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-034.

#### `al-soc-034-gold` — DM Notification · Gold
**إشعار رسالة · ذهبي**

*accent · any · depth · easing: spring · 0.5s in · 2s hold*

*Original: M-034*

Variant of M-034: نسخة ذهبية فاخرة

**Spec (EN):** A phone-style notification card (app icon, bold title, one-line preview) drops from above the top edge with a spring (overshoot about 10%), holds about 2s, then slides back up. Add a soft notification chime.

**Spec (AR):** إشعار بستايل الجوال (أيقونة التطبيق، عنوان عريض، وسطر معاينة) ينزل من فوق الشاشة بحركة نابض (يتعدى تقريباً 10%)، يثبت تقريباً ثانيتين، وبعدين يرجع لفوق. حط معاه صوت إشعار ناعم.

**When to use:**
- EN: Use when you need a gold version of M-034.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-034.

#### `al-soc-034-boxed` — DM Notification · Boxed
**إشعار رسالة · صندوق**

*accent · any · depth · easing: spring · 0.5s in · 2s hold*

*Original: M-034*

Variant of M-034: النص داخل صندوق ملون

**Spec (EN):** A phone-style notification card (app icon, bold title, one-line preview) drops from above the top edge with a spring (overshoot about 10%), holds about 2s, then slides back up. Add a soft notification chime.

**Spec (AR):** إشعار بستايل الجوال (أيقونة التطبيق، عنوان عريض، وسطر معاينة) ينزل من فوق الشاشة بحركة نابض (يتعدى تقريباً 10%)، يثبت تقريباً ثانيتين، وبعدين يرجع لفوق. حط معاه صوت إشعار ناعم.

**When to use:**
- EN: Use when you need a boxed version of M-034.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-034.

#### `al-soc-035-fast` — Paper Plane · Fast
**طيارة ورق · سريع**

*accent · calm · depth · easing: easeInOutSine · 1.2s*

*Original: M-035*

Variant of M-035: أسرع بـ 40%

**Spec (EN):** A paper-plane icon flies along a curved path from the lower left to the upper right, rotating to follow the path and shrinking at the end, leaving a dashed trail that draws behind it.

**Spec (AR):** أيقونة طيارة ورق تطير على مسار منحني من تحت يسار لفوق يمين، تلف مع اتجاه المسار وتصغر بالنهاية، وتخلي وراها خط متقطع ينرسم.

**When to use:**
- EN: Use when you need a fast version of M-035.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-035.

#### `al-soc-035-slow` — Paper Plane · Slow
**طيارة ورق · بطيء**

*accent · calm · depth · easing: easeInOutSine · 1.2s*

*Original: M-035*

Variant of M-035: أبطأ بـ 60%

**Spec (EN):** A paper-plane icon flies along a curved path from the lower left to the upper right, rotating to follow the path and shrinking at the end, leaving a dashed trail that draws behind it.

**Spec (AR):** أيقونة طيارة ورق تطير على مسار منحني من تحت يسار لفوق يمين، تلف مع اتجاه المسار وتصغر بالنهاية، وتخلي وراها خط متقطع ينرسم.

**When to use:**
- EN: Use when you need a slow version of M-035.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-035.

#### `al-soc-035-gold` — Paper Plane · Gold
**طيارة ورق · ذهبي**

*accent · calm · depth · easing: easeInOutSine · 1.2s*

*Original: M-035*

Variant of M-035: نسخة ذهبية فاخرة

**Spec (EN):** A paper-plane icon flies along a curved path from the lower left to the upper right, rotating to follow the path and shrinking at the end, leaving a dashed trail that draws behind it.

**Spec (AR):** أيقونة طيارة ورق تطير على مسار منحني من تحت يسار لفوق يمين، تلف مع اتجاه المسار وتصغر بالنهاية، وتخلي وراها خط متقطع ينرسم.

**When to use:**
- EN: Use when you need a gold version of M-035.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-035.

#### `al-soc-035-boxed` — Paper Plane · Boxed
**طيارة ورق · صندوق**

*accent · calm · depth · easing: easeInOutSine · 1.2s*

*Original: M-035*

Variant of M-035: النص داخل صندوق ملون

**Spec (EN):** A paper-plane icon flies along a curved path from the lower left to the upper right, rotating to follow the path and shrinking at the end, leaving a dashed trail that draws behind it.

**Spec (AR):** أيقونة طيارة ورق تطير على مسار منحني من تحت يسار لفوق يمين، تلف مع اتجاه المسار وتصغر بالنهاية، وتخلي وراها خط متقطع ينرسم.

**When to use:**
- EN: Use when you need a boxed version of M-035.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-035.

#### `al-soc-161-fast` — Bell Ring · Fast
**جرس الإشعارات · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.8s*

*Original: M-161*

Variant of M-161: أسرع بـ 40%

**Spec (EN):** A bell icon swings from its top: +22°, -20°, +14°, -10°, +5° over 0.8s, then a red count badge pops on its corner. Add a soft ding.

**Spec (AR):** أيقونة جرس تتأرجح من فوق: +22، -20، +14، -10، +5 درجة خلال 0.8 ثانية، وبعدين شارة حمرا فيها رقم تنط على زاويتها. حط معاها صوت رنة خفيفة.

**When to use:**
- EN: Use when you need a fast version of M-161.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-161.

#### `al-soc-161-slow` — Bell Ring · Slow
**جرس الإشعارات · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.8s*

*Original: M-161*

Variant of M-161: أبطأ بـ 60%

**Spec (EN):** A bell icon swings from its top: +22°, -20°, +14°, -10°, +5° over 0.8s, then a red count badge pops on its corner. Add a soft ding.

**Spec (AR):** أيقونة جرس تتأرجح من فوق: +22، -20، +14، -10، +5 درجة خلال 0.8 ثانية، وبعدين شارة حمرا فيها رقم تنط على زاويتها. حط معاها صوت رنة خفيفة.

**When to use:**
- EN: Use when you need a slow version of M-161.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-161.

#### `al-soc-161-gold` — Bell Ring · Gold
**جرس الإشعارات · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.8s*

*Original: M-161*

Variant of M-161: نسخة ذهبية فاخرة

**Spec (EN):** A bell icon swings from its top: +22°, -20°, +14°, -10°, +5° over 0.8s, then a red count badge pops on its corner. Add a soft ding.

**Spec (AR):** أيقونة جرس تتأرجح من فوق: +22، -20، +14، -10، +5 درجة خلال 0.8 ثانية، وبعدين شارة حمرا فيها رقم تنط على زاويتها. حط معاها صوت رنة خفيفة.

**When to use:**
- EN: Use when you need a gold version of M-161.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-161.

#### `al-soc-161-boxed` — Bell Ring · Boxed
**جرس الإشعارات · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.8s*

*Original: M-161*

Variant of M-161: النص داخل صندوق ملون

**Spec (EN):** A bell icon swings from its top: +22°, -20°, +14°, -10°, +5° over 0.8s, then a red count badge pops on its corner. Add a soft ding.

**Spec (AR):** أيقونة جرس تتأرجح من فوق: +22، -20، +14، -10، +5 درجة خلال 0.8 ثانية، وبعدين شارة حمرا فيها رقم تنط على زاويتها. حط معاها صوت رنة خفيفة.

**When to use:**
- EN: Use when you need a boxed version of M-161.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-161.

#### `al-soc-162-fast` — Share Tap · Fast
**ضغطة مشاركة · سريع**

*accent · any · timeline · easing: easeOutBack · 0.6s*

*Original: M-162*

Variant of M-162: أسرع بـ 40%

**Spec (EN):** A tap indicator presses the share (paper plane) icon; the icon squashes to 80% then pops to 120% and settles, with a small burst of dots.

**Spec (AR):** مؤشر ضغطة يضغط أيقونة المشاركة (طيارة ورق)، والأيقونة تنضغط لـ 80% وبعدين تنط لـ 120% وتستقر، مع انفجار نقاط صغيرة.

**When to use:**
- EN: Use when you need a fast version of M-162.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-162.

#### `al-soc-162-slow` — Share Tap · Slow
**ضغطة مشاركة · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.6s*

*Original: M-162*

Variant of M-162: أبطأ بـ 60%

**Spec (EN):** A tap indicator presses the share (paper plane) icon; the icon squashes to 80% then pops to 120% and settles, with a small burst of dots.

**Spec (AR):** مؤشر ضغطة يضغط أيقونة المشاركة (طيارة ورق)، والأيقونة تنضغط لـ 80% وبعدين تنط لـ 120% وتستقر، مع انفجار نقاط صغيرة.

**When to use:**
- EN: Use when you need a slow version of M-162.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-162.

#### `al-soc-162-gold` — Share Tap · Gold
**ضغطة مشاركة · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.6s*

*Original: M-162*

Variant of M-162: نسخة ذهبية فاخرة

**Spec (EN):** A tap indicator presses the share (paper plane) icon; the icon squashes to 80% then pops to 120% and settles, with a small burst of dots.

**Spec (AR):** مؤشر ضغطة يضغط أيقونة المشاركة (طيارة ورق)، والأيقونة تنضغط لـ 80% وبعدين تنط لـ 120% وتستقر، مع انفجار نقاط صغيرة.

**When to use:**
- EN: Use when you need a gold version of M-162.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-162.

#### `al-soc-162-boxed` — Share Tap · Boxed
**ضغطة مشاركة · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.6s*

*Original: M-162*

Variant of M-162: النص داخل صندوق ملون

**Spec (EN):** A tap indicator presses the share (paper plane) icon; the icon squashes to 80% then pops to 120% and settles, with a small burst of dots.

**Spec (AR):** مؤشر ضغطة يضغط أيقونة المشاركة (طيارة ورق)، والأيقونة تنضغط لـ 80% وبعدين تنط لـ 120% وتستقر، مع انفجار نقاط صغيرة.

**When to use:**
- EN: Use when you need a boxed version of M-162.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-162.

#### `al-soc-163-fast` — Save Bookmark · Fast
**حفظ المنشور · سريع**

*accent · any · depth · easing: easeOutCubic · 0.5s*

*Original: M-163*

Variant of M-163: أسرع بـ 40%

**Spec (EN):** A bookmark outline icon fills up from bottom to top with white over 0.5s, then pops to 120% and settles.

**Spec (AR):** أيقونة حفظ بحدود بس تتعبى أبيض من تحت لفوق خلال 0.5 ثانية، وبعدين تنط لـ 120% وتستقر.

**When to use:**
- EN: Use when you need a fast version of M-163.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-163.

#### `al-soc-163-slow` — Save Bookmark · Slow
**حفظ المنشور · بطيء**

*accent · any · depth · easing: easeOutCubic · 0.5s*

*Original: M-163*

Variant of M-163: أبطأ بـ 60%

**Spec (EN):** A bookmark outline icon fills up from bottom to top with white over 0.5s, then pops to 120% and settles.

**Spec (AR):** أيقونة حفظ بحدود بس تتعبى أبيض من تحت لفوق خلال 0.5 ثانية، وبعدين تنط لـ 120% وتستقر.

**When to use:**
- EN: Use when you need a slow version of M-163.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-163.

#### `al-soc-163-gold` — Save Bookmark · Gold
**حفظ المنشور · ذهبي**

*accent · any · depth · easing: easeOutCubic · 0.5s*

*Original: M-163*

Variant of M-163: نسخة ذهبية فاخرة

**Spec (EN):** A bookmark outline icon fills up from bottom to top with white over 0.5s, then pops to 120% and settles.

**Spec (AR):** أيقونة حفظ بحدود بس تتعبى أبيض من تحت لفوق خلال 0.5 ثانية، وبعدين تنط لـ 120% وتستقر.

**When to use:**
- EN: Use when you need a gold version of M-163.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-163.

#### `al-soc-163-boxed` — Save Bookmark · Boxed
**حفظ المنشور · صندوق**

*accent · any · depth · easing: easeOutCubic · 0.5s*

*Original: M-163*

Variant of M-163: النص داخل صندوق ملون

**Spec (EN):** A bookmark outline icon fills up from bottom to top with white over 0.5s, then pops to 120% and settles.

**Spec (AR):** أيقونة حفظ بحدود بس تتعبى أبيض من تحت لفوق خلال 0.5 ثانية، وبعدين تنط لـ 120% وتستقر.

**When to use:**
- EN: Use when you need a boxed version of M-163.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-163.

#### `al-soc-164-fast` — Story Ring · Fast
**حلقة الستوري · سريع**

*accent · calm · depth · easing: linear · loop · 3s*

*Original: M-164*

Variant of M-164: أسرع بـ 40%

**Spec (EN):** A circular avatar sits inside a gradient ring (brand colors) that rotates one full turn every 3s, like an unseen story.

**Spec (AR):** صورة بروفايل دائرية داخل حلقة متدرجة بألوان الهوية، تلف لفة كاملة كل 3 ثواني، مثل الستوري اللي ما انشافت.

**When to use:**
- EN: Use when you need a fast version of M-164.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-164.

#### `al-soc-164-slow` — Story Ring · Slow
**حلقة الستوري · بطيء**

*accent · calm · depth · easing: linear · loop · 3s*

*Original: M-164*

Variant of M-164: أبطأ بـ 60%

**Spec (EN):** A circular avatar sits inside a gradient ring (brand colors) that rotates one full turn every 3s, like an unseen story.

**Spec (AR):** صورة بروفايل دائرية داخل حلقة متدرجة بألوان الهوية، تلف لفة كاملة كل 3 ثواني، مثل الستوري اللي ما انشافت.

**When to use:**
- EN: Use when you need a slow version of M-164.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-164.

#### `al-soc-164-gold` — Story Ring · Gold
**حلقة الستوري · ذهبي**

*accent · calm · depth · easing: linear · loop · 3s*

*Original: M-164*

Variant of M-164: نسخة ذهبية فاخرة

**Spec (EN):** A circular avatar sits inside a gradient ring (brand colors) that rotates one full turn every 3s, like an unseen story.

**Spec (AR):** صورة بروفايل دائرية داخل حلقة متدرجة بألوان الهوية، تلف لفة كاملة كل 3 ثواني، مثل الستوري اللي ما انشافت.

**When to use:**
- EN: Use when you need a gold version of M-164.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-164.

#### `al-soc-164-boxed` — Story Ring · Boxed
**حلقة الستوري · صندوق**

*accent · calm · depth · easing: linear · loop · 3s*

*Original: M-164*

Variant of M-164: النص داخل صندوق ملون

**Spec (EN):** A circular avatar sits inside a gradient ring (brand colors) that rotates one full turn every 3s, like an unseen story.

**Spec (AR):** صورة بروفايل دائرية داخل حلقة متدرجة بألوان الهوية، تلف لفة كاملة كل 3 ثواني، مثل الستوري اللي ما انشافت.

**When to use:**
- EN: Use when you need a boxed version of M-164.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-164.

#### `al-soc-165-fast` — Swipe Up Arrow · Fast
**سهم اسحب لفوق · سريع**

*accent · any · depth · easing: easeOutCubic · loop · 1.2s*

*Original: M-165*

Variant of M-165: أسرع بـ 40%

**Spec (EN):** Two stacked chevrons move up 40% and fade, repeating every 1.2s, above a short label such as "اسحب".

**Spec (AR):** سهمين فوق بعض يطلعون لفوق 40% ويختفون، ويتكررون كل 1.2 ثانية، فوق كلمة قصيرة مثل "اسحب".

**When to use:**
- EN: Use when you need a fast version of M-165.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-165.

#### `al-soc-165-slow` — Swipe Up Arrow · Slow
**سهم اسحب لفوق · بطيء**

*accent · any · depth · easing: easeOutCubic · loop · 1.2s*

*Original: M-165*

Variant of M-165: أبطأ بـ 60%

**Spec (EN):** Two stacked chevrons move up 40% and fade, repeating every 1.2s, above a short label such as "اسحب".

**Spec (AR):** سهمين فوق بعض يطلعون لفوق 40% ويختفون، ويتكررون كل 1.2 ثانية، فوق كلمة قصيرة مثل "اسحب".

**When to use:**
- EN: Use when you need a slow version of M-165.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-165.

#### `al-soc-165-gold` — Swipe Up Arrow · Gold
**سهم اسحب لفوق · ذهبي**

*accent · any · depth · easing: easeOutCubic · loop · 1.2s*

*Original: M-165*

Variant of M-165: نسخة ذهبية فاخرة

**Spec (EN):** Two stacked chevrons move up 40% and fade, repeating every 1.2s, above a short label such as "اسحب".

**Spec (AR):** سهمين فوق بعض يطلعون لفوق 40% ويختفون، ويتكررون كل 1.2 ثانية، فوق كلمة قصيرة مثل "اسحب".

**When to use:**
- EN: Use when you need a gold version of M-165.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-165.

#### `al-soc-165-boxed` — Swipe Up Arrow · Boxed
**سهم اسحب لفوق · صندوق**

*accent · any · depth · easing: easeOutCubic · loop · 1.2s*

*Original: M-165*

Variant of M-165: النص داخل صندوق ملون

**Spec (EN):** Two stacked chevrons move up 40% and fade, repeating every 1.2s, above a short label such as "اسحب".

**Spec (AR):** سهمين فوق بعض يطلعون لفوق 40% ويختفون، ويتكررون كل 1.2 ثانية، فوق كلمة قصيرة مثل "اسحب".

**When to use:**
- EN: Use when you need a boxed version of M-165.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-165.

#### `al-soc-166-fast` — Poll Sticker · Fast
**ملصق تصويت · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.8s fill*

*Original: M-166*

Variant of M-166: أسرع بـ 40%

**Spec (EN):** A light card with a question and two option rows. Accent bars fill each row to its percentage over 0.8s, with the percentages shown.

**Spec (AR):** بطاقة فاتحة فيها سؤال وخيارين. شرائط بلون الهوية تعبي كل خيار لنسبته خلال 0.8 ثانية، والنسب ظاهرة.

**When to use:**
- EN: Use when you need a fast version of M-166.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-166.

#### `al-soc-166-slow` — Poll Sticker · Slow
**ملصق تصويت · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.8s fill*

*Original: M-166*

Variant of M-166: أبطأ بـ 60%

**Spec (EN):** A light card with a question and two option rows. Accent bars fill each row to its percentage over 0.8s, with the percentages shown.

**Spec (AR):** بطاقة فاتحة فيها سؤال وخيارين. شرائط بلون الهوية تعبي كل خيار لنسبته خلال 0.8 ثانية، والنسب ظاهرة.

**When to use:**
- EN: Use when you need a slow version of M-166.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-166.

#### `al-soc-166-gold` — Poll Sticker · Gold
**ملصق تصويت · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.8s fill*

*Original: M-166*

Variant of M-166: نسخة ذهبية فاخرة

**Spec (EN):** A light card with a question and two option rows. Accent bars fill each row to its percentage over 0.8s, with the percentages shown.

**Spec (AR):** بطاقة فاتحة فيها سؤال وخيارين. شرائط بلون الهوية تعبي كل خيار لنسبته خلال 0.8 ثانية، والنسب ظاهرة.

**When to use:**
- EN: Use when you need a gold version of M-166.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-166.

#### `al-soc-166-boxed` — Poll Sticker · Boxed
**ملصق تصويت · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.8s fill*

*Original: M-166*

Variant of M-166: النص داخل صندوق ملون

**Spec (EN):** A light card with a question and two option rows. Accent bars fill each row to its percentage over 0.8s, with the percentages shown.

**Spec (AR):** بطاقة فاتحة فيها سؤال وخيارين. شرائط بلون الهوية تعبي كل خيار لنسبته خلال 0.8 ثانية، والنسب ظاهرة.

**When to use:**
- EN: Use when you need a boxed version of M-166.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-166.

#### `al-soc-167-fast` — Typing Dots · Fast
**نقاط يكتب · سريع**

*accent · calm · timeline · easing: easeInOutSine · loop · 1s*

*Original: M-167*

Variant of M-167: أسرع بـ 40%

**Spec (EN):** A chat bubble with three dots; each dot rises and brightens in turn, 0.15s apart, looping every second.

**Spec (AR):** فقاعة شات فيها ثلاث نقاط، كل نقطة تطلع وتنور بدورها وبينهم 0.15 ثانية، وتتكرر كل ثانية.

**When to use:**
- EN: Use when you need a fast version of M-167.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-167.

#### `al-soc-167-slow` — Typing Dots · Slow
**نقاط يكتب · بطيء**

*accent · calm · timeline · easing: easeInOutSine · loop · 1s*

*Original: M-167*

Variant of M-167: أبطأ بـ 60%

**Spec (EN):** A chat bubble with three dots; each dot rises and brightens in turn, 0.15s apart, looping every second.

**Spec (AR):** فقاعة شات فيها ثلاث نقاط، كل نقطة تطلع وتنور بدورها وبينهم 0.15 ثانية، وتتكرر كل ثانية.

**When to use:**
- EN: Use when you need a slow version of M-167.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-167.

#### `al-soc-167-gold` — Typing Dots · Gold
**نقاط يكتب · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · loop · 1s*

*Original: M-167*

Variant of M-167: نسخة ذهبية فاخرة

**Spec (EN):** A chat bubble with three dots; each dot rises and brightens in turn, 0.15s apart, looping every second.

**Spec (AR):** فقاعة شات فيها ثلاث نقاط، كل نقطة تطلع وتنور بدورها وبينهم 0.15 ثانية، وتتكرر كل ثانية.

**When to use:**
- EN: Use when you need a gold version of M-167.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-167.

#### `al-soc-167-boxed` — Typing Dots · Boxed
**نقاط يكتب · صندوق**

*accent · calm · timeline · easing: easeInOutSine · loop · 1s*

*Original: M-167*

Variant of M-167: النص داخل صندوق ملون

**Spec (EN):** A chat bubble with three dots; each dot rises and brightens in turn, 0.15s apart, looping every second.

**Spec (AR):** فقاعة شات فيها ثلاث نقاط، كل نقطة تطلع وتنور بدورها وبينهم 0.15 ثانية، وتتكرر كل ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-167.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-167.

#### `al-soc-168-fast` — Chat Bubbles · Fast
**فقاعات محادثة · سريع**

*accent · any · timeline · easing: easeOutBack · 0.25s per bubble*

*Original: M-168*

Variant of M-168: أسرع بـ 40%

**Spec (EN):** Message bubbles pop in one at a time from their tail corner (scale 0 to 105% to 100% over 0.25s), alternating sides like a real chat.

**Spec (AR):** فقاعات الرسائل تنط وحدة وحدة من زاوية ذيلها (من 0 لـ 105% لـ 100% خلال 0.25 ثانية)، يمين ويسار بالتناوب مثل المحادثة الحقيقية.

**When to use:**
- EN: Use when you need a fast version of M-168.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-168.

#### `al-soc-168-slow` — Chat Bubbles · Slow
**فقاعات محادثة · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.25s per bubble*

*Original: M-168*

Variant of M-168: أبطأ بـ 60%

**Spec (EN):** Message bubbles pop in one at a time from their tail corner (scale 0 to 105% to 100% over 0.25s), alternating sides like a real chat.

**Spec (AR):** فقاعات الرسائل تنط وحدة وحدة من زاوية ذيلها (من 0 لـ 105% لـ 100% خلال 0.25 ثانية)، يمين ويسار بالتناوب مثل المحادثة الحقيقية.

**When to use:**
- EN: Use when you need a slow version of M-168.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-168.

#### `al-soc-168-gold` — Chat Bubbles · Gold
**فقاعات محادثة · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.25s per bubble*

*Original: M-168*

Variant of M-168: نسخة ذهبية فاخرة

**Spec (EN):** Message bubbles pop in one at a time from their tail corner (scale 0 to 105% to 100% over 0.25s), alternating sides like a real chat.

**Spec (AR):** فقاعات الرسائل تنط وحدة وحدة من زاوية ذيلها (من 0 لـ 105% لـ 100% خلال 0.25 ثانية)، يمين ويسار بالتناوب مثل المحادثة الحقيقية.

**When to use:**
- EN: Use when you need a gold version of M-168.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-168.

#### `al-soc-168-boxed` — Chat Bubbles · Boxed
**فقاعات محادثة · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.25s per bubble*

*Original: M-168*

Variant of M-168: النص داخل صندوق ملون

**Spec (EN):** Message bubbles pop in one at a time from their tail corner (scale 0 to 105% to 100% over 0.25s), alternating sides like a real chat.

**Spec (AR):** فقاعات الرسائل تنط وحدة وحدة من زاوية ذيلها (من 0 لـ 105% لـ 100% خلال 0.25 ثانية)، يمين ويسار بالتناوب مثل المحادثة الحقيقية.

**When to use:**
- EN: Use when you need a boxed version of M-168.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-168.

#### `al-soc-169-fast` — Floating Hearts · Fast
**قلوب تطير · سريع**

*accent · any · depth · easing: easeOut · loop*

*Original: M-169*

Variant of M-169: أسرع بـ 40%

**Spec (EN):** Small hearts spawn near the bottom corner every 0.2–0.4s and float up about 90% of the frame with a gentle sideways sway, growing slightly and fading.

**Spec (AR):** قلوب صغيرة تطلع قرب الزاوية التحت كل 0.2 إلى 0.4 ثانية، وتطير لفوق تقريباً 90% من الشاشة مع تمايل خفيف على الجنب، تكبر شوي وتختفي.

**When to use:**
- EN: Use when you need a fast version of M-169.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-169.

#### `al-soc-169-slow` — Floating Hearts · Slow
**قلوب تطير · بطيء**

*accent · any · depth · easing: easeOut · loop*

*Original: M-169*

Variant of M-169: أبطأ بـ 60%

**Spec (EN):** Small hearts spawn near the bottom corner every 0.2–0.4s and float up about 90% of the frame with a gentle sideways sway, growing slightly and fading.

**Spec (AR):** قلوب صغيرة تطلع قرب الزاوية التحت كل 0.2 إلى 0.4 ثانية، وتطير لفوق تقريباً 90% من الشاشة مع تمايل خفيف على الجنب، تكبر شوي وتختفي.

**When to use:**
- EN: Use when you need a slow version of M-169.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-169.

#### `al-soc-169-gold` — Floating Hearts · Gold
**قلوب تطير · ذهبي**

*accent · any · depth · easing: easeOut · loop*

*Original: M-169*

Variant of M-169: نسخة ذهبية فاخرة

**Spec (EN):** Small hearts spawn near the bottom corner every 0.2–0.4s and float up about 90% of the frame with a gentle sideways sway, growing slightly and fading.

**Spec (AR):** قلوب صغيرة تطلع قرب الزاوية التحت كل 0.2 إلى 0.4 ثانية، وتطير لفوق تقريباً 90% من الشاشة مع تمايل خفيف على الجنب، تكبر شوي وتختفي.

**When to use:**
- EN: Use when you need a gold version of M-169.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-169.

#### `al-soc-169-boxed` — Floating Hearts · Boxed
**قلوب تطير · صندوق**

*accent · any · depth · easing: easeOut · loop*

*Original: M-169*

Variant of M-169: النص داخل صندوق ملون

**Spec (EN):** Small hearts spawn near the bottom corner every 0.2–0.4s and float up about 90% of the frame with a gentle sideways sway, growing slightly and fading.

**Spec (AR):** قلوب صغيرة تطلع قرب الزاوية التحت كل 0.2 إلى 0.4 ثانية، وتطير لفوق تقريباً 90% من الشاشة مع تمايل خفيف على الجنب، تكبر شوي وتختفي.

**When to use:**
- EN: Use when you need a boxed version of M-169.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-169.

#### `al-soc-170-fast` — View Counter · Fast
**عداد مشاهدات · سريع**

*accent · any · timeline · easing: easeOutExpo · 1.2s count*

*Original: M-170*

Variant of M-170: أسرع بـ 40%

**Spec (EN):** An eye icon with a number counting up from 0 to the target (see M-040), in tabular mono digits.

**Spec (AR):** أيقونة عين مع رقم يعد من 0 لين الرقم المطلوب (شوف M-040)، بأرقام mono متساوية العرض.

**When to use:**
- EN: Use when you need a fast version of M-170.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-170.

#### `al-soc-170-slow` — View Counter · Slow
**عداد مشاهدات · بطيء**

*accent · any · timeline · easing: easeOutExpo · 1.2s count*

*Original: M-170*

Variant of M-170: أبطأ بـ 60%

**Spec (EN):** An eye icon with a number counting up from 0 to the target (see M-040), in tabular mono digits.

**Spec (AR):** أيقونة عين مع رقم يعد من 0 لين الرقم المطلوب (شوف M-040)، بأرقام mono متساوية العرض.

**When to use:**
- EN: Use when you need a slow version of M-170.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-170.

#### `al-soc-170-gold` — View Counter · Gold
**عداد مشاهدات · ذهبي**

*accent · any · timeline · easing: easeOutExpo · 1.2s count*

*Original: M-170*

Variant of M-170: نسخة ذهبية فاخرة

**Spec (EN):** An eye icon with a number counting up from 0 to the target (see M-040), in tabular mono digits.

**Spec (AR):** أيقونة عين مع رقم يعد من 0 لين الرقم المطلوب (شوف M-040)، بأرقام mono متساوية العرض.

**When to use:**
- EN: Use when you need a gold version of M-170.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-170.

#### `al-soc-170-boxed` — View Counter · Boxed
**عداد مشاهدات · صندوق**

*accent · any · timeline · easing: easeOutExpo · 1.2s count*

*Original: M-170*

Variant of M-170: النص داخل صندوق ملون

**Spec (EN):** An eye icon with a number counting up from 0 to the target (see M-040), in tabular mono digits.

**Spec (AR):** أيقونة عين مع رقم يعد من 0 لين الرقم المطلوب (شوف M-040)، بأرقام mono متساوية العرض.

**When to use:**
- EN: Use when you need a boxed version of M-170.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-170.

#### `al-soc-171-fast` — Profile Card · Fast
**بطاقة بروفايل · سريع**

*accent · any · timeline · easing: spring · 0.5s in*

*Original: M-171*

Variant of M-171: أسرع بـ 40%

**Spec (EN):** A light rounded card with avatar, name, handle and a follow button slides up from below the frame with a spring and a 4% overshoot, holds, then slides back.

**Spec (AR):** بطاقة فاتحة بزوايا دائرية فيها الصورة والاسم واليوزر وزر متابعة، تطلع من تحت الشاشة بحركة نابض وتتعدى 4%، تثبت، وبعدين ترجع.

**When to use:**
- EN: Use when you need a fast version of M-171.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-171.

#### `al-soc-171-slow` — Profile Card · Slow
**بطاقة بروفايل · بطيء**

*accent · any · timeline · easing: spring · 0.5s in*

*Original: M-171*

Variant of M-171: أبطأ بـ 60%

**Spec (EN):** A light rounded card with avatar, name, handle and a follow button slides up from below the frame with a spring and a 4% overshoot, holds, then slides back.

**Spec (AR):** بطاقة فاتحة بزوايا دائرية فيها الصورة والاسم واليوزر وزر متابعة، تطلع من تحت الشاشة بحركة نابض وتتعدى 4%، تثبت، وبعدين ترجع.

**When to use:**
- EN: Use when you need a slow version of M-171.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-171.

#### `al-soc-171-gold` — Profile Card · Gold
**بطاقة بروفايل · ذهبي**

*accent · any · timeline · easing: spring · 0.5s in*

*Original: M-171*

Variant of M-171: نسخة ذهبية فاخرة

**Spec (EN):** A light rounded card with avatar, name, handle and a follow button slides up from below the frame with a spring and a 4% overshoot, holds, then slides back.

**Spec (AR):** بطاقة فاتحة بزوايا دائرية فيها الصورة والاسم واليوزر وزر متابعة، تطلع من تحت الشاشة بحركة نابض وتتعدى 4%، تثبت، وبعدين ترجع.

**When to use:**
- EN: Use when you need a gold version of M-171.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-171.

#### `al-soc-171-boxed` — Profile Card · Boxed
**بطاقة بروفايل · صندوق**

*accent · any · timeline · easing: spring · 0.5s in*

*Original: M-171*

Variant of M-171: النص داخل صندوق ملون

**Spec (EN):** A light rounded card with avatar, name, handle and a follow button slides up from below the frame with a spring and a 4% overshoot, holds, then slides back.

**Spec (AR):** بطاقة فاتحة بزوايا دائرية فيها الصورة والاسم واليوزر وزر متابعة، تطلع من تحت الشاشة بحركة نابض وتتعدى 4%، تثبت، وبعدين ترجع.

**When to use:**
- EN: Use when you need a boxed version of M-171.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-171.

#### `al-soc-172-fast` — Link Sticker · Fast
**ملصق رابط · سريع**

*accent · any · timeline · easing: easeOutBack · 0.4s + wiggle*

*Original: M-172*

Variant of M-172: أسرع بـ 40%

**Spec (EN):** A white pill sticker with a link icon and the URL pops in (0.4s), then wiggles gently every couple of seconds to invite a tap.

**Spec (AR):** ملصق أبيض على شكل كبسولة فيه أيقونة رابط والرابط، ينط (0.4 ثانية)، وبعدين يتمايل بخفة كل كم ثانية عشان يشجع على الضغط.

**When to use:**
- EN: Use when you need a fast version of M-172.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-172.

#### `al-soc-172-slow` — Link Sticker · Slow
**ملصق رابط · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.4s + wiggle*

*Original: M-172*

Variant of M-172: أبطأ بـ 60%

**Spec (EN):** A white pill sticker with a link icon and the URL pops in (0.4s), then wiggles gently every couple of seconds to invite a tap.

**Spec (AR):** ملصق أبيض على شكل كبسولة فيه أيقونة رابط والرابط، ينط (0.4 ثانية)، وبعدين يتمايل بخفة كل كم ثانية عشان يشجع على الضغط.

**When to use:**
- EN: Use when you need a slow version of M-172.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-172.

#### `al-soc-172-gold` — Link Sticker · Gold
**ملصق رابط · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.4s + wiggle*

*Original: M-172*

Variant of M-172: نسخة ذهبية فاخرة

**Spec (EN):** A white pill sticker with a link icon and the URL pops in (0.4s), then wiggles gently every couple of seconds to invite a tap.

**Spec (AR):** ملصق أبيض على شكل كبسولة فيه أيقونة رابط والرابط، ينط (0.4 ثانية)، وبعدين يتمايل بخفة كل كم ثانية عشان يشجع على الضغط.

**When to use:**
- EN: Use when you need a gold version of M-172.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-172.

#### `al-soc-172-boxed` — Link Sticker · Boxed
**ملصق رابط · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.4s + wiggle*

*Original: M-172*

Variant of M-172: النص داخل صندوق ملون

**Spec (EN):** A white pill sticker with a link icon and the URL pops in (0.4s), then wiggles gently every couple of seconds to invite a tap.

**Spec (AR):** ملصق أبيض على شكل كبسولة فيه أيقونة رابط والرابط، ينط (0.4 ثانية)، وبعدين يتمايل بخفة كل كم ثانية عشان يشجع على الضغط.

**When to use:**
- EN: Use when you need a boxed version of M-172.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-172.

#### `al-soc-173-fast` — Countdown · Fast
**عد تنازلي · سريع**

*accent · any · timeline · easing: easeOutBack · 1s per number*

*Original: M-173*

Variant of M-173: أسرع بـ 40%

**Spec (EN):** Big mono digits 3, 2, 1 replace each other every second, each popping from 60% to 110% to 100% and fading out. Add a tick sound per number.

**Spec (AR):** أرقام mono كبيرة 3 و2 و1 تتبدل كل ثانية، كل رقم ينط من 60% لـ 110% لـ 100% ويختفي. حط صوت تكة مع كل رقم.

**When to use:**
- EN: Use when you need a fast version of M-173.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-173.

#### `al-soc-173-slow` — Countdown · Slow
**عد تنازلي · بطيء**

*accent · any · timeline · easing: easeOutBack · 1s per number*

*Original: M-173*

Variant of M-173: أبطأ بـ 60%

**Spec (EN):** Big mono digits 3, 2, 1 replace each other every second, each popping from 60% to 110% to 100% and fading out. Add a tick sound per number.

**Spec (AR):** أرقام mono كبيرة 3 و2 و1 تتبدل كل ثانية، كل رقم ينط من 60% لـ 110% لـ 100% ويختفي. حط صوت تكة مع كل رقم.

**When to use:**
- EN: Use when you need a slow version of M-173.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-173.

#### `al-soc-173-gold` — Countdown · Gold
**عد تنازلي · ذهبي**

*accent · any · timeline · easing: easeOutBack · 1s per number*

*Original: M-173*

Variant of M-173: نسخة ذهبية فاخرة

**Spec (EN):** Big mono digits 3, 2, 1 replace each other every second, each popping from 60% to 110% to 100% and fading out. Add a tick sound per number.

**Spec (AR):** أرقام mono كبيرة 3 و2 و1 تتبدل كل ثانية، كل رقم ينط من 60% لـ 110% لـ 100% ويختفي. حط صوت تكة مع كل رقم.

**When to use:**
- EN: Use when you need a gold version of M-173.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-173.

#### `al-soc-173-boxed` — Countdown · Boxed
**عد تنازلي · صندوق**

*accent · any · timeline · easing: easeOutBack · 1s per number*

*Original: M-173*

Variant of M-173: النص داخل صندوق ملون

**Spec (EN):** Big mono digits 3, 2, 1 replace each other every second, each popping from 60% to 110% to 100% and fading out. Add a tick sound per number.

**Spec (AR):** أرقام mono كبيرة 3 و2 و1 تتبدل كل ثانية، كل رقم ينط من 60% لـ 110% لـ 100% ويختفي. حط صوت تكة مع كل رقم.

**When to use:**
- EN: Use when you need a boxed version of M-173.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-173.

#### `al-soc-174-fast` — Question Sticker · Fast
**ملصق سؤال · سريع**

*accent · any · timeline · easing: easeOutBack · 0.4s in*

*Original: M-174*

Variant of M-174: أسرع بـ 40%

**Spec (EN):** A light card with an accent header "اسألني سؤال" and a text field pops in, then a short question types into the field.

**Spec (AR):** بطاقة فاتحة فوقها عنوان بلون الهوية "اسألني سؤال" وتحته خانة كتابة، تنط، وبعدين سؤال قصير ينكتب في الخانة.

**When to use:**
- EN: Use when you need a fast version of M-174.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-174.

#### `al-soc-174-slow` — Question Sticker · Slow
**ملصق سؤال · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.4s in*

*Original: M-174*

Variant of M-174: أبطأ بـ 60%

**Spec (EN):** A light card with an accent header "اسألني سؤال" and a text field pops in, then a short question types into the field.

**Spec (AR):** بطاقة فاتحة فوقها عنوان بلون الهوية "اسألني سؤال" وتحته خانة كتابة، تنط، وبعدين سؤال قصير ينكتب في الخانة.

**When to use:**
- EN: Use when you need a slow version of M-174.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-174.

#### `al-soc-174-gold` — Question Sticker · Gold
**ملصق سؤال · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.4s in*

*Original: M-174*

Variant of M-174: نسخة ذهبية فاخرة

**Spec (EN):** A light card with an accent header "اسألني سؤال" and a text field pops in, then a short question types into the field.

**Spec (AR):** بطاقة فاتحة فوقها عنوان بلون الهوية "اسألني سؤال" وتحته خانة كتابة، تنط، وبعدين سؤال قصير ينكتب في الخانة.

**When to use:**
- EN: Use when you need a gold version of M-174.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-174.

#### `al-soc-174-boxed` — Question Sticker · Boxed
**ملصق سؤال · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.4s in*

*Original: M-174*

Variant of M-174: النص داخل صندوق ملون

**Spec (EN):** A light card with an accent header "اسألني سؤال" and a text field pops in, then a short question types into the field.

**Spec (AR):** بطاقة فاتحة فوقها عنوان بلون الهوية "اسألني سؤال" وتحته خانة كتابة، تنط، وبعدين سؤال قصير ينكتب في الخانة.

**When to use:**
- EN: Use when you need a boxed version of M-174.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-174.

#### `al-soc-175-fast` — Mention Tag · Fast
**تاق منشن · سريع**

*accent · any · timeline · easing: easeOutBack · 0.3s*

*Original: M-175*

Variant of M-175: أسرع بـ 40%

**Spec (EN):** A dark rounded tag with a small pointer and the @handle pops from the tagged point (scale 0 to 110% to 100% over 0.3s).

**Spec (AR):** تاق غامق بزوايا دائرية مع سهم صغير واليوزر، ينط من النقطة المحددة (من 0 لـ 110% لـ 100% خلال 0.3 ثانية).

**When to use:**
- EN: Use when you need a fast version of M-175.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-175.

#### `al-soc-175-slow` — Mention Tag · Slow
**تاق منشن · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.3s*

*Original: M-175*

Variant of M-175: أبطأ بـ 60%

**Spec (EN):** A dark rounded tag with a small pointer and the @handle pops from the tagged point (scale 0 to 110% to 100% over 0.3s).

**Spec (AR):** تاق غامق بزوايا دائرية مع سهم صغير واليوزر، ينط من النقطة المحددة (من 0 لـ 110% لـ 100% خلال 0.3 ثانية).

**When to use:**
- EN: Use when you need a slow version of M-175.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-175.

#### `al-soc-175-gold` — Mention Tag · Gold
**تاق منشن · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.3s*

*Original: M-175*

Variant of M-175: نسخة ذهبية فاخرة

**Spec (EN):** A dark rounded tag with a small pointer and the @handle pops from the tagged point (scale 0 to 110% to 100% over 0.3s).

**Spec (AR):** تاق غامق بزوايا دائرية مع سهم صغير واليوزر، ينط من النقطة المحددة (من 0 لـ 110% لـ 100% خلال 0.3 ثانية).

**When to use:**
- EN: Use when you need a gold version of M-175.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-175.

#### `al-soc-175-boxed` — Mention Tag · Boxed
**تاق منشن · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.3s*

*Original: M-175*

Variant of M-175: النص داخل صندوق ملون

**Spec (EN):** A dark rounded tag with a small pointer and the @handle pops from the tagged point (scale 0 to 110% to 100% over 0.3s).

**Spec (AR):** تاق غامق بزوايا دائرية مع سهم صغير واليوزر، ينط من النقطة المحددة (من 0 لـ 110% لـ 100% خلال 0.3 ثانية).

**When to use:**
- EN: Use when you need a boxed version of M-175.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-175.

#### `al-soc-176-fast` — Verified Badge · Fast
**علامة التوثيق · سريع**

*accent · any · depth · easing: easeOutBack · 0.4s*

*Original: M-176*

Variant of M-176: أسرع بـ 40%

**Spec (EN):** A blue circular check badge spins in from -180° and 0 scale to a 130% pop and settles next to the name over 0.4s.

**Spec (AR):** علامة توثيق زرقا دائرية تدخل وهي تلف من -180 درجة وحجم 0، تنط لـ 130% وتستقر جنب الاسم خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-176.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-176.

#### `al-soc-176-slow` — Verified Badge · Slow
**علامة التوثيق · بطيء**

*accent · any · depth · easing: easeOutBack · 0.4s*

*Original: M-176*

Variant of M-176: أبطأ بـ 60%

**Spec (EN):** A blue circular check badge spins in from -180° and 0 scale to a 130% pop and settles next to the name over 0.4s.

**Spec (AR):** علامة توثيق زرقا دائرية تدخل وهي تلف من -180 درجة وحجم 0، تنط لـ 130% وتستقر جنب الاسم خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-176.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-176.

#### `al-soc-176-gold` — Verified Badge · Gold
**علامة التوثيق · ذهبي**

*accent · any · depth · easing: easeOutBack · 0.4s*

*Original: M-176*

Variant of M-176: نسخة ذهبية فاخرة

**Spec (EN):** A blue circular check badge spins in from -180° and 0 scale to a 130% pop and settles next to the name over 0.4s.

**Spec (AR):** علامة توثيق زرقا دائرية تدخل وهي تلف من -180 درجة وحجم 0، تنط لـ 130% وتستقر جنب الاسم خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-176.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-176.

#### `al-soc-176-boxed` — Verified Badge · Boxed
**علامة التوثيق · صندوق**

*accent · any · depth · easing: easeOutBack · 0.4s*

*Original: M-176*

Variant of M-176: النص داخل صندوق ملون

**Spec (EN):** A blue circular check badge spins in from -180° and 0 scale to a 130% pop and settles next to the name over 0.4s.

**Spec (AR):** علامة توثيق زرقا دائرية تدخل وهي تلف من -180 درجة وحجم 0، تنط لـ 130% وتستقر جنب الاسم خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-176.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-176.

#### `al-soc-177-fast` — Comment Stack · Fast
**تعليقات تتكدس · سريع**

*accent · any · depth · easing: easeOutCubic · 0.3s per comment*

*Original: M-177*

Variant of M-177: أسرع بـ 40%

**Spec (EN):** Comment rows (avatar dot + short text) slide up and fade in one by one, 0.5s apart, stacking into a list.

**Spec (AR):** صفوف تعليقات (نقطة صورة ونص قصير) تطلع لفوق وتظهر وحدة وحدة وبينهم 0.5 ثانية، وتتكدس في قائمة.

**When to use:**
- EN: Use when you need a fast version of M-177.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-177.

#### `al-soc-177-slow` — Comment Stack · Slow
**تعليقات تتكدس · بطيء**

*accent · any · depth · easing: easeOutCubic · 0.3s per comment*

*Original: M-177*

Variant of M-177: أبطأ بـ 60%

**Spec (EN):** Comment rows (avatar dot + short text) slide up and fade in one by one, 0.5s apart, stacking into a list.

**Spec (AR):** صفوف تعليقات (نقطة صورة ونص قصير) تطلع لفوق وتظهر وحدة وحدة وبينهم 0.5 ثانية، وتتكدس في قائمة.

**When to use:**
- EN: Use when you need a slow version of M-177.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-177.

#### `al-soc-177-gold` — Comment Stack · Gold
**تعليقات تتكدس · ذهبي**

*accent · any · depth · easing: easeOutCubic · 0.3s per comment*

*Original: M-177*

Variant of M-177: نسخة ذهبية فاخرة

**Spec (EN):** Comment rows (avatar dot + short text) slide up and fade in one by one, 0.5s apart, stacking into a list.

**Spec (AR):** صفوف تعليقات (نقطة صورة ونص قصير) تطلع لفوق وتظهر وحدة وحدة وبينهم 0.5 ثانية، وتتكدس في قائمة.

**When to use:**
- EN: Use when you need a gold version of M-177.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-177.

#### `al-soc-177-boxed` — Comment Stack · Boxed
**تعليقات تتكدس · صندوق**

*accent · any · depth · easing: easeOutCubic · 0.3s per comment*

*Original: M-177*

Variant of M-177: النص داخل صندوق ملون

**Spec (EN):** Comment rows (avatar dot + short text) slide up and fade in one by one, 0.5s apart, stacking into a list.

**Spec (AR):** صفوف تعليقات (نقطة صورة ونص قصير) تطلع لفوق وتظهر وحدة وحدة وبينهم 0.5 ثانية، وتتكدس في قائمة.

**When to use:**
- EN: Use when you need a boxed version of M-177.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-177.

#### `al-soc-178-fast` — Notification Badge · Fast
**شارة رقم · سريع**

*accent · any · depth · easing: easeOutBack · 0.3s*

*Original: M-178*

Variant of M-178: أسرع بـ 40%

**Spec (EN):** A red rounded badge with a number pops onto the top corner of an icon (0 to 130% to 100% over 0.3s), then the icon gives a small pop.

**Spec (AR):** شارة حمرا بزوايا دائرية فيها رقم تنط على زاوية الأيقونة الفوق (من 0 لـ 130% لـ 100% خلال 0.3 ثانية)، وبعدين الأيقونة تنط نطة صغيرة.

**When to use:**
- EN: Use when you need a fast version of M-178.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-178.

#### `al-soc-178-slow` — Notification Badge · Slow
**شارة رقم · بطيء**

*accent · any · depth · easing: easeOutBack · 0.3s*

*Original: M-178*

Variant of M-178: أبطأ بـ 60%

**Spec (EN):** A red rounded badge with a number pops onto the top corner of an icon (0 to 130% to 100% over 0.3s), then the icon gives a small pop.

**Spec (AR):** شارة حمرا بزوايا دائرية فيها رقم تنط على زاوية الأيقونة الفوق (من 0 لـ 130% لـ 100% خلال 0.3 ثانية)، وبعدين الأيقونة تنط نطة صغيرة.

**When to use:**
- EN: Use when you need a slow version of M-178.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-178.

#### `al-soc-178-gold` — Notification Badge · Gold
**شارة رقم · ذهبي**

*accent · any · depth · easing: easeOutBack · 0.3s*

*Original: M-178*

Variant of M-178: نسخة ذهبية فاخرة

**Spec (EN):** A red rounded badge with a number pops onto the top corner of an icon (0 to 130% to 100% over 0.3s), then the icon gives a small pop.

**Spec (AR):** شارة حمرا بزوايا دائرية فيها رقم تنط على زاوية الأيقونة الفوق (من 0 لـ 130% لـ 100% خلال 0.3 ثانية)، وبعدين الأيقونة تنط نطة صغيرة.

**When to use:**
- EN: Use when you need a gold version of M-178.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-178.

#### `al-soc-178-boxed` — Notification Badge · Boxed
**شارة رقم · صندوق**

*accent · any · depth · easing: easeOutBack · 0.3s*

*Original: M-178*

Variant of M-178: النص داخل صندوق ملون

**Spec (EN):** A red rounded badge with a number pops onto the top corner of an icon (0 to 130% to 100% over 0.3s), then the icon gives a small pop.

**Spec (AR):** شارة حمرا بزوايا دائرية فيها رقم تنط على زاوية الأيقونة الفوق (من 0 لـ 130% لـ 100% خلال 0.3 ثانية)، وبعدين الأيقونة تنط نطة صغيرة.

**When to use:**
- EN: Use when you need a boxed version of M-178.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-178.

#### `al-soc-179-fast` — Sound On · Fast
**شغّل الصوت · سريع**

*accent · calm · timeline · easing: easeInOutSine · loop · 1.2s*

*Original: M-179*

Variant of M-179: أسرع بـ 40%

**Spec (EN):** A speaker icon with three sound waves that light up one after another, 0.2s apart, looping every 1.2s.

**Spec (AR):** أيقونة سماعة مع ثلاث موجات صوت تنور وحدة ورا الثانية وبينهم 0.2 ثانية، وتتكرر كل 1.2 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-179.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-179.

#### `al-soc-179-slow` — Sound On · Slow
**شغّل الصوت · بطيء**

*accent · calm · timeline · easing: easeInOutSine · loop · 1.2s*

*Original: M-179*

Variant of M-179: أبطأ بـ 60%

**Spec (EN):** A speaker icon with three sound waves that light up one after another, 0.2s apart, looping every 1.2s.

**Spec (AR):** أيقونة سماعة مع ثلاث موجات صوت تنور وحدة ورا الثانية وبينهم 0.2 ثانية، وتتكرر كل 1.2 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-179.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-179.

#### `al-soc-179-gold` — Sound On · Gold
**شغّل الصوت · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · loop · 1.2s*

*Original: M-179*

Variant of M-179: نسخة ذهبية فاخرة

**Spec (EN):** A speaker icon with three sound waves that light up one after another, 0.2s apart, looping every 1.2s.

**Spec (AR):** أيقونة سماعة مع ثلاث موجات صوت تنور وحدة ورا الثانية وبينهم 0.2 ثانية، وتتكرر كل 1.2 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-179.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-179.

#### `al-soc-179-boxed` — Sound On · Boxed
**شغّل الصوت · صندوق**

*accent · calm · timeline · easing: easeInOutSine · loop · 1.2s*

*Original: M-179*

Variant of M-179: النص داخل صندوق ملون

**Spec (EN):** A speaker icon with three sound waves that light up one after another, 0.2s apart, looping every 1.2s.

**Spec (AR):** أيقونة سماعة مع ثلاث موجات صوت تنور وحدة ورا الثانية وبينهم 0.2 ثانية، وتتكرر كل 1.2 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-179.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-179.

#### `al-soc-180-fast` — Search Typing · Fast
**بحث ينكتب · سريع**

*accent · any · timeline · easing: steps · 1.2s typing*

*Original: M-180*

Variant of M-180: أسرع بـ 40%

**Spec (EN):** A light rounded search bar with a magnifier icon; the query types in letter by letter from the reading-start side.

**Spec (AR):** شريط بحث فاتح بزوايا دائرية فيه أيقونة عدسة، والكلام ينكتب فيه حرف حرف من جهة بداية القراءة.

**When to use:**
- EN: Use when you need a fast version of M-180.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-180.

#### `al-soc-180-slow` — Search Typing · Slow
**بحث ينكتب · بطيء**

*accent · any · timeline · easing: steps · 1.2s typing*

*Original: M-180*

Variant of M-180: أبطأ بـ 60%

**Spec (EN):** A light rounded search bar with a magnifier icon; the query types in letter by letter from the reading-start side.

**Spec (AR):** شريط بحث فاتح بزوايا دائرية فيه أيقونة عدسة، والكلام ينكتب فيه حرف حرف من جهة بداية القراءة.

**When to use:**
- EN: Use when you need a slow version of M-180.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-180.

#### `al-soc-180-gold` — Search Typing · Gold
**بحث ينكتب · ذهبي**

*accent · any · timeline · easing: steps · 1.2s typing*

*Original: M-180*

Variant of M-180: نسخة ذهبية فاخرة

**Spec (EN):** A light rounded search bar with a magnifier icon; the query types in letter by letter from the reading-start side.

**Spec (AR):** شريط بحث فاتح بزوايا دائرية فيه أيقونة عدسة، والكلام ينكتب فيه حرف حرف من جهة بداية القراءة.

**When to use:**
- EN: Use when you need a gold version of M-180.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-180.

#### `al-soc-180-boxed` — Search Typing · Boxed
**بحث ينكتب · صندوق**

*accent · any · timeline · easing: steps · 1.2s typing*

*Original: M-180*

Variant of M-180: النص داخل صندوق ملون

**Spec (EN):** A light rounded search bar with a magnifier icon; the query types in letter by letter from the reading-start side.

**Spec (AR):** شريط بحث فاتح بزوايا دائرية فيه أيقونة عدسة، والكلام ينكتب فيه حرف حرف من جهة بداية القراءة.

**When to use:**
- EN: Use when you need a boxed version of M-180.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-180.

### Logos & Titles (الشعارات والعناوين) — 125 motions

#### `al-lgo-036` — Logo Float
**شعار يطفو**

*workhorse · calm · depth · easing: easeInOutSine · loop · 3s*

*Original: M-036*

A logo floating gently behind you.

**Spec (EN):** The logo hovers behind the person (background layer, under the person matte) with a gentle ±9% vertical bob on a 3s sine loop and a soft glow.

**Spec (AR):** الشعار يطفو ورا الشخص (طبقة الخلفية تحت قناع الشخص) بحركة خفيفة لفوق وتحت ±9% كل 3 ثواني (sine) مع توهج ناعم.

**When to use:**
- EN: A logo floating gently behind you.
- AR: شعار ورا جسمك يتحرك بهدوء.

#### `al-lgo-037` — Logo Spin-In
**شعار يدور ويدخل**

*workhorse · high · depth · easing: easeOutBack · 0.7s*

*Original: M-037*

Opening or closing a video.

**Spec (EN):** The logo spins in from -220° and scale 0 to 0° and 112%, then settles at 100% over 0.7s total. Exit: shrink to 0 with a 90° turn.

**Spec (AR):** الشعار يدخل وهو يدور من -220 درجة وحجم 0 لين 0 درجة و112%، وبعدين يستقر على 100%، والمجموع 0.7 ثانية. وبالخروج يصغر لـ 0 مع لفة 90 درجة.

**When to use:**
- EN: Opening or closing a video.
- AR: بداية أو نهاية الفيديو.

#### `al-lgo-038` — Title Card Drop
**بطاقة عنوان تنزل**

*workhorse · any · depth · easing: spring · 0.55s in*

*Original: M-038*

The tool or topic name, like a "Claude Opus 5.5" card.

**Spec (EN):** A dark rounded card with an accent border, an icon on one side and a two-line title (bold mono title plus an accent subtitle) drops from above the frame with a spring and about a 10% overshoot. Holds, then slides back up.

**Spec (AR):** بطاقة غامقة بزوايا دائرية وإطار بلون الهوية، فيها أيقونة على جنب وعنوان بسطرين (عنوان عريض mono وتحته عنوان فرعي بلون الهوية)، تنزل من فوق الشاشة بحركة نابض وتتعدى تقريباً 10%. تثبت، وبعدين ترجع لفوق.

**When to use:**
- EN: The tool or topic name, like a "Claude Opus 5.5" card.
- AR: اسم الأداة أو الموضوع، مثل بطاقة "Claude Opus 5.5".

#### `al-lgo-039` — Lower Third
**شريط الاسم السفلي**

*workhorse · any · timeline · easing: easeOutExpo · 0.4s bar · 0.3s text*

*Original: M-039*

Introduce your name or handle.

**Spec (EN):** An accent bar grows in from the right edge (0.4s), then the name and the subtitle slide in 12% and fade in inside it (0.3s, 0.08s stagger). Holds, then the text fades and the bar retracts.

**Spec (AR):** شريط بلون الهوية يطلع من الحافة اليمين (0.4 ثانية)، وبعدين الاسم والسطر اللي تحته يدخلون بإزاحة 12% ويظهرون داخل الشريط (0.3 ثانية، وبينهم 0.08 ثانية). يثبت، وبعدين النص يختفي والشريط ينسحب.

**When to use:**
- EN: Introduce your name or handle.
- AR: تعريف باسمك أو حسابك.

#### `al-lgo-040` — Number Counter
**عداد أرقام**

*workhorse · any · depth · easing: easeOutExpo · 1.2s count*

*Original: M-040*

A stat or big number counting up.

**Spec (EN):** A number counts up from 0 to the target value over 1.2s (easeOutExpo, fast at first, then slowing), in tabular monospaced digits with an accent color, and a label beneath. Optionally scale-punch the final value (M-008).

**Spec (AR):** رقم يعد من 0 لين الرقم المطلوب خلال 1.2 ثانية (easeOutExpo: سريع بالبداية وبعدين يبطّي)، بأرقام mono متساوية العرض وبلون الهوية، وتحته وصف. وتقدر تحط على الرقم الأخير ضربة تكبير (M-008).

**When to use:**
- EN: A stat or big number counting up.
- AR: إحصائية أو رقم كبير يعد قدامك.

#### `al-lgo-181` — Logo Mask Reveal
**شعار ينكشف من قناع**

*workhorse · any · timeline · easing: easeInOutQuart · 0.6s*

*Original: M-181*

A logo rises from behind an invisible line, premium style.

**Spec (EN):** The logo sits inside a box with hidden overflow and slides up from below its edge into place over 0.6s (see M-004).

**Spec (AR):** الشعار داخل صندوق مخفي الأطراف، ويطلع من تحت حافته لمكانه خلال 0.6 ثانية (شوف M-004).

**When to use:**
- EN: A logo rises from behind an invisible line, premium style.
- AR: شعار يطلع من تحت خط مثل العناوين الفخمة.

#### `al-lgo-182` — Logo Stroke Draw
**رسم حدود الشعار**

*workhorse · any · depth · easing: easeInOutCubic · 1s draw · 0.4s fill*

*Original: M-182*

The logo draws its outline, then fills.

**Spec (EN):** Animate the logo vector outline stroke from 0 to full length over 1s, then fade in the fill over 0.4s.

**Spec (AR):** حرّك حدود الشعار (الفيكتور) من 0 لين يكتمل خلال ثانية، وبعدين خل التعبئة تظهر خلال 0.4 ثانية.

**When to use:**
- EN: The logo draws its outline, then fills.
- AR: الشعار ينرسم بالخط وبعدين يتعبى.

#### `al-lgo-183` — Logo Glitch
**شعار جلتش**

*workhorse · any · timeline · easing: steps · 0.4s burst*

*Original: M-183*

The logo glitches with split colors, techy.

**Spec (EN):** For about 0.4s the logo jumps a few percent in random directions with red and cyan offset copies, then snaps back clean.

**Spec (AR):** لمدة تقريباً 0.4 ثانية الشعار ينط كم نسبة باتجاهات عشوائية مع نسخ حمرا وسماوية منزاحة، وبعدين يرجع نظيف.

**When to use:**
- EN: The logo glitches with split colors, techy.
- AR: الشعار يرجف بألوان منفصلة، تقني.

#### `al-lgo-184` — Logo Bounce
**شعار يطيح ويرتد**

*workhorse · high · depth · easing: easeOutBounce · 0.8s*

*Original: M-184*

The logo drops in and bounces twice.

**Spec (EN):** The logo falls from above the frame, lands, bounces up 30% then 10% and settles over about 0.8s.

**Spec (AR):** الشعار يطيح من فوق الشاشة، ينزل، يرتد لفوق 30% وبعدين 10% ويستقر خلال تقريباً 0.8 ثانية.

**When to use:**
- EN: The logo drops in and bounces twice.
- AR: الشعار يطيح من فوق ويرتد مرتين.

#### `al-lgo-185` — Logo Shine
**لمعة على الشعار**

*workhorse · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-185*

A shine passes over a logo badge.

**Spec (EN):** A bright diagonal band sweeps across the logo badge from one side to the other over 0.8s, clipped to the badge shape.

**Spec (AR):** شريط لامع مايل يمر على شارة الشعار من جهة للثانية خلال 0.8 ثانية، وما يطلع برا شكل الشارة.

**When to use:**
- EN: A shine passes over a logo badge.
- AR: لمعة تمر على شعار داخل شارة.

#### `al-lgo-186` — Logo Assemble
**الشعار يتجمع**

*workhorse · any · timeline · easing: easeOutCubic · 1s*

*Original: M-186*

Particles gather into the logo, the reverse of M-026.

**Spec (EN):** Hundreds of particles start scattered and fly inward to their positions in the logo over 1s; when they arrive, the solid logo fades in and the particles disappear.

**Spec (AR):** مئات الجزيئات تبدأ متفرقة وتطير لأماكنها داخل الشعار خلال ثانية، ولمن توصل الشعار الكامل يظهر والجزيئات تختفي.

**When to use:**
- EN: Particles gather into the logo, the reverse of M-026.
- AR: جزيئات تتجمع وتصير الشعار، عكس التناثر.

#### `al-lgo-187` — End Card
**بطاقة النهاية**

*workhorse · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-187*

The closing card: logo, handle and a follow prompt.

**Spec (EN):** The logo scales in, then the handle and a "تابعني" line fade up under it 0.15s apart. Hold until the end of the video.

**Spec (AR):** الشعار يكبر ويدخل، وبعدين اليوزر وجملة "تابعني" يطلعون تحته وبينهم 0.15 ثانية. ويثبتون لين آخر الفيديو.

**When to use:**
- EN: The closing card: logo, handle and a follow prompt.
- AR: آخر الفيديو: الشعار وحسابك وتابعني.

#### `al-lgo-188` — Watermark Corner
**علامة مائية بالزاوية**

*workhorse · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-188*

Your logo small in the corner for the whole video.

**Spec (EN):** The logo flies from the center to a top corner while shrinking, then stays there at about 55% opacity and 12% of the width for the rest of the video.

**Spec (AR):** الشعار يطير من النص لزاوية فوق وهو يصغر، وبعدين يبقى هناك بشفافية تقريباً 55% وبحجم 12% من العرض لين آخر الفيديو.

**When to use:**
- EN: Your logo small in the corner for the whole video.
- AR: شعارك صغير بالزاوية طول الفيديو.

#### `al-lgo-189` — Badge Stamp
**ختم**

*workhorse · any · timeline · easing: easeInQuad · 0.3s*

*Original: M-189*

A stamp hits the screen, like "approved" or "free".

**Spec (EN):** A circular stamp with bold text drops from 240% scale to about 92% and settles at 100% in 0.3s, tilted -14°, with a small screen shake on impact.

**Spec (AR):** ختم دائري فيه كلمة عريضة ينزل من حجم 240% لـ تقريباً 92% ويستقر على 100% خلال 0.3 ثانية، مايل -14 درجة، مع هزة خفيفة للشاشة لحظة الضربة.

**When to use:**
- EN: A stamp hits the screen, like "approved" or "free".
- AR: ختم ينطبع على الشاشة، مثل "معتمد" أو "مجاني".

#### `al-lgo-190` — Title Underline Card
**عنوان مع خط**

*workhorse · any · depth · easing: easeOutCubic · 0.9s total*

*Original: M-190*

A big title, an underline drawing in, and a subtitle.

**Spec (EN):** The title fades up (0.4s), an accent underline draws under it (0.4s), then the subtitle fades in (0.3s).

**Spec (AR):** العنوان يطلع من تحت ويظهر (0.4 ثانية)، وخط بلون الهوية ينرسم تحته (0.4 ثانية)، وبعدين العنوان الفرعي يظهر (0.3 ثانية).

**When to use:**
- EN: A big title, an underline drawing in, and a subtitle.
- AR: عنوان كبير وخط ينرسم تحته وعنوان فرعي.

#### `al-lgo-191` — Chapter Title
**عنوان فصل**

*workhorse · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-191*

A big number and title for each part of the video.

**Spec (EN):** A large accent mono number (01, 02…) slides in, then the chapter title fades up beside or under it 0.15s later.

**Spec (AR):** رقم mono كبير بلون الهوية (01 و02…) يدخل، وبعدين عنوان الجزء يطلع جنبه أو تحته بعد 0.15 ثانية.

**When to use:**
- EN: A big number and title for each part of the video.
- AR: رقم كبير وعنوان لكل جزء بالفيديو.

#### `al-lgo-192` — Price Tag
**بطاقة سعر**

*workhorse · high · depth · easing: easeOutBack · 0.6s*

*Original: M-192*

A price or discount tag swings in.

**Spec (EN):** A yellow tag-shaped label swings in from its hole side, from -90° to +12°, -6° and settles over 0.6s.

**Spec (AR):** ملصق أصفر بشكل بطاقة سعر يتأرجح من جهة الفتحة، من -90 درجة لـ +12 و-6 ويستقر خلال 0.6 ثانية.

**When to use:**
- EN: A price or discount tag swings in.
- AR: سعر أو خصم يطلع ويتأرجح.

#### `al-lgo-193` — Progress Bar
**شريط تقدم**

*workhorse · any · timeline · easing: easeInOutCubic · 1.2s*

*Original: M-193*

A bar fills with a percentage, like loading or progress.

**Spec (EN):** A rounded track fills with an accent gradient from the reading-start side over 1.2s while a percentage counts up above it.

**Spec (AR):** مسار بزوايا دائرية يتعبى بتدرج بلون الهوية من جهة بداية القراءة خلال 1.2 ثانية، وفوقه نسبة تعد.

**When to use:**
- EN: A bar fills with a percentage, like loading or progress.
- AR: شريط يعبي مع نسبة، مثل التحميل أو التقدم.

#### `al-lgo-194` — Checklist Tick
**قائمة تتصحح**

*workhorse · any · timeline · easing: easeOutCubic · 0.3s per tick · 0.5s stagger*

*Original: M-194*

Items get ticked one by one, like steps.

**Spec (EN):** Each list item has a box; a mint check mark draws inside it (0.3s), items ticking 0.5s apart.

**Spec (AR):** كل بند في القائمة له مربع، وعلامة صح نعناعية تنرسم داخله (0.3 ثانية)، والبنود تتصحح وبينهم 0.5 ثانية.

**When to use:**
- EN: Items get ticked one by one, like steps.
- AR: نقاط تتصحح وحدة وحدة، مثل الخطوات.

#### `al-lgo-195` — Step Numbers
**خطوات مرقمة**

*workhorse · high · timeline · easing: easeOutBack · 0.25s per step*

*Original: M-195*

Numbers 1, 2, 3 pop in with a connecting line.

**Spec (EN):** Circular accent number badges pop in one by one, 0.4s apart, while a line draws behind them connecting each step.

**Spec (AR):** دواير أرقام بلون الهوية تنط وحدة وحدة وبينهم 0.4 ثانية، وخط ينرسم وراهم يوصل الخطوات.

**When to use:**
- EN: Numbers 1, 2, 3 pop in with a connecting line.
- AR: 1، 2، 3 تطلع ورا بعض مع خط يوصلهم.

#### `al-lgo-196` — Quote Card
**بطاقة اقتباس**

*workhorse · any · timeline · easing: easeOutCubic · 0.8s*

*Original: M-196*

A quote or key line with its author.

**Spec (EN):** A large accent quote mark scales in, then the quote text fades up line by line, then the author name fades in, each 0.2s apart.

**Spec (AR):** علامة اقتباس كبيرة بلون الهوية تكبر وتدخل، وبعدين نص الاقتباس يطلع سطر سطر، وبعدين اسم القائل يظهر، وبين كل وحدة 0.2 ثانية.

**When to use:**
- EN: A quote or key line with its author.
- AR: اقتباس أو جملة مهمة مع اسم قائلها.

#### `al-lgo-197` — Stat Bars
**أعمدة بيانات**

*workhorse · any · timeline · easing: easeOutCubic · 0.6s · 0.1s stagger*

*Original: M-197*

A bar chart grows in, for numbers and comparisons.

**Spec (EN):** Vertical bars grow from the baseline to their values over 0.6s, each starting 0.1s after the previous one, with alternating brand colors.

**Spec (AR):** أعمدة عمودية تطلع من الخط الأساسي لقيمها خلال 0.6 ثانية، وكل عمود يبدأ بعد اللي قبله بـ 0.1 ثانية، بألوان الهوية بالتناوب.

**When to use:**
- EN: A bar chart grows in, for numbers and comparisons.
- AR: رسم أعمدة يطلع، للأرقام والمقارنات.

#### `al-lgo-198` — Pie Fill
**دائرة نسبة**

*workhorse · any · timeline · easing: easeOutCubic · 1s*

*Original: M-198*

A ring fills to a percentage.

**Spec (EN):** A thick ring fills clockwise with the accent color from 0 to the target percentage over 1s, with the number in the middle.

**Spec (AR):** حلقة عريضة تتعبى مع عقارب الساعة بلون الهوية من 0 لين النسبة المطلوبة خلال ثانية، والرقم بالنص.

**When to use:**
- EN: A ring fills to a percentage.
- AR: حلقة تعبي لنسبة معينة.

#### `al-lgo-199` — Map Pin Drop
**دبوس موقع**

*workhorse · high · timeline · easing: easeOutBounce · 0.5s*

*Original: M-199*

A location pin drops onto a place, like "Kuwait".

**Spec (EN):** A pin falls from above, lands with a small bounce, and a ripple ring spreads under it on impact, with the place name fading in below.

**Spec (AR):** دبوس يطيح من فوق، ينزل مع ارتداد خفيف، ودائرة تموج تتوسع تحته لحظة النزول، واسم المكان يظهر تحته.

**When to use:**
- EN: A location pin drops onto a place, like "Kuwait".
- AR: دبوس يطيح على مكان، مثل "الكويت".

#### `al-lgo-200` — Signature Write
**توقيع ينكتب**

*workhorse · calm · timeline · easing: easeInOutSine · 1.5s*

*Original: M-200*

Your signature writes itself at the end of the video.

**Spec (EN):** Animate a handwritten signature path stroke from start to end over about 1.5s with a slight ease, as if written live. Hold, then fade.

**Spec (AR):** حرّك مسار توقيع بخط اليد من بدايته لآخره خلال تقريباً 1.5 ثانية بنعومة، كأنه ينكتب الحين. ثبّته، وبعدين خله يختفي.

**When to use:**
- EN: Your signature writes itself at the end of the video.
- AR: توقيعك ينكتب بخط اليد آخر الفيديو.

#### `al-lgo-036-fast` — Logo Float · Fast
**شعار يطفو · سريع**

*accent · calm · depth · easing: easeInOutSine · loop · 3s*

*Original: M-036*

Variant of M-036: أسرع بـ 40%

**Spec (EN):** The logo hovers behind the person (background layer, under the person matte) with a gentle ±9% vertical bob on a 3s sine loop and a soft glow.

**Spec (AR):** الشعار يطفو ورا الشخص (طبقة الخلفية تحت قناع الشخص) بحركة خفيفة لفوق وتحت ±9% كل 3 ثواني (sine) مع توهج ناعم.

**When to use:**
- EN: Use when you need a fast version of M-036.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-036.

#### `al-lgo-036-slow` — Logo Float · Slow
**شعار يطفو · بطيء**

*accent · calm · depth · easing: easeInOutSine · loop · 3s*

*Original: M-036*

Variant of M-036: أبطأ بـ 60%

**Spec (EN):** The logo hovers behind the person (background layer, under the person matte) with a gentle ±9% vertical bob on a 3s sine loop and a soft glow.

**Spec (AR):** الشعار يطفو ورا الشخص (طبقة الخلفية تحت قناع الشخص) بحركة خفيفة لفوق وتحت ±9% كل 3 ثواني (sine) مع توهج ناعم.

**When to use:**
- EN: Use when you need a slow version of M-036.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-036.

#### `al-lgo-036-gold` — Logo Float · Gold
**شعار يطفو · ذهبي**

*accent · calm · depth · easing: easeInOutSine · loop · 3s*

*Original: M-036*

Variant of M-036: نسخة ذهبية فاخرة

**Spec (EN):** The logo hovers behind the person (background layer, under the person matte) with a gentle ±9% vertical bob on a 3s sine loop and a soft glow.

**Spec (AR):** الشعار يطفو ورا الشخص (طبقة الخلفية تحت قناع الشخص) بحركة خفيفة لفوق وتحت ±9% كل 3 ثواني (sine) مع توهج ناعم.

**When to use:**
- EN: Use when you need a gold version of M-036.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-036.

#### `al-lgo-036-boxed` — Logo Float · Boxed
**شعار يطفو · صندوق**

*accent · calm · depth · easing: easeInOutSine · loop · 3s*

*Original: M-036*

Variant of M-036: النص داخل صندوق ملون

**Spec (EN):** The logo hovers behind the person (background layer, under the person matte) with a gentle ±9% vertical bob on a 3s sine loop and a soft glow.

**Spec (AR):** الشعار يطفو ورا الشخص (طبقة الخلفية تحت قناع الشخص) بحركة خفيفة لفوق وتحت ±9% كل 3 ثواني (sine) مع توهج ناعم.

**When to use:**
- EN: Use when you need a boxed version of M-036.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-036.

#### `al-lgo-037-fast` — Logo Spin-In · Fast
**شعار يدور ويدخل · سريع**

*accent · any · depth · easing: easeOutBack · 0.7s*

*Original: M-037*

Variant of M-037: أسرع بـ 40%

**Spec (EN):** The logo spins in from -220° and scale 0 to 0° and 112%, then settles at 100% over 0.7s total. Exit: shrink to 0 with a 90° turn.

**Spec (AR):** الشعار يدخل وهو يدور من -220 درجة وحجم 0 لين 0 درجة و112%، وبعدين يستقر على 100%، والمجموع 0.7 ثانية. وبالخروج يصغر لـ 0 مع لفة 90 درجة.

**When to use:**
- EN: Use when you need a fast version of M-037.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-037.

#### `al-lgo-037-slow` — Logo Spin-In · Slow
**شعار يدور ويدخل · بطيء**

*accent · any · depth · easing: easeOutBack · 0.7s*

*Original: M-037*

Variant of M-037: أبطأ بـ 60%

**Spec (EN):** The logo spins in from -220° and scale 0 to 0° and 112%, then settles at 100% over 0.7s total. Exit: shrink to 0 with a 90° turn.

**Spec (AR):** الشعار يدخل وهو يدور من -220 درجة وحجم 0 لين 0 درجة و112%، وبعدين يستقر على 100%، والمجموع 0.7 ثانية. وبالخروج يصغر لـ 0 مع لفة 90 درجة.

**When to use:**
- EN: Use when you need a slow version of M-037.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-037.

#### `al-lgo-037-gold` — Logo Spin-In · Gold
**شعار يدور ويدخل · ذهبي**

*accent · any · depth · easing: easeOutBack · 0.7s*

*Original: M-037*

Variant of M-037: نسخة ذهبية فاخرة

**Spec (EN):** The logo spins in from -220° and scale 0 to 0° and 112%, then settles at 100% over 0.7s total. Exit: shrink to 0 with a 90° turn.

**Spec (AR):** الشعار يدخل وهو يدور من -220 درجة وحجم 0 لين 0 درجة و112%، وبعدين يستقر على 100%، والمجموع 0.7 ثانية. وبالخروج يصغر لـ 0 مع لفة 90 درجة.

**When to use:**
- EN: Use when you need a gold version of M-037.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-037.

#### `al-lgo-037-boxed` — Logo Spin-In · Boxed
**شعار يدور ويدخل · صندوق**

*accent · any · depth · easing: easeOutBack · 0.7s*

*Original: M-037*

Variant of M-037: النص داخل صندوق ملون

**Spec (EN):** The logo spins in from -220° and scale 0 to 0° and 112%, then settles at 100% over 0.7s total. Exit: shrink to 0 with a 90° turn.

**Spec (AR):** الشعار يدخل وهو يدور من -220 درجة وحجم 0 لين 0 درجة و112%، وبعدين يستقر على 100%، والمجموع 0.7 ثانية. وبالخروج يصغر لـ 0 مع لفة 90 درجة.

**When to use:**
- EN: Use when you need a boxed version of M-037.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-037.

#### `al-lgo-038-fast` — Title Card Drop · Fast
**بطاقة عنوان تنزل · سريع**

*accent · any · depth · easing: spring · 0.55s in*

*Original: M-038*

Variant of M-038: أسرع بـ 40%

**Spec (EN):** A dark rounded card with an accent border, an icon on one side and a two-line title (bold mono title plus an accent subtitle) drops from above the frame with a spring and about a 10% overshoot. Holds, then slides back up.

**Spec (AR):** بطاقة غامقة بزوايا دائرية وإطار بلون الهوية، فيها أيقونة على جنب وعنوان بسطرين (عنوان عريض mono وتحته عنوان فرعي بلون الهوية)، تنزل من فوق الشاشة بحركة نابض وتتعدى تقريباً 10%. تثبت، وبعدين ترجع لفوق.

**When to use:**
- EN: Use when you need a fast version of M-038.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-038.

#### `al-lgo-038-slow` — Title Card Drop · Slow
**بطاقة عنوان تنزل · بطيء**

*accent · any · depth · easing: spring · 0.55s in*

*Original: M-038*

Variant of M-038: أبطأ بـ 60%

**Spec (EN):** A dark rounded card with an accent border, an icon on one side and a two-line title (bold mono title plus an accent subtitle) drops from above the frame with a spring and about a 10% overshoot. Holds, then slides back up.

**Spec (AR):** بطاقة غامقة بزوايا دائرية وإطار بلون الهوية، فيها أيقونة على جنب وعنوان بسطرين (عنوان عريض mono وتحته عنوان فرعي بلون الهوية)، تنزل من فوق الشاشة بحركة نابض وتتعدى تقريباً 10%. تثبت، وبعدين ترجع لفوق.

**When to use:**
- EN: Use when you need a slow version of M-038.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-038.

#### `al-lgo-038-gold` — Title Card Drop · Gold
**بطاقة عنوان تنزل · ذهبي**

*accent · any · depth · easing: spring · 0.55s in*

*Original: M-038*

Variant of M-038: نسخة ذهبية فاخرة

**Spec (EN):** A dark rounded card with an accent border, an icon on one side and a two-line title (bold mono title plus an accent subtitle) drops from above the frame with a spring and about a 10% overshoot. Holds, then slides back up.

**Spec (AR):** بطاقة غامقة بزوايا دائرية وإطار بلون الهوية، فيها أيقونة على جنب وعنوان بسطرين (عنوان عريض mono وتحته عنوان فرعي بلون الهوية)، تنزل من فوق الشاشة بحركة نابض وتتعدى تقريباً 10%. تثبت، وبعدين ترجع لفوق.

**When to use:**
- EN: Use when you need a gold version of M-038.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-038.

#### `al-lgo-038-boxed` — Title Card Drop · Boxed
**بطاقة عنوان تنزل · صندوق**

*accent · any · depth · easing: spring · 0.55s in*

*Original: M-038*

Variant of M-038: النص داخل صندوق ملون

**Spec (EN):** A dark rounded card with an accent border, an icon on one side and a two-line title (bold mono title plus an accent subtitle) drops from above the frame with a spring and about a 10% overshoot. Holds, then slides back up.

**Spec (AR):** بطاقة غامقة بزوايا دائرية وإطار بلون الهوية، فيها أيقونة على جنب وعنوان بسطرين (عنوان عريض mono وتحته عنوان فرعي بلون الهوية)، تنزل من فوق الشاشة بحركة نابض وتتعدى تقريباً 10%. تثبت، وبعدين ترجع لفوق.

**When to use:**
- EN: Use when you need a boxed version of M-038.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-038.

#### `al-lgo-039-fast` — Lower Third · Fast
**شريط الاسم السفلي · سريع**

*accent · any · timeline · easing: easeOutExpo · 0.4s bar · 0.3s text*

*Original: M-039*

Variant of M-039: أسرع بـ 40%

**Spec (EN):** An accent bar grows in from the right edge (0.4s), then the name and the subtitle slide in 12% and fade in inside it (0.3s, 0.08s stagger). Holds, then the text fades and the bar retracts.

**Spec (AR):** شريط بلون الهوية يطلع من الحافة اليمين (0.4 ثانية)، وبعدين الاسم والسطر اللي تحته يدخلون بإزاحة 12% ويظهرون داخل الشريط (0.3 ثانية، وبينهم 0.08 ثانية). يثبت، وبعدين النص يختفي والشريط ينسحب.

**When to use:**
- EN: Use when you need a fast version of M-039.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-039.

#### `al-lgo-039-slow` — Lower Third · Slow
**شريط الاسم السفلي · بطيء**

*accent · any · timeline · easing: easeOutExpo · 0.4s bar · 0.3s text*

*Original: M-039*

Variant of M-039: أبطأ بـ 60%

**Spec (EN):** An accent bar grows in from the right edge (0.4s), then the name and the subtitle slide in 12% and fade in inside it (0.3s, 0.08s stagger). Holds, then the text fades and the bar retracts.

**Spec (AR):** شريط بلون الهوية يطلع من الحافة اليمين (0.4 ثانية)، وبعدين الاسم والسطر اللي تحته يدخلون بإزاحة 12% ويظهرون داخل الشريط (0.3 ثانية، وبينهم 0.08 ثانية). يثبت، وبعدين النص يختفي والشريط ينسحب.

**When to use:**
- EN: Use when you need a slow version of M-039.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-039.

#### `al-lgo-039-gold` — Lower Third · Gold
**شريط الاسم السفلي · ذهبي**

*accent · any · timeline · easing: easeOutExpo · 0.4s bar · 0.3s text*

*Original: M-039*

Variant of M-039: نسخة ذهبية فاخرة

**Spec (EN):** An accent bar grows in from the right edge (0.4s), then the name and the subtitle slide in 12% and fade in inside it (0.3s, 0.08s stagger). Holds, then the text fades and the bar retracts.

**Spec (AR):** شريط بلون الهوية يطلع من الحافة اليمين (0.4 ثانية)، وبعدين الاسم والسطر اللي تحته يدخلون بإزاحة 12% ويظهرون داخل الشريط (0.3 ثانية، وبينهم 0.08 ثانية). يثبت، وبعدين النص يختفي والشريط ينسحب.

**When to use:**
- EN: Use when you need a gold version of M-039.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-039.

#### `al-lgo-039-boxed` — Lower Third · Boxed
**شريط الاسم السفلي · صندوق**

*accent · any · timeline · easing: easeOutExpo · 0.4s bar · 0.3s text*

*Original: M-039*

Variant of M-039: النص داخل صندوق ملون

**Spec (EN):** An accent bar grows in from the right edge (0.4s), then the name and the subtitle slide in 12% and fade in inside it (0.3s, 0.08s stagger). Holds, then the text fades and the bar retracts.

**Spec (AR):** شريط بلون الهوية يطلع من الحافة اليمين (0.4 ثانية)، وبعدين الاسم والسطر اللي تحته يدخلون بإزاحة 12% ويظهرون داخل الشريط (0.3 ثانية، وبينهم 0.08 ثانية). يثبت، وبعدين النص يختفي والشريط ينسحب.

**When to use:**
- EN: Use when you need a boxed version of M-039.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-039.

#### `al-lgo-040-fast` — Number Counter · Fast
**عداد أرقام · سريع**

*accent · any · depth · easing: easeOutExpo · 1.2s count*

*Original: M-040*

Variant of M-040: أسرع بـ 40%

**Spec (EN):** A number counts up from 0 to the target value over 1.2s (easeOutExpo, fast at first, then slowing), in tabular monospaced digits with an accent color, and a label beneath. Optionally scale-punch the final value (M-008).

**Spec (AR):** رقم يعد من 0 لين الرقم المطلوب خلال 1.2 ثانية (easeOutExpo: سريع بالبداية وبعدين يبطّي)، بأرقام mono متساوية العرض وبلون الهوية، وتحته وصف. وتقدر تحط على الرقم الأخير ضربة تكبير (M-008).

**When to use:**
- EN: Use when you need a fast version of M-040.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-040.

#### `al-lgo-040-slow` — Number Counter · Slow
**عداد أرقام · بطيء**

*accent · any · depth · easing: easeOutExpo · 1.2s count*

*Original: M-040*

Variant of M-040: أبطأ بـ 60%

**Spec (EN):** A number counts up from 0 to the target value over 1.2s (easeOutExpo, fast at first, then slowing), in tabular monospaced digits with an accent color, and a label beneath. Optionally scale-punch the final value (M-008).

**Spec (AR):** رقم يعد من 0 لين الرقم المطلوب خلال 1.2 ثانية (easeOutExpo: سريع بالبداية وبعدين يبطّي)، بأرقام mono متساوية العرض وبلون الهوية، وتحته وصف. وتقدر تحط على الرقم الأخير ضربة تكبير (M-008).

**When to use:**
- EN: Use when you need a slow version of M-040.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-040.

#### `al-lgo-040-gold` — Number Counter · Gold
**عداد أرقام · ذهبي**

*accent · any · depth · easing: easeOutExpo · 1.2s count*

*Original: M-040*

Variant of M-040: نسخة ذهبية فاخرة

**Spec (EN):** A number counts up from 0 to the target value over 1.2s (easeOutExpo, fast at first, then slowing), in tabular monospaced digits with an accent color, and a label beneath. Optionally scale-punch the final value (M-008).

**Spec (AR):** رقم يعد من 0 لين الرقم المطلوب خلال 1.2 ثانية (easeOutExpo: سريع بالبداية وبعدين يبطّي)، بأرقام mono متساوية العرض وبلون الهوية، وتحته وصف. وتقدر تحط على الرقم الأخير ضربة تكبير (M-008).

**When to use:**
- EN: Use when you need a gold version of M-040.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-040.

#### `al-lgo-040-boxed` — Number Counter · Boxed
**عداد أرقام · صندوق**

*accent · any · depth · easing: easeOutExpo · 1.2s count*

*Original: M-040*

Variant of M-040: النص داخل صندوق ملون

**Spec (EN):** A number counts up from 0 to the target value over 1.2s (easeOutExpo, fast at first, then slowing), in tabular monospaced digits with an accent color, and a label beneath. Optionally scale-punch the final value (M-008).

**Spec (AR):** رقم يعد من 0 لين الرقم المطلوب خلال 1.2 ثانية (easeOutExpo: سريع بالبداية وبعدين يبطّي)، بأرقام mono متساوية العرض وبلون الهوية، وتحته وصف. وتقدر تحط على الرقم الأخير ضربة تكبير (M-008).

**When to use:**
- EN: Use when you need a boxed version of M-040.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-040.

#### `al-lgo-181-fast` — Logo Mask Reveal · Fast
**شعار ينكشف من قناع · سريع**

*accent · any · timeline · easing: easeInOutQuart · 0.6s*

*Original: M-181*

Variant of M-181: أسرع بـ 40%

**Spec (EN):** The logo sits inside a box with hidden overflow and slides up from below its edge into place over 0.6s (see M-004).

**Spec (AR):** الشعار داخل صندوق مخفي الأطراف، ويطلع من تحت حافته لمكانه خلال 0.6 ثانية (شوف M-004).

**When to use:**
- EN: Use when you need a fast version of M-181.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-181.

#### `al-lgo-181-slow` — Logo Mask Reveal · Slow
**شعار ينكشف من قناع · بطيء**

*accent · any · timeline · easing: easeInOutQuart · 0.6s*

*Original: M-181*

Variant of M-181: أبطأ بـ 60%

**Spec (EN):** The logo sits inside a box with hidden overflow and slides up from below its edge into place over 0.6s (see M-004).

**Spec (AR):** الشعار داخل صندوق مخفي الأطراف، ويطلع من تحت حافته لمكانه خلال 0.6 ثانية (شوف M-004).

**When to use:**
- EN: Use when you need a slow version of M-181.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-181.

#### `al-lgo-181-gold` — Logo Mask Reveal · Gold
**شعار ينكشف من قناع · ذهبي**

*accent · any · timeline · easing: easeInOutQuart · 0.6s*

*Original: M-181*

Variant of M-181: نسخة ذهبية فاخرة

**Spec (EN):** The logo sits inside a box with hidden overflow and slides up from below its edge into place over 0.6s (see M-004).

**Spec (AR):** الشعار داخل صندوق مخفي الأطراف، ويطلع من تحت حافته لمكانه خلال 0.6 ثانية (شوف M-004).

**When to use:**
- EN: Use when you need a gold version of M-181.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-181.

#### `al-lgo-181-boxed` — Logo Mask Reveal · Boxed
**شعار ينكشف من قناع · صندوق**

*accent · any · timeline · easing: easeInOutQuart · 0.6s*

*Original: M-181*

Variant of M-181: النص داخل صندوق ملون

**Spec (EN):** The logo sits inside a box with hidden overflow and slides up from below its edge into place over 0.6s (see M-004).

**Spec (AR):** الشعار داخل صندوق مخفي الأطراف، ويطلع من تحت حافته لمكانه خلال 0.6 ثانية (شوف M-004).

**When to use:**
- EN: Use when you need a boxed version of M-181.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-181.

#### `al-lgo-182-fast` — Logo Stroke Draw · Fast
**رسم حدود الشعار · سريع**

*accent · any · depth · easing: easeInOutCubic · 1s draw · 0.4s fill*

*Original: M-182*

Variant of M-182: أسرع بـ 40%

**Spec (EN):** Animate the logo vector outline stroke from 0 to full length over 1s, then fade in the fill over 0.4s.

**Spec (AR):** حرّك حدود الشعار (الفيكتور) من 0 لين يكتمل خلال ثانية، وبعدين خل التعبئة تظهر خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-182.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-182.

#### `al-lgo-182-slow` — Logo Stroke Draw · Slow
**رسم حدود الشعار · بطيء**

*accent · any · depth · easing: easeInOutCubic · 1s draw · 0.4s fill*

*Original: M-182*

Variant of M-182: أبطأ بـ 60%

**Spec (EN):** Animate the logo vector outline stroke from 0 to full length over 1s, then fade in the fill over 0.4s.

**Spec (AR):** حرّك حدود الشعار (الفيكتور) من 0 لين يكتمل خلال ثانية، وبعدين خل التعبئة تظهر خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-182.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-182.

#### `al-lgo-182-gold` — Logo Stroke Draw · Gold
**رسم حدود الشعار · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 1s draw · 0.4s fill*

*Original: M-182*

Variant of M-182: نسخة ذهبية فاخرة

**Spec (EN):** Animate the logo vector outline stroke from 0 to full length over 1s, then fade in the fill over 0.4s.

**Spec (AR):** حرّك حدود الشعار (الفيكتور) من 0 لين يكتمل خلال ثانية، وبعدين خل التعبئة تظهر خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-182.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-182.

#### `al-lgo-182-boxed` — Logo Stroke Draw · Boxed
**رسم حدود الشعار · صندوق**

*accent · any · depth · easing: easeInOutCubic · 1s draw · 0.4s fill*

*Original: M-182*

Variant of M-182: النص داخل صندوق ملون

**Spec (EN):** Animate the logo vector outline stroke from 0 to full length over 1s, then fade in the fill over 0.4s.

**Spec (AR):** حرّك حدود الشعار (الفيكتور) من 0 لين يكتمل خلال ثانية، وبعدين خل التعبئة تظهر خلال 0.4 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-182.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-182.

#### `al-lgo-183-fast` — Logo Glitch · Fast
**شعار جلتش · سريع**

*accent · any · timeline · easing: steps · 0.4s burst*

*Original: M-183*

Variant of M-183: أسرع بـ 40%

**Spec (EN):** For about 0.4s the logo jumps a few percent in random directions with red and cyan offset copies, then snaps back clean.

**Spec (AR):** لمدة تقريباً 0.4 ثانية الشعار ينط كم نسبة باتجاهات عشوائية مع نسخ حمرا وسماوية منزاحة، وبعدين يرجع نظيف.

**When to use:**
- EN: Use when you need a fast version of M-183.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-183.

#### `al-lgo-183-slow` — Logo Glitch · Slow
**شعار جلتش · بطيء**

*accent · any · timeline · easing: steps · 0.4s burst*

*Original: M-183*

Variant of M-183: أبطأ بـ 60%

**Spec (EN):** For about 0.4s the logo jumps a few percent in random directions with red and cyan offset copies, then snaps back clean.

**Spec (AR):** لمدة تقريباً 0.4 ثانية الشعار ينط كم نسبة باتجاهات عشوائية مع نسخ حمرا وسماوية منزاحة، وبعدين يرجع نظيف.

**When to use:**
- EN: Use when you need a slow version of M-183.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-183.

#### `al-lgo-183-gold` — Logo Glitch · Gold
**شعار جلتش · ذهبي**

*accent · any · timeline · easing: steps · 0.4s burst*

*Original: M-183*

Variant of M-183: نسخة ذهبية فاخرة

**Spec (EN):** For about 0.4s the logo jumps a few percent in random directions with red and cyan offset copies, then snaps back clean.

**Spec (AR):** لمدة تقريباً 0.4 ثانية الشعار ينط كم نسبة باتجاهات عشوائية مع نسخ حمرا وسماوية منزاحة، وبعدين يرجع نظيف.

**When to use:**
- EN: Use when you need a gold version of M-183.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-183.

#### `al-lgo-183-boxed` — Logo Glitch · Boxed
**شعار جلتش · صندوق**

*accent · any · timeline · easing: steps · 0.4s burst*

*Original: M-183*

Variant of M-183: النص داخل صندوق ملون

**Spec (EN):** For about 0.4s the logo jumps a few percent in random directions with red and cyan offset copies, then snaps back clean.

**Spec (AR):** لمدة تقريباً 0.4 ثانية الشعار ينط كم نسبة باتجاهات عشوائية مع نسخ حمرا وسماوية منزاحة، وبعدين يرجع نظيف.

**When to use:**
- EN: Use when you need a boxed version of M-183.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-183.

#### `al-lgo-184-fast` — Logo Bounce · Fast
**شعار يطيح ويرتد · سريع**

*accent · any · depth · easing: easeOutBounce · 0.8s*

*Original: M-184*

Variant of M-184: أسرع بـ 40%

**Spec (EN):** The logo falls from above the frame, lands, bounces up 30% then 10% and settles over about 0.8s.

**Spec (AR):** الشعار يطيح من فوق الشاشة، ينزل، يرتد لفوق 30% وبعدين 10% ويستقر خلال تقريباً 0.8 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-184.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-184.

#### `al-lgo-184-slow` — Logo Bounce · Slow
**شعار يطيح ويرتد · بطيء**

*accent · any · depth · easing: easeOutBounce · 0.8s*

*Original: M-184*

Variant of M-184: أبطأ بـ 60%

**Spec (EN):** The logo falls from above the frame, lands, bounces up 30% then 10% and settles over about 0.8s.

**Spec (AR):** الشعار يطيح من فوق الشاشة، ينزل، يرتد لفوق 30% وبعدين 10% ويستقر خلال تقريباً 0.8 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-184.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-184.

#### `al-lgo-184-gold` — Logo Bounce · Gold
**شعار يطيح ويرتد · ذهبي**

*accent · any · depth · easing: easeOutBounce · 0.8s*

*Original: M-184*

Variant of M-184: نسخة ذهبية فاخرة

**Spec (EN):** The logo falls from above the frame, lands, bounces up 30% then 10% and settles over about 0.8s.

**Spec (AR):** الشعار يطيح من فوق الشاشة، ينزل، يرتد لفوق 30% وبعدين 10% ويستقر خلال تقريباً 0.8 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-184.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-184.

#### `al-lgo-184-boxed` — Logo Bounce · Boxed
**شعار يطيح ويرتد · صندوق**

*accent · any · depth · easing: easeOutBounce · 0.8s*

*Original: M-184*

Variant of M-184: النص داخل صندوق ملون

**Spec (EN):** The logo falls from above the frame, lands, bounces up 30% then 10% and settles over about 0.8s.

**Spec (AR):** الشعار يطيح من فوق الشاشة، ينزل، يرتد لفوق 30% وبعدين 10% ويستقر خلال تقريباً 0.8 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-184.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-184.

#### `al-lgo-185-fast` — Logo Shine · Fast
**لمعة على الشعار · سريع**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-185*

Variant of M-185: أسرع بـ 40%

**Spec (EN):** A bright diagonal band sweeps across the logo badge from one side to the other over 0.8s, clipped to the badge shape.

**Spec (AR):** شريط لامع مايل يمر على شارة الشعار من جهة للثانية خلال 0.8 ثانية، وما يطلع برا شكل الشارة.

**When to use:**
- EN: Use when you need a fast version of M-185.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-185.

#### `al-lgo-185-slow` — Logo Shine · Slow
**لمعة على الشعار · بطيء**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-185*

Variant of M-185: أبطأ بـ 60%

**Spec (EN):** A bright diagonal band sweeps across the logo badge from one side to the other over 0.8s, clipped to the badge shape.

**Spec (AR):** شريط لامع مايل يمر على شارة الشعار من جهة للثانية خلال 0.8 ثانية، وما يطلع برا شكل الشارة.

**When to use:**
- EN: Use when you need a slow version of M-185.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-185.

#### `al-lgo-185-gold` — Logo Shine · Gold
**لمعة على الشعار · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-185*

Variant of M-185: نسخة ذهبية فاخرة

**Spec (EN):** A bright diagonal band sweeps across the logo badge from one side to the other over 0.8s, clipped to the badge shape.

**Spec (AR):** شريط لامع مايل يمر على شارة الشعار من جهة للثانية خلال 0.8 ثانية، وما يطلع برا شكل الشارة.

**When to use:**
- EN: Use when you need a gold version of M-185.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-185.

#### `al-lgo-185-boxed` — Logo Shine · Boxed
**لمعة على الشعار · صندوق**

*accent · calm · timeline · easing: easeInOutSine · 0.8s*

*Original: M-185*

Variant of M-185: النص داخل صندوق ملون

**Spec (EN):** A bright diagonal band sweeps across the logo badge from one side to the other over 0.8s, clipped to the badge shape.

**Spec (AR):** شريط لامع مايل يمر على شارة الشعار من جهة للثانية خلال 0.8 ثانية، وما يطلع برا شكل الشارة.

**When to use:**
- EN: Use when you need a boxed version of M-185.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-185.

#### `al-lgo-186-fast` — Logo Assemble · Fast
**الشعار يتجمع · سريع**

*accent · any · timeline · easing: easeOutCubic · 1s*

*Original: M-186*

Variant of M-186: أسرع بـ 40%

**Spec (EN):** Hundreds of particles start scattered and fly inward to their positions in the logo over 1s; when they arrive, the solid logo fades in and the particles disappear.

**Spec (AR):** مئات الجزيئات تبدأ متفرقة وتطير لأماكنها داخل الشعار خلال ثانية، ولمن توصل الشعار الكامل يظهر والجزيئات تختفي.

**When to use:**
- EN: Use when you need a fast version of M-186.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-186.

#### `al-lgo-186-slow` — Logo Assemble · Slow
**الشعار يتجمع · بطيء**

*accent · any · timeline · easing: easeOutCubic · 1s*

*Original: M-186*

Variant of M-186: أبطأ بـ 60%

**Spec (EN):** Hundreds of particles start scattered and fly inward to their positions in the logo over 1s; when they arrive, the solid logo fades in and the particles disappear.

**Spec (AR):** مئات الجزيئات تبدأ متفرقة وتطير لأماكنها داخل الشعار خلال ثانية، ولمن توصل الشعار الكامل يظهر والجزيئات تختفي.

**When to use:**
- EN: Use when you need a slow version of M-186.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-186.

#### `al-lgo-186-gold` — Logo Assemble · Gold
**الشعار يتجمع · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 1s*

*Original: M-186*

Variant of M-186: نسخة ذهبية فاخرة

**Spec (EN):** Hundreds of particles start scattered and fly inward to their positions in the logo over 1s; when they arrive, the solid logo fades in and the particles disappear.

**Spec (AR):** مئات الجزيئات تبدأ متفرقة وتطير لأماكنها داخل الشعار خلال ثانية، ولمن توصل الشعار الكامل يظهر والجزيئات تختفي.

**When to use:**
- EN: Use when you need a gold version of M-186.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-186.

#### `al-lgo-186-boxed` — Logo Assemble · Boxed
**الشعار يتجمع · صندوق**

*accent · any · timeline · easing: easeOutCubic · 1s*

*Original: M-186*

Variant of M-186: النص داخل صندوق ملون

**Spec (EN):** Hundreds of particles start scattered and fly inward to their positions in the logo over 1s; when they arrive, the solid logo fades in and the particles disappear.

**Spec (AR):** مئات الجزيئات تبدأ متفرقة وتطير لأماكنها داخل الشعار خلال ثانية، ولمن توصل الشعار الكامل يظهر والجزيئات تختفي.

**When to use:**
- EN: Use when you need a boxed version of M-186.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-186.

#### `al-lgo-187-fast` — End Card · Fast
**بطاقة النهاية · سريع**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-187*

Variant of M-187: أسرع بـ 40%

**Spec (EN):** The logo scales in, then the handle and a "تابعني" line fade up under it 0.15s apart. Hold until the end of the video.

**Spec (AR):** الشعار يكبر ويدخل، وبعدين اليوزر وجملة "تابعني" يطلعون تحته وبينهم 0.15 ثانية. ويثبتون لين آخر الفيديو.

**When to use:**
- EN: Use when you need a fast version of M-187.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-187.

#### `al-lgo-187-slow` — End Card · Slow
**بطاقة النهاية · بطيء**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-187*

Variant of M-187: أبطأ بـ 60%

**Spec (EN):** The logo scales in, then the handle and a "تابعني" line fade up under it 0.15s apart. Hold until the end of the video.

**Spec (AR):** الشعار يكبر ويدخل، وبعدين اليوزر وجملة "تابعني" يطلعون تحته وبينهم 0.15 ثانية. ويثبتون لين آخر الفيديو.

**When to use:**
- EN: Use when you need a slow version of M-187.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-187.

#### `al-lgo-187-gold` — End Card · Gold
**بطاقة النهاية · ذهبي**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-187*

Variant of M-187: نسخة ذهبية فاخرة

**Spec (EN):** The logo scales in, then the handle and a "تابعني" line fade up under it 0.15s apart. Hold until the end of the video.

**Spec (AR):** الشعار يكبر ويدخل، وبعدين اليوزر وجملة "تابعني" يطلعون تحته وبينهم 0.15 ثانية. ويثبتون لين آخر الفيديو.

**When to use:**
- EN: Use when you need a gold version of M-187.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-187.

#### `al-lgo-187-boxed` — End Card · Boxed
**بطاقة النهاية · صندوق**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-187*

Variant of M-187: النص داخل صندوق ملون

**Spec (EN):** The logo scales in, then the handle and a "تابعني" line fade up under it 0.15s apart. Hold until the end of the video.

**Spec (AR):** الشعار يكبر ويدخل، وبعدين اليوزر وجملة "تابعني" يطلعون تحته وبينهم 0.15 ثانية. ويثبتون لين آخر الفيديو.

**When to use:**
- EN: Use when you need a boxed version of M-187.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-187.

#### `al-lgo-188-fast` — Watermark Corner · Fast
**علامة مائية بالزاوية · سريع**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-188*

Variant of M-188: أسرع بـ 40%

**Spec (EN):** The logo flies from the center to a top corner while shrinking, then stays there at about 55% opacity and 12% of the width for the rest of the video.

**Spec (AR):** الشعار يطير من النص لزاوية فوق وهو يصغر، وبعدين يبقى هناك بشفافية تقريباً 55% وبحجم 12% من العرض لين آخر الفيديو.

**When to use:**
- EN: Use when you need a fast version of M-188.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-188.

#### `al-lgo-188-slow` — Watermark Corner · Slow
**علامة مائية بالزاوية · بطيء**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-188*

Variant of M-188: أبطأ بـ 60%

**Spec (EN):** The logo flies from the center to a top corner while shrinking, then stays there at about 55% opacity and 12% of the width for the rest of the video.

**Spec (AR):** الشعار يطير من النص لزاوية فوق وهو يصغر، وبعدين يبقى هناك بشفافية تقريباً 55% وبحجم 12% من العرض لين آخر الفيديو.

**When to use:**
- EN: Use when you need a slow version of M-188.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-188.

#### `al-lgo-188-gold` — Watermark Corner · Gold
**علامة مائية بالزاوية · ذهبي**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-188*

Variant of M-188: نسخة ذهبية فاخرة

**Spec (EN):** The logo flies from the center to a top corner while shrinking, then stays there at about 55% opacity and 12% of the width for the rest of the video.

**Spec (AR):** الشعار يطير من النص لزاوية فوق وهو يصغر، وبعدين يبقى هناك بشفافية تقريباً 55% وبحجم 12% من العرض لين آخر الفيديو.

**When to use:**
- EN: Use when you need a gold version of M-188.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-188.

#### `al-lgo-188-boxed` — Watermark Corner · Boxed
**علامة مائية بالزاوية · صندوق**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-188*

Variant of M-188: النص داخل صندوق ملون

**Spec (EN):** The logo flies from the center to a top corner while shrinking, then stays there at about 55% opacity and 12% of the width for the rest of the video.

**Spec (AR):** الشعار يطير من النص لزاوية فوق وهو يصغر، وبعدين يبقى هناك بشفافية تقريباً 55% وبحجم 12% من العرض لين آخر الفيديو.

**When to use:**
- EN: Use when you need a boxed version of M-188.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-188.

#### `al-lgo-189-fast` — Badge Stamp · Fast
**ختم · سريع**

*accent · calm · timeline · easing: easeInQuad · 0.3s*

*Original: M-189*

Variant of M-189: أسرع بـ 40%

**Spec (EN):** A circular stamp with bold text drops from 240% scale to about 92% and settles at 100% in 0.3s, tilted -14°, with a small screen shake on impact.

**Spec (AR):** ختم دائري فيه كلمة عريضة ينزل من حجم 240% لـ تقريباً 92% ويستقر على 100% خلال 0.3 ثانية، مايل -14 درجة، مع هزة خفيفة للشاشة لحظة الضربة.

**When to use:**
- EN: Use when you need a fast version of M-189.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-189.

#### `al-lgo-189-slow` — Badge Stamp · Slow
**ختم · بطيء**

*accent · calm · timeline · easing: easeInQuad · 0.3s*

*Original: M-189*

Variant of M-189: أبطأ بـ 60%

**Spec (EN):** A circular stamp with bold text drops from 240% scale to about 92% and settles at 100% in 0.3s, tilted -14°, with a small screen shake on impact.

**Spec (AR):** ختم دائري فيه كلمة عريضة ينزل من حجم 240% لـ تقريباً 92% ويستقر على 100% خلال 0.3 ثانية، مايل -14 درجة، مع هزة خفيفة للشاشة لحظة الضربة.

**When to use:**
- EN: Use when you need a slow version of M-189.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-189.

#### `al-lgo-189-gold` — Badge Stamp · Gold
**ختم · ذهبي**

*accent · calm · timeline · easing: easeInQuad · 0.3s*

*Original: M-189*

Variant of M-189: نسخة ذهبية فاخرة

**Spec (EN):** A circular stamp with bold text drops from 240% scale to about 92% and settles at 100% in 0.3s, tilted -14°, with a small screen shake on impact.

**Spec (AR):** ختم دائري فيه كلمة عريضة ينزل من حجم 240% لـ تقريباً 92% ويستقر على 100% خلال 0.3 ثانية، مايل -14 درجة، مع هزة خفيفة للشاشة لحظة الضربة.

**When to use:**
- EN: Use when you need a gold version of M-189.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-189.

#### `al-lgo-189-boxed` — Badge Stamp · Boxed
**ختم · صندوق**

*accent · calm · timeline · easing: easeInQuad · 0.3s*

*Original: M-189*

Variant of M-189: النص داخل صندوق ملون

**Spec (EN):** A circular stamp with bold text drops from 240% scale to about 92% and settles at 100% in 0.3s, tilted -14°, with a small screen shake on impact.

**Spec (AR):** ختم دائري فيه كلمة عريضة ينزل من حجم 240% لـ تقريباً 92% ويستقر على 100% خلال 0.3 ثانية، مايل -14 درجة، مع هزة خفيفة للشاشة لحظة الضربة.

**When to use:**
- EN: Use when you need a boxed version of M-189.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-189.

#### `al-lgo-190-fast` — Title Underline Card · Fast
**عنوان مع خط · سريع**

*accent · any · depth · easing: easeOutCubic · 0.9s total*

*Original: M-190*

Variant of M-190: أسرع بـ 40%

**Spec (EN):** The title fades up (0.4s), an accent underline draws under it (0.4s), then the subtitle fades in (0.3s).

**Spec (AR):** العنوان يطلع من تحت ويظهر (0.4 ثانية)، وخط بلون الهوية ينرسم تحته (0.4 ثانية)، وبعدين العنوان الفرعي يظهر (0.3 ثانية).

**When to use:**
- EN: Use when you need a fast version of M-190.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-190.

#### `al-lgo-190-slow` — Title Underline Card · Slow
**عنوان مع خط · بطيء**

*accent · any · depth · easing: easeOutCubic · 0.9s total*

*Original: M-190*

Variant of M-190: أبطأ بـ 60%

**Spec (EN):** The title fades up (0.4s), an accent underline draws under it (0.4s), then the subtitle fades in (0.3s).

**Spec (AR):** العنوان يطلع من تحت ويظهر (0.4 ثانية)، وخط بلون الهوية ينرسم تحته (0.4 ثانية)، وبعدين العنوان الفرعي يظهر (0.3 ثانية).

**When to use:**
- EN: Use when you need a slow version of M-190.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-190.

#### `al-lgo-190-gold` — Title Underline Card · Gold
**عنوان مع خط · ذهبي**

*accent · any · depth · easing: easeOutCubic · 0.9s total*

*Original: M-190*

Variant of M-190: نسخة ذهبية فاخرة

**Spec (EN):** The title fades up (0.4s), an accent underline draws under it (0.4s), then the subtitle fades in (0.3s).

**Spec (AR):** العنوان يطلع من تحت ويظهر (0.4 ثانية)، وخط بلون الهوية ينرسم تحته (0.4 ثانية)، وبعدين العنوان الفرعي يظهر (0.3 ثانية).

**When to use:**
- EN: Use when you need a gold version of M-190.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-190.

#### `al-lgo-190-boxed` — Title Underline Card · Boxed
**عنوان مع خط · صندوق**

*accent · any · depth · easing: easeOutCubic · 0.9s total*

*Original: M-190*

Variant of M-190: النص داخل صندوق ملون

**Spec (EN):** The title fades up (0.4s), an accent underline draws under it (0.4s), then the subtitle fades in (0.3s).

**Spec (AR):** العنوان يطلع من تحت ويظهر (0.4 ثانية)، وخط بلون الهوية ينرسم تحته (0.4 ثانية)، وبعدين العنوان الفرعي يظهر (0.3 ثانية).

**When to use:**
- EN: Use when you need a boxed version of M-190.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-190.

#### `al-lgo-191-fast` — Chapter Title · Fast
**عنوان فصل · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-191*

Variant of M-191: أسرع بـ 40%

**Spec (EN):** A large accent mono number (01, 02…) slides in, then the chapter title fades up beside or under it 0.15s later.

**Spec (AR):** رقم mono كبير بلون الهوية (01 و02…) يدخل، وبعدين عنوان الجزء يطلع جنبه أو تحته بعد 0.15 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-191.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-191.

#### `al-lgo-191-slow` — Chapter Title · Slow
**عنوان فصل · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-191*

Variant of M-191: أبطأ بـ 60%

**Spec (EN):** A large accent mono number (01, 02…) slides in, then the chapter title fades up beside or under it 0.15s later.

**Spec (AR):** رقم mono كبير بلون الهوية (01 و02…) يدخل، وبعدين عنوان الجزء يطلع جنبه أو تحته بعد 0.15 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-191.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-191.

#### `al-lgo-191-gold` — Chapter Title · Gold
**عنوان فصل · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-191*

Variant of M-191: نسخة ذهبية فاخرة

**Spec (EN):** A large accent mono number (01, 02…) slides in, then the chapter title fades up beside or under it 0.15s later.

**Spec (AR):** رقم mono كبير بلون الهوية (01 و02…) يدخل، وبعدين عنوان الجزء يطلع جنبه أو تحته بعد 0.15 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-191.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-191.

#### `al-lgo-191-boxed` — Chapter Title · Boxed
**عنوان فصل · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.6s*

*Original: M-191*

Variant of M-191: النص داخل صندوق ملون

**Spec (EN):** A large accent mono number (01, 02…) slides in, then the chapter title fades up beside or under it 0.15s later.

**Spec (AR):** رقم mono كبير بلون الهوية (01 و02…) يدخل، وبعدين عنوان الجزء يطلع جنبه أو تحته بعد 0.15 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-191.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-191.

#### `al-lgo-192-fast` — Price Tag · Fast
**بطاقة سعر · سريع**

*accent · any · depth · easing: easeOutBack · 0.6s*

*Original: M-192*

Variant of M-192: أسرع بـ 40%

**Spec (EN):** A yellow tag-shaped label swings in from its hole side, from -90° to +12°, -6° and settles over 0.6s.

**Spec (AR):** ملصق أصفر بشكل بطاقة سعر يتأرجح من جهة الفتحة، من -90 درجة لـ +12 و-6 ويستقر خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-192.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-192.

#### `al-lgo-192-slow` — Price Tag · Slow
**بطاقة سعر · بطيء**

*accent · any · depth · easing: easeOutBack · 0.6s*

*Original: M-192*

Variant of M-192: أبطأ بـ 60%

**Spec (EN):** A yellow tag-shaped label swings in from its hole side, from -90° to +12°, -6° and settles over 0.6s.

**Spec (AR):** ملصق أصفر بشكل بطاقة سعر يتأرجح من جهة الفتحة، من -90 درجة لـ +12 و-6 ويستقر خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-192.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-192.

#### `al-lgo-192-gold` — Price Tag · Gold
**بطاقة سعر · ذهبي**

*accent · any · depth · easing: easeOutBack · 0.6s*

*Original: M-192*

Variant of M-192: نسخة ذهبية فاخرة

**Spec (EN):** A yellow tag-shaped label swings in from its hole side, from -90° to +12°, -6° and settles over 0.6s.

**Spec (AR):** ملصق أصفر بشكل بطاقة سعر يتأرجح من جهة الفتحة، من -90 درجة لـ +12 و-6 ويستقر خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-192.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-192.

#### `al-lgo-192-boxed` — Price Tag · Boxed
**بطاقة سعر · صندوق**

*accent · any · depth · easing: easeOutBack · 0.6s*

*Original: M-192*

Variant of M-192: النص داخل صندوق ملون

**Spec (EN):** A yellow tag-shaped label swings in from its hole side, from -90° to +12°, -6° and settles over 0.6s.

**Spec (AR):** ملصق أصفر بشكل بطاقة سعر يتأرجح من جهة الفتحة، من -90 درجة لـ +12 و-6 ويستقر خلال 0.6 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-192.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-192.

#### `al-lgo-193-fast` — Progress Bar · Fast
**شريط تقدم · سريع**

*accent · any · timeline · easing: easeInOutCubic · 1.2s*

*Original: M-193*

Variant of M-193: أسرع بـ 40%

**Spec (EN):** A rounded track fills with an accent gradient from the reading-start side over 1.2s while a percentage counts up above it.

**Spec (AR):** مسار بزوايا دائرية يتعبى بتدرج بلون الهوية من جهة بداية القراءة خلال 1.2 ثانية، وفوقه نسبة تعد.

**When to use:**
- EN: Use when you need a fast version of M-193.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-193.

#### `al-lgo-193-slow` — Progress Bar · Slow
**شريط تقدم · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 1.2s*

*Original: M-193*

Variant of M-193: أبطأ بـ 60%

**Spec (EN):** A rounded track fills with an accent gradient from the reading-start side over 1.2s while a percentage counts up above it.

**Spec (AR):** مسار بزوايا دائرية يتعبى بتدرج بلون الهوية من جهة بداية القراءة خلال 1.2 ثانية، وفوقه نسبة تعد.

**When to use:**
- EN: Use when you need a slow version of M-193.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-193.

#### `al-lgo-193-gold` — Progress Bar · Gold
**شريط تقدم · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 1.2s*

*Original: M-193*

Variant of M-193: نسخة ذهبية فاخرة

**Spec (EN):** A rounded track fills with an accent gradient from the reading-start side over 1.2s while a percentage counts up above it.

**Spec (AR):** مسار بزوايا دائرية يتعبى بتدرج بلون الهوية من جهة بداية القراءة خلال 1.2 ثانية، وفوقه نسبة تعد.

**When to use:**
- EN: Use when you need a gold version of M-193.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-193.

#### `al-lgo-193-boxed` — Progress Bar · Boxed
**شريط تقدم · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 1.2s*

*Original: M-193*

Variant of M-193: النص داخل صندوق ملون

**Spec (EN):** A rounded track fills with an accent gradient from the reading-start side over 1.2s while a percentage counts up above it.

**Spec (AR):** مسار بزوايا دائرية يتعبى بتدرج بلون الهوية من جهة بداية القراءة خلال 1.2 ثانية، وفوقه نسبة تعد.

**When to use:**
- EN: Use when you need a boxed version of M-193.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-193.

#### `al-lgo-194-fast` — Checklist Tick · Fast
**قائمة تتصحح · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.3s per tick · 0.5s stagger*

*Original: M-194*

Variant of M-194: أسرع بـ 40%

**Spec (EN):** Each list item has a box; a mint check mark draws inside it (0.3s), items ticking 0.5s apart.

**Spec (AR):** كل بند في القائمة له مربع، وعلامة صح نعناعية تنرسم داخله (0.3 ثانية)، والبنود تتصحح وبينهم 0.5 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-194.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-194.

#### `al-lgo-194-slow` — Checklist Tick · Slow
**قائمة تتصحح · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.3s per tick · 0.5s stagger*

*Original: M-194*

Variant of M-194: أبطأ بـ 60%

**Spec (EN):** Each list item has a box; a mint check mark draws inside it (0.3s), items ticking 0.5s apart.

**Spec (AR):** كل بند في القائمة له مربع، وعلامة صح نعناعية تنرسم داخله (0.3 ثانية)، والبنود تتصحح وبينهم 0.5 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-194.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-194.

#### `al-lgo-194-gold` — Checklist Tick · Gold
**قائمة تتصحح · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.3s per tick · 0.5s stagger*

*Original: M-194*

Variant of M-194: نسخة ذهبية فاخرة

**Spec (EN):** Each list item has a box; a mint check mark draws inside it (0.3s), items ticking 0.5s apart.

**Spec (AR):** كل بند في القائمة له مربع، وعلامة صح نعناعية تنرسم داخله (0.3 ثانية)، والبنود تتصحح وبينهم 0.5 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-194.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-194.

#### `al-lgo-194-boxed` — Checklist Tick · Boxed
**قائمة تتصحح · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.3s per tick · 0.5s stagger*

*Original: M-194*

Variant of M-194: النص داخل صندوق ملون

**Spec (EN):** Each list item has a box; a mint check mark draws inside it (0.3s), items ticking 0.5s apart.

**Spec (AR):** كل بند في القائمة له مربع، وعلامة صح نعناعية تنرسم داخله (0.3 ثانية)، والبنود تتصحح وبينهم 0.5 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-194.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-194.

#### `al-lgo-195-fast` — Step Numbers · Fast
**خطوات مرقمة · سريع**

*accent · any · timeline · easing: easeOutBack · 0.25s per step*

*Original: M-195*

Variant of M-195: أسرع بـ 40%

**Spec (EN):** Circular accent number badges pop in one by one, 0.4s apart, while a line draws behind them connecting each step.

**Spec (AR):** دواير أرقام بلون الهوية تنط وحدة وحدة وبينهم 0.4 ثانية، وخط ينرسم وراهم يوصل الخطوات.

**When to use:**
- EN: Use when you need a fast version of M-195.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-195.

#### `al-lgo-195-slow` — Step Numbers · Slow
**خطوات مرقمة · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.25s per step*

*Original: M-195*

Variant of M-195: أبطأ بـ 60%

**Spec (EN):** Circular accent number badges pop in one by one, 0.4s apart, while a line draws behind them connecting each step.

**Spec (AR):** دواير أرقام بلون الهوية تنط وحدة وحدة وبينهم 0.4 ثانية، وخط ينرسم وراهم يوصل الخطوات.

**When to use:**
- EN: Use when you need a slow version of M-195.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-195.

#### `al-lgo-195-gold` — Step Numbers · Gold
**خطوات مرقمة · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.25s per step*

*Original: M-195*

Variant of M-195: نسخة ذهبية فاخرة

**Spec (EN):** Circular accent number badges pop in one by one, 0.4s apart, while a line draws behind them connecting each step.

**Spec (AR):** دواير أرقام بلون الهوية تنط وحدة وحدة وبينهم 0.4 ثانية، وخط ينرسم وراهم يوصل الخطوات.

**When to use:**
- EN: Use when you need a gold version of M-195.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-195.

#### `al-lgo-195-boxed` — Step Numbers · Boxed
**خطوات مرقمة · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.25s per step*

*Original: M-195*

Variant of M-195: النص داخل صندوق ملون

**Spec (EN):** Circular accent number badges pop in one by one, 0.4s apart, while a line draws behind them connecting each step.

**Spec (AR):** دواير أرقام بلون الهوية تنط وحدة وحدة وبينهم 0.4 ثانية، وخط ينرسم وراهم يوصل الخطوات.

**When to use:**
- EN: Use when you need a boxed version of M-195.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-195.

#### `al-lgo-196-fast` — Quote Card · Fast
**بطاقة اقتباس · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.8s*

*Original: M-196*

Variant of M-196: أسرع بـ 40%

**Spec (EN):** A large accent quote mark scales in, then the quote text fades up line by line, then the author name fades in, each 0.2s apart.

**Spec (AR):** علامة اقتباس كبيرة بلون الهوية تكبر وتدخل، وبعدين نص الاقتباس يطلع سطر سطر، وبعدين اسم القائل يظهر، وبين كل وحدة 0.2 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-196.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-196.

#### `al-lgo-196-slow` — Quote Card · Slow
**بطاقة اقتباس · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.8s*

*Original: M-196*

Variant of M-196: أبطأ بـ 60%

**Spec (EN):** A large accent quote mark scales in, then the quote text fades up line by line, then the author name fades in, each 0.2s apart.

**Spec (AR):** علامة اقتباس كبيرة بلون الهوية تكبر وتدخل، وبعدين نص الاقتباس يطلع سطر سطر، وبعدين اسم القائل يظهر، وبين كل وحدة 0.2 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-196.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-196.

#### `al-lgo-196-gold` — Quote Card · Gold
**بطاقة اقتباس · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.8s*

*Original: M-196*

Variant of M-196: نسخة ذهبية فاخرة

**Spec (EN):** A large accent quote mark scales in, then the quote text fades up line by line, then the author name fades in, each 0.2s apart.

**Spec (AR):** علامة اقتباس كبيرة بلون الهوية تكبر وتدخل، وبعدين نص الاقتباس يطلع سطر سطر، وبعدين اسم القائل يظهر، وبين كل وحدة 0.2 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-196.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-196.

#### `al-lgo-196-boxed` — Quote Card · Boxed
**بطاقة اقتباس · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.8s*

*Original: M-196*

Variant of M-196: النص داخل صندوق ملون

**Spec (EN):** A large accent quote mark scales in, then the quote text fades up line by line, then the author name fades in, each 0.2s apart.

**Spec (AR):** علامة اقتباس كبيرة بلون الهوية تكبر وتدخل، وبعدين نص الاقتباس يطلع سطر سطر، وبعدين اسم القائل يظهر، وبين كل وحدة 0.2 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-196.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-196.

#### `al-lgo-197-fast` — Stat Bars · Fast
**أعمدة بيانات · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.6s · 0.1s stagger*

*Original: M-197*

Variant of M-197: أسرع بـ 40%

**Spec (EN):** Vertical bars grow from the baseline to their values over 0.6s, each starting 0.1s after the previous one, with alternating brand colors.

**Spec (AR):** أعمدة عمودية تطلع من الخط الأساسي لقيمها خلال 0.6 ثانية، وكل عمود يبدأ بعد اللي قبله بـ 0.1 ثانية، بألوان الهوية بالتناوب.

**When to use:**
- EN: Use when you need a fast version of M-197.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-197.

#### `al-lgo-197-slow` — Stat Bars · Slow
**أعمدة بيانات · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.6s · 0.1s stagger*

*Original: M-197*

Variant of M-197: أبطأ بـ 60%

**Spec (EN):** Vertical bars grow from the baseline to their values over 0.6s, each starting 0.1s after the previous one, with alternating brand colors.

**Spec (AR):** أعمدة عمودية تطلع من الخط الأساسي لقيمها خلال 0.6 ثانية، وكل عمود يبدأ بعد اللي قبله بـ 0.1 ثانية، بألوان الهوية بالتناوب.

**When to use:**
- EN: Use when you need a slow version of M-197.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-197.

#### `al-lgo-197-gold` — Stat Bars · Gold
**أعمدة بيانات · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.6s · 0.1s stagger*

*Original: M-197*

Variant of M-197: نسخة ذهبية فاخرة

**Spec (EN):** Vertical bars grow from the baseline to their values over 0.6s, each starting 0.1s after the previous one, with alternating brand colors.

**Spec (AR):** أعمدة عمودية تطلع من الخط الأساسي لقيمها خلال 0.6 ثانية، وكل عمود يبدأ بعد اللي قبله بـ 0.1 ثانية، بألوان الهوية بالتناوب.

**When to use:**
- EN: Use when you need a gold version of M-197.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-197.

#### `al-lgo-197-boxed` — Stat Bars · Boxed
**أعمدة بيانات · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.6s · 0.1s stagger*

*Original: M-197*

Variant of M-197: النص داخل صندوق ملون

**Spec (EN):** Vertical bars grow from the baseline to their values over 0.6s, each starting 0.1s after the previous one, with alternating brand colors.

**Spec (AR):** أعمدة عمودية تطلع من الخط الأساسي لقيمها خلال 0.6 ثانية، وكل عمود يبدأ بعد اللي قبله بـ 0.1 ثانية، بألوان الهوية بالتناوب.

**When to use:**
- EN: Use when you need a boxed version of M-197.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-197.

#### `al-lgo-198-fast` — Pie Fill · Fast
**دائرة نسبة · سريع**

*accent · any · timeline · easing: easeOutCubic · 1s*

*Original: M-198*

Variant of M-198: أسرع بـ 40%

**Spec (EN):** A thick ring fills clockwise with the accent color from 0 to the target percentage over 1s, with the number in the middle.

**Spec (AR):** حلقة عريضة تتعبى مع عقارب الساعة بلون الهوية من 0 لين النسبة المطلوبة خلال ثانية، والرقم بالنص.

**When to use:**
- EN: Use when you need a fast version of M-198.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-198.

#### `al-lgo-198-slow` — Pie Fill · Slow
**دائرة نسبة · بطيء**

*accent · any · timeline · easing: easeOutCubic · 1s*

*Original: M-198*

Variant of M-198: أبطأ بـ 60%

**Spec (EN):** A thick ring fills clockwise with the accent color from 0 to the target percentage over 1s, with the number in the middle.

**Spec (AR):** حلقة عريضة تتعبى مع عقارب الساعة بلون الهوية من 0 لين النسبة المطلوبة خلال ثانية، والرقم بالنص.

**When to use:**
- EN: Use when you need a slow version of M-198.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-198.

#### `al-lgo-198-gold` — Pie Fill · Gold
**دائرة نسبة · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 1s*

*Original: M-198*

Variant of M-198: نسخة ذهبية فاخرة

**Spec (EN):** A thick ring fills clockwise with the accent color from 0 to the target percentage over 1s, with the number in the middle.

**Spec (AR):** حلقة عريضة تتعبى مع عقارب الساعة بلون الهوية من 0 لين النسبة المطلوبة خلال ثانية، والرقم بالنص.

**When to use:**
- EN: Use when you need a gold version of M-198.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-198.

#### `al-lgo-198-boxed` — Pie Fill · Boxed
**دائرة نسبة · صندوق**

*accent · any · timeline · easing: easeOutCubic · 1s*

*Original: M-198*

Variant of M-198: النص داخل صندوق ملون

**Spec (EN):** A thick ring fills clockwise with the accent color from 0 to the target percentage over 1s, with the number in the middle.

**Spec (AR):** حلقة عريضة تتعبى مع عقارب الساعة بلون الهوية من 0 لين النسبة المطلوبة خلال ثانية، والرقم بالنص.

**When to use:**
- EN: Use when you need a boxed version of M-198.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-198.

#### `al-lgo-199-fast` — Map Pin Drop · Fast
**دبوس موقع · سريع**

*accent · any · timeline · easing: easeOutBounce · 0.5s*

*Original: M-199*

Variant of M-199: أسرع بـ 40%

**Spec (EN):** A pin falls from above, lands with a small bounce, and a ripple ring spreads under it on impact, with the place name fading in below.

**Spec (AR):** دبوس يطيح من فوق، ينزل مع ارتداد خفيف، ودائرة تموج تتوسع تحته لحظة النزول، واسم المكان يظهر تحته.

**When to use:**
- EN: Use when you need a fast version of M-199.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-199.

#### `al-lgo-199-slow` — Map Pin Drop · Slow
**دبوس موقع · بطيء**

*accent · any · timeline · easing: easeOutBounce · 0.5s*

*Original: M-199*

Variant of M-199: أبطأ بـ 60%

**Spec (EN):** A pin falls from above, lands with a small bounce, and a ripple ring spreads under it on impact, with the place name fading in below.

**Spec (AR):** دبوس يطيح من فوق، ينزل مع ارتداد خفيف، ودائرة تموج تتوسع تحته لحظة النزول، واسم المكان يظهر تحته.

**When to use:**
- EN: Use when you need a slow version of M-199.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-199.

#### `al-lgo-199-gold` — Map Pin Drop · Gold
**دبوس موقع · ذهبي**

*accent · any · timeline · easing: easeOutBounce · 0.5s*

*Original: M-199*

Variant of M-199: نسخة ذهبية فاخرة

**Spec (EN):** A pin falls from above, lands with a small bounce, and a ripple ring spreads under it on impact, with the place name fading in below.

**Spec (AR):** دبوس يطيح من فوق، ينزل مع ارتداد خفيف، ودائرة تموج تتوسع تحته لحظة النزول، واسم المكان يظهر تحته.

**When to use:**
- EN: Use when you need a gold version of M-199.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-199.

#### `al-lgo-199-boxed` — Map Pin Drop · Boxed
**دبوس موقع · صندوق**

*accent · any · timeline · easing: easeOutBounce · 0.5s*

*Original: M-199*

Variant of M-199: النص داخل صندوق ملون

**Spec (EN):** A pin falls from above, lands with a small bounce, and a ripple ring spreads under it on impact, with the place name fading in below.

**Spec (AR):** دبوس يطيح من فوق، ينزل مع ارتداد خفيف، ودائرة تموج تتوسع تحته لحظة النزول، واسم المكان يظهر تحته.

**When to use:**
- EN: Use when you need a boxed version of M-199.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-199.

#### `al-lgo-200-fast` — Signature Write · Fast
**توقيع ينكتب · سريع**

*accent · calm · timeline · easing: easeInOutSine · 1.5s*

*Original: M-200*

Variant of M-200: أسرع بـ 40%

**Spec (EN):** Animate a handwritten signature path stroke from start to end over about 1.5s with a slight ease, as if written live. Hold, then fade.

**Spec (AR):** حرّك مسار توقيع بخط اليد من بدايته لآخره خلال تقريباً 1.5 ثانية بنعومة، كأنه ينكتب الحين. ثبّته، وبعدين خله يختفي.

**When to use:**
- EN: Use when you need a fast version of M-200.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-200.

#### `al-lgo-200-slow` — Signature Write · Slow
**توقيع ينكتب · بطيء**

*accent · calm · timeline · easing: easeInOutSine · 1.5s*

*Original: M-200*

Variant of M-200: أبطأ بـ 60%

**Spec (EN):** Animate a handwritten signature path stroke from start to end over about 1.5s with a slight ease, as if written live. Hold, then fade.

**Spec (AR):** حرّك مسار توقيع بخط اليد من بدايته لآخره خلال تقريباً 1.5 ثانية بنعومة، كأنه ينكتب الحين. ثبّته، وبعدين خله يختفي.

**When to use:**
- EN: Use when you need a slow version of M-200.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-200.

#### `al-lgo-200-gold` — Signature Write · Gold
**توقيع ينكتب · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · 1.5s*

*Original: M-200*

Variant of M-200: نسخة ذهبية فاخرة

**Spec (EN):** Animate a handwritten signature path stroke from start to end over about 1.5s with a slight ease, as if written live. Hold, then fade.

**Spec (AR):** حرّك مسار توقيع بخط اليد من بدايته لآخره خلال تقريباً 1.5 ثانية بنعومة، كأنه ينكتب الحين. ثبّته، وبعدين خله يختفي.

**When to use:**
- EN: Use when you need a gold version of M-200.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-200.

#### `al-lgo-200-boxed` — Signature Write · Boxed
**توقيع ينكتب · صندوق**

*accent · calm · timeline · easing: easeInOutSine · 1.5s*

*Original: M-200*

Variant of M-200: النص داخل صندوق ملون

**Spec (EN):** Animate a handwritten signature path stroke from start to end over about 1.5s with a slight ease, as if written live. Hold, then fade.

**Spec (AR):** حرّك مسار توقيع بخط اليد من بدايته لآخره خلال تقريباً 1.5 ثانية بنعومة، كأنه ينكتب الحين. ثبّته، وبعدين خله يختفي.

**When to use:**
- EN: Use when you need a boxed version of M-200.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-200.

### Person FX (تأثيرات الشخص) — 65 motions

#### `al-per-201` — Text Behind Person
**نص ورا الشخص**

*workhorse · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-201*

A huge title behind your head with you in front, a top trend.

**Spec (EN):** Place a very large bold title on a layer between the background and the person (use the person matte), so the head overlaps the letters. The title rises in with M-004 style.

**Spec (AR):** حط عنوان كبير جداً وعريض على طبقة بين الخلفية والشخص (باستخدام قناع الشخص)، فيكون الراس قدام الحروف. والعنوان يطلع بحركة مثل M-004.

**When to use:**
- EN: A huge title behind your head with you in front, a top trend.
- AR: عنوان كبير ورا راسك وانت قدامه، من أشهر الترندات.

#### `al-per-202` — Color Pop
**ألوان عليك بس**

*workhorse · calm · depth · easing: easeInOutSine · 0.4s*

*Original: M-202*

The background goes black and white while you stay in color.

**Spec (EN):** Using the person matte, desaturate only the background to 0% and darken it slightly over 0.4s; the person keeps full color.

**Spec (AR):** باستخدام قناع الشخص، شيل ألوان الخلفية بس لين 0% وغمّقها شوي خلال 0.4 ثانية، والشخص يبقى بألوانه كاملة.

**When to use:**
- EN: The background goes black and white while you stay in color.
- AR: الخلفية أبيض وأسود وانت بالألوان.

#### `al-per-203` — Echo Trail
**أثر حركة الشخص**

*workhorse · calm · timeline · easing: easeInOutSine · loop*

*Original: M-203*

Transparent copies of you trail behind your movement.

**Spec (EN):** Duplicate the person layer 2–4 times, each delayed by 3–5 frames and at decreasing opacity (30%, 15%…), so movement leaves an echo trail.

**Spec (AR):** كرر طبقة الشخص 2 إلى 4 مرات، كل نسخة متأخرة 3 إلى 5 فريمات وشفافيتها تقل (30% ثم 15%…)، فالحركة تخلي وراها أثر.

**When to use:**
- EN: Transparent copies of you trail behind your movement.
- AR: نسخ شفافة منك تلحقك وانت تتحرك.

#### `al-per-204` — Clone Trio
**ثلاث نسخ منك**

*workhorse · high · depth · easing: easeOutBack · 0.3s per clone*

*Original: M-204*

Multiple copies of you in the same shot.

**Spec (EN):** Composite 2–3 mattes of the person from different takes side by side; each clone pops in (scale 90% to 100% with fade) 0.3s apart.

**Spec (AR):** ركّب 2 إلى 3 أقنعة للشخص من لقطات مختلفة جنب بعض، وكل نسخة تنط (من 90% لـ 100% مع ظهور) وبينهم 0.3 ثانية.

**When to use:**
- EN: Multiple copies of you in the same shot.
- AR: أكثر من نسخة منك بنفس اللقطة.

#### `al-per-205` — Doodle Outline
**خربشات حولك**

*workhorse · any · timeline · easing: easeInOutCubic · 0.8s draw*

*Original: M-205*

Animated hand-drawn doodles around the person.

**Spec (EN):** Draw loose white hand-drawn strokes (a crown, sparks, an outline arc) around the head that write on over 0.8s and wiggle slightly while held.

**Spec (AR):** ارسم خطوط يد بيضا حرة (تاج، شرار، قوس حول الراس) تنرسم حول الراس خلال 0.8 ثانية وتتمايل شوي وهي ثابتة.

**When to use:**
- EN: Animated hand-drawn doodles around the person.
- AR: رسومات يد متحركة حول الشخص، ستايل شبابي.

#### `al-per-206` — Sticker Cutout
**الشخص ملصق**

*workhorse · high · timeline · easing: easeOutBack · 0.4s*

*Original: M-206*

The person becomes a white-bordered sticker that pops.

**Spec (EN):** Using the person matte, add a thick white outline (about 1% of the width) and a soft drop shadow, then pop the sticker in with a slight tilt (scale 0 to 108% to 100%).

**Spec (AR):** باستخدام قناع الشخص، حط حدود بيضا عريضة (تقريباً 1% من العرض) وظل ناعم، وبعدين خل الملصق ينط مع ميلان خفيف (من 0 لـ 108% لـ 100%).

**When to use:**
- EN: The person becomes a white-bordered sticker that pops.
- AR: الشخص يصير ملصق بإطار أبيض وينط.

#### `al-per-207` — Pop-Out Frame
**الشخص يطلع من الإطار**

*workhorse · high · depth · easing: easeOutBack · 0.5s*

*Original: M-207*

The person breaks out of a frame, a 3D feel.

**Spec (EN):** A rounded frame shows the background; the person matte is layered above it so the head sticks out over the top edge of the frame. The frame scales in first.

**Spec (AR):** إطار بزوايا دائرية يعرض الخلفية، وقناع الشخص فوقه بحيث الراس يطلع برا الحافة الفوق للإطار. والإطار يكبر ويدخل أول.

**When to use:**
- EN: The person breaks out of a frame, a 3D feel.
- AR: الشخص يطلع راسه برا الإطار، إحساس 3D.

#### `al-per-208` — Portrait Mode
**وضع البورتريه**

*workhorse · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-208*

A blurred background with the person sharp, like a phone portrait.

**Spec (EN):** Using the person matte, blur only the background to about 1.5% over 0.5s while the person stays sharp.

**Spec (AR):** باستخدام قناع الشخص، ضبّب الخلفية بس لـ تقريباً 1.5% خلال 0.5 ثانية والشخص يبقى واضح.

**When to use:**
- EN: A blurred background with the person sharp, like a phone portrait.
- AR: خلفية مضببة والشخص واضح، مثل كاميرا الجوال.

#### `al-per-209` — Silhouette Fill
**الشخص يتلون لون واحد**

*workhorse · any · timeline · easing: easeOutQuad · 0.3s*

*Original: M-209*

The person turns into a solid brand-color silhouette, poster style.

**Spec (EN):** Using the person matte, fill the person with a flat accent color (keep the matte edge soft) and fade it in over 0.3s on a beat.

**Spec (AR):** باستخدام قناع الشخص، عبّي الشخص بلون الهوية لون واحد (وخل حافة القناع ناعمة)، وخله يظهر خلال 0.3 ثانية على الإيقاع.

**When to use:**
- EN: The person turns into a solid brand-color silhouette, poster style.
- AR: الشخص يصير ظل بلون الهوية، ستايل البوستر.

#### `al-per-210` — Neon Outline
**حدود نيون للشخص**

*workhorse · any · timeline · easing: steps · loop flicker*

*Original: M-210*

A glowing neon edge traced around the person.

**Spec (EN):** Trace the person matte edge with a 0.8% mint line plus a wide glow, and flicker it on like neon (see M-056).

**Spec (AR):** ارسم حافة قناع الشخص بخط نعناعي 0.8% مع توهج عريض، وخله يشتغل ويرمش مثل النيون (شوف M-056).

**When to use:**
- EN: A glowing neon edge traced around the person.
- AR: حدود مضيئة حول الشخص ستايل النيون.

#### `al-per-211` — Spotlight Follow
**ضوء يتبع الشخص**

*workhorse · calm · camera · easing: easeInOutSine · loop*

*Original: M-211*

Everything goes dark except a light circle that follows you.

**Spec (EN):** Darken the frame about 85% except a soft circle around the person; the circle tracks the head position every frame.

**Spec (AR):** غمّق الشاشة تقريباً 85% إلا دائرة ناعمة حول الشخص، والدائرة تتبع مكان الراس كل فريم.

**When to use:**
- EN: Everything goes dark except a light circle that follows you.
- AR: كل شي غامق إلا دائرة ضوء تتبعك.

#### `al-per-212` — Halftone Person
**الشخص بنقاط**

*workhorse · any · timeline · easing: easeOutQuad · 0.4s*

*Original: M-212*

The person rendered in halftone dots like old print.

**Spec (EN):** Inside the person matte, overlay an accent halftone dot pattern (dot size tied to brightness) with a multiply blend.

**Spec (AR):** داخل قناع الشخص، حط نقش نقاط بلون الهوية (حجم النقطة على حسب الإضاءة) بدمج multiply.

**When to use:**
- EN: The person rendered in halftone dots like old print.
- AR: الشخص يتحول لنقاط مثل الطباعة القديمة.

#### `al-per-213` — Background Flash Swap
**الخلفية تتبدل على الإيقاع**

*workhorse · any · depth · easing: cut · per beat*

*Original: M-213*

The background color flips on every beat while you stay.

**Spec (EN):** Using the person matte, replace the background with a solid color that changes on every beat (cycle 3–4 brand colors).

**Spec (AR):** باستخدام قناع الشخص، بدّل الخلفية بلون واحد يتغير مع كل ضربة إيقاع (لف على 3 إلى 4 ألوان من الهوية).

**When to use:**
- EN: The background color flips on every beat while you stay.
- AR: لون الخلفية يتبدل مع كل ضربة والشخص ثابت.

#### `al-per-201-fast` — Text Behind Person · Fast
**نص ورا الشخص · سريع**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-201*

Variant of M-201: أسرع بـ 40%

**Spec (EN):** Place a very large bold title on a layer between the background and the person (use the person matte), so the head overlaps the letters. The title rises in with M-004 style.

**Spec (AR):** حط عنوان كبير جداً وعريض على طبقة بين الخلفية والشخص (باستخدام قناع الشخص)، فيكون الراس قدام الحروف. والعنوان يطلع بحركة مثل M-004.

**When to use:**
- EN: Use when you need a fast version of M-201.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-201.

#### `al-per-201-slow` — Text Behind Person · Slow
**نص ورا الشخص · بطيء**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-201*

Variant of M-201: أبطأ بـ 60%

**Spec (EN):** Place a very large bold title on a layer between the background and the person (use the person matte), so the head overlaps the letters. The title rises in with M-004 style.

**Spec (AR):** حط عنوان كبير جداً وعريض على طبقة بين الخلفية والشخص (باستخدام قناع الشخص)، فيكون الراس قدام الحروف. والعنوان يطلع بحركة مثل M-004.

**When to use:**
- EN: Use when you need a slow version of M-201.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-201.

#### `al-per-201-gold` — Text Behind Person · Gold
**نص ورا الشخص · ذهبي**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-201*

Variant of M-201: نسخة ذهبية فاخرة

**Spec (EN):** Place a very large bold title on a layer between the background and the person (use the person matte), so the head overlaps the letters. The title rises in with M-004 style.

**Spec (AR):** حط عنوان كبير جداً وعريض على طبقة بين الخلفية والشخص (باستخدام قناع الشخص)، فيكون الراس قدام الحروف. والعنوان يطلع بحركة مثل M-004.

**When to use:**
- EN: Use when you need a gold version of M-201.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-201.

#### `al-per-201-boxed` — Text Behind Person · Boxed
**نص ورا الشخص · صندوق**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-201*

Variant of M-201: النص داخل صندوق ملون

**Spec (EN):** Place a very large bold title on a layer between the background and the person (use the person matte), so the head overlaps the letters. The title rises in with M-004 style.

**Spec (AR):** حط عنوان كبير جداً وعريض على طبقة بين الخلفية والشخص (باستخدام قناع الشخص)، فيكون الراس قدام الحروف. والعنوان يطلع بحركة مثل M-004.

**When to use:**
- EN: Use when you need a boxed version of M-201.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-201.

#### `al-per-202-fast` — Color Pop · Fast
**ألوان عليك بس · سريع**

*accent · calm · depth · easing: easeInOutSine · 0.4s*

*Original: M-202*

Variant of M-202: أسرع بـ 40%

**Spec (EN):** Using the person matte, desaturate only the background to 0% and darken it slightly over 0.4s; the person keeps full color.

**Spec (AR):** باستخدام قناع الشخص، شيل ألوان الخلفية بس لين 0% وغمّقها شوي خلال 0.4 ثانية، والشخص يبقى بألوانه كاملة.

**When to use:**
- EN: Use when you need a fast version of M-202.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-202.

#### `al-per-202-slow` — Color Pop · Slow
**ألوان عليك بس · بطيء**

*accent · calm · depth · easing: easeInOutSine · 0.4s*

*Original: M-202*

Variant of M-202: أبطأ بـ 60%

**Spec (EN):** Using the person matte, desaturate only the background to 0% and darken it slightly over 0.4s; the person keeps full color.

**Spec (AR):** باستخدام قناع الشخص، شيل ألوان الخلفية بس لين 0% وغمّقها شوي خلال 0.4 ثانية، والشخص يبقى بألوانه كاملة.

**When to use:**
- EN: Use when you need a slow version of M-202.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-202.

#### `al-per-202-gold` — Color Pop · Gold
**ألوان عليك بس · ذهبي**

*accent · calm · depth · easing: easeInOutSine · 0.4s*

*Original: M-202*

Variant of M-202: نسخة ذهبية فاخرة

**Spec (EN):** Using the person matte, desaturate only the background to 0% and darken it slightly over 0.4s; the person keeps full color.

**Spec (AR):** باستخدام قناع الشخص، شيل ألوان الخلفية بس لين 0% وغمّقها شوي خلال 0.4 ثانية، والشخص يبقى بألوانه كاملة.

**When to use:**
- EN: Use when you need a gold version of M-202.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-202.

#### `al-per-202-boxed` — Color Pop · Boxed
**ألوان عليك بس · صندوق**

*accent · calm · depth · easing: easeInOutSine · 0.4s*

*Original: M-202*

Variant of M-202: النص داخل صندوق ملون

**Spec (EN):** Using the person matte, desaturate only the background to 0% and darken it slightly over 0.4s; the person keeps full color.

**Spec (AR):** باستخدام قناع الشخص، شيل ألوان الخلفية بس لين 0% وغمّقها شوي خلال 0.4 ثانية، والشخص يبقى بألوانه كاملة.

**When to use:**
- EN: Use when you need a boxed version of M-202.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-202.

#### `al-per-203-fast` — Echo Trail · Fast
**أثر حركة الشخص · سريع**

*accent · calm · timeline · easing: easeInOutSine · loop*

*Original: M-203*

Variant of M-203: أسرع بـ 40%

**Spec (EN):** Duplicate the person layer 2–4 times, each delayed by 3–5 frames and at decreasing opacity (30%, 15%…), so movement leaves an echo trail.

**Spec (AR):** كرر طبقة الشخص 2 إلى 4 مرات، كل نسخة متأخرة 3 إلى 5 فريمات وشفافيتها تقل (30% ثم 15%…)، فالحركة تخلي وراها أثر.

**When to use:**
- EN: Use when you need a fast version of M-203.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-203.

#### `al-per-203-slow` — Echo Trail · Slow
**أثر حركة الشخص · بطيء**

*accent · calm · timeline · easing: easeInOutSine · loop*

*Original: M-203*

Variant of M-203: أبطأ بـ 60%

**Spec (EN):** Duplicate the person layer 2–4 times, each delayed by 3–5 frames and at decreasing opacity (30%, 15%…), so movement leaves an echo trail.

**Spec (AR):** كرر طبقة الشخص 2 إلى 4 مرات، كل نسخة متأخرة 3 إلى 5 فريمات وشفافيتها تقل (30% ثم 15%…)، فالحركة تخلي وراها أثر.

**When to use:**
- EN: Use when you need a slow version of M-203.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-203.

#### `al-per-203-gold` — Echo Trail · Gold
**أثر حركة الشخص · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · loop*

*Original: M-203*

Variant of M-203: نسخة ذهبية فاخرة

**Spec (EN):** Duplicate the person layer 2–4 times, each delayed by 3–5 frames and at decreasing opacity (30%, 15%…), so movement leaves an echo trail.

**Spec (AR):** كرر طبقة الشخص 2 إلى 4 مرات، كل نسخة متأخرة 3 إلى 5 فريمات وشفافيتها تقل (30% ثم 15%…)، فالحركة تخلي وراها أثر.

**When to use:**
- EN: Use when you need a gold version of M-203.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-203.

#### `al-per-203-boxed` — Echo Trail · Boxed
**أثر حركة الشخص · صندوق**

*accent · calm · timeline · easing: easeInOutSine · loop*

*Original: M-203*

Variant of M-203: النص داخل صندوق ملون

**Spec (EN):** Duplicate the person layer 2–4 times, each delayed by 3–5 frames and at decreasing opacity (30%, 15%…), so movement leaves an echo trail.

**Spec (AR):** كرر طبقة الشخص 2 إلى 4 مرات، كل نسخة متأخرة 3 إلى 5 فريمات وشفافيتها تقل (30% ثم 15%…)، فالحركة تخلي وراها أثر.

**When to use:**
- EN: Use when you need a boxed version of M-203.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-203.

#### `al-per-204-fast` — Clone Trio · Fast
**ثلاث نسخ منك · سريع**

*accent · any · depth · easing: easeOutBack · 0.3s per clone*

*Original: M-204*

Variant of M-204: أسرع بـ 40%

**Spec (EN):** Composite 2–3 mattes of the person from different takes side by side; each clone pops in (scale 90% to 100% with fade) 0.3s apart.

**Spec (AR):** ركّب 2 إلى 3 أقنعة للشخص من لقطات مختلفة جنب بعض، وكل نسخة تنط (من 90% لـ 100% مع ظهور) وبينهم 0.3 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-204.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-204.

#### `al-per-204-slow` — Clone Trio · Slow
**ثلاث نسخ منك · بطيء**

*accent · any · depth · easing: easeOutBack · 0.3s per clone*

*Original: M-204*

Variant of M-204: أبطأ بـ 60%

**Spec (EN):** Composite 2–3 mattes of the person from different takes side by side; each clone pops in (scale 90% to 100% with fade) 0.3s apart.

**Spec (AR):** ركّب 2 إلى 3 أقنعة للشخص من لقطات مختلفة جنب بعض، وكل نسخة تنط (من 90% لـ 100% مع ظهور) وبينهم 0.3 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-204.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-204.

#### `al-per-204-gold` — Clone Trio · Gold
**ثلاث نسخ منك · ذهبي**

*accent · any · depth · easing: easeOutBack · 0.3s per clone*

*Original: M-204*

Variant of M-204: نسخة ذهبية فاخرة

**Spec (EN):** Composite 2–3 mattes of the person from different takes side by side; each clone pops in (scale 90% to 100% with fade) 0.3s apart.

**Spec (AR):** ركّب 2 إلى 3 أقنعة للشخص من لقطات مختلفة جنب بعض، وكل نسخة تنط (من 90% لـ 100% مع ظهور) وبينهم 0.3 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-204.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-204.

#### `al-per-204-boxed` — Clone Trio · Boxed
**ثلاث نسخ منك · صندوق**

*accent · any · depth · easing: easeOutBack · 0.3s per clone*

*Original: M-204*

Variant of M-204: النص داخل صندوق ملون

**Spec (EN):** Composite 2–3 mattes of the person from different takes side by side; each clone pops in (scale 90% to 100% with fade) 0.3s apart.

**Spec (AR):** ركّب 2 إلى 3 أقنعة للشخص من لقطات مختلفة جنب بعض، وكل نسخة تنط (من 90% لـ 100% مع ظهور) وبينهم 0.3 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-204.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-204.

#### `al-per-205-fast` — Doodle Outline · Fast
**خربشات حولك · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.8s draw*

*Original: M-205*

Variant of M-205: أسرع بـ 40%

**Spec (EN):** Draw loose white hand-drawn strokes (a crown, sparks, an outline arc) around the head that write on over 0.8s and wiggle slightly while held.

**Spec (AR):** ارسم خطوط يد بيضا حرة (تاج، شرار، قوس حول الراس) تنرسم حول الراس خلال 0.8 ثانية وتتمايل شوي وهي ثابتة.

**When to use:**
- EN: Use when you need a fast version of M-205.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-205.

#### `al-per-205-slow` — Doodle Outline · Slow
**خربشات حولك · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.8s draw*

*Original: M-205*

Variant of M-205: أبطأ بـ 60%

**Spec (EN):** Draw loose white hand-drawn strokes (a crown, sparks, an outline arc) around the head that write on over 0.8s and wiggle slightly while held.

**Spec (AR):** ارسم خطوط يد بيضا حرة (تاج، شرار، قوس حول الراس) تنرسم حول الراس خلال 0.8 ثانية وتتمايل شوي وهي ثابتة.

**When to use:**
- EN: Use when you need a slow version of M-205.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-205.

#### `al-per-205-gold` — Doodle Outline · Gold
**خربشات حولك · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.8s draw*

*Original: M-205*

Variant of M-205: نسخة ذهبية فاخرة

**Spec (EN):** Draw loose white hand-drawn strokes (a crown, sparks, an outline arc) around the head that write on over 0.8s and wiggle slightly while held.

**Spec (AR):** ارسم خطوط يد بيضا حرة (تاج، شرار، قوس حول الراس) تنرسم حول الراس خلال 0.8 ثانية وتتمايل شوي وهي ثابتة.

**When to use:**
- EN: Use when you need a gold version of M-205.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-205.

#### `al-per-205-boxed` — Doodle Outline · Boxed
**خربشات حولك · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.8s draw*

*Original: M-205*

Variant of M-205: النص داخل صندوق ملون

**Spec (EN):** Draw loose white hand-drawn strokes (a crown, sparks, an outline arc) around the head that write on over 0.8s and wiggle slightly while held.

**Spec (AR):** ارسم خطوط يد بيضا حرة (تاج، شرار، قوس حول الراس) تنرسم حول الراس خلال 0.8 ثانية وتتمايل شوي وهي ثابتة.

**When to use:**
- EN: Use when you need a boxed version of M-205.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-205.

#### `al-per-206-fast` — Sticker Cutout · Fast
**الشخص ملصق · سريع**

*accent · any · timeline · easing: easeOutBack · 0.4s*

*Original: M-206*

Variant of M-206: أسرع بـ 40%

**Spec (EN):** Using the person matte, add a thick white outline (about 1% of the width) and a soft drop shadow, then pop the sticker in with a slight tilt (scale 0 to 108% to 100%).

**Spec (AR):** باستخدام قناع الشخص، حط حدود بيضا عريضة (تقريباً 1% من العرض) وظل ناعم، وبعدين خل الملصق ينط مع ميلان خفيف (من 0 لـ 108% لـ 100%).

**When to use:**
- EN: Use when you need a fast version of M-206.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-206.

#### `al-per-206-slow` — Sticker Cutout · Slow
**الشخص ملصق · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.4s*

*Original: M-206*

Variant of M-206: أبطأ بـ 60%

**Spec (EN):** Using the person matte, add a thick white outline (about 1% of the width) and a soft drop shadow, then pop the sticker in with a slight tilt (scale 0 to 108% to 100%).

**Spec (AR):** باستخدام قناع الشخص، حط حدود بيضا عريضة (تقريباً 1% من العرض) وظل ناعم، وبعدين خل الملصق ينط مع ميلان خفيف (من 0 لـ 108% لـ 100%).

**When to use:**
- EN: Use when you need a slow version of M-206.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-206.

#### `al-per-206-gold` — Sticker Cutout · Gold
**الشخص ملصق · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.4s*

*Original: M-206*

Variant of M-206: نسخة ذهبية فاخرة

**Spec (EN):** Using the person matte, add a thick white outline (about 1% of the width) and a soft drop shadow, then pop the sticker in with a slight tilt (scale 0 to 108% to 100%).

**Spec (AR):** باستخدام قناع الشخص، حط حدود بيضا عريضة (تقريباً 1% من العرض) وظل ناعم، وبعدين خل الملصق ينط مع ميلان خفيف (من 0 لـ 108% لـ 100%).

**When to use:**
- EN: Use when you need a gold version of M-206.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-206.

#### `al-per-206-boxed` — Sticker Cutout · Boxed
**الشخص ملصق · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.4s*

*Original: M-206*

Variant of M-206: النص داخل صندوق ملون

**Spec (EN):** Using the person matte, add a thick white outline (about 1% of the width) and a soft drop shadow, then pop the sticker in with a slight tilt (scale 0 to 108% to 100%).

**Spec (AR):** باستخدام قناع الشخص، حط حدود بيضا عريضة (تقريباً 1% من العرض) وظل ناعم، وبعدين خل الملصق ينط مع ميلان خفيف (من 0 لـ 108% لـ 100%).

**When to use:**
- EN: Use when you need a boxed version of M-206.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-206.

#### `al-per-207-fast` — Pop-Out Frame · Fast
**الشخص يطلع من الإطار · سريع**

*accent · any · depth · easing: easeOutBack · 0.5s*

*Original: M-207*

Variant of M-207: أسرع بـ 40%

**Spec (EN):** A rounded frame shows the background; the person matte is layered above it so the head sticks out over the top edge of the frame. The frame scales in first.

**Spec (AR):** إطار بزوايا دائرية يعرض الخلفية، وقناع الشخص فوقه بحيث الراس يطلع برا الحافة الفوق للإطار. والإطار يكبر ويدخل أول.

**When to use:**
- EN: Use when you need a fast version of M-207.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-207.

#### `al-per-207-slow` — Pop-Out Frame · Slow
**الشخص يطلع من الإطار · بطيء**

*accent · any · depth · easing: easeOutBack · 0.5s*

*Original: M-207*

Variant of M-207: أبطأ بـ 60%

**Spec (EN):** A rounded frame shows the background; the person matte is layered above it so the head sticks out over the top edge of the frame. The frame scales in first.

**Spec (AR):** إطار بزوايا دائرية يعرض الخلفية، وقناع الشخص فوقه بحيث الراس يطلع برا الحافة الفوق للإطار. والإطار يكبر ويدخل أول.

**When to use:**
- EN: Use when you need a slow version of M-207.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-207.

#### `al-per-207-gold` — Pop-Out Frame · Gold
**الشخص يطلع من الإطار · ذهبي**

*accent · any · depth · easing: easeOutBack · 0.5s*

*Original: M-207*

Variant of M-207: نسخة ذهبية فاخرة

**Spec (EN):** A rounded frame shows the background; the person matte is layered above it so the head sticks out over the top edge of the frame. The frame scales in first.

**Spec (AR):** إطار بزوايا دائرية يعرض الخلفية، وقناع الشخص فوقه بحيث الراس يطلع برا الحافة الفوق للإطار. والإطار يكبر ويدخل أول.

**When to use:**
- EN: Use when you need a gold version of M-207.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-207.

#### `al-per-207-boxed` — Pop-Out Frame · Boxed
**الشخص يطلع من الإطار · صندوق**

*accent · any · depth · easing: easeOutBack · 0.5s*

*Original: M-207*

Variant of M-207: النص داخل صندوق ملون

**Spec (EN):** A rounded frame shows the background; the person matte is layered above it so the head sticks out over the top edge of the frame. The frame scales in first.

**Spec (AR):** إطار بزوايا دائرية يعرض الخلفية، وقناع الشخص فوقه بحيث الراس يطلع برا الحافة الفوق للإطار. والإطار يكبر ويدخل أول.

**When to use:**
- EN: Use when you need a boxed version of M-207.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-207.

#### `al-per-208-fast` — Portrait Mode · Fast
**وضع البورتريه · سريع**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-208*

Variant of M-208: أسرع بـ 40%

**Spec (EN):** Using the person matte, blur only the background to about 1.5% over 0.5s while the person stays sharp.

**Spec (AR):** باستخدام قناع الشخص، ضبّب الخلفية بس لـ تقريباً 1.5% خلال 0.5 ثانية والشخص يبقى واضح.

**When to use:**
- EN: Use when you need a fast version of M-208.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-208.

#### `al-per-208-slow` — Portrait Mode · Slow
**وضع البورتريه · بطيء**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-208*

Variant of M-208: أبطأ بـ 60%

**Spec (EN):** Using the person matte, blur only the background to about 1.5% over 0.5s while the person stays sharp.

**Spec (AR):** باستخدام قناع الشخص، ضبّب الخلفية بس لـ تقريباً 1.5% خلال 0.5 ثانية والشخص يبقى واضح.

**When to use:**
- EN: Use when you need a slow version of M-208.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-208.

#### `al-per-208-gold` — Portrait Mode · Gold
**وضع البورتريه · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-208*

Variant of M-208: نسخة ذهبية فاخرة

**Spec (EN):** Using the person matte, blur only the background to about 1.5% over 0.5s while the person stays sharp.

**Spec (AR):** باستخدام قناع الشخص، ضبّب الخلفية بس لـ تقريباً 1.5% خلال 0.5 ثانية والشخص يبقى واضح.

**When to use:**
- EN: Use when you need a gold version of M-208.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-208.

#### `al-per-208-boxed` — Portrait Mode · Boxed
**وضع البورتريه · صندوق**

*accent · any · depth · easing: easeInOutCubic · 0.5s*

*Original: M-208*

Variant of M-208: النص داخل صندوق ملون

**Spec (EN):** Using the person matte, blur only the background to about 1.5% over 0.5s while the person stays sharp.

**Spec (AR):** باستخدام قناع الشخص، ضبّب الخلفية بس لـ تقريباً 1.5% خلال 0.5 ثانية والشخص يبقى واضح.

**When to use:**
- EN: Use when you need a boxed version of M-208.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-208.

#### `al-per-209-fast` — Silhouette Fill · Fast
**الشخص يتلون لون واحد · سريع**

*accent · calm · timeline · easing: easeOutQuad · 0.3s*

*Original: M-209*

Variant of M-209: أسرع بـ 40%

**Spec (EN):** Using the person matte, fill the person with a flat accent color (keep the matte edge soft) and fade it in over 0.3s on a beat.

**Spec (AR):** باستخدام قناع الشخص، عبّي الشخص بلون الهوية لون واحد (وخل حافة القناع ناعمة)، وخله يظهر خلال 0.3 ثانية على الإيقاع.

**When to use:**
- EN: Use when you need a fast version of M-209.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-209.

#### `al-per-209-slow` — Silhouette Fill · Slow
**الشخص يتلون لون واحد · بطيء**

*accent · calm · timeline · easing: easeOutQuad · 0.3s*

*Original: M-209*

Variant of M-209: أبطأ بـ 60%

**Spec (EN):** Using the person matte, fill the person with a flat accent color (keep the matte edge soft) and fade it in over 0.3s on a beat.

**Spec (AR):** باستخدام قناع الشخص، عبّي الشخص بلون الهوية لون واحد (وخل حافة القناع ناعمة)، وخله يظهر خلال 0.3 ثانية على الإيقاع.

**When to use:**
- EN: Use when you need a slow version of M-209.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-209.

#### `al-per-209-gold` — Silhouette Fill · Gold
**الشخص يتلون لون واحد · ذهبي**

*accent · calm · timeline · easing: easeOutQuad · 0.3s*

*Original: M-209*

Variant of M-209: نسخة ذهبية فاخرة

**Spec (EN):** Using the person matte, fill the person with a flat accent color (keep the matte edge soft) and fade it in over 0.3s on a beat.

**Spec (AR):** باستخدام قناع الشخص، عبّي الشخص بلون الهوية لون واحد (وخل حافة القناع ناعمة)، وخله يظهر خلال 0.3 ثانية على الإيقاع.

**When to use:**
- EN: Use when you need a gold version of M-209.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-209.

#### `al-per-209-boxed` — Silhouette Fill · Boxed
**الشخص يتلون لون واحد · صندوق**

*accent · calm · timeline · easing: easeOutQuad · 0.3s*

*Original: M-209*

Variant of M-209: النص داخل صندوق ملون

**Spec (EN):** Using the person matte, fill the person with a flat accent color (keep the matte edge soft) and fade it in over 0.3s on a beat.

**Spec (AR):** باستخدام قناع الشخص، عبّي الشخص بلون الهوية لون واحد (وخل حافة القناع ناعمة)، وخله يظهر خلال 0.3 ثانية على الإيقاع.

**When to use:**
- EN: Use when you need a boxed version of M-209.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-209.

#### `al-per-210-fast` — Neon Outline · Fast
**حدود نيون للشخص · سريع**

*accent · any · timeline · easing: steps · loop flicker*

*Original: M-210*

Variant of M-210: أسرع بـ 40%

**Spec (EN):** Trace the person matte edge with a 0.8% mint line plus a wide glow, and flicker it on like neon (see M-056).

**Spec (AR):** ارسم حافة قناع الشخص بخط نعناعي 0.8% مع توهج عريض، وخله يشتغل ويرمش مثل النيون (شوف M-056).

**When to use:**
- EN: Use when you need a fast version of M-210.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-210.

#### `al-per-210-slow` — Neon Outline · Slow
**حدود نيون للشخص · بطيء**

*accent · any · timeline · easing: steps · loop flicker*

*Original: M-210*

Variant of M-210: أبطأ بـ 60%

**Spec (EN):** Trace the person matte edge with a 0.8% mint line plus a wide glow, and flicker it on like neon (see M-056).

**Spec (AR):** ارسم حافة قناع الشخص بخط نعناعي 0.8% مع توهج عريض، وخله يشتغل ويرمش مثل النيون (شوف M-056).

**When to use:**
- EN: Use when you need a slow version of M-210.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-210.

#### `al-per-210-gold` — Neon Outline · Gold
**حدود نيون للشخص · ذهبي**

*accent · any · timeline · easing: steps · loop flicker*

*Original: M-210*

Variant of M-210: نسخة ذهبية فاخرة

**Spec (EN):** Trace the person matte edge with a 0.8% mint line plus a wide glow, and flicker it on like neon (see M-056).

**Spec (AR):** ارسم حافة قناع الشخص بخط نعناعي 0.8% مع توهج عريض، وخله يشتغل ويرمش مثل النيون (شوف M-056).

**When to use:**
- EN: Use when you need a gold version of M-210.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-210.

#### `al-per-210-boxed` — Neon Outline · Boxed
**حدود نيون للشخص · صندوق**

*accent · any · timeline · easing: steps · loop flicker*

*Original: M-210*

Variant of M-210: النص داخل صندوق ملون

**Spec (EN):** Trace the person matte edge with a 0.8% mint line plus a wide glow, and flicker it on like neon (see M-056).

**Spec (AR):** ارسم حافة قناع الشخص بخط نعناعي 0.8% مع توهج عريض، وخله يشتغل ويرمش مثل النيون (شوف M-056).

**When to use:**
- EN: Use when you need a boxed version of M-210.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-210.

#### `al-per-211-fast` — Spotlight Follow · Fast
**ضوء يتبع الشخص · سريع**

*accent · calm · camera · easing: easeInOutSine · loop*

*Original: M-211*

Variant of M-211: أسرع بـ 40%

**Spec (EN):** Darken the frame about 85% except a soft circle around the person; the circle tracks the head position every frame.

**Spec (AR):** غمّق الشاشة تقريباً 85% إلا دائرة ناعمة حول الشخص، والدائرة تتبع مكان الراس كل فريم.

**When to use:**
- EN: Use when you need a fast version of M-211.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-211.

#### `al-per-211-slow` — Spotlight Follow · Slow
**ضوء يتبع الشخص · بطيء**

*accent · calm · camera · easing: easeInOutSine · loop*

*Original: M-211*

Variant of M-211: أبطأ بـ 60%

**Spec (EN):** Darken the frame about 85% except a soft circle around the person; the circle tracks the head position every frame.

**Spec (AR):** غمّق الشاشة تقريباً 85% إلا دائرة ناعمة حول الشخص، والدائرة تتبع مكان الراس كل فريم.

**When to use:**
- EN: Use when you need a slow version of M-211.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-211.

#### `al-per-211-gold` — Spotlight Follow · Gold
**ضوء يتبع الشخص · ذهبي**

*accent · calm · camera · easing: easeInOutSine · loop*

*Original: M-211*

Variant of M-211: نسخة ذهبية فاخرة

**Spec (EN):** Darken the frame about 85% except a soft circle around the person; the circle tracks the head position every frame.

**Spec (AR):** غمّق الشاشة تقريباً 85% إلا دائرة ناعمة حول الشخص، والدائرة تتبع مكان الراس كل فريم.

**When to use:**
- EN: Use when you need a gold version of M-211.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-211.

#### `al-per-211-boxed` — Spotlight Follow · Boxed
**ضوء يتبع الشخص · صندوق**

*accent · calm · camera · easing: easeInOutSine · loop*

*Original: M-211*

Variant of M-211: النص داخل صندوق ملون

**Spec (EN):** Darken the frame about 85% except a soft circle around the person; the circle tracks the head position every frame.

**Spec (AR):** غمّق الشاشة تقريباً 85% إلا دائرة ناعمة حول الشخص، والدائرة تتبع مكان الراس كل فريم.

**When to use:**
- EN: Use when you need a boxed version of M-211.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-211.

#### `al-per-212-fast` — Halftone Person · Fast
**الشخص بنقاط · سريع**

*accent · calm · timeline · easing: easeOutQuad · 0.4s*

*Original: M-212*

Variant of M-212: أسرع بـ 40%

**Spec (EN):** Inside the person matte, overlay an accent halftone dot pattern (dot size tied to brightness) with a multiply blend.

**Spec (AR):** داخل قناع الشخص، حط نقش نقاط بلون الهوية (حجم النقطة على حسب الإضاءة) بدمج multiply.

**When to use:**
- EN: Use when you need a fast version of M-212.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-212.

#### `al-per-212-slow` — Halftone Person · Slow
**الشخص بنقاط · بطيء**

*accent · calm · timeline · easing: easeOutQuad · 0.4s*

*Original: M-212*

Variant of M-212: أبطأ بـ 60%

**Spec (EN):** Inside the person matte, overlay an accent halftone dot pattern (dot size tied to brightness) with a multiply blend.

**Spec (AR):** داخل قناع الشخص، حط نقش نقاط بلون الهوية (حجم النقطة على حسب الإضاءة) بدمج multiply.

**When to use:**
- EN: Use when you need a slow version of M-212.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-212.

#### `al-per-212-gold` — Halftone Person · Gold
**الشخص بنقاط · ذهبي**

*accent · calm · timeline · easing: easeOutQuad · 0.4s*

*Original: M-212*

Variant of M-212: نسخة ذهبية فاخرة

**Spec (EN):** Inside the person matte, overlay an accent halftone dot pattern (dot size tied to brightness) with a multiply blend.

**Spec (AR):** داخل قناع الشخص، حط نقش نقاط بلون الهوية (حجم النقطة على حسب الإضاءة) بدمج multiply.

**When to use:**
- EN: Use when you need a gold version of M-212.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-212.

#### `al-per-212-boxed` — Halftone Person · Boxed
**الشخص بنقاط · صندوق**

*accent · calm · timeline · easing: easeOutQuad · 0.4s*

*Original: M-212*

Variant of M-212: النص داخل صندوق ملون

**Spec (EN):** Inside the person matte, overlay an accent halftone dot pattern (dot size tied to brightness) with a multiply blend.

**Spec (AR):** داخل قناع الشخص، حط نقش نقاط بلون الهوية (حجم النقطة على حسب الإضاءة) بدمج multiply.

**When to use:**
- EN: Use when you need a boxed version of M-212.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-212.

#### `al-per-213-fast` — Background Flash Swap · Fast
**الخلفية تتبدل على الإيقاع · سريع**

*accent · any · depth · easing: cut · per beat*

*Original: M-213*

Variant of M-213: أسرع بـ 40%

**Spec (EN):** Using the person matte, replace the background with a solid color that changes on every beat (cycle 3–4 brand colors).

**Spec (AR):** باستخدام قناع الشخص، بدّل الخلفية بلون واحد يتغير مع كل ضربة إيقاع (لف على 3 إلى 4 ألوان من الهوية).

**When to use:**
- EN: Use when you need a fast version of M-213.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-213.

#### `al-per-213-slow` — Background Flash Swap · Slow
**الخلفية تتبدل على الإيقاع · بطيء**

*accent · any · depth · easing: cut · per beat*

*Original: M-213*

Variant of M-213: أبطأ بـ 60%

**Spec (EN):** Using the person matte, replace the background with a solid color that changes on every beat (cycle 3–4 brand colors).

**Spec (AR):** باستخدام قناع الشخص، بدّل الخلفية بلون واحد يتغير مع كل ضربة إيقاع (لف على 3 إلى 4 ألوان من الهوية).

**When to use:**
- EN: Use when you need a slow version of M-213.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-213.

#### `al-per-213-gold` — Background Flash Swap · Gold
**الخلفية تتبدل على الإيقاع · ذهبي**

*accent · any · depth · easing: cut · per beat*

*Original: M-213*

Variant of M-213: نسخة ذهبية فاخرة

**Spec (EN):** Using the person matte, replace the background with a solid color that changes on every beat (cycle 3–4 brand colors).

**Spec (AR):** باستخدام قناع الشخص، بدّل الخلفية بلون واحد يتغير مع كل ضربة إيقاع (لف على 3 إلى 4 ألوان من الهوية).

**When to use:**
- EN: Use when you need a gold version of M-213.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-213.

#### `al-per-213-boxed` — Background Flash Swap · Boxed
**الخلفية تتبدل على الإيقاع · صندوق**

*accent · any · depth · easing: cut · per beat*

*Original: M-213*

Variant of M-213: النص داخل صندوق ملون

**Spec (EN):** Using the person matte, replace the background with a solid color that changes on every beat (cycle 3–4 brand colors).

**Spec (AR):** باستخدام قناع الشخص، بدّل الخلفية بلون واحد يتغير مع كل ضربة إيقاع (لف على 3 إلى 4 ألوان من الهوية).

**When to use:**
- EN: Use when you need a boxed version of M-213.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-213.

### Audio & Beat (الصوت والإيقاع) — 60 motions

#### `al-aud-214` — Waveform
**موجة صوت**

*workhorse · calm · timeline · easing: linear · live*

*Original: M-214*

A waveform that moves with your voice.

**Spec (EN):** Analyze the voice track loudness (RMS) per frame and draw 30–60 thin rounded accent bars whose heights follow the audio around a center line.

**Spec (AR):** حلل قوة الصوت (RMS) لكل فريم، وارسم 30 إلى 60 عمود رفيع بزوايا دائرية بلون الهوية، طولهم يتبع الصوت حول خط بالنص.

**When to use:**
- EN: A waveform that moves with your voice.
- AR: موجة تتحرك مع صوتك تحت الكابشن أو على البودكاست.

#### `al-aud-215` — Equalizer Bars
**أعمدة صوت**

*workhorse · any · timeline · easing: easeOut · live*

*Original: M-215*

Bars that bounce with the audio or music.

**Spec (EN):** Split the audio spectrum into 6–10 frequency bands and draw a vertical gradient bar per band whose height follows that band with quick attack and slower release.

**Spec (AR):** قسّم طيف الصوت 6 إلى 10 ترددات، وارسم عمود متدرج لكل تردد، طوله يتبع التردد بصعود سريع ونزول أبطأ.

**When to use:**
- EN: Bars that bounce with the audio or music.
- AR: أعمدة تنط مع الصوت أو الموسيقى.

#### `al-aud-216` — Circular Visualizer
**دائرة صوت**

*workhorse · any · timeline · easing: easeOut · live*

*Original: M-216*

Audio bars arranged in a circle around your photo.

**Spec (EN):** Place 24–48 accent bars radially around a circular avatar; each bar length follows one frequency band of the audio.

**Spec (AR):** حط 24 إلى 48 عمود بلون الهوية بشكل دائري حول صورة دائرية، وطول كل عمود يتبع تردد من ترددات الصوت.

**When to use:**
- EN: Audio bars arranged in a circle around your photo.
- AR: أعمدة صوت حول صورتك بشكل دائري.

#### `al-aud-217` — Beat Flash
**وميض على الإيقاع**

*workhorse · any · timeline · easing: easeOut · per beat · 0.15s*

*Original: M-217*

A light flash on every beat of the music.

**Spec (EN):** Detect beats in the music track; on each beat flash a white overlay to about 40–85% and fade it out over 0.15s.

**Spec (AR):** اكتشف الضربات في الموسيقى، ومع كل ضربة طلّع وميض أبيض يوصل 40 إلى 85% ويختفي خلال 0.15 ثانية.

**When to use:**
- EN: A light flash on every beat of the music.
- AR: وميض خفيف مع كل ضربة بالموسيقى.

#### `al-aud-218` — Beat Zoom
**زوم على الإيقاع**

*workhorse · any · timeline · easing: easeOutCubic · per beat · 0.2s*

*Original: M-218*

The frame pulses a zoom on every beat.

**Spec (EN):** On each detected beat, jump the frame scale to 112% and ease back to 100% over about 0.2s.

**Spec (AR):** مع كل ضربة، كبّر الصورة لـ 112% وخلها ترجع لـ 100% بنعومة خلال تقريباً 0.2 ثانية.

**When to use:**
- EN: The frame pulses a zoom on every beat.
- AR: الصورة تنبض زوم مع كل ضربة.

#### `al-aud-219` — Beat Shake
**هزة على الإيقاع**

*workhorse · calm · timeline · easing: linear · per beat · 0.15s*

*Original: M-219*

A short shake on every heavy beat.

**Spec (EN):** On each strong beat (kick), shake the overscaled frame (106%) with 2–3 quick offsets of ±2% over 0.15s.

**Spec (AR):** مع كل ضربة قوية (kick)، هز الصورة المكبرة (106%) بـ 2 إلى 3 إزاحات سريعة ±2% خلال 0.15 ثانية.

**When to use:**
- EN: A short shake on every heavy beat.
- AR: هزة قصيرة مع كل ضربة قوية.

#### `al-aud-220` — Audio Pulse Ring
**حلقة تنبض مع الصوت**

*workhorse · any · timeline · easing: easeOut · live*

*Original: M-220*

A ring around your photo that swells with your voice.

**Spec (EN):** Draw an accent ring around a circular avatar; its scale (100–118%) and opacity follow the voice loudness each frame.

**Spec (AR):** ارسم حلقة بلون الهوية حول صورة دائرية، وحجمها (100% إلى 118%) وشفافيتها يتبعون قوة الصوت كل فريم.

**When to use:**
- EN: A ring around your photo that swells with your voice.
- AR: حلقة حول صورتك تكبر مع صوتك.

#### `al-aud-221` — Waveform Caption
**كابشن مع موجة**

*workhorse · calm · camera · easing: linear · live*

*Original: M-221*

A caption with a small live waveform under it.

**Spec (EN):** Show the caption as usual and draw a compact waveform (M-214) just under it, following the voice.

**Spec (AR):** اعرض الكابشن عادي وارسم موجة صغيرة (M-214) تحته على طول، تتبع الصوت.

**When to use:**
- EN: A caption with a small live waveform under it.
- AR: كابشن وتحته موجة صغيرة تتحرك مع الكلام.

#### `al-aud-222` — Mic Pulse
**مايك ينبض**

*workhorse · any · timeline · easing: easeOutCubic · loop · 1.5s*

*Original: M-222*

A microphone icon with ripples, for podcasts and voice.

**Spec (EN):** A mic icon sits at the center while thin rings expand from it every 0.5s and fade (see M-150).

**Spec (AR):** أيقونة مايك بالنص، ومنها دواير رفيعة تكبر كل 0.5 ثانية وتختفي (شوف M-150).

**When to use:**
- EN: A microphone icon with ripples, for podcasts and voice.
- AR: أيقونة مايك مع موجات، للبودكاست والصوتيات.

#### `al-aud-223` — Podcast Card
**بطاقة بودكاست**

*workhorse · any · depth · easing: spring · 0.5s in*

*Original: M-223*

A podcast episode card with a photo and waveform.

**Spec (EN):** A light card with avatar, episode title, show name and a small live waveform slides up with a spring and holds.

**Spec (AR):** بطاقة فاتحة فيها الصورة وعنوان الحلقة واسم البرنامج وموجة صغيرة، تطلع لفوق بحركة نابض وتثبت.

**When to use:**
- EN: A podcast episode card with a photo and waveform.
- AR: بطاقة حلقة بودكاست مع صورة وموجة.

#### `al-aud-224` — Volume Meter
**مؤشر الصوت**

*workhorse · calm · depth · easing: linear · live*

*Original: M-224*

A level meter rising and falling with the voice.

**Spec (EN):** Stack 8–12 segments vertically; segments light up from the bottom with loudness (green, then yellow, then red at the top).

**Spec (AR):** رتّب 8 إلى 12 مربع فوق بعض، والمربعات تنور من تحت لفوق مع قوة الصوت (أخضر، وبعدين أصفر، وفوق أحمر).

**When to use:**
- EN: A level meter rising and falling with the voice.
- AR: مؤشر صوت يعلى ويهبط مع الكلام.

#### `al-aud-225` — BPM Counter
**عداد الإيقاع**

*workhorse · any · timeline · easing: easeOut · per beat*

*Original: M-225*

A BPM number with a dot pulsing on the beat.

**Spec (EN):** Show the tempo as a mono number with "BPM" and a dot that flashes to 150% on every beat.

**Spec (AR):** اعرض سرعة الإيقاع برقم mono مع كلمة "BPM"، ونقطة تكبر لـ 150% وتومض مع كل ضربة.

**When to use:**
- EN: A BPM number with a dot pulsing on the beat.
- AR: رقم الـ BPM مع نقطة تنبض على الإيقاع.

#### `al-aud-214-fast` — Waveform · Fast
**موجة صوت · سريع**

*accent · calm · timeline · easing: linear · live*

*Original: M-214*

Variant of M-214: أسرع بـ 40%

**Spec (EN):** Analyze the voice track loudness (RMS) per frame and draw 30–60 thin rounded accent bars whose heights follow the audio around a center line.

**Spec (AR):** حلل قوة الصوت (RMS) لكل فريم، وارسم 30 إلى 60 عمود رفيع بزوايا دائرية بلون الهوية، طولهم يتبع الصوت حول خط بالنص.

**When to use:**
- EN: Use when you need a fast version of M-214.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-214.

#### `al-aud-214-slow` — Waveform · Slow
**موجة صوت · بطيء**

*accent · calm · timeline · easing: linear · live*

*Original: M-214*

Variant of M-214: أبطأ بـ 60%

**Spec (EN):** Analyze the voice track loudness (RMS) per frame and draw 30–60 thin rounded accent bars whose heights follow the audio around a center line.

**Spec (AR):** حلل قوة الصوت (RMS) لكل فريم، وارسم 30 إلى 60 عمود رفيع بزوايا دائرية بلون الهوية، طولهم يتبع الصوت حول خط بالنص.

**When to use:**
- EN: Use when you need a slow version of M-214.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-214.

#### `al-aud-214-gold` — Waveform · Gold
**موجة صوت · ذهبي**

*accent · calm · timeline · easing: linear · live*

*Original: M-214*

Variant of M-214: نسخة ذهبية فاخرة

**Spec (EN):** Analyze the voice track loudness (RMS) per frame and draw 30–60 thin rounded accent bars whose heights follow the audio around a center line.

**Spec (AR):** حلل قوة الصوت (RMS) لكل فريم، وارسم 30 إلى 60 عمود رفيع بزوايا دائرية بلون الهوية، طولهم يتبع الصوت حول خط بالنص.

**When to use:**
- EN: Use when you need a gold version of M-214.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-214.

#### `al-aud-214-boxed` — Waveform · Boxed
**موجة صوت · صندوق**

*accent · calm · timeline · easing: linear · live*

*Original: M-214*

Variant of M-214: النص داخل صندوق ملون

**Spec (EN):** Analyze the voice track loudness (RMS) per frame and draw 30–60 thin rounded accent bars whose heights follow the audio around a center line.

**Spec (AR):** حلل قوة الصوت (RMS) لكل فريم، وارسم 30 إلى 60 عمود رفيع بزوايا دائرية بلون الهوية، طولهم يتبع الصوت حول خط بالنص.

**When to use:**
- EN: Use when you need a boxed version of M-214.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-214.

#### `al-aud-215-fast` — Equalizer Bars · Fast
**أعمدة صوت · سريع**

*accent · any · timeline · easing: easeOut · live*

*Original: M-215*

Variant of M-215: أسرع بـ 40%

**Spec (EN):** Split the audio spectrum into 6–10 frequency bands and draw a vertical gradient bar per band whose height follows that band with quick attack and slower release.

**Spec (AR):** قسّم طيف الصوت 6 إلى 10 ترددات، وارسم عمود متدرج لكل تردد، طوله يتبع التردد بصعود سريع ونزول أبطأ.

**When to use:**
- EN: Use when you need a fast version of M-215.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-215.

#### `al-aud-215-slow` — Equalizer Bars · Slow
**أعمدة صوت · بطيء**

*accent · any · timeline · easing: easeOut · live*

*Original: M-215*

Variant of M-215: أبطأ بـ 60%

**Spec (EN):** Split the audio spectrum into 6–10 frequency bands and draw a vertical gradient bar per band whose height follows that band with quick attack and slower release.

**Spec (AR):** قسّم طيف الصوت 6 إلى 10 ترددات، وارسم عمود متدرج لكل تردد، طوله يتبع التردد بصعود سريع ونزول أبطأ.

**When to use:**
- EN: Use when you need a slow version of M-215.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-215.

#### `al-aud-215-gold` — Equalizer Bars · Gold
**أعمدة صوت · ذهبي**

*accent · any · timeline · easing: easeOut · live*

*Original: M-215*

Variant of M-215: نسخة ذهبية فاخرة

**Spec (EN):** Split the audio spectrum into 6–10 frequency bands and draw a vertical gradient bar per band whose height follows that band with quick attack and slower release.

**Spec (AR):** قسّم طيف الصوت 6 إلى 10 ترددات، وارسم عمود متدرج لكل تردد، طوله يتبع التردد بصعود سريع ونزول أبطأ.

**When to use:**
- EN: Use when you need a gold version of M-215.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-215.

#### `al-aud-215-boxed` — Equalizer Bars · Boxed
**أعمدة صوت · صندوق**

*accent · any · timeline · easing: easeOut · live*

*Original: M-215*

Variant of M-215: النص داخل صندوق ملون

**Spec (EN):** Split the audio spectrum into 6–10 frequency bands and draw a vertical gradient bar per band whose height follows that band with quick attack and slower release.

**Spec (AR):** قسّم طيف الصوت 6 إلى 10 ترددات، وارسم عمود متدرج لكل تردد، طوله يتبع التردد بصعود سريع ونزول أبطأ.

**When to use:**
- EN: Use when you need a boxed version of M-215.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-215.

#### `al-aud-216-fast` — Circular Visualizer · Fast
**دائرة صوت · سريع**

*accent · any · timeline · easing: easeOut · live*

*Original: M-216*

Variant of M-216: أسرع بـ 40%

**Spec (EN):** Place 24–48 accent bars radially around a circular avatar; each bar length follows one frequency band of the audio.

**Spec (AR):** حط 24 إلى 48 عمود بلون الهوية بشكل دائري حول صورة دائرية، وطول كل عمود يتبع تردد من ترددات الصوت.

**When to use:**
- EN: Use when you need a fast version of M-216.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-216.

#### `al-aud-216-slow` — Circular Visualizer · Slow
**دائرة صوت · بطيء**

*accent · any · timeline · easing: easeOut · live*

*Original: M-216*

Variant of M-216: أبطأ بـ 60%

**Spec (EN):** Place 24–48 accent bars radially around a circular avatar; each bar length follows one frequency band of the audio.

**Spec (AR):** حط 24 إلى 48 عمود بلون الهوية بشكل دائري حول صورة دائرية، وطول كل عمود يتبع تردد من ترددات الصوت.

**When to use:**
- EN: Use when you need a slow version of M-216.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-216.

#### `al-aud-216-gold` — Circular Visualizer · Gold
**دائرة صوت · ذهبي**

*accent · any · timeline · easing: easeOut · live*

*Original: M-216*

Variant of M-216: نسخة ذهبية فاخرة

**Spec (EN):** Place 24–48 accent bars radially around a circular avatar; each bar length follows one frequency band of the audio.

**Spec (AR):** حط 24 إلى 48 عمود بلون الهوية بشكل دائري حول صورة دائرية، وطول كل عمود يتبع تردد من ترددات الصوت.

**When to use:**
- EN: Use when you need a gold version of M-216.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-216.

#### `al-aud-216-boxed` — Circular Visualizer · Boxed
**دائرة صوت · صندوق**

*accent · any · timeline · easing: easeOut · live*

*Original: M-216*

Variant of M-216: النص داخل صندوق ملون

**Spec (EN):** Place 24–48 accent bars radially around a circular avatar; each bar length follows one frequency band of the audio.

**Spec (AR):** حط 24 إلى 48 عمود بلون الهوية بشكل دائري حول صورة دائرية، وطول كل عمود يتبع تردد من ترددات الصوت.

**When to use:**
- EN: Use when you need a boxed version of M-216.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-216.

#### `al-aud-217-fast` — Beat Flash · Fast
**وميض على الإيقاع · سريع**

*accent · any · timeline · easing: easeOut · per beat · 0.15s*

*Original: M-217*

Variant of M-217: أسرع بـ 40%

**Spec (EN):** Detect beats in the music track; on each beat flash a white overlay to about 40–85% and fade it out over 0.15s.

**Spec (AR):** اكتشف الضربات في الموسيقى، ومع كل ضربة طلّع وميض أبيض يوصل 40 إلى 85% ويختفي خلال 0.15 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-217.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-217.

#### `al-aud-217-slow` — Beat Flash · Slow
**وميض على الإيقاع · بطيء**

*accent · any · timeline · easing: easeOut · per beat · 0.15s*

*Original: M-217*

Variant of M-217: أبطأ بـ 60%

**Spec (EN):** Detect beats in the music track; on each beat flash a white overlay to about 40–85% and fade it out over 0.15s.

**Spec (AR):** اكتشف الضربات في الموسيقى، ومع كل ضربة طلّع وميض أبيض يوصل 40 إلى 85% ويختفي خلال 0.15 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-217.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-217.

#### `al-aud-217-gold` — Beat Flash · Gold
**وميض على الإيقاع · ذهبي**

*accent · any · timeline · easing: easeOut · per beat · 0.15s*

*Original: M-217*

Variant of M-217: نسخة ذهبية فاخرة

**Spec (EN):** Detect beats in the music track; on each beat flash a white overlay to about 40–85% and fade it out over 0.15s.

**Spec (AR):** اكتشف الضربات في الموسيقى، ومع كل ضربة طلّع وميض أبيض يوصل 40 إلى 85% ويختفي خلال 0.15 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-217.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-217.

#### `al-aud-217-boxed` — Beat Flash · Boxed
**وميض على الإيقاع · صندوق**

*accent · any · timeline · easing: easeOut · per beat · 0.15s*

*Original: M-217*

Variant of M-217: النص داخل صندوق ملون

**Spec (EN):** Detect beats in the music track; on each beat flash a white overlay to about 40–85% and fade it out over 0.15s.

**Spec (AR):** اكتشف الضربات في الموسيقى، ومع كل ضربة طلّع وميض أبيض يوصل 40 إلى 85% ويختفي خلال 0.15 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-217.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-217.

#### `al-aud-218-fast` — Beat Zoom · Fast
**زوم على الإيقاع · سريع**

*accent · any · timeline · easing: easeOutCubic · per beat · 0.2s*

*Original: M-218*

Variant of M-218: أسرع بـ 40%

**Spec (EN):** On each detected beat, jump the frame scale to 112% and ease back to 100% over about 0.2s.

**Spec (AR):** مع كل ضربة، كبّر الصورة لـ 112% وخلها ترجع لـ 100% بنعومة خلال تقريباً 0.2 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-218.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-218.

#### `al-aud-218-slow` — Beat Zoom · Slow
**زوم على الإيقاع · بطيء**

*accent · any · timeline · easing: easeOutCubic · per beat · 0.2s*

*Original: M-218*

Variant of M-218: أبطأ بـ 60%

**Spec (EN):** On each detected beat, jump the frame scale to 112% and ease back to 100% over about 0.2s.

**Spec (AR):** مع كل ضربة، كبّر الصورة لـ 112% وخلها ترجع لـ 100% بنعومة خلال تقريباً 0.2 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-218.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-218.

#### `al-aud-218-gold` — Beat Zoom · Gold
**زوم على الإيقاع · ذهبي**

*accent · any · timeline · easing: easeOutCubic · per beat · 0.2s*

*Original: M-218*

Variant of M-218: نسخة ذهبية فاخرة

**Spec (EN):** On each detected beat, jump the frame scale to 112% and ease back to 100% over about 0.2s.

**Spec (AR):** مع كل ضربة، كبّر الصورة لـ 112% وخلها ترجع لـ 100% بنعومة خلال تقريباً 0.2 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-218.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-218.

#### `al-aud-218-boxed` — Beat Zoom · Boxed
**زوم على الإيقاع · صندوق**

*accent · any · timeline · easing: easeOutCubic · per beat · 0.2s*

*Original: M-218*

Variant of M-218: النص داخل صندوق ملون

**Spec (EN):** On each detected beat, jump the frame scale to 112% and ease back to 100% over about 0.2s.

**Spec (AR):** مع كل ضربة، كبّر الصورة لـ 112% وخلها ترجع لـ 100% بنعومة خلال تقريباً 0.2 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-218.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-218.

#### `al-aud-219-fast` — Beat Shake · Fast
**هزة على الإيقاع · سريع**

*accent · calm · timeline · easing: linear · per beat · 0.15s*

*Original: M-219*

Variant of M-219: أسرع بـ 40%

**Spec (EN):** On each strong beat (kick), shake the overscaled frame (106%) with 2–3 quick offsets of ±2% over 0.15s.

**Spec (AR):** مع كل ضربة قوية (kick)، هز الصورة المكبرة (106%) بـ 2 إلى 3 إزاحات سريعة ±2% خلال 0.15 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-219.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-219.

#### `al-aud-219-slow` — Beat Shake · Slow
**هزة على الإيقاع · بطيء**

*accent · calm · timeline · easing: linear · per beat · 0.15s*

*Original: M-219*

Variant of M-219: أبطأ بـ 60%

**Spec (EN):** On each strong beat (kick), shake the overscaled frame (106%) with 2–3 quick offsets of ±2% over 0.15s.

**Spec (AR):** مع كل ضربة قوية (kick)، هز الصورة المكبرة (106%) بـ 2 إلى 3 إزاحات سريعة ±2% خلال 0.15 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-219.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-219.

#### `al-aud-219-gold` — Beat Shake · Gold
**هزة على الإيقاع · ذهبي**

*accent · calm · timeline · easing: linear · per beat · 0.15s*

*Original: M-219*

Variant of M-219: نسخة ذهبية فاخرة

**Spec (EN):** On each strong beat (kick), shake the overscaled frame (106%) with 2–3 quick offsets of ±2% over 0.15s.

**Spec (AR):** مع كل ضربة قوية (kick)، هز الصورة المكبرة (106%) بـ 2 إلى 3 إزاحات سريعة ±2% خلال 0.15 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-219.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-219.

#### `al-aud-219-boxed` — Beat Shake · Boxed
**هزة على الإيقاع · صندوق**

*accent · calm · timeline · easing: linear · per beat · 0.15s*

*Original: M-219*

Variant of M-219: النص داخل صندوق ملون

**Spec (EN):** On each strong beat (kick), shake the overscaled frame (106%) with 2–3 quick offsets of ±2% over 0.15s.

**Spec (AR):** مع كل ضربة قوية (kick)، هز الصورة المكبرة (106%) بـ 2 إلى 3 إزاحات سريعة ±2% خلال 0.15 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-219.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-219.

#### `al-aud-220-fast` — Audio Pulse Ring · Fast
**حلقة تنبض مع الصوت · سريع**

*accent · any · timeline · easing: easeOut · live*

*Original: M-220*

Variant of M-220: أسرع بـ 40%

**Spec (EN):** Draw an accent ring around a circular avatar; its scale (100–118%) and opacity follow the voice loudness each frame.

**Spec (AR):** ارسم حلقة بلون الهوية حول صورة دائرية، وحجمها (100% إلى 118%) وشفافيتها يتبعون قوة الصوت كل فريم.

**When to use:**
- EN: Use when you need a fast version of M-220.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-220.

#### `al-aud-220-slow` — Audio Pulse Ring · Slow
**حلقة تنبض مع الصوت · بطيء**

*accent · any · timeline · easing: easeOut · live*

*Original: M-220*

Variant of M-220: أبطأ بـ 60%

**Spec (EN):** Draw an accent ring around a circular avatar; its scale (100–118%) and opacity follow the voice loudness each frame.

**Spec (AR):** ارسم حلقة بلون الهوية حول صورة دائرية، وحجمها (100% إلى 118%) وشفافيتها يتبعون قوة الصوت كل فريم.

**When to use:**
- EN: Use when you need a slow version of M-220.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-220.

#### `al-aud-220-gold` — Audio Pulse Ring · Gold
**حلقة تنبض مع الصوت · ذهبي**

*accent · any · timeline · easing: easeOut · live*

*Original: M-220*

Variant of M-220: نسخة ذهبية فاخرة

**Spec (EN):** Draw an accent ring around a circular avatar; its scale (100–118%) and opacity follow the voice loudness each frame.

**Spec (AR):** ارسم حلقة بلون الهوية حول صورة دائرية، وحجمها (100% إلى 118%) وشفافيتها يتبعون قوة الصوت كل فريم.

**When to use:**
- EN: Use when you need a gold version of M-220.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-220.

#### `al-aud-220-boxed` — Audio Pulse Ring · Boxed
**حلقة تنبض مع الصوت · صندوق**

*accent · any · timeline · easing: easeOut · live*

*Original: M-220*

Variant of M-220: النص داخل صندوق ملون

**Spec (EN):** Draw an accent ring around a circular avatar; its scale (100–118%) and opacity follow the voice loudness each frame.

**Spec (AR):** ارسم حلقة بلون الهوية حول صورة دائرية، وحجمها (100% إلى 118%) وشفافيتها يتبعون قوة الصوت كل فريم.

**When to use:**
- EN: Use when you need a boxed version of M-220.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-220.

#### `al-aud-221-fast` — Waveform Caption · Fast
**كابشن مع موجة · سريع**

*accent · calm · camera · easing: linear · live*

*Original: M-221*

Variant of M-221: أسرع بـ 40%

**Spec (EN):** Show the caption as usual and draw a compact waveform (M-214) just under it, following the voice.

**Spec (AR):** اعرض الكابشن عادي وارسم موجة صغيرة (M-214) تحته على طول، تتبع الصوت.

**When to use:**
- EN: Use when you need a fast version of M-221.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-221.

#### `al-aud-221-slow` — Waveform Caption · Slow
**كابشن مع موجة · بطيء**

*accent · calm · camera · easing: linear · live*

*Original: M-221*

Variant of M-221: أبطأ بـ 60%

**Spec (EN):** Show the caption as usual and draw a compact waveform (M-214) just under it, following the voice.

**Spec (AR):** اعرض الكابشن عادي وارسم موجة صغيرة (M-214) تحته على طول، تتبع الصوت.

**When to use:**
- EN: Use when you need a slow version of M-221.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-221.

#### `al-aud-221-gold` — Waveform Caption · Gold
**كابشن مع موجة · ذهبي**

*accent · calm · camera · easing: linear · live*

*Original: M-221*

Variant of M-221: نسخة ذهبية فاخرة

**Spec (EN):** Show the caption as usual and draw a compact waveform (M-214) just under it, following the voice.

**Spec (AR):** اعرض الكابشن عادي وارسم موجة صغيرة (M-214) تحته على طول، تتبع الصوت.

**When to use:**
- EN: Use when you need a gold version of M-221.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-221.

#### `al-aud-221-boxed` — Waveform Caption · Boxed
**كابشن مع موجة · صندوق**

*accent · calm · camera · easing: linear · live*

*Original: M-221*

Variant of M-221: النص داخل صندوق ملون

**Spec (EN):** Show the caption as usual and draw a compact waveform (M-214) just under it, following the voice.

**Spec (AR):** اعرض الكابشن عادي وارسم موجة صغيرة (M-214) تحته على طول، تتبع الصوت.

**When to use:**
- EN: Use when you need a boxed version of M-221.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-221.

#### `al-aud-222-fast` — Mic Pulse · Fast
**مايك ينبض · سريع**

*accent · any · timeline · easing: easeOutCubic · loop · 1.5s*

*Original: M-222*

Variant of M-222: أسرع بـ 40%

**Spec (EN):** A mic icon sits at the center while thin rings expand from it every 0.5s and fade (see M-150).

**Spec (AR):** أيقونة مايك بالنص، ومنها دواير رفيعة تكبر كل 0.5 ثانية وتختفي (شوف M-150).

**When to use:**
- EN: Use when you need a fast version of M-222.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-222.

#### `al-aud-222-slow` — Mic Pulse · Slow
**مايك ينبض · بطيء**

*accent · any · timeline · easing: easeOutCubic · loop · 1.5s*

*Original: M-222*

Variant of M-222: أبطأ بـ 60%

**Spec (EN):** A mic icon sits at the center while thin rings expand from it every 0.5s and fade (see M-150).

**Spec (AR):** أيقونة مايك بالنص، ومنها دواير رفيعة تكبر كل 0.5 ثانية وتختفي (شوف M-150).

**When to use:**
- EN: Use when you need a slow version of M-222.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-222.

#### `al-aud-222-gold` — Mic Pulse · Gold
**مايك ينبض · ذهبي**

*accent · any · timeline · easing: easeOutCubic · loop · 1.5s*

*Original: M-222*

Variant of M-222: نسخة ذهبية فاخرة

**Spec (EN):** A mic icon sits at the center while thin rings expand from it every 0.5s and fade (see M-150).

**Spec (AR):** أيقونة مايك بالنص، ومنها دواير رفيعة تكبر كل 0.5 ثانية وتختفي (شوف M-150).

**When to use:**
- EN: Use when you need a gold version of M-222.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-222.

#### `al-aud-222-boxed` — Mic Pulse · Boxed
**مايك ينبض · صندوق**

*accent · any · timeline · easing: easeOutCubic · loop · 1.5s*

*Original: M-222*

Variant of M-222: النص داخل صندوق ملون

**Spec (EN):** A mic icon sits at the center while thin rings expand from it every 0.5s and fade (see M-150).

**Spec (AR):** أيقونة مايك بالنص، ومنها دواير رفيعة تكبر كل 0.5 ثانية وتختفي (شوف M-150).

**When to use:**
- EN: Use when you need a boxed version of M-222.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-222.

#### `al-aud-223-fast` — Podcast Card · Fast
**بطاقة بودكاست · سريع**

*accent · any · depth · easing: spring · 0.5s in*

*Original: M-223*

Variant of M-223: أسرع بـ 40%

**Spec (EN):** A light card with avatar, episode title, show name and a small live waveform slides up with a spring and holds.

**Spec (AR):** بطاقة فاتحة فيها الصورة وعنوان الحلقة واسم البرنامج وموجة صغيرة، تطلع لفوق بحركة نابض وتثبت.

**When to use:**
- EN: Use when you need a fast version of M-223.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-223.

#### `al-aud-223-slow` — Podcast Card · Slow
**بطاقة بودكاست · بطيء**

*accent · any · depth · easing: spring · 0.5s in*

*Original: M-223*

Variant of M-223: أبطأ بـ 60%

**Spec (EN):** A light card with avatar, episode title, show name and a small live waveform slides up with a spring and holds.

**Spec (AR):** بطاقة فاتحة فيها الصورة وعنوان الحلقة واسم البرنامج وموجة صغيرة، تطلع لفوق بحركة نابض وتثبت.

**When to use:**
- EN: Use when you need a slow version of M-223.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-223.

#### `al-aud-223-gold` — Podcast Card · Gold
**بطاقة بودكاست · ذهبي**

*accent · any · depth · easing: spring · 0.5s in*

*Original: M-223*

Variant of M-223: نسخة ذهبية فاخرة

**Spec (EN):** A light card with avatar, episode title, show name and a small live waveform slides up with a spring and holds.

**Spec (AR):** بطاقة فاتحة فيها الصورة وعنوان الحلقة واسم البرنامج وموجة صغيرة، تطلع لفوق بحركة نابض وتثبت.

**When to use:**
- EN: Use when you need a gold version of M-223.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-223.

#### `al-aud-223-boxed` — Podcast Card · Boxed
**بطاقة بودكاست · صندوق**

*accent · any · depth · easing: spring · 0.5s in*

*Original: M-223*

Variant of M-223: النص داخل صندوق ملون

**Spec (EN):** A light card with avatar, episode title, show name and a small live waveform slides up with a spring and holds.

**Spec (AR):** بطاقة فاتحة فيها الصورة وعنوان الحلقة واسم البرنامج وموجة صغيرة، تطلع لفوق بحركة نابض وتثبت.

**When to use:**
- EN: Use when you need a boxed version of M-223.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-223.

#### `al-aud-224-fast` — Volume Meter · Fast
**مؤشر الصوت · سريع**

*accent · calm · depth · easing: linear · live*

*Original: M-224*

Variant of M-224: أسرع بـ 40%

**Spec (EN):** Stack 8–12 segments vertically; segments light up from the bottom with loudness (green, then yellow, then red at the top).

**Spec (AR):** رتّب 8 إلى 12 مربع فوق بعض، والمربعات تنور من تحت لفوق مع قوة الصوت (أخضر، وبعدين أصفر، وفوق أحمر).

**When to use:**
- EN: Use when you need a fast version of M-224.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-224.

#### `al-aud-224-slow` — Volume Meter · Slow
**مؤشر الصوت · بطيء**

*accent · calm · depth · easing: linear · live*

*Original: M-224*

Variant of M-224: أبطأ بـ 60%

**Spec (EN):** Stack 8–12 segments vertically; segments light up from the bottom with loudness (green, then yellow, then red at the top).

**Spec (AR):** رتّب 8 إلى 12 مربع فوق بعض، والمربعات تنور من تحت لفوق مع قوة الصوت (أخضر، وبعدين أصفر، وفوق أحمر).

**When to use:**
- EN: Use when you need a slow version of M-224.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-224.

#### `al-aud-224-gold` — Volume Meter · Gold
**مؤشر الصوت · ذهبي**

*accent · calm · depth · easing: linear · live*

*Original: M-224*

Variant of M-224: نسخة ذهبية فاخرة

**Spec (EN):** Stack 8–12 segments vertically; segments light up from the bottom with loudness (green, then yellow, then red at the top).

**Spec (AR):** رتّب 8 إلى 12 مربع فوق بعض، والمربعات تنور من تحت لفوق مع قوة الصوت (أخضر، وبعدين أصفر، وفوق أحمر).

**When to use:**
- EN: Use when you need a gold version of M-224.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-224.

#### `al-aud-224-boxed` — Volume Meter · Boxed
**مؤشر الصوت · صندوق**

*accent · calm · depth · easing: linear · live*

*Original: M-224*

Variant of M-224: النص داخل صندوق ملون

**Spec (EN):** Stack 8–12 segments vertically; segments light up from the bottom with loudness (green, then yellow, then red at the top).

**Spec (AR):** رتّب 8 إلى 12 مربع فوق بعض، والمربعات تنور من تحت لفوق مع قوة الصوت (أخضر، وبعدين أصفر، وفوق أحمر).

**When to use:**
- EN: Use when you need a boxed version of M-224.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-224.

#### `al-aud-225-fast` — BPM Counter · Fast
**عداد الإيقاع · سريع**

*accent · any · timeline · easing: easeOut · per beat*

*Original: M-225*

Variant of M-225: أسرع بـ 40%

**Spec (EN):** Show the tempo as a mono number with "BPM" and a dot that flashes to 150% on every beat.

**Spec (AR):** اعرض سرعة الإيقاع برقم mono مع كلمة "BPM"، ونقطة تكبر لـ 150% وتومض مع كل ضربة.

**When to use:**
- EN: Use when you need a fast version of M-225.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-225.

#### `al-aud-225-slow` — BPM Counter · Slow
**عداد الإيقاع · بطيء**

*accent · any · timeline · easing: easeOut · per beat*

*Original: M-225*

Variant of M-225: أبطأ بـ 60%

**Spec (EN):** Show the tempo as a mono number with "BPM" and a dot that flashes to 150% on every beat.

**Spec (AR):** اعرض سرعة الإيقاع برقم mono مع كلمة "BPM"، ونقطة تكبر لـ 150% وتومض مع كل ضربة.

**When to use:**
- EN: Use when you need a slow version of M-225.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-225.

#### `al-aud-225-gold` — BPM Counter · Gold
**عداد الإيقاع · ذهبي**

*accent · any · timeline · easing: easeOut · per beat*

*Original: M-225*

Variant of M-225: نسخة ذهبية فاخرة

**Spec (EN):** Show the tempo as a mono number with "BPM" and a dot that flashes to 150% on every beat.

**Spec (AR):** اعرض سرعة الإيقاع برقم mono مع كلمة "BPM"، ونقطة تكبر لـ 150% وتومض مع كل ضربة.

**When to use:**
- EN: Use when you need a gold version of M-225.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-225.

#### `al-aud-225-boxed` — BPM Counter · Boxed
**عداد الإيقاع · صندوق**

*accent · any · timeline · easing: easeOut · per beat*

*Original: M-225*

Variant of M-225: النص داخل صندوق ملون

**Spec (EN):** Show the tempo as a mono number with "BPM" and a dot that flashes to 150% on every beat.

**Spec (AR):** اعرض سرعة الإيقاع برقم mono مع كلمة "BPM"، ونقطة تكبر لـ 150% وتومض مع كل ضربة.

**When to use:**
- EN: Use when you need a boxed version of M-225.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-225.

### Screens & UI (الشاشات والواجهات) — 75 motions

#### `al-scr-226` — App Window Pop
**نافذة تطبيق تطلع**

*workhorse · high · timeline · easing: easeOutBack · 0.4s*

*Original: M-226*

A desktop app window pops up while you explain.

**Spec (EN):** A rounded window with three title-bar dots and a title scales from 60% to 104% to 100% with a fade over 0.4s, showing your screenshot or screen recording inside.

**Spec (AR):** نافذة بزوايا دائرية فوقها ثلاث نقاط وعنوان، تكبر من 60% لـ 104% لـ 100% وهي تظهر خلال 0.4 ثانية، وداخلها صورة شاشتك أو تسجيلها.

**When to use:**
- EN: A desktop app window pops up while you explain.
- AR: نافذة برنامج أو موقع تطلع قدامك وانت تشرح.

#### `al-scr-227` — Phone Scroll
**جوال يسكرول**

*workhorse · any · depth · easing: easeInOutCubic · 2s scroll*

*Original: M-227*

Shows an app or page scrolling inside a phone.

**Spec (EN):** A phone frame with rounded corners shows your screen recording or a long screenshot that scrolls up smoothly inside it, then eases to a stop.

**Spec (AR):** إطار جوال بزوايا دائرية يعرض تسجيل شاشتك أو صورة طويلة تتحرك لفوق بنعومة داخله، وبعدين توقف بهدوء.

**When to use:**
- EN: Shows an app or page scrolling inside a phone.
- AR: تعرض تطبيق أو صفحة على جوال يتحرك لتحت.

#### `al-scr-228` — Laptop Mockup
**شاشتك داخل لابتوب**

*workhorse · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-228*

Places your screen recording inside a laptop.

**Spec (EN):** A laptop mockup (screen bezel and base) rises 10% with a fade over 0.6s; your screen recording plays inside the screen area.

**Spec (AR):** لابتوب (إطار الشاشة والقاعدة) يطلع لفوق 10% ويظهر خلال 0.6 ثانية، وتسجيل شاشتك يشتغل داخل الشاشة.

**When to use:**
- EN: Places your screen recording inside a laptop.
- AR: تعرض تسجيل شاشتك داخل لابتوب.

#### `al-scr-229` — Browser Window
**نافذة متصفح**

*workhorse · high · timeline · easing: easeOutBack · 0.4s*

*Original: M-229*

A website inside a browser window with a URL bar.

**Spec (EN):** A browser window with dots, a URL bar showing your site, and the page content pops in; the URL can type itself first (see M-180).

**Spec (AR):** نافذة متصفح فيها النقاط وشريط رابط فيه موقعك ومحتوى الصفحة، تنط وتطلع، والرابط ممكن ينكتب أول (شوف M-180).

**When to use:**
- EN: A website inside a browser window with a URL bar.
- AR: موقع داخل نافذة متصفح فيها رابط.

#### `al-scr-230` — Phone Slide In
**جوال يدخل من الجنب**

*workhorse · any · timeline · easing: easeOutCubic · 0.5s*

*Original: M-230*

A phone with your app slides in next to you.

**Spec (EN):** A phone mockup slides in from the side edge with a slight tilt that straightens over 0.5s, then holds beside the speaker.

**Spec (AR):** جوال فيه تطبيقك يدخل من حافة الشاشة مايل شوي ويستقيم خلال 0.5 ثانية، ويثبت جنب المتكلم.

**When to use:**
- EN: A phone with your app slides in next to you.
- AR: جوال فيه تطبيقك يدخل جنبك وانت تتكلم.

#### `al-scr-231` — Cursor Click
**مؤشر يضغط**

*workhorse · any · timeline · easing: easeInOutCubic · 1s*

*Original: M-231*

A mouse cursor glides over and clicks a button.

**Spec (EN):** A cursor arrow moves along a smooth curve to a button, scales to 85% on click, and a white ring expands from the click point.

**Spec (AR):** سهم ماوس يتحرك على مسار ناعم لين زر، يصغر لـ 85% وقت الضغط، ودائرة بيضا تكبر من مكان الضغطة.

**When to use:**
- EN: A mouse cursor glides over and clicks a button.
- AR: ماوس يتحرك ويضغط على زر في الشاشة.

#### `al-scr-232` — Zoom to Cursor
**زوم على الماوس**

*workhorse · any · timeline · easing: easeInOutCubic · 0.6s*

*Original: M-232*

A zoom that follows the cursor in a screen recording.

**Spec (EN):** In a screen recording, zoom to about 180% centered on the cursor position over 0.6s, follow it smoothly while zoomed, then zoom back out.

**Spec (AR):** في تسجيل الشاشة، سوّ زوم لـ تقريباً 180% على مكان الماوس خلال 0.6 ثانية، واتبعه بنعومة وانت مقرّب، وبعدين ارجع.

**When to use:**
- EN: A zoom that follows the cursor in a screen recording.
- AR: زوم يتبع مكان الماوس في تسجيل الشاشة.

#### `al-scr-233` — Modal Pop
**نافذة منبثقة**

*workhorse · high · depth · easing: easeOutBack · 0.3s*

*Original: M-233*

A dialog pops up over a dimmed background.

**Spec (EN):** The background dims to about 55% black while a rounded dialog card scales from 90% to 102% to 100% over 0.3s.

**Spec (AR):** الخلفية تغمق تقريباً 55% أسود، ونافذة بزوايا دائرية تكبر من 90% لـ 102% لـ 100% خلال 0.3 ثانية.

**When to use:**
- EN: A dialog pops up over a dimmed background.
- AR: نافذة تنبيه أو سؤال تطلع وراها خلفية غامقة.

#### `al-scr-234` — Toggle Switch
**زر تشغيل**

*workhorse · any · timeline · easing: easeInOutCubic · 0.3s*

*Original: M-234*

A switch flips from off to on.

**Spec (EN):** A pill toggle: the knob slides to the other side over 0.3s while the track color changes from gray to the accent.

**Spec (AR):** زر على شكل كبسولة: الدائرة تنزلق للجهة الثانية خلال 0.3 ثانية ولون المسار يتحول من رمادي للون الهوية.

**When to use:**
- EN: A switch flips from off to on.
- AR: زر يتحول من مطفي لشغال.

#### `al-scr-235` — Loading Spinner
**دائرة تحميل**

*workhorse · calm · depth · easing: linear · loop · 0.8s*

*Original: M-235*

A "one moment" spinner before the result.

**Spec (EN):** A ring with one accent segment rotates one full turn every 0.8s; replace it with the result when it finishes.

**Spec (AR):** حلقة فيها جزء بلون الهوية تلف لفة كاملة كل 0.8 ثانية، وبعدين بدّلها بالنتيجة لمن تخلص.

**When to use:**
- EN: A "one moment" spinner before the result.
- AR: "لحظة…" قبل ما تطلع النتيجة.

#### `al-scr-236` — Notification Stack
**إشعارات فوق بعض**

*workhorse · any · timeline · easing: spring · 0.3s each*

*Original: M-236*

Notifications stacking up, like many messages arriving.

**Spec (EN):** Notification cards drop in from the top one after another, 0.4s apart; each new card pushes the earlier ones down slightly.

**Spec (AR):** بطاقات إشعار تنزل من فوق وحدة ورا الثانية وبينهم 0.4 ثانية، وكل بطاقة جديدة تنزّل اللي قبلها شوي.

**When to use:**
- EN: Notifications stacking up, like many messages arriving.
- AR: إشعارات تتكدس ورا بعض، مثل لمن يوصلك رسايل كثيرة.

#### `al-scr-237` — Keyboard Shortcut
**اختصار كيبورد**

*workhorse · any · timeline · easing: easeOut · 0.6s*

*Original: M-237*

Shows a shortcut like Ctrl + C being pressed.

**Spec (EN):** Key caps appear side by side; each key presses down (moves 2% and turns accent) in order, 0.15s apart.

**Spec (AR):** أزرار الكيبورد تطلع جنب بعض، وكل زر ينضغط (ينزل 2% ويصير بلون الهوية) بالترتيب وبينهم 0.15 ثانية.

**When to use:**
- EN: Shows a shortcut like Ctrl + C being pressed.
- AR: تعرض اختصار مثل Ctrl + C وهو ينضغط.

#### `al-scr-238` — Tab Switch
**تبديل تبويب**

*workhorse · any · timeline · easing: easeInOutCubic · 0.35s*

*Original: M-238*

Tabs change and the content slides.

**Spec (EN):** An accent underline slides from one tab to the next while the content panel slides across in the same direction over 0.35s.

**Spec (AR):** خط بلون الهوية ينزلق من تبويب للثاني، ولوحة المحتوى تنزلق بنفس الاتجاه خلال 0.35 ثانية.

**When to use:**
- EN: Tabs change and the content slides.
- AR: التبويب يتغير والمحتوى ينزلق.

#### `al-scr-239` — Form Fill
**تعبئة نموذج**

*workhorse · any · timeline · easing: steps · ~0.8s per field*

*Original: M-239*

Form fields fill in one after another, for tutorials.

**Spec (EN):** Each labelled field types its value in order (see M-082), and a checkmark appears at the end of each field when done.

**Spec (AR):** كل خانة لها عنوان تنكتب قيمتها بالترتيب (شوف M-082)، وتطلع علامة صح بآخر كل خانة لمن تخلص.

**When to use:**
- EN: Form fields fill in one after another, for tutorials.
- AR: خانات تتعبى ورا بعض، للشروحات.

#### `al-scr-240` — Upload Progress
**رفع ملف**

*workhorse · any · depth · easing: easeInOutCubic · 1.2s*

*Original: M-240*

A file uploading with a progress bar.

**Spec (EN):** A file card with an icon and name shows a progress bar filling from 0 to 100% while the percentage counts up, then a check appears.

**Spec (AR):** بطاقة ملف فيها أيقونة واسم، وشريط تقدم يتعبى من 0 لـ 100% والنسبة تعد، وبعدين تطلع علامة صح.

**When to use:**
- EN: A file uploading with a progress bar.
- AR: ملف ينرفع مع شريط تقدم.

#### `al-scr-226-fast` — App Window Pop · Fast
**نافذة تطبيق تطلع · سريع**

*accent · any · timeline · easing: easeOutBack · 0.4s*

*Original: M-226*

Variant of M-226: أسرع بـ 40%

**Spec (EN):** A rounded window with three title-bar dots and a title scales from 60% to 104% to 100% with a fade over 0.4s, showing your screenshot or screen recording inside.

**Spec (AR):** نافذة بزوايا دائرية فوقها ثلاث نقاط وعنوان، تكبر من 60% لـ 104% لـ 100% وهي تظهر خلال 0.4 ثانية، وداخلها صورة شاشتك أو تسجيلها.

**When to use:**
- EN: Use when you need a fast version of M-226.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-226.

#### `al-scr-226-slow` — App Window Pop · Slow
**نافذة تطبيق تطلع · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.4s*

*Original: M-226*

Variant of M-226: أبطأ بـ 60%

**Spec (EN):** A rounded window with three title-bar dots and a title scales from 60% to 104% to 100% with a fade over 0.4s, showing your screenshot or screen recording inside.

**Spec (AR):** نافذة بزوايا دائرية فوقها ثلاث نقاط وعنوان، تكبر من 60% لـ 104% لـ 100% وهي تظهر خلال 0.4 ثانية، وداخلها صورة شاشتك أو تسجيلها.

**When to use:**
- EN: Use when you need a slow version of M-226.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-226.

#### `al-scr-226-gold` — App Window Pop · Gold
**نافذة تطبيق تطلع · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.4s*

*Original: M-226*

Variant of M-226: نسخة ذهبية فاخرة

**Spec (EN):** A rounded window with three title-bar dots and a title scales from 60% to 104% to 100% with a fade over 0.4s, showing your screenshot or screen recording inside.

**Spec (AR):** نافذة بزوايا دائرية فوقها ثلاث نقاط وعنوان، تكبر من 60% لـ 104% لـ 100% وهي تظهر خلال 0.4 ثانية، وداخلها صورة شاشتك أو تسجيلها.

**When to use:**
- EN: Use when you need a gold version of M-226.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-226.

#### `al-scr-226-boxed` — App Window Pop · Boxed
**نافذة تطبيق تطلع · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.4s*

*Original: M-226*

Variant of M-226: النص داخل صندوق ملون

**Spec (EN):** A rounded window with three title-bar dots and a title scales from 60% to 104% to 100% with a fade over 0.4s, showing your screenshot or screen recording inside.

**Spec (AR):** نافذة بزوايا دائرية فوقها ثلاث نقاط وعنوان، تكبر من 60% لـ 104% لـ 100% وهي تظهر خلال 0.4 ثانية، وداخلها صورة شاشتك أو تسجيلها.

**When to use:**
- EN: Use when you need a boxed version of M-226.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-226.

#### `al-scr-227-fast` — Phone Scroll · Fast
**جوال يسكرول · سريع**

*accent · any · depth · easing: easeInOutCubic · 2s scroll*

*Original: M-227*

Variant of M-227: أسرع بـ 40%

**Spec (EN):** A phone frame with rounded corners shows your screen recording or a long screenshot that scrolls up smoothly inside it, then eases to a stop.

**Spec (AR):** إطار جوال بزوايا دائرية يعرض تسجيل شاشتك أو صورة طويلة تتحرك لفوق بنعومة داخله، وبعدين توقف بهدوء.

**When to use:**
- EN: Use when you need a fast version of M-227.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-227.

#### `al-scr-227-slow` — Phone Scroll · Slow
**جوال يسكرول · بطيء**

*accent · any · depth · easing: easeInOutCubic · 2s scroll*

*Original: M-227*

Variant of M-227: أبطأ بـ 60%

**Spec (EN):** A phone frame with rounded corners shows your screen recording or a long screenshot that scrolls up smoothly inside it, then eases to a stop.

**Spec (AR):** إطار جوال بزوايا دائرية يعرض تسجيل شاشتك أو صورة طويلة تتحرك لفوق بنعومة داخله، وبعدين توقف بهدوء.

**When to use:**
- EN: Use when you need a slow version of M-227.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-227.

#### `al-scr-227-gold` — Phone Scroll · Gold
**جوال يسكرول · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 2s scroll*

*Original: M-227*

Variant of M-227: نسخة ذهبية فاخرة

**Spec (EN):** A phone frame with rounded corners shows your screen recording or a long screenshot that scrolls up smoothly inside it, then eases to a stop.

**Spec (AR):** إطار جوال بزوايا دائرية يعرض تسجيل شاشتك أو صورة طويلة تتحرك لفوق بنعومة داخله، وبعدين توقف بهدوء.

**When to use:**
- EN: Use when you need a gold version of M-227.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-227.

#### `al-scr-227-boxed` — Phone Scroll · Boxed
**جوال يسكرول · صندوق**

*accent · any · depth · easing: easeInOutCubic · 2s scroll*

*Original: M-227*

Variant of M-227: النص داخل صندوق ملون

**Spec (EN):** A phone frame with rounded corners shows your screen recording or a long screenshot that scrolls up smoothly inside it, then eases to a stop.

**Spec (AR):** إطار جوال بزوايا دائرية يعرض تسجيل شاشتك أو صورة طويلة تتحرك لفوق بنعومة داخله، وبعدين توقف بهدوء.

**When to use:**
- EN: Use when you need a boxed version of M-227.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-227.

#### `al-scr-228-fast` — Laptop Mockup · Fast
**شاشتك داخل لابتوب · سريع**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-228*

Variant of M-228: أسرع بـ 40%

**Spec (EN):** A laptop mockup (screen bezel and base) rises 10% with a fade over 0.6s; your screen recording plays inside the screen area.

**Spec (AR):** لابتوب (إطار الشاشة والقاعدة) يطلع لفوق 10% ويظهر خلال 0.6 ثانية، وتسجيل شاشتك يشتغل داخل الشاشة.

**When to use:**
- EN: Use when you need a fast version of M-228.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-228.

#### `al-scr-228-slow` — Laptop Mockup · Slow
**شاشتك داخل لابتوب · بطيء**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-228*

Variant of M-228: أبطأ بـ 60%

**Spec (EN):** A laptop mockup (screen bezel and base) rises 10% with a fade over 0.6s; your screen recording plays inside the screen area.

**Spec (AR):** لابتوب (إطار الشاشة والقاعدة) يطلع لفوق 10% ويظهر خلال 0.6 ثانية، وتسجيل شاشتك يشتغل داخل الشاشة.

**When to use:**
- EN: Use when you need a slow version of M-228.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-228.

#### `al-scr-228-gold` — Laptop Mockup · Gold
**شاشتك داخل لابتوب · ذهبي**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-228*

Variant of M-228: نسخة ذهبية فاخرة

**Spec (EN):** A laptop mockup (screen bezel and base) rises 10% with a fade over 0.6s; your screen recording plays inside the screen area.

**Spec (AR):** لابتوب (إطار الشاشة والقاعدة) يطلع لفوق 10% ويظهر خلال 0.6 ثانية، وتسجيل شاشتك يشتغل داخل الشاشة.

**When to use:**
- EN: Use when you need a gold version of M-228.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-228.

#### `al-scr-228-boxed` — Laptop Mockup · Boxed
**شاشتك داخل لابتوب · صندوق**

*accent · any · depth · easing: easeOutCubic · 0.6s in*

*Original: M-228*

Variant of M-228: النص داخل صندوق ملون

**Spec (EN):** A laptop mockup (screen bezel and base) rises 10% with a fade over 0.6s; your screen recording plays inside the screen area.

**Spec (AR):** لابتوب (إطار الشاشة والقاعدة) يطلع لفوق 10% ويظهر خلال 0.6 ثانية، وتسجيل شاشتك يشتغل داخل الشاشة.

**When to use:**
- EN: Use when you need a boxed version of M-228.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-228.

#### `al-scr-229-fast` — Browser Window · Fast
**نافذة متصفح · سريع**

*accent · any · timeline · easing: easeOutBack · 0.4s*

*Original: M-229*

Variant of M-229: أسرع بـ 40%

**Spec (EN):** A browser window with dots, a URL bar showing your site, and the page content pops in; the URL can type itself first (see M-180).

**Spec (AR):** نافذة متصفح فيها النقاط وشريط رابط فيه موقعك ومحتوى الصفحة، تنط وتطلع، والرابط ممكن ينكتب أول (شوف M-180).

**When to use:**
- EN: Use when you need a fast version of M-229.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-229.

#### `al-scr-229-slow` — Browser Window · Slow
**نافذة متصفح · بطيء**

*accent · any · timeline · easing: easeOutBack · 0.4s*

*Original: M-229*

Variant of M-229: أبطأ بـ 60%

**Spec (EN):** A browser window with dots, a URL bar showing your site, and the page content pops in; the URL can type itself first (see M-180).

**Spec (AR):** نافذة متصفح فيها النقاط وشريط رابط فيه موقعك ومحتوى الصفحة، تنط وتطلع، والرابط ممكن ينكتب أول (شوف M-180).

**When to use:**
- EN: Use when you need a slow version of M-229.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-229.

#### `al-scr-229-gold` — Browser Window · Gold
**نافذة متصفح · ذهبي**

*accent · any · timeline · easing: easeOutBack · 0.4s*

*Original: M-229*

Variant of M-229: نسخة ذهبية فاخرة

**Spec (EN):** A browser window with dots, a URL bar showing your site, and the page content pops in; the URL can type itself first (see M-180).

**Spec (AR):** نافذة متصفح فيها النقاط وشريط رابط فيه موقعك ومحتوى الصفحة، تنط وتطلع، والرابط ممكن ينكتب أول (شوف M-180).

**When to use:**
- EN: Use when you need a gold version of M-229.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-229.

#### `al-scr-229-boxed` — Browser Window · Boxed
**نافذة متصفح · صندوق**

*accent · any · timeline · easing: easeOutBack · 0.4s*

*Original: M-229*

Variant of M-229: النص داخل صندوق ملون

**Spec (EN):** A browser window with dots, a URL bar showing your site, and the page content pops in; the URL can type itself first (see M-180).

**Spec (AR):** نافذة متصفح فيها النقاط وشريط رابط فيه موقعك ومحتوى الصفحة، تنط وتطلع، والرابط ممكن ينكتب أول (شوف M-180).

**When to use:**
- EN: Use when you need a boxed version of M-229.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-229.

#### `al-scr-230-fast` — Phone Slide In · Fast
**جوال يدخل من الجنب · سريع**

*accent · any · timeline · easing: easeOutCubic · 0.5s*

*Original: M-230*

Variant of M-230: أسرع بـ 40%

**Spec (EN):** A phone mockup slides in from the side edge with a slight tilt that straightens over 0.5s, then holds beside the speaker.

**Spec (AR):** جوال فيه تطبيقك يدخل من حافة الشاشة مايل شوي ويستقيم خلال 0.5 ثانية، ويثبت جنب المتكلم.

**When to use:**
- EN: Use when you need a fast version of M-230.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-230.

#### `al-scr-230-slow` — Phone Slide In · Slow
**جوال يدخل من الجنب · بطيء**

*accent · any · timeline · easing: easeOutCubic · 0.5s*

*Original: M-230*

Variant of M-230: أبطأ بـ 60%

**Spec (EN):** A phone mockup slides in from the side edge with a slight tilt that straightens over 0.5s, then holds beside the speaker.

**Spec (AR):** جوال فيه تطبيقك يدخل من حافة الشاشة مايل شوي ويستقيم خلال 0.5 ثانية، ويثبت جنب المتكلم.

**When to use:**
- EN: Use when you need a slow version of M-230.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-230.

#### `al-scr-230-gold` — Phone Slide In · Gold
**جوال يدخل من الجنب · ذهبي**

*accent · any · timeline · easing: easeOutCubic · 0.5s*

*Original: M-230*

Variant of M-230: نسخة ذهبية فاخرة

**Spec (EN):** A phone mockup slides in from the side edge with a slight tilt that straightens over 0.5s, then holds beside the speaker.

**Spec (AR):** جوال فيه تطبيقك يدخل من حافة الشاشة مايل شوي ويستقيم خلال 0.5 ثانية، ويثبت جنب المتكلم.

**When to use:**
- EN: Use when you need a gold version of M-230.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-230.

#### `al-scr-230-boxed` — Phone Slide In · Boxed
**جوال يدخل من الجنب · صندوق**

*accent · any · timeline · easing: easeOutCubic · 0.5s*

*Original: M-230*

Variant of M-230: النص داخل صندوق ملون

**Spec (EN):** A phone mockup slides in from the side edge with a slight tilt that straightens over 0.5s, then holds beside the speaker.

**Spec (AR):** جوال فيه تطبيقك يدخل من حافة الشاشة مايل شوي ويستقيم خلال 0.5 ثانية، ويثبت جنب المتكلم.

**When to use:**
- EN: Use when you need a boxed version of M-230.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-230.

#### `al-scr-231-fast` — Cursor Click · Fast
**مؤشر يضغط · سريع**

*accent · any · timeline · easing: easeInOutCubic · 1s*

*Original: M-231*

Variant of M-231: أسرع بـ 40%

**Spec (EN):** A cursor arrow moves along a smooth curve to a button, scales to 85% on click, and a white ring expands from the click point.

**Spec (AR):** سهم ماوس يتحرك على مسار ناعم لين زر، يصغر لـ 85% وقت الضغط، ودائرة بيضا تكبر من مكان الضغطة.

**When to use:**
- EN: Use when you need a fast version of M-231.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-231.

#### `al-scr-231-slow` — Cursor Click · Slow
**مؤشر يضغط · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 1s*

*Original: M-231*

Variant of M-231: أبطأ بـ 60%

**Spec (EN):** A cursor arrow moves along a smooth curve to a button, scales to 85% on click, and a white ring expands from the click point.

**Spec (AR):** سهم ماوس يتحرك على مسار ناعم لين زر، يصغر لـ 85% وقت الضغط، ودائرة بيضا تكبر من مكان الضغطة.

**When to use:**
- EN: Use when you need a slow version of M-231.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-231.

#### `al-scr-231-gold` — Cursor Click · Gold
**مؤشر يضغط · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 1s*

*Original: M-231*

Variant of M-231: نسخة ذهبية فاخرة

**Spec (EN):** A cursor arrow moves along a smooth curve to a button, scales to 85% on click, and a white ring expands from the click point.

**Spec (AR):** سهم ماوس يتحرك على مسار ناعم لين زر، يصغر لـ 85% وقت الضغط، ودائرة بيضا تكبر من مكان الضغطة.

**When to use:**
- EN: Use when you need a gold version of M-231.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-231.

#### `al-scr-231-boxed` — Cursor Click · Boxed
**مؤشر يضغط · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 1s*

*Original: M-231*

Variant of M-231: النص داخل صندوق ملون

**Spec (EN):** A cursor arrow moves along a smooth curve to a button, scales to 85% on click, and a white ring expands from the click point.

**Spec (AR):** سهم ماوس يتحرك على مسار ناعم لين زر، يصغر لـ 85% وقت الضغط، ودائرة بيضا تكبر من مكان الضغطة.

**When to use:**
- EN: Use when you need a boxed version of M-231.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-231.

#### `al-scr-232-fast` — Zoom to Cursor · Fast
**زوم على الماوس · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.6s*

*Original: M-232*

Variant of M-232: أسرع بـ 40%

**Spec (EN):** In a screen recording, zoom to about 180% centered on the cursor position over 0.6s, follow it smoothly while zoomed, then zoom back out.

**Spec (AR):** في تسجيل الشاشة، سوّ زوم لـ تقريباً 180% على مكان الماوس خلال 0.6 ثانية، واتبعه بنعومة وانت مقرّب، وبعدين ارجع.

**When to use:**
- EN: Use when you need a fast version of M-232.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-232.

#### `al-scr-232-slow` — Zoom to Cursor · Slow
**زوم على الماوس · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.6s*

*Original: M-232*

Variant of M-232: أبطأ بـ 60%

**Spec (EN):** In a screen recording, zoom to about 180% centered on the cursor position over 0.6s, follow it smoothly while zoomed, then zoom back out.

**Spec (AR):** في تسجيل الشاشة، سوّ زوم لـ تقريباً 180% على مكان الماوس خلال 0.6 ثانية، واتبعه بنعومة وانت مقرّب، وبعدين ارجع.

**When to use:**
- EN: Use when you need a slow version of M-232.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-232.

#### `al-scr-232-gold` — Zoom to Cursor · Gold
**زوم على الماوس · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.6s*

*Original: M-232*

Variant of M-232: نسخة ذهبية فاخرة

**Spec (EN):** In a screen recording, zoom to about 180% centered on the cursor position over 0.6s, follow it smoothly while zoomed, then zoom back out.

**Spec (AR):** في تسجيل الشاشة، سوّ زوم لـ تقريباً 180% على مكان الماوس خلال 0.6 ثانية، واتبعه بنعومة وانت مقرّب، وبعدين ارجع.

**When to use:**
- EN: Use when you need a gold version of M-232.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-232.

#### `al-scr-232-boxed` — Zoom to Cursor · Boxed
**زوم على الماوس · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.6s*

*Original: M-232*

Variant of M-232: النص داخل صندوق ملون

**Spec (EN):** In a screen recording, zoom to about 180% centered on the cursor position over 0.6s, follow it smoothly while zoomed, then zoom back out.

**Spec (AR):** في تسجيل الشاشة، سوّ زوم لـ تقريباً 180% على مكان الماوس خلال 0.6 ثانية، واتبعه بنعومة وانت مقرّب، وبعدين ارجع.

**When to use:**
- EN: Use when you need a boxed version of M-232.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-232.

#### `al-scr-233-fast` — Modal Pop · Fast
**نافذة منبثقة · سريع**

*accent · any · depth · easing: easeOutBack · 0.3s*

*Original: M-233*

Variant of M-233: أسرع بـ 40%

**Spec (EN):** The background dims to about 55% black while a rounded dialog card scales from 90% to 102% to 100% over 0.3s.

**Spec (AR):** الخلفية تغمق تقريباً 55% أسود، ونافذة بزوايا دائرية تكبر من 90% لـ 102% لـ 100% خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-233.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-233.

#### `al-scr-233-slow` — Modal Pop · Slow
**نافذة منبثقة · بطيء**

*accent · any · depth · easing: easeOutBack · 0.3s*

*Original: M-233*

Variant of M-233: أبطأ بـ 60%

**Spec (EN):** The background dims to about 55% black while a rounded dialog card scales from 90% to 102% to 100% over 0.3s.

**Spec (AR):** الخلفية تغمق تقريباً 55% أسود، ونافذة بزوايا دائرية تكبر من 90% لـ 102% لـ 100% خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-233.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-233.

#### `al-scr-233-gold` — Modal Pop · Gold
**نافذة منبثقة · ذهبي**

*accent · any · depth · easing: easeOutBack · 0.3s*

*Original: M-233*

Variant of M-233: نسخة ذهبية فاخرة

**Spec (EN):** The background dims to about 55% black while a rounded dialog card scales from 90% to 102% to 100% over 0.3s.

**Spec (AR):** الخلفية تغمق تقريباً 55% أسود، ونافذة بزوايا دائرية تكبر من 90% لـ 102% لـ 100% خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-233.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-233.

#### `al-scr-233-boxed` — Modal Pop · Boxed
**نافذة منبثقة · صندوق**

*accent · any · depth · easing: easeOutBack · 0.3s*

*Original: M-233*

Variant of M-233: النص داخل صندوق ملون

**Spec (EN):** The background dims to about 55% black while a rounded dialog card scales from 90% to 102% to 100% over 0.3s.

**Spec (AR):** الخلفية تغمق تقريباً 55% أسود، ونافذة بزوايا دائرية تكبر من 90% لـ 102% لـ 100% خلال 0.3 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-233.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-233.

#### `al-scr-234-fast` — Toggle Switch · Fast
**زر تشغيل · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.3s*

*Original: M-234*

Variant of M-234: أسرع بـ 40%

**Spec (EN):** A pill toggle: the knob slides to the other side over 0.3s while the track color changes from gray to the accent.

**Spec (AR):** زر على شكل كبسولة: الدائرة تنزلق للجهة الثانية خلال 0.3 ثانية ولون المسار يتحول من رمادي للون الهوية.

**When to use:**
- EN: Use when you need a fast version of M-234.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-234.

#### `al-scr-234-slow` — Toggle Switch · Slow
**زر تشغيل · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.3s*

*Original: M-234*

Variant of M-234: أبطأ بـ 60%

**Spec (EN):** A pill toggle: the knob slides to the other side over 0.3s while the track color changes from gray to the accent.

**Spec (AR):** زر على شكل كبسولة: الدائرة تنزلق للجهة الثانية خلال 0.3 ثانية ولون المسار يتحول من رمادي للون الهوية.

**When to use:**
- EN: Use when you need a slow version of M-234.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-234.

#### `al-scr-234-gold` — Toggle Switch · Gold
**زر تشغيل · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.3s*

*Original: M-234*

Variant of M-234: نسخة ذهبية فاخرة

**Spec (EN):** A pill toggle: the knob slides to the other side over 0.3s while the track color changes from gray to the accent.

**Spec (AR):** زر على شكل كبسولة: الدائرة تنزلق للجهة الثانية خلال 0.3 ثانية ولون المسار يتحول من رمادي للون الهوية.

**When to use:**
- EN: Use when you need a gold version of M-234.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-234.

#### `al-scr-234-boxed` — Toggle Switch · Boxed
**زر تشغيل · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.3s*

*Original: M-234*

Variant of M-234: النص داخل صندوق ملون

**Spec (EN):** A pill toggle: the knob slides to the other side over 0.3s while the track color changes from gray to the accent.

**Spec (AR):** زر على شكل كبسولة: الدائرة تنزلق للجهة الثانية خلال 0.3 ثانية ولون المسار يتحول من رمادي للون الهوية.

**When to use:**
- EN: Use when you need a boxed version of M-234.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-234.

#### `al-scr-235-fast` — Loading Spinner · Fast
**دائرة تحميل · سريع**

*accent · calm · depth · easing: linear · loop · 0.8s*

*Original: M-235*

Variant of M-235: أسرع بـ 40%

**Spec (EN):** A ring with one accent segment rotates one full turn every 0.8s; replace it with the result when it finishes.

**Spec (AR):** حلقة فيها جزء بلون الهوية تلف لفة كاملة كل 0.8 ثانية، وبعدين بدّلها بالنتيجة لمن تخلص.

**When to use:**
- EN: Use when you need a fast version of M-235.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-235.

#### `al-scr-235-slow` — Loading Spinner · Slow
**دائرة تحميل · بطيء**

*accent · calm · depth · easing: linear · loop · 0.8s*

*Original: M-235*

Variant of M-235: أبطأ بـ 60%

**Spec (EN):** A ring with one accent segment rotates one full turn every 0.8s; replace it with the result when it finishes.

**Spec (AR):** حلقة فيها جزء بلون الهوية تلف لفة كاملة كل 0.8 ثانية، وبعدين بدّلها بالنتيجة لمن تخلص.

**When to use:**
- EN: Use when you need a slow version of M-235.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-235.

#### `al-scr-235-gold` — Loading Spinner · Gold
**دائرة تحميل · ذهبي**

*accent · calm · depth · easing: linear · loop · 0.8s*

*Original: M-235*

Variant of M-235: نسخة ذهبية فاخرة

**Spec (EN):** A ring with one accent segment rotates one full turn every 0.8s; replace it with the result when it finishes.

**Spec (AR):** حلقة فيها جزء بلون الهوية تلف لفة كاملة كل 0.8 ثانية، وبعدين بدّلها بالنتيجة لمن تخلص.

**When to use:**
- EN: Use when you need a gold version of M-235.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-235.

#### `al-scr-235-boxed` — Loading Spinner · Boxed
**دائرة تحميل · صندوق**

*accent · calm · depth · easing: linear · loop · 0.8s*

*Original: M-235*

Variant of M-235: النص داخل صندوق ملون

**Spec (EN):** A ring with one accent segment rotates one full turn every 0.8s; replace it with the result when it finishes.

**Spec (AR):** حلقة فيها جزء بلون الهوية تلف لفة كاملة كل 0.8 ثانية، وبعدين بدّلها بالنتيجة لمن تخلص.

**When to use:**
- EN: Use when you need a boxed version of M-235.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-235.

#### `al-scr-236-fast` — Notification Stack · Fast
**إشعارات فوق بعض · سريع**

*accent · any · timeline · easing: spring · 0.3s each*

*Original: M-236*

Variant of M-236: أسرع بـ 40%

**Spec (EN):** Notification cards drop in from the top one after another, 0.4s apart; each new card pushes the earlier ones down slightly.

**Spec (AR):** بطاقات إشعار تنزل من فوق وحدة ورا الثانية وبينهم 0.4 ثانية، وكل بطاقة جديدة تنزّل اللي قبلها شوي.

**When to use:**
- EN: Use when you need a fast version of M-236.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-236.

#### `al-scr-236-slow` — Notification Stack · Slow
**إشعارات فوق بعض · بطيء**

*accent · any · timeline · easing: spring · 0.3s each*

*Original: M-236*

Variant of M-236: أبطأ بـ 60%

**Spec (EN):** Notification cards drop in from the top one after another, 0.4s apart; each new card pushes the earlier ones down slightly.

**Spec (AR):** بطاقات إشعار تنزل من فوق وحدة ورا الثانية وبينهم 0.4 ثانية، وكل بطاقة جديدة تنزّل اللي قبلها شوي.

**When to use:**
- EN: Use when you need a slow version of M-236.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-236.

#### `al-scr-236-gold` — Notification Stack · Gold
**إشعارات فوق بعض · ذهبي**

*accent · any · timeline · easing: spring · 0.3s each*

*Original: M-236*

Variant of M-236: نسخة ذهبية فاخرة

**Spec (EN):** Notification cards drop in from the top one after another, 0.4s apart; each new card pushes the earlier ones down slightly.

**Spec (AR):** بطاقات إشعار تنزل من فوق وحدة ورا الثانية وبينهم 0.4 ثانية، وكل بطاقة جديدة تنزّل اللي قبلها شوي.

**When to use:**
- EN: Use when you need a gold version of M-236.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-236.

#### `al-scr-236-boxed` — Notification Stack · Boxed
**إشعارات فوق بعض · صندوق**

*accent · any · timeline · easing: spring · 0.3s each*

*Original: M-236*

Variant of M-236: النص داخل صندوق ملون

**Spec (EN):** Notification cards drop in from the top one after another, 0.4s apart; each new card pushes the earlier ones down slightly.

**Spec (AR):** بطاقات إشعار تنزل من فوق وحدة ورا الثانية وبينهم 0.4 ثانية، وكل بطاقة جديدة تنزّل اللي قبلها شوي.

**When to use:**
- EN: Use when you need a boxed version of M-236.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-236.

#### `al-scr-237-fast` — Keyboard Shortcut · Fast
**اختصار كيبورد · سريع**

*accent · any · timeline · easing: easeOut · 0.6s*

*Original: M-237*

Variant of M-237: أسرع بـ 40%

**Spec (EN):** Key caps appear side by side; each key presses down (moves 2% and turns accent) in order, 0.15s apart.

**Spec (AR):** أزرار الكيبورد تطلع جنب بعض، وكل زر ينضغط (ينزل 2% ويصير بلون الهوية) بالترتيب وبينهم 0.15 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-237.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-237.

#### `al-scr-237-slow` — Keyboard Shortcut · Slow
**اختصار كيبورد · بطيء**

*accent · any · timeline · easing: easeOut · 0.6s*

*Original: M-237*

Variant of M-237: أبطأ بـ 60%

**Spec (EN):** Key caps appear side by side; each key presses down (moves 2% and turns accent) in order, 0.15s apart.

**Spec (AR):** أزرار الكيبورد تطلع جنب بعض، وكل زر ينضغط (ينزل 2% ويصير بلون الهوية) بالترتيب وبينهم 0.15 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-237.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-237.

#### `al-scr-237-gold` — Keyboard Shortcut · Gold
**اختصار كيبورد · ذهبي**

*accent · any · timeline · easing: easeOut · 0.6s*

*Original: M-237*

Variant of M-237: نسخة ذهبية فاخرة

**Spec (EN):** Key caps appear side by side; each key presses down (moves 2% and turns accent) in order, 0.15s apart.

**Spec (AR):** أزرار الكيبورد تطلع جنب بعض، وكل زر ينضغط (ينزل 2% ويصير بلون الهوية) بالترتيب وبينهم 0.15 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-237.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-237.

#### `al-scr-237-boxed` — Keyboard Shortcut · Boxed
**اختصار كيبورد · صندوق**

*accent · any · timeline · easing: easeOut · 0.6s*

*Original: M-237*

Variant of M-237: النص داخل صندوق ملون

**Spec (EN):** Key caps appear side by side; each key presses down (moves 2% and turns accent) in order, 0.15s apart.

**Spec (AR):** أزرار الكيبورد تطلع جنب بعض، وكل زر ينضغط (ينزل 2% ويصير بلون الهوية) بالترتيب وبينهم 0.15 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-237.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-237.

#### `al-scr-238-fast` — Tab Switch · Fast
**تبديل تبويب · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.35s*

*Original: M-238*

Variant of M-238: أسرع بـ 40%

**Spec (EN):** An accent underline slides from one tab to the next while the content panel slides across in the same direction over 0.35s.

**Spec (AR):** خط بلون الهوية ينزلق من تبويب للثاني، ولوحة المحتوى تنزلق بنفس الاتجاه خلال 0.35 ثانية.

**When to use:**
- EN: Use when you need a fast version of M-238.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-238.

#### `al-scr-238-slow` — Tab Switch · Slow
**تبديل تبويب · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.35s*

*Original: M-238*

Variant of M-238: أبطأ بـ 60%

**Spec (EN):** An accent underline slides from one tab to the next while the content panel slides across in the same direction over 0.35s.

**Spec (AR):** خط بلون الهوية ينزلق من تبويب للثاني، ولوحة المحتوى تنزلق بنفس الاتجاه خلال 0.35 ثانية.

**When to use:**
- EN: Use when you need a slow version of M-238.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-238.

#### `al-scr-238-gold` — Tab Switch · Gold
**تبديل تبويب · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.35s*

*Original: M-238*

Variant of M-238: نسخة ذهبية فاخرة

**Spec (EN):** An accent underline slides from one tab to the next while the content panel slides across in the same direction over 0.35s.

**Spec (AR):** خط بلون الهوية ينزلق من تبويب للثاني، ولوحة المحتوى تنزلق بنفس الاتجاه خلال 0.35 ثانية.

**When to use:**
- EN: Use when you need a gold version of M-238.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-238.

#### `al-scr-238-boxed` — Tab Switch · Boxed
**تبديل تبويب · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.35s*

*Original: M-238*

Variant of M-238: النص داخل صندوق ملون

**Spec (EN):** An accent underline slides from one tab to the next while the content panel slides across in the same direction over 0.35s.

**Spec (AR):** خط بلون الهوية ينزلق من تبويب للثاني، ولوحة المحتوى تنزلق بنفس الاتجاه خلال 0.35 ثانية.

**When to use:**
- EN: Use when you need a boxed version of M-238.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-238.

#### `al-scr-239-fast` — Form Fill · Fast
**تعبئة نموذج · سريع**

*accent · any · timeline · easing: steps · ~0.8s per field*

*Original: M-239*

Variant of M-239: أسرع بـ 40%

**Spec (EN):** Each labelled field types its value in order (see M-082), and a checkmark appears at the end of each field when done.

**Spec (AR):** كل خانة لها عنوان تنكتب قيمتها بالترتيب (شوف M-082)، وتطلع علامة صح بآخر كل خانة لمن تخلص.

**When to use:**
- EN: Use when you need a fast version of M-239.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-239.

#### `al-scr-239-slow` — Form Fill · Slow
**تعبئة نموذج · بطيء**

*accent · any · timeline · easing: steps · ~0.8s per field*

*Original: M-239*

Variant of M-239: أبطأ بـ 60%

**Spec (EN):** Each labelled field types its value in order (see M-082), and a checkmark appears at the end of each field when done.

**Spec (AR):** كل خانة لها عنوان تنكتب قيمتها بالترتيب (شوف M-082)، وتطلع علامة صح بآخر كل خانة لمن تخلص.

**When to use:**
- EN: Use when you need a slow version of M-239.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-239.

#### `al-scr-239-gold` — Form Fill · Gold
**تعبئة نموذج · ذهبي**

*accent · any · timeline · easing: steps · ~0.8s per field*

*Original: M-239*

Variant of M-239: نسخة ذهبية فاخرة

**Spec (EN):** Each labelled field types its value in order (see M-082), and a checkmark appears at the end of each field when done.

**Spec (AR):** كل خانة لها عنوان تنكتب قيمتها بالترتيب (شوف M-082)، وتطلع علامة صح بآخر كل خانة لمن تخلص.

**When to use:**
- EN: Use when you need a gold version of M-239.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-239.

#### `al-scr-239-boxed` — Form Fill · Boxed
**تعبئة نموذج · صندوق**

*accent · any · timeline · easing: steps · ~0.8s per field*

*Original: M-239*

Variant of M-239: النص داخل صندوق ملون

**Spec (EN):** Each labelled field types its value in order (see M-082), and a checkmark appears at the end of each field when done.

**Spec (AR):** كل خانة لها عنوان تنكتب قيمتها بالترتيب (شوف M-082)، وتطلع علامة صح بآخر كل خانة لمن تخلص.

**When to use:**
- EN: Use when you need a boxed version of M-239.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-239.

#### `al-scr-240-fast` — Upload Progress · Fast
**رفع ملف · سريع**

*accent · any · depth · easing: easeInOutCubic · 1.2s*

*Original: M-240*

Variant of M-240: أسرع بـ 40%

**Spec (EN):** A file card with an icon and name shows a progress bar filling from 0 to 100% while the percentage counts up, then a check appears.

**Spec (AR):** بطاقة ملف فيها أيقونة واسم، وشريط تقدم يتعبى من 0 لـ 100% والنسبة تعد، وبعدين تطلع علامة صح.

**When to use:**
- EN: Use when you need a fast version of M-240.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-240.

#### `al-scr-240-slow` — Upload Progress · Slow
**رفع ملف · بطيء**

*accent · any · depth · easing: easeInOutCubic · 1.2s*

*Original: M-240*

Variant of M-240: أبطأ بـ 60%

**Spec (EN):** A file card with an icon and name shows a progress bar filling from 0 to 100% while the percentage counts up, then a check appears.

**Spec (AR):** بطاقة ملف فيها أيقونة واسم، وشريط تقدم يتعبى من 0 لـ 100% والنسبة تعد، وبعدين تطلع علامة صح.

**When to use:**
- EN: Use when you need a slow version of M-240.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-240.

#### `al-scr-240-gold` — Upload Progress · Gold
**رفع ملف · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 1.2s*

*Original: M-240*

Variant of M-240: نسخة ذهبية فاخرة

**Spec (EN):** A file card with an icon and name shows a progress bar filling from 0 to 100% while the percentage counts up, then a check appears.

**Spec (AR):** بطاقة ملف فيها أيقونة واسم، وشريط تقدم يتعبى من 0 لـ 100% والنسبة تعد، وبعدين تطلع علامة صح.

**When to use:**
- EN: Use when you need a gold version of M-240.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-240.

#### `al-scr-240-boxed` — Upload Progress · Boxed
**رفع ملف · صندوق**

*accent · any · depth · easing: easeInOutCubic · 1.2s*

*Original: M-240*

Variant of M-240: النص داخل صندوق ملون

**Spec (EN):** A file card with an icon and name shows a progress bar filling from 0 to 100% while the percentage counts up, then a check appears.

**Spec (AR):** بطاقة ملف فيها أيقونة واسم، وشريط تقدم يتعبى من 0 لـ 100% والنسبة تعد، وبعدين تطلع علامة صح.

**When to use:**
- EN: Use when you need a boxed version of M-240.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-240.

### Tracking (تتبع الحركة) — 40 motions

#### `al-trk-241` — Label Follow
**نص يلحق شي يتحرك**

*workhorse · any · camera · easing: tracked · live*

*Original: M-241*

A label that sticks to a moving object.

**Spec (EN):** Track a point on the object (optical flow or a tracker) and attach a label with a small pointer above it; the label follows the point every frame with slight smoothing.

**Spec (AR):** تتبّع نقطة على الشي (optical flow أو أداة تتبع) وثبّت فوقها تاق مع سهم صغير، والتاق يلحق النقطة كل فريم بنعومة خفيفة.

**When to use:**
- EN: A label that sticks to a moving object.
- AR: كلمة أو اسم يلحق شي يتحرك بالفيديو.

#### `al-trk-242` — Tracking Ring
**دائرة تتبع**

*workhorse · any · sound · easing: tracked · live*

*Original: M-242*

A ring that follows an object to point it out.

**Spec (EN):** Track the object and draw a mint ring slightly larger than it, centered on the tracked point, with a soft pulse.

**Spec (AR):** تتبّع الشي وارسم حوله دائرة نعناعية أكبر منه شوي، مركزها على نقطة التتبع، مع نبض ناعم.

**When to use:**
- EN: A ring that follows an object to point it out.
- AR: دائرة تلحق شي معين عشان تبينه.

#### `al-trk-243` — Face Blur
**تضبيب وجه**

*workhorse · any · timeline · easing: tracked · live*

*Original: M-243*

Hides a face or a plate for privacy.

**Spec (EN):** Detect and track the face (or plate) and cover it with a rounded box that blurs what is behind it about 2.5%, following it every frame.

**Spec (AR):** اكتشف الوجه (أو اللوحة) وتتبّعه، وغطّه بمربع بزوايا دائرية يضبّب اللي وراه تقريباً 2.5%، ويلحقه كل فريم.

**When to use:**
- EN: Hides a face or a plate for privacy.
- AR: تخفي وجه شخص أو لوحة سيارة للخصوصية.

#### `al-trk-244` — Callout Line
**خط يأشر بملاحظة**

*workhorse · any · camera · easing: easeInOutCubic · 0.6s*

*Original: M-244*

A line draws from an object to a note beside it.

**Spec (EN):** A thin line draws from the tracked point to a corner over 0.6s, then a small note box fades in at the end of the line.

**Spec (AR):** خط رفيع ينرسم من النقطة المتتبعة لزاوية خلال 0.6 ثانية، وبعدين صندوق ملاحظة صغير يظهر بآخر الخط.

**When to use:**
- EN: A line draws from an object to a note beside it.
- AR: خط ينرسم من شي لملاحظة جنبه.

#### `al-trk-245` — Screen Replace
**تبديل شاشة جوال**

*workhorse · any · depth · easing: tracked · live*

*Original: M-245*

Puts another image inside a phone screen in the video.

**Spec (EN):** Track the four corners of the screen in the footage and warp your image or recording onto that quad every frame (corner pin), with a slight glare overlay.

**Spec (AR):** تتبّع الزوايا الأربع للشاشة في الفيديو، وركّب صورتك أو تسجيلك على هالشكل كل فريم (corner pin)، مع لمعة خفيفة فوقه.

**When to use:**
- EN: Puts another image inside a phone screen in the video.
- AR: تحط صورة ثانية داخل شاشة جوال بالفيديو.

#### `al-trk-246` — Arrow Follow
**سهم يلحق**

*workhorse · any · timeline · easing: tracked · live*

*Original: M-246*

An arrow that keeps pointing at a moving thing.

**Spec (EN):** Track the object and keep an accent arrow just above it pointing down, bobbing slightly while it follows.

**Spec (AR):** تتبّع الشي وخل سهم بلون الهوية فوقه على طول يأشر لتحت، ويتحرك شوي وهو يلحقه.

**When to use:**
- EN: An arrow that keeps pointing at a moving thing.
- AR: سهم يأشر على شي يتحرك.

#### `al-trk-247` — Emoji Follow
**إيموجي يلحق**

*workhorse · any · depth · easing: tracked · live*

*Original: M-247*

A sticker or emoji that follows a moving object.

**Spec (EN):** Track the object and stick a sticker (or emoji image) on it, scaled to its size and following its position and rotation.

**Spec (AR):** تتبّع الشي والصق عليه ملصق (أو صورة إيموجي)، بحجمه، ويلحق مكانه ودورانه.

**When to use:**
- EN: A sticker or emoji that follows a moving object.
- AR: إيموجي أو ملصق يلحق شي يتحرك.

#### `al-trk-248` — Path Trace
**رسم مسار الحركة**

*workhorse · calm · timeline · easing: linear · live*

*Original: M-248*

Draws the path an object travelled.

**Spec (EN):** Track the object and draw a dashed accent line along its past positions that builds up as it moves.

**Spec (AR):** تتبّع الشي وارسم خط متقطع بلون الهوية على الأماكن اللي مر فيها، والخط يطول وهو يتحرك.

**When to use:**
- EN: Draws the path an object travelled.
- AR: خط يرسم الطريق اللي مشى فيه الشي.

#### `al-trk-241-fast` — Label Follow · Fast
**نص يلحق شي يتحرك · سريع**

*accent · any · camera · easing: tracked · live*

*Original: M-241*

Variant of M-241: أسرع بـ 40%

**Spec (EN):** Track a point on the object (optical flow or a tracker) and attach a label with a small pointer above it; the label follows the point every frame with slight smoothing.

**Spec (AR):** تتبّع نقطة على الشي (optical flow أو أداة تتبع) وثبّت فوقها تاق مع سهم صغير، والتاق يلحق النقطة كل فريم بنعومة خفيفة.

**When to use:**
- EN: Use when you need a fast version of M-241.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-241.

#### `al-trk-241-slow` — Label Follow · Slow
**نص يلحق شي يتحرك · بطيء**

*accent · any · camera · easing: tracked · live*

*Original: M-241*

Variant of M-241: أبطأ بـ 60%

**Spec (EN):** Track a point on the object (optical flow or a tracker) and attach a label with a small pointer above it; the label follows the point every frame with slight smoothing.

**Spec (AR):** تتبّع نقطة على الشي (optical flow أو أداة تتبع) وثبّت فوقها تاق مع سهم صغير، والتاق يلحق النقطة كل فريم بنعومة خفيفة.

**When to use:**
- EN: Use when you need a slow version of M-241.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-241.

#### `al-trk-241-gold` — Label Follow · Gold
**نص يلحق شي يتحرك · ذهبي**

*accent · any · camera · easing: tracked · live*

*Original: M-241*

Variant of M-241: نسخة ذهبية فاخرة

**Spec (EN):** Track a point on the object (optical flow or a tracker) and attach a label with a small pointer above it; the label follows the point every frame with slight smoothing.

**Spec (AR):** تتبّع نقطة على الشي (optical flow أو أداة تتبع) وثبّت فوقها تاق مع سهم صغير، والتاق يلحق النقطة كل فريم بنعومة خفيفة.

**When to use:**
- EN: Use when you need a gold version of M-241.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-241.

#### `al-trk-241-boxed` — Label Follow · Boxed
**نص يلحق شي يتحرك · صندوق**

*accent · any · camera · easing: tracked · live*

*Original: M-241*

Variant of M-241: النص داخل صندوق ملون

**Spec (EN):** Track a point on the object (optical flow or a tracker) and attach a label with a small pointer above it; the label follows the point every frame with slight smoothing.

**Spec (AR):** تتبّع نقطة على الشي (optical flow أو أداة تتبع) وثبّت فوقها تاق مع سهم صغير، والتاق يلحق النقطة كل فريم بنعومة خفيفة.

**When to use:**
- EN: Use when you need a boxed version of M-241.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-241.

#### `al-trk-242-fast` — Tracking Ring · Fast
**دائرة تتبع · سريع**

*accent · any · sound · easing: tracked · live*

*Original: M-242*

Variant of M-242: أسرع بـ 40%

**Spec (EN):** Track the object and draw a mint ring slightly larger than it, centered on the tracked point, with a soft pulse.

**Spec (AR):** تتبّع الشي وارسم حوله دائرة نعناعية أكبر منه شوي، مركزها على نقطة التتبع، مع نبض ناعم.

**When to use:**
- EN: Use when you need a fast version of M-242.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-242.

#### `al-trk-242-slow` — Tracking Ring · Slow
**دائرة تتبع · بطيء**

*accent · any · sound · easing: tracked · live*

*Original: M-242*

Variant of M-242: أبطأ بـ 60%

**Spec (EN):** Track the object and draw a mint ring slightly larger than it, centered on the tracked point, with a soft pulse.

**Spec (AR):** تتبّع الشي وارسم حوله دائرة نعناعية أكبر منه شوي، مركزها على نقطة التتبع، مع نبض ناعم.

**When to use:**
- EN: Use when you need a slow version of M-242.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-242.

#### `al-trk-242-gold` — Tracking Ring · Gold
**دائرة تتبع · ذهبي**

*accent · any · sound · easing: tracked · live*

*Original: M-242*

Variant of M-242: نسخة ذهبية فاخرة

**Spec (EN):** Track the object and draw a mint ring slightly larger than it, centered on the tracked point, with a soft pulse.

**Spec (AR):** تتبّع الشي وارسم حوله دائرة نعناعية أكبر منه شوي، مركزها على نقطة التتبع، مع نبض ناعم.

**When to use:**
- EN: Use when you need a gold version of M-242.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-242.

#### `al-trk-242-boxed` — Tracking Ring · Boxed
**دائرة تتبع · صندوق**

*accent · any · sound · easing: tracked · live*

*Original: M-242*

Variant of M-242: النص داخل صندوق ملون

**Spec (EN):** Track the object and draw a mint ring slightly larger than it, centered on the tracked point, with a soft pulse.

**Spec (AR):** تتبّع الشي وارسم حوله دائرة نعناعية أكبر منه شوي، مركزها على نقطة التتبع، مع نبض ناعم.

**When to use:**
- EN: Use when you need a boxed version of M-242.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-242.

#### `al-trk-243-fast` — Face Blur · Fast
**تضبيب وجه · سريع**

*accent · any · timeline · easing: tracked · live*

*Original: M-243*

Variant of M-243: أسرع بـ 40%

**Spec (EN):** Detect and track the face (or plate) and cover it with a rounded box that blurs what is behind it about 2.5%, following it every frame.

**Spec (AR):** اكتشف الوجه (أو اللوحة) وتتبّعه، وغطّه بمربع بزوايا دائرية يضبّب اللي وراه تقريباً 2.5%، ويلحقه كل فريم.

**When to use:**
- EN: Use when you need a fast version of M-243.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-243.

#### `al-trk-243-slow` — Face Blur · Slow
**تضبيب وجه · بطيء**

*accent · any · timeline · easing: tracked · live*

*Original: M-243*

Variant of M-243: أبطأ بـ 60%

**Spec (EN):** Detect and track the face (or plate) and cover it with a rounded box that blurs what is behind it about 2.5%, following it every frame.

**Spec (AR):** اكتشف الوجه (أو اللوحة) وتتبّعه، وغطّه بمربع بزوايا دائرية يضبّب اللي وراه تقريباً 2.5%، ويلحقه كل فريم.

**When to use:**
- EN: Use when you need a slow version of M-243.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-243.

#### `al-trk-243-gold` — Face Blur · Gold
**تضبيب وجه · ذهبي**

*accent · any · timeline · easing: tracked · live*

*Original: M-243*

Variant of M-243: نسخة ذهبية فاخرة

**Spec (EN):** Detect and track the face (or plate) and cover it with a rounded box that blurs what is behind it about 2.5%, following it every frame.

**Spec (AR):** اكتشف الوجه (أو اللوحة) وتتبّعه، وغطّه بمربع بزوايا دائرية يضبّب اللي وراه تقريباً 2.5%، ويلحقه كل فريم.

**When to use:**
- EN: Use when you need a gold version of M-243.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-243.

#### `al-trk-243-boxed` — Face Blur · Boxed
**تضبيب وجه · صندوق**

*accent · any · timeline · easing: tracked · live*

*Original: M-243*

Variant of M-243: النص داخل صندوق ملون

**Spec (EN):** Detect and track the face (or plate) and cover it with a rounded box that blurs what is behind it about 2.5%, following it every frame.

**Spec (AR):** اكتشف الوجه (أو اللوحة) وتتبّعه، وغطّه بمربع بزوايا دائرية يضبّب اللي وراه تقريباً 2.5%، ويلحقه كل فريم.

**When to use:**
- EN: Use when you need a boxed version of M-243.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-243.

#### `al-trk-244-fast` — Callout Line · Fast
**خط يأشر بملاحظة · سريع**

*accent · any · camera · easing: easeInOutCubic · 0.6s*

*Original: M-244*

Variant of M-244: أسرع بـ 40%

**Spec (EN):** A thin line draws from the tracked point to a corner over 0.6s, then a small note box fades in at the end of the line.

**Spec (AR):** خط رفيع ينرسم من النقطة المتتبعة لزاوية خلال 0.6 ثانية، وبعدين صندوق ملاحظة صغير يظهر بآخر الخط.

**When to use:**
- EN: Use when you need a fast version of M-244.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-244.

#### `al-trk-244-slow` — Callout Line · Slow
**خط يأشر بملاحظة · بطيء**

*accent · any · camera · easing: easeInOutCubic · 0.6s*

*Original: M-244*

Variant of M-244: أبطأ بـ 60%

**Spec (EN):** A thin line draws from the tracked point to a corner over 0.6s, then a small note box fades in at the end of the line.

**Spec (AR):** خط رفيع ينرسم من النقطة المتتبعة لزاوية خلال 0.6 ثانية، وبعدين صندوق ملاحظة صغير يظهر بآخر الخط.

**When to use:**
- EN: Use when you need a slow version of M-244.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-244.

#### `al-trk-244-gold` — Callout Line · Gold
**خط يأشر بملاحظة · ذهبي**

*accent · any · camera · easing: easeInOutCubic · 0.6s*

*Original: M-244*

Variant of M-244: نسخة ذهبية فاخرة

**Spec (EN):** A thin line draws from the tracked point to a corner over 0.6s, then a small note box fades in at the end of the line.

**Spec (AR):** خط رفيع ينرسم من النقطة المتتبعة لزاوية خلال 0.6 ثانية، وبعدين صندوق ملاحظة صغير يظهر بآخر الخط.

**When to use:**
- EN: Use when you need a gold version of M-244.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-244.

#### `al-trk-244-boxed` — Callout Line · Boxed
**خط يأشر بملاحظة · صندوق**

*accent · any · camera · easing: easeInOutCubic · 0.6s*

*Original: M-244*

Variant of M-244: النص داخل صندوق ملون

**Spec (EN):** A thin line draws from the tracked point to a corner over 0.6s, then a small note box fades in at the end of the line.

**Spec (AR):** خط رفيع ينرسم من النقطة المتتبعة لزاوية خلال 0.6 ثانية، وبعدين صندوق ملاحظة صغير يظهر بآخر الخط.

**When to use:**
- EN: Use when you need a boxed version of M-244.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-244.

#### `al-trk-245-fast` — Screen Replace · Fast
**تبديل شاشة جوال · سريع**

*accent · any · depth · easing: tracked · live*

*Original: M-245*

Variant of M-245: أسرع بـ 40%

**Spec (EN):** Track the four corners of the screen in the footage and warp your image or recording onto that quad every frame (corner pin), with a slight glare overlay.

**Spec (AR):** تتبّع الزوايا الأربع للشاشة في الفيديو، وركّب صورتك أو تسجيلك على هالشكل كل فريم (corner pin)، مع لمعة خفيفة فوقه.

**When to use:**
- EN: Use when you need a fast version of M-245.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-245.

#### `al-trk-245-slow` — Screen Replace · Slow
**تبديل شاشة جوال · بطيء**

*accent · any · depth · easing: tracked · live*

*Original: M-245*

Variant of M-245: أبطأ بـ 60%

**Spec (EN):** Track the four corners of the screen in the footage and warp your image or recording onto that quad every frame (corner pin), with a slight glare overlay.

**Spec (AR):** تتبّع الزوايا الأربع للشاشة في الفيديو، وركّب صورتك أو تسجيلك على هالشكل كل فريم (corner pin)، مع لمعة خفيفة فوقه.

**When to use:**
- EN: Use when you need a slow version of M-245.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-245.

#### `al-trk-245-gold` — Screen Replace · Gold
**تبديل شاشة جوال · ذهبي**

*accent · any · depth · easing: tracked · live*

*Original: M-245*

Variant of M-245: نسخة ذهبية فاخرة

**Spec (EN):** Track the four corners of the screen in the footage and warp your image or recording onto that quad every frame (corner pin), with a slight glare overlay.

**Spec (AR):** تتبّع الزوايا الأربع للشاشة في الفيديو، وركّب صورتك أو تسجيلك على هالشكل كل فريم (corner pin)، مع لمعة خفيفة فوقه.

**When to use:**
- EN: Use when you need a gold version of M-245.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-245.

#### `al-trk-245-boxed` — Screen Replace · Boxed
**تبديل شاشة جوال · صندوق**

*accent · any · depth · easing: tracked · live*

*Original: M-245*

Variant of M-245: النص داخل صندوق ملون

**Spec (EN):** Track the four corners of the screen in the footage and warp your image or recording onto that quad every frame (corner pin), with a slight glare overlay.

**Spec (AR):** تتبّع الزوايا الأربع للشاشة في الفيديو، وركّب صورتك أو تسجيلك على هالشكل كل فريم (corner pin)، مع لمعة خفيفة فوقه.

**When to use:**
- EN: Use when you need a boxed version of M-245.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-245.

#### `al-trk-246-fast` — Arrow Follow · Fast
**سهم يلحق · سريع**

*accent · any · timeline · easing: tracked · live*

*Original: M-246*

Variant of M-246: أسرع بـ 40%

**Spec (EN):** Track the object and keep an accent arrow just above it pointing down, bobbing slightly while it follows.

**Spec (AR):** تتبّع الشي وخل سهم بلون الهوية فوقه على طول يأشر لتحت، ويتحرك شوي وهو يلحقه.

**When to use:**
- EN: Use when you need a fast version of M-246.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-246.

#### `al-trk-246-slow` — Arrow Follow · Slow
**سهم يلحق · بطيء**

*accent · any · timeline · easing: tracked · live*

*Original: M-246*

Variant of M-246: أبطأ بـ 60%

**Spec (EN):** Track the object and keep an accent arrow just above it pointing down, bobbing slightly while it follows.

**Spec (AR):** تتبّع الشي وخل سهم بلون الهوية فوقه على طول يأشر لتحت، ويتحرك شوي وهو يلحقه.

**When to use:**
- EN: Use when you need a slow version of M-246.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-246.

#### `al-trk-246-gold` — Arrow Follow · Gold
**سهم يلحق · ذهبي**

*accent · any · timeline · easing: tracked · live*

*Original: M-246*

Variant of M-246: نسخة ذهبية فاخرة

**Spec (EN):** Track the object and keep an accent arrow just above it pointing down, bobbing slightly while it follows.

**Spec (AR):** تتبّع الشي وخل سهم بلون الهوية فوقه على طول يأشر لتحت، ويتحرك شوي وهو يلحقه.

**When to use:**
- EN: Use when you need a gold version of M-246.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-246.

#### `al-trk-246-boxed` — Arrow Follow · Boxed
**سهم يلحق · صندوق**

*accent · any · timeline · easing: tracked · live*

*Original: M-246*

Variant of M-246: النص داخل صندوق ملون

**Spec (EN):** Track the object and keep an accent arrow just above it pointing down, bobbing slightly while it follows.

**Spec (AR):** تتبّع الشي وخل سهم بلون الهوية فوقه على طول يأشر لتحت، ويتحرك شوي وهو يلحقه.

**When to use:**
- EN: Use when you need a boxed version of M-246.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-246.

#### `al-trk-247-fast` — Emoji Follow · Fast
**إيموجي يلحق · سريع**

*accent · any · depth · easing: tracked · live*

*Original: M-247*

Variant of M-247: أسرع بـ 40%

**Spec (EN):** Track the object and stick a sticker (or emoji image) on it, scaled to its size and following its position and rotation.

**Spec (AR):** تتبّع الشي والصق عليه ملصق (أو صورة إيموجي)، بحجمه، ويلحق مكانه ودورانه.

**When to use:**
- EN: Use when you need a fast version of M-247.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-247.

#### `al-trk-247-slow` — Emoji Follow · Slow
**إيموجي يلحق · بطيء**

*accent · any · depth · easing: tracked · live*

*Original: M-247*

Variant of M-247: أبطأ بـ 60%

**Spec (EN):** Track the object and stick a sticker (or emoji image) on it, scaled to its size and following its position and rotation.

**Spec (AR):** تتبّع الشي والصق عليه ملصق (أو صورة إيموجي)، بحجمه، ويلحق مكانه ودورانه.

**When to use:**
- EN: Use when you need a slow version of M-247.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-247.

#### `al-trk-247-gold` — Emoji Follow · Gold
**إيموجي يلحق · ذهبي**

*accent · any · depth · easing: tracked · live*

*Original: M-247*

Variant of M-247: نسخة ذهبية فاخرة

**Spec (EN):** Track the object and stick a sticker (or emoji image) on it, scaled to its size and following its position and rotation.

**Spec (AR):** تتبّع الشي والصق عليه ملصق (أو صورة إيموجي)، بحجمه، ويلحق مكانه ودورانه.

**When to use:**
- EN: Use when you need a gold version of M-247.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-247.

#### `al-trk-247-boxed` — Emoji Follow · Boxed
**إيموجي يلحق · صندوق**

*accent · any · depth · easing: tracked · live*

*Original: M-247*

Variant of M-247: النص داخل صندوق ملون

**Spec (EN):** Track the object and stick a sticker (or emoji image) on it, scaled to its size and following its position and rotation.

**Spec (AR):** تتبّع الشي والصق عليه ملصق (أو صورة إيموجي)، بحجمه، ويلحق مكانه ودورانه.

**When to use:**
- EN: Use when you need a boxed version of M-247.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-247.

#### `al-trk-248-fast` — Path Trace · Fast
**رسم مسار الحركة · سريع**

*accent · calm · timeline · easing: linear · live*

*Original: M-248*

Variant of M-248: أسرع بـ 40%

**Spec (EN):** Track the object and draw a dashed accent line along its past positions that builds up as it moves.

**Spec (AR):** تتبّع الشي وارسم خط متقطع بلون الهوية على الأماكن اللي مر فيها، والخط يطول وهو يتحرك.

**When to use:**
- EN: Use when you need a fast version of M-248.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-248.

#### `al-trk-248-slow` — Path Trace · Slow
**رسم مسار الحركة · بطيء**

*accent · calm · timeline · easing: linear · live*

*Original: M-248*

Variant of M-248: أبطأ بـ 60%

**Spec (EN):** Track the object and draw a dashed accent line along its past positions that builds up as it moves.

**Spec (AR):** تتبّع الشي وارسم خط متقطع بلون الهوية على الأماكن اللي مر فيها، والخط يطول وهو يتحرك.

**When to use:**
- EN: Use when you need a slow version of M-248.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-248.

#### `al-trk-248-gold` — Path Trace · Gold
**رسم مسار الحركة · ذهبي**

*accent · calm · timeline · easing: linear · live*

*Original: M-248*

Variant of M-248: نسخة ذهبية فاخرة

**Spec (EN):** Track the object and draw a dashed accent line along its past positions that builds up as it moves.

**Spec (AR):** تتبّع الشي وارسم خط متقطع بلون الهوية على الأماكن اللي مر فيها، والخط يطول وهو يتحرك.

**When to use:**
- EN: Use when you need a gold version of M-248.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-248.

#### `al-trk-248-boxed` — Path Trace · Boxed
**رسم مسار الحركة · صندوق**

*accent · calm · timeline · easing: linear · live*

*Original: M-248*

Variant of M-248: النص داخل صندوق ملون

**Spec (EN):** Track the object and draw a dashed accent line along its past positions that builds up as it moves.

**Spec (AR):** تتبّع الشي وارسم خط متقطع بلون الهوية على الأماكن اللي مر فيها، والخط يطول وهو يتحرك.

**When to use:**
- EN: Use when you need a boxed version of M-248.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-248.

### 3D (Alansari) (الثلاثي الأبعاد) — 50 motions

#### `al-d3-249` — 3D Spin Text
**نص يلف 3D**

*workhorse · calm · depth · easing: linear · loop · 3s*

*Original: M-249*

A word spinning around its vertical axis in 3D.

**Spec (EN):** Rotate the text around the Y axis with perspective, one full turn every 3s; keep the back face visible or mirrored.

**Spec (AR):** لف النص على المحور العمودي مع عمق 3D، لفة كاملة كل 3 ثواني، وخل الوجه الخلفي ظاهر أو معكوس.

**When to use:**
- EN: A word spinning around its vertical axis in 3D.
- AR: كلمة تلف حول نفسها ثلاثي الأبعاد.

#### `al-d3-250` — Extruded Text
**نص بارز**

*workhorse · calm · timeline · easing: easeInOutSine · loop · 4s*

*Original: M-250*

Thick extruded text like a solid object.

**Spec (EN):** Give the text a stacked, darker accent depth (6–10 offset layers) and gently tilt it in 3D (±14°) on a 4s loop.

**Spec (AR):** خل للنص عمق متراكب بلون الهوية أغمق (6 إلى 10 طبقات منزاحة)، وميّله بخفة 3D (±14 درجة) كل 4 ثواني.

**When to use:**
- EN: Thick extruded text like a solid object.
- AR: نص سميك بارز مثل المجسم.

#### `al-d3-251` — Parallax 2.5D
**صورة بعمق**

*workhorse · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-251*

A still photo moves in layers as if it has depth.

**Spec (EN):** Separate the subject from the background (matte or depth map); move the background slowly one way and the subject the other way, with a 115% scale to hide edges.

**Spec (AR):** افصل الشخص عن الخلفية (قناع أو خريطة عمق)، وحرّك الخلفية ببطء لجهة والشخص للجهة الثانية، مع تكبير 115% عشان الأطراف ما تبين.

**When to use:**
- EN: A still photo moves in layers as if it has depth.
- AR: صورة ثابتة تتحرك بطبقات كأن فيها عمق.

#### `al-d3-252` — Card Flip
**بطاقة تنقلب**

*workhorse · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-252*

A card flips to reveal the answer.

**Spec (EN):** A card rotates 180° around the Y axis with perspective over 0.6s, showing its back side with the reveal text.

**Spec (AR):** بطاقة تلف 180 درجة على المحور العمودي مع عمق خلال 0.6 ثانية، وتبين ظهرها وفيه الجواب.

**When to use:**
- EN: A card flips to reveal the answer.
- AR: بطاقة تنقلب وتكشف الجواب أو المعلومة.

#### `al-d3-253` — Cube Spin
**مكعب يلف**

*workhorse · calm · depth · easing: linear · loop · 4s*

*Original: M-253*

A spinning 3D cube for a logo or product.

**Spec (EN):** Build a cube from six faces with preserve-3d, tilt it -20° on X and rotate it a full turn on Y every 4s; put the logo on the faces.

**Spec (AR):** ابنِ مكعب من ستة أوجه بـ preserve-3d، ميّله -20 درجة على X ولفّه لفة كاملة على Y كل 4 ثواني، وحط الشعار على الأوجه.

**When to use:**
- EN: A spinning 3D cube for a logo or product.
- AR: مكعب ثلاثي الأبعاد يلف، لشعار أو منتج.

#### `al-d3-254` — Tilt Card
**بطاقة تميل**

*workhorse · calm · timeline · easing: easeInOutSine · loop · 4s*

*Original: M-254*

A card tilting as if held in your hand.

**Spec (EN):** Tilt a card on X and Y (±12–16°) with perspective on a smooth 4s loop, with a soft shadow beneath it.

**Spec (AR):** ميّل البطاقة على X و Y (±12 إلى 16 درجة) مع عمق كل 4 ثواني بنعومة، وتحتها ظل ناعم.

**When to use:**
- EN: A card tilting as if held in your hand.
- AR: بطاقة تميل وكأنك ماسكها بيدك.

#### `al-d3-255` — Layer Explode
**طبقات تنفصل**

*workhorse · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-255*

Design layers separate apart in 3D.

**Spec (EN):** Tilt a stack of layers into an isometric view and push each layer apart on Z (0, 8%, 16%…), then bring them back together.

**Spec (AR):** ميّل كومة الطبقات لزاوية جانبية، وبعّد كل طبقة عن الثانية على Z (0، 8%، 16%…)، وبعدين رجّعهم مع بعض.

**When to use:**
- EN: Design layers separate apart in 3D.
- AR: طبقات التصميم تنفصل عن بعض بشكل 3D.

#### `al-d3-256` — 3D Carousel
**عجلة بطاقات**

*workhorse · calm · depth · easing: linear · loop · 6s*

*Original: M-256*

Cards rotating on a 3D ring to show several items.

**Spec (EN):** Place 5–8 cards evenly around a 3D ring (rotateY steps + translateZ) and rotate the ring slowly.

**Spec (AR):** حط من 5 إلى 8 بطاقات متساوية حول حلقة 3D (rotateY ثم translateZ)، ولف الحلقة ببطء.

**When to use:**
- EN: Cards rotating on a 3D ring to show several items.
- AR: بطاقات تدور بشكل دائري، لعرض عدة أشياء.

#### `al-d3-257` — Float Shadow
**عنصر يطفو مع ظل**

*workhorse · calm · depth · easing: easeInOutSine · loop · 3s*

*Original: M-257*

A product or logo floats with a shadow that changes below it.

**Spec (EN):** Bob the object up 6% with a slight rotation while its drop shadow grows softer and lighter at the top of the motion.

**Spec (AR):** خل العنصر يطلع لفوق 6% مع دوران خفيف، وظله تحته يصير أنعم وأخف لمن يكون فوق.

**When to use:**
- EN: A product or logo floats with a shadow that changes below it.
- AR: منتج أو شعار يطفو وظله يتغير تحته.

#### `al-d3-258` — Coin Flip
**عملة تنقلب**

*workhorse · any · depth · easing: easeInOutQuad · 1.2s*

*Original: M-258*

A coin tosses and flips, like heads or tails.

**Spec (EN):** A two-sided coin rises and falls while spinning several times around the Y axis over about 1.2s, landing on one face.

**Spec (AR):** عملة بوجهين تطلع وتنزل وهي تلف كم لفة على المحور العمودي خلال تقريباً 1.2 ثانية، وتوقف على وجه.

**When to use:**
- EN: A coin tosses and flips, like heads or tails.
- AR: عملة تطير وتنقلب، مثل "صح ولا خطأ".

#### `al-d3-249-fast` — 3D Spin Text · Fast
**نص يلف 3D · سريع**

*accent · calm · depth · easing: linear · loop · 3s*

*Original: M-249*

Variant of M-249: أسرع بـ 40%

**Spec (EN):** Rotate the text around the Y axis with perspective, one full turn every 3s; keep the back face visible or mirrored.

**Spec (AR):** لف النص على المحور العمودي مع عمق 3D، لفة كاملة كل 3 ثواني، وخل الوجه الخلفي ظاهر أو معكوس.

**When to use:**
- EN: Use when you need a fast version of M-249.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-249.

#### `al-d3-249-slow` — 3D Spin Text · Slow
**نص يلف 3D · بطيء**

*accent · calm · depth · easing: linear · loop · 3s*

*Original: M-249*

Variant of M-249: أبطأ بـ 60%

**Spec (EN):** Rotate the text around the Y axis with perspective, one full turn every 3s; keep the back face visible or mirrored.

**Spec (AR):** لف النص على المحور العمودي مع عمق 3D، لفة كاملة كل 3 ثواني، وخل الوجه الخلفي ظاهر أو معكوس.

**When to use:**
- EN: Use when you need a slow version of M-249.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-249.

#### `al-d3-249-gold` — 3D Spin Text · Gold
**نص يلف 3D · ذهبي**

*accent · calm · depth · easing: linear · loop · 3s*

*Original: M-249*

Variant of M-249: نسخة ذهبية فاخرة

**Spec (EN):** Rotate the text around the Y axis with perspective, one full turn every 3s; keep the back face visible or mirrored.

**Spec (AR):** لف النص على المحور العمودي مع عمق 3D، لفة كاملة كل 3 ثواني، وخل الوجه الخلفي ظاهر أو معكوس.

**When to use:**
- EN: Use when you need a gold version of M-249.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-249.

#### `al-d3-249-boxed` — 3D Spin Text · Boxed
**نص يلف 3D · صندوق**

*accent · calm · depth · easing: linear · loop · 3s*

*Original: M-249*

Variant of M-249: النص داخل صندوق ملون

**Spec (EN):** Rotate the text around the Y axis with perspective, one full turn every 3s; keep the back face visible or mirrored.

**Spec (AR):** لف النص على المحور العمودي مع عمق 3D، لفة كاملة كل 3 ثواني، وخل الوجه الخلفي ظاهر أو معكوس.

**When to use:**
- EN: Use when you need a boxed version of M-249.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-249.

#### `al-d3-250-fast` — Extruded Text · Fast
**نص بارز · سريع**

*accent · calm · timeline · easing: easeInOutSine · loop · 4s*

*Original: M-250*

Variant of M-250: أسرع بـ 40%

**Spec (EN):** Give the text a stacked, darker accent depth (6–10 offset layers) and gently tilt it in 3D (±14°) on a 4s loop.

**Spec (AR):** خل للنص عمق متراكب بلون الهوية أغمق (6 إلى 10 طبقات منزاحة)، وميّله بخفة 3D (±14 درجة) كل 4 ثواني.

**When to use:**
- EN: Use when you need a fast version of M-250.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-250.

#### `al-d3-250-slow` — Extruded Text · Slow
**نص بارز · بطيء**

*accent · calm · timeline · easing: easeInOutSine · loop · 4s*

*Original: M-250*

Variant of M-250: أبطأ بـ 60%

**Spec (EN):** Give the text a stacked, darker accent depth (6–10 offset layers) and gently tilt it in 3D (±14°) on a 4s loop.

**Spec (AR):** خل للنص عمق متراكب بلون الهوية أغمق (6 إلى 10 طبقات منزاحة)، وميّله بخفة 3D (±14 درجة) كل 4 ثواني.

**When to use:**
- EN: Use when you need a slow version of M-250.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-250.

#### `al-d3-250-gold` — Extruded Text · Gold
**نص بارز · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · loop · 4s*

*Original: M-250*

Variant of M-250: نسخة ذهبية فاخرة

**Spec (EN):** Give the text a stacked, darker accent depth (6–10 offset layers) and gently tilt it in 3D (±14°) on a 4s loop.

**Spec (AR):** خل للنص عمق متراكب بلون الهوية أغمق (6 إلى 10 طبقات منزاحة)، وميّله بخفة 3D (±14 درجة) كل 4 ثواني.

**When to use:**
- EN: Use when you need a gold version of M-250.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-250.

#### `al-d3-250-boxed` — Extruded Text · Boxed
**نص بارز · صندوق**

*accent · calm · timeline · easing: easeInOutSine · loop · 4s*

*Original: M-250*

Variant of M-250: النص داخل صندوق ملون

**Spec (EN):** Give the text a stacked, darker accent depth (6–10 offset layers) and gently tilt it in 3D (±14°) on a 4s loop.

**Spec (AR):** خل للنص عمق متراكب بلون الهوية أغمق (6 إلى 10 طبقات منزاحة)، وميّله بخفة 3D (±14 درجة) كل 4 ثواني.

**When to use:**
- EN: Use when you need a boxed version of M-250.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-250.

#### `al-d3-251-fast` — Parallax 2.5D · Fast
**صورة بعمق · سريع**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-251*

Variant of M-251: أسرع بـ 40%

**Spec (EN):** Separate the subject from the background (matte or depth map); move the background slowly one way and the subject the other way, with a 115% scale to hide edges.

**Spec (AR):** افصل الشخص عن الخلفية (قناع أو خريطة عمق)، وحرّك الخلفية ببطء لجهة والشخص للجهة الثانية، مع تكبير 115% عشان الأطراف ما تبين.

**When to use:**
- EN: Use when you need a fast version of M-251.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-251.

#### `al-d3-251-slow` — Parallax 2.5D · Slow
**صورة بعمق · بطيء**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-251*

Variant of M-251: أبطأ بـ 60%

**Spec (EN):** Separate the subject from the background (matte or depth map); move the background slowly one way and the subject the other way, with a 115% scale to hide edges.

**Spec (AR):** افصل الشخص عن الخلفية (قناع أو خريطة عمق)، وحرّك الخلفية ببطء لجهة والشخص للجهة الثانية، مع تكبير 115% عشان الأطراف ما تبين.

**When to use:**
- EN: Use when you need a slow version of M-251.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-251.

#### `al-d3-251-gold` — Parallax 2.5D · Gold
**صورة بعمق · ذهبي**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-251*

Variant of M-251: نسخة ذهبية فاخرة

**Spec (EN):** Separate the subject from the background (matte or depth map); move the background slowly one way and the subject the other way, with a 115% scale to hide edges.

**Spec (AR):** افصل الشخص عن الخلفية (قناع أو خريطة عمق)، وحرّك الخلفية ببطء لجهة والشخص للجهة الثانية، مع تكبير 115% عشان الأطراف ما تبين.

**When to use:**
- EN: Use when you need a gold version of M-251.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-251.

#### `al-d3-251-boxed` — Parallax 2.5D · Boxed
**صورة بعمق · صندوق**

*accent · calm · depth · easing: easeInOutSine · loop · 4s*

*Original: M-251*

Variant of M-251: النص داخل صندوق ملون

**Spec (EN):** Separate the subject from the background (matte or depth map); move the background slowly one way and the subject the other way, with a 115% scale to hide edges.

**Spec (AR):** افصل الشخص عن الخلفية (قناع أو خريطة عمق)، وحرّك الخلفية ببطء لجهة والشخص للجهة الثانية، مع تكبير 115% عشان الأطراف ما تبين.

**When to use:**
- EN: Use when you need a boxed version of M-251.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-251.

#### `al-d3-252-fast` — Card Flip · Fast
**بطاقة تنقلب · سريع**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-252*

Variant of M-252: أسرع بـ 40%

**Spec (EN):** A card rotates 180° around the Y axis with perspective over 0.6s, showing its back side with the reveal text.

**Spec (AR):** بطاقة تلف 180 درجة على المحور العمودي مع عمق خلال 0.6 ثانية، وتبين ظهرها وفيه الجواب.

**When to use:**
- EN: Use when you need a fast version of M-252.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-252.

#### `al-d3-252-slow` — Card Flip · Slow
**بطاقة تنقلب · بطيء**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-252*

Variant of M-252: أبطأ بـ 60%

**Spec (EN):** A card rotates 180° around the Y axis with perspective over 0.6s, showing its back side with the reveal text.

**Spec (AR):** بطاقة تلف 180 درجة على المحور العمودي مع عمق خلال 0.6 ثانية، وتبين ظهرها وفيه الجواب.

**When to use:**
- EN: Use when you need a slow version of M-252.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-252.

#### `al-d3-252-gold` — Card Flip · Gold
**بطاقة تنقلب · ذهبي**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-252*

Variant of M-252: نسخة ذهبية فاخرة

**Spec (EN):** A card rotates 180° around the Y axis with perspective over 0.6s, showing its back side with the reveal text.

**Spec (AR):** بطاقة تلف 180 درجة على المحور العمودي مع عمق خلال 0.6 ثانية، وتبين ظهرها وفيه الجواب.

**When to use:**
- EN: Use when you need a gold version of M-252.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-252.

#### `al-d3-252-boxed` — Card Flip · Boxed
**بطاقة تنقلب · صندوق**

*accent · any · depth · easing: easeInOutCubic · 0.6s*

*Original: M-252*

Variant of M-252: النص داخل صندوق ملون

**Spec (EN):** A card rotates 180° around the Y axis with perspective over 0.6s, showing its back side with the reveal text.

**Spec (AR):** بطاقة تلف 180 درجة على المحور العمودي مع عمق خلال 0.6 ثانية، وتبين ظهرها وفيه الجواب.

**When to use:**
- EN: Use when you need a boxed version of M-252.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-252.

#### `al-d3-253-fast` — Cube Spin · Fast
**مكعب يلف · سريع**

*accent · calm · depth · easing: linear · loop · 4s*

*Original: M-253*

Variant of M-253: أسرع بـ 40%

**Spec (EN):** Build a cube from six faces with preserve-3d, tilt it -20° on X and rotate it a full turn on Y every 4s; put the logo on the faces.

**Spec (AR):** ابنِ مكعب من ستة أوجه بـ preserve-3d، ميّله -20 درجة على X ولفّه لفة كاملة على Y كل 4 ثواني، وحط الشعار على الأوجه.

**When to use:**
- EN: Use when you need a fast version of M-253.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-253.

#### `al-d3-253-slow` — Cube Spin · Slow
**مكعب يلف · بطيء**

*accent · calm · depth · easing: linear · loop · 4s*

*Original: M-253*

Variant of M-253: أبطأ بـ 60%

**Spec (EN):** Build a cube from six faces with preserve-3d, tilt it -20° on X and rotate it a full turn on Y every 4s; put the logo on the faces.

**Spec (AR):** ابنِ مكعب من ستة أوجه بـ preserve-3d، ميّله -20 درجة على X ولفّه لفة كاملة على Y كل 4 ثواني، وحط الشعار على الأوجه.

**When to use:**
- EN: Use when you need a slow version of M-253.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-253.

#### `al-d3-253-gold` — Cube Spin · Gold
**مكعب يلف · ذهبي**

*accent · calm · depth · easing: linear · loop · 4s*

*Original: M-253*

Variant of M-253: نسخة ذهبية فاخرة

**Spec (EN):** Build a cube from six faces with preserve-3d, tilt it -20° on X and rotate it a full turn on Y every 4s; put the logo on the faces.

**Spec (AR):** ابنِ مكعب من ستة أوجه بـ preserve-3d، ميّله -20 درجة على X ولفّه لفة كاملة على Y كل 4 ثواني، وحط الشعار على الأوجه.

**When to use:**
- EN: Use when you need a gold version of M-253.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-253.

#### `al-d3-253-boxed` — Cube Spin · Boxed
**مكعب يلف · صندوق**

*accent · calm · depth · easing: linear · loop · 4s*

*Original: M-253*

Variant of M-253: النص داخل صندوق ملون

**Spec (EN):** Build a cube from six faces with preserve-3d, tilt it -20° on X and rotate it a full turn on Y every 4s; put the logo on the faces.

**Spec (AR):** ابنِ مكعب من ستة أوجه بـ preserve-3d، ميّله -20 درجة على X ولفّه لفة كاملة على Y كل 4 ثواني، وحط الشعار على الأوجه.

**When to use:**
- EN: Use when you need a boxed version of M-253.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-253.

#### `al-d3-254-fast` — Tilt Card · Fast
**بطاقة تميل · سريع**

*accent · calm · timeline · easing: easeInOutSine · loop · 4s*

*Original: M-254*

Variant of M-254: أسرع بـ 40%

**Spec (EN):** Tilt a card on X and Y (±12–16°) with perspective on a smooth 4s loop, with a soft shadow beneath it.

**Spec (AR):** ميّل البطاقة على X و Y (±12 إلى 16 درجة) مع عمق كل 4 ثواني بنعومة، وتحتها ظل ناعم.

**When to use:**
- EN: Use when you need a fast version of M-254.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-254.

#### `al-d3-254-slow` — Tilt Card · Slow
**بطاقة تميل · بطيء**

*accent · calm · timeline · easing: easeInOutSine · loop · 4s*

*Original: M-254*

Variant of M-254: أبطأ بـ 60%

**Spec (EN):** Tilt a card on X and Y (±12–16°) with perspective on a smooth 4s loop, with a soft shadow beneath it.

**Spec (AR):** ميّل البطاقة على X و Y (±12 إلى 16 درجة) مع عمق كل 4 ثواني بنعومة، وتحتها ظل ناعم.

**When to use:**
- EN: Use when you need a slow version of M-254.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-254.

#### `al-d3-254-gold` — Tilt Card · Gold
**بطاقة تميل · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · loop · 4s*

*Original: M-254*

Variant of M-254: نسخة ذهبية فاخرة

**Spec (EN):** Tilt a card on X and Y (±12–16°) with perspective on a smooth 4s loop, with a soft shadow beneath it.

**Spec (AR):** ميّل البطاقة على X و Y (±12 إلى 16 درجة) مع عمق كل 4 ثواني بنعومة، وتحتها ظل ناعم.

**When to use:**
- EN: Use when you need a gold version of M-254.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-254.

#### `al-d3-254-boxed` — Tilt Card · Boxed
**بطاقة تميل · صندوق**

*accent · calm · timeline · easing: easeInOutSine · loop · 4s*

*Original: M-254*

Variant of M-254: النص داخل صندوق ملون

**Spec (EN):** Tilt a card on X and Y (±12–16°) with perspective on a smooth 4s loop, with a soft shadow beneath it.

**Spec (AR):** ميّل البطاقة على X و Y (±12 إلى 16 درجة) مع عمق كل 4 ثواني بنعومة، وتحتها ظل ناعم.

**When to use:**
- EN: Use when you need a boxed version of M-254.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-254.

#### `al-d3-255-fast` — Layer Explode · Fast
**طبقات تنفصل · سريع**

*accent · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-255*

Variant of M-255: أسرع بـ 40%

**Spec (EN):** Tilt a stack of layers into an isometric view and push each layer apart on Z (0, 8%, 16%…), then bring them back together.

**Spec (AR):** ميّل كومة الطبقات لزاوية جانبية، وبعّد كل طبقة عن الثانية على Z (0، 8%، 16%…)، وبعدين رجّعهم مع بعض.

**When to use:**
- EN: Use when you need a fast version of M-255.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-255.

#### `al-d3-255-slow` — Layer Explode · Slow
**طبقات تنفصل · بطيء**

*accent · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-255*

Variant of M-255: أبطأ بـ 60%

**Spec (EN):** Tilt a stack of layers into an isometric view and push each layer apart on Z (0, 8%, 16%…), then bring them back together.

**Spec (AR):** ميّل كومة الطبقات لزاوية جانبية، وبعّد كل طبقة عن الثانية على Z (0، 8%، 16%…)، وبعدين رجّعهم مع بعض.

**When to use:**
- EN: Use when you need a slow version of M-255.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-255.

#### `al-d3-255-gold` — Layer Explode · Gold
**طبقات تنفصل · ذهبي**

*accent · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-255*

Variant of M-255: نسخة ذهبية فاخرة

**Spec (EN):** Tilt a stack of layers into an isometric view and push each layer apart on Z (0, 8%, 16%…), then bring them back together.

**Spec (AR):** ميّل كومة الطبقات لزاوية جانبية، وبعّد كل طبقة عن الثانية على Z (0، 8%، 16%…)، وبعدين رجّعهم مع بعض.

**When to use:**
- EN: Use when you need a gold version of M-255.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-255.

#### `al-d3-255-boxed` — Layer Explode · Boxed
**طبقات تنفصل · صندوق**

*accent · any · timeline · easing: easeInOutCubic · 0.8s*

*Original: M-255*

Variant of M-255: النص داخل صندوق ملون

**Spec (EN):** Tilt a stack of layers into an isometric view and push each layer apart on Z (0, 8%, 16%…), then bring them back together.

**Spec (AR):** ميّل كومة الطبقات لزاوية جانبية، وبعّد كل طبقة عن الثانية على Z (0، 8%، 16%…)، وبعدين رجّعهم مع بعض.

**When to use:**
- EN: Use when you need a boxed version of M-255.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-255.

#### `al-d3-256-fast` — 3D Carousel · Fast
**عجلة بطاقات · سريع**

*accent · calm · depth · easing: linear · loop · 6s*

*Original: M-256*

Variant of M-256: أسرع بـ 40%

**Spec (EN):** Place 5–8 cards evenly around a 3D ring (rotateY steps + translateZ) and rotate the ring slowly.

**Spec (AR):** حط من 5 إلى 8 بطاقات متساوية حول حلقة 3D (rotateY ثم translateZ)، ولف الحلقة ببطء.

**When to use:**
- EN: Use when you need a fast version of M-256.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-256.

#### `al-d3-256-slow` — 3D Carousel · Slow
**عجلة بطاقات · بطيء**

*accent · calm · depth · easing: linear · loop · 6s*

*Original: M-256*

Variant of M-256: أبطأ بـ 60%

**Spec (EN):** Place 5–8 cards evenly around a 3D ring (rotateY steps + translateZ) and rotate the ring slowly.

**Spec (AR):** حط من 5 إلى 8 بطاقات متساوية حول حلقة 3D (rotateY ثم translateZ)، ولف الحلقة ببطء.

**When to use:**
- EN: Use when you need a slow version of M-256.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-256.

#### `al-d3-256-gold` — 3D Carousel · Gold
**عجلة بطاقات · ذهبي**

*accent · calm · depth · easing: linear · loop · 6s*

*Original: M-256*

Variant of M-256: نسخة ذهبية فاخرة

**Spec (EN):** Place 5–8 cards evenly around a 3D ring (rotateY steps + translateZ) and rotate the ring slowly.

**Spec (AR):** حط من 5 إلى 8 بطاقات متساوية حول حلقة 3D (rotateY ثم translateZ)، ولف الحلقة ببطء.

**When to use:**
- EN: Use when you need a gold version of M-256.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-256.

#### `al-d3-256-boxed` — 3D Carousel · Boxed
**عجلة بطاقات · صندوق**

*accent · calm · depth · easing: linear · loop · 6s*

*Original: M-256*

Variant of M-256: النص داخل صندوق ملون

**Spec (EN):** Place 5–8 cards evenly around a 3D ring (rotateY steps + translateZ) and rotate the ring slowly.

**Spec (AR):** حط من 5 إلى 8 بطاقات متساوية حول حلقة 3D (rotateY ثم translateZ)، ولف الحلقة ببطء.

**When to use:**
- EN: Use when you need a boxed version of M-256.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-256.

#### `al-d3-257-fast` — Float Shadow · Fast
**عنصر يطفو مع ظل · سريع**

*accent · calm · depth · easing: easeInOutSine · loop · 3s*

*Original: M-257*

Variant of M-257: أسرع بـ 40%

**Spec (EN):** Bob the object up 6% with a slight rotation while its drop shadow grows softer and lighter at the top of the motion.

**Spec (AR):** خل العنصر يطلع لفوق 6% مع دوران خفيف، وظله تحته يصير أنعم وأخف لمن يكون فوق.

**When to use:**
- EN: Use when you need a fast version of M-257.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-257.

#### `al-d3-257-slow` — Float Shadow · Slow
**عنصر يطفو مع ظل · بطيء**

*accent · calm · depth · easing: easeInOutSine · loop · 3s*

*Original: M-257*

Variant of M-257: أبطأ بـ 60%

**Spec (EN):** Bob the object up 6% with a slight rotation while its drop shadow grows softer and lighter at the top of the motion.

**Spec (AR):** خل العنصر يطلع لفوق 6% مع دوران خفيف، وظله تحته يصير أنعم وأخف لمن يكون فوق.

**When to use:**
- EN: Use when you need a slow version of M-257.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-257.

#### `al-d3-257-gold` — Float Shadow · Gold
**عنصر يطفو مع ظل · ذهبي**

*accent · calm · depth · easing: easeInOutSine · loop · 3s*

*Original: M-257*

Variant of M-257: نسخة ذهبية فاخرة

**Spec (EN):** Bob the object up 6% with a slight rotation while its drop shadow grows softer and lighter at the top of the motion.

**Spec (AR):** خل العنصر يطلع لفوق 6% مع دوران خفيف، وظله تحته يصير أنعم وأخف لمن يكون فوق.

**When to use:**
- EN: Use when you need a gold version of M-257.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-257.

#### `al-d3-257-boxed` — Float Shadow · Boxed
**عنصر يطفو مع ظل · صندوق**

*accent · calm · depth · easing: easeInOutSine · loop · 3s*

*Original: M-257*

Variant of M-257: النص داخل صندوق ملون

**Spec (EN):** Bob the object up 6% with a slight rotation while its drop shadow grows softer and lighter at the top of the motion.

**Spec (AR):** خل العنصر يطلع لفوق 6% مع دوران خفيف، وظله تحته يصير أنعم وأخف لمن يكون فوق.

**When to use:**
- EN: Use when you need a boxed version of M-257.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-257.

#### `al-d3-258-fast` — Coin Flip · Fast
**عملة تنقلب · سريع**

*accent · calm · depth · easing: easeInOutQuad · 1.2s*

*Original: M-258*

Variant of M-258: أسرع بـ 40%

**Spec (EN):** A two-sided coin rises and falls while spinning several times around the Y axis over about 1.2s, landing on one face.

**Spec (AR):** عملة بوجهين تطلع وتنزل وهي تلف كم لفة على المحور العمودي خلال تقريباً 1.2 ثانية، وتوقف على وجه.

**When to use:**
- EN: Use when you need a fast version of M-258.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-258.

#### `al-d3-258-slow` — Coin Flip · Slow
**عملة تنقلب · بطيء**

*accent · calm · depth · easing: easeInOutQuad · 1.2s*

*Original: M-258*

Variant of M-258: أبطأ بـ 60%

**Spec (EN):** A two-sided coin rises and falls while spinning several times around the Y axis over about 1.2s, landing on one face.

**Spec (AR):** عملة بوجهين تطلع وتنزل وهي تلف كم لفة على المحور العمودي خلال تقريباً 1.2 ثانية، وتوقف على وجه.

**When to use:**
- EN: Use when you need a slow version of M-258.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-258.

#### `al-d3-258-gold` — Coin Flip · Gold
**عملة تنقلب · ذهبي**

*accent · calm · depth · easing: easeInOutQuad · 1.2s*

*Original: M-258*

Variant of M-258: نسخة ذهبية فاخرة

**Spec (EN):** A two-sided coin rises and falls while spinning several times around the Y axis over about 1.2s, landing on one face.

**Spec (AR):** عملة بوجهين تطلع وتنزل وهي تلف كم لفة على المحور العمودي خلال تقريباً 1.2 ثانية، وتوقف على وجه.

**When to use:**
- EN: Use when you need a gold version of M-258.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-258.

#### `al-d3-258-boxed` — Coin Flip · Boxed
**عملة تنقلب · صندوق**

*accent · calm · depth · easing: easeInOutQuad · 1.2s*

*Original: M-258*

Variant of M-258: النص داخل صندوق ملون

**Spec (EN):** A two-sided coin rises and falls while spinning several times around the Y axis over about 1.2s, landing on one face.

**Spec (AR):** عملة بوجهين تطلع وتنزل وهي تلف كم لفة على المحور العمودي خلال تقريباً 1.2 ثانية، وتوقف على وجه.

**When to use:**
- EN: Use when you need a boxed version of M-258.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-258.

### Time FX (تأثيرات الوقت) — 40 motions

#### `al-tim-259` — Reverse
**عكس الفيديو**

*workhorse · calm · depth · easing: linear · clip length*

*Original: M-259*

The clip plays backwards for surprise or fun.

**Spec (EN):** Play the selected segment backwards (frames in reverse order) and show a small "◀◀" tag in the corner.

**Spec (AR):** شغّل الجزء المختار بالعكس (الفريمات من آخرها لأولها)، وطلّع تاق صغير "◀◀" بالزاوية.

**When to use:**
- EN: The clip plays backwards for surprise or fun.
- AR: الفيديو يرجع لورا، للمفاجأة أو الضحك.

#### `al-tim-260` — Boomerang
**بومرنغ**

*workhorse · calm · timeline · easing: linear · loop · 1s*

*Original: M-260*

A short clip plays forward and back in a loop.

**Spec (EN):** Take a 0.5–1s segment and play it forward then backward repeatedly, like a boomerang.

**Spec (AR):** خذ جزء من 0.5 إلى ثانية وشغّله قدام وبعدين ورا بتكرار، مثل البومرنغ.

**When to use:**
- EN: A short clip plays forward and back in a loop.
- AR: لقطة قصيرة تروح وترجع بتكرار.

#### `al-tim-261` — Stop Motion
**ستوب موشن**

*workhorse · any · depth · easing: steps · 12fps*

*Original: M-261*

Choppy, frame-by-frame motion like stop motion.

**Spec (EN):** Drop the frame rate to about 8–12fps by holding each frame for 3–4 frames, giving a choppy stop-motion feel.

**Spec (AR):** نزّل عدد الفريمات لتقريباً 8 إلى 12 بالثانية بتثبيت كل فريم 3 إلى 4 فريمات، فتطلع الحركة متقطعة مثل الستوب موشن.

**When to use:**
- EN: Choppy, frame-by-frame motion like stop motion.
- AR: حركة متقطعة مثل الرسوم المصورة.

#### `al-tim-262` — Strobe
**ستروب**

*workhorse · any · blur · easing: steps · 0.8s*

*Original: M-262*

Frozen copies of a move stay behind it.

**Spec (EN):** Every 4 frames, freeze a copy of the person at about 35% opacity so the motion leaves a trail of still poses.

**Spec (AR):** كل 4 فريمات، ثبّت نسخة من الشخص بشفافية تقريباً 35%، فالحركة تخلي وراها وقفات ثابتة.

**When to use:**
- EN: Frozen copies of a move stay behind it.
- AR: نسخ ثابتة من الحركة تبقى ورا بعض.

#### `al-tim-263` — Time-Lapse Clock
**ساعة تسرّع**

*workhorse · calm · depth · easing: linear · 1.5s*

*Original: M-263*

Clock hands spin fast, like "hours later".

**Spec (EN):** A clock face with the minute hand spinning many turns and the hour hand moving slowly, for 1–2s, with a "+3h" style label.

**Spec (AR):** ساعة عقرب الدقايق فيها يلف لفات كثيرة وعقرب الساعات يمشي ببطء، لمدة ثانية إلى ثانيتين، مع تاق مثل "+3h".

**When to use:**
- EN: Clock hands spin fast, like "hours later".
- AR: ساعة عقاربها تلف بسرعة، مثل "بعد ساعات".

#### `al-tim-264` — Day to Night
**من النهار لليل**

*workhorse · calm · timeline · easing: easeInOutSine · 2s*

*Original: M-264*

The lighting shifts as if time passes.

**Spec (EN):** Grade the shot from warm daylight to a cool, darker night look over about 2s (color temperature, exposure and saturation).

**Spec (AR):** غيّر ألوان اللقطة من نهار دافي لليل بارد وأغمق خلال تقريباً ثانيتين (حرارة اللون، والإضاءة، والتشبع).

**When to use:**
- EN: The lighting shifts as if time passes.
- AR: الإضاءة تتغير كأن الوقت يمشي.

#### `al-tim-265` — Fast Forward
**تقديم سريع**

*workhorse · calm · blur · easing: linear · clip length*

*Original: M-265*

The clip speeds up with a ▶▶ tag.

**Spec (EN):** Play the segment at 2–4× speed with a "▶▶ 4×" tag and a light motion blur.

**Spec (AR):** شغّل الجزء بسرعة 2 إلى 4 مرات مع تاق "▶▶ 4×" وضبابية حركة خفيفة.

**When to use:**
- EN: The clip speeds up with a ▶▶ tag.
- AR: الفيديو يسرع مع تاق ▶▶.

#### `al-tim-266` — Rewind Glitch
**ترجيع مع تشويش**

*workhorse · any · timeline · easing: steps · 0.6s*

*Original: M-266*

A fast rewind with tape-like noise lines.

**Spec (EN):** Play the last second backwards at 3× with VHS noise lines (M-155) and a "◀◀ REW" tag, then cut back to normal.

**Spec (AR):** شغّل آخر ثانية بالعكس بسرعة 3 مرات مع خطوط تشويش (M-155) وتاق "◀◀ REW"، وبعدين ارجع طبيعي.

**When to use:**
- EN: A fast rewind with tape-like noise lines.
- AR: ترجيع سريع مع خطوط تشويش، مثل الشريط.

#### `al-tim-259-fast` — Reverse · Fast
**عكس الفيديو · سريع**

*accent · calm · depth · easing: linear · clip length*

*Original: M-259*

Variant of M-259: أسرع بـ 40%

**Spec (EN):** Play the selected segment backwards (frames in reverse order) and show a small "◀◀" tag in the corner.

**Spec (AR):** شغّل الجزء المختار بالعكس (الفريمات من آخرها لأولها)، وطلّع تاق صغير "◀◀" بالزاوية.

**When to use:**
- EN: Use when you need a fast version of M-259.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-259.

#### `al-tim-259-slow` — Reverse · Slow
**عكس الفيديو · بطيء**

*accent · calm · depth · easing: linear · clip length*

*Original: M-259*

Variant of M-259: أبطأ بـ 60%

**Spec (EN):** Play the selected segment backwards (frames in reverse order) and show a small "◀◀" tag in the corner.

**Spec (AR):** شغّل الجزء المختار بالعكس (الفريمات من آخرها لأولها)، وطلّع تاق صغير "◀◀" بالزاوية.

**When to use:**
- EN: Use when you need a slow version of M-259.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-259.

#### `al-tim-259-gold` — Reverse · Gold
**عكس الفيديو · ذهبي**

*accent · calm · depth · easing: linear · clip length*

*Original: M-259*

Variant of M-259: نسخة ذهبية فاخرة

**Spec (EN):** Play the selected segment backwards (frames in reverse order) and show a small "◀◀" tag in the corner.

**Spec (AR):** شغّل الجزء المختار بالعكس (الفريمات من آخرها لأولها)، وطلّع تاق صغير "◀◀" بالزاوية.

**When to use:**
- EN: Use when you need a gold version of M-259.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-259.

#### `al-tim-259-boxed` — Reverse · Boxed
**عكس الفيديو · صندوق**

*accent · calm · depth · easing: linear · clip length*

*Original: M-259*

Variant of M-259: النص داخل صندوق ملون

**Spec (EN):** Play the selected segment backwards (frames in reverse order) and show a small "◀◀" tag in the corner.

**Spec (AR):** شغّل الجزء المختار بالعكس (الفريمات من آخرها لأولها)، وطلّع تاق صغير "◀◀" بالزاوية.

**When to use:**
- EN: Use when you need a boxed version of M-259.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-259.

#### `al-tim-260-fast` — Boomerang · Fast
**بومرنغ · سريع**

*accent · calm · timeline · easing: linear · loop · 1s*

*Original: M-260*

Variant of M-260: أسرع بـ 40%

**Spec (EN):** Take a 0.5–1s segment and play it forward then backward repeatedly, like a boomerang.

**Spec (AR):** خذ جزء من 0.5 إلى ثانية وشغّله قدام وبعدين ورا بتكرار، مثل البومرنغ.

**When to use:**
- EN: Use when you need a fast version of M-260.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-260.

#### `al-tim-260-slow` — Boomerang · Slow
**بومرنغ · بطيء**

*accent · calm · timeline · easing: linear · loop · 1s*

*Original: M-260*

Variant of M-260: أبطأ بـ 60%

**Spec (EN):** Take a 0.5–1s segment and play it forward then backward repeatedly, like a boomerang.

**Spec (AR):** خذ جزء من 0.5 إلى ثانية وشغّله قدام وبعدين ورا بتكرار، مثل البومرنغ.

**When to use:**
- EN: Use when you need a slow version of M-260.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-260.

#### `al-tim-260-gold` — Boomerang · Gold
**بومرنغ · ذهبي**

*accent · calm · timeline · easing: linear · loop · 1s*

*Original: M-260*

Variant of M-260: نسخة ذهبية فاخرة

**Spec (EN):** Take a 0.5–1s segment and play it forward then backward repeatedly, like a boomerang.

**Spec (AR):** خذ جزء من 0.5 إلى ثانية وشغّله قدام وبعدين ورا بتكرار، مثل البومرنغ.

**When to use:**
- EN: Use when you need a gold version of M-260.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-260.

#### `al-tim-260-boxed` — Boomerang · Boxed
**بومرنغ · صندوق**

*accent · calm · timeline · easing: linear · loop · 1s*

*Original: M-260*

Variant of M-260: النص داخل صندوق ملون

**Spec (EN):** Take a 0.5–1s segment and play it forward then backward repeatedly, like a boomerang.

**Spec (AR):** خذ جزء من 0.5 إلى ثانية وشغّله قدام وبعدين ورا بتكرار، مثل البومرنغ.

**When to use:**
- EN: Use when you need a boxed version of M-260.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-260.

#### `al-tim-261-fast` — Stop Motion · Fast
**ستوب موشن · سريع**

*accent · any · depth · easing: steps · 12fps*

*Original: M-261*

Variant of M-261: أسرع بـ 40%

**Spec (EN):** Drop the frame rate to about 8–12fps by holding each frame for 3–4 frames, giving a choppy stop-motion feel.

**Spec (AR):** نزّل عدد الفريمات لتقريباً 8 إلى 12 بالثانية بتثبيت كل فريم 3 إلى 4 فريمات، فتطلع الحركة متقطعة مثل الستوب موشن.

**When to use:**
- EN: Use when you need a fast version of M-261.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-261.

#### `al-tim-261-slow` — Stop Motion · Slow
**ستوب موشن · بطيء**

*accent · any · depth · easing: steps · 12fps*

*Original: M-261*

Variant of M-261: أبطأ بـ 60%

**Spec (EN):** Drop the frame rate to about 8–12fps by holding each frame for 3–4 frames, giving a choppy stop-motion feel.

**Spec (AR):** نزّل عدد الفريمات لتقريباً 8 إلى 12 بالثانية بتثبيت كل فريم 3 إلى 4 فريمات، فتطلع الحركة متقطعة مثل الستوب موشن.

**When to use:**
- EN: Use when you need a slow version of M-261.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-261.

#### `al-tim-261-gold` — Stop Motion · Gold
**ستوب موشن · ذهبي**

*accent · any · depth · easing: steps · 12fps*

*Original: M-261*

Variant of M-261: نسخة ذهبية فاخرة

**Spec (EN):** Drop the frame rate to about 8–12fps by holding each frame for 3–4 frames, giving a choppy stop-motion feel.

**Spec (AR):** نزّل عدد الفريمات لتقريباً 8 إلى 12 بالثانية بتثبيت كل فريم 3 إلى 4 فريمات، فتطلع الحركة متقطعة مثل الستوب موشن.

**When to use:**
- EN: Use when you need a gold version of M-261.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-261.

#### `al-tim-261-boxed` — Stop Motion · Boxed
**ستوب موشن · صندوق**

*accent · any · depth · easing: steps · 12fps*

*Original: M-261*

Variant of M-261: النص داخل صندوق ملون

**Spec (EN):** Drop the frame rate to about 8–12fps by holding each frame for 3–4 frames, giving a choppy stop-motion feel.

**Spec (AR):** نزّل عدد الفريمات لتقريباً 8 إلى 12 بالثانية بتثبيت كل فريم 3 إلى 4 فريمات، فتطلع الحركة متقطعة مثل الستوب موشن.

**When to use:**
- EN: Use when you need a boxed version of M-261.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-261.

#### `al-tim-262-fast` — Strobe · Fast
**ستروب · سريع**

*accent · any · blur · easing: steps · 0.8s*

*Original: M-262*

Variant of M-262: أسرع بـ 40%

**Spec (EN):** Every 4 frames, freeze a copy of the person at about 35% opacity so the motion leaves a trail of still poses.

**Spec (AR):** كل 4 فريمات، ثبّت نسخة من الشخص بشفافية تقريباً 35%، فالحركة تخلي وراها وقفات ثابتة.

**When to use:**
- EN: Use when you need a fast version of M-262.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-262.

#### `al-tim-262-slow` — Strobe · Slow
**ستروب · بطيء**

*accent · any · blur · easing: steps · 0.8s*

*Original: M-262*

Variant of M-262: أبطأ بـ 60%

**Spec (EN):** Every 4 frames, freeze a copy of the person at about 35% opacity so the motion leaves a trail of still poses.

**Spec (AR):** كل 4 فريمات، ثبّت نسخة من الشخص بشفافية تقريباً 35%، فالحركة تخلي وراها وقفات ثابتة.

**When to use:**
- EN: Use when you need a slow version of M-262.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-262.

#### `al-tim-262-gold` — Strobe · Gold
**ستروب · ذهبي**

*accent · any · blur · easing: steps · 0.8s*

*Original: M-262*

Variant of M-262: نسخة ذهبية فاخرة

**Spec (EN):** Every 4 frames, freeze a copy of the person at about 35% opacity so the motion leaves a trail of still poses.

**Spec (AR):** كل 4 فريمات، ثبّت نسخة من الشخص بشفافية تقريباً 35%، فالحركة تخلي وراها وقفات ثابتة.

**When to use:**
- EN: Use when you need a gold version of M-262.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-262.

#### `al-tim-262-boxed` — Strobe · Boxed
**ستروب · صندوق**

*accent · any · blur · easing: steps · 0.8s*

*Original: M-262*

Variant of M-262: النص داخل صندوق ملون

**Spec (EN):** Every 4 frames, freeze a copy of the person at about 35% opacity so the motion leaves a trail of still poses.

**Spec (AR):** كل 4 فريمات، ثبّت نسخة من الشخص بشفافية تقريباً 35%، فالحركة تخلي وراها وقفات ثابتة.

**When to use:**
- EN: Use when you need a boxed version of M-262.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-262.

#### `al-tim-263-fast` — Time-Lapse Clock · Fast
**ساعة تسرّع · سريع**

*accent · calm · depth · easing: linear · 1.5s*

*Original: M-263*

Variant of M-263: أسرع بـ 40%

**Spec (EN):** A clock face with the minute hand spinning many turns and the hour hand moving slowly, for 1–2s, with a "+3h" style label.

**Spec (AR):** ساعة عقرب الدقايق فيها يلف لفات كثيرة وعقرب الساعات يمشي ببطء، لمدة ثانية إلى ثانيتين، مع تاق مثل "+3h".

**When to use:**
- EN: Use when you need a fast version of M-263.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-263.

#### `al-tim-263-slow` — Time-Lapse Clock · Slow
**ساعة تسرّع · بطيء**

*accent · calm · depth · easing: linear · 1.5s*

*Original: M-263*

Variant of M-263: أبطأ بـ 60%

**Spec (EN):** A clock face with the minute hand spinning many turns and the hour hand moving slowly, for 1–2s, with a "+3h" style label.

**Spec (AR):** ساعة عقرب الدقايق فيها يلف لفات كثيرة وعقرب الساعات يمشي ببطء، لمدة ثانية إلى ثانيتين، مع تاق مثل "+3h".

**When to use:**
- EN: Use when you need a slow version of M-263.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-263.

#### `al-tim-263-gold` — Time-Lapse Clock · Gold
**ساعة تسرّع · ذهبي**

*accent · calm · depth · easing: linear · 1.5s*

*Original: M-263*

Variant of M-263: نسخة ذهبية فاخرة

**Spec (EN):** A clock face with the minute hand spinning many turns and the hour hand moving slowly, for 1–2s, with a "+3h" style label.

**Spec (AR):** ساعة عقرب الدقايق فيها يلف لفات كثيرة وعقرب الساعات يمشي ببطء، لمدة ثانية إلى ثانيتين، مع تاق مثل "+3h".

**When to use:**
- EN: Use when you need a gold version of M-263.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-263.

#### `al-tim-263-boxed` — Time-Lapse Clock · Boxed
**ساعة تسرّع · صندوق**

*accent · calm · depth · easing: linear · 1.5s*

*Original: M-263*

Variant of M-263: النص داخل صندوق ملون

**Spec (EN):** A clock face with the minute hand spinning many turns and the hour hand moving slowly, for 1–2s, with a "+3h" style label.

**Spec (AR):** ساعة عقرب الدقايق فيها يلف لفات كثيرة وعقرب الساعات يمشي ببطء، لمدة ثانية إلى ثانيتين، مع تاق مثل "+3h".

**When to use:**
- EN: Use when you need a boxed version of M-263.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-263.

#### `al-tim-264-fast` — Day to Night · Fast
**من النهار لليل · سريع**

*accent · calm · timeline · easing: easeInOutSine · 2s*

*Original: M-264*

Variant of M-264: أسرع بـ 40%

**Spec (EN):** Grade the shot from warm daylight to a cool, darker night look over about 2s (color temperature, exposure and saturation).

**Spec (AR):** غيّر ألوان اللقطة من نهار دافي لليل بارد وأغمق خلال تقريباً ثانيتين (حرارة اللون، والإضاءة، والتشبع).

**When to use:**
- EN: Use when you need a fast version of M-264.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-264.

#### `al-tim-264-slow` — Day to Night · Slow
**من النهار لليل · بطيء**

*accent · calm · timeline · easing: easeInOutSine · 2s*

*Original: M-264*

Variant of M-264: أبطأ بـ 60%

**Spec (EN):** Grade the shot from warm daylight to a cool, darker night look over about 2s (color temperature, exposure and saturation).

**Spec (AR):** غيّر ألوان اللقطة من نهار دافي لليل بارد وأغمق خلال تقريباً ثانيتين (حرارة اللون، والإضاءة، والتشبع).

**When to use:**
- EN: Use when you need a slow version of M-264.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-264.

#### `al-tim-264-gold` — Day to Night · Gold
**من النهار لليل · ذهبي**

*accent · calm · timeline · easing: easeInOutSine · 2s*

*Original: M-264*

Variant of M-264: نسخة ذهبية فاخرة

**Spec (EN):** Grade the shot from warm daylight to a cool, darker night look over about 2s (color temperature, exposure and saturation).

**Spec (AR):** غيّر ألوان اللقطة من نهار دافي لليل بارد وأغمق خلال تقريباً ثانيتين (حرارة اللون، والإضاءة، والتشبع).

**When to use:**
- EN: Use when you need a gold version of M-264.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-264.

#### `al-tim-264-boxed` — Day to Night · Boxed
**من النهار لليل · صندوق**

*accent · calm · timeline · easing: easeInOutSine · 2s*

*Original: M-264*

Variant of M-264: النص داخل صندوق ملون

**Spec (EN):** Grade the shot from warm daylight to a cool, darker night look over about 2s (color temperature, exposure and saturation).

**Spec (AR):** غيّر ألوان اللقطة من نهار دافي لليل بارد وأغمق خلال تقريباً ثانيتين (حرارة اللون، والإضاءة، والتشبع).

**When to use:**
- EN: Use when you need a boxed version of M-264.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-264.

#### `al-tim-265-fast` — Fast Forward · Fast
**تقديم سريع · سريع**

*accent · calm · blur · easing: linear · clip length*

*Original: M-265*

Variant of M-265: أسرع بـ 40%

**Spec (EN):** Play the segment at 2–4× speed with a "▶▶ 4×" tag and a light motion blur.

**Spec (AR):** شغّل الجزء بسرعة 2 إلى 4 مرات مع تاق "▶▶ 4×" وضبابية حركة خفيفة.

**When to use:**
- EN: Use when you need a fast version of M-265.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-265.

#### `al-tim-265-slow` — Fast Forward · Slow
**تقديم سريع · بطيء**

*accent · calm · blur · easing: linear · clip length*

*Original: M-265*

Variant of M-265: أبطأ بـ 60%

**Spec (EN):** Play the segment at 2–4× speed with a "▶▶ 4×" tag and a light motion blur.

**Spec (AR):** شغّل الجزء بسرعة 2 إلى 4 مرات مع تاق "▶▶ 4×" وضبابية حركة خفيفة.

**When to use:**
- EN: Use when you need a slow version of M-265.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-265.

#### `al-tim-265-gold` — Fast Forward · Gold
**تقديم سريع · ذهبي**

*accent · calm · blur · easing: linear · clip length*

*Original: M-265*

Variant of M-265: نسخة ذهبية فاخرة

**Spec (EN):** Play the segment at 2–4× speed with a "▶▶ 4×" tag and a light motion blur.

**Spec (AR):** شغّل الجزء بسرعة 2 إلى 4 مرات مع تاق "▶▶ 4×" وضبابية حركة خفيفة.

**When to use:**
- EN: Use when you need a gold version of M-265.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-265.

#### `al-tim-265-boxed` — Fast Forward · Boxed
**تقديم سريع · صندوق**

*accent · calm · blur · easing: linear · clip length*

*Original: M-265*

Variant of M-265: النص داخل صندوق ملون

**Spec (EN):** Play the segment at 2–4× speed with a "▶▶ 4×" tag and a light motion blur.

**Spec (AR):** شغّل الجزء بسرعة 2 إلى 4 مرات مع تاق "▶▶ 4×" وضبابية حركة خفيفة.

**When to use:**
- EN: Use when you need a boxed version of M-265.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-265.

#### `al-tim-266-fast` — Rewind Glitch · Fast
**ترجيع مع تشويش · سريع**

*accent · any · timeline · easing: steps · 0.6s*

*Original: M-266*

Variant of M-266: أسرع بـ 40%

**Spec (EN):** Play the last second backwards at 3× with VHS noise lines (M-155) and a "◀◀ REW" tag, then cut back to normal.

**Spec (AR):** شغّل آخر ثانية بالعكس بسرعة 3 مرات مع خطوط تشويش (M-155) وتاق "◀◀ REW"، وبعدين ارجع طبيعي.

**When to use:**
- EN: Use when you need a fast version of M-266.
- AR: استخدم عندما تحتاج نسخة أسرع بـ 40% من M-266.

#### `al-tim-266-slow` — Rewind Glitch · Slow
**ترجيع مع تشويش · بطيء**

*accent · any · timeline · easing: steps · 0.6s*

*Original: M-266*

Variant of M-266: أبطأ بـ 60%

**Spec (EN):** Play the last second backwards at 3× with VHS noise lines (M-155) and a "◀◀ REW" tag, then cut back to normal.

**Spec (AR):** شغّل آخر ثانية بالعكس بسرعة 3 مرات مع خطوط تشويش (M-155) وتاق "◀◀ REW"، وبعدين ارجع طبيعي.

**When to use:**
- EN: Use when you need a slow version of M-266.
- AR: استخدم عندما تحتاج نسخة أبطأ بـ 60% من M-266.

#### `al-tim-266-gold` — Rewind Glitch · Gold
**ترجيع مع تشويش · ذهبي**

*accent · any · timeline · easing: steps · 0.6s*

*Original: M-266*

Variant of M-266: نسخة ذهبية فاخرة

**Spec (EN):** Play the last second backwards at 3× with VHS noise lines (M-155) and a "◀◀ REW" tag, then cut back to normal.

**Spec (AR):** شغّل آخر ثانية بالعكس بسرعة 3 مرات مع خطوط تشويش (M-155) وتاق "◀◀ REW"، وبعدين ارجع طبيعي.

**When to use:**
- EN: Use when you need a gold version of M-266.
- AR: استخدم عندما تحتاج نسخة نسخة ذهبية فاخرة من M-266.

#### `al-tim-266-boxed` — Rewind Glitch · Boxed
**ترجيع مع تشويش · صندوق**

*accent · any · timeline · easing: steps · 0.6s*

*Original: M-266*

Variant of M-266: النص داخل صندوق ملون

**Spec (EN):** Play the last second backwards at 3× with VHS noise lines (M-155) and a "◀◀ REW" tag, then cut back to normal.

**Spec (AR):** شغّل آخر ثانية بالعكس بسرعة 3 مرات مع خطوط تشويش (M-155) وتاق "◀◀ REW"، وبعدين ارجع طبيعي.

**When to use:**
- EN: Use when you need a boxed version of M-266.
- AR: استخدم عندما تحتاج نسخة النص داخل صندوق ملون من M-266.
