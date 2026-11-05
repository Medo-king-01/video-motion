# Cover & Thumbnail Generator

The generator creates two static assets from the same approved copy and visual direction:

- \`cover-9x16.png\` — 1080×1920 for Reels / TikTok / vertical video covers.
- \`thumbnail-16x9.png\` — 1280×720 for YouTube thumbnails.

It is an offline Pillow tool. It does not call an image API, download media, modify the source video, or add a default logo, studio name, series title, or episode number.

## Quick start

From the repository root:

\`\`\`bash
python3 tools/cover_generator.py \\
  --title "أداة هتغيّر شغلك" \\
  --subtitle "شرح عملي للمطورين" \\
  --pose explain \\
  --out-dir projects/my-reel/out/cover
\`\`\`

Use a frame from a local image or video as the blurred background:

\`\`\`bash
python3 tools/cover_generator.py \\
  --title "Claude Code" \\
  --subtitle "من الفكرة للتنفيذ" \\
  --frame projects/my-reel/out/master.mp4 \\
  --at 4.2 \\
  --pose laptop-hold \\
  --style tech-editorial \\
  --out-dir projects/my-reel/out/cover
\`\`\`

Use a custom transparent PNG instead of a pose from the library:

\`\`\`bash
python3 tools/cover_generator.py \\
  --title "أفضل أدوات AI" \\
  --pose-file assets/my-character.png \\
  --style blueprint
\`\`\`

## Options

| Option | Purpose |
|---|---|
| \`--title\` | Required exact title. The tool never invents copy. |
| \`--subtitle\` | Optional supporting line. |
| \`--eyebrow\` | Optional short label supplied by the user. |
| \`--frame\` | Optional local image or video used as a blurred background. |
| \`--at\` | Video timestamp in seconds; defaults to 0. |
| \`--pose\` | Pose slug from \`assets/poses/poses.json\`. |
| \`--pose-file\` | Optional custom transparent PNG; mutually exclusive with \`--pose\`. |
| \`--style\` | \`tech-editorial\`, \`keynote\`, \`blueprint\`, or \`terminal\`. |
| \`--font\` | Optional family from \`assets/fonts/fonts.json\`. |
| \`--out-dir\` | Output directory; defaults to \`cache/covers\`. |

## Design and safety rules

- Palette values are read from \`medo-motion/brand/brand.json\`; the generator does not introduce arbitrary brand colours.
- Style profiles use only font families registered in \`assets/fonts/fonts.json\`.
- Arabic and mixed Arabic/Latin copy is laid out with Pillow's RAQM text engine when available.
- Presenter PNGs are uniformly scaled and anchored inside the canvas. The generator never crops the source pose, so the head and feet remain inside the output.
- Only the exact user-provided title, subtitle, and eyebrow are rendered. There is no logo or default series branding.
- Input symlinks are rejected. Video frame extraction uses the configured local \`FFMPEG_BIN\` (or \`ffmpeg\` on PATH).
- The source image/video is not modified.

## Mobile-safe review

After generating the portrait cover, run the existing mobile-grid audit:

\`\`\`bash
python3 tools/phone_preview.py projects/my-reel/out/cover/cover-9x16.png \\
  --out projects/my-reel/out/cover/cover-mobile-qa.png
\`\`\`

Review the full Reel/TikTok player, profile-grid crop, square-feed crop, and small mobile tile before publishing. A generated image is a draft until this review is complete.

## Current boundaries

This first implementation is a deterministic static cover compositor, not a full graphic-design editor. It does not generate new character art, remove backgrounds, select a video frame automatically, or upload/publish assets. Those decisions remain explicit and local.
