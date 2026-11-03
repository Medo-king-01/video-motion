# Short commands for humans and agents. `make help` lists them.
.DEFAULT_GOAL := help
PY ?= python3

help:            ## show this list
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup:           ## install runtime deps (Python/Node are prerequisites; use a venv)
	bash tools/setup.sh

setup-dev:       ## install runtime + pytest/Ruff for local CI
	bash tools/setup.sh --dev

doctor:          ## print READY / DEGRADED / BLOCKED per capability
	$(PY) tools/doctor.py

test:            ## unit tests (no renders)
	$(PY) -m pytest

ci:              ## lint + unit tests + brand audit (what CI would run)
	bash tools/ci.sh

selftest:        ## doctor + tests + P/K frames (R render: python3 tools/selftest.py --remotion)
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

grid:            ## tempo-locked cue sheet: make grid PATTERN="k.h.|k.h." BPM=120 BARS=2 [OUT=c.json]
	$(PY) tools/sfx_kit.py --grid "$(or $(PATTERN),k.h.|k.h.|k.h.|k...)" --bpm $(or $(BPM),120) \
		--bars $(or $(BARS),1) --out $(or $(OUT),cache/grid-cues.json)

length:          ## measure the VO and derive the timeline: make length VO=assets/vo/x.wav
	$(PY) tools/vo_length.py $(or $(VO),out/vo24.wav) $(if $(JSON),--json $(JSON),)

fonts:           ## (re)install the free type system into assets/fonts: make fonts
	$(PY) tools/fonts_install.py

fonts-sheet:     ## specimen sheet of every family + pairings (cache/fonts-sheet.png)
	$(PY) tools/fonts_preview.py

techniques:      ## draw this reel's moves from the library: make techniques PLAN=projects/x/plan/beats.json
	$(PY) tools/techniques.py --draw $(if $(PLAN),--from-plan $(PLAN) --json $(dir $(PLAN))techniques.json,) \
		$(if $(SEED),--seed $(SEED),) $(if $(ENERGY),--energy $(ENERGY),)

techniques-doc:  ## regenerate docs/techniques.md from assets/techniques.json
	$(PY) tools/techniques.py --markdown docs/techniques.md

lint:            ## lint a reel plan before rendering: make lint P=projects/x [STRICT=1]
	$(PY) tools/reel_lint.py $(or $(P),.) $(if $(STRICT),--strict,) $(if $(SCAN),--scan-code,)

poses:           ## rebuild Medo's pose cut-outs + a QA sheet: make poses
	$(PY) tools/presenter_build.py --sheet cache/poses-sheet.png

sfx:             ## render the sound-kit audition (cache/sfx-demo.mp3)
	$(PY) tools/sfx_kit.py --demo cache/sfx-demo.mp3

sfx-bank:        ## write one WAV per sound: make sfx-bank DIR=out/sfx
	$(PY) tools/sfx_kit.py --bank $(or $(DIR),out/sfx)

transitions:     ## QA sheet + preview clip of every transition: make transitions [VIDEO=1]
	$(PY) tools/transitions_sheet.py $(if $(VIDEO),--video cache/transitions.mp4,)

icons:           ## rebuild the animated icon layer + a QA sheet
	$(PY) medo-motion/icons/build.py
	$(PY) tools/icons_sheet.py --out cache/icons-sheet.png

clean:           ## remove caches and render output (keeps sources)
	find . -name __pycache__ -type d -not -path "*/node_modules/*" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
	rm -rf projects/*/out projects/*/cache cache

.PHONY: help setup setup-dev doctor test ci selftest new brand icons studio theatre techniques techniques-doc lint poses sfx sfx-bank transitions clean
