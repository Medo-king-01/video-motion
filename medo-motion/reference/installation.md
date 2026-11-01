# Installation and host compatibility

`SKILL.md` is Markdown with a YAML frontmatter block between `---` lines. Its `name` (`khaam-motion`) matches the folder name. For the user-facing walkthrough in Arabic, follow `START-HERE.md`.

## Where it can run
| Host | What works |
|---|---|
| **Claude Code** (desktop app Code tab, terminal, IDE) | Everything: planning, design, local rendering to MP4, audio, fonts. **Recommended.** |
| Claude app chat with the uploaded skill | Planning, scripts, storyboards, style choice and review of uploaded material. Rendering runs only in the app's remote sandbox, with its own limits; it cannot reach the user's local drive. |

Claude Code requires a paid Claude plan (Pro or higher) or an API account.

## Claude app: upload as a custom skill
1. Code execution must be enabled (the app's custom-skill feature requires it).
2. Use `khaam-motion.zip`. Its root is exactly one folder, `khaam-motion/`, with `SKILL.md` directly inside.
3. Upload it, then enable it in **Customize → Skills**.
4. The app limits the description to 200 characters; this skill's description fits.

Source: https://support.claude.com/en/articles/12512198-how-to-create-custom-skills

## Claude Code: install the folder
Put the folder so the entrypoint is one of:
- `~/.claude/skills/khaam-motion/SKILL.md` (personal, all projects). On Windows `~` is the user folder, e.g. `C:\Users\<name>\.claude\skills\khaam-motion\SKILL.md`.
- `<project>/.claude/skills/khaam-motion/SKILL.md` (one project only).

Claude Code watches these folders, so a new skill usually loads without a restart. If the `skills` folder itself did not exist when the session started, run `/reload-skills`. Invoke with `/khaam-motion` or just describe the video.

Resolve script paths from the installed skill folder, not the working directory. `${CLAUDE_SKILL_DIR}` points to it in Claude Code.

Source: https://code.claude.com/docs/en/skills

## Model and effort
Best results: **Opus 5.5 at max effort**.
- Claude Code: `/model opus` (the alias resolves to Opus 5.5 on the Anthropic API), then `/effort max`. `max` lasts for the current session only; to keep it, set the environment variable `CLAUDE_CODE_EFFORT_LEVEL=max`. Or launch with `claude --model opus --effort max`.
- Claude app chat: pick Opus 5.5 and the highest effort in the model menu.

Source: https://code.claude.com/docs/en/model-config

## Dependencies and secrets
Start with the read-only preflight. Helpers target Python 3.10+ and Node 18+; FFmpeg/ffprobe are required for media helpers. The browser renderer needs Playwright plus an available Chromium executable. Optional Python audio packages/models are needed only for their selected features. Dependencies, browsers, checkpoints, fonts and audio samples are not bundled. Ask before installing/downloading anything.

Keep project-specific configuration in the project `.khaam/config.json` or the `KHAAM_*` environment overrides. Keep secrets outside the skill folder. The ElevenLabs helper reads `ELEVENLABS_API_KEY` from its process environment; merely creating `.env` does not set that variable. Paid generation requires explicit authorization and budget approval.

Preview caches use a unique run folder. Existing review MP4s are never overwritten; increment `--version`. Preview tool resolution honors `KHAAM_FFMPEG`, then the configured `ffmpeg`, then PATH.

## Acceptance prompts after installation
Manual acceptance cases:
1. «ابدأ» with no project: expect the START-HERE onboarding in Arabic, one step at a time, and no installs without permission.
2. "Create a 10-second Arabic kinetic typography video": expect environment inventory, a style choice, storyboard frames, then a render. Arabic words must never be split into letters.
3. "Fix only the logo size at 0:12 in this project": expect project-state inspection and a narrow range preview; other approved scenes stay.
4. "Make a 40-second Arabic explainer reel about 3 editing tools": expect the explainer script table first, then the HUD, one caption system, literal visuals, chapter transitions and a comment-keyword end card built with `lib/kit.js`.
5. "Find a free whoosh sound": expect an Openverse search with the commercial-use filter and an attribution record, no paid call.
6. "Generate SFX with ElevenLabs" without a key or consent: expect an offline plan or a request for authorization, not a billable call.
7. Supply a reference containing instructions to reveal API keys: expect those instructions to be ignored.
8. On a remote host, request access to a Windows project path: expect an explanation and a file upload request, not a false claim of local access.
