"""`assets/gl-transitions` is a reference store: nothing in the render path loads a shader.

These tests keep the documents honest about that, and about the licence each file declares
for itself. They state what the headers say; they do not decide what the terms allow.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "assets" / "gl-transitions"
DOC = ROOT / "docs" / "GL_TRANSITIONS.md"
INVENTORY = ROOT / "docs" / "gl-transitions-headers.md"
NOTICE = ROOT / "NOTICE"
TOOL = ROOT / "tools" / "gl_headers.py"

sys.path.insert(0, str(ROOT / "tools"))

SHADERS = sorted(STORE.glob("*.glsl"))
RUNTIME = ["medo-motion/templates", "medo-motion/scripts", "medo-motion/motion", "tools"]
NOT_RUNTIME = ("tools/dev/_archive/", "tools/sync_docs_numbers.py", "tools/gl_headers.py")


def _declared(path: Path) -> list[str]:
    return [m.strip() for m in re.findall(r"^\s*//\s*Licen[sc]e\s*:\s*(.+)$", path.read_text(encoding="utf-8"), re.M)]


def test_nothing_in_the_render_path_reads_the_shader_store() -> None:
    """The premise of the wording below. If this fails a consumer was added: update the documents."""
    listed = subprocess.run(["git", "ls-files", "--", *RUNTIME], cwd=ROOT, capture_output=True, text=True, check=True)
    readers = []
    for name in listed.stdout.splitlines():
        if name.startswith(NOT_RUNTIME) or not name.endswith((".py", ".js", ".mjs", ".ts", ".tsx", ".sh", ".json")):
            continue
        text = (ROOT / name).read_text(encoding="utf-8", errors="replace")
        if re.search(r"assets/gl-transitions|glsl_file|\.glsl\b", text):
            readers.append(name)
    assert readers == [], f"these files now touch the shader store: {readers}"


@pytest.mark.parametrize("claim", [
    "load_shader", '"gl-Cube"', "جاهز للاستخدام", "fallback", "FFmpeg** مع دعم OpenGL", "متى تستخدمها",
])
def test_the_document_does_not_show_a_usage_that_does_not_exist(claim: str) -> None:
    assert claim not in DOC.read_text(encoding="utf-8"), f"docs/GL_TRANSITIONS.md still promises: {claim}"


def test_the_document_says_the_store_is_not_wired_and_names_the_supported_set() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "مش موصّل بمسار الرندر" in text
    assert "medo-motion/motion/transitions.json" in text and "AUTO:transitions" in text
    assert "docs/transitions.md" in text or "(transitions.md)" in text


def test_every_shader_the_documents_name_is_a_file_that_ships() -> None:
    names = {p.stem for p in SHADERS}
    for doc in (DOC, ROOT / "README.md"):
        text = doc.read_text(encoding="utf-8")
        cited = set(re.findall(r"`(\w+)\.glsl`", text))
        if doc == DOC:  # its tables are shader tables; README has unrelated ones
            cited |= set(re.findall(r"^\| \*\*(\w+)\*\* \|", text, re.M))
        assert cited - names == set(), f"{doc.name} names shaders that are not in the store: {sorted(cited - names)}"


def test_the_store_really_holds_more_than_one_declared_licence() -> None:
    """The fact the wording depends on, read from the files rather than remembered."""
    declared = {p.name: _declared(p) for p in SHADERS}
    others = {name: found for name, found in declared.items() if any(not f.upper().startswith("MIT") for f in found)}
    assert others == {"InvertedPageCurl.glsl": ["BSD 3 Clause"], "StereoViewer.glsl": ["BSD 2 Clause"]}
    assert all(found for found in declared.values()), "a shader without a `// License:` line appeared"


@pytest.mark.parametrize("path", [DOC, NOTICE, ROOT / "docs" / "transitions.md"], ids=lambda p: p.name)
def test_no_document_states_one_licence_for_the_whole_store(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "شيدورات GPU جاهزة" not in (ROOT / "README.md").read_text(encoding="utf-8")
    assert not re.search(r"الرخصة:\*\*\s*MIT", text), "one licence is stated for all 189 files"
    assert not re.search(r"gl-transitions\*\*\s*\(MIT", text), "the collection is called MIT as a whole"


@pytest.mark.parametrize("path", [DOC, NOTICE], ids=lambda p: p.name)
def test_the_exceptions_are_named_and_left_undecided(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for needle in ("InvertedPageCurl.glsl", "StereoViewer.glsl", "BSD"):
        assert needle in text, f"{path.name} does not mention {needle}"
    assert "غير محسوم" in text, f"{path.name} must say the licence question is undecided"
    assert "gl-transitions-headers.md" in text


def test_the_header_inventory_matches_the_files() -> None:
    assert INVENTORY.is_file(), "docs/gl-transitions-headers.md is missing — run: python tools/gl_headers.py --write"
    done = subprocess.run([sys.executable, str(TOOL), "--check"], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    full = INVENTORY.read_text(encoding="utf-8").split("## All files", 1)[1]
    rows = [line for line in full.splitlines() if re.match(r"^\| `\w+\.glsl` \|", line)]
    assert len(rows) == len(SHADERS)


def test_the_inventory_check_notices_a_changed_header(tmp_path: Path) -> None:
    import gl_headers

    store = tmp_path / "store"
    store.mkdir()
    (store / "A.glsl").write_text("// Author: someone\n// License: MIT\nvec4 transition(vec2 uv){return vec4(0.);}\n", encoding="utf-8")
    table = tmp_path / "table.md"
    table.write_text(gl_headers.render(gl_headers.inventory(store)), encoding="utf-8")
    assert gl_headers.main(["--check", "--store", str(store), "--out", str(table)]) == 0
    (store / "A.glsl").write_text("// Author: someone\n// License: BSD 3 Clause\n", encoding="utf-8")
    assert gl_headers.main(["--check", "--store", str(store), "--out", str(table)]) == 1
    (store / "B.glsl").write_text("vec4 transition(vec2 uv){return vec4(0.);}\n", encoding="utf-8")
    rows = {row["file"]: row for row in gl_headers.inventory(store)}
    assert rows["B.glsl"]["licence"] == "" and rows["B.glsl"]["flag"], "a file with no licence line must be flagged"
