"""The technique library: a measured catalogue, a reproducible draw, and no length rule.

The draw is the point. An agent choosing by hand picks the same fade-up, push-in and end card in
every film; these tests pin that the draw actually varies with the seed, respects the energy and
format filters, never repeats an id, and stays connected to the docs.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "techniques.py"
LIB = ROOT / "assets" / "techniques.json"
sys.path.insert(0, str(ROOT / "tools"))

import techniques  # noqa: E402

DATA = techniques.load(LIB)


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


def test_library_is_valid():
    assert techniques.validate(DATA) == []


GL_TRANSITIONS_DIR = ROOT / "assets" / "gl-transitions"


def _gl_shader(e: dict) -> Path:
    # gl-* entries point at a real GLSL file shipped in-repo — that is their build artifact.
    return GL_TRANSITIONS_DIR / Path(e.get("glsl_file", "")).name


def test_library_shape():
    picks = DATA["techniques"]
    assert len(picks) >= 30, "a draw from fewer than 30 entries converges again"
    ids = {e["id"] for e in picks}
    assert len(ids) == len(picks)
    order = DATA["format"]["reel"]["order"]
    assert set(order) <= {e["category"] for e in picks}
    for e in picks:
        if e.get("source") == "gl-transitions":
            # shader references: the "how" is one line by design; the artifact must exist
            assert e["glsl_file"], f"{e['id']}: gl-transition entry without glsl_file"
            assert _gl_shader(e).is_file(), f"{e['id']}: missing shader {e['glsl_file']}"
        else:
            assert len(e["how"]) > 60, f"{e['id']}: 'how' must be a build step, not a mood"
        assert e["primitive"] in techniques.PRIMITIVES
        assert e["role"] in techniques.ROLES


API_SURFACE = sorted({
    n for f in [*(ROOT / "medo-motion" / "templates" / "procedural-reels").glob("*.py"),
                *(ROOT / "medo-motion" / "templates" / "render" / "lib").glob("*.js")]
    for n in re.findall(r"(?:^def |^export (?:function|const|class) )(\w+)", f.read_text(encoding="utf-8"), re.M)
    if len(n) > 2
})


def test_each_recipe_names_a_real_api():
    """Every entry must be buildable the day it is drawn — via the contract of its family.

    The library is a merge of three authoring contracts, and the check honours all three
    instead of forcing the studio-API rule onto imports that were never authored against it:

    - studio-authored (`source` missing/"-"): `how` must name an API this studio ships,
      so the agent can reach for real code the day it draws the move;
    - rewritten imports (alansari-motion-library / opus-motion-library): measured recipe —
      `how` must be a real build step (> 60 chars) with a concrete spec, not a mood;
    - gl-transitions (GLSL shaders): `glsl_file` must reference a shader that ships in-repo,
      and the entry must record its `uniforms` (possibly empty for parameterless shaders).
    """
    for e in DATA["techniques"]:
        source = e.get("source", "-")
        if source == "gl-transitions":
            assert e.get("glsl_file"), f"{e['id']}: gl-transition entry without glsl_file"
            assert _gl_shader(e).is_file(), f"{e['id']}: missing shader {e['glsl_file']}"
            assert isinstance(e.get("uniforms"), list), f"{e['id']}: uniforms must be a list"
        elif source == "-":
            assert any(api in e["how"] for api in API_SURFACE), f"{e['id']}: no known API in 'how'"
        else:  # rewritten imports: measured spec, reviewed and rewritten for this studio
            assert len(e["how"]) > 60, f"{e['id']}: 'how' must be a build step, not a mood"
            assert len(e["how"]) < 2000, f"{e['id']}: 'how' drifted into prose"
            # `evidence` is a 0–9 score (0 = none), never falsy-checked; the authoring
            # contract for imports is a complete, measured spec triple.
            assert e.get("summary") and e.get("timing") and e.get("use_when"), \
                f"{e['id']}: import missing summary/timing/use_when"


def test_recipes_were_rewritten_for_this_studio():
    """The library is adapted from cinetic (MIT); a copied React recipe would mean it was not."""
    foreign = ("useCurrentFrame", "AbsoluteFill", "Remotion", "gsap", "npm ", "src/brand/tokens")
    for e in DATA["techniques"]:
        for token in foreign:
            assert token not in e["how"], f"{e['id']}: still speaks {token}"


def test_every_primitive_maps_to_a_shipped_module():
    need = {
        "type": ["procedural-reels/lib.py", "render/lib/kit.js"],
        "grid": ["procedural-reels/beat.py", "render/lib/beat.js"],
        "camera": ["procedural-reels/lib.py", "render/lib/motion.js"],
        "depth": ["procedural-reels/space3d.py", "render/lib/space3d.js"],
        "transition": ["procedural-reels/transition.py", "render/lib/transition.js"],
        "layout": ["procedural-reels/presenter.py", "render/lib/presenter.js"],
        "finish": ["render/lib/kit.js"],
        "blur": ["render/lib/kit.js"],
        "sound": ["procedural-reels/sfx.py"],
        "timeline": ["procedural-reels/lib.py"],
    }
    base = ROOT / "medo-motion" / "templates"
    for primitive, paths in need.items():
        assert primitive in techniques.PRIMITIVES
        for rel in paths:
            assert (base / rel).is_file(), f"primitive '{primitive}' points at missing {rel}"


def test_draw_is_reproducible():
    a = techniques.draw(DATA, 24, "calm", seed=41)
    b = techniques.draw(DATA, 24, "calm", seed=41)
    assert [p["id"] for p in a["picks"]] == [p["id"] for p in b["picks"]]
    assert a["seed"] == 41


def test_draw_varies_with_the_seed():
    plans = {tuple(p["id"] for p in techniques.draw(DATA, 24, "calm", seed=s)["picks"]) for s in range(12)}
    assert len(plans) >= 8, "the draw must not converge on one plan"


def test_plan_size_comes_from_the_length():
    fmt = DATA["format"]["reel"]
    assert techniques.plan_size(fmt, 10, "calm") == techniques.MIN_PICKS
    assert techniques.plan_size(fmt, 24, "calm") == 7
    assert techniques.plan_size(fmt, 24, "medium") > techniques.plan_size(fmt, 24, "calm")
    assert techniques.plan_size(fmt, 600, "calm") == len(fmt["order"])


def test_calm_never_draws_a_high_energy_move():
    for seed in range(30):
        for p in techniques.draw(DATA, 30, "calm", seed=seed)["picks"]:
            assert p["energy"] != "high", f"seed {seed} drew {p['id']}"


def test_energy_high_can_draw_high():
    drawn = {p["id"] for seed in range(20) for p in techniques.draw(DATA, 30, "high", seed=seed)["picks"]}
    assert any(e["energy"] == "high" and e["id"] in drawn for e in DATA["techniques"])


def test_no_id_repeats_and_signatures_are_budgeted():
    for seed in range(20):
        picks = techniques.draw(DATA, 45, "medium", seed=seed)["picks"]
        ids = [p["id"] for p in picks]
        assert len(ids) == len(set(ids))
        sigs = sum(1 for p in picks if p["role"] == "signature")
        assert sigs <= (2 if len(picks) >= 10 else 1)


def test_exclude_rerolls_and_category_filters():
    first = techniques.draw(DATA, 24, "calm", seed=41)["picks"][0]
    second = techniques.draw(DATA, 24, "calm", seed=41, exclude=[first["id"]])["picks"]
    assert first["id"] not in [p["id"] for p in second]
    camera = techniques.draw(DATA, 24, "calm", seed=3, only="camera")["picks"]
    assert camera and all(p["category"] == "camera" for p in camera)


def test_from_plan_reads_the_vo_length(tmp_path):
    plan = tmp_path / "beats.json"
    plan.write_text(json.dumps({"duration": 18.4, "scenes": []}), encoding="utf-8")
    out = tmp_path / "picks.json"
    r = run("--from-plan", str(plan), "--json", str(out), "--seed", "5")
    assert r.returncode == 0, r.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["seconds"] == 18.4
    assert len(payload["picks"]) == techniques.plan_size(DATA["format"]["reel"], 18.4, "calm")
    assert {"id", "how", "timing", "bans"} <= set(payload["picks"][0])


def test_from_plan_without_a_duration_asks_for_the_vo(tmp_path):
    plan = tmp_path / "beats.json"
    plan.write_text(json.dumps({"duration": None, "scenes": []}), encoding="utf-8")
    r = run("--from-plan", str(plan))
    assert r.returncode == 2
    assert "vo_length.py" in r.stderr


def test_cli_list_show_validate():
    assert run("--validate").returncode == 0
    listing = run("--list", "--category", "camera")
    assert listing.returncode == 0 and "cam-" in listing.stdout
    shown = run("--show", "tr-velocity-handoff-cut")
    assert shown.returncode == 0 and "velocity" in shown.stdout.lower()
    assert run("--show", "no-such-id").returncode == 2


def test_ui_families_are_in_the_reel_order():
    """Screens are part of the grammar: the four UI families draw like every other move."""
    order = DATA["format"]["reel"]["order"]
    for cat in ("ui_choreography", "product_demo", "data_and_numbers", "micro_interaction"):
        entries = [e for e in DATA["techniques"] if e["category"] == cat]
        assert len(entries) >= 4, f"{cat}: {len(entries)} entries"
        assert cat in order, f"{cat} is never drawn"
    drawn = {p["id"] for seed in range(40) for p in techniques.draw(DATA, 40, "medium", seed=seed)["picks"]}
    ui = {e["id"] for e in DATA["techniques"]
          if e["category"] in ("ui_choreography", "product_demo", "data_and_numbers", "micro_interaction")}
    assert drawn & ui, "a 40 s reel never draws a UI move"


def test_ui_recipes_are_built_not_captured():
    """A screenshot would be someone else's pixels; every UI recipe names our own art layer."""
    ui = [e for e in DATA["techniques"] if e["category"] in
          ("ui_choreography", "product_demo", "data_and_numbers", "micro_interaction")]
    modules = ("kit.", "art.", "lib.", "presenter.", "beat.")
    for e in ui:
        assert any(api in e["how"] for api in API_SURFACE) or any(m in e["how"] for m in modules), \
            f"{e['id']}: built from what?"
        assert "screenshot" not in e["how"].lower(), f"{e['id']}: screenshots are not ours to use"


