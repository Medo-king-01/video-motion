# Hybrid render contract (P + K + R)

This scaffold lets one reel use all three engines where each is strongest:

- **P** — Pillow-based presenter, illustration, and explainer frames.
- **K** — Canvas/Playwright scenes, kinetic type, and its existing motion toolkit.
- **R** — Remotion compositions and React-based graphics.

The engines make **sequential, full-frame segments** in one video. A segment is assigned to exactly one engine. This does **not** composite simultaneous layers from P, K, and R in the same frame, and it does not transfer one engine's capabilities into another. In particular, P/K transitions and animated icons are not automatically available in R.

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
