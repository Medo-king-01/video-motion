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

echo "== brand audit =="
$PY medo-motion/scripts/brand_check.py

echo "CI OK"
