"""Clean-room boundary and documentation tests for `docs/openmontage-fit.md`."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_openmontage_fit_doc_exists_and_is_indexed():
    doc = ROOT / "docs" / "openmontage-fit.md"
    assert doc.is_file(), "docs/openmontage-fit.md must exist"
    text = doc.read_text(encoding="utf-8")
    assert "AGPL-3.0" in text
    assert "d21f5d4eaa08422b09c7091757a05affcbabb35b" in text
    for tool_name in ("media_qa.py", "layout_audit_p.py", "stage_gate.py", "doctor.py --json"):
        assert tool_name in text

    index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "openmontage-fit.md" in index


def test_no_openmontage_dependency_or_copied_imports():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert "openmontage" not in pyproject

    for pkg_json in (ROOT / "package.json", ROOT / "medo-motion" / "templates" / "remotion" / "package.json"):
        if pkg_json.is_file():
            pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
            deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
            assert not any("openmontage" in k.lower() for k in deps)

    import_re = re.compile(r"^\s*(?:from|import)\s+openmontage\b", re.M)
    for folder in (ROOT / "tools", ROOT / "medo-motion"):
        for py_file in folder.rglob("*.py"):
            assert not import_re.search(py_file.read_text(encoding="utf-8")), f"forbidden import in {py_file}"
