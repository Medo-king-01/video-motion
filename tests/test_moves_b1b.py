"""B1b: the first new element moves, with numbers that must agree in K, R and P.

`pixel-list` and `parallax` are pure functions: (status, time) -> numbers. The JS lives in
`shared/js/moves.js` (copied to K and R by `sync_shared_libs`), the Python mirror in
`procedural-reels/moves.py`, and the Canvas adapter in `render/lib/moves-render.js`. These tests
pin the behaviour, the JS/Python parity and the adapter's exact transforms, with a fake context
instead of a browser.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "medo-motion"

import importlib.util  # noqa: E402


def _load(name: str, path: Path):
    """Load a module under a unique name so `moves` (tools) and `moves` (engine P) coexist."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


pmoves = _load("p_reels_moves", SKILL / "templates" / "procedural-reels" / "moves.py")

SHARED = ROOT / "shared" / "js" / "moves.js"
K_COPY = SKILL / "templates" / "render" / "lib" / "moves.js"
R_COPY = SKILL / "templates" / "remotion" / "src" / "lib" / "moves.js"
ADAPTER = SKILL / "templates" / "render" / "lib" / "moves-render.js"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def node_json(body: str) -> object:
    """Run a module snippet against shared/js/moves.js and return its JSON output."""
    script = ("const m = await import('./shared/js/moves.js');\n"
              f"console.log(JSON.stringify((() => {{ return ({body}); }})()));")
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=str(ROOT),
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_the_engines_ship_the_same_move_source() -> None:
    canonical = SHARED.read_bytes()
    assert K_COPY.read_bytes() == canonical
    assert R_COPY.read_bytes() == canonical


@needs_node
def test_pixel_list_starts_hidden_and_settles_on_target() -> None:
    start = node_json("[m.pixelListItem(0, 0), m.pixelListItem(0, 5)]")
    assert start[0]["opacity"] == pytest.approx(0.0)
    assert start[0]["x"] > 0 and start[0]["y"] < 0
    assert start[1] == {"opacity": 1, "x": 0, "y": 0, "scale": 1, "pixelStep": 0.025}


@needs_node
def test_pixel_list_snaps_offsets_to_whole_pixels() -> None:
    states = node_json("[0, 0.07, 0.13, 0.21].map(t => m.pixelListItem(1, t, { fontSize: 40 }))")
    for state in states:
        for axis in ("x", "y"):
            pixels = state[axis] * 40
            assert abs(pixels - round(pixels)) < 1e-9, (axis, state)


@needs_node
def test_pixel_list_rejects_nonsense() -> None:
    errors = node_json("""(() => {
        const out = [];
        for (const call of [() => m.pixelListItem(-1, 0), () => m.pixelListItem(0, -1),
                            () => m.pixelListItem(0, 0, { enter: 0 }),
                            () => m.pixelListItem(1.5, 0)]) {
            try { call(); out.push('no-error'); } catch (e) { out.push(e.name); }
        }
        return out;
    })()""")
    assert errors == ["RangeError"] * 4


def test_python_mirror_rejects_nonsense() -> None:
    with pytest.raises(ValueError):
        pmoves.pixel_list_item(-1, 0)
    with pytest.raises(ValueError):
        pmoves.pixel_list_item(0, -1)
    with pytest.raises(ValueError):
        pmoves.pixel_list_item(0, 0, enter=0)


@needs_node
def test_parallax_depth_zero_is_pinned_and_one_follows_fully() -> None:
    states = node_json("[m.parallaxLayer(0, 0.5), m.parallaxLayer(1, 0.5), m.parallaxLayer(0.5, 0.5)]")
    assert states[0] == {"x": 0, "y": 0, "scale": 1}
    assert states[1]["x"] == pytest.approx(-0.4)
    assert states[2]["x"] == pytest.approx(-0.2)
    assert states[1]["scale"] == pytest.approx(1.02)


@needs_node
def test_parallax_progress_is_clamped_and_depth_is_validated() -> None:
    out = node_json("""(() => {
        const states = [m.parallaxLayer(1, -1), m.parallaxLayer(1, 2), m.parallaxLayer(1, 0.5)];
        let error = 'none';
        try { m.parallaxLayer(1.5, 0.5); } catch (e) { error = e.name; }
        return { states, error };
    })()""")
    assert out["states"][0]["x"] == 0
    assert out["states"][1]["x"] == pytest.approx(-0.8)
    assert out["error"] == "RangeError"


@needs_node
def test_camera_progress_is_monotone_and_clamped() -> None:
    values = node_json("[m.cameraProgress(-1, 0, 1), m.cameraProgress(0, 0, 1),"
                       " m.cameraProgress(0.5, 0, 1), m.cameraProgress(9, 0, 1)]")
    assert values[0] == 0 and values[1] == 0 and values[3] == 1
    assert 0 < values[2] < 1


