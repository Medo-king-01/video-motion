"""Real Remotion renders for the Machine Explainer kit (Engine R, persistent Chromium).

Split out of `test_machine_explainer.py`, which keeps the spec/validation/parity half: these two
tests need `npm ci`, a bundled webpack graph and a live Chromium, and they are the only reason that
file pulled the Remotion runtime fixture in. Both share the module-scoped fixture below, so keeping
them together means one browser boot instead of two.

The builder helpers `_run_remotion` / `_make_remotion_project` moved too: nothing on the spec side
calls them.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "medo-motion"
TOOLS = ROOT / "tools"


def _run_remotion(command, cwd, env):
    """Run the Remotion launcher, retrying once on its transient bundler 404.

    Under `pytest -n 2` the bundler occasionally serves the studio before the webpack bundle
    directory exists ("The requested path (/tmp/remotion-webpack-bundle-…/index.html) could not
    be found"); a second launch rebuilds it. Only that marker is retried — a layout failure or a
    real render error must fail the test on the first attempt.
    """
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=180)
    output = result.stdout + "\n" + result.stderr
    transient = "remotion-webpack-bundle" in output and "could not be found" in output
    if result.returncode != 0 and transient:
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=180)
    return result

@pytest.fixture(scope="module")
def _remotion_runtime(tmp_path_factory):
    """Prepare Remotion node_modules + shared Chromium once for real Engine R renders."""
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    chrom_proc = subprocess.run(
        ["node", str(TOOLS / "chromium.mjs"), "--json"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if chrom_proc.returncode != 0:
        pytest.skip(f"Chromium unavailable: {chrom_proc.stderr}")
    chrom = json.loads(chrom_proc.stdout)

    env_mods = os.environ.get("MEDO_REMOTION_TEST_NODE_MODULES")
    if env_mods and Path(env_mods).is_dir():
        modules_dir = Path(env_mods).resolve()
    else:
        if shutil.which("npm") is None:
            pytest.skip("npm is not installed and MEDO_REMOTION_TEST_NODE_MODULES is unset")
        deps_dir = tmp_path_factory.mktemp("remotion_deps")
        rem_tpl = SKILL / "templates" / "remotion"
        shutil.copy2(rem_tpl / "package.json", deps_dir / "package.json")
        shutil.copy2(rem_tpl / "package-lock.json", deps_dir / "package-lock.json")
        ci_res = subprocess.run(
            ["npm", "ci", "--prefer-offline", "--no-audit", "--no-fund"],
            cwd=deps_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if ci_res.returncode != 0:
            pytest.skip(f"Remotion npm ci unavailable offline: {ci_res.stderr[:240]}")
        modules_dir = deps_dir / "node_modules"

    env = {
        **os.environ,
        "MEDO_TOOLKIT": str(ROOT / "tools" / "toolkit"),
        "MEDO_CHROMIUM": chrom["executablePath"],
        "REMOTION_BROWSER_EXECUTABLE": chrom["executablePath"],
    }
    if chrom.get("args"):
        env["REMOTION_CHROMIUM_ARGS"] = " ".join(chrom["args"])
    if chrom.get("libraryPath"):
        env["LD_LIBRARY_PATH"] = ":".join(
            [p for p in (chrom["libraryPath"], env.get("LD_LIBRARY_PATH")) if p]
        )
    return modules_dir, env


def _make_remotion_project(tmp_path: Path, modules_dir: Path, root_tsx: str) -> Path:
    proj = tmp_path / "r_proj"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "r-machine-test", "--engine", "r", "--out", str(proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (proj / "node_modules").symlink_to(modules_dir, target_is_directory=True)
    (proj / "plan" / "beats.json").write_text(
        json.dumps({"duration": 4.0, "fps": 30, "frames": 120, "bounds": [0, 4.0], "scenes": [{"index": 1, "start": 0, "end": 4.0, "dur": 4.0, "frames": 120}]}),
        encoding="utf-8",
    )
    valid_td = {
        "version": 3,
        "status": "directed",
        "decidedBy": "agent",
        "concept": "Remotion MachineDiagram real test direction",
        "scenes": [
            {
                "scene": 1,
                "captionStyle": "softfade",
                "captionWhy": "clean technical entry",
                "textStyles": {"title": "softfade", "body": "softfade", "label": "riseword"},
                "textWhy": "crisp Arabic label motion",
                "fontStyles": {
                    "title": {"family": "Cairo", "weight": 800},
                    "body": {"family": "Cairo", "weight": 700},
                    "label": {"family": "Cairo", "weight": 800},
                },
                "fontWhy": "Cairo bold technical Arabic",
            }
        ],
    }
    (proj / "plan" / "text-direction.json").write_text(json.dumps(valid_td), encoding="utf-8")
    font_dst = proj / "public" / "fonts" / "Cairo"
    font_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "assets" / "fonts" / "Cairo" / "Cairo_800ExtraBold.ttf", font_dst)
    (proj / "src" / "Root.tsx").write_text(root_tsx, encoding="utf-8")
    return proj


@pytest.mark.xdist_group("remotion-bundler")
def test_remotion_machine_diagram_real_render_active_and_inactive_states(tmp_path: Path, _remotion_runtime):
    from PIL import Image, ImageChops  # noqa: PLC0415

    modules_dir, env = _remotion_runtime
    spec = {
        "version": 1,
        "id": "r-real-nvme",
        "archetype": "nvme_ssd",
        "clock": "scene",
        "start": 0.0,
        "end": 3.2,
        "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.7},
        "sources": [{"id": "s1", "title": "NVM Express Base Specification 2.0d", "kind": "spec", "ref": "NVMe-2.0d"}],
        "steps": [
            {
                "id": "step-1",
                "evidence": "source",
                "sourceId": "s1",
                "locator": {"kind": "section", "value": "§3.1.2"},
                "quote": "Host submits queue entries over PCIe lanes to the controller.",
                "copyIds": ["c-1"],
                "timing": "sync",
                "anchor": {"word": 0, "text": "الكنترولر"},
                "start": 1.0,
                "end": 2.8,
                "activeTags": ["pcie_bus", "controller", "dram_cache"],
                "motion": {"kind": "packet_flow", "path": "pcie_to_controller", "tint": "intake"},
            }
        ],
    }
    td_doc = {
        "version": 3,
        "status": "directed",
        "decidedBy": "agent",
        "concept": "Real Remotion MachineDiagram verification",
        "scenes": [
            {
                "scene": 1,
                "captionStyle": "softfade",
                "captionWhy": "clean technical entry",
                "textStyles": {"label": "riseword"},
                "textWhy": "crisp Arabic label motion",
                "fontStyles": {"label": {"family": "Cairo", "weight": 800}},
                "fontWhy": "Cairo bold technical Arabic",
            }
        ],
    }
    copy_by_id = {"c-1": "بيانات PCIe بتدخل للكنترولر"}

    root_tsx = f"""import React, {{useEffect, useState}} from 'react';
import {{AbsoluteFill, Composition, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig}} from 'remotion';
import {{BRAND, PALETTE}} from './brand';
import {{MachineDiagram}} from './lib/MachineDiagram';

const SPEC = {json.dumps(spec)};
const TD = {json.dumps(td_doc)};
const COPY = {json.dumps(copy_by_id)};

const SceneComp: React.FC = () => {{
  const frame = useCurrentFrame();
  const {{fps}} = useVideoConfig();
  const [fontGate] = useState(() => delayRender('Load Cairo font'));
  useEffect(() => {{
    new FontFace('Cairo', `url('${{staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}}')`, {{weight: '800'}})
      .load()
      .then((f) => {{ document.fonts.add(f); continueRender(fontGate); }})
      .catch((e) => cancelRender(e));
  }}, [fontGate]);
  return (
    <AbsoluteFill style={{{{background: PALETTE.ink}}}}>
      <MachineDiagram
        spec={{SPEC}}
        time={{frame / fps}}
        direction={{TD}}
        scene={{1}}
        copyById={{COPY}}
        theme="dark"
        strictLayout
      />
    </AbsoluteFill>
  );
}};

export const RemotionRoot: React.FC = () => (
  <Composition id="MachineRealTest" component={{SceneComp}} durationInFrames={{120}} fps={{BRAND.fps}} width={{BRAND.width}} height={{BRAND.height}} />
);
"""
    proj = _make_remotion_project(tmp_path, modules_dir, root_tsx)

    # 1. Strict TypeScript check across MachineDiagram.tsx, DirectedText.tsx, layout.tsx, and Root.tsx
    tsc = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "--noEmit"],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert tsc.returncode == 0, tsc.stdout + "\n" + tsc.stderr

    def render_still(frame_idx: int, name: str) -> Image.Image:
        out_file = proj / name
        r = _run_remotion(
            [
                "node", "scripts/launch-remotion.mjs", "still", "src/index.ts",
                "MachineRealTest", str(out_file), f"--frame={frame_idx}", "--log=error",
            ],
            proj, env,
        )
        assert r.returncode == 0, r.stdout + "\n" + r.stderr
        return Image.open(out_file).convert("RGB")

    # Frame 9 (t=0.30s): inside opening reveal, BEFORE step-1 [1.0..2.8] -> geometry visible, callout absent
    im_pre = render_still(9, "pre.png")
    # Frame 48 (t=1.60s): step-1 ACTIVE -> geometry + packet_flow + DirectedText Arabic callout visible
    im_act1 = render_still(48, "active1.png")
    # Frame 57 (t=1.90s): step-1 ACTIVE later instant -> packet_flow dots moved deterministically
    im_act2 = render_still(57, "active2.png")
    # Frame 108 (t=3.60s): AFTER spec.end (3.2s) -> MachineDiagram inactive (returns null -> pure ink #0A0A0A)
    im_off = render_still(108, "inactive.png")

    # Verify inactive frame is pure #0A0A0A (RGB 10,10,10)
    assert im_off.getextrema() == ((10, 10), (10, 10), (10, 10))

    # Verify isometric geometry renders in both pre-step and active frames (diagram crop y=600..880)
    diag_pre = np.asarray(im_pre.crop((240, 600, 800, 880)))
    diag_act1 = np.asarray(im_act1.crop((240, 600, 800, 880)))
    assert int(diag_pre.max()) > 90
    assert int(diag_act1.max()) > 160
    # Active motion (packets + active part highlight) visibly changes diagram pixels between t=1.60s and t=1.90s
    assert ImageChops.difference(
        im_act1.crop((240, 600, 800, 880)),
        im_act2.crop((240, 600, 800, 880)),
    ).getbbox() is not None

    # Verify DirectedText Arabic callout is absent at t=0.30s and crisp at t=1.60s (callout crop y=900..1060)
    txt_pre = np.asarray(im_pre.crop((140, 900, 940, 1060)))
    txt_act = np.asarray(im_act1.crop((140, 900, 940, 1060)))
    assert int(txt_pre.max()) <= 12, "Callout region must be empty before step-1 starts"
    assert int(txt_act.max()) > 180, "DirectedText Arabic callout must render visible ink during active step"


@pytest.mark.xdist_group("remotion-bundler")
def test_remotion_layout_audit_catches_multiline_arabic_overflow_and_right_rail(tmp_path: Path, _remotion_runtime):
    modules_dir, env = _remotion_runtime
    spec = {
        "version": 1,
        "id": "r-layout-gate",
        "archetype": "nvme_ssd",
        "clock": "scene",
        "start": 0.0,
        "end": 3.0,
        "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.5},
        "sources": [{"id": "s1", "title": "NVM Express Base Specification 2.0d", "kind": "spec", "ref": "NVMe-2.0d"}],
        "steps": [
            {
                "id": "step-1",
                "evidence": "source",
                "sourceId": "s1",
                "locator": {"kind": "section", "value": "§3.1.2"},
                "quote": "Host submits queue entries over PCIe lanes to the controller.",
                "copyIds": ["c-1"],
                "timing": "sync",
                "anchor": {"word": 0, "text": "الكنترولر"},
                "start": 0.8,
                "end": 2.8,
                "activeTags": ["pcie_bus", "controller"],
                "motion": {"kind": "packet_flow", "path": "pcie_to_controller", "tint": "intake"},
            }
        ],
    }
    td_doc = {
        "version": 3,
        "status": "directed",
        "decidedBy": "agent",
        "concept": "Engine R Arabic layout gate verification",
        "scenes": [
            {
                "scene": 1,
                "captionStyle": "softfade",
                "captionWhy": "clean technical entry",
                "textStyles": {"label": "softfade"},
                "textWhy": "test wrapping and placement",
                "fontStyles": {"label": {"family": "Cairo", "weight": 800}},
                "fontWhy": "Cairo bold Arabic",
            }
        ],
    }

    root_tsx = f"""import React, {{useEffect, useLayoutEffect, useRef, useState}} from 'react';
import {{AbsoluteFill, Composition, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig}} from 'remotion';
import {{BRAND, PALETTE}} from './brand';
import {{MachineDiagram}} from './lib/MachineDiagram';
import {{auditLayout, collectDomLayoutBoxes, ProtectBox}} from './lib/layout';

const SPEC = {json.dumps(spec)};
const TD = {json.dumps(td_doc)};

type VariantProps = {{ mode?: 'safe_short' | 'wrap_overflow' | 'right_rail' | 'diagram_collide' | 'motion_shift' | 'face_overlap' }};

const GateComp: React.FC<VariantProps> = ({{mode = 'safe_short'}}) => {{
  const frame = useCurrentFrame();
  const {{fps}} = useVideoConfig();
  const stageRef = useRef<HTMLDivElement | null>(null);
  const [fontsReady, setFontsReady] = useState(false);
  const [fontGate] = useState(() => delayRender('Load Cairo font'));
  useEffect(() => {{
    new FontFace('Cairo', `url('${{staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}}')`, {{weight: '800'}})
      .load()
      .then((f) => {{ document.fonts.add(f); setFontsReady(true); continueRender(fontGate); }})
      .catch((e) => cancelRender(e));
  }}, [fontGate]);

  useLayoutEffect(() => {{
    if (mode !== 'face_overlap' || !fontsReady || !stageRef.current) return;
    const issues = auditLayout(collectDomLayoutBoxes(stageRef.current), {{checkPlatformUi: true}});
    if (issues.length > 0) {{
      cancelRender(
        new Error(
          `Remotion layout audit failed: ${{issues.map((i) => `${{i.code}}: ${{i.message}}`).join('; ')}}`,
        ),
      );
    }}
  }}, [mode, fontsReady, frame]);

  const copyText =
    mode === 'wrap_overflow'
      ? 'البيانات بتتنقل عبر خطوط PCIe السريعة مباشرة للكنترولر وبتتوزع بالتوازي على قنوات الذاكرة المدمجة في أكثر من سطر متتالي'
      : 'بيانات PCIe بتدخل للكنترولر';
  const calloutY =
    mode === 'wrap_overflow' ? 1235
    : mode === 'right_rail' ? 1150
    : mode === 'diagram_collide' ? 740
    : 1235;
  const calloutStyle: React.CSSProperties =
    mode === 'right_rail'
      ? {{textAlign: 'right'}}
      : mode === 'motion_shift'
        ? {{textAlign: 'center', transform: 'translateY(130px) scale(1.15)'}}
        : {{textAlign: 'center'}};

  return (
    <AbsoluteFill ref={{stageRef}} style={{{{background: PALETTE.ink}}}}>
      {{mode === 'face_overlap' ? (
        <ProtectBox id="presenter.face" kind="face" box={{{{x: 340, y: 1215, w: 400, h: 100}}}} />
      ) : null}}
      <MachineDiagram
        spec={{SPEC}}
        time={{frame / fps}}
        direction={{TD}}
        scene={{1}}
        copyById={{{{'c-1': copyText}}}}
        calloutY={{calloutY}}
        calloutStyle={{calloutStyle}}
        theme="dark"
        strictLayout={{mode !== 'face_overlap'}}
      />
    </AbsoluteFill>
  );
}};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="LayoutGateTest"
    component={{GateComp}}
    durationInFrames={{90}}
    fps={{BRAND.fps}}
    width={{BRAND.width}}
    height={{BRAND.height}}
    defaultProps={{{{mode: 'safe_short'}}}}
  />
);
"""
    proj = _make_remotion_project(tmp_path, modules_dir, root_tsx)

    def run_mode(mode: str):
        return _run_remotion(
            [
                "node", "scripts/launch-remotion.mjs", "still", "src/index.ts",
                "LayoutGateTest", str(proj / f"{mode}.png"),
                "--frame=48", f'--props={json.dumps({"mode": mode})}',
            ],
            proj, env,
        )

    # 1. Short single-line centered Arabic text at calloutY=1235 fits inside [200..1350] and x=[300..780] -> PASS
    r_ok = run_mode("safe_short")
    assert r_ok.returncode == 0, r_ok.stdout + "\n" + r_ok.stderr

    # 2. Long Arabic copy at the EXACT SAME calloutY=1235 wraps onto 3 lines past y=1350 -> FAIL L01!
    r_wrap = run_mode("wrap_overflow")
    combined_wrap = r_wrap.stdout + "\n" + r_wrap.stderr
    assert r_wrap.returncode != 0
    assert "Remotion layout audit failed" in combined_wrap and "L01" in combined_wrap, combined_wrap

    # 3. Right-aligned Arabic text at y=1150 extends into x=940..1040 -> FAIL L04 (PLATFORM_RIGHT_RAIL)!
    r_rail = run_mode("right_rail")
    combined_rail = r_rail.stdout + "\n" + r_rail.stderr
    assert r_rail.returncode != 0
    assert "Remotion layout audit failed" in combined_rail and "L04" in combined_rail, combined_rail

    # 4. Callout placed over the cutaway diagram (calloutY=740) -> FAIL L02 (keep-box collision)!
    r_col = run_mode("diagram_collide")
    combined_col = r_col.stdout + "\n" + r_col.stderr
    assert r_col.returncode != 0
    assert "Remotion layout audit failed" in combined_col and "L02" in combined_col, combined_col

    # 5. Transform/motion displacement pushing an otherwise-safe calloutY=1235 line past y=1350 -> FAIL L01!
    r_shift = run_mode("motion_shift")
    combined_shift = r_shift.stdout + "\n" + r_shift.stderr
    assert r_shift.returncode != 0
    assert "Remotion layout audit failed" in combined_shift and "L01" in combined_shift, combined_shift

    # 6. Text overlapping a protected presenter `face` box -> FAIL L03 (face overlap, distinct from L02)!
    r_face = run_mode("face_overlap")
    combined_face = r_face.stdout + "\n" + r_face.stderr
    assert r_face.returncode != 0
    assert (
        "Remotion layout audit failed" in combined_face
        and "L03" in combined_face
        and "presenter face box" in combined_face
    ), combined_face
