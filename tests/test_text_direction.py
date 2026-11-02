"""Agent-authored text direction: no default style, explicit per-scene choices,
validated identically in Python (P/lint) and JS (K/R), and enforced by the scaffold.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys

import pytest
from conftest import ENGINE_P, ROOT, SKILL

sys.path.insert(0, str(ENGINE_P))
import text_direction as td  # noqa: E402

GOOD_DIR = json.loads((ROOT / "tests" / "fixtures" / "reel" / "good" / "plan" / "text-direction.json").read_text())
GOOD_BEATS = json.loads((ROOT / "tests" / "fixtures" / "reel" / "good" / "plan" / "beats.json").read_text())
GOOD_COPY = json.loads((ROOT / "tests" / "fixtures" / "reel" / "good" / "plan" / "copy.json").read_text())


def test_good_direction_validates_clean():
    report = td.validate(GOOD_DIR, GOOD_BEATS)
    assert report["errors"] == []
    assert report["warnings"] == []


def test_draft_or_missing_choices_are_errors():
    draft = td.init_draft(GOOD_BEATS)
    report = td.validate(draft, GOOD_BEATS)
    assert report["errors"], "a draft must not pass as directed"
    assert td.validate({}, GOOD_BEATS)["errors"]


def test_unknown_style_and_role_are_rejected():
    bad = json.loads(json.dumps(GOOD_DIR))
    bad["scenes"][0]["captionStyle"] = "definitely-not-a-style"
    bad["scenes"][0]["textStyles"] = {"banner": "pop"}
    report = td.validate(bad, GOOD_BEATS)
    assert any("captionStyle" in e for e in report["errors"])
    assert any("unknown text role" in e for e in report["errors"])


def test_repeated_motif_warns_unless_explained():
    same = json.loads(json.dumps(GOOD_DIR))
    for sc in same["scenes"]:
        sc["captionStyle"] = "pop"
    assert td.validate(same, GOOD_BEATS)["warnings"]
    same["motifReason"] = "a deliberate uniform caption motif for this calm explainer"
    assert not td.validate(same, GOOD_BEATS)["warnings"]


def test_resolve_helpers_require_explicit_choices():
    assert td.caption_style_for(GOOD_DIR, 1) == GOOD_DIR["scenes"][0]["captionStyle"]
    with pytest.raises(ValueError):
        td.caption_style_for(td.init_draft(GOOD_BEATS), 1)
    with pytest.raises(ValueError):
        td.text_style_for(GOOD_DIR, 1, "nonexistent-role")


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_js_and_python_validate_identically():
    cases = {
        "good": GOOD_DIR,
        "draft": td.init_draft(GOOD_BEATS),
        "empty": {},
    }
    script = (
        "import { validateTextDirection } from "
        + json.dumps(str(SKILL / "templates" / "render" / "lib" / "text-direction.js")) + ";\n"
        "const cases = JSON.parse(process.argv[1]);\n"
        "const beats = JSON.parse(process.argv[2]);\n"
        "const out = {};\n"
        "const copy = JSON.parse(process.argv[3]);\n"
        "for (const [k, v] of Object.entries(cases)) out[k] = validateTextDirection(v, beats, copy);\n"
        "console.log(JSON.stringify(out));\n"
    )
    r = subprocess.run(["node", "-e", script, json.dumps(cases), json.dumps(GOOD_BEATS), json.dumps(GOOD_COPY)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    js = json.loads(r.stdout)
    for name, direction in cases.items():
        py = td.validate(direction, GOOD_BEATS, GOOD_COPY)
        assert js[name]["errors"] == py["errors"], name
        assert js[name]["warnings"] == py["warnings"], name


def test_good_direction_covers_every_text_fragment():
    assert td.validate(GOOD_DIR, GOOD_BEATS, GOOD_COPY)["errors"] == []


def test_undirected_text_fragment_is_an_error():
    copy = json.loads(json.dumps(GOOD_COPY))
    del copy["copy"][1]["role"]
    report = td.validate(GOOD_DIR, GOOD_BEATS, copy)
    assert any("known role" in e for e in report["errors"])
    # a known role with no style in the scene is also rejected
    copy = json.loads(json.dumps(GOOD_COPY))
    copy["copy"][1]["role"] = "quote"
    report = td.validate(GOOD_DIR, GOOD_BEATS, copy)
    assert any("no textStyles.quote" in e for e in report["errors"])


def test_element_override_resolves_and_must_match_role():
    first = GOOD_COPY["copy"][0]
    assert td.text_style_for(GOOD_DIR, first["scene"], "hook", first["id"]) == "wordPop"
    with pytest.raises(ValueError):
        td.text_style_for(GOOD_DIR, first["scene"], "title", first["id"])


def test_tool_init_then_check(tmp_path):
    proj = tmp_path / "reel"
    (proj / "plan").mkdir(parents=True)
    (proj / "plan" / "beats.json").write_text(json.dumps(GOOD_BEATS), encoding="utf-8")
    tool = ROOT / "tools" / "text_direction.py"
    r = subprocess.run([sys.executable, str(tool), str(proj), "--init"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    draft = json.loads((proj / "plan" / "text-direction.json").read_text())
    assert draft["status"] == "draft" and len(draft["scenes"]) == len(GOOD_BEATS["scenes"])
    # draft must fail the check
    r = subprocess.run([sys.executable, str(tool), str(proj), "--check"], capture_output=True, text=True)
    assert r.returncode == 1
    # fill it with the good direction -> passes
    (proj / "plan" / "text-direction.json").write_text(json.dumps(GOOD_DIR), encoding="utf-8")
    r = subprocess.run([sys.executable, str(tool), str(proj), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_new_project_scaffolds_a_draft_direction(tmp_path):
    slug = f"_pytest-dir-{tmp_path.name}"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"), slug, "--engine", "k"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    proj = ROOT / "projects" / slug
    try:
        direction = json.loads((proj / "plan" / "text-direction.json").read_text())
        assert direction["status"] == "draft"
        assert direction["decidedBy"] is None
        assert (proj / "src" / "lib" / "text-direction.js").is_file()
        assert (proj / "src" / "lib" / "caption-motion.js").is_file()
    finally:
        shutil.rmtree(proj, ignore_errors=True)