def test_docs_are_generated_from_the_library(tmp_path):
    out = tmp_path / "techniques.md"
    assert run("--markdown", str(out)).returncode == 0
    assert "Velocity handoff cut" in out.read_text(encoding="utf-8")
    assert "ty-pose-occlusion-title-reveal" in out.read_text(encoding="utf-8")
    docs = ROOT / "docs" / "techniques.md"
    assert docs.is_file(), "docs/techniques.md must exist (make techniques-doc)"
    assert run("--markdown", str(docs), "--check").returncode == 0, "docs/techniques.md is stale"


def test_pose_occlusion_title_recipe_uses_native_p_k_layers():
    """The Skillry idea is translated to our transparent pose art and native renderer APIs."""
    entry = next(e for e in DATA["techniques"] if e["id"] == "ty-pose-occlusion-title-reveal")
    assert entry["category"] == "typography"
    assert entry["evidence"] == 0, "new adaptation stays unproven until visually rendered and reviewed"
    for api in ("lib.text_sprite", "presenter.draw", "arabic.setArabic", "presenter.drawPresenter"):
        assert api in entry["how"]
    assert "transparent" in entry["summary"]
    assert "not assume an R port" in entry["how"]


# --- reference-only entries are catalogued but never drawn -------------------------------------

def _draws():
    """Every way a gl-transition could be picked: all energies, many seeds, long reels, forced sizes."""
    for energy in ("calm", "medium", "high"):
        for seed in range(40):
            yield techniques.draw(DATA, 24 + seed * 3, energy, seed=seed)
        yield techniques.draw(DATA, 600, energy, seed=7, n=len(DATA["format"]["reel"]["order"]))


