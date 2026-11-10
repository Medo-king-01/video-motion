"""Phase 2A - real Chromium and Remotion renders for the Fixed Stage (category E).

Every test here scaffolds a project and renders actual frames: the slow, browser-bound half of the
suite. Fixtures live in `fixed_stage_support.py`; pure geometry lives in `test_fixed_stage.py`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from fixed_stage_support import (
    TOOLS,
    _run_remotion_stills_batch,
    _sample_direction,
)
from PIL import Image

pytestmark = [pytest.mark.slow, pytest.mark.usefixtures("_cleanup_stage_tmp")]



# ===========================================================================
# E. Cross-Engine Real Rendering Verification (Engines K & R in Chromium)
# ===========================================================================


# ===========================================================================
# E1-E2. One real render per engine: K stills, R Remotion composition
# ===========================================================================

def test_e1_engine_k_real_chromium_render_and_audit_replay(tmp_path: Path, _chromium_env):
    _chrom, env = _chromium_env
    proj = tmp_path / "k_stage_proj"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "k-stage-test", "--engine", "k", "--out", str(proj)],
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
            {"id": "hdr-k-1", "scene": 1, "role": "label", "text": "موضوع الحلقة: معمارية المعالج", "start": 0.4, "end": 1.9},
            {"id": "body-k-1", "scene": 1, "role": "title", "text": "الفرق بين اللابتوب والمكتبي", "start": 0.0, "end": 2.0},
        ],
    }
    td_doc = _sample_direction()
    stage_spec = {
        "version": 1,
        "id": "k-stage",
        "clock": "vo",
        "theme": "dark",
        "defaultFramedBox": {"x": 100, "y": 280, "w": 880, "h": 1000, "r": 100},
        "under": {
            "surfaceRole": "ink_shadow",
            "background": None,
            "frame": {"enabled": False},
        },
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 0.3},
            {"mode": "transition", "from": "fullscreen", "to": "framed", "start": 0.3, "end": 0.7, "ease": "cubicInOut"},
            {"mode": "framed", "start": 0.7, "end": 2.0},
        ],
        "over": {
            "progressBar": {"enabled": True, "y": 64, "height": 8, "marginX": 60, "trackRole": "paper", "trackAlpha": 0.2, "fillRole": "red"},
            "header": {
                "enabled": True,
                "slots": [
                    {
                        "id": "hdr-k",
                        "scene": 1,
                        "copyId": "hdr-k-1",
                        "role": "label",
                        "start": 0.4,
                        "end": 1.9,
                        "x": 540,
                        "y": 136,
                        "size": 40,
                        "maxWidth": 880,
                        "colorRole": "paper",
                    }
                ],
            },
            "captions": {"enabled": True, "y": 1455},
        },
    }

    (proj / "plan" / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
    (proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (proj / "plan" / "stage.json").write_text(json.dumps(stage_spec), encoding="utf-8")

    (proj / "src" / "data.js").write_text(
        "export const W = 1080, H = 1920, FPS = 30;\n"
        "export const scenes = [{ id: 's1', start: 0, end: 2.0 }];\n"
        "export const DURATION = 2.0;\n",
        encoding="utf-8",
    )
    words_js = json.dumps([
        {"text": "الفرق", "start": 0.1, "end": 0.9},
        {"text": "الحقيقي", "start": 0.95, "end": 1.85},
    ], ensure_ascii=False)
    (proj / "src" / "scenes" / "s1.js").write_text(
        f"""import {{ renderFixedStage }} from '../lib/stage-canvas.js';
import {{ drawDirectedText, useDirectedFonts }} from '../lib/captions.js';
import {{ compositeTransition, makeLayer }} from '../lib/transition.js';
import {{ PALETTE }} from '../lib/brand.js';

export const supportsReducedMotion = true;
export const manualFixedStage = true;
let stageSpec = null;
let copyMap = {{}};
const WORDS = {words_js};

export async function init() {{
  const [stRes, cpRes, tdRes] = await Promise.all([
    fetch('/plan/stage.json'),
    fetch('/plan/copy.json'),
    fetch('/plan/text-direction.json'),
  ]);
  stageSpec = await stRes.json();
  const cpDoc = await cpRes.json();
  for (const item of cpDoc.copy || []) copyMap[item.id] = item.text;
  const tdDoc = await tdRes.json();
  await useDirectedFonts(tdDoc, 1);
}}

