# Deterministic effect states

This first implementation slice adds frame-addressable state functions for three requested
effect families. They are pure functions of local time and explicit parameters; they do not
read clocks, retain state between frames, or use random-number APIs.

| Reference | API | Returned state |
|---|---|---|
| M-018 Light Sweep | light_sweep / lightSweep | normalized band center, width, angle and alpha |
| M-020 Whip Pan | whip_pan / whipPan | normalized camera offset, analytic velocity and bounded blur distance |
| M-026 Particle Dissolve | particle_dissolve / particleDissolve | seeded normalized particle positions, radii and per-particle alpha |

## Renderer contract

- Coordinates, widths, offsets and radii are normalized to the frame dimensions.
- The caller supplies scene-local seconds. Sampling the same time and parameters returns the
  same state, including after reverse or non-sequential seeks.
- Particle positions come from a small 32-bit integer hash. The seed and count are explicit;
  count is capped at 256 to keep accidental workloads bounded.
- Whip-pan velocity is the analytic derivative of the smoothstep offset. blur_distance is
  bounded by max_blur; a renderer may map it to its existing velocity-blur sampling.
- Light Sweep returns a band description, not a baked gradient or image asset. The renderer
  chooses the palette-safe highlight treatment.

## Current scope and limitation

These APIs establish matching P/K/R effect-state math and can be sampled at any frame. They
are not yet renderer integrations: no Pillow/Canvas/Remotion drawing or transition compositing
is added in this slice. In particular, Particle Dissolve still needs an image sampling and
compositing path in each renderer, and R still needs its catalog-transition adapter before
these effects can be selected as scene transitions. Do not describe these states alone as
finished visual effects.