def test_the_draw_can_reach_the_slot_where_gl_transitions_sit():
    """Guard against a vacuous pass: the category is in the reel order and a long draw fills past it."""
    order = DATA["format"]["reel"]["order"]
    assert "gl-transition" in order
    full = techniques.draw(DATA, 600, "high", seed=7, n=len(order))
    assert len(full["picks"]) >= order.index("gl-transition"), "the draw never gets as far as that slot"


def test_draw_never_returns_a_gl_transition():
    for result in _draws():
        drawn = [p["id"] for p in result["picks"] if p["category"] == "gl-transition" or p.get("source") == "gl-transitions"]
        assert drawn == [], f"seed {result['seed']} · {result['energy']}: drew a shader no engine renders: {drawn}"


def test_asking_for_the_category_by_name_draws_nothing_and_says_why(tmp_path):
    assert techniques.draw(DATA, 24, "calm", seed=1, only="gl-transition")["picks"] == []
    done = subprocess.run([sys.executable, str(ROOT / "tools" / "techniques.py"), "--draw", "--seconds", "24",
                           "--category", "gl-transition", "--seed", "1"], capture_output=True, text=True)
    assert done.returncode == 2 and "reference" in done.stderr and "transitions.json" in done.stderr


def test_the_exclusion_removes_nothing_from_the_library():
    entries = [e for e in DATA["techniques"] if e["category"] == "gl-transition"]
    assert len(entries) == 189 and "gl-transition" in techniques.categories(DATA)
    assert techniques.REFERENCE_ONLY == {"gl-transition"}
