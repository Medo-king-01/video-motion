"""The presenter library: cut-outs, manifest, and the idle motion both engines share."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys

import numpy as np
import pytest
from conftest import ROOT, SKILL

POSES_DIR = ROOT / "assets" / "poses"
MANIFEST = POSES_DIR / "poses.json"
P_DIR = SKILL / "templates" / "procedural-reels"

sys.path.insert(0, str(P_DIR))
sys.path.insert(0, str(ROOT / "tools"))

EXPECTED = {"neutral", "explain", "point", "welcome", "wave", "clap", "like", "thinking",
            "thinking-deep", "puzzled", "sad", "shocked", "walk", "run"}


@pytest.fixture(scope="module")
def manifest():
    if not MANIFEST.exists():
        pytest.skip("poses were not built")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_every_pose_is_present_and_described(manifest):
    poses = manifest["poses"]
    assert set(poses) == EXPECTED, "manifest does not match the documented pose set"
    for meta in poses.values():
        path = POSES_DIR / meta["file"]
        assert path.is_file(), f"missing {path}"
        assert meta["ar"] and meta["en"] and meta["tags"]
        assert 0.5 <= meta["scale"] <= 1.5
    raws = {p.stem for p in (POSES_DIR / "raw").glob("*.jpg")}
    assert raws == EXPECTED, "every pose must keep its original"


def test_cutouts_are_normalised_and_transparent(manifest):
    from PIL import Image  # noqa: PLC0415

    heights = []
    for slug, meta in manifest["poses"].items():
        im = Image.open(POSES_DIR / meta["file"]).convert("RGBA")
        a = np.asarray(im)[..., 3].astype(np.float32) / 255
        heights.append(a.shape[0])
        ys, xs = np.where(a > 0.03)
        assert ys.min() <= 12 and ys.max() >= a.shape[0] - 13, f"{slug} is not trimmed to the figure"
        # background gone: the corners must be fully transparent
        assert a[:4, :4].max() < 0.02 and a[-4:, -4:].max() < 0.02, f"{slug} has an opaque corner"
        # and the figure must actually be there
        assert (a > 0.5).mean() > 0.10, f"{slug} lost most of its figure"
    assert max(heights) - min(heights) <= 8, "poses must share one figure height"


def test_no_white_fringe_on_the_brand_background(manifest):
    """A light halo is the classic cut-out failure: check the ring just inside the silhouette."""
    from PIL import Image  # noqa: PLC0415
    from scipy import ndimage as ndi  # noqa: PLC0415

    for slug in ("neutral", "wave", "thinking-deep", "run"):
        im = np.asarray(Image.open(POSES_DIR / manifest["poses"][slug]["file"]).convert("RGBA")).astype(np.float32)
        a = im[..., 3] / 255
        solid = a > 0.9
        edge = ndi.binary_dilation(solid, iterations=1) & ~solid
        if edge.sum() < 50:
            continue
        rgb = im[..., :3][edge]
        near_white = ((rgb.min(1) > 240) & (rgb.max(1) - rgb.min(1) < 12)).mean()
        assert near_white < 0.35, f"{slug}: {near_white:.0%} of the rim is background white"


def test_manifest_feet_anchor_puts_the_soles_on_the_ground(manifest):
    import presenter  # noqa: PLC0415

    presenter.manifest.cache_clear()
    for slug, meta in manifest["poses"].items():
        h = 1000
        spr = presenter.sprite(slug, h)
        assert spr.shape[0] == h
        assert presenter.poses()[slug]["feet"] == pytest.approx(meta["feet"])


def test_pose_lookup_and_aliases(manifest):
    import presenter  # noqa: PLC0415

    assert presenter.resolve("medo_wave") == "wave"
    assert presenter.resolve("medo_think") == "thinking"
    assert presenter.resolve("nonsense") == "neutral"
    assert set(presenter.available()) == EXPECTED


def test_idle_motion_is_bounded_and_periodic():
    import presenter  # noqa: PLC0415

    for t in (0, 0.37, 2.5, 11.9):
        assert 0.99 <= presenter.breathe(t) <= 1.01
        assert abs(presenter.bob(t)) <= 2.6
        assert abs(presenter.sway(t)) <= 2.1
        assert abs(presenter.lean("neutral", t)) <= 1.0
    assert max(presenter.pulse("run", t / 50) for t in range(200)) > 4
    assert all(presenter.pulse("neutral", t / 10) == 0 for t in range(50))


def test_pose_track_cross_fades_on_cue():
    import presenter  # noqa: PLC0415

    track = presenter.PoseTrack([{"t": 0, "pose": "neutral"}, {"t": 2.0, "pose": "explain"}])
    assert track.at(0)["pose"] == "neutral"
    mid = track.at(2.06)
    assert mid["pose"] == "explain" and mid["prev"] == "neutral"
    assert 0 < mid["blend"] < 1 and mid["settle"] > 1.0
    assert track.at(3.0)["blend"] == 1 and track.at(3.0)["prev"] is None


def test_cutout_keeps_the_shirt_but_drops_the_background_gap():
    """Synthetic figure: white canvas, dark body, a white 'shirt' hole and a background gap."""
    from presenter_build import cutout  # noqa: PLC0415

    img = np.full((300, 200, 3), 255, np.uint8)
    img[40:260, 60:140] = (40, 34, 33)          # body
    img[90:150, 75:125] = (243, 242, 241)       # t-shirt (shaded white) — must survive
    img[190:250, 120:140] = (255, 255, 255)     # background showing through a limb gap
    img[189, 60:140] = (40, 34, 33)             # close the gap so it becomes a hole
    rgba = cutout(img, [])
    a = rgba[..., 3] / 255.0
    assert a[60, 100] > 0.9, "body lost"
    assert a[120, 100] > 0.9, "t-shirt was punched out"
    assert a[220, 130] < 0.1, "enclosed background gap was filled"
    assert a[10, 10] < 0.05, "background kept"


def test_engine_k_and_p_place_the_pose_identically(manifest):
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    import presenter  # noqa: PLC0415

    script = (
        "const p = await import(" + json.dumps(str(SKILL / "templates" / "render" / "lib" / "presenter.js")) + ");\n"
        "const names = ['neutral', 'wave', 'run', 'thinking-deep'];\n"
        "const out = {};\n"
        "for (const n of names) out[n] = [0, .5, 2.3, 7.7].map(t => p.poseFrame(n, t, { height: .62, x: .48, flip: false }));\n"
        "console.log(JSON.stringify(out));\n"
    )
    r = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    js = json.loads(r.stdout)
    for name, frames in js.items():
        meta = presenter.poses()[name]
        for t, ref in zip((0, 0.5, 2.3, 7.7), frames, strict=True):
            h = 0.62 * 1920 * meta["scale"]
            feet = meta["feet"]
            expect_cy = 1390 - (feet - 0.5) * h - presenter.bob(t) - presenter.pulse(name, t)
            assert ref["cy"] == pytest.approx(expect_cy, abs=0.2), f"{name} cy @ {t}"
            assert ref["cx"] == pytest.approx(0.48 * 1080 + presenter.sway(t), abs=0.2), f"{name} cx @ {t}"
            assert ref["rot"] == pytest.approx(presenter.lean(name, t), abs=1e-6)
            assert ref["scale"] == pytest.approx(presenter.breathe(t), abs=1e-9)


def test_scenes_and_project_template_are_wired():
    scene = SKILL / "templates" / "render" / "scenes" / "presenter-example.js"
    assert scene.is_file()
    text = scene.read_text(encoding="utf-8")
    assert "loadPoses" in text and "PoseTrack" in text
    data = (SKILL / "templates" / "render" / "data.js").read_text(encoding="utf-8")
    assert "presenter-example" in data
    np_ = (ROOT / "tools" / "new_project.py").read_text(encoding="utf-8")
    assert "poses_src" in np_, "new projects must receive the pose library"
