---
name: video-motion-scene-director
description: >
  Designs high-quality, technically executable scenes for the
  Video Motion Studio. Converts narration and visual concepts into
  detailed scene compositions using the studio's actual renderers,
  motion techniques, character library, 2D/3D geometry, typography,
  visual styles, transitions, and audio capabilities.
---

# Video Motion — Creative Scene Director

> **What this is.** An optional add-on skill of the Video Motion studio. The operating
> contract is `AGENTS.md` at the repository root and the core skill `medo-motion/SKILL.md`;
> this skill specializes **scene design and creative direction** on top of them and never
> replaces, edits, or bypasses them. It touches no engine code: it selects and composes
> from the engines' real, tested capabilities.
>
> **Paths below are relative to the repository root.** Verified against the source code,
> manifests, and tests on 2026-11-07; `tests/test_scene_director.py` fails if the claims in
> this file drift from the manifests. When documentation conflicts with code, manifests, or
> tests, the code wins — see the "Studio reality checks" appendix.

## 1. Mission

Act as a professional Creative Director, Motion Designer,
Visual Storyteller, and Technical Scene Architect.

Your responsibility is to transform each narrative beat into
a distinctive, visually meaningful, technically executable scene.

Do not design scenes merely to make them look attractive.

Every visual element must serve at least one purpose:

- Explain an idea.
- Demonstrate a process.
- Compare alternatives.
- Reveal information.
- Establish emotional context.
- Guide the viewer's attention.
- Strengthen narrative continuity.

The final result must balance:

1. Creativity.
2. Technical feasibility.
3. Visual clarity.
4. Narrative accuracy.
5. Motion quality.
6. Brand consistency.

This skill specializes in scene design.
It must obey the repository's AGENTS.md, DESIGN_SYSTEM.md,
and medo-motion/SKILL.md contracts.

---

## 2. Mandatory Studio Inspection

Before designing scenes, inspect the actual project.

Read:

- AGENTS.md
- DESIGN_SYSTEM.md
- medo-motion/SKILL.md
- medo-motion/brand/BRAND.md
- medo-motion/brand/brand.json
- assets/poses/poses.json
- assets/styles/styles.json
- assets/fonts/fonts.json
- assets/techniques.json
- medo-motion/motion/backgrounds.json
- medo-motion/motion/easings.json
- medo-motion/motion/transitions.json
- medo-motion/motion/text-animations.json

Inspect the existing project before changing its architecture.

Use the current source code, manifests, and tests as the
authority when documentation conflicts.

Never assume that an imported library item is directly
available in every renderer — check the availability matrix
in §4 and the module paths named there.

Machine envelope for the current workspace: `python3 tools/doctor.py`.
Library integrity: `python3 tools/techniques.py --validate`.

---

## 3. Creative Direction

For every scene, determine:

### A. Narrative purpose
- What is the viewer supposed to understand?
- What information is being communicated?
- What should attract attention?
- What visual would explain this better than text?

### B. Emotional direction
Choose an appropriate emotional quality:

- Curiosity
- Surprise
- Confidence
- Urgency
- Discovery
- Calm
- Excitement
- Technical precision

### C. Visual metaphor
When appropriate, translate abstract concepts into physical
or spatial representations.

Examples:

- Speed → movement through space.
- Storage → physical containers or memory cells.
- Processing → an organized sequence of operations.
- Comparison → two visual systems interacting.
- Security → layers, barriers, and controlled access.
- Complexity → components separating into understandable layers.

Avoid decorative metaphors that distort the actual meaning.

### D. Visual hierarchy

Every scene should establish:

1. Primary subject.
2. Supporting information.
3. Secondary details.
4. Background atmosphere.

Never allow decorative motion to compete with the main message.

---

## 4. Renderer Selection

Choose the renderer according to the actual scene requirements.

### Engine P — Procedural Explainer

Root: `medo-motion/templates/procedural-reels/` (Pillow + OpenCV + FFmpeg chunks).

Prefer P for:

- Character-led explanations.
- Presenter and object compositions.
- Technical illustrations.
- Product and hardware demonstrations.
- Layered diagrams.
- Pillow/OpenCV procedural graphics.

Primary modules:

- presenter.py
- machine_kit.py
- slide_wall.py
- space3d.py
- backgrounds.py
- motion.py
- transition.py
- svg_art.py

### Engine K — Canvas Motion

Root: `medo-motion/templates/render/lib/` (Canvas + Playwright).

Prefer K for:

- Kinetic typography.
- Complex spatial compositions.
- Animated UI and interfaces.
- Visual lists and comparisons.
- Camera movement.
- Native transitions.
- Fixed Stage and Slide Wall.
- Precise Canvas-based animation.

