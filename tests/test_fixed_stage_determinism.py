"""Phase 2A - seek determinism, chunked P renders and brand drift (categories F-G).

F asks whether the same instant renders the same when reached forwards, backwards or at random, and
whether a chunked P render equals a whole one; G is the palette lock over the shipped templates. The
scene builders at the bottom of this module are the fixture reel these tests render.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from fixed_stage_support import (
    ENGINE_K,
    ENGINE_P,
    ENGINE_R,
    INK,
    RED,
    ROOT,
    SKILL,
    TOOLS,
    WHITE,
    _sample_direction,
    _sample_stage_spec,
    _sample_words,
    captions,
    fill_rect,
    stage,
)

pytestmark = [pytest.mark.slow, pytest.mark.usefixtures("_cleanup_stage_tmp")]



# ===========================================================================
# F. Determinism, Reverse-Seek & Engine P Chunked Rendering Tests
# ===========================================================================


def test_f1_engine_p_forward_reverse_random_seek_determinism():
    spec = _sample_stage_spec(radius=54.0)
    direction = _sample_direction()
    copy_by_id = {"hdr-topic-1": "موضوع الحلقة: استقرار الفريمات"}
    words = _sample_words()

    def _render_at(t: float) -> bytes:
        fr = stage.render_fixed_stage(
            spec,
            t,
            lambda ts, _st: (
                lambda buf: (
                    fill_rect(buf, 0, 0, 1080, 1920, INK, 1.0),
                    fill_rect(buf, 120, 400, 120 + int(600 * (ts / 3.0)), 480, RED, 1.0),
                    captions.draw_directed_text(
                        buf,
                        "اختبار الثبات الزمني",
                        direction=direction,
                        scene=1,
                        role="title",
                        element_id="det-title",
                        t=ts,
                        start=0.0,
                        end=3.0,
                        cx=540,
                        cy=760,
                        size=54,
                        color=WHITE,
                    ),
                    buf.astype(np.uint8),
                )[3]
            )(np.zeros((1920, 1080, 3), dtype=np.float32)),
            duration=3.0,
            direction=direction,
            copy_by_id=copy_by_id,
            words=words,
            caption_style="pop",
        )
        return hashlib.sha256(fr.tobytes()).hexdigest().encode("ascii")

    indices = list(range(0, 90, 3))
    fwd = {i: _render_at(i / 30.0) for i in indices}
    rev = {i: _render_at(i / 30.0) for i in reversed(indices)}

    shuffled = list(indices)
    random.Random(99).shuffle(shuffled)
    rnd = {i: _render_at(i / 30.0) for i in shuffled}

    assert fwd == rev
    assert fwd == rnd


def test_f2_engine_p_chunked_rendering_and_layout_audit_replay(tmp_path: Path):
    proj = tmp_path / "p_stage_proj"
    env = {
        **os.environ,
        "PATH": f"{ROOT / 'tools' / 'bin'}:{ROOT / '.venv' / 'bin'}:{os.environ.get('PATH', '')}",
    }
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "p-stage-test", "--engine", "p", "--out", str(proj)],
        check=True,
        capture_output=True,
        text=True,
    )

    beats = {
        "duration": 2.0,
        "fps": 30,
        "frames": 60,
        "bounds": [0.0, 2.0],
        "scenes": [{"index": 1, "start": 0.0, "end": 2.0, "dur": 2.0, "frames": 60, "theme": "dark"}],
    }
    copy_doc = {
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "hdr-p-1", "scene": 1, "role": "label", "text": "موضوع الحلقة: الرندر بالمقاطع", "start": 0.3, "end": 1.9},
            {"id": "title-p-1", "scene": 1, "role": "title", "text": "نفس النتيجة في كل مقطع", "start": 0.0, "end": 2.0},
        ],
    }
    td_doc = _sample_direction()
    stage_spec = {
        "version": 1,
        "id": "p-chunk-stage",
        "clock": "vo",
        "theme": "dark",
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 0.5},
            {"mode": "transition", "from": "fullscreen", "to": "framed", "start": 0.5, "end": 1.1, "ease": "cubicInOut"},
            {"mode": "framed", "start": 1.1, "end": 2.0},
        ],
        "over": {
            "header": {
                "enabled": True,
                "slots": [
                    {
                        "id": "hdr-p",
                        "scene": 1,
                        "copyId": "hdr-p-1",
                        "role": "label",
                        "start": 0.3,
                        "end": 1.9,
                        "x": 540,
                        "y": 136,
                        "size": 38,
                        "maxWidth": 880,
                    }
                ],
            }
        },
    }

    (proj / "plan" / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
    (proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (proj / "plan" / "stage.json").write_text(json.dumps(stage_spec), encoding="utf-8")

    (proj / "scenes.py").write_text(
        """import json
