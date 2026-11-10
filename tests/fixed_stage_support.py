"""Shared fixtures and sample data for the Fixed Stage suite (categories A-G).

This module holds what the three Fixed Stage test modules would otherwise copy: the engine import
setup, the three sample builders every phase needs, and the Chromium/Remotion runtime fixtures that
are expensive to create.

It carries no tests and no `pytestmark`: pytest only collects `test_*.py`, so nothing here is a test
module. The `slow` mark belongs to the consumers - a helper that quietly marked itself would mark
tests that merely import something else from it.
"""
from __future__ import annotations  # noqa: F401 - re-exported for the Fixed Stage test modules

import hashlib  # noqa: F401 - re-exported for the Fixed Stage test modules
import json  # noqa: F401 - re-exported for the Fixed Stage test modules
import os  # noqa: F401 - re-exported for the Fixed Stage test modules
import random  # noqa: F401 - re-exported for the Fixed Stage test modules
import re  # noqa: F401 - re-exported for the Fixed Stage test modules
import shutil  # noqa: F401 - re-exported for the Fixed Stage test modules
import subprocess  # noqa: F401 - re-exported for the Fixed Stage test modules
import sys  # noqa: F401 - re-exported for the Fixed Stage test modules
from pathlib import Path  # noqa: F401 - re-exported for the Fixed Stage test modules

import numpy as np  # noqa: F401 - re-exported for the Fixed Stage test modules
import pytest  # noqa: F401 - re-exported for the Fixed Stage test modules
from PIL import Image  # noqa: F401 - re-exported for the Fixed Stage test modules

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "medo-motion"
ENGINE_P = SKILL / "templates" / "procedural-reels"
ENGINE_K = SKILL / "templates" / "render"
ENGINE_R = SKILL / "templates" / "remotion"
TOOLS = ROOT / "tools"

if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(ENGINE_P) in sys.path:
    sys.path.remove(str(ENGINE_P))
sys.path.insert(0, str(ENGINE_P))

import captions  # noqa: E402,F401 - re-exported for the Fixed Stage test modules
import layout_p  # noqa: E402,F401 - re-exported for the Fixed Stage test modules
import stage  # noqa: E402,F401 - re-exported for the Fixed Stage test modules
import transition  # noqa: E402,F401 - re-exported for the Fixed Stage test modules
from lib import INK, RED, WHITE, YEL, fill_rect  # noqa: E402,F401 - re-exported


def _sample_stage_spec(*, radius: float = 48.0, with_header: bool = True) -> dict:
    hdr_slots = (
        [
            {
                "id": "hdr-s1",
                "scene": 1,
                "copyId": "hdr-topic-1",
                "role": "label",
                "start": 0.6,
                "end": 2.4,
                "x": 540,
                "y": 136,
                "size": 38,
                "maxWidth": 880,
                "colorRole": "paper",
                "accentRole": "salmon",
                "pillRole": "ink",
                "pillBorderRole": "red",
                "pillAlpha": 0.92,
                "anchor": {"scene": 1, "word": 1, "text": "الفرق"},
            }
        ]
        if with_header
        else []
    )
    return {
        "version": 1,
        "id": "test-fixed-stage",
        "clock": "vo",
        "theme": "dark",
        "canvas": {"w": 1080, "h": 1920, "fps": 30},
        "defaultFramedBox": {"x": 80, "y": 240, "w": 920, "h": 1060, "r": radius},
        "under": {
            "surfaceRole": "ink_shadow",
            "background": {"id": "wash", "theme": "dark", "density": 40, "angle": 0, "speed": 1.0},
            "frame": {
                "enabled": True,
                "strokeRole": "red",
                "strokeWidth": 3,
                "matRole": "ink_shadow",
                "matAlpha": 0.35,
            },
        },
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 0.5},
            {
                "mode": "transition",
                "from": "fullscreen",
                "to": "framed",
                "start": 0.5,
                "end": 1.1,
                "ease": "cubicInOut",
                "anchor": {"scene": 1, "word": 1, "text": "الفرق"},
            },
            {"mode": "framed", "start": 1.1, "end": 2.1},
            {
                "mode": "transition",
                "from": "framed",
                "to": "fullscreen",
                "start": 2.1,
                "end": 2.7,
                "ease": "cubicInOut",
            },
            {"mode": "fullscreen", "start": 2.7, "end": 3.0},
        ],
        "over": {
            "progressBar": {
                "enabled": True,
                "y": 64,
                "height": 6,
                "marginX": 60,
                "trackRole": "paper",
                "trackAlpha": 0.18,
                "fillRole": "red",
            },
            "header": {
                "enabled": with_header,
                "slots": hdr_slots,
            },
            "captions": {"enabled": True, "y": 1455},
        },
    }


