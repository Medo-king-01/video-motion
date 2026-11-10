"""Animated backgrounds: catalogue ↔ JS ↔ Python parity, brand roles, and (with Chromium) pixels."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys

import numpy as np
import pytest
from conftest import ROOT, SKILL

CATALOG = SKILL / "motion" / "backgrounds.json"
K_LIB = SKILL / "templates" / "render" / "lib" / "backgrounds.js"
R_LIB = SKILL / "templates" / "remotion" / "src" / "lib" / "backgrounds.js"
P_DIR = SKILL / "templates" / "procedural-reels"
BRAND = ROOT / "medo-motion" / "brand" / "brand.json"

# Append, never insert(0): the engine folder contains a CLI named `chunk.py`, and on Python 3.10 the
# stdlib `wave` module does `from chunk import Chunk`. Putting that folder first shadows `chunk` and
# collection dies with "usage: chunk.py START_FRAME END_FRAME" (this exact failure hit CI on 3.10).
for _p in (str(ROOT / "tools"), str(P_DIR)):
    if _p not in sys.path:
        sys.path.append(_p)

import backgrounds as bg  # noqa: E402
import backgrounds_sheet  # noqa: E402

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop


@pytest.fixture(scope="module")
def catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _js_export(module: str, expr: str) -> str:
    script = (f"const m = await import({json.dumps(module)});\n"
              f"console.log(JSON.stringify({expr}));\n")
    r = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_catalog_is_the_single_list(catalog):
    ids = [b["id"] for b in catalog["backgrounds"]]
    assert len(ids) == len(set(ids)) == 12
    assert ids == list(bg.BACKGROUND_IDS)
    for item in catalog["backgrounds"]:
        assert item["ar"] and item["en"] and item["desc"] and item["family"]
        assert set(item["params"]) == {"angle", "density"}
    assert bg.BACKGROUND_IDS == tuple(bg.DEFAULT_PARAMS)


def test_js_catalog_matches_the_json():
    """lib/backgrounds.js carries an embedded copy so a bare templates/ project still works."""
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    ids = _js_export(str(K_LIB), "m.BACKGROUND_IDS")
    roles = _js_export(str(K_LIB), "m.ROLES")
    params = _js_export(str(K_LIB), "m.DEFAULTS.params")
    assert ids == list(bg.BACKGROUND_IDS)
    assert roles == {k: {r: v for r, v in m.items()} for k, m in bg.ROLES.items()}
    assert params == bg.DEFAULT_PARAMS


def test_both_engine_copies_are_byte_identical():
    """K and R import different folders; the same file must serve both (like motion.js)."""
    assert K_LIB.read_bytes() == R_LIB.read_bytes()


def test_every_colour_is_a_brand_role(catalog):
    """No raw hex anywhere in the role maps, and every role names a real brand token."""
    palette = json.loads(BRAND.read_text(encoding="utf-8"))["palette"]
    palette = {k: v["hex"] for k, v in palette.items()} | {"inkShadow": "#030303"}
    for theme in ("dark", "light"):
        for name, role in catalog["roles"][theme].items():
            assert "#" not in role, f"{theme}.{name} is a raw colour: {role}"
            token = role.split("@")[0]
            assert token in palette, f"{theme}.{name} → unknown brand token {token}"
            if "@" in role:
                alpha = float(role.split("@")[1])
                assert 0 < alpha <= 1, f"{theme}.{name} alpha out of range"
    # the Python + JS copies agree with the catalog
    assert {k: dict(v) for k, v in bg.ROLES.items()} == {k: catalog["roles"][k] for k in ("dark", "light")}


def test_roles_resolve_to_the_brand_palette():
    palette = json.loads(BRAND.read_text(encoding="utf-8"))["palette"]
    for theme in ("dark", "light"):
        for role, (rgb, _alpha) in bg.theme_colors(theme):
            token = bg.ROLES[theme][role].split("@")[0]
            hexv = palette.get(token, {}).get("hex") if token != "inkShadow" else "#030303"
            assert hexv, token
            want = tuple(float(int(hexv[i:i + 2], 16)) for i in (1, 3, 5))
            assert rgb == want, f"{theme}.{role}: {rgb} != {hexv}"
    # the two themes differ where it matters: the accent is the bright red on dark, deep on light
    assert bg.theme_colors("dark")[list(dict(bg.theme_colors("dark"))).index("accent")][1][0][0] == 203
    assert bg.theme_colors("light")[list(dict(bg.theme_colors("light"))).index("accent")][1][0][0] == 159


def test_frames_are_pure_and_deterministic():
    """Same t, same picture — forward, backward or in chunks. This is what makes P chunk-parallel."""
    for bid in bg.ids():
        a = bg.frame(bid, 180, 320, 2.4)
        b = bg.frame(bid, 180, 320, 2.4)
        assert np.array_equal(a, b), bid
        c = bg.frame(bid, 180, 320, 2.4 + 10.0)   # far ahead: still the same frame shape/space
        assert c.shape == a.shape and c.dtype == np.uint8
    # different times must actually change the picture (a static background is a bug)
    for bid in ("iso-grid", "pulse", "perspective", "glyphs", "frames"):
        assert not np.array_equal(bg.frame(bid, 180, 320, 1.0), bg.frame(bid, 180, 320, 4.0)), bid


def test_backgrounds_are_on_palette(catalog):
    """Every rendered frame is a mix of brand tokens: each pixel is close to the line segment between
    two palette colours, i.e. no hue from outside the brand can get in (this is the rule the whole
    library was re-coloured for)."""
    palette = json.loads(BRAND.read_text(encoding="utf-8"))["palette"]
    hexes = {v["hex"].lower() for v in palette.values()} | {"#030303"}
    brand = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in hexes], np.float32)

    def distance_to_segment(points: np.ndarray) -> np.ndarray:
        """Per-pixel max-channel distance to the nearest brand↔brand mix."""
        best = np.full(len(points), 1e9, np.float32)
        for i in range(len(brand)):
            for j in range(i, len(brand)):
                a, b = brand[i], brand[j]
                ab = b - a
                denom = float(ab @ ab) or 1e-6
                t = np.clip(((points - a) @ ab) / denom, 0.0, 1.0)
                proj = a + t[:, None] * ab
                best = np.minimum(best, np.abs(points - proj).max(1))
        return best

    for theme in ("dark", "light"):
        for bid in bg.ids():
            im = bg.frame(bid, 120, 200, 2.4, theme).astype(np.float32).reshape(-1, 3)
            sample = im[:: max(1, len(im) // 1500)]
            d = distance_to_segment(sample)
            assert d.mean() < 12, f"{theme}/{bid}: colours are {d.mean():.0f} away from the palette"


def test_unknown_ids_and_params_fall_back():
    assert bg.resolve_spec({"id": "nope"})["id"] == "wash"
    assert bg.resolve_spec({"id": "pulse", "theme": "neon"})["theme"] == "dark"
    assert bg.resolve_spec({"id": "pulse"})["density"] == bg.DEFAULT_PARAMS["pulse"]["density"]
    assert bg.resolve_spec({"id": "pulse", "density": 70})["density"] == 70
    im = bg.frame("nope", 90, 160, 1.0)          # must not raise, must still be a frame
    assert im.shape == (160, 90, 3)


def test_paint_into_fills_an_existing_frame():
    frame = np.zeros((160, 90, 3), np.uint8)
    out = bg.paint_into(frame, "aura", t=1.5, theme="light")
    assert out is frame and frame.mean() > 100   # a light theme actually painted a light frame


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_engine_k_and_p_draw_the_same_background():
    """Rasterise both engines and compare. A drift here is a visible difference inside a reel."""
    ids = list(bg.ids())
    worst = []
    for theme in ("dark", "light"):
        try:
            k = backgrounds_sheet.render_k(ids, 180, 320, 2.4, theme)
        except RuntimeError as exc:                       # no Chromium in this environment
            pytest.skip(f"engine K unavailable: {exc}")
        for bid in ids:
            p = bg.frame(bid, 180, 320, 2.4, theme)
            delta = float(np.abs(p.astype(np.int16) - k[bid].astype(np.int16)).mean())
            worst.append((delta, theme, bid))
    worst.sort(reverse=True)
    assert worst[0][0] < 16, f"P and K drifted apart: {worst[:3]}"
    assert sum(1 for d, _t, _b in worst if d < 10) >= len(worst) - 3, f"parity too loose: {worst[:3]}"


def test_engine_p_frame_budget():
    """A background may not dominate a frame. Budget: < 700 ms per 1080×1920 frame on CI hardware."""
    import time

    for bid in bg.ids():
        t0 = time.perf_counter()
        bg.frame(bid, 1080, 1920, 2.4)
        ms = (time.perf_counter() - t0) * 1000
        assert ms < 700, f"{bid} takes {ms:.0f} ms/frame at 1080×1920"


def test_engine_path_never_shadows_the_stdlib_chunk_module():
    """Regression guard for the Python 3.10 CI failure this file caused.

    The engine folder ships a `chunk.py` CLI, and on 3.10 the stdlib `wave` module does
    `from chunk import Chunk`. A test module that puts the engine folder FIRST in sys.path can
    therefore kill collection with `SystemExit: usage: chunk.py START_FRAME END_FRAME` — but only
    when it is collected before `wave` is imported. Two rules keep it dead:
      1. tests/conftest.py imports `wave` before any test module runs (documented there);
      2. a test module that needs the engine appends the folder instead of inserting it.
    """
    conftest = (ROOT / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "import wave" in conftest, "conftest must import wave before tests touch sys.path"
    assert conftest.index("import wave") < conftest.index("sys.path.append"), "wave must come first"
    here = (ROOT / "tests" / "test_backgrounds.py").read_text(encoding="utf-8")
    calls = [ln.strip() for ln in here.splitlines() if ln.strip().startswith("sys.path.insert")]
    assert not any("P_DIR" in ln or "procedural-reels" in ln for ln in calls), \
        f"append the engine folder, never insert(0): {calls}"


def test_sheet_builds(tmp_path):
    out = backgrounds_sheet.sheet(tmp_path / "sheet.png", only=["pulse", "wash"], themes=("dark",), w=90, h=160)
    assert out.is_file() and out.stat().st_size > 1000
