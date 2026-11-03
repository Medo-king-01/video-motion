# Craft — the measured rules, and how this studio enforces them

Everything here comes from the cinetic study (MIT, © 2026 Leonxlnx): thousands of frames of
top-tier launch films measured frame by frame. The numbers were then **re-scaled to this studio**
(1080×1920, 30 fps, Arabic type, presenter on paper) and trimmed to what we are allowed to do.
Nothing on this page is a target length — the reel is exactly as long as Medo's voice-over
(`docs/length.md`).

- Draw the moves: `python3 tools/techniques.py --draw --from-plan plan/beats.json`
- Check a plan: `python3 tools/reel_lint.py projects/<slug>` (`--strict`, `--scan-code`, `--json`)
- Library: `assets/techniques.json` → readable at [`techniques.md`](techniques.md)

Two tools, one idea: an agent should not choose the same four moves by hand, and a plan should not
be able to call itself finished before it has been measured.

---

## 1. What the measurements say

Converted to our frame rate (halve every 60 fps frame count) and our format.

| Measure | Measured median | What we default to |
|---|---|---|
| Median shot | 1.46 s (1.1–2.8 s) | 1.2–3.0 s; longer only when the picture changes inside the shot |
| Shortest shot | 0.67 s (0.27–1.27 s) | 0.27 s floor, and **no copy** under 0.45 s |
| Picture change | about every 0.7 s | about every 1 s — calm default |
| First visible change | 0.10 s | ≤ 0.43 s, always |
| First readable word | 0.40 s | ≈ 0.40 s |
| Longest near-still run | 1.1 s | **0.5 s max** (house ban on holds) |
| Entrance decay | ×0.92 / frame (τ ≈ 12 f) | same, at 30 fps |
| Exit acceleration | ×1.14 / frame over ~16 f | same, into every cut |
| Readable text speed | ~2 px/f (0–12.5) | 1.5–3 px/f |
| Peak camera push | 4.8–9.6 % scale per frame | 2–3 % per frame at 30 fps, blurred above 20 px/f |
| Words per card | 3–4 (1–7) | 2–3; ≤ 4 new, ≤ 8 visible |
| Dwell | 0.4 s per word (0.3–0.55) | 0.4 s/word, floor 0.5 s |
| Copy rate | 0.4–1.7 words/s | same |
| Copy coverage | — | ≤ 65 % of runtime, 1.5 s text-free in every 10 s |
| Motion blur trigger | 20–40 px/f | 20 px/f, 6–16 px of smear, fast frames only |
| Accent share | ~5 % of pixels | ≤ 6 %, one full-bleed beat per reel |
| Grid lock | hero cuts ±1 f; 13/18 within ±40 ms | every cut within 120 ms, hero events on the step |

**The house default is the calm end.** Where the measured range is wide we sit at its quiet edge:
fewer words, longer holds, fewer events, slower moves. A brief that asks for energy opts into
`--energy high` in the draw and `--pace crisp` in the lint (5 words per fragment, 10 visible, 80 %
coverage) — never into 60 fps churn, because our delivery is 30 fps and the studio bans the effects
that usually fill that gap.

## 2. Rules that conflict with the study, and who wins

The study describes films that sometimes used looks we do not allow, so its rules were re-stated in
a ban-safe form. Where the two disagree, **this studio wins**, and the reason is written down:

| The study says | We do | Why |
|---|---|---|
| Serif and italic type are banned | Amiri and Instrument Serif stay, as **roles** (quote, editorial) | Arabic has no italic tradition; the locked brand owns its type (`docs/fonts.md`) |
| A deliberate 1.1 s still can buy a slam | Stills ≤ **0.5 s** | house ban on holds; we buy the slam with a velocity hole instead |
| 60 fps, "author at the delivery rate" | 30 fps, 1080×1920 | delivery format; motion blur covers the gap, and `tx-speed-gated-motion-blur` is in the draw |
| Lengths per format (20–45 s…) | length = the VO | `docs/length.md`; no number in this repo may prescribe a duration |
| One accent hue from an allowed family | palette v2, 12 colours | `brand/brand.json`; `brand_check.py` fails the build otherwise |
| Product UI in motion | Medo in motion | there is no product UI in a talking reel; poses are the "footage" |

## 3. The lint rules

Twenty-three rules in four groups. `tools/reel_lint.py <project>` reads `plan/beats.json` (from `tools/vo_length.py`),
`plan/copy.json` and `plan/techniques.json` (from `tools/techniques.py`). `!!` is an error,
` ?` is a warning, and `--strict` makes warnings fail.