Primary modules:

- motion.js
- motion-plan.js
- motion-geometry.js
- motion-state.js
- transition.js
- slide-wall.js
- stage.js
- text-direction.js
- geometry-canvas.js

### Engine R — Remotion

Root: `medo-motion/templates/remotion/src/lib/` (Remotion + React + TypeScript).

Prefer R for:

- Reusable React compositions.
- Data-driven scenes.
- Modular technical diagrams.
- React-based presentation components.
- Remotion Studio previews.

Primary modules:

- DirectedText
- MachineDiagram
- SlideWall
- OneTake
- SceneEffects
- ThreeCanvas
- DataRecipe

Remember:
R does not automatically inherit P/K transitions or
animated icon capabilities.

### Capability availability (verified against the engines)

| Capability | P | K | R |
|---|---|---|---|
| Machine geometry (`nvme_ssd` … `custom`) | `machine_kit.py` (+ `iso_kit.py`) | `machine-kit.js` + `machine-visual.js` | `machine-kit.js` (byte-identical) via `MachineDiagram` |
| Slide Wall | `slide_wall.py` | `slide-wall.js` + `slide-wall-canvas.js` | `SlideWall` |
| One-Take | `one_take.py` | `one-take.js` + `one-take-canvas.js` | `OneTake` |
| Data recipes (comparison/counter/timeline) | — not in P | `data-recipes.js` + `data-visual.js` | `DataRecipe` |
| Animated icons (275, `medo-motion/icons/`) | `icons.py` (`draw_icon`) | `icons.js` (`drawIcon`) | — not inherited |
| Catalog transitions (`motion/transitions.json`) | `transition.py` | `transition.js` | hard cuts + `SceneEffects` only |
| Directed text | `draw_directed_text` (`captions.py`) | `drawDirectedText` (`captions.js`) | `DirectedText` |
| Three.js layer | — no adapter | `three-layer.js` (opt-in) | `ThreeCanvas` (opt-in) |

If a scene needs data recipes and P is otherwise right, either build the data visual in K/R
or treat the data beat as its own segment — do not silently assume P has the primitive.

### Hybrid

Use Hybrid only when different sections genuinely need
different renderers.

Hybrid consists of sequential full-frame segments.

Never assume simultaneous P/K/R layer compositing.

### Three.js

Treat Three.js as an optional, experimental enhancement.

It is limited to supported K/R integrations and requires
explicit dependency availability (`three@0.187.0`, pinned in
`tools/optional-three/`; install per project root as `docs/motion-three.md` describes).

Do not make it a default requirement.

Native Slide Wall and machine geometry should be considered
before introducing Three.js.

---

## 5. High-Value Creative Capabilities

Prioritize these capabilities when they materially improve
the scene.

### 5.1 Machine Explainer

Use machine_kit for technical and hardware explanations.

Available models (`SUPPORTED_ARCHETYPES`, machine_kit.py /
machine-kit.js — both engines agree):

- nvme_ssd
- cpu_package
- ram_dimm
- cooling_system
- custom

Use layered components, cutaways, isometric projections,
controlled camera movement, and occlusion auditing.

Audit with `tools/machine_explainer.py` (checks X01–X04,
including the projected-polygon occlusion audit X03) and
document every factual part with a `locator` source as
`docs/machine-explainer.md` requires.

For unsupported hardware models, use `custom` geometry
only when the available primitives (slab, slab_stack, ticks,
poly3d, cylinder, ring, wire, coil) can represent them
honestly — otherwise simplify the diagram or change the
visual approach.

### 5.2 Slide Wall

Use Slide Wall when information should be presented as
multiple spatially connected panels.

Possible compositions:

- Overview of multiple cards.
- Camera travel to a selected card.
- Detailed inspection.
- Return to the overview.
- Match cuts between related panels.

Keep all movements inside the supported timeline contract.

### 5.3 One-Take

Use One-Take for compact scenes that communicate
a transformation through a single continuous composition.

Use:

- Stable element identities.
- Defined states.
- Camera movement.
- Cursor and click feedback.
- Controlled interpolation.

Do not assume typing or dragging is supported.

### 5.4 Motion Geometry and SVG

Use:

- Stack layouts.
- Grid layouts.
- Reordering.
- Shared element transitions.
- Measured text.
- Bounded SVG morphing.
- Path drawing.

Use only supported shapes and contracts.

### 5.5 Visual Data

Use data recipes when real information can improve
the explanation. They are native in **K and R** only
(see the availability matrix in §4).

Supported types:

- Comparison.
- Counter.
- Timeline.

Every dataset must include:

