"""Phase 2A - `plan/stage.json` handling when a project is scaffolded (category E, E3-E5).

E1/E2 in `test_fixed_stage_remotion.py` answer "does this engine draw the stage correctly". These
answer a different question: does a *generated* project get the stage spec applied without rewriting
its entrypoints, does `autowrap: false` stay out of the way, and does a legacy project without
`stage.json` render exactly like one that disables it. Scaffolding dominates the runtime, so keeping
them apart keeps the hard-failure surface smaller.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from fixed_stage_support import (
    ROOT,
    TOOLS,
    _run_remotion_stills_batch,
    _sample_direction,
    stage,
)
from PIL import Image

pytestmark = [pytest.mark.slow, pytest.mark.usefixtures("_cleanup_stage_tmp")]


# ===========================================================================
# E3-E5. Scaffolded / legacy projects and the plan/stage.json contract
# ===========================================================================


def test_e3_scaffolded_projects_auto_apply_plan_stage_json_without_rewriting_entrypoints(
    tmp_path: Path, _remotion_runtime
):
    """Scaffold fresh P, K, and R projects via `tools/new_project.py` and activate Fixed Stage
    purely via project plan/data files — without modifying any engine runtime entrypoint."""
    modules_dir, env = _remotion_runtime
    ff = shutil.which("ffmpeg", path=env["PATH"])
    assert ff is not None

    # ---- 1. Engine P scaffolded project (scenes.py untouched!) ----
    p_proj = tmp_path / "auto_p"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "auto-p", "--engine", "p", "--out", str(p_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    draft_stage = json.loads((p_proj / "plan" / "stage.json").read_text(encoding="utf-8"))
    assert draft_stage["enabled"] is False
    assert draft_stage["defaultFramedBox"] == {"x": 56, "y": 224, "w": 968, "h": 1096, "r": 36}

    scenes_py_before = hashlib.sha256((p_proj / "scenes.py").read_bytes()).hexdigest()
    from chunk_utils import build_signature  # noqa: PLC0415

    sig_disabled = build_signature(p_proj, p_proj / "assets", 45, 15, [0.0, 1.5], 30, 1080, 1920)

    p_beats = {
        "duration": 1.5,
        "fps": 30,
        "frames": 45,
        "bounds": [0.0, 1.5],
        "scenes": [{"index": 1, "start": 0.0, "end": 1.5, "dur": 1.5, "frames": 45, "theme": "dark"}],
    }
    p_copy = {
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "hdr-auto", "scene": 1, "role": "label", "text": "موضوع الحلقة: التفعيل التلقائي", "start": 0.5, "end": 1.45}
        ],
    }
    p_td = _sample_direction()
    # Engine K's example.js fills #030303, so UNDER="paper" (#F3F2F1) contrasts cleanly;
    # Engine P's scene1 (THEME[0]==0) & Engine R's MotionReel scene 0 are light scenes, so UNDER="ink_shadow" (#030303) contrasts cleanly!
    auto_stage_paper = {
        "version": 1,
        "enabled": True,
        "id": "auto-stage-k",
        "clock": "vo",
        "theme": "light",
        "defaultFramedBox": {"x": 56, "y": 224, "w": 968, "h": 1096, "r": 90},
        "under": {
            "surfaceRole": "paper",
            "background": None,
            "frame": {"enabled": False},
        },
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 0.3},
            {"mode": "transition", "from": "fullscreen", "to": "framed", "start": 0.3, "end": 0.7, "ease": "cubicInOut"},
            {"mode": "framed", "start": 0.7, "end": 1.5},
        ],
        "over": {
            "progressBar": {"enabled": True, "y": 64, "height": 8, "marginX": 60, "trackRole": "ink", "trackAlpha": 0.18, "fillRole": "red"},
            "header": {
                "enabled": True,
                "slots": [
                    {
                        "id": "hdr-auto-slot",
                        "scene": 1,
                        "copyId": "hdr-auto",
                        "role": "label",
                        "start": 0.5,
                        "end": 1.45,
                        "x": 540,
                        "y": 136,
                        "size": 38,
                        "maxWidth": 880,
                        "colorRole": "ink",
                    }
                ],
            },
            "captions": {"enabled": True, "y": 1455},
        },
    }
    auto_stage_dark = {
        **auto_stage_paper,
        "id": "auto-stage-pr",
        "theme": "dark",
        "under": {"surfaceRole": "ink_shadow", "background": None, "frame": {"enabled": False}},
        "over": {
            "progressBar": {"enabled": True, "y": 64, "height": 8, "marginX": 60, "trackRole": "paper", "trackAlpha": 0.2, "fillRole": "red"},
            "header": {
                "enabled": True,
                "slots": [
                    {
                        "id": "hdr-auto-dark",
                        "scene": 1,
                        "copyId": "hdr-auto",
                        "role": "label",
                        "start": 0.5,
                        "end": 1.45,
                        "x": 540,
                        "y": 136,
                        "size": 38,
                        "maxWidth": 880,
                        "colorRole": "paper",
                    }
                ],
            },
            "captions": {"enabled": False, "y": 1455},
        },
    }
    (p_proj / "plan" / "beats.json").write_text(json.dumps(p_beats), encoding="utf-8")
    (p_proj / "plan" / "copy.json").write_text(json.dumps(p_copy, ensure_ascii=False), encoding="utf-8")
    (p_proj / "plan" / "text-direction.json").write_text(json.dumps(p_td), encoding="utf-8")
    (p_proj / "plan" / "stage.json").write_text(json.dumps(auto_stage_dark), encoding="utf-8")

    sig_enabled = build_signature(p_proj, p_proj / "assets", 45, 15, [0.0, 1.5], 30, 1080, 1920)
    assert sig_enabled != sig_disabled, "Modifying plan/stage.json must invalidate Engine P chunk cache signature"
    assert hashlib.sha256((p_proj / "scenes.py").read_bytes()).hexdigest() == scenes_py_before

    p_seg = p_proj / "out" / "auto_p.mp4"
    p_run = subprocess.run(
        [
            sys.executable, str(TOOLS / "render_p_segment.py"),
            "--project", str(p_proj),
            "--from-frame", "0", "--to-frame", "36",
            "--out", str(p_seg),
            "--ffmpeg", ff,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert p_run.returncode == 0, p_run.stdout + "\n" + p_run.stderr
    assert hashlib.sha256((p_proj / "scenes.py").read_bytes()).hexdigest() == scenes_py_before

    import av  # noqa: PLC0415

    with av.open(str(p_seg)) as container:
        decoded_p = [f.to_ndarray(format="rgb24") for f in container.decode(video=0)]
    assert len(decoded_p) == 36
    # Frame 3 (t=0.10s, fullscreen): corner (10, 10) is scene1's light background (>190 luma)
    assert int(decoded_p[3][10, 10].min()) > 190
    # Frame 30 (t=1.00s, framed x=56..1024, y=224..1320, r=90): exterior (20, 700) & corner luna (62, 230) -> UNDER ink_shadow (<15)
    assert int(decoded_p[30][700, 20].max()) < 15
    assert int(decoded_p[30][230, 62].max()) < 15
    # OVER progress bar (y=66, x=150) -> RED, and OVER header (y=115..160) has bright paper glyphs (>200) on dark UNDER!
    assert int(decoded_p[30][66, 150, 0]) > 180 and int(decoded_p[30][66, 150, 2]) < 60
    assert int(decoded_p[30][115:160, 260:820].max()) > 200

    # ---- 2. Engine K scaffolded project (src/main.js, src/data.js & src/scenes/*.js ALL untouched!) ----
    k_proj = tmp_path / "auto_k"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "auto-k", "--engine", "k", "--out", str(k_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    k_main_before = hashlib.sha256((k_proj / "src" / "main.js").read_bytes()).hexdigest()
    k_data_before = hashlib.sha256((k_proj / "src" / "data.js").read_bytes()).hexdigest()
    k_scene_before = hashlib.sha256((k_proj / "src" / "scenes" / "example.js").read_bytes()).hexdigest()

    (k_proj / "plan" / "beats.json").write_text(json.dumps(p_beats), encoding="utf-8")
    (k_proj / "plan" / "copy.json").write_text(json.dumps(p_copy, ensure_ascii=False), encoding="utf-8")
    (k_proj / "plan" / "text-direction.json").write_text(json.dumps(p_td), encoding="utf-8")
    (k_proj / "plan" / "stage.json").write_text(json.dumps(auto_stage_paper), encoding="utf-8")

    k_frames = k_proj / "cache" / "auto-k-frames"
    k_res = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "1.2", "--fps", "30", "--jpg", "--out", str(k_frames)],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_res.returncode == 0, k_res.stdout + "\n" + k_res.stderr
    assert hashlib.sha256((k_proj / "src" / "main.js").read_bytes()).hexdigest() == k_main_before
    assert hashlib.sha256((k_proj / "src" / "data.js").read_bytes()).hexdigest() == k_data_before
    assert hashlib.sha256((k_proj / "src" / "scenes" / "example.js").read_bytes()).hexdigest() == k_scene_before

    k_full = np.asarray(Image.open(k_frames / "00003.jpg").convert("RGB"))
    k_framed = np.asarray(Image.open(k_frames / "00030.jpg").convert("RGB"))
    # Frame 3 (t=0.10s, fullscreen): example.js fills #030303 -> corner (10, 10) is dark (<20)
    assert int(k_full[10, 10].max()) < 20
    # Frame 30 (t=1.00s, framed r=90): exterior (20, 700) & rounded-corner luna (62, 230) -> UNDER paper (>230), interior (540, 500) -> dark (<20)
    assert int(k_framed[700, 20].min()) > 230
    assert int(k_framed[230, 62].min()) > 230
    assert int(k_framed[500, 540].max()) < 20
    assert int(k_framed[66, 150, 0]) > 180 and int(k_framed[66, 150, 2]) < 50
    assert int(k_framed[115:160, 260:820].min()) < 80

    # ---- 3. Engine R scaffolded project (src/RemotionRoot.tsx, src/Root.tsx, src/index.ts untouched!) ----
    r_proj = tmp_path / "auto_r"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "auto-r", "--engine", "r", "--out", str(r_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (r_proj / "node_modules").symlink_to(modules_dir, target_is_directory=True)
    r_root_before = hashlib.sha256((r_proj / "src" / "RemotionRoot.tsx").read_bytes()).hexdigest()
    r_entry_before = hashlib.sha256((r_proj / "src" / "Root.tsx").read_bytes()).hexdigest()

    (r_proj / "plan" / "beats.json").write_text(json.dumps(p_beats), encoding="utf-8")
    (r_proj / "plan" / "copy.json").write_text(json.dumps(p_copy, ensure_ascii=False), encoding="utf-8")
    (r_proj / "plan" / "text-direction.json").write_text(json.dumps(p_td), encoding="utf-8")
    (r_proj / "plan" / "stage.json").write_text(json.dumps(auto_stage_dark), encoding="utf-8")

    # Replace data.ts placeholder copy cards (standard data configuration required by render.mjs)
    data_ts = (r_proj / "src" / "data.ts").read_text(encoding="utf-8")
    for old_s, new_s in (
        ("اكتب عنوان المشهد", "عنوان المشهد الأول"),
        ("حط هنا الجملة الأساسية اللي عايز المشاهد يفتكرها.", "جملة أساسية واضحة داخل النافذة."),
    ):
        data_ts = data_ts.replace(old_s, new_s)
    (r_proj / "src" / "data.ts").write_text(data_ts, encoding="utf-8")

    tsc_r = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "--noEmit"],
        cwd=r_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert tsc_r.returncode == 0, tsc_r.stdout + "\n" + tsc_r.stderr

    batch_e3 = _run_remotion_stills_batch(
        r_proj,
        env,
        [
            {"key": "full", "compId": "MedoReel", "frame": 3, "outPath": str(r_proj / "r_auto_full.png")},
            {"key": "framed", "compId": "MedoReel", "frame": 30, "outPath": str(r_proj / "r_auto_framed.png")},
        ],
    )
    assert batch_e3["full"]["ok"], batch_e3["full"]["error"]
    assert batch_e3["framed"]["ok"], batch_e3["framed"]["error"]

    assert hashlib.sha256((r_proj / "src" / "RemotionRoot.tsx").read_bytes()).hexdigest() == r_root_before
    assert hashlib.sha256((r_proj / "src" / "Root.tsx").read_bytes()).hexdigest() == r_entry_before

    r_im_full = np.asarray(Image.open(r_proj / "r_auto_full.png").convert("RGB"))
    r_im_framed = np.asarray(Image.open(r_proj / "r_auto_framed.png").convert("RGB"))
    # Frame 3 (t=0.10s, fullscreen): corner (10, 10) is MotionReel's light paper gradient (>230)
    assert int(r_im_full[10, 10].min()) > 230
    # Frame 30 (t=1.00s, framed r=90): exterior (20, 700) & rounded-corner luna (62, 230) -> exact UNDER #030303 (3,3,3)!
    assert tuple(r_im_framed[700, 20]) == (3, 3, 3)
    assert tuple(r_im_framed[230, 62]) == (3, 3, 3)
    # Interior (540, 300) has bright MotionReel content, and OVER progress bar + header are unclipped!
    assert int(r_im_framed[300, 540].min()) > 200
    assert tuple(r_im_framed[66, 150]) == (203, 39, 27)
    assert int(r_im_framed[115:160, 260:820].max()) > 200


def test_e4_autowrap_false_prevents_double_wrapping_and_preserves_manual_stage_p_k_r(
    tmp_path: Path, _remotion_runtime
):
    """Explicitly verify `autoWrap: false` across Engines P, K, and R:
    1) Default runtime entrypoints do NOT auto-wrap when `plan/stage.json` sets `enabled: true, autoWrap: false`.
    2) Manual Fixed Stage invocation works cleanly with ZERO double-wrapping (verified geometrically via
       a wider manual window `x=80..1000` vs `plan/stage.json`'s narrower `x=220..860` window).
    """
    modules_dir, env = _remotion_runtime
    td_doc = _sample_direction()
    beats_doc = {
        "duration": 1.0,
        "fps": 30,
        "frames": 30,
        "bounds": [0.0, 1.0],
        "scenes": [{"index": 1, "start": 0.0, "end": 1.0, "dur": 1.0, "frames": 30, "theme": "light"}],
    }
    copy_doc = {
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "manual-title", "scene": 1, "role": "title", "text": "تحكم يدوي بدون تغليف مزدوج", "start": 0.0, "end": 1.0}
        ],
    }
    # Narrow box in plan/stage.json (x=220..860) with enabled=true, autoWrap=false
    plan_stage_no_autowrap = {
        "version": 1,
        "enabled": True,
        "autoWrap": False,
        "id": "plan-narrow-no-autowrap",
        "clock": "vo",
        "mode": "framed",
        "theme": "dark",
        "defaultFramedBox": {"x": 220, "y": 360, "w": 640, "h": 900, "r": 40},
        "under": {"surfaceRole": "ink_shadow", "background": None, "frame": {"enabled": False}},
    }
    # Wider box used by manual Fixed Stage invocation (x=80..1000)
    manual_wider_stage = {
        "version": 1,
        "enabled": True,
        "id": "manual-wider-stage",
        "clock": "vo",
        "mode": "framed",
        "theme": "dark",
        "defaultFramedBox": {"x": 80, "y": 240, "w": 920, "h": 1060, "r": 40},
        "under": {"surfaceRole": "ink_shadow", "background": None, "frame": {"enabled": False}},
        "over": {"progressBar": {"enabled": False}, "header": {"enabled": False}, "captions": {"enabled": False}},
    }

    # --- 1. Engine P ---
    p_proj = tmp_path / "autowrap_p"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "autowrap-p", "--engine", "p", "--out", str(p_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (p_proj / "plan" / "beats.json").write_text(json.dumps(beats_doc), encoding="utf-8")
    (p_proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (p_proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (p_proj / "plan" / "stage.json").write_text(json.dumps(plan_stage_no_autowrap), encoding="utf-8")

    assert stage.load_project_stage(p_proj) is None
    manual_bundle = stage.load_project_stage(p_proj, include_manual=True)
    assert manual_bundle is not None
    assert manual_bundle["spec"]["autoWrap"] is False
    assert manual_bundle["spec"]["defaultFramedBox"]["x"] == 220.0

    # 1a. Unedited scenes.py does NOT auto-wrap when autoWrap=False
    p_unwrapped_png = p_proj / "p_unwrapped.png"
    p_res1 = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from PIL import Image; import scenes; "
            f"Image.fromarray(scenes.render_frame(0.5)).save({str(p_unwrapped_png)!r})",
        ],
        cwd=p_proj,
        env={**env, "REEL_DIR": str(p_proj)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert p_res1.returncode == 0, p_res1.stdout + "\n" + p_res1.stderr
    p_im_unwrapped = np.asarray(Image.open(p_unwrapped_png).convert("RGB"))
    assert int(p_im_unwrapped[10, 10].min()) > 200  # light scene1 corner, NOT #030303

    # 1b. Manual Fixed Stage wrapper around scenes.render_frame(t) applies wider box once (no double-wrap!)
    p_manual_png = p_proj / "p_manual.png"
    p_res2 = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json; from PIL import Image; import scenes, stage; "
            f"ms = json.loads({json.dumps(manual_wider_stage)!r}); "
            "fr = stage.render_fixed_stage(ms, 0.5, lambda ts, _st: scenes.render_frame(ts)); "
            f"Image.fromarray(fr).save({str(p_manual_png)!r})",
        ],
        cwd=p_proj,
        env={**env, "REEL_DIR": str(p_proj)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert p_res2.returncode == 0, p_res2.stdout + "\n" + p_res2.stderr
    p_im_manual = np.asarray(Image.open(p_manual_png).convert("RGB"))
    assert tuple(p_im_manual[700, 40]) == (3, 3, 3)  # Outside manual box (x=40 < 80) -> #030303
    assert int(p_im_manual[700, 140].max()) > 180  # Inside manual box (80 < 140 < 220), NOT clipped to #030303!

    # --- 2. Engine K ---
    k_proj = tmp_path / "autowrap_k"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "autowrap-k", "--engine", "k", "--out", str(k_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (k_proj / "plan" / "beats.json").write_text(json.dumps(beats_doc), encoding="utf-8")
    (k_proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (k_proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (k_proj / "plan" / "stage.json").write_text(json.dumps(plan_stage_no_autowrap), encoding="utf-8")
    (k_proj / "src" / "data.js").write_text(
        "export const W = 1080, H = 1920, FPS = 30;\n"
        "export const scenes = [{ id: 's1', start: 0, end: 1.0 }];\n"
        "export const DURATION = 1.0;\n",
        encoding="utf-8",
    )

    # 2a. Scene WITHOUT manualFixedStage does NOT get auto-wrapped when autoWrap=false
    (k_proj / "src" / "scenes" / "s1.js").write_text(
        """import { PALETTE } from '../lib/brand.js';
export const supportsReducedMotion = true;
export async function draw(ctx, _lt, { W, H, stageSpec }) {
  if (!stageSpec || stageSpec.defaultFramedBox.x !== 220) {
    throw new Error('Expected loaded stageSpec with x=220 to be passed to manual scene');
  }
  ctx.fillStyle = PALETTE.paper;
  ctx.fillRect(0, 0, W, H);
}
""",
        encoding="utf-8",
    )
    k_unwrap_out = k_proj / "cache" / "k_unwrapped"
    k_res1 = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.2", "--fps", "30", "--jpg", "--out", str(k_unwrap_out)],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_res1.returncode == 0, k_res1.stdout + "\n" + k_res1.stderr
    k_im_unwrap = np.asarray(Image.open(k_unwrap_out / "00003.jpg").convert("RGB"))
    assert int(k_im_unwrap[10, 10].min()) > 220

    # 2b. Manual Fixed Stage inside s1.js (STILL without `manualFixedStage = true`!) works with zero double-wrapping
    (k_proj / "src" / "scenes" / "s1.js").write_text(
        f"""import {{ renderFixedStage }} from '../lib/stage-canvas.js';
import {{ drawDirectedText, useDirectedFonts }} from '../lib/captions.js';
import {{ PALETTE }} from '../lib/brand.js';

export const supportsReducedMotion = true;
const MANUAL_SPEC = {json.dumps(manual_wider_stage)};

export async function init() {{
  const r = await fetch('/plan/text-direction.json');
  await useDirectedFonts(await r.json(), 1);
}}

export async function draw(ctx, localT, {{ W, H, t, direction, copyById, motionMode }}) {{
  await renderFixedStage(ctx, MANUAL_SPEC, t, {{
    duration: 1.0,
    direction,
    copyById,
    motionMode,
    drawContent: (c) => {{
      c.fillStyle = PALETTE.paper;
      c.fillRect(0, 0, W, H);
      drawDirectedText(c, copyById['manual-title'], {{
        direction, scene: 1, role: 'title', elementId: 'manual-title',
        time: localT, start: 0, end: 1.0, x: 540, y: 740, size: 48,
        color: PALETTE.ink, theme: 'light', shadow: 'transparent',
      }});
    }},
  }});
}}
""",
        encoding="utf-8",
    )
    k_audit_out = k_proj / "cache" / "k_manual_audit"
    k_audit = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.4", "--fps", "30", "--audit", "--replay", "--out", str(k_audit_out)],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_audit.returncode == 0, k_audit.stdout + "\n" + k_audit.stderr

    k_manual_out = k_proj / "cache" / "k_manual_frames"
    k_res2 = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.2", "--fps", "30", "--jpg", "--out", str(k_manual_out)],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_res2.returncode == 0, k_res2.stdout + "\n" + k_res2.stderr
    k_im_manual = np.asarray(Image.open(k_manual_out / "00003.jpg").convert("RGB"))
    assert int(k_im_manual[700, 40].max()) <= 12  # Outside manual box -> #030303
    assert int(k_im_manual[700, 140].min()) > 220  # Inside manual box (x=140), NOT clipped by plan/stage.json (x=220..860)!

    # --- 3. Engine R ---
    r_proj = tmp_path / "autowrap_r"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "autowrap-r", "--engine", "r", "--out", str(r_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (r_proj / "node_modules").symlink_to(modules_dir, target_is_directory=True)
    (r_proj / "plan" / "beats.json").write_text(json.dumps(beats_doc), encoding="utf-8")
    (r_proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (r_proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (r_proj / "plan" / "stage.json").write_text(json.dumps(plan_stage_no_autowrap), encoding="utf-8")

    # Add a second composition `ManualStageReel` in Root.tsx that wraps `<MotionReel />` manually in `<FixedStage>`
    (r_proj / "src" / "Root.tsx").write_text(
        f"""import React from 'react';
import {{Composition, useCurrentFrame, useVideoConfig}} from 'remotion';
import {{BRAND}} from './brand';
import {{DURATION_IN_FRAMES, DURATION_SECONDS, IS_PREVIEW_TIMELINE}} from './data';
import {{MotionReel, STAGE_PLAN}} from './RemotionRoot';
import {{FixedStage}} from './lib/FixedStage';

const MANUAL_SPEC = {json.dumps(manual_wider_stage)};

const ManualWrappedReel: React.FC = () => {{
  const frame = useCurrentFrame();
  const {{fps}} = useVideoConfig();
  if (!STAGE_PLAN || STAGE_PLAN.defaultFramedBox?.x !== 220) {{
    throw new Error('Expected STAGE_PLAN with x=220 to remain accessible');
  }}
  return (
    <FixedStage spec={{MANUAL_SPEC}} time={{frame / fps}} duration={{DURATION_SECONDS}}>
      <MotionReel />
    </FixedStage>
  );
}};

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="MedoReel"
      component={{MotionReel}}
      durationInFrames={{DURATION_IN_FRAMES}}
      fps={{BRAND.fps}}
      width={{BRAND.width}}
      height={{BRAND.height}}
      defaultProps={{{{audioFile: null, previewOnly: IS_PREVIEW_TIMELINE, motionMode: 'normal'}}}}
    />
    <Composition
      id="ManualStageReel"
      component={{ManualWrappedReel}}
      durationInFrames={{DURATION_IN_FRAMES}}
      fps={{BRAND.fps}}
      width={{BRAND.width}}
      height={{BRAND.height}}
    />
  </>
);
""",
        encoding="utf-8",
    )

    tsc_r = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "--noEmit"],
        cwd=r_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert tsc_r.returncode == 0, tsc_r.stdout + "\n" + tsc_r.stderr

    batch_e4 = _run_remotion_stills_batch(
        r_proj,
        env,
        [
            {"key": "unwrap", "compId": "MedoReel", "frame": 10, "outPath": str(r_proj / "r_unwrapped.png")},
            {"key": "manual", "compId": "ManualStageReel", "frame": 10, "outPath": str(r_proj / "r_manual.png")},
        ],
    )
    assert batch_e4["unwrap"]["ok"], batch_e4["unwrap"]["error"]
    assert batch_e4["manual"]["ok"], batch_e4["manual"]["error"]

    r_im_unwrap = np.asarray(Image.open(r_proj / "r_unwrapped.png").convert("RGB"))
    r_im_manual = np.asarray(Image.open(r_proj / "r_manual.png").convert("RGB"))
    assert int(r_im_unwrap[10, 10].min()) > 230  # Default MotionReel NOT wrapped when autoWrap=false
    assert tuple(r_im_manual[700, 40]) == (3, 3, 3)  # Manual FixedStage IS active outside x=80..1000
    assert int(r_im_manual[700, 140].max()) > 180  # Inside manual box (x=140), NOT double-wrapped to #030303!


def test_e5_legacy_projects_without_stage_json_and_enabled_false_equivalence(
    tmp_path: Path, _remotion_runtime
):
    """Verify two critical backward-compatibility guarantees across P, K, R, and reel_lint.py:
    1) Legacy projects that do NOT have `plan/stage.json` at all work out-of-the-box with zero migration
       (including Engine R `tsc --noEmit` and `@remotion/bundler` compilation).
    2) New projects with `plan/stage.json` set to `enabled: false` produce 100% pixel-identical output
       to legacy projects without `plan/stage.json`.
    """
    modules_dir, env = _remotion_runtime
    td_doc = _sample_direction()
    beats_doc = {
        "duration": 1.0,
        "fps": 30,
        "frames": 30,
        "bounds": [0.0, 1.0],
        "scenes": [{"index": 1, "start": 0.0, "end": 1.0, "dur": 1.0, "frames": 30, "theme": "light"}],
    }
    copy_doc = {
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "leg-title", "scene": 1, "role": "title", "text": "توافق المشاريع القديمة والجديدة", "start": 0.0, "end": 1.0}
        ],
    }

    # --- 0. reel_lint.py on legacy fixture (no stage.json) vs enabled:false ---
    lint_legacy = tmp_path / "lint_legacy"
    shutil.copytree(ROOT / "tests" / "fixtures" / "reel" / "good", lint_legacy)
    assert not (lint_legacy / "plan" / "stage.json").exists()
    lint_res_leg = subprocess.run(
        [sys.executable, str(TOOLS / "reel_lint.py"), str(lint_legacy)],
        capture_output=True,
        text=True,
    )
    assert lint_res_leg.returncode == 0, lint_res_leg.stdout + "\n" + lint_res_leg.stderr

    # --- 1. Engine P: enabled:false == legacy missing plan/stage.json ---
    p_proj = tmp_path / "compat_p"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "compat-p", "--engine", "p", "--out", str(p_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    # Even if mode is changed to 'framed', enabled: false must preserve 100% legacy behavior!
    p_stage_doc = json.loads((p_proj / "plan" / "stage.json").read_text(encoding="utf-8"))
    assert p_stage_doc["enabled"] is False
    p_stage_doc["mode"] = "framed"
    (p_proj / "plan" / "stage.json").write_text(json.dumps(p_stage_doc), encoding="utf-8")

    p_disabled_png = p_proj / "p_disabled.png"
    p_legacy_png = p_proj / "p_legacy.png"
    for target_png, remove_stage in ((p_disabled_png, False), (p_legacy_png, True)):
        if remove_stage:
            (p_proj / "plan" / "stage.json").unlink()
            assert not (p_proj / "plan" / "stage.json").exists()
        res = subprocess.run(
            [
                sys.executable,
                "-c",
                "from PIL import Image; import scenes; "
                f"Image.fromarray(scenes.render_frame(0.4)).save({str(target_png)!r})",
            ],
            cwd=p_proj,
            env={**env, "REEL_DIR": str(p_proj)},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert res.returncode == 0, res.stdout + "\n" + res.stderr

    p_arr_disabled = np.asarray(Image.open(p_disabled_png).convert("RGB"))
    p_arr_legacy = np.asarray(Image.open(p_legacy_png).convert("RGB"))
    assert np.array_equal(p_arr_disabled, p_arr_legacy)
    assert int(p_arr_legacy[10, 10].min()) > 200

    # --- 2. Engine K: enabled:false == legacy missing plan/stage.json (+ --audit passes without 404) ---
    k_proj = tmp_path / "compat_k"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "compat-k", "--engine", "k", "--out", str(k_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (k_proj / "plan" / "beats.json").write_text(json.dumps(beats_doc), encoding="utf-8")
    (k_proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (k_proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (k_proj / "src" / "data.js").write_text(
        "export const W = 1080, H = 1920, FPS = 30;\n"
        "export const scenes = [{ id: 's1', start: 0, end: 1.0 }];\n"
        "export const DURATION = 1.0;\n",
        encoding="utf-8",
    )
    (k_proj / "src" / "scenes" / "s1.js").write_text(
        """import { drawDirectedText, useDirectedFonts } from '../lib/captions.js';