### Structure — `plan/beats.json`

| Code | Rule | Level |
|---|---|---|
| `S01` | A duration exists (the VO has been measured) and scenes are listed | error |
| `S02` | The timeline starts at 0, is monotonic, and ends exactly on the VO duration | error |
| `S03` | A scene under 0.27 s is punctuation only; under 0.45 s it can carry no words | warn |
| `S04` | A scene longer than 2.2 s must declare `events[]` — the picture changes inside the shot | warn |
| `S05` | Every cut lands within `--tol` (default 120 ms) of the tempo grid | warn |
| `S06` | Frame 0 is not an empty ground: something is already on screen at `t = 0` (a fragment starting at 0, or `events[0].t = 0`). Social players freeze frame 0 as the thumbnail, and a title that fades in from nothing means the poster is a blank background | warn |
| `U01` | A scene flagged `"ui": true` must declare its interaction (`events[]`) and run ≥ 1.2 s | warn |

### Copy — `plan/copy.json`

```json
{"pace": "calm", "bpm": 100,
 "copy": [{"scene": 1, "text": "النهاردة", "start": 0.4, "end": 1.5, "mode": "build"}]}
```

| Code | Rule | Level |
|---|---|---|
| `C00` | No copy plan at all (nothing checks the screen) | warn |
| `C01` | ≤ 4 words per fragment (calm) / 5 (crisp) | error |
| `C02` | ≤ 8 words visible at once (5 when a line replaces itself) | error |
| `C03` | Dwell ≥ 0.4 s per word, floor 0.5 s (error at 75 % of that, warn below) | error |
| `C04` | 0.4–1.7 on-screen words per second over the whole reel | warn |
| `C05` | Copy covers ≤ 65 % of the runtime (80 % crisp) | warn |
| `C06` | ≥ 1.5 s of text-free picture inside every full 10 s window | warn |
| `C07` | No banned words (`introducing`, `lorem ipsum`, `نقدم لكم`, `اسم السلسلة`, `لوجو`) — skipped for a fragment marked `"approvedByUser": true`, because a name/title/episode the user asked for is his words, not the studio's default | error |
| `C08` | A sentence never arrives in one block (> 6 words ending in `. ! ؟ ?`) | error |
| `C09` | A fragment ends after it starts (`end > start`) | error |
| `C10` | Every fragment points at a scene that exists | error |
| `C11` | A fragment arrives within 120 ms of the grid | warn |

A fragment may also declare the ground it is drawn on and the colour itself:
`{"text": "…", "color": "salmon", "size": 76}` plus `"theme": "dark"|"light"` on its scene in
`plan/beats.json` (the same two words the backgrounds use). That is what `T06` measures.

### Moves — `plan/techniques.json`

| Code | Rule | Level |
|---|---|---|
| `M00` | No draw at all | warn |
| `M01` | Never three moves in a row from the same category | warn |
| `M02` | At most two signature moves | warn |

### Text direction — `plan/text-direction.json`

The agent chooses an explicit caption + on-screen text style **per scene** and explains why.
There is no default look and no random picker. Initialise the skeleton after the beats exist:
`python3 tools/text_direction.py projects/<slug> --init`, then fill every choice.

| Code | Rule | Level |
|---|---|---|
| `T00` | A text direction exists (the agent has decided the styles) | error |
| `T01` | Every scene has a valid `captionStyle`, a rationale, and valid `textStyles`/`textElements` | error |
| `T02` | Variety: not one identical caption style across the whole reel unless `motifReason` explains it | warn |
| `T03` | EVERY on-screen text fragment (title, keyword, number, CTA, label, UI…) has a known role and resolves to an explicit style | error |
| `T04` | Scene code draws text only through the directed helpers (`drawDirectedText` / `draw_directed_text` / `DirectedText`), never raw `fillText`/`text_sprite`/`txt` | error |
| `T05` | EVERY on-screen text fragment has an agent-chosen font from the manifest (family + weight), and Arabic text uses an Arabic-capable family | error |
| `T06` | A fragment that names a `color` clears WCAG against the ground it is actually drawn on: ≥ 4.5:1 for body text, ≥ 3:1 at or above `text_contrast.large_px` (76 px). Both ends of the scene's background ramp are tested, so a token that only survives the middle of a gradient fails. Pairs `brand.json → text_contrast.forbidden_on_theme` bans (red on dark, gray_4/salmon on light) fail regardless of size | error |

