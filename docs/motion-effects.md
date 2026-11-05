# Deterministic effect states

This implementation adds frame-addressable state functions for three requested effect
families. They are pure functions of local time and explicit parameters; they do not
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
  bounded by max_blur; current adapters map it to a bounded Gaussian blur approximation.
- Light Sweep renderer adapters use the state function and composite a soft diagonal highlight:
  - Engine P: `effects_render.draw_light_sweep(image, t, **options)` returns a new Pillow RGB/RGBA frame.
  - Engine K: `effects-render.drawLightSweep(ctx, t, width, height, options)` paints into a Canvas2D context.
  - Engine R: `LightSweep` from `lib/LightSweep.tsx` is an absolute overlay; place it after the content it should affect.
- Light Sweep adapters preserve arbitrary-time sampling. They are renderer helpers, not automatically
  injected into every scene; the scene/overlay caller must invoke or mount the adapter.
- Whip Pan renderer adapters apply the camera translation and bounded blur:
  - Engine P: `effects_render.draw_whip_pan(image, t, **options)` returns a new Pillow frame.
  - Engine K: `effects-render.drawWhipPan(ctx, t, width, height, drawFrame, options)` wraps a scene draw callback.
  - Engine R: `WhipPan` from `lib/WhipPan.tsx` wraps scene content in a translated, clipped layer.
- Whip Pan adapters are callable but not automatically injected. Their blur is Gaussian and isotropic,
  not a directional shutter-sample renderer.

## Current scope and limitation

Light Sweep now has raster/overlay adapters in P, K and R. The adapters are not yet wired into
the generic scene authoring schema or automatically applied to existing renders.

Whip Pan has callable renderer adapters, but they are not wired into the generic scene authoring
schema or automatically applied to existing renders.

Particle Dissolve now has callable sampled-color particle renderers:
- Engine P: `effects_render.draw_particle_dissolve(image, t, **options)` returns a transparent RGBA Pillow frame.
- Engine K: `effects-render.drawParticleDissolve(ctx, sourceCtx, t, width, height, options)` samples a separate readable source Canvas2D context and paints the particle layer.
- Engine R: `ParticleDissolve` from `lib/ParticleDissolve.tsx` accepts a source URL, frame time and dimensions, then samples the loaded source image into a canvas particle layer. Cross-origin images require CORS permission.

These adapters are callable render helpers, not automatic scene transitions. They are not yet wired into
the generic scene-authoring schema; R also still needs a catalog transition adapter before they can
be selected as scene transitions. The current particle renderer is a sampled-color dot dissolve,
not a full-resolution shatter or tile-fragment simulation.
