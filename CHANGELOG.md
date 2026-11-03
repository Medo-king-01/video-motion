# Changelog

## Unreleased — 2026-11-03

- Project scaffolds are trackable by Git; only generated output/caches/secrets are ignored.
- Setup has explicit Python/Node prerequisites, a read-only inventory mode, strict failures,
  an optional development dependency set, and reviewed Python constraints / npm lockfile installs.
- Private atomic `.env` creation; symlink/path preflight on scaffold, reference analysis,
  font downloads and caption output. P segments use unique temporary files.
- Caption schema: script `words` are strings; frozen `final` contains scene-local timings.
  Mono PCM16 WAV is required; missing ASR anchors and invalid scene bounds fail clearly.
  JavaScript values are JSON-encoded.
- Font readiness checks every expected family, weight and file; npm font downloads have
  version/integrity pins. Existing bundled assets and licensing are unchanged.
- Added Python 3.10/3.12 quality matrix and scheduled/manual dependency auditing.
- Start from the full repository; see `docs/development.md` for setup and migration details.

Engine contracts and templates are unchanged: P/K/R still use the shared motion/font/brand
interfaces; Hybrid remains sequential full-frame segments with one soundtrack (`HYBRID.md`).
Local validation on Python 3.11: `bash tools/ci.sh` and
`python3 tools/selftest.py --remotion --hybrid` passed (P, K, R and Hybrid real renders).
GitHub matrix results must be checked after the workflow runs; they are not implied by local success.

Additional local checks: 373 tests passed; real `setup.sh --dev --check` left the complete
repository tree unchanged; one real pinned font package passed SHA-512 verification/extraction.
`pip-audit` (base/development Python baseline on 3.11) and production npm audits
(toolkit + Remotion template lockfiles) reported no known vulnerabilities. Optional ASR
dependencies and the legacy Python 3.10 Pillow baseline are not covered by that clean audit.
