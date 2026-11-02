# STYLE.md — <اسم الاتجاه / Direction>

> Recipe for this project only. It translates visual references into the Medo studio's tested primitives; it does not override `brand/BRAND.md`.

## Source and rights
- **Reference:** `<assets/refs/... or none>`
- **Analysis:** `<cache/reference-analysis/report.md or none>`
- **Use:** study technique, pacing and composition only.
- **Do not reproduce:** reference text, logo, characters, footage, proprietary marks or distinctive artwork.

## What defines the look
- **Feeling:** <three words and one sentence>
- **Composition:** <framing, hierarchy, negative space, recurring layout>
- **Recurring device:** <shape, grid, card, line, chart, camera move>
- **Texture:** <none / paper / grain / glow; measured restraint>

## Brand-safe translation
- **Background:** <approved palette token from `brand/brand.json`>
- **Primary text:** <approved palette token>
- **Accent:** <approved palette token; explain where it appears>
- **Typography:** agent-chosen per scene/element from `assets/fonts/fonts.json` and recorded in `plan/text-direction.json` (`fontStyles`/`fontElements`); no forced default. Arabic text needs an Arabic-capable family; roles/weights and pairings from `docs/fonts.md`.
- Reference colors are observations only. Use a brand token instead of copying any sampled hex.

## Motion and pacing
| Event | Studio primitive | Easing / recipe | Approx. duration | Cue / VO relation |
|---|---|---|---:|---|
| Entry | <existing technique / simple cut> | <from `motion/easings.json`> | <s> | <beat / phrase> |
| Hold | <pose / layout / data> | <deterministic> | <s> | <why> |
| Exit / transition | <catalogued P/K transition, or R hard cut> | <approved recipe> | <s> | <cue> |

- **Pacing observation:** <shot length, pauses, density; measured values in report are advisory>
- **Adaptable techniques:** <only items supported by the selected engine and studio>
- **Unsupported / deliberately omitted:** <e.g. reference logo, unlicensed footage, unported R transition>

## Do / Don't
- **Do:** <three concise, measurable rules>
- **Don't:** <three constraints, including no brand drift>

## Decisions / uncertainty
- <what was inferred rather than measured; how to validate in the contact sheet>