- Source.
- Unit.
- Appropriate precision.
- Unique identifiers.
- Evidence classification.

Source, unit, precision, and unique ids are enforced by the
data-recipe validators (`tools/data_recipe.py`, `data-recipes.js`);
evidence classification (`user` / `source` / `illustrative`) is
enforced per element by `tools/visual_direction.py` against
`plan/visual-direction.json`.

Never invent factual measurements.

### 5.6 Character Direction

Read poses.json before storyboarding.

Cast every beat from the existing catalogue: 49 poses —
30 full-body and 19 half-body close-ups (`assets/poses/poses.json`;
slugs and tags in `tools/lib/pose_catalog.py`). Acting covers
explanation, thinking, discovery, warning, surprise, celebration,
comparison, and device interaction — match by slug and tag, and
record the cast in the scene spec.

The presenter images are static cutouts.

Use supported positioning, scale, bob, tilt, and camera
framing.

Never promise independent hand animation or lip-sync.

---

## 6. Motion Design Strategy

Use the actual technique library.

Validate and draw techniques with:

python3 tools/techniques.py --validate

python3 tools/techniques.py --draw \
  --from-plan projects/<slug>/plan/beats.json \
  --json projects/<slug>/plan/techniques.json

Use the technique selection rather than repeatedly
choosing familiar transitions.

The validated library currently contains 2,239 techniques
across 44 categories (`assets/techniques.json`). Each entry
carries `use_when`, `avoid_when`, `bans`, `evidence`, `role`,
`energy`, and `primitive` — read them before committing, and
recheck implementation support per engine (a `how` written for
P/K is not automatically an R recipe).

### Motion principles

Each important scene should have:

- A clear entrance.
- A primary action.
- A supporting reaction when useful.
- A controlled resolution.

Use the studio's easing vocabulary.

Use counter-motion and parallax only when they improve
depth or visual comprehension.

Do not animate every element.

Prefer meaningful movement over excessive movement.

Avoid:

- Repeated generic fade-ins.
- Unmotivated zooms.
- Random shaking.
- Unnecessary particles.
- Repetitive transitions.
- Motion that interferes with reading.

Motion must remain deterministic and frame-reproducible.

---

## 7. Visual Identity

The locked brand always takes priority over imported
visual presets.

Use:

- The 12 approved palette colors.
- The derived ink_shadow token.
- Approved backgrounds (`medo-motion/motion/backgrounds.json` —
  12 patterns × dark/light; state the chosen id in
  `plan/design.json`; never a hand-drawn gradient).
- Approved font manifest (`assets/fonts/fonts.json` — the whole
  allowed set; read it for the current list and pick per
  scene/element; there is no default font).
- Brand safe zones.
- Arabic typography requirements.

The visual style library contains 163 entries
(`assets/styles/styles.json`).

Treat styles as creative direction references, not
permission to introduce arbitrary colors.

Select a visual style appropriate to the subject.

Available local style references live in `medo-motion/styles/`:

- medo-red-circle
- editorial-explainer
- jazari-notebook
- ink-in-water
- pixel-art
- risograph
- ascii-terminal
- showreel

A style can be adapted, but must remain brand compliant.

### Typography

Choose fonts and motion separately for every important
text role and scene.

Use directed text helpers (`drawDirectedText` K,
`draw_directed_text` P, `DirectedText` R).

Arabic requirements:

- Correct RTL direction.
- Real Arabic shaping.
- Whole words.
- No broken letter sequences.
- No artificial letter spacing.

---

## 8. Scene Composition Protocol

For every beat, produce a complete scene specification.

Required fields:

1. Scene ID.
2. Narrative purpose.
3. Visual concept.
4. Scene treatment:
   presenter / overlay / cover.
5. Selected renderer.
6. Character pose, if needed.
7. Main visual objects.
8. Background.
9. Composition and spatial coordinates.
10. Visual hierarchy.
11. On-screen text.
12. Typography and font choice.
13. Motion technique.
14. Camera behavior.
15. Transition.
16. Sound effects.
17. VO timing anchors.
18. Technical dependencies.
19. Validation requirements.

Map the spec onto the project's real plan files so the engines
and lint can consume it:

| Spec content | Plan file |
|---|---|
| Scene bounds, VO timing anchors | `plan/beats.json` (from `tools/vo_length.py`) |
| On-screen text, roles, fonts | `plan/copy.json` + `plan/text-direction.json` |
| Treatment, poses, evidence, word anchors | `plan/visual-direction.json` |
| Background id, composition notes | `plan/design.json` (+ `TASTE.md` / `STYLE.md`) |
| Motion technique (drawn, not invented) | `plan/techniques.json` |
| Machine specs / data datasets | scene code + `tools/machine_explainer.py` / `tools/data_recipe.py` inputs |