@pytest.mark.parametrize("index, elapsed, font_size", [
    (0, 0.0, 40), (0, 0.2, 40), (3, 0.47, 40), (2, 1.5, 72), (4, 0.31, 96),
])
@needs_node
def test_js_and_python_agree_on_pixel_list(index: int, elapsed: float, font_size: int) -> None:
    js = node_json(f"m.pixelListItem({index}, {elapsed}, {{ fontSize: {font_size} }})")
    py = pmoves.pixel_list_item(index, elapsed, font_size=font_size)
    for key in ("opacity", "x", "y", "scale", "pixelStep"):
        assert js[key] == pytest.approx(py[key], abs=1e-9), key


@pytest.mark.parametrize("depth, progress", [(0, 0.3), (0.25, 0.5), (1, 0.9), (0.6, 0)])
@needs_node
def test_js_and_python_agree_on_parallax(depth: float, progress: float) -> None:
    js = node_json(f"m.parallaxLayer({depth}, {progress}, {{ panY: 0.4, zoom: 0.08 }})")
    py = pmoves.parallax_layer(depth, progress, pan_y=0.4, zoom=0.08)
    for key in ("x", "y", "scale"):
        assert js[key] == pytest.approx(py[key], abs=1e-9), key


FAKE_CTX = """
class Ctx {
  constructor() { this.ops = []; this.globalAlpha = 1; this.alphaSeen = []; }
  save() { this.ops.push(['save']); }
  restore() { this.ops.push(['restore']); }
  translate(x, y) { this.ops.push(['translate', x, y]); }
  scale(x, y) { this.ops.push(['scale', x, y]); }
}
"""


@needs_node
def test_the_list_adapter_sets_opacity_and_pixel_offset_per_row() -> None:
    script = f"""
    {FAKE_CTX}
    const adapters = await import('./medo-motion/templates/render/lib/moves-render.js');
    const ctx = new Ctx();
    const states = adapters.drawPixelList(ctx, ['a', 'b', 'c'], 0.3,
        {{ x: 100, y: 200, fontSize: 40, lineHeight: 1.5 }}, (c, item, state) => {{
            c.alphaSeen.push({{ item, alpha: c.globalAlpha }});
        }});
    console.log(JSON.stringify({{ states, ops: ctx.ops, alphaSeen: ctx.alphaSeen }}));
    """
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=str(ROOT),
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert len(out["states"]) == 3
    assert out["ops"].count(["save"]) == 3 and out["ops"].count(["restore"]) == 3
    translates = [op for op in out["ops"] if op[0] == "translate"]
    assert len(translates) == 3
    first, second = out["states"][0], out["states"][1]
    assert translates[0][1] == pytest.approx(100 + first["x"] * 40)
    assert translates[1][2] == pytest.approx(200 + 1.5 * 40 + second["y"] * 40)
    assert out["alphaSeen"][0]["alpha"] == pytest.approx(first["opacity"])


@needs_node
def test_the_parallax_adapter_scales_around_the_frame_centre() -> None:
    script = f"""
    {FAKE_CTX}
    const adapters = await import('./medo-motion/templates/render/lib/moves-render.js');
    const ctx = new Ctx();
    const states = adapters.drawParallax(ctx, [{{ depth: 1 }}, {{ depth: 0 }}], 0.5,
        {{ width: 1080, height: 1920, unit: 40 }}, () => {{}});
    console.log(JSON.stringify({{ states, ops: ctx.ops }}));
    """
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=str(ROOT),
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    translates = [op for op in out["ops"] if op[0] == "translate"]
    assert translates[0] == ["translate", 16, 0]
    assert translates[1] == ["translate", 540, 960]
    assert translates[2] == ["translate", -540, -960]


@needs_node
def test_the_adapters_refuse_a_missing_context_or_callback() -> None:
    script = """
    const adapters = await import('./medo-motion/templates/render/lib/moves-render.js');
    const out = [];
    for (const call of [() => adapters.drawPixelList(null, [], 0, {}, () => {}),
                        () => adapters.drawPixelList({ save(){}, restore(){}, translate(){} }, [], 0, {} , null),
                        () => adapters.drawParallax(null, [], 0, {}, () => {})]) {
        try { call(); out.push('no-error'); } catch (e) { out.push(e.name); }
    }
    console.log(JSON.stringify(out));
    """
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=str(ROOT),
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["TypeError", "TypeError", "TypeError"]