def _sample_direction() -> dict:
    return {
        "version": 3,
        "status": "directed",
        "decidedBy": "agent",
        "concept": "Fixed Stage technical verification",
        "scenes": [
            {
                "scene": 1,
                "captionStyle": "pop",
                "captionWhy": "clear word emphasis synchronized to VO",
                "textStyles": {
                    "title": "riseword",
                    "body": "softfade",
                    "label": "softfade",
                },
                "textWhy": "clean legible motion inside Fixed Stage",
                "fontStyles": {
                    "title": {"family": "Cairo", "weight": 800},
                    "body": {"family": "Cairo", "weight": 700},
                    "label": {"family": "Cairo", "weight": 800},
                },
                "fontWhy": "Cairo bold Arabic legibility",
            }
        ],
    }


def _sample_words() -> list[dict]:
    return [
        {"text": "إيه", "start": 0.15, "end": 0.48},
        {"text": "الفرق", "start": 0.55, "end": 1.05},
        {"text": "الحقيقي", "start": 1.15, "end": 1.75},
        {"text": "بينهم؟", "start": 1.80, "end": 2.45},
    ]


# ===========================================================================
# A. Unit Tests — Core Stage Geometry & Parity
# ===========================================================================


def _run_remotion_stills_batch(proj: Path, env: dict, tasks: list[dict]) -> dict[str, dict]:
    """Bundle `src/index.ts` ONCE and render multiple stills/props in ONE persistent Chromium
    instance (`@remotion/bundler` + `@remotion/renderer`), avoiding redundant Webpack builds."""
    runner_js = """
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';

const tasks = JSON.parse(process.argv[1]);
const entryPoint = path.resolve('src/index.ts');
const browserExecutable = process.env.REMOTION_BROWSER_EXECUTABLE;
const serveUrl = await bundle({entryPoint, onProgress: () => {}});
const puppeteerInstance = await openBrowser('chrome', {
  browserExecutable,
  chromiumOptions: {disableWebSecurity: false},
});
const results = {};
try {
  for (const t of tasks) {
    try {
      const inputProps = t.props || {};
      const composition = await selectComposition({
        serveUrl,
        id: t.compId,
        puppeteerInstance,
        inputProps,
      });
      await renderStill({
        composition,
        serveUrl,
        frame: t.frame,
        imageFormat: 'png',
        output: t.outPath ? path.resolve(t.outPath) : null,
        puppeteerInstance,
        inputProps,
      });
      results[t.key] = {ok: true, error: null};
    } catch (err) {
      results[t.key] = {ok: false, error: String(err?.stack || err?.message || err)};
    }
  }
  console.log('__BATCH_RESULTS__' + JSON.stringify(results));
} finally {
  process.on('unhandledRejection', () => {});
  await new Promise((r) => setTimeout(r, 150));
  try {
    await puppeteerInstance.close({silent: true});
  } catch {}
  try {
    fs.rmSync(serveUrl, {recursive: true, force: true});
  } catch {}
}
process.exit(0);
"""
    res = subprocess.run(
        ["node", "--input-type=module", "-e", runner_js, json.dumps(tasks)],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
    )
    assert res.returncode == 0, res.stdout + "\n" + res.stderr
    marker_lines = [ln for ln in res.stdout.splitlines() if ln.startswith("__BATCH_RESULTS__")]
    assert marker_lines, res.stdout + "\n" + res.stderr
    return json.loads(marker_lines[-1][len("__BATCH_RESULTS__"):])


# `import *` skips underscore names by default; the sample builders and fixtures below are marked
# private on purpose (they are not tests), so export them explicitly.
__all__ = [name for name in globals() if not name.startswith("__")]