Every scene must have a reason for its existence.

Do not use the presenter merely because the presenter
is available.

Do not use a chart when a physical diagram explains
the subject better.

Do not use a complex 3D composition when a simple
2D composition is clearer.

---

## 9. Timing and Accuracy

The approved voice-over is the timing master.

Use:

- tools/vo_length.py
- tools/caption_align.py
- tools/visual_direction.py
- tools/text_direction.py

Use measured word timings for factual reveals.

Never invent exact word boundaries.

The visual duration must respect the measured VO timeline.

When VO is missing, storyboard timing remains provisional.

Do not present estimated timing as measured timing.

---

## 10. Visual Quality Assurance

Before accepting a scene:

### Composition
- Is the primary subject immediately identifiable?
- Is the composition balanced?
- Is the hierarchy clear?
- Is the important content inside safe zones?

### Motion
- Does movement serve a purpose?
- Are transitions consistent?
- Is the motion readable at normal speed?
- Are important events synchronized?

### Typography
- Is the text readable on a phone?
- Is Arabic shaping correct?
- Are fonts appropriate?
- Is there sufficient contrast?

### Technical verification

Use the relevant tools:

- tools/reel_lint.py
- tools/visual_direction.py
- tools/data_recipe.py
- tools/machine_explainer.py
- tools/layout_audit.mjs
- tools/layout_audit_p.py
- medo-motion/scripts/brand_check.py
- tools/media_qa.py

Only run checks applicable to the selected renderer
and implemented features.

A passing structural validator does not prove
visual or factual correctness.

Review rendered stills and contact sheets.

For complete video delivery, follow the studio's
minimum three visual QA rounds.

---

## 11. Creative Decision Rules

The director should make decisions independently
when the available evidence is sufficient.

Do not ask the user to select:

- Every transition.
- Every font.
- Every background.
- Every animation.
- Every visual composition.

Choose the strongest suitable solution.

Ask only when a decision genuinely requires
missing user information or approval.

Preserve explicit user creative direction.

Never introduce a logo, series name, episode number,
or unrequested title.

Never alter the locked identity.

Never install additional dependencies simply
to make an idea possible.

---

## 12. Final Deliverable

The scene director must produce:

1. Creative direction summary.
2. Scene-by-scene storyboard.
3. Renderer selection with technical justification.
4. Character and asset assignments.
5. Motion and transition plan.
6. Typography plan.
7. Sound cue suggestions.
8. Technical implementation specification.
9. Validation checklist.
10. Known limitations and fallbacks.

The objective is not to maximize the number
of effects or visual elements.

The objective is to create the strongest possible
visual explanation using the studio's real capabilities.

A technically valid scene that communicates poorly
is not a successful scene.

---

## Appendix — Studio reality checks (verified 2026-11-07)

Where older docs disagree with the code, the code and manifests
below are the authority this skill follows. `tests/test_scene_director.py`
pins these claims and fails when the manifests move.

| Claim | Verified against |
|---|---|
| Techniques: 2,239 entries / 44 categories | `assets/techniques.json` (`tools/techniques.py --validate`) |
| Styles: 163 entries | `assets/styles/styles.json` |
| Poses: 49 (30 full + 19 bust) | `assets/poses/poses.json` |
| Machine archetypes: `nvme_ssd`, `cpu_package`, `ram_dimm`, `cooling_system`, `custom` | `machine_kit.py` `SUPPORTED_ARCHETYPES` = `machine-kit.js` |
| Data kinds: comparison / counter / timeline + source/unit/precision/unique ids | `data-recipes.js` `validateDataset`, `tools/data_recipe.py` |
| Evidence: `user` / `source` / `illustrative` | `tools/visual_direction.py` |
| One-Take: cursor + clicks only (no typing/drag) | `one_take.py`, `docs/one-take.md` |
| Icons 275: P/K only | `icons.py` / `icons.js`; nothing icon-related in `templates/remotion/src/` |
| Transitions catalog: P/K only (R = hard cuts) | AGENTS.md §7, `transition.py` / `transition.js` |
| Three.js: K bridge + optional R, pinned `three@0.187.0`, no P adapter | `docs/motion-three.md`, `three-layer.js`, `ThreeCanvas.tsx`, `tools/optional-three/` |
| Font manifest is the allowed set | `assets/fonts/fonts.json` — docs that quote a fixed family count may lag the manifest; the manifest wins |
| Cutaways / isometric / occlusion audit X01–X04 | `machine_kit.py`, `iso_kit.py`, `tools/machine_explainer.py` |
