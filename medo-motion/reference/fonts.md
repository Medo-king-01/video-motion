<!-- Video Motion · font choice & sourcing (manifest-first). -->
# Font choice & sourcing — the studio manifest comes first

**There is no forced creative default.** The agent chooses the most attractive, reel-fitting
face (Arabic or Latin) for every on-screen text element and records it in
`plan/text-direction.json` (`fontStyles` / `fontElements`). The unified reference is
`DESIGN_SYSTEM.md`; the human-facing catalog is `docs/fonts.md`.

## 1) Choose from the manifest

- The only fonts allowed on screen are in `assets/fonts/fonts.json` — 125 families (61 Arabic + 64 Latin):
  123 SIL OFL 1.1 + Permanent Marker (Apache-2.0) + Ubuntu (UFL-1.0), free for commercial use and redistribution.
- Choose from the curated shortlist (`medo-motion/looks/shortlist.json`) unless a reason is recorded;
  families measured >= 0.20 collision ratio are `status: review` in the manifest — see docs/fonts.md.
- Cairo/Inter are a last-resort fallback for system chrome only, not a creative default.
- Arabic text must use an Arabic-capable family. Keep whole-word shaping, RTL, no letter-spacing.
- Prefer an Arabic↔Latin pair with the same feel; at most two families per scene unless a
  deliberate reason is recorded.
- Show the chosen faces in `plan/design.html` and record the rationale in `TASTE.md` §3.

## 2) If the manifest is missing a face

Research candidates first, but **do not put an unregistered font on screen**. To add a family:

1. Verify it is SIL OFL 1.1 (or another licence the studio explicitly accepts) and that it
   actually shapes Arabic correctly if it will carry Arabic text.
2. Add it to `FAMILIES` in `tools/fonts_install.py` (family, npm package, weights, role, pairs, tags).
3. Run `python3 tools/fonts_install.py --only "<Family>"` to fetch the TTFs + OFL into
   `assets/fonts/<Family>/` and rebuild the manifest.
4. Document it in `docs/fonts.md` and `assets/CREDITS.md`.
5. Run the font tests (`tests/test_fonts.py`): licence, shaping-overlap gate, and rendering.
   Families whose static instances collide (e.g. Reem Kufi, Noto Kufi Arabic, Jomhuria) are rejected.

External specimen sites (Google Fonts, Open Foundry, Fontshare, etc.) are useful for *researching*
candidates to add to the manifest. Personal-use-only fonts are not allowed in this studio's
client/commercial output; when in doubt, pick an OFL family already in the manifest.

## 3) Use in code

- **K:** `useFont` / `useDirectedFonts` from `lib/fonts.js` + `lib/captions.js`, then `ctx.font`.
- **P:** `lib.font(size, family, weight)` / `text_sprite(..., family, weight)`.
- **R:** the scaffold copies the manifest to `public/fonts/`; `RemotionRoot` generates
  `@font-face` from it and `DirectedText` applies the plan's chosen family/weight.
- Always render a test still and confirm the intended face loaded (no silent fallback, no missing glyphs).
