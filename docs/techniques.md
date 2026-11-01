# Technique library

Adapted from [cinetic](https://github.com/Leonxlnx/cinetic) (MIT) and re-measured for this studio.
Draw a plan with `python3 tools/techniques.py --draw --from-plan plan/beats.json`; this page is
generated from `assets/techniques.json` (`--markdown docs/techniques.md`), so edit the JSON, not this.

**41 techniques** · seconds per pick: calm 3.5s, medium 2.5s, high 2.5s

## Opening Hook

### `oh-cold-open-mid-move` — Cold open mid-move

*workhorse · any · timeline · evidence 5 · first change ≤ 0.10 s; first readable word ≈ 0.40 s*

No fade from black, no title card. Frame 1 is already in motion: the camera is mid-push, a word is half-built, the grid is already crawling. The first visible change lands inside 0.10 s.

**How:** Draw local time as t + 0.35 s into every entrance so nothing starts at rest: P `lib.prog(t+0.35,a,b)` / K `seg(t + 0.35, start, dur)`. Never call a fade at t=0; the paper flood, the pose and the HUD all exist on the first frame.

**Use when:** Always. It is the cheapest way to read as directed instead of generated.

**Avoid when:** Never — the only exception is a deliberate cold open on a still, which must then slam within 0.4 s.

### `oh-question-then-first-cut` — Question, then the first hard cut answers it

*signature · medium · timeline · evidence 2 · answer at 1.1–1.6 s, on the scene bound*

The opening fragment is the question the viewer already has; the first hard cut (median 1.3 s in) lands the answer as a picture, not a caption.

**How:** Put the question as one 2–4 word fragment in scene 1, and make scene 1 end exactly where the VO's first silence starts (`plan/beats.json` bounds). The answer is the close-up pose (`presenter.draw(fr, 'close-explain', t)`) or the 3D object arriving on the cut, with the `sfx` hit on that frame — never another line of type.

**Use when:** A VO whose first sentence is a premise or a problem.

**Avoid when:** The VO opens with a personal greeting — then open on the pose instead.

### `oh-word-arrives-with-the-move` — The first word arrives with the move, not before it

*workhorse · any · type · evidence 4 · 18–24 f settle at 30 fps, 4–10 f between words*

Nothing sits still waiting to be read. The first word enters at 40% ink and settles over 18–24 frames while the camera is still travelling.

**How:** P: `paste(sp, y+rise*(1-e_out(p)), alpha=0.4+0.6*e_out(p))` with rise 25 px over 0.6 s; K: `enter(t, start, {dur:0.62, from:0.4, rise:25})`. The camera keeps creeping (`cam-living-hold-creep`) underneath.

**Use when:** Every title, every fragment.

**Avoid when:** Never pair it with a scale start above 1.17× — that reads as a zoom, not a settle.

### `oh-one-beat-of-still-then-slam` — One beat of still, then the slam

*accent · high · timeline · evidence 3 · still 0.4–0.5 s, slam settles over 0.7 s*

A single deliberate empty beat (≤0.5 s in this studio) buys the first slam its weight. Used once per film, on the key claim.

**How:** Hold the pose and the paper still for 12–15 f, keep breathing only (`presenter.breathe`), then land the word at 1.4–2.1× scale with 2–4 f of `blur_steps` smear and settle in 20 f.

**Use when:** Once, on the line the film is actually about.

**Avoid when:** Twice in one reel, or anywhere the VO is still talking over it.

## Typography

### `ty-masked-baseline-rise` — Masked baseline rise

*workhorse · calm · type · evidence 4 · 10–12 f per word, 8 f apart (30 fps)*

Each word rises out of its own clipped line box, darkening from grey to ink. Whole words only — the mask is per word, never per letter.

**How:** P: build a sprite per word with `lib.text_sprite`, paste through a clip box whose height grows with `e_out(p)`; colour lerps `gray_4 → ink` over the same p. K: `ctx.save(); ctx.beginPath(); ctx.rect(x, lineTop, w, lineH*e); ctx.clip(); drawWord(...)`. Words 8 f apart, 10–12 f each.

**Use when:** The default entrance for Arabic headlines — it respects shaping because the clip never cuts a letter.

**Avoid when:** On a word that must be readable in under 0.4 s (a hook word) — use the settle instead.

### `ty-inplace-light-up-on-beats` — In-place light-up on the beat

*workhorse · calm · grid · evidence 4 · 1 step per word at 100–120 BPM, ramp 4 f, recency 12–24 f*

The finished line is laid out first; words light from `gray_2` to ink on successive grid steps, so the type follows the tempo without moving.

**How:** Lay the whole line at final positions, then per word pick a step from `beat.grid(bpm)` (`on_grid`) and ramp colour over 4 f. The newest word may take `red` for 12–24 f then settle to ink — once per card, not per word.

**Use when:** Long Arabic lines where motion would fight readability.

**Avoid when:** More than 8 words visible — the line becomes a scan.

### `ty-recentre-line-build` — Re-centring line build

*workhorse · medium · type · evidence 6 · 24–38 f re-centre, words 6–9 f apart*

Words arrive right-to-left (Arabic reading order) and the line re-centres once per word on an expo-out, never per letter.

**How:** Compute the final line width once; after each word lands, tween the line origin to `0.5 - width/2` with `e_out` over 24–38 f. Keep the vertical baseline fixed so only x breathes.

**Use when:** A short claim that grows to most of the frame width.

**Avoid when:** RTL is on and the words contain punctuation-only tokens — group them with the previous word first.

### `ty-staggered-word-roll` — Staggered word roll

*workhorse · medium · type · evidence 4 · 5–6 f per word, 20 f settle*

The outgoing word rises and blurs out while the incoming word comes up from below — a vertical roller inside one line, 5–6 f per word.

**How:** Two sprites per slot: outgoing at `y - 20*e`, `blur_steps` 6 px, alpha out over 10 f; incoming from `y + 24` settling in 20 f. Drive the slot changes from `beat` steps so it never drifts.

**Use when:** A list of three to five short Arabic terms that share a grammar.

**Avoid when:** Words longer than ~10 characters — the roll outruns the eye.

### `ty-reading-order-exit` — Reading-order exit

*workhorse · any · type · evidence 3 · exit finished 2 f before the cut*

Text rarely fades on its own. It leaves on the cut, or word by word in reading order, each rising 10–20 px and gone in 2–3 f.

**How:** Trigger the exit 6–8 f before the scene bound from `plan/beats.json`, front to back (Arabic: right to left), with the background already accelerating out (`transition` velocity curve).

**Use when:** Every fragment that does not die with its whole scene.

**Avoid when:** A hero line — it goes with the cut instead, never a slow fade.

### `ty-oversize-blur-slide-in` — Oversize word with velocity blur

*signature · high · blur · evidence 3 · sharp within 0.33 s, readable by 0.5 s*

One word at 15–30% of frame height travels in fast with directional blur, then goes pin-sharp within 10 f and is legible by 0.5 s.

**How:** Speed from the timeline (`velocity`), smear with `blur_steps(vx, vy)` (P) / `drawBlurred` (K), then draw the crisp pass once the speed drops under ~12 px/f. Blur lives only on the fast frames.

**Use when:** A two-word punchline in the middle act.

**Avoid when:** On a word the VO is also saying slowly — the two rhythms fight.

### `ty-scaled-echo-extrusion` — Scaled echo extrusion

*accent · medium · type · evidence 2 · static, revealed with the word (0.4 s)*

A word is repeated behind itself at stepped scales and descending opacity, reading as depth without a gradient or a glow.

**How:** Draw the sprite 4–7 times at `scale = 1 + i*0.06`, alpha `0.30 * (1 - i/n)`, offset 2–4 px per step, in `ink_shadow`; the front copy is full ink. Cheap, flat, and on-palette.

**Use when:** The one word that should feel monumental.

**Avoid when:** Small type, or over a textured background — the echoes turn to mush.

### `ty-vertical-word-stack` — Vertical word stack

*workhorse · medium · layout · evidence 1 · 6–8 f per line at 100 BPM*

Words stack down the 9:16 frame like a column, one per line, each landing on its own step — it turns the vertical format into an advantage.

**How:** One word per line at 12–16% of frame height, line pitch 1.15×, each arriving 6–8 f after the last on `e_out`, stacked from the top safe line downward; measure every word with `lib.text_sprite` first so a long word cannot overflow the 40 px margin, and give the last line the accent.

**Use when:** Three to five short terms, or a list that must fill the tall frame.

**Avoid when:** Words longer than the frame width at that size — check with the measured sprite width first.

### `ty-scramble-decode-latin-only` — Scramble decode (Latin readouts only)

*accent · medium · type · evidence 3 · 12–18 f, always shorter than the word it decorates*

A mono readout resolves from random glyphs, one character at a time. It is a Latin/mono device: Arabic is banned from it.

**How:** For HUD numbers and mono labels only (`IBM Plex Mono`), seed a `rng(seed)` and reveal left to right in 12–18 f. Arabic never uses it — per-letter reveal breaks shaping and the studio rules.

**Use when:** A counter, a timestamp, a version tag.

**Avoid when:** Any Arabic word, any word the viewer must read.

## Transition

### `tr-velocity-handoff-cut` — Velocity handoff cut

*workhorse · any · transition · evidence 9 · exit accel 10–18 f, decay τ ≈ 12 f*

The outgoing shot accelerates over its last 0.3–0.6 s and the next shot starts at exactly that speed, so the cut is felt as one move.

**How:** Before a bound: ease in to the exit (`x = e_in(p)`), peak 25–45 px/f at 1080-wide, and start the next scene with the same velocity decaying (`*0.92` per frame, τ ≈ 12 f at 30 fps). Keep the camera vector identical across the cut.

**Use when:** The default cut — it is the highest-evidence move in the library.

**Avoid when:** Between two static cards; with no speed to hand over it just looks like a jolt.

### `tr-scale-through-cut` — Scale-through cut

*signature · high · transition · evidence 6 · 14–18 f each way at 30 fps*

A shape (a word, a pill, the pose's silhouette) grows past the frame, and the next shot is revealed inside the same shape at the same scale rate.

**How:** Animate a mask rect/rounded-rect from 0.2× to 3× with `e_in` over 14–18 f, swap the plate at the peak, then continue outward from 3× to rest. `transition.layer()` masks already support this.

**Use when:** Act changes, or when a word becomes a container.

**Avoid when:** Twice in a row — it reads as a template.

### `tr-polarity-flip-cut` — Polarity flip cut

*accent · high · transition · evidence 6 · instant, on the scene bound*

Paper becomes ink (or the reverse) on the frame of the cut, with type and pose re-coloured instantly. No dissolve, no fade.

**How:** Flip the `THEME` flag on the cut frame and swap the two role colours (`paper ↔ ink`, `ink_shadow ↔ gray_1`); the pose sprite is re-tinted by its alpha mask, and the SFX hit lands on the same frame. It is a hard cut that changes world.

**Use when:** Acts that must feel like chapters.

**Avoid when:** More than twice — the film starts to strobe.

### `tr-shape-match-cut` — Shape match cut

*workhorse · medium · transition · evidence 4 · the match holds for 2–4 f around the cut*

Something in shot A (a circle, a bar, the mouth of a cup) is in the same place, size and colour as something in shot B, so the eye carries the object across.

**How:** Choose the match object once per film (the dot, the bar, the ring) and reuse it as the carrier — `lc-one-centred-subject` and `tr-dot-relay` both depend on it. Match centre within 6 px and radius within 4%.

**Use when:** When the film has a story device (it should).

**Avoid when:** Two diagonal compositions — the eye has no anchor to match.

### `tr-dot-relay` — Dot relay into the next scene

*signature · medium · transition · evidence 3 · 10 f collapse, 12–16 f growth*

Everything collapses to one dot, the dot travels, and the next scene grows out of it. The device the film owns is the thing that survives the cut.

**How:** Fade the composition to the accent dot over 8–10 f (`e_in`), carry the dot along a 40–70 px/f path across the cut, then scale the next scene from 0.05× around the dot in 12–16 f.

**Use when:** Mid-film, to link two unrelated pictures.

**Avoid when:** Collapsing to a dot that then means nothing — the relay must be the same object.

### `tr-subtract-reveal` — Reveal by subtraction

*workhorse · medium · transition · evidence 4 · 18–24 f, one direction only*

The frame is over-full, then everything that is not the point is removed in one move, leaving one object, one word, one pose.

**How:** Start with 3–5 layered props (`lc-one-centred-subject` inverse), then run a single scale-and-delete pass over 18–24 f in one direction, keeping the hero element exactly in place.

**Use when:** The moment the film makes its single point.

**Avoid when:** As a habit — it costs a whole scene to earn.

## Camera

### `cam-living-hold-creep` — Living hold creep

*workhorse · calm · camera · evidence 5 · continuous, one direction change per 6–9 s*

Nothing is ever locked. A held shot creeps 1.5–3 px/f with one direction change, so the frame is alive while the eye reads.

**How:** `z = 1 + 0.02*e_io(p)` plus `tx = 6*sin(2πt/T)` with T = 6–9 s, under any readable text. Cap the speed at 3 px/f — faster and the type stops being sharp.

**Use when:** Every shot longer than 1 s.

**Avoid when:** Nowhere — a locked camera is the tell that the sheet is generated.

### `cam-punch-in-insert` — Punch-in insert

*workhorse · medium · camera · evidence 5 · 6–8 f punch, settle 12 f*

At the cut, the same plate punches in 1.25–1.6× and lands a beat later — the cheapest way to make one scene feel like two.

**How:** Because Medo ships `full` and `bust` framings of the same pose (`assets/poses/poses.json`), cut from `explain` to `close-explain` and add 1.15–1.3× scale over 6 f so the face lands at the same size. Pure crop, no new art.

**Use when:** Emphasis on a single sentence, inside one VO scene.

**Avoid when:** More than once per scene — it stops meaning 'listen'.

### `cam-isolating-push` — Isolating push

*workhorse · medium · camera · evidence 3 · 0.7–1.0 s push*

A slow push toward the one object that matters while the rest of the frame drifts out of the safe area.

**How:** `z: 1 → 1.18` over 20–30 f with `e_io`, target = the object's centre, plus a matched push on the type layer at half the amount so the parallax reads as depth.

**Use when:** Before a reveal or a number.

**Avoid when:** When the push would move the caption out of the safe margin.

### `cam-parallax-truck` — Layered parallax truck

*workhorse · calm · camera · evidence 1 · continuous, 0.8–1.5 px/f*

Background, pose and type move at different rates. The depth comes from speed, not from blur or shadow.

**How:** Offset each layer by `k` px/f with k = 0.35 / 1.0 / 1.8 for bg / presenter / type, each layer padded 8% so nothing pops at the edges. Works in both engines with a translate.

**Use when:** A quiet explanation beat that still has to breathe.

**Avoid when:** Over a busy paper texture — the layers stop separating.

### `cam-pull-lands-event` — Pull-back that lands an event

*workhorse · calm · camera · evidence 2 · 18 f pull, event on the last 2 f*

The camera pulls out and the thing it reveals lands exactly on the last frame of the move — the move causes the event.

**How:** `z: 1.4 → 1.0` with `e_out` over 18 f, and put the word/object arrival on the final 2 f, with the SFX on that frame.

**Use when:** An end-of-sentence payoff.

**Avoid when:** If the reveal is larger than the frame — it will pop.

### `cam-crane-push` — Crane down with a delayed push

*accent · calm · camera · evidence 1 · 24 f crane, push offset 8 f*

A vertical crane (the format's own axis) with the push starting 6–8 f later, so two moves read as one gesture.

**How:** `ty: +40 → 0` on `e_io` over 24 f; the push `z: 1 → 1.1` starts 8 f in on the same curve family. In 9:16 the vertical axis is the one with the most room, so this is the house crane.

**Use when:** Scene openings between two VO sentences.

**Avoid when:** Two cranes back to back.

### `cam-hero-push-with-turn` — Hero push with a 3D turn

*signature · high · depth · evidence 1 · 1.0–1.3 s*

The camera pushes while the object turns — the one move that makes the 3D layer worth having.

**How:** `space3d.camera(dist, yaw, pitch)` with yaw sweeping −35° → +35° over 30–40 f while `dist` drops 12%; keep `sorted_faces` + `shade` on, back-face cull on `dot(n, cam.pos − face_centre) ≤ 0`.

**Use when:** The single 3D hero moment of the reel.

**Avoid when:** Yaw beyond ±80° (the cull breaks) or more than one per film.

## Pacing

### `ps-beat-quantized-chunks` — Phrase chunks on the grid

*workhorse · medium · grid · evidence 2 · hero events within ±1 f of a step; everything within ±40 ms*

Every picture event lands on a grid step, and the VO's phrases are cut into chunks that map onto bars — so the edit and the tempo are the same object.

**How:** `beat.grid(bpm)` gives the steps; `vo_length.py --bpm` snaps the scene bounds onto them first, then place events at `on_grid(bpm, bar, step)`. A cut that drifts 110 ms off the grid reads as layered, not composed.

**Use when:** Always — this is the spine the other moves hang from.

**Avoid when:** Never; if the VO has no tempo, pick 100 BPM and snap within 0.12 s.

### `ps-breath-envelope` — Breath envelope per card

*workhorse · medium · timeline · evidence 7 · burst 0.3–0.5 s, plateau 1–3 s, exit 0.27 s*

Each card opens on a burst, decays into a reading plateau, and hands its energy to the next card — a sawtooth, not a flat line.

**How:** Per scene: the first 20–25% of the frames carry the entrance (`prog` on an `e_out` curve), the rest is a cruise at 1.5–3 px/f, and the last 8–10 f accelerate into the cut. Take the scene's own bounds from `plan/beats.json`, and its length in beats from `beat.bar_seconds`.

**Use when:** Every scene longer than 1.2 s.

**Avoid when:** Very short punctuation scenes — they are all burst.

### `ps-luma-act-map` — Light and dark as chapters

*workhorse · any · layout · evidence 5 · per act (2–4 per reel)*

The reel's acts are separated by the stage's luminance, not by a label: paper act, ink act, paper act. It gives structure with zero on-screen furniture.

**How:** Assign `THEME` per act from the VO's own structure (question, proof, close). The light act is `drawPaper` with `paperTile`, the dark one the paper inverse; flip on a scene bound with `tr-polarity-flip-cut` and keep the accent's meaning constant across the flip.

**Use when:** Reels longer than ~25 s.

**Avoid when:** Alternating every scene — that is a strobe, not a structure.

### `ps-machine-grid-human-gaps` — Machine on the grid, hands off it

*workhorse · medium · grid · evidence 3 · grid ±0 f, human layer ±80 ms*

The geometric layer is rigidly quantised; the presenter and the hand-made props are deliberately not. The contrast is the personality.

**How:** Grid, HUD and type land on `beat` steps to the frame; the pose bobs/sways on `presenter.bob` and `presenter.sway` with a phase offset, and the paper texture is fixed to the world, not to the beat.

**Use when:** Any reel where Medo is on screen — that is all of them.

**Avoid when:** Nothing. Do not quantise the presenter.

## Layout

### `lc-negative-space-caption` — Caption in the subject's negative space

*workhorse · calm · layout · evidence 1 · as long as the VO phrase*

The caption lives in the part of the frame the pose leaves empty, so the presenter and the type never fight.

**How:** `presenter.draw(..., x=0.62)` puts the pose right; the caption block sits left of its bounding box at 58 px Cairo, on the 40 px margin. Mirror it (x=0.38) on the next scene to keep the frame from settling into one template.

**Use when:** Every sentence that runs while Medo is on screen.

**Avoid when:** The pose is centred and large — then use `lc-one-centred-subject` instead.

### `lc-one-centred-subject` — One huge centred subject

*workhorse · any · layout · evidence 2 · one scene*

Exactly one thing in the middle of the frame, at 40–70% of its height, with everything else empty paper.

**How:** Choose the object or the pose, place it on the optical centre (y ≈ 0.46 H, not the geometric centre), and delete every other element. The caption, if any, goes above or below on the margin, never both.

**Use when:** The claim, the number, the turn.

**Avoid when:** Two scenes in a row — the film stops moving.

### `lc-gap-open-insert` — Words part for an inserted object

*workhorse · medium · layout · evidence 5 · 12 f open, 14 f insert, 12 f close*

A line of type splits at its centre word, the object rises through the gap, and the line closes again — the insertion is the transition.

**How:** Measure the line, split it into two sprites, offset them apart by `gap = 0.25 * wordWidth * e_io(p)` over 12 f, run the object through on the vertical axis, close over 12 f.

**Use when:** A demonstration that needs to interrupt a sentence.

**Avoid when:** A line wider than the safe area once split.

## Depth

### `d3-extruded-slab-orbit` — Object on a thick extruded slab

*workhorse · medium · depth · evidence 1 · orbit 25–35 f, ±30°*

A flat thing (a card, a word plate) gets real thickness and a slow orbit, so it casts its own edge shadow in-palette.

**How:** `space3d.prism(poly2d, depth)` with depth 6–10% of width, cap role `paper`, side role `gray_2`, plus a 2 px hairline in `ink` on the front cap and the floor shadow as a squashed `ink_shadow` ellipse.

**Use when:** Turning a flat prop into the film's object.

**Avoid when:** Depth above 12% — it reads as a crate.

### `d3-coin-edge-to-face` — Edge-on sliver snaps face-on

*accent · medium · depth · evidence 2 · 10 f to face-on, 20 f settle*

The object starts as a 1-pixel-thin sliver seen edge-on, then rotates to face the camera in 10 f — a reveal with no fade anywhere.

**How:** `yaw = 90° → 8°` with front-loaded easing (35% of the rotation in the first frame, blurred: `blur_steps`), `shade` ramping as the normal turns toward the light.

**Use when:** Revealing the key word-plate or the closing statement.

**Avoid when:** Twice in one act.

### `d3-flip-face-swap` — 3D flip that swaps the state

*workhorse · medium · depth · evidence 2 · 10 f flip, no overshoot*

A 180° flip hides the swap: the back face is already the new word/picture when it lands.

**How:** Rotate the plate about y with `space3d`, cull the back face, and swap the texture at 90°; 2–3 f of `blur_steps` at the fastest frame. The flip is 10 f and never bounces.

**Use when:** A before/after pair, or two opposite words.

**Avoid when:** Any overshoot or spring on the landing.

### `d3-spotlit-tilted-object` — Tilted object on a spotlit ground

*workhorse · calm · depth · evidence 2 · static hold with the camera creep*

The ground is a pool of light and everything else is darkness; the object sits tilted inside it, lit from one side.

**How:** `shade(color, normal, light=[0.35,0.75,0.55])` with ambient 0.45 gives the ramp with zero gradient code; the pool is a hard-edged `paper` ellipse under the object, and the rest of the stage is `ink`.

**Use when:** A quiet beat that still needs weight.

**Avoid when:** Over the light theme — the pool has nothing to contrast against.

## Finish

### `tx-speed-gated-motion-blur` — Speed-gated motion blur

*workhorse · any · blur · evidence 6 · per frame, from the real velocity*

Blur appears only above ~20–40 px/f and only on the fast frames; everything settled is pin-sharp. It is physics, not a filter.

**How:** `velocity(t)` → if `speed > 20`: `blur_steps(vx, vy, n=6)` (P) or `drawBlurred` (K) with 6–16 px of smear; below that draw crisp. Never blur a whole scene or a still.

**Use when:** Slams, whips, flips, scale-throughs.

**Avoid when:** Slow type or a delivered still — blur there reads as a cheap filter.

### `tx-paper-grain-and-edges` — Paper grain and hairline edges

*workhorse · any · finish · evidence 3 · static texture, rebuilt per frame with a frame-keyed seed*

The texture that sells the material: frame-keyed paper grain, hairlines on the objects, and one key shadow — no vignette bloom, no gradient overlays.

**How:** K: `paperTile(seed)` + `drawPaper`; P: the existing `make_bg` grid + grain. Hairline = 2 px `ink` at 20–35% alpha, shadow = `ink_shadow` at 18% offset 14 px with a 36 px blur, both from `kit.withShadow`.

**Use when:** Always, both engines — it is what makes the palette look printed.

**Avoid when:** Never animate the grain; a crawling texture reads as noise.

## Sound

### `ps-silence-first` — Silence as the default bed

*signature · calm · sound · evidence 4 · hole 12–15 f before the hero cut*

There is no music under the voice. The soundtrack is the VO plus hits that are caused by something on screen — and one deliberate hole before the biggest moment.

**How:** `sfx.py` events are keyed to picture events (a cut, a landing, a flip), never to a bar counter alone. Before the key claim, drop the sub for 12–15 f and release it on the cut. Target −14.5 ± 0.3 LUFS integrated, TP ≤ −1.5 dBTP after the mux.

**Use when:** Always — the voice is the score.

**Avoid when:** Medo explicitly asks for a music bed.

### `sn-hit-on-visible-event` — Every hit is caused by something you can see

*workhorse · any · sound · evidence 5 · cue frame = landing frame (±0 f)*

An SFX fires only on the frame where a visible thing lands. No ambient ticking, no filler whooshes, no sound for a cut nobody sees.

**How:** Drive `sfx.py` from the same event list the picture uses (`grid_cues` / the scene's event table), with the cue on the exact frame of the landing. One sound per event, and the kit is synthesized (`tools/sfx_kit.py`).

**Use when:** Every sound in the reel.

**Avoid when:** Never — an unattributed sound is the audio version of filler text.

## Typography

### `ty-masked-baseline-rise` — Masked baseline rise

*workhorse · calm · type · evidence 4 · 10–12 f per word, 8 f apart (30 fps)*

Each word rises out of its own clipped line box, darkening from grey to ink. Whole words only — the mask is per word, never per letter.

**How:** P: build a sprite per word with `lib.text_sprite`, paste through a clip box whose height grows with `e_out(p)`; colour lerps `gray_4 → ink` over the same p. K: `ctx.save(); ctx.beginPath(); ctx.rect(x, lineTop, w, lineH*e); ctx.clip(); drawWord(...)`. Words 8 f apart, 10–12 f each.

**Use when:** The default entrance for Arabic headlines — it respects shaping because the clip never cuts a letter.

**Avoid when:** On a word that must be readable in under 0.4 s (a hook word) — use the settle instead.

### `ty-inplace-light-up-on-beats` — In-place light-up on the beat

*workhorse · calm · grid · evidence 4 · 1 step per word at 100–120 BPM, ramp 4 f, recency 12–24 f*

The finished line is laid out first; words light from `gray_2` to ink on successive grid steps, so the type follows the tempo without moving.

**How:** Lay the whole line at final positions, then per word pick a step from `beat.grid(bpm)` (`on_grid`) and ramp colour over 4 f. The newest word may take `red` for 12–24 f then settle to ink — once per card, not per word.

**Use when:** Long Arabic lines where motion would fight readability.

**Avoid when:** More than 8 words visible — the line becomes a scan.

### `ty-recentre-line-build` — Re-centring line build

*workhorse · medium · type · evidence 6 · 24–38 f re-centre, words 6–9 f apart*

Words arrive right-to-left (Arabic reading order) and the line re-centres once per word on an expo-out, never per letter.

**How:** Compute the final line width once; after each word lands, tween the line origin to `0.5 - width/2` with `e_out` over 24–38 f. Keep the vertical baseline fixed so only x breathes.

**Use when:** A short claim that grows to most of the frame width.

**Avoid when:** RTL is on and the words contain punctuation-only tokens — group them with the previous word first.

### `ty-staggered-word-roll` — Staggered word roll

*workhorse · medium · type · evidence 4 · 5–6 f per word, 20 f settle*

The outgoing word rises and blurs out while the incoming word comes up from below — a vertical roller inside one line, 5–6 f per word.

**How:** Two sprites per slot: outgoing at `y - 20*e`, `blur_steps` 6 px, alpha out over 10 f; incoming from `y + 24` settling in 20 f. Drive the slot changes from `beat` steps so it never drifts.

**Use when:** A list of three to five short Arabic terms that share a grammar.

**Avoid when:** Words longer than ~10 characters — the roll outruns the eye.

### `ty-reading-order-exit` — Reading-order exit

*workhorse · any · type · evidence 3 · exit finished 2 f before the cut*

Text rarely fades on its own. It leaves on the cut, or word by word in reading order, each rising 10–20 px and gone in 2–3 f.

**How:** Trigger the exit 6–8 f before the scene bound from `plan/beats.json`, front to back (Arabic: right to left), with the background already accelerating out (`transition` velocity curve).

**Use when:** Every fragment that does not die with its whole scene.

**Avoid when:** A hero line — it goes with the cut instead, never a slow fade.

### `ty-oversize-blur-slide-in` — Oversize word with velocity blur

*signature · high · blur · evidence 3 · sharp within 0.33 s, readable by 0.5 s*

One word at 15–30% of frame height travels in fast with directional blur, then goes pin-sharp within 10 f and is legible by 0.5 s.

**How:** Speed from the timeline (`velocity`), smear with `blur_steps(vx, vy)` (P) / `drawBlurred` (K), then draw the crisp pass once the speed drops under ~12 px/f. Blur lives only on the fast frames.

**Use when:** A two-word punchline in the middle act.

**Avoid when:** On a word the VO is also saying slowly — the two rhythms fight.

### `ty-scaled-echo-extrusion` — Scaled echo extrusion

*accent · medium · type · evidence 2 · static, revealed with the word (0.4 s)*

A word is repeated behind itself at stepped scales and descending opacity, reading as depth without a gradient or a glow.

**How:** Draw the sprite 4–7 times at `scale = 1 + i*0.06`, alpha `0.30 * (1 - i/n)`, offset 2–4 px per step, in `ink_shadow`; the front copy is full ink. Cheap, flat, and on-palette.

**Use when:** The one word that should feel monumental.

**Avoid when:** Small type, or over a textured background — the echoes turn to mush.

### `ty-vertical-word-stack` — Vertical word stack

*workhorse · medium · layout · evidence 1 · 6–8 f per line at 100 BPM*

Words stack down the 9:16 frame like a column, one per line, each landing on its own step — it turns the vertical format into an advantage.

**How:** One word per line at 12–16% of frame height, line pitch 1.15×, each arriving 6–8 f after the last on `e_out`, stacked from the top safe line downward; measure every word with `lib.text_sprite` first so a long word cannot overflow the 40 px margin, and give the last line the accent.

**Use when:** Three to five short terms, or a list that must fill the tall frame.

**Avoid when:** Words longer than the frame width at that size — check with the measured sprite width first.

### `ty-scramble-decode-latin-only` — Scramble decode (Latin readouts only)

*accent · medium · type · evidence 3 · 12–18 f, always shorter than the word it decorates*

A mono readout resolves from random glyphs, one character at a time. It is a Latin/mono device: Arabic is banned from it.

**How:** For HUD numbers and mono labels only (`IBM Plex Mono`), seed a `rng(seed)` and reveal left to right in 12–18 f. Arabic never uses it — per-letter reveal breaks shaping and the studio rules.

**Use when:** A counter, a timestamp, a version tag.

**Avoid when:** Any Arabic word, any word the viewer must read.

## Transition

### `tr-velocity-handoff-cut` — Velocity handoff cut

*workhorse · any · transition · evidence 9 · exit accel 10–18 f, decay τ ≈ 12 f*

The outgoing shot accelerates over its last 0.3–0.6 s and the next shot starts at exactly that speed, so the cut is felt as one move.

**How:** Before a bound: ease in to the exit (`x = e_in(p)`), peak 25–45 px/f at 1080-wide, and start the next scene with the same velocity decaying (`*0.92` per frame, τ ≈ 12 f at 30 fps). Keep the camera vector identical across the cut.

**Use when:** The default cut — it is the highest-evidence move in the library.

**Avoid when:** Between two static cards; with no speed to hand over it just looks like a jolt.

### `tr-scale-through-cut` — Scale-through cut

*signature · high · transition · evidence 6 · 14–18 f each way at 30 fps*

A shape (a word, a pill, the pose's silhouette) grows past the frame, and the next shot is revealed inside the same shape at the same scale rate.

**How:** Animate a mask rect/rounded-rect from 0.2× to 3× with `e_in` over 14–18 f, swap the plate at the peak, then continue outward from 3× to rest. `transition.layer()` masks already support this.

**Use when:** Act changes, or when a word becomes a container.

**Avoid when:** Twice in a row — it reads as a template.

### `tr-polarity-flip-cut` — Polarity flip cut

*accent · high · transition · evidence 6 · instant, on the scene bound*

Paper becomes ink (or the reverse) on the frame of the cut, with type and pose re-coloured instantly. No dissolve, no fade.

**How:** Flip the `THEME` flag on the cut frame and swap the two role colours (`paper ↔ ink`, `ink_shadow ↔ gray_1`); the pose sprite is re-tinted by its alpha mask, and the SFX hit lands on the same frame. It is a hard cut that changes world.

**Use when:** Acts that must feel like chapters.

**Avoid when:** More than twice — the film starts to strobe.

### `tr-shape-match-cut` — Shape match cut

*workhorse · medium · transition · evidence 4 · the match holds for 2–4 f around the cut*

Something in shot A (a circle, a bar, the mouth of a cup) is in the same place, size and colour as something in shot B, so the eye carries the object across.

**How:** Choose the match object once per film (the dot, the bar, the ring) and reuse it as the carrier — `lc-one-centred-subject` and `tr-dot-relay` both depend on it. Match centre within 6 px and radius within 4%.

**Use when:** When the film has a story device (it should).

**Avoid when:** Two diagonal compositions — the eye has no anchor to match.

### `tr-dot-relay` — Dot relay into the next scene

*signature · medium · transition · evidence 3 · 10 f collapse, 12–16 f growth*

Everything collapses to one dot, the dot travels, and the next scene grows out of it. The device the film owns is the thing that survives the cut.

**How:** Fade the composition to the accent dot over 8–10 f (`e_in`), carry the dot along a 40–70 px/f path across the cut, then scale the next scene from 0.05× around the dot in 12–16 f.

**Use when:** Mid-film, to link two unrelated pictures.

**Avoid when:** Collapsing to a dot that then means nothing — the relay must be the same object.

### `tr-subtract-reveal` — Reveal by subtraction

*workhorse · medium · transition · evidence 4 · 18–24 f, one direction only*

The frame is over-full, then everything that is not the point is removed in one move, leaving one object, one word, one pose.

**How:** Start with 3–5 layered props (`lc-one-centred-subject` inverse), then run a single scale-and-delete pass over 18–24 f in one direction, keeping the hero element exactly in place.

**Use when:** The moment the film makes its single point.

**Avoid when:** As a habit — it costs a whole scene to earn.

## Camera

### `cam-living-hold-creep` — Living hold creep

*workhorse · calm · camera · evidence 5 · continuous, one direction change per 6–9 s*

Nothing is ever locked. A held shot creeps 1.5–3 px/f with one direction change, so the frame is alive while the eye reads.

**How:** `z = 1 + 0.02*e_io(p)` plus `tx = 6*sin(2πt/T)` with T = 6–9 s, under any readable text. Cap the speed at 3 px/f — faster and the type stops being sharp.

**Use when:** Every shot longer than 1 s.

**Avoid when:** Nowhere — a locked camera is the tell that the sheet is generated.

### `cam-punch-in-insert` — Punch-in insert

*workhorse · medium · camera · evidence 5 · 6–8 f punch, settle 12 f*

At the cut, the same plate punches in 1.25–1.6× and lands a beat later — the cheapest way to make one scene feel like two.

**How:** Because Medo ships `full` and `bust` framings of the same pose (`assets/poses/poses.json`), cut from `explain` to `close-explain` and add 1.15–1.3× scale over 6 f so the face lands at the same size. Pure crop, no new art.

**Use when:** Emphasis on a single sentence, inside one VO scene.

**Avoid when:** More than once per scene — it stops meaning 'listen'.

### `cam-isolating-push` — Isolating push

*workhorse · medium · camera · evidence 3 · 0.7–1.0 s push*

A slow push toward the one object that matters while the rest of the frame drifts out of the safe area.

**How:** `z: 1 → 1.18` over 20–30 f with `e_io`, target = the object's centre, plus a matched push on the type layer at half the amount so the parallax reads as depth.

**Use when:** Before a reveal or a number.

**Avoid when:** When the push would move the caption out of the safe margin.

### `cam-parallax-truck` — Layered parallax truck

*workhorse · calm · camera · evidence 1 · continuous, 0.8–1.5 px/f*

Background, pose and type move at different rates. The depth comes from speed, not from blur or shadow.

**How:** Offset each layer by `k` px/f with k = 0.35 / 1.0 / 1.8 for bg / presenter / type, each layer padded 8% so nothing pops at the edges. Works in both engines with a translate.

**Use when:** A quiet explanation beat that still has to breathe.

**Avoid when:** Over a busy paper texture — the layers stop separating.

### `cam-pull-lands-event` — Pull-back that lands an event

*workhorse · calm · camera · evidence 2 · 18 f pull, event on the last 2 f*

The camera pulls out and the thing it reveals lands exactly on the last frame of the move — the move causes the event.

**How:** `z: 1.4 → 1.0` with `e_out` over 18 f, and put the word/object arrival on the final 2 f, with the SFX on that frame.

**Use when:** An end-of-sentence payoff.

**Avoid when:** If the reveal is larger than the frame — it will pop.

### `cam-crane-push` — Crane down with a delayed push

*accent · calm · camera · evidence 1 · 24 f crane, push offset 8 f*

A vertical crane (the format's own axis) with the push starting 6–8 f later, so two moves read as one gesture.

**How:** `ty: +40 → 0` on `e_io` over 24 f; the push `z: 1 → 1.1` starts 8 f in on the same curve family. In 9:16 the vertical axis is the one with the most room, so this is the house crane.

**Use when:** Scene openings between two VO sentences.

**Avoid when:** Two cranes back to back.

### `cam-hero-push-with-turn` — Hero push with a 3D turn

*signature · high · depth · evidence 1 · 1.0–1.3 s*

The camera pushes while the object turns — the one move that makes the 3D layer worth having.

**How:** `space3d.camera(dist, yaw, pitch)` with yaw sweeping −35° → +35° over 30–40 f while `dist` drops 12%; keep `sorted_faces` + `shade` on, back-face cull on `dot(n, cam.pos − face_centre) ≤ 0`.

**Use when:** The single 3D hero moment of the reel.

**Avoid when:** Yaw beyond ±80° (the cull breaks) or more than one per film.