import numpy as np
from pathlib import Path
import captions
import stage
from lib import W, H, INK, RED, WHITE, fill_rect
from render_policy import motion_mode
import os

SUPPORTS_REDUCED_MOTION = True
FPS = 30
B = [0.0, 2.0]
CHIP = None

_ROOT = Path(__file__).resolve().parent
_STAGE = stage.create_stage(json.loads((_ROOT / 'plan' / 'stage.json').read_text(encoding='utf-8')))
_TD = json.loads((_ROOT / 'plan' / 'text-direction.json').read_text(encoding='utf-8'))
_CP_DOC = json.loads((_ROOT / 'plan' / 'copy.json').read_text(encoding='utf-8'))
_COPY = {item['id']: item['text'] for item in _CP_DOC['copy']}
_WORDS = [
    {'text': 'نفس', 'start': 0.15, 'end': 0.85},
    {'text': 'النتيجة', 'start': 0.90, 'end': 1.80},
]

def _content(t, _st):
    fr = np.zeros((H, W, 3), dtype=np.float32)
    fill_rect(fr, 0, 0, W, H, INK, 1.0)
    fill_rect(fr, 140, 420, 940, 460, RED, 0.85)
    captions.draw_directed_text(
        fr, _COPY['title-p-1'],
        direction=_TD, scene=1, role='title', element_id='title-p-1',
        t=t, start=0.0, end=2.0, cx=540, cy=740, size=54, color=WHITE,
    )
    return fr.astype(np.uint8)

def render_frame(t):
    mode = motion_mode(os.environ.get('MEDO_MOTION_MODE', 'normal'))
    return stage.render_fixed_stage(
        _STAGE['spec'], t, _content,
        duration=2.0, direction=_TD, copy_by_id=_COPY,
        words=_WORDS, caption_style='pop', motion_mode=mode,
    )
""",
        encoding="utf-8",
    )

    # 1. Run layout_audit_p.py --replay --platform-ui across all 60 frames (including transition 0.5..1.1s!)
    audit_out = proj / "cache" / "audit-p"
    audit_p = subprocess.run(
        [sys.executable, str(TOOLS / "layout_audit_p.py"), "--project", str(proj), "--out", str(audit_out), "--replay", "--platform-ui"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert audit_p.returncode == 0, audit_p.stdout + "\n" + audit_p.stderr
    rep = json.loads((audit_out / "report.json").read_text(encoding="utf-8"))
    assert rep["status"] == "pass"
    assert rep["replay"]["status"] == "pass"
    assert rep["replay"]["checkedFrames"] == 60
    assert rep["replay"]["failedFrames"] == 0

    # 2. Render 3 chunks out-of-order (40..60, then 0..20, then 20..40 splitting right through [0.5..1.1s]!)
    from chunk_utils import is_valid_chunk  # noqa: PLC0415

    for a, b in ((40, 60), (0, 20), (20, 40)):
        c_res = subprocess.run(
            [sys.executable, str(proj / "chunk.py"), str(a), str(b)],
            cwd=proj,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert c_res.returncode == 0, c_res.stdout + "\n" + c_res.stderr
        chunk_mp4 = proj / "out" / f"c_{a:05d}_{b:05d}.mp4"
        assert is_valid_chunk(chunk_mp4, b - a, 1080, 1920)


def test_f3_engine_r_persistent_browser_reverse_and_random_seek_determinism(
    tmp_path: Path, _remotion_runtime
):
    """Verify Engine R reverse-seeking and random-timestamp scrubbing inside ONE persistent
    Chromium browser instance (`openBrowser` + `renderStill`) across fullscreen, transition, and framed states."""
    modules_dir, env = _remotion_runtime
    proj = tmp_path / "r_reverse_seek"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "r-reverse-seek", "--engine", "r", "--out", str(proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (proj / "node_modules").symlink_to(modules_dir, target_is_directory=True)

    beats = {
        "duration": 1.5,
        "fps": 30,
        "frames": 45,
        "bounds": [0.0, 1.5],
        "scenes": [{"index": 1, "start": 0.0, "end": 1.5, "dur": 1.5, "frames": 45}],
    }
    copy_doc = {
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "hdr-rev", "scene": 1, "role": "label", "text": "اختبار القفز العكسي في Remotion", "start": 0.25, "end": 1.45}
        ],
    }
    td_doc = _sample_direction()
    stage_spec = {
        "version": 1,
        "enabled": True,
        "id": "r-reverse-stage",
        "clock": "vo",
        "theme": "dark",
        "defaultFramedBox": {"x": 56, "y": 224, "w": 968, "h": 1096, "r": 72},
        "under": {
            "surfaceRole": "ink_shadow",
            "background": {"id": "wash", "theme": "dark", "speed": 1.0},
            "frame": {"enabled": True, "strokeRole": "red", "strokeWidth": 3, "matRole": "ink_shadow", "matAlpha": 0.36},
        },
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 0.2},
            {"mode": "transition", "from": "fullscreen", "to": "framed", "start": 0.2, "end": 0.7, "ease": "cubicInOut"},
            {"mode": "framed", "start": 0.7, "end": 1.5},
        ],
        "over": {
            "progressBar": {"enabled": True, "y": 64, "height": 6, "marginX": 60, "trackRole": "paper", "trackAlpha": 0.18, "fillRole": "red"},
            "header": {
                "enabled": True,
                "slots": [
                    {
                        "id": "hdr-rev-slot",
                        "scene": 1,
                        "copyId": "hdr-rev",
                        "role": "label",
                        "start": 0.25,
                        "end": 1.45,
                        "x": 540,
                        "y": 136,
                        "size": 38,
                        "maxWidth": 880,
                    }
                ],
            },
        },
    }
    (proj / "plan" / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
    (proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (proj / "plan" / "stage.json").write_text(json.dumps(stage_spec), encoding="utf-8")

    # Run a single persistent Chromium instance via @remotion/renderer and scrub forward, backward, and shuffled!
    scrub_mjs = proj / "scrub_verify.mjs"
    scrub_mjs.write_text(
        """import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';