import { PALETTE } from '../lib/brand.js';
export const supportsReducedMotion = true;
export async function init() {
  const r = await fetch('/plan/text-direction.json');
  await useDirectedFonts(await r.json(), 1);
}
export async function draw(ctx, localT, { W, H, direction }) {
  ctx.fillStyle = PALETTE.paper;
  ctx.fillRect(0, 0, W, H);
  drawDirectedText(ctx, 'توافق المشاريع القديمة والجديدة', {
    direction, scene: 1, role: 'title', elementId: 'leg-title',
    time: localT, start: 0, end: 1.0, x: 540, y: 740, size: 48,
    color: PALETTE.ink, theme: 'light', shadow: 'transparent',
  });
}
""",
        encoding="utf-8",
    )

    k_dis_out = k_proj / "cache" / "k_disabled"
    k_dis_res = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.2", "--fps", "30", "--jpg", "--out", str(k_dis_out)],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_dis_res.returncode == 0, k_dis_res.stdout + "\n" + k_dis_res.stderr

    # Delete plan/stage.json to simulate legacy Engine K project
    (k_proj / "plan" / "stage.json").unlink()
    k_leg_audit = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.2", "--fps", "30", "--audit", "--out", str(k_proj / "cache" / "k_leg_audit")],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_leg_audit.returncode == 0, k_leg_audit.stdout + "\n" + k_leg_audit.stderr

    k_leg_out = k_proj / "cache" / "k_legacy"
    k_leg_res = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.2", "--fps", "30", "--jpg", "--out", str(k_leg_out)],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_leg_res.returncode == 0, k_leg_res.stdout + "\n" + k_leg_res.stderr
    assert (k_dis_out / "00003.jpg").read_bytes() == (k_leg_out / "00003.jpg").read_bytes()

    # --- 3. Engine R: enabled:false == legacy missing plan/stage.json (tsc + bundler + pixel equality!) ---
    r_proj = tmp_path / "compat_r"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "compat-r", "--engine", "r", "--out", str(r_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (r_proj / "node_modules").symlink_to(modules_dir, target_is_directory=True)
    (r_proj / "plan" / "beats.json").write_text(json.dumps(beats_doc), encoding="utf-8")
    (r_proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (r_proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")

    # 3a. With scaffolded plan/stage.json (enabled: false)
    tsc_dis = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "--noEmit"],
        cwd=r_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert tsc_dis.returncode == 0, tsc_dis.stdout + "\n" + tsc_dis.stderr
    batch_dis = _run_remotion_stills_batch(
        r_proj,
        env,
        [{"key": "dis", "compId": "MedoReel", "frame": 10, "outPath": str(r_proj / "r_disabled.png")}],
    )
    assert batch_dis["dis"]["ok"], batch_dis["dis"]["error"]

    # 3b. Delete plan/stage.json completely -> legacy Engine R project without plan/stage.json!
    # Exercise `scripts/launch-remotion.mjs still` CLI end-to-end here too!
    (r_proj / "plan" / "stage.json").unlink()
    assert not (r_proj / "plan" / "stage.json").exists()

    tsc_leg = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "--noEmit"],
        cwd=r_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert tsc_leg.returncode == 0, tsc_leg.stdout + "\n" + tsc_leg.stderr
    st_leg = subprocess.run(
        [
            "node", "scripts/launch-remotion.mjs", "still", "src/index.ts",
            "MedoReel", str(r_proj / "r_legacy.png"), "--frame=10", "--log=error",
        ],
        cwd=r_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert st_leg.returncode == 0, st_leg.stdout + "\n" + st_leg.stderr

    r_arr_dis = np.asarray(Image.open(r_proj / "r_disabled.png").convert("RGB"))
    r_arr_leg = np.asarray(Image.open(r_proj / "r_legacy.png").convert("RGB"))
    assert np.array_equal(r_arr_dis, r_arr_leg)
    assert int(r_arr_leg[10, 10].min()) > 230


# ===========================================================================
# F. Determinism, Reverse-Seek & Engine P Chunked Rendering Tests
# ===========================================================================
