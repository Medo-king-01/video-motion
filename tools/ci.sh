#!/usr/bin/env bash
# The checks CI would run, locally and anywhere: lint → unit tests → brand audit.
# GitHub Actions needs the `workflows` permission to own .github/workflows, so this
# script is the portable version of that pipeline (run it in any agent/terminal).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-python3}

echo "== ruff =="
$PY -m ruff check . 2>/dev/null || ruff check .

echo "== pytest =="
$PY -m pytest -q

echo "== technique library =="
$PY tools/techniques.py --validate
$PY tools/techniques.py --markdown docs/techniques.md --check

echo "== reel lint =="
$PY tools/reel_lint.py tests/fixtures/reel/good --strict
if $PY tools/reel_lint.py tests/fixtures/reel/bad >/dev/null 2>&1; then
  echo "!! the deliberately-bad fixture passed the lint — a rule stopped firing"
  exit 1
fi

echo "== icons =="
$PY medo-motion/icons/build.py --check

echo "== brand audit =="
$PY medo-motion/scripts/brand_check.py --project medo-motion/templates

echo "CI OK"