### Code scan — `--scan-code`

| Code | Rule | Level |
|---|---|---|
| `K01` | No `sparkle`, `confetti`, `particle`, `lensflare`, `rgbsplit`, `crossfade`, `shake` in the project's own scene files | warn |

Suppress a single finding with a comment on the same line: `shake_flash(t)  # lint: allow shake`.

## 3b. UI inserts — what we build, and what we refuse to fake

A talking reel still needs screens: a phone in Medo's hand, a list filling up, a number landing.
That is what the **ui_choreography**, **product_demo**, **data_and_numbers** and
**micro_interaction** families are for (17 of the 59 moves). They are drawn like any other move,
and they obey the same bans — so the rules that matter are:

- **The screen is ours.** Built from `kit.phone` / `kit.appWindow` / `kit.card` / `kit.checklist` /
  `kit.rolling` (K) and `art.laptop` / `art.desktop` / `art.follow_button` / `art.paper_spec` /
  `library sprites` (P). Never a screenshot, never a stock UI kit, never a framework-blue mock-up —
  a screen capture is someone else's pixels and someone else's brand.
- **Every value comes from the script.** A number, a label or a row that is not in Medo's VO or
  direction is filler, and filler is a ban (`fake-metrics`).
- **A UI scene is a shot, not a slide.** It needs an interaction (the tap, the insert, the tick) —
  `U01` warns when a scene is flagged `ui` and nothing changes in it, or when it is too short for the
  change to read.
- **Text inside a screen still obeys the copy rules.** ≥ 27 px equivalent (2.5 % of frame height) to
  be readable at all, ≤ 4 new words per fragment, and no sentence dumped on a mock screen.
- **One accent, one meaning.** The accent marks the thing that changed; a mock-up that uses the
  accent on every button and badge means nothing (the palette's 12 colours are the whole budget).
- **Depth without the banned looks**: dim (35 % ink overlay) and scale (0.92), never
  glassmorphism, glow or drop shadows above 18 % alpha.
- **The presenter stays the anchor.** A UI insert is a cut away from Medo, not a floating phone over
  a talking face: `pd-phone-in-hand` attaches the device to the pose, the other `pd-*` moves cut to a
  full screen shot and cut back on the beat.

## 4. The draw

`tools/techniques.py --draw` fills a plan in the format's order of need — hook, typography,
transition, camera, pacing, layout, depth, finish, sound — one technique per 3.5 s when calm and per
2.5 s otherwise (minimum 4, maximum the length of the order). Weights:

```
role      workhorse 3 · accent 2 · signature 1
proof     1 + evidence/4, capped at 3
energy    same 1.0 · "any" 0.7 · other 0.25 · calm never draws "high"
```

The seed is printed, so the plan is reproducible and belongs in `plan/techniques.json`. A draw is a
starting point, not a quota: build what the concept can carry, reroll a pick that fights it
(`--exclude <id>`, at most twice), and never add a move the draw did not give you — draw it with
`--category`.

**Who owns what.** The draw gives you the *move*; the brand gives you the *look*; the VO gives you
the *timing*. A technique that cannot be built inside the 12-colour palette, with whole-word Arabic
type, is not available — every entry in `assets/techniques.json` was rewritten against this studio's
own primitives, and `tests/test_techniques.py` fails if a recipe drifts back to React or GSAP.

## 5. The loop

1. VO → `tools/vo_length.py out/vo.wav --json plan/beats.json --bpm 100` (length + cuts).
2. Draw → `tools/techniques.py --draw --from-plan plan/beats.json --json plan/techniques.json`.
3. Copy → `plan/copy.json` (fragments, times, mode, role), following §3.
4. Text direction → `tools/text_direction.py projects/<slug> --init`, then the agent fills
   `captionStyle` / `textStyles` per scene with a rationale (no default style).
5. Lint → `tools/reel_lint.py projects/<slug> --scan-code`; fix errors, read warnings.
6. Render → `run_all.sh` (P) or `node src/render.js` (K).
7. Measure the render → loudness, peak, A/V duration (`docs/audio.md`), then `--check` again.

Steps 5 and 7 are gates: a reel that has not passed both has not been looked at, only rendered.

## Sources

- cinetic — measured craft study and technique library, MIT, © 2026 Leonxlnx:
  <https://github.com/Leonxlnx/cinetic>. Adapted, not vendored: no React, no Remotion, no npm at
  render time (see `assets/CREDITS.md`).
