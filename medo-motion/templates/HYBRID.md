# Hybrid render contract (P + K + R)

This scaffold lets one reel use all three engines where each is strongest:

- **P** — Pillow-based presenter, illustration, and explainer frames.
- **K** — Canvas/Playwright scenes, kinetic type, and its existing motion toolkit.
- **R** — Remotion compositions and React-based graphics.

Two shapes are supported, and a project may mix them:

- **v1 — sequential, full-frame segments** <!-- CAP:sequence -->: a segment is assigned to exactly
  one engine, and that engine owns the whole frame.
- **v2 — one transparent overlay** <!-- CAP:layers -->: a segment carries `layers` = an opaque
  base plus **one** Engine-K layer rendered with alpha, so kinetic type or UI can sit over
  presenter footage <!-- CAP:alpha_layer -->. Only K may be transparent
  <!-- CAP:alpha_k_only -->, and never more than one overlay
  <!-- CAP:single_overlay -->. v1 files keep working: they are normalised on read
  <!-- CAP:v1_normalised -->. Masking, two-overlay stacks and alpha on P/R are **not** supported.

Neither shape transfers one engine's capabilities into another: P/K transitions and animated icons
are not automatically available in R.

## 1. Prepare a timeline

Measure the approved voice-over first and use exactly 30 fps. Write `plan/hybrid.json` using integer, half-open frame ranges (`start_frame` inclusive, `end_frame` exclusive). Segments must start at frame 0, be contiguous without gaps or overlaps, and end at `duration_frames`.

```json
{
  "version": 1,
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "duration_frames": 300,
  "audio": "assets/vo/vo24.wav",
  "segments": [
    {"id": "presenter", "engine": "p", "start_frame": 0, "end_frame": 90},
    {"id": "headline", "engine": "k", "start_frame": 90, "end_frame": 180},
    {"id": "data-story", "engine": "r", "start_frame": 180, "end_frame": 300}
  ]
}
```

Here, 300 frames is 10 seconds. Use the measured VO duration to calculate the frame count; the audio duration must match the timeline within 0.15 seconds. Set `audio` to `null` only for a deliberately silent video.

For R segments, also keep `plan/beats.json` valid for the **whole** composition: its measured `duration`, contiguous scene boundaries, and final scene end must match the hybrid timeline. P's timing lives in `scenes.py` (`B`); K's lives in `src/data.js`. Edit those engine-native timelines and scene content to suit the reel. The hybrid plan selects which engine renders each interval; it does not rewrite engine scene designs.

## 1a. Layer segments (v2)

A v2 plan uses `layers` instead of `engine` for that segment (`version: 2` at the top level):

```json
{
  "id": "presenter-with-type",
  "start_frame": 0,
  "end_frame": 90,
  "layers": [
    {"engine": "p"},
    {"engine": "k", "alpha": true}
  ]
}
```

- The first layer is the **opaque base** (P, K or R); the second is a **transparent K overlay**.
- `engine` and `layers` in the same segment is an error — use one.
- The overlay module must not paint a full-bleed background: `src/main.js` leaves the canvas
  transparent when `alpha=1` (it clears instead of filling).
- Frames come from the segment's frame range only: the overlay is composited with
  `overlay=format=auto` and `-frames:v` from the frame delta, never from `-shortest` — a mismatch
  is an error, not a silence <!-- CAP:frame_exact -->.
- The soundtrack is still added once, after picture assembly
  <!-- CAP:audio_after_picture -->.

## 2. Configure and render

Install the R scaffold dependencies once with `npm ci`. K uses the configured shared toolkit/Chromium described in `medo-motion/reference/planning-and-tracking.md` and `tools/chromium.mjs`; no browser or packages are downloaded automatically by the hybrid renderer.

From this project directory:

```sh
python3 ../../tools/render_hybrid.py --project .
```

The renderer validates the plan before rendering, checks every silent engine segment with ffprobe for exact frame count, dimensions, and frame rate, then joins the segments and adds the soundtrack once. The finished file is `out/hybrid.mp4`; per-segment diagnostics are kept in a unique `cache/hybrid-*` directory. Existing output files are never overwritten. Choose a new `--out` path for another version.

Optional command-line overrides: `--plan`, `--out`, `--audio` (or `--audio -` to force silence), `--ffmpeg`, `--ffprobe`, `--node`, and `--python`.

## Scope and quality checks

- Video contract: 1080×1920, 30 fps, exact integer frame count.
- Exactly one selected engine renders each full-frame segment; there are no hidden approval gates.
- Each engine's assets and features remain engine-local unless they are deliberately ported and separately tested.
- Audio is muxed only after picture assembly, giving the complete reel one continuous track.
- A failing engine, invalid segment, gap, overlap, duration mismatch, or bad final stream stops the render rather than claiming success.