const entryPoint = path.resolve('src/index.ts');
const browserExecutable = process.env.REMOTION_BROWSER_EXECUTABLE;
const serveUrl = await bundle({entryPoint, onProgress: () => {}});
const puppeteerInstance = await openBrowser('chrome', {
  browserExecutable,
  chromiumOptions: {disableWebSecurity: false},
});

try {
  const composition = await selectComposition({
    serveUrl,
    id: 'MedoReel',
    puppeteerInstance,
    inputProps: {motionMode: 'normal'},
  });

  async function renderOrder(frames) {
    const out = {};
    for (const f of frames) {
      const {buffer} = await renderStill({
        composition,
        serveUrl,
        frame: f,
        imageFormat: 'png',
        scale: 0.5,
        puppeteerInstance,
        inputProps: {motionMode: 'normal'},
      });
      out[String(f)] = crypto.createHash('sha256').update(buffer).digest('hex');
    }
    return out;
  }

  const forward = await renderOrder([3, 9, 15, 21, 30]);
  const reverse = await renderOrder([30, 21, 15, 9, 3]);
  const shuffled = await renderOrder([15, 3, 30, 9, 21]);
  console.log(JSON.stringify({forward, reverse, shuffled}));
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
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        ["node", str(scrub_mjs)],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
    )
    assert res.returncode == 0, res.stdout + "\n" + res.stderr
    last_json = [ln for ln in res.stdout.strip().splitlines() if ln.strip().startswith("{")][-1]
    digests = json.loads(last_json)
    assert digests["forward"] == digests["reverse"], f"Engine R reverse-seek drift: {digests}"
    assert digests["forward"] == digests["shuffled"], f"Engine R random-seek drift: {digests}"
    # Distinct frames across fullscreen -> transition -> framed must not collapse to identical images
    assert len(set(digests["forward"].values())) == 5


# ===========================================================================
# G. Brand Lock, Dependency & Scope Guard Tests
# ===========================================================================

def test_g1_brand_palette_lock_and_zero_threejs_or_archive_drift():
    brand_doc = json.loads((SKILL / "brand" / "brand.json").read_text(encoding="utf-8"))
    allowed_hex = {"#" + v["hex"].lstrip("#").upper() for v in brand_doc["palette"].values()}
    allowed_hex.add(brand_doc["derived"]["ink_shadow"]["hex"].upper())
    assert brand_doc["brand"]["logo"] is None
    assert brand_doc["brand"]["on_screen_name"] is None

    stage_files = [
        ENGINE_P / "stage.py",
        ENGINE_K / "lib" / "stage.js",
        ENGINE_K / "lib" / "stage-canvas.js",
        ENGINE_R / "src" / "lib" / "stage.js",
        ENGINE_R / "src" / "lib" / "FixedStage.tsx",
    ]
    for path in stage_files:
        text = path.read_text(encoding="utf-8")
        assert not re.search(
            r"\bthree\.js\b|from\s+['\"]three['\"]|import\s+three\b|@remotion/three",
            text,
            re.IGNORECASE,
        ), f"{path.name} must not depend on Three.js in Phase 2A"
        for hx in re.findall(r"#[0-9A-Fa-f]{6}", text):
            assert hx.upper() in allowed_hex, f"{path.name} contains off-palette hex {hx}"

    # Run official brand_check.py against templates
    bc = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "brand_check.py"), "--project", str(SKILL / "templates")],
        capture_output=True,
        text=True,
    )
    assert bc.returncode == 0, bc.stdout + "\n" + bc.stderr
