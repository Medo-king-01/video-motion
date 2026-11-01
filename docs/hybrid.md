# Hybrid P/K/R reels

A hybrid project combines the three renderer strengths within one timeline: P for presenter/explainer imagery, K for Canvas and kinetic typography, and R for React/Remotion compositions. Version 1 uses **sequential full-frame segments**. Each segment has exactly one rendering engine; simultaneous layers or importing one engine's feature catalog into another are out of scope.

Create the scaffold with `python3 tools/new_project.py <slug> --engine hybrid`. It preserves all three source engines in the project and creates `plan/hybrid.json`. Configure integer, half-open frame ranges at 30 fps, edit each engine's own scene data, and run `python3 ../../tools/render_hybrid.py --project .` from the project root. The renderer validates continuous coverage, exact segment frame counts, 1080×1920 size, 30 fps, and final duration. It adds the optional single soundtrack only after picture assembly and refuses to overwrite an existing final file.

The project-local operator guide, schema example, setup notes, and scope boundaries are in [`medo-motion/templates/HYBRID.md`](../medo-motion/templates/HYBRID.md); the scaffold copies it to `HYBRID.md`. Run `python3 tools/selftest.py --hybrid` to exercise short P, K, and R segments, assembly, and audio muxing end to end. This smoke test does not claim that unported P/K effects exist in R.
