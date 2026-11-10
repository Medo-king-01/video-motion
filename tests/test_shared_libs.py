"""K↔R parity: `shared/js/` is the only editable copy of the libraries both engines ship."""
from __future__ import annotations

import shutil
import subprocess
import sys

import pytest
from conftest import ROOT

TOOLS = ROOT / "tools"
SOURCE = ROOT / "shared" / "js"
TARGETS = (
    ROOT / "medo-motion" / "templates" / "render" / "lib",
    ROOT / "medo-motion" / "templates" / "remotion" / "src" / "lib",
)


def _sync():
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    import sync_shared_libs  # noqa: PLC0415

    return sync_shared_libs


def _skeleton(tmp_path):
    """A repository-shaped tree with the shared sources and both engine copies."""
    root = tmp_path / "repo"
    for relative in ("shared/js", "medo-motion/templates/render/lib", "medo-motion/templates/remotion/src/lib"):
        (root / relative).mkdir(parents=True)
    for source in SOURCE.glob("*.js"):
        shutil.copy2(source, root / "shared/js" / source.name)
        for relative in ("medo-motion/templates/render/lib", "medo-motion/templates/remotion/src/lib"):
            shutil.copy2(source, root / relative / source.name)
    return root


def test_the_shared_set_is_not_empty_and_has_no_stray_top_level_files():
    names = sorted(p.name for p in SOURCE.glob("*.js"))
    assert len(names) >= 20, "shared/js should carry the 27 JS libraries both engines use"
    assert all(p.is_file() for p in SOURCE.glob("*.js"))


def test_the_repository_is_in_sync():
    module = _sync()
    assert module.drift(ROOT) == []
    assert module.sync(ROOT) == 0


@pytest.mark.parametrize("name", sorted(p.name for p in SOURCE.glob("*.js")))
def test_every_shared_file_is_byte_identical_in_both_engines(name):
    canonical = (SOURCE / name).read_bytes()
    for target in TARGETS:
        copy = target / name
        assert copy.is_file(), f"{copy} is missing — run tools/sync_shared_libs.py --write"
        assert copy.read_bytes() == canonical, f"{copy} drifted — run tools/sync_shared_libs.py --write"


def test_no_library_is_duplicated_by_hand_outside_shared():
    module = _sync()
    shared = set(module.source_files(ROOT))
    for name in module.shared_in_every_engine(ROOT):
        assert name in shared, (
            f"{name} exists in both engines but not in shared/js — promote it to shared/js, "
            "then run tools/sync_shared_libs.py --write"
        )


def test_machine_exports_exactly_the_shared_files():
    result = subprocess.run(
        [sys.executable, str(TOOLS / "sync_shared_libs.py"), "--list", "--root", str(ROOT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == sorted(p.name for p in SOURCE.glob("*.js"))


def test_check_reports_drift_in_a_copy(tmp_path):
    module = _sync()
    root = _skeleton(tmp_path)
    assert module.drift(root) == []
    victim = root / "medo-motion/templates/remotion/src/lib" / sorted(module.source_files(root))[0]
    victim.write_text("// hand edit\n", encoding="utf-8")
    problems = module.drift(root)
    assert len(problems) == 1 and problems[0].startswith("drift:")
    assert module.sync(root) == 1


def test_missing_copy_is_reported_and_write_restores_it(tmp_path):
    module = _sync()
    root = _skeleton(tmp_path)
    victim = root / "medo-motion/templates/render/lib" / sorted(module.source_files(root))[0]
    victim.unlink()
    assert any(line.startswith("missing:") for line in module.drift(root))
    assert module.sync(root, write=True) == 0
    assert victim.is_file() and victim.read_bytes() == (root / "shared/js" / victim.name).read_bytes()
    assert module.drift(root) == []


def test_write_is_idempotent(tmp_path):
    module = _sync()
    root = _skeleton(tmp_path)
    root.joinpath("medo-motion/templates/render/lib").joinpath(
        sorted(module.source_files(root))[0]
    ).write_text("// stale\n", encoding="utf-8")
    assert module.sync(root, write=True) == 0
    before = {p: p.read_bytes() for p in (root / "shared/js").glob("*.js")}
    assert module.sync(root, write=True) == 0
    assert {p: p.read_bytes() for p in (root / "shared/js").glob("*.js")} == before


def test_unpromoted_duplicate_is_reported(tmp_path):
    module = _sync()
    root = _skeleton(tmp_path)
    for relative in ("medo-motion/templates/render/lib", "medo-motion/templates/remotion/src/lib"):
        (root / relative / "hand-copied.js").write_text("export const x = 1;\n", encoding="utf-8")
    problems = module.drift(root)
    assert any(line.startswith("unpromoted: hand-copied.js") for line in problems)
    assert module.sync(root) == 1
