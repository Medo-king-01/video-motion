"""B3: exploded views over `machine-kit.js` — open, hold, close, and land exactly where we started.

The explosion is a 3D transform on the model parts (before projection), scheduled by a window inside
the machine's own time range. These tests pin the schedule, the geometry, the P↔K parity and the
preview's determinism.
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
ENGINE_P = ROOT / "medo-motion" / "templates" / "procedural-reels"
SPEC = ROOT / "medo-motion" / "motion" / "examples" / "exploded-nvme.json"
PREVIEW = TOOLS / "machine_explode_preview.mjs"

sys.path.insert(0, str(ENGINE_P))
import machine_kit as mk  # noqa: E402

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

TIMES = (4.5, 5.6, 6.2, 7.3)


def spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def mutated(fn) -> dict:
    board = copy.deepcopy(spec())
    fn(board)
    return board


def node(script: str) -> str:
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=str(ROOT),
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    return result.stdout


KIT = json.dumps((ROOT / "shared" / "js" / "machine-kit.js").as_uri())


def kit_script(body: str) -> str:
    return ("import { readFileSync } from 'node:fs';\n"
            f"const kit = await import({KIT});\n"
            "const spec = JSON.parse(readFileSync('medo-motion/motion/examples/exploded-nvme.json', 'utf8'));\n"
            f"console.log(JSON.stringify((() => {{ {body} }})()));")


# ---------------------------------------------------------------- contract
def test_the_sample_spec_is_valid_in_both_engines() -> None:
    assert mk.validate_machine_spec(spec()) == []


@needs_node
def test_the_sample_spec_is_valid_in_the_js_kit() -> None:
    out = node(kit_script("return kit.validateMachineSpec(spec);"))
    assert json.loads(out) == []


@pytest.mark.parametrize(("edit", "needle"), [
    (lambda s: s["explode"].update(amount=1.5), "explode.amount"),
    (lambda s: s["explode"].update(end=9.0), "window must sit inside"),
    (lambda s: s["explode"].update(end=4.9), "explode requires finite start < end"),
    (lambda s: s["explode"].update(hold=0.95), "explode.hold"),
    (lambda s: s["explode"].update(spread=500), "explode.spread"),
    (lambda s: s["explode"].update(focus="gpu"), "explode.focus"),
])
@needs_node
def test_both_validators_reject_the_same_broken_explode(edit, needle: str) -> None:
    broken = mutated(edit)
    py_errors = mk.validate_machine_spec(broken)
    assert any(needle in error for error in py_errors), py_errors
    js_errors = json.loads(node(
        "import { readFileSync } from 'node:fs';\n"
        f"const kit = await import({KIT});\n"
        f"const spec = {json.dumps(broken)};\n"
        "console.log(JSON.stringify(kit.validateMachineSpec(spec)));"))
    assert any(needle in error for error in js_errors), js_errors


# ---------------------------------------------------------------- schedule
def sample_times() -> list[float]:
    cfg = spec()["explode"]
    start, end = cfg["start"], cfg["end"]
    travel = (end - start) * (1 - cfg["hold"]) / 2
    return [start - 0.1, start + travel * 0.5, start + travel + 0.05,
            end - travel * 0.5, end - 1e-4, end, end + 0.1]


def phases_py() -> list[dict]:
    return [mk.explode_progress_at(spec(), t) for t in sample_times()]


def test_the_schedule_opens_holds_and_closes() -> None:
    before, opening, hold, closing, nearly, end, after = phases_py()
    assert before["phase"] == "closed" and before["amount"] == 0
    assert opening["phase"] == "opening" and 0 < opening["amount"] < 0.8
    assert hold["phase"] == "hold" and hold["amount"] == 0.8
    assert closing["phase"] == "closing" and 0 < closing["amount"] < 0.8
    assert nearly["amount"] < 0.01, "the last frames must be visually closed"
    assert end["amount"] == 0, "the window must land exactly on closed, not near it"
    assert after["phase"] == "closed" and after["amount"] == 0


@needs_node
def test_the_schedule_matches_between_engines() -> None:
    js = json.loads(node(kit_script(
        f"return {json.dumps(sample_times())}.map(t => kit.explodeProgressAt(spec, t));")))
    assert js == phases_py()


# ---------------------------------------------------------------- geometry
def test_amount_zero_leaves_every_part_untouched() -> None:
    model = mk.expand_machine_model(spec())
    shaped = mk.explode_machine_model(model, 0.0)
    assert shaped["parts"] == model["parts"]


def test_parts_keep_identity_and_order_when_exploded() -> None:
    model = mk.expand_machine_model(spec())
    shaped = mk.explode_machine_model(model, 0.8, spread=130, focus="pcb")
    assert [p["id"] for p in shaped["parts"]] == [p["id"] for p in model["parts"]]
    moved = [a["id"] for a, b in zip(shaped["parts"], model["parts"], strict=True) if a != b]
    assert moved, "an exploded model must actually move something"
    assert "pcb" not in moved, "the focused base part holds still"
    assert len(moved) == len(model["parts"]) - 1


def test_the_offset_is_deterministic() -> None:
    model = mk.expand_machine_model(spec())
    a = mk.explode_machine_model(model, 0.55, spread=130)
    b = mk.explode_machine_model(model, 0.55, spread=130)
    assert a == b
    assert a is not model


def test_the_bounds_grow_while_open_and_return_when_closed() -> None:
    closed = mk.build_machine_scene(spec(), 4.0)["bounds"]
    open_ = mk.build_machine_scene(spec(), 6.2)["bounds"]
    again = mk.build_machine_scene(spec(), 7.6)["bounds"]
    assert open_["w"] > closed["w"] * 1.4, (closed, open_)
    assert open_["h"] > closed["h"] * 1.1
    assert again == closed


def test_reassembly_restores_the_exact_geometry_and_order() -> None:
    plain_spec = mutated(lambda s: s.pop("explode"))
    again = mk.build_machine_scene(spec(), 7.6)
    plain = mk.build_machine_scene(plain_spec, 7.6)
    assert again["explode"]["amount"] == 0
    assert [op["partId"] for op in again["ops"]] == [op["partId"] for op in plain["ops"]]
    assert again["vertices"] == plain["vertices"]
    assert again["bounds"] == plain["bounds"]


@needs_node
def test_the_focused_part_never_moves_in_the_js_kit() -> None:
    out = node(kit_script("""
        const vertexOf = (graph, id) => graph.ops
            .filter(o => o.partId === id && o.kind === 'solid')
            .flatMap(o => o.faces.flatMap(f => f.points));
        const closed = kit.buildMachineScene(spec, 4.0);
        const open = kit.buildMachineScene(spec, 6.2);
        return { closed: vertexOf(closed, 'pcb'), open: vertexOf(open, 'pcb'),
                 openCount: open.ops.length, phase: open.explode.phase };
    """))
    data = json.loads(out)
    assert data["phase"] == "hold"
    assert data["closed"] == data["open"]


# ---------------------------------------------------------------- P ↔ K parity
@needs_node
def test_python_and_javascript_agree_on_the_exploded_geometry() -> None:
    js = json.loads(node(kit_script(
        f"return {json.dumps(list(TIMES))}.map(t => kit.buildMachineScene(spec, t, {{theme: 'dark'}}));")))
    for time, graph in zip(TIMES, js, strict=True):
        py = mk.build_machine_scene(spec(), time, theme="dark")
        assert py["explode"] == graph["explode"]
        assert py["bounds"] == graph["bounds"], time
        assert [op["partId"] for op in py["ops"]] == [op["partId"] for op in graph["ops"]]
        for py_op, js_op in zip(py["ops"], graph["ops"], strict=True):
            assert py_op["kind"] == js_op["kind"]
            if py_op["kind"] == "solid":
                for py_face, js_face in zip(py_op["faces"], js_op["faces"], strict=True):
                    assert py_face["fill"] == js_face["fill"]
                    for py_pt, js_pt in zip(py_face["points"], js_face["points"], strict=True):
                        assert py_pt == pytest.approx(js_pt, abs=1e-4)


# ---------------------------------------------------------------- preview
@needs_node
def test_the_exploded_preview_is_byte_identical_across_runs(tmp_path: Path) -> None:
    outs = [tmp_path / "a.html", tmp_path / "b.html"]
    for path in outs:
        result = subprocess.run(["node", str(PREVIEW), str(SPEC), str(path)], cwd=str(ROOT),
                                capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        assert "6 frames" in result.stdout
    first, second = (path.read_bytes() for path in outs)
    assert first == second
    html = first.decode("utf-8")
    assert html.count("<svg") == 6
    for needle in ("opening", "hold", "closing", "amount 0.800", "viewBox"):
        assert needle in html, needle
