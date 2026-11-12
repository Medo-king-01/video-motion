"""B2: the declarative board — six element kinds, one interpreter, no scene code.

The board is data. `tools/board_check.py` refuses anything outside the studio's vocabularies
(brand roles, pose names, move ids) and `shared/js/board.js` turns a valid board into draw ops.
These tests pin the validator, the ops, the Canvas adapter and the preview.
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
sys.path.insert(0, str(TOOLS))

import board_check  # noqa: E402

BOARD = ROOT / "medo-motion" / "motion" / "boards" / "explainer-sample.json"
K_BOARD = ROOT / "medo-motion" / "templates" / "render" / "lib" / "board.js"
R_BOARD = ROOT / "medo-motion" / "templates" / "remotion" / "src" / "lib" / "board.js"
PREVIEW = ROOT / "tools" / "board_preview.mjs"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def sample() -> dict:
    return json.loads(BOARD.read_text(encoding="utf-8"))


def errors_after(mutate) -> list[str]:
    board = copy.deepcopy(sample())
    mutate(board)
    return board_check.validate(board)


def node(script: str) -> str:
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=str(ROOT),
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    return result.stdout


def board_script(body: str) -> str:
    """Load the sample board in node and evaluate `body` (a return expression or statements)."""
    return ("import { readFileSync } from 'node:fs';\n"
            "const board = JSON.parse(readFileSync('medo-motion/motion/boards/explainer-sample.json', 'utf8'));\n"
            "const b = await import('./shared/js/board.js');\n"
            f"console.log(JSON.stringify((() => {{ {body} }})()));")


def node_block(code: str) -> str:
    """Run a block of statements with `b` and `board` in scope, returning its return value."""
    return node(board_script(code))


# ---------------------------------------------------------------- validator
def test_the_repository_board_is_valid() -> None:
    assert board_check.validate(sample()) == []


def test_the_sample_covers_every_kind() -> None:
    kinds = {element["kind"] for scene in sample()["scenes"] for element in scene["elements"]}
    assert kinds == set(board_check.KINDS)


def test_summary_counts_the_elements() -> None:
    summary = board_check.summary(sample())
    assert summary["scenes"] == 2
    assert summary["has_camera"] is True
    assert summary["kinds"] == {"text": 2, "shape": 1, "draw": 1, "data": 1, "person": 1, "image": 1}


def test_an_unknown_kind_is_refused() -> None:
    errors = errors_after(lambda board: board["scenes"][0]["elements"][0].update(kind="video"))
    assert any("is not one of" in error for error in errors), errors


def test_an_unknown_field_is_refused() -> None:
    errors = errors_after(lambda board: board["scenes"][0]["elements"][0].update(blur=4))
    assert any("unknown field" in error for error in errors), errors


def test_a_missing_required_field_is_refused() -> None:
    errors = errors_after(lambda board: board["scenes"][0]["elements"][0].pop("text"))
    assert any("$.scenes[0].elements[0].text: required" in error for error in errors), errors


def test_duplicate_ids_are_refused() -> None:
    errors = errors_after(lambda board: board["scenes"][1]["elements"][0].update(id="title"))
    assert any("duplicate id" in error for error in errors), errors


def test_overlapping_scenes_are_refused() -> None:
    errors = errors_after(lambda board: board["scenes"][1].update(start=2.0))
    assert any("may not overlap" in error for error in errors), errors


def test_a_scene_past_the_board_duration_is_refused() -> None:
    errors = errors_after(lambda board: board["scenes"][1].update(duration=9.0))
    assert any("exceeds board duration" in error for error in errors), errors


def test_a_colour_that_is_not_a_brand_role_is_refused() -> None:
    errors = errors_after(lambda board: board["scenes"][0]["elements"][0].update(color="#ff0000"))
    assert any("is not a brand role" in error for error in errors), errors


def test_a_pose_outside_the_catalog_is_refused() -> None:
    errors = errors_after(lambda board: board["scenes"][0]["elements"][2].update(pose="moonwalk"))
    assert any("is not in assets/poses" in error for error in errors), errors


def test_a_move_outside_the_catalog_is_refused() -> None:
    errors = errors_after(lambda board: board["scenes"][0]["elements"][0]["move"].update(move="spin"))
    assert any("is not one of" in error for error in errors), errors


def test_an_unsafe_image_path_is_refused() -> None:
    errors = errors_after(lambda board: board["scenes"][1]["elements"][3].update(src="../secret.png"))
    assert any("safe project-relative path" in error for error in errors), errors


def test_broken_points_and_bars_are_refused() -> None:
    def mutate(board):
        board["scenes"][1]["elements"][0]["points"] = [[0, 0]]
        board["scenes"][1]["elements"][1]["values"] = []
        board["scenes"][1]["elements"][1]["gap"] = 1.5

    errors = errors_after(mutate)
    assert any("at least 2 points" in error for error in errors), errors
    assert any("1..12 finite numbers" in error for error in errors), errors
    assert any("within 0..0.9" in error for error in errors), errors


def test_a_present_person_width_must_be_positive() -> None:
    errors = errors_after(lambda board: board["scenes"][0]["elements"][2].update(w=0))
    assert any("B04" in error and ".w:" in error for error in errors), errors


def test_a_future_version_is_refused() -> None:
    errors = errors_after(lambda board: board.update(version=2))
    assert any("only version 1" in error for error in errors), errors


# ---------------------------------------------------------------- interpreter
@needs_node
def test_the_frame_is_deterministic_and_sorted_by_z() -> None:
    out = node(board_script("""
        const a = b.boardFrame(board, 1.6), c = b.boardFrame(board, 1.6);
        return { same: JSON.stringify(a) === JSON.stringify(c), ids: a.ops.map(o => o.id),
                 z: a.ops.map(o => o.z), scene: a.sceneId, local: a.local };
    """))
    data = json.loads(out)
    assert data["same"] is True
    assert data["scene"] == "intro"
    assert data["local"] == pytest.approx(1.6)
    assert data["z"] == sorted(data["z"])
    assert data["ids"] == ["presenter", "underline", "title"]


@needs_node
def test_elements_wait_for_their_start_time() -> None:
    out = node(board_script("""
        return [b.boardFrame(board, 0.4).ops.map(o => o.id),
                b.boardFrame(board, 0.2).ops.map(o => o.id)];
    """))
    early, earlier = json.loads(out)
    assert "underline" not in earlier and "underline" not in early
    assert "presenter" in earlier


@needs_node
def test_a_person_gets_a_finite_default_width() -> None:
    out = node(board_script("""
        const person = b.boardFrame(board, 0.4).ops.find(o => o.kind === 'person');
        return { w: person.w, h: person.h, finite: Number.isFinite(person.w) };
    """))
    data = json.loads(out)
    assert data["finite"] is True
    assert data["w"] == round(data["h"] * 0.62)


def test_camera_moves_are_sampled() -> None:
    out = node(board_script("""
        const intro = b.boardFrame(board, 3.1).camera, how = b.boardFrame(board, 6.9).camera;
        return { intro, how };
    """))
    data = json.loads(out)
    assert data["intro"]["scale"] > 1.0
    assert data["how"]["scale"] >= 1.0


@needs_node
def test_unknown_values_throw_instead_of_guessing() -> None:
    out = node(board_script("""
        const bad = (mutate) => { const copy = JSON.parse(JSON.stringify(board)); mutate(copy);
            try { b.boardFrame(copy, 1); return 'none'; } catch (e) { return e.message; } };
        return {
            kind: bad(c => { c.scenes[0].elements[0].kind = 'hologram'; }),
            move: bad(c => { c.scenes[0].elements[0].move.move = 'spin'; }),
            outside: bad(() => {}),
            time: (() => { try { b.boardFrame(board, 99); return 'none'; }
                           catch (e) { return e.message; } })(),
        };
    """))
    data = json.loads(out)
    assert "Unknown board kind" in data["kind"]
    assert "Unknown element move" in data["move"]
    assert "none" == data["outside"], "a valid board must not throw"
    assert "outside the board" in data["time"]


# ---------------------------------------------------------------- canvas adapter
FAKE_CTX = """
class Ctx {
  constructor() { this.ops = []; this.globalAlpha = 1; this.text = []; }
  save() { this.ops.push('save'); } restore() { this.ops.push('restore'); }
  translate(x, y) { this.ops.push('translate'); } scale() { this.ops.push('scale'); }
  rotate() { this.ops.push('rotate'); } beginPath() { this.ops.push('beginPath'); }
  rect() { this.ops.push('rect'); } roundRect() { this.ops.push('roundRect'); }
  ellipse() { this.ops.push('ellipse'); } moveTo() { this.ops.push('moveTo'); }
  lineTo() { this.ops.push('lineTo'); } stroke() { this.ops.push('stroke'); }
  fill() { this.ops.push('fill'); } fillRect() { this.ops.push('fillRect'); }
  fillText(t, x, y, max) { this.text.push([t, x, y, max ?? null]); }
  drawImage() { this.ops.push('drawImage'); }
}
"""


@needs_node
def test_the_canvas_adapter_balances_save_restore_and_draws_each_kind() -> None:
    out = node_block(f"""
        {FAKE_CTX}
        const ctx = new Ctx();
        const frame = b.boardFrame(board, 4.6);
        const image = {{ width: 10, height: 10 }};
        const painted = b.drawBoardFrame(ctx, frame, {{ colors: {{ ink: '#111' }}, images: {{ screen: image }} }});
        return {{ painted, ops: ctx.ops, text: ctx.text }};
    """)
    data = json.loads(out)
    assert data["painted"] == 4
    assert data["ops"].count("save") == data["ops"].count("restore")
    assert "fillRect" in data["ops"] and "drawImage" in data["ops"]
    assert data["ops"].count("stroke") >= 2, "polyline and arrow head"
    assert data["text"][0][0].startswith("كل درجة")


@needs_node
def test_text_ops_carry_alignment_and_max_width() -> None:
    out = node_block(f"""
        {FAKE_CTX}
        const ctx = new Ctx();
        b.drawBoardFrame(ctx, b.boardFrame(board, 1.0),
            {{ colors: {{ ink: '#111' }}, images: {{ presenter: {{ width: 10, height: 10 }} }} }});
        return ctx.text;
    """)
    text = json.loads(out)
    title = next(entry for entry in text if entry[0].startswith("لماذا"))
    assert title[3] == 880


@needs_node
def test_a_missing_person_image_is_an_error_not_a_blank_frame() -> None:
    out = node_block(f"""
        {FAKE_CTX}
        try {{ b.drawBoardFrame(new Ctx(), b.boardFrame(board, 0.5), {{}}); return 'none'; }}
        catch (e) {{ return e.message; }}
    """)
    message = json.loads(out)
    assert "needs assets.images" in message


def test_the_engines_ship_the_same_board_source() -> None:
    canonical = (ROOT / "shared" / "js" / "board.js").read_bytes()
    assert K_BOARD.read_bytes() == canonical
    assert R_BOARD.read_bytes() == canonical


# ---------------------------------------------------------------- CLI + preview
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "board_check.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=60)


def test_cli_accepts_the_sample() -> None:
    result = run()
    assert result.returncode == 0, result.stderr
    assert "Valid board" in result.stdout


def test_cli_json_summary() -> None:
    result = run(str(BOARD), "--json")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["kinds"]["person"] == 1


def test_cli_reports_an_invalid_board(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    board = sample()
    board["scenes"][0]["elements"][0]["kind"] = "hologram"
    broken.write_text(json.dumps(board), encoding="utf-8")
    result = run(str(broken))
    assert result.returncode == 1
    assert "is not one of" in result.stderr


def test_cli_reports_an_unreadable_file(tmp_path: Path) -> None:
    result = run(str(tmp_path / "missing.json"))
    assert result.returncode == 2
    assert "Cannot read board" in result.stderr


@needs_node
def test_the_preview_is_byte_identical_across_runs(tmp_path: Path) -> None:
    outs = [tmp_path / "a.html", tmp_path / "b.html"]
    for path in outs:
        result = subprocess.run(["node", str(PREVIEW), str(BOARD), str(path)], cwd=str(ROOT),
                                capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        assert "4 frames" in result.stdout
    first, second = (path.read_bytes() for path in outs)
    assert first == second
    html = first.decode("utf-8")
    for needle in ("لماذا تبرد الشريحة", "person: explain", "image: media/thermal-shot.png", "t="):
        assert needle in html, needle
    assert "NaN" not in html, "every person/image placeholder must have a width"