export async function draw(ctx, localT, {{ W, H, t, direction, motionMode }}) {{
  await renderFixedStage(ctx, stageSpec, t, {{
    duration: 2.0,
    direction,
    copyById: copyMap,
    words: WORDS,
    captionStyle: 'pop',
    motionMode,
    drawContent: (c) => {{
      // Bright paper fill + salmon wipe transition spanning the whole 1080x1920 CONTENT space
      const layA = makeLayer(W, H, (g) => {{ g.fillStyle = PALETTE.paper; g.fillRect(0, 0, W, H); }});
      const layB = makeLayer(W, H, (g) => {{ g.fillStyle = PALETTE.salmon; g.fillRect(0, 0, W, H); }});
      compositeTransition(c, layA, layB, 'wipe', 0.5, W, H);
      drawDirectedText(c, copyMap['body-k-1'], {{
        direction, scene: 1, role: 'title', elementId: 'body-k-1',
        time: localT, start: 0, end: 2.0, x: 540, y: 740, size: 54,
        color: PALETTE.ink, theme: 'light', shadow: 'transparent',
      }});
    }},
  }});
}}
""",
        encoding="utf-8",
    )

    # 1. Run Engine K layout audit + reverse-seek RGBA SHA-256 replay + social right-rail check
    audit_out = proj / "cache" / "audit-k"
    audit_res = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "2.0", "--fps", "30", "--audit", "--replay", "--platform-ui", "--out", str(audit_out)],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert audit_res.returncode == 0, audit_res.stdout + "\n" + audit_res.stderr
    report = json.loads((audit_out / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    assert report["replay"]["status"] == "pass"
    assert report["replay"]["checkedFrames"] == 60
    assert report["replay"]["failedFrames"] == 0

    # 2. Render actual JPG frames and inspect fullscreen vs framed rounded clipping & unclipped OVER
    frames_out = proj / "cache" / "frames-k"
    jpg_res = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "2.0", "--fps", "30", "--jpg", "--out", str(frames_out)],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert jpg_res.returncode == 0, jpg_res.stdout + "\n" + jpg_res.stderr

    # Frame 3 (t=0.10s -> fullscreen): extreme corner (10, 10) has bright content
    im_full = np.asarray(Image.open(frames_out / "00003.jpg").convert("RGB"))
    assert int(im_full[10, 10].max()) > 180

    # Frame 36 (t=1.20s -> framed x=100..980, y=280..1280, r=100):
    im_framed = np.asarray(Image.open(frames_out / "00036.jpg").convert("RGB"))
    # Outside window on left (x=50, y=800) & inside exterior rounded corner luna (x=106, y=286): dark #030303 (JPEG <= 12)
    assert int(im_framed[800, 50].max()) <= 12
    assert int(im_framed[286, 106].max()) <= 12
    assert int(im_framed[286, 974].max()) <= 12
    assert int(im_framed[1274, 106].max()) <= 12
    assert int(im_framed[1274, 974].max()) <= 12
    # Interior of window has bright wipe transition (left side salmon, right side paper)
    assert int(im_framed[600, 300].max()) > 180
    assert int(im_framed[600, 800].max()) > 220
    # Unclipped OVER header (y~136), progress bar (y~66), and caption (y~1455) render outside win(t)!
    assert int(im_framed[64:72, 100:500, 0].max()) > 170
    assert int(im_framed[115:160, 250:830].max()) > 180
    assert int(im_framed[1425:1485, 250:830].max()) > 180


def test_e2_engine_r_real_remotion_chromium_render_and_dom_layout_audit(tmp_path: Path, _remotion_runtime):
    modules_dir, env = _remotion_runtime
    proj = tmp_path / "r_stage_proj"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "r-stage-test", "--engine", "r", "--out", str(proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (proj / "node_modules").symlink_to(modules_dir, target_is_directory=True)

    td_doc = _sample_direction()
    stage_spec = {
        "version": 1,
        "id": "r-stage",
        "clock": "vo",
        "theme": "dark",
        "defaultFramedBox": {"x": 100, "y": 280, "w": 880, "h": 1000, "r": 100},
        "under": {
            "surfaceRole": "ink_shadow",
            "background": None,
            "frame": {"enabled": False},
        },
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 0.4},
            {"mode": "transition", "from": "fullscreen", "to": "framed", "start": 0.4, "end": 1.0, "ease": "cubicInOut"},
            {"mode": "framed", "start": 1.0, "end": 3.0},
        ],
        "over": {
            "progressBar": {"enabled": True, "y": 64, "height": 8, "marginX": 60, "trackRole": "paper", "trackAlpha": 0.2, "fillRole": "red"},
            "header": {
                "enabled": True,
                "slots": [
                    {
                        "id": "hdr-r",
                        "scene": 1,
                        "copyId": "hdr-r-1",
                        "role": "label",
                        "start": 0.5,
                        "end": 2.8,
                        "x": 540,
                        "y": 136,
                        "size": 40,
                        "maxWidth": 880,
                        "colorRole": "paper",
                    }
                ],
            },
            "captions": {"enabled": True, "y": 1455},
        },
    }
    copy_map = {
        "hdr-r-1": "موضوع الحلقة: معمارية الذاكرة",
        "body-r-1": "الفرق بين DDR5 و DDR4",
        "cap-r-1": "سرعة نقل أعلى بكثير",
    }

    (proj / "plan" / "beats.json").write_text(
        json.dumps({"duration": 3.0, "fps": 30, "frames": 90, "bounds": [0, 3.0], "scenes": [{"index": 1, "start": 0, "end": 3.0, "dur": 3.0, "frames": 90}]}),
        encoding="utf-8",
    )
    (proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")

    root_tsx = f"""import React, {{useEffect, useLayoutEffect, useRef, useState}} from 'react';
