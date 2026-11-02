"""The reels text-animation catalog: extraction, studio-track translation, brand
safety, K/P numeric parity, and the styled caption renderer (engine K)."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess

import pytest
from conftest import ROOT, SKILL

CATALOG_PATH = SKILL / "motion" / "text-animations.json"
STYLES_JS = SKILL / "templates" / "render" / "lib" / "caption-styles.js"
CATALOG = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
ANIMS = {a["id"]: a for a in CATALOG["animations"]}


def _importer():
    spec = importlib.util.spec_from_file_location("text_animations_import", ROOT / "tools" / "text_animations_import.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_catalog_is_complete_and_well_formed():
    assert len(ANIMS) == 51
    assert set(CATALOG["families"]) == {"reels", "trending", "kinetic", "cyber", "cinematic"}
    required = {"id", "name", "family", "duration", "captionSafe", "boxed", "colorRole", "tracks", "keyframes"}
    for a in ANIMS.values():
        assert required <= set(a), a["id"]
        assert a["family"] in CATALOG["families"]
        assert a["duration"] > 0
        assert a["colorRole"] in {"paper", "salmon", "red", "ink"}
        assert a["split"] in {"word", "char"}


def test_tracks_are_valid_studio_motion_tracks():
    for a in ANIMS.values():
        for name, tr in a["tracks"].items():
            assert name.startswith("word."), (a["id"], name)
            ts = [k["t"] for k in tr]
            assert ts == sorted(ts), (a["id"], name)
            assert all(isinstance(k["v"], (int, float)) for k in tr), (a["id"], name)
            for k in tr[1:]:
                e = k.get("ease")
                assert e is None or isinstance(e, (str, list)), (a["id"], name, e)
                if isinstance(e, list):
                    assert len(e) == 4


def test_boxed_entries_are_not_caption_safe():
    for a in ANIMS.values():
        if a["boxed"]:
            assert not a["captionSafe"], a["id"]
    for bid in ("ctapill", "sticker", "hormozi", "wordbox", "lowerthird", "stamp"):
        assert ANIMS[bid]["boxed"], bid
    # the transform-only reels captions are safe
    for sid in ("fadetilt", "softfade", "zoompunch", "wordpop", "impact"):
        assert ANIMS[sid]["captionSafe"], sid


def test_entrance_presets_are_bounded_and_snappy():
    n = 0
    for a in ANIMS.values():
        if "entrance" not in a:
            continue
        n += 1
        e = a["entrance"]
        assert 0.2 <= e["enter"] <= 0.45, a["id"]
        assert a["captionSafe"], a["id"]
        for tr in e["tracks"].values():
            assert tr[0]["t"] == 0
            assert tr[-1]["t"] <= e["enter"] + 1e-6
    assert n >= 25


def test_tracks_carry_no_color_only_brand_roles():
    # numeric tracks must never embed a hex; color is a semantic role resolved by the renderer
    for a in ANIMS.values():
        for tr in a["tracks"].values():
            for k in tr:
                assert isinstance(k["v"], (int, float)), (a["id"], k)


def test_caption_styles_js_in_sync_with_catalog():
    tai = _importer()
    assert STYLES_JS.read_text(encoding="utf-8") == tai.emit_caption_styles_js(CATALOG)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_js_and_python_agree_on_catalog_tracks(tmp_path):
    from motion import timeline  # noqa: PLC0415

    a = ANIMS["fadetilt"]
    spec = {"duration": a["duration"], "tracks": a["tracks"]}
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    script = tmp_path / "check.mjs"
    script.write_text(
        "import { timeline } from " + json.dumps(str(SKILL / "templates" / "render" / "lib" / "motion.js")) + ";\n"
        "import { readFile } from 'node:fs/promises';\n"
        "const spec = JSON.parse(await readFile(process.argv[2], 'utf8'));\n"
        "const tl = timeline(spec);\n"
        "console.log(JSON.stringify([0, 0.2, 0.66, 1.5, 2.46, 3.0].map(t => tl.at(t))));\n",
        encoding="utf-8",
    )
    r = subprocess.run(["node", str(script), str(spec_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    js_values = json.loads(r.stdout)
    tl = timeline(spec)
    for t, js in zip([0, 0.2, 0.66, 1.5, 2.46, 3.0], js_values, strict=True):
        py = tl.at(t)
        for key in py:
            assert py[key] == pytest.approx(js[key], abs=1e-3), f"{key} @ {t}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_caption_renderer_all_styles_draw_without_error(tmp_path):
    script = tmp_path / "render.mjs"
    script.write_text(
        "import { drawWordCaption, activeWordAt, validateWordTimeline, STYLE_ALIAS } from "
        + json.dumps(str(SKILL / "templates" / "render" / "lib" / "captions.js")) + ";\n"
        "import { CAPTION_STYLE_IDS } from "
        + json.dumps(str(STYLES_JS)) + ";\n"
        """