def test_the_registry_lists_the_new_family() -> None:
    registry = _load("moves_registry", ROOT / "tools" / "moves.py")
    data = registry.load()
    family = data["families"]["element-moves"]
    assert family["state"] == "executable"
    assert set(family["members"]) == {
        "pixel-list", "parallax", "orbit", "word-path", "explode", "mask-wipe",
        "data-count", "card-stack", "camera-push", "particle-burst"}
    summary = registry.audit(data)
    assert summary["families"]["element-moves"]["count"] == 10
    assert "element-moves" in summary["by_engine"]["K"]
    assert "element-moves" in summary["by_engine"]["P"]


@needs_node
def test_the_preview_sheet_is_byte_identical_across_runs(tmp_path: Path) -> None:
    out = [tmp_path / "a.html", tmp_path / "b.html"]
    for path in out:
        result = subprocess.run(["node", str(ROOT / "tools" / "moves_preview.mjs"), str(path)],
                                cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        assert path.is_file()
    first, second = (path.read_bytes() for path in out)
    assert first == second
    text = first.decode("utf-8")
    assert "pixel-list" in text and "parallax" in text
    assert "40 frames" in subprocess.run(
        ["node", str(ROOT / "tools" / "moves_preview.mjs"), str(tmp_path / "c.html")],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120).stdout


@pytest.mark.parametrize("call", [
    ("orbitItem", "orbit_item", (2, 0.7), {"count": 5, "radius": 1.4}),
    ("wordPathItem", "word_path_item", (1, 0.4), {"fromX": -1.5, "rotation": 6}),
    ("explodePart", "explode_part", (3, 0.9), {"count": 7, "hold": 0.2, "back": 0.4}),
    ("maskWipe", "mask_wipe", (0.3,), {"direction": "rtl", "feather": 0.1}),
    ("dataCount", "data_count", (0.4,), {"to": 250.5, "decimals": 2}),
    ("cardStackItem", "card_stack_item", (2, 0.5), {"spread": 0.25, "tilt": 4}),
    ("cameraPush", "camera_push", (0.6,), {"toScale": 1.2, "toX": 30}),
    ("particleBurst", "particle_burst", (5, 0.3), {"count": 12, "seed": 11}),
])
@needs_node
def test_js_and_python_agree_on_the_eight_new_moves(call) -> None:
    js_name, py_name, args, kwargs = call
    js_call = ", ".join([*(str(a) for a in args), json.dumps(kwargs)])
    js = node_json(f"m.{js_name}({js_call})")
    py = getattr(pmoves, py_name)(*args, **{_snake(key): value for key, value in kwargs.items()})
    for key in py:
        assert js[key] == pytest.approx(py[key], abs=1e-9), key


def _snake(name: str) -> str:
    out = "".join("_" + ch.lower() if ch.isupper() else ch for ch in name)
    return {"from_x": "from_x", "to_x": "to_x", "to_scale": "to_scale"}.get(out, out)


@needs_node
def test_orbit_is_periodic_and_depth_changes_scale() -> None:
    states = node_json("[m.orbitItem(0, 0.2, {count: 4}), m.orbitItem(0, 0.2 + 1 / 0.35, {count: 4}),"
                       " m.orbitItem(0, 0.2, {count: 4, speed: 0})]")
    assert states[0]["x"] == pytest.approx(states[1]["x"], abs=1e-9)
    assert states[0]["y"] == pytest.approx(states[1]["y"], abs=1e-9)
    assert states[2]["scale"] == pytest.approx(1 + 0.08 * states[2]["depth"])


@needs_node
def test_word_path_settles_and_explode_returns() -> None:
    out = node_json("""(() => ({
        word: m.wordPathItem(0, 5, {fromX: -2, toX: 0}),
        exploded: m.explodePart(0, 0.4, {duration: 0.4}),
        held: m.explodePart(0, 0.7, {duration: 0.4, hold: 0.4}),
        back: m.explodePart(0, 1.4, {duration: 0.4, hold: 0.4, back: 0.4}),
        stay: m.explodePart(0, 5, {duration: 0.4, hold: 0.4, reassemble: false}),
    }))()""")
    assert out["word"]["x"] == pytest.approx(0) and out["word"]["y"] == pytest.approx(0)
    assert out["word"]["opacity"] == pytest.approx(1)
    assert out["exploded"]["progress"] == pytest.approx(1)
    assert out["held"]["progress"] == pytest.approx(1)
    assert out["back"]["x"] == pytest.approx(0, abs=1e-9)
    assert out["stay"]["progress"] == pytest.approx(1)


@needs_node
def test_mask_wipe_directions_and_validation() -> None:
    out = node_json("""(() => {
        const error = (fn) => { try { fn(); return 'none'; } catch (e) { return e.name; } };
        return {
          ltr: m.maskWipe(1, {duration: 1}), rtl: m.maskWipe(0.5, {duration: 1, direction: 'rtl'}),
          ttb: m.maskWipe(1, {duration: 1, direction: 'ttb'}),
          btt: m.maskWipe(0.5, {duration: 1, direction: 'btt'}),
          bad: error(() => m.maskWipe(0, {direction: 'diagonal'})),
        };
    })()""")
    assert out["ltr"]["w"] == pytest.approx(1) and out["ltr"]["x"] == 0
    assert out["rtl"]["x"] == pytest.approx(0.125) and out["rtl"]["w"] == pytest.approx(0.875)
    assert out["ttb"]["h"] == pytest.approx(1)
    assert out["btt"]["y"] == pytest.approx(0.125)
    assert out["bad"] == "RangeError"


@needs_node
def test_data_count_clamps_and_rounds() -> None:
    values = node_json("[m.dataCount(0, {to: 250, decimals: 1}), m.dataCount(5, {to: 250, decimals: 1}),"
                       " m.dataCount(0.5, {to: 10, decimals: 0})]")
    assert values[0]["value"] == 0
    assert values[1]["value"] == 250
    assert 0 < values[2]["value"] < 10, "the mid value follows the ease, not a linear 50%"


@needs_node
def test_card_stack_camera_and_burst_boundaries() -> None:
    out = node_json("""(() => ({
        cards: [0, 1, 2].map(i => m.cardStackItem(i, 5)),
        camera: [m.cameraPush(0, {toScale: 1.2}), m.cameraPush(9, {toScale: 1.2})],
        burst: m.particleBurst(3, 1.4, {duration: 0.7}),
        repeat: [m.particleBurst(3, 0.3), m.particleBurst(3, 0.3)],
    }))()""")
    assert all(card["x"] == 0 and card["opacity"] == 1 for card in out["cards"])
    assert out["camera"][0]["scale"] == pytest.approx(1.0)
    assert out["camera"][1]["scale"] == pytest.approx(1.2)
    assert out["burst"]["opacity"] == pytest.approx(0)
    assert out["repeat"][0] == out["repeat"][1]


FAKE_CTX_EXTRA = """
class Ctx2 extends Ctx {
  rotate(a) { this.ops.push(['rotate', a]); }
  beginPath() { this.ops.push(['beginPath']); }
  rect(x, y, w, h) { this.ops.push(['rect', x, y, w, h]); }
  clip() { this.ops.push(['clip']); }
}
"""


@needs_node
def test_the_new_adapters_transform_the_context() -> None:
    script = f"""
    {FAKE_CTX}
    {FAKE_CTX_EXTRA}
    const a = await import('./medo-motion/templates/render/lib/moves-render.js');
    const ctx = new Ctx2();
    a.drawOrbit(ctx, ['x', 'y'], 0.5, {{ unit: 40, count: 2 }}, () => {{}});
    a.drawWordPath(ctx, ['و'], 0.2, {{ unit: 40 }}, () => {{}});
    a.drawExplode(ctx, [{{}}], 0.3, {{ unit: 40 }}, () => {{}});
    a.drawMaskWipe(ctx, 0.5, {{ duration: 1, width: 200, height: 100, direction: 'ltr' }}, () => {{}});
    a.drawCardStack(ctx, ['a', 'b'], 0.3, {{ unit: 40 }}, () => {{}});
    a.drawCameraPush(ctx, 0.5, {{ width: 200, height: 100, toScale: 1.5 }}, () => {{}});
    a.drawParticleBurst(ctx, 0.2, {{ unit: 40, count: 4 }}, () => {{}});
    const counted = a.drawDataCount({{}}, 0.4, {{ to: 99 }}, () => {{}});
    console.log(JSON.stringify({{ ops: ctx.ops.map(op => op[0]), counted }}));
    """
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=str(ROOT),
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    ops = out["ops"]
    assert ops.count("save") == ops.count("restore")
    assert 1 <= ops.count("clip") <= 1
    assert "rect" in ops and "rotate" in ops
    assert out["counted"]["value"] == 87, "0.4s of a 0.8s ease-out window = 87 of 99"


@needs_node
def test_mask_wipe_adapter_refuses_a_context_without_clip() -> None:
    script = f"""
    {FAKE_CTX}
    const a = await import('./medo-motion/templates/render/lib/moves-render.js');
    try {{ a.drawMaskWipe(new Ctx(), 0.5, {{}}, () => {{}}); console.log('no-error'); }}
    catch (e) {{ console.log(e.name); }}
    """
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=str(ROOT),
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "TypeError"
