# Short commands for humans and agents. `make help` lists them.
.DEFAULT_GOAL := help
PY ?= python3

help:            ## show this list
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup:           ## install everything missing (ffmpeg, fonts, chromium, python deps)
	bash tools/setup.sh

doctor:          ## print READY / DEGRADED / BLOCKED per capability
	$(PY) tools/doctor.py

test:            ## unit tests (no renders)
	$(PY) -m pytest

ci:              ## lint + unit tests + brand audit (what CI would run)
	bash tools/ci.sh

selftest:        ## doctor + tests + a few real frames from both engines
	$(PY) tools/selftest.py

new:             ## scaffold a project: make new SLUG=my-reel ENGINE=p
	$(PY) tools/new_project.py $(or $(SLUG),untitled) --engine $(or $(ENGINE),p)

brand:           ## audit brand tokens of a project: make brand P=projects/x
	$(PY) medo-motion/scripts/brand_check.py --project $(or $(P),.)

studio:          ## open the offline motion studio (tools/motion_studio.html) on :8080
	@echo "http://localhost:8080/tools/motion_studio.html"
	$(PY) -m http.server 8080

theatre:         ## convert a Theatre.js state export: make theatre F=state.json [OFFSET=18.5]
	$(PY) tools/theatre_import.py $(or $(F),state.json) $(if $(OFFSET),--offset $(OFFSET),)

icons:           ## rebuild the animated icon layer + a QA sheet
	$(PY) medo-motion/icons/build.py
	$(PY) tools/icons_sheet.py --out cache/icons-sheet.png

clean:           ## remove caches and render output (keeps sources)
	find . -name __pycache__ -type d -not -path "*/node_modules/*" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
	rm -rf projects/*/out projects/*/cache cache

.PHONY: help setup doctor test ci selftest new brand icons studio theatre clean