const calls = { fillText: 0, stroke: 0, gradient: 0 };
const ctx = new Proxy({}, {
  get(t, prop) {
    if (prop === 'measureText') return () => ({ width: 220 });
    if (prop === 'createLinearGradient') return () => { calls.gradient++; return { addColorStop() {} }; };
    if (prop === 'fillText') return () => { calls.fillText++; };
    if (prop === 'stroke') return () => { calls.stroke++; };
    return () => {};
  },
  set() { return true; },
});
const words = [
  { text: 'قبل', start: 0.5, end: 0.9 },
  { text: 'ما', start: 0.9, end: 1.2 },
  { text: 'تشتري', start: 1.2, end: 1.8 },
];
validateWordTimeline(words);
if (activeWordAt(words, 1.0).text !== 'ما') throw new Error('activeWordAt broken');
if (activeWordAt(words, 0.1) !== null) throw new Error('pre-roll should be null');
const styles = ['pop', 'karaoke', 'underline', 'hormozi', ...Object.keys(STYLE_ALIAS), ...CAPTION_STYLE_IDS];
let drawn = 0;
for (const style of styles) {
  for (const t of [0.55, 0.7, 1.0, 1.4]) {
    const w = drawWordCaption(ctx, t, words, { W: 1080, H: 1920, style, theme: 'dark' });
    if (w) drawn++;
  }
}
// explicit pop still draws exactly one word and never stroke/gradient
calls.fillText = 0; calls.stroke = 0; calls.gradient = 0;
drawWordCaption(ctx, 1.0, words, { W: 1080, H: 1920, style: 'pop' });
if (calls.fillText !== 1 || calls.stroke !== 0 || calls.gradient !== 0) throw new Error('explicit pop changed');
// no default: omitting style must fail loudly
let threw = false;
try { drawWordCaption(ctx, 1.0, words, { W: 1080, H: 1920 }); } catch { threw = true; }
if (!threw) throw new Error('missing style should be rejected (no default look)');
// karaoke uses a gradient sweep; underline strokes
calls.gradient = 0; drawWordCaption(ctx, 1.0, words, { W: 1080, H: 1920, style: 'karaoke' });
if (calls.gradient < 1) throw new Error('karaoke should sweep a gradient');
calls.stroke = 0; drawWordCaption(ctx, 1.0, words, { W: 1080, H: 1920, style: 'underline' });
if (calls.stroke < 1) throw new Error('underline should stroke');
console.log(JSON.stringify({ styles: styles.length, drawn, ok: true }));
""",
        encoding="utf-8",
    )
    r = subprocess.run(["node", str(script)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["ok"] and out["drawn"] > 0
    assert out["styles"] >= 30


def test_generated_presets_are_in_sync_across_engines():
    tai = _importer()
    js = tai.emit_caption_styles_js(CATALOG)
    py = tai.emit_caption_styles_py(CATALOG)
    assert (SKILL / "templates" / "render" / "lib" / "caption-styles.js").read_text(encoding="utf-8") == js
    assert (SKILL / "templates" / "remotion" / "src" / "lib" / "caption-styles.js").read_text(encoding="utf-8") == js
    assert (SKILL / "templates" / "procedural-reels" / "caption_styles.py").read_text(encoding="utf-8") == py


def test_shared_caption_motion_and_direction_modules_are_identical():
    for name in ("caption-motion.js", "text-direction.js"):
        k = (SKILL / "templates" / "render" / "lib" / name).read_text(encoding="utf-8")
        r = (SKILL / "templates" / "remotion" / "src" / "lib" / name).read_text(encoding="utf-8")
        assert k == r, name


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_caption_transform_js_python_parity(tmp_path):
    from caption_motion import caption_transform  # noqa: PLC0415

    styles = ["pop", "karaoke", "underline", "hormozi", "fadetilt", "zoompunch", "impact", "elastic"]
    samples = [(0.0, 0.6), (0.05, 0.6), (0.2, 0.6), (0.45, 0.6), (0.6, 0.6)]
    spec = {"styles": styles, "samples": samples}
    (tmp_path / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    script = tmp_path / "check.mjs"
    script.write_text(
        "import { captionTransform } from " + json.dumps(str(SKILL / "templates" / "render" / "lib" / "caption-motion.js")) + ";\n"
        "import { readFile } from 'node:fs/promises';\n"
        "const { styles, samples } = JSON.parse(await readFile(process.argv[2], 'utf8'));\n"
        "const out = styles.map(s => samples.map(([e, d]) => captionTransform(s, e, d)));\n"
        "console.log(JSON.stringify(out));\n",
        encoding="utf-8",
    )
    r = subprocess.run(["node", str(script), str(tmp_path / "spec.json")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    js = json.loads(r.stdout)
    for style, row in zip(styles, js, strict=True):
        for (e, d), jsv in zip(samples, row, strict=True):
            pyv = caption_transform(style, e, d)
            for key in ("opacity", "x", "y", "rotate", "scale", "blur", "underlineP", "karaokeP"):
                assert pyv[key] == pytest.approx(jsv[key], abs=1e-3), f"{style}.{key} @ {e}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_missing_style_is_rejected_in_js():
    script = "import { captionTransform } from " + json.dumps(str(SKILL / "templates" / "render" / "lib" / "caption-motion.js")) + ";\n"
    script += "let threw=false; try{captionTransform(undefined,0,0.5);}catch{threw=true;} if(!threw) throw new Error('no default');\n"
    script += "let threw2=false; try{captionTransform('not-a-style',0,0.5);}catch{threw2=true;} if(!threw2) throw new Error('unknown accepted');\n"
    script += "console.log('ok');\n"
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "ok"