import {{AbsoluteFill, Composition, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig}} from 'remotion';
import {{BRAND, PALETTE}} from './brand';
import {{FixedStage}} from './lib/FixedStage';
import {{DirectedText}} from './lib/DirectedText';
import {{auditLayout, collectDomLayoutBoxes, collectDomStageWindow}} from './lib/layout';

const STAGE_SPEC = {json.dumps(stage_spec)};
const TD = {json.dumps(td_doc)};
const COPY = {json.dumps(copy_map, ensure_ascii=False)};

type StageTestProps = {{ mode?: 'clean' | 'outside_win' | 'corner_clip' }};

const StageComp: React.FC<StageTestProps> = ({{mode = 'clean'}}) => {{
  const frame = useCurrentFrame();
  const {{fps, durationInFrames}} = useVideoConfig();
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [fontsReady, setFontsReady] = useState(false);
  const [fontGate] = useState(() => delayRender('Load Cairo font'));

  useEffect(() => {{
    Promise.all([
      new FontFace('Cairo', `url('${{staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}}')`, {{weight: '800'}}).load(),
      new FontFace('Cairo', `url('${{staticFile('fonts/Cairo/Cairo_700Bold.ttf')}}')`, {{weight: '700'}}).load(),
    ])
      .then((faces) => {{
        faces.forEach((f) => document.fonts.add(f));
        setFontsReady(true);
        continueRender(fontGate);
      }})
      .catch((e) => cancelRender(e));
  }}, [fontGate]);

  useLayoutEffect(() => {{
    if (!fontsReady || !rootRef.current) return;
    const boxes = collectDomLayoutBoxes(rootRef.current);
    const stageWin = collectDomStageWindow(rootRef.current);
    const issues = auditLayout(boxes, {{checkPlatformUi: true, stageWin}});
    if (issues.length > 0) {{
      cancelRender(
        new Error(`Remotion Stage Audit Failed: ${{issues.map((i) => `${{i.code}}: ${{i.message}}`).join('; ')}}`),
      );
    }}
  }}, [fontsReady, frame, mode]);

  const t = frame / fps;
  const contentStyle: React.CSSProperties =
    mode === 'outside_win'
      ? {{position: 'absolute', top: 680, left: 48, fontSize: 48, textAlign: 'left'}}
      : mode === 'corner_clip'
        ? {{position: 'absolute', top: 284, right: 104, fontSize: 44, textAlign: 'right'}}
        : {{position: 'absolute', top: 680, left: 180, right: 180, fontSize: 52, textAlign: 'center'}};

  return (
    <AbsoluteFill ref={{rootRef}}>
      <FixedStage
        spec={{STAGE_SPEC}}
        time={{t}}
        duration={{durationInFrames / fps}}
        direction={{TD}}
        copyById={{COPY}}
        over={{
          <DirectedText
            direction={{TD}}
            scene={{1}}
            role="label"
            elementId="cap-r-1"
            zone="caption"
            time={{t}}
            start={{0}}
            end={{3.0}}
            size={{46}}
            color={{PALETTE.paper}}
            style={{{{position: 'absolute', top: 1425, left: 140, right: 140, fontSize: 46, textAlign: 'center'}}}}
          >
            {{COPY['cap-r-1']}}
          </DirectedText>
        }}
      >
        <AbsoluteFill style={{{{backgroundColor: PALETTE.paper}}}}>
          <DirectedText
            direction={{TD}}
            scene={{1}}
            role="title"
            elementId="body-r-1"
            zone="content"
            time={{t}}
            start={{0}}
            end={{3.0}}
            size={{48}}
            color={{PALETTE.ink}}
            theme="light"
            style={{contentStyle}}
          >
            {{COPY['body-r-1']}}
          </DirectedText>
        </AbsoluteFill>
      </FixedStage>
    </AbsoluteFill>
  );
}};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="FixedStageRealTest"
    component={{StageComp}}
    durationInFrames={{90}}
    fps={{BRAND.fps}}
    width={{BRAND.width}}
    height={{BRAND.height}}
    defaultProps={{{{mode: 'clean'}}}}
  />
);
"""
    (proj / "src" / "Root.tsx").write_text(root_tsx, encoding="utf-8")

    # 1. Strict TypeScript check (`tsc --noEmit`) across FixedStage.tsx, stage.js, layout.tsx, and Root.tsx
    tsc = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "--noEmit"],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert tsc.returncode == 0, tsc.stdout + "\n" + tsc.stderr

    batch_e2 = _run_remotion_stills_batch(
        proj,
        env,
        [
            {"key": "full", "compId": "FixedStageRealTest", "frame": 6, "outPath": str(proj / "full.png"), "props": {"mode": "clean"}},
            {"key": "framed", "compId": "FixedStageRealTest", "frame": 48, "outPath": str(proj / "framed.png"), "props": {"mode": "clean"}},
            {"key": "l05", "compId": "FixedStageRealTest", "frame": 48, "outPath": str(proj / "bad_l05.png"), "props": {"mode": "outside_win"}},
            {"key": "l06", "compId": "FixedStageRealTest", "frame": 48, "outPath": str(proj / "bad_l06.png"), "props": {"mode": "corner_clip"}},
        ],
    )
    assert batch_e2["full"]["ok"], batch_e2["full"]["error"]
    im_full = np.asarray(Image.open(proj / "full.png").convert("RGB"))
    assert tuple(im_full[10, 10]) == (243, 242, 241)

    assert batch_e2["framed"]["ok"], batch_e2["framed"]["error"]
    im_framed = np.asarray(Image.open(proj / "framed.png").convert("RGB"))
    # Outside window & inside exterior rounded-corner lunas -> exact ink_shadow (#030303 -> RGB 3,3,3)
    assert tuple(im_framed[800, 50]) == (3, 3, 3)
    for cx, cy in ((106, 286), (974, 286), (106, 1274), (974, 1274)):
        assert tuple(im_framed[cy, cx]) == (3, 3, 3), f"Engine R rounded clip leaked at ({cx}, {cy}): {im_framed[cy, cx]}"
    # Interior of window -> bright paper (#F3F2F1)
    assert tuple(im_framed[500, 540]) == (243, 242, 241)
    # Unclipped OVER layer: progress bar (y=66), header (y~136), caption (y~1445)
    assert int(im_framed[66, 200, 0]) == 203
    assert int(im_framed[115:160, 260:820].max()) > 200
    assert int(im_framed[1420:1480, 260:820].max()) > 200

    # DOM Layout Audit in Chromium catches L05 (outside win(t)) and L06 (rounded-corner Arabic glyph clipping)
    assert not batch_e2["l05"]["ok"]
    assert "L05" in batch_e2["l05"]["error"]
    assert not batch_e2["l06"]["ok"]
    assert "L06" in batch_e2["l06"]["error"]
