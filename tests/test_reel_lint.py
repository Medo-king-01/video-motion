"""The pre-render lint: the craft numbers become gates, and the reel length stays the VO's.

Two fixtures drive it: `good/` is a 24 s reel that passes every rule, `bad/` is the same reel with
every tell put back in. The important property is the one the project must never break — **no rule
here has an opinion about how long the reel is**.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "reel_lint.py"
FIX = ROOT / "tests" / "fixtures" / "reel"
GOOD, BAD = FIX / "good", FIX / "bad"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


def codes(result: subprocess.CompletedProcess) -> set[str]:
    """The codes the lint flagged (errors "!!" and warnings " ?"), not its passing lines."""
    out = set()
    for line in (result.stdout + result.stderr).splitlines():
        if line[:2] not in ("!!", " ?"):
            continue
        parts = line.strip(" ?!").split()
        if parts and parts[0][0] in "SCMKUT" and parts[0][1:].isdigit():
            out.add(parts[0])
    return out


def test_good_plan_passes_clean():
    r = run(str(GOOD))
    assert r.returncode == 0, r.stdout
    assert "0 error(s), 0 warning(s)" in r.stdout


def test_bad_plan_fails_on_the_real_tells():
    r = run(str(BAD))
    assert r.returncode == 1
    found = codes(r)
    for code in ["C01", "C03", "C02", "C07", "C08", "C10", "M01", "M02", "S05"]:
        assert code in found, f"{code} was not reported:\n{r.stdout}"


def test_strict_promotes_warnings():
    assert run(str(GOOD), "--strict").returncode == 0
    loose = run(str(BAD))
    strict = run(str(BAD), "--strict")
    assert (loose.returncode, strict.returncode) == (1, 1)
    # the good plan with one drifting cut is a warning, not an error — until --strict
    plan = json.loads((GOOD / "plan" / "beats.json").read_text(encoding="utf-8"))
    assert plan["scenes"][0]["events"], "fixture sanity"
    import shutil
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "drift"
        shutil.copytree(GOOD, proj)
        beats = json.loads((proj / "plan" / "beats.json").read_text(encoding="utf-8"))
        beats["scenes"][0]["end"] = beats["scenes"][1]["start"] = 3.17
        (proj / "plan" / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
        loose_run, strict_run = run(str(proj)), run(str(proj), "--strict")
        assert "S05" in codes(loose_run)
        assert loose_run.returncode == 0, loose_run.stdout
        assert strict_run.returncode == 1


def test_no_length_rule_anywhere(tmp_path):
    """An 11 s reel and a 95 s reel must both be able to pass: the VO decides the length."""
    good = json.loads((GOOD / "plan" / "beats.json").read_text(encoding="utf-8"))
    for seconds in (11.0, 95.0):
        proj = tmp_path / f"reel-{int(seconds)}"
        (proj / "plan").mkdir(parents=True)
        beats = {"duration": seconds, "fps": 30,
                 "scenes": [{"index": i + 1, "start": seconds * i / 4, "end": seconds * (i + 1) / 4,
                             "events": [{"t": 0.1, "what": "opening"}]} for i in range(4)]}
        (proj / "plan" / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
        styles = ["karaoke", "softFade", "zoomPunch", "underline"]
        direction = {"version": 3, "status": "directed", "decidedBy": "agent",
                     "concept": "text motion follows the spoken emphasis across the reel",
                     "scenes": [{"scene": i + 1, "captionStyle": styles[i], "captionWhy": f"scene {i+1} emphasis",
                                 "textStyles": {}, "textWhy": None} for i in range(4)]}
        (proj / "plan" / "text-direction.json").write_text(json.dumps(direction), encoding="utf-8")
        r = run(str(proj))
        assert r.returncode == 0, r.stdout
        assert f"timeline {seconds:g} s" in r.stdout, r.stdout
        assert "PASS" in r.stdout
    assert good["duration"] == 24.0


def test_copy_stretch_and_grid(tmp_path):
    proj = tmp_path / "stretch"
    (proj / "plan").mkdir(parents=True)
    beats = {"duration": 20.0, "fps": 30,
             "scenes": [{"index": 1, "start": 0.0, "end": 10.0, "events": [{"t": 0.2, "what": "a"},
                                                                          {"t": 3.0, "what": "b"}]},
                        {"index": 2, "start": 10.0, "end": 20.0, "events": [{"t": 10.5, "what": "c"}]}]}
    (proj / "plan" / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
    copy = {"pace": "calm", "bpm": 100, "copy": [
        {"scene": 1, "text": "كلام كتير", "start": 1.0, "end": 3.0, "mode": "build"},
        {"scene": 1, "text": "وكمان", "start": 4.0, "end": 5.0, "mode": "build"},
        {"scene": 2, "text": "وآخر حاجة", "start": 12.15, "end": 14.0, "mode": "build"},
    ]}
    (proj / "plan" / "copy.json").write_text(json.dumps(copy, ensure_ascii=False), encoding="utf-8")
    r = run(str(proj))
    found = codes(r)
    assert "C11" in found, r.stdout        # 12.15 s sits 150 ms off the 100 BPM grid
    assert "C06" not in found, r.stdout    # long text-free stretches are allowed

    # ...and the opposite: copy that never lets the picture breathe is flagged
    copy["copy"].append({"scene": 2, "text": "كمان", "start": 14.0, "end": 20.0, "mode": "build"})
    copy["copy"].append({"scene": 1, "text": "وكمان تاني", "start": 5.0, "end": 10.0, "mode": "build"})
    (proj / "plan" / "copy.json").write_text(json.dumps(copy, ensure_ascii=False), encoding="utf-8")
    dense = run(str(proj))
    assert "C06" in codes(dense), dense.stdout


def test_ui_inserts_need_an_interaction(tmp_path):
    """A screen that never changes is a mock, not a scene — and it needs time to read."""
    import json as js
    proj = tmp_path / "ui"
    (proj / "plan").mkdir(parents=True)
    beats = {"duration": 12.0, "fps": 30, "scenes": [
        {"index": 1, "start": 0.0, "end": 5.0, "ui": True, "events": [{"t": 0.6, "what": "tap"}]},
        {"index": 2, "start": 5.0, "end": 6.0, "ui": True},
        {"index": 3, "start": 6.0, "end": 12.0, "ui": True, "events": [{"t": 6.5, "what": "tick"}]},
    ]}
    (proj / "plan" / "beats.json").write_text(js.dumps(beats), encoding="utf-8")
    r = run(str(proj))
    assert "U01" in codes(r), r.stdout
    messages = [ln for ln in r.stdout.splitlines() if "U01" in ln]
    assert any("no interaction" in m for m in messages), messages
    assert any("1.00 s" in m for m in messages), messages     # the 1 s insert is too short
    assert not any("scene 1" in m for m in messages)          # 5 s with a tap is fine


def test_json_report(tmp_path):
    out = tmp_path / "qa" / "lint.json"
    r = run(str(BAD), "--json", str(out))
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["failed"] is True
    assert payload["duration"] == 24.0
    assert {i["level"] for i in payload["items"]} == {"error", "warn", "ok"}
    assert r.returncode == 1


def test_scan_code_finds_banned_looks_and_honours_allow(tmp_path):
    proj = tmp_path / "scan"
    (proj / "plan").mkdir(parents=True)
    (proj / "plan" / "beats.json").write_text(
        (GOOD / "plan" / "beats.json").read_text(encoding="utf-8"), encoding="utf-8")
    (proj / "plan" / "copy.json").write_text(
        (GOOD / "plan" / "copy.json").read_text(encoding="utf-8"), encoding="utf-8")
    (proj / "scenes.py").write_text(
        "def f():\n"
        "    sparkle(4, (243, 242, 241))          # sparkles for AI\n"
        "    crossfade(a, b, 0.5)\n"
        "    shake_flash(t)  # lint: allow shake\n", encoding="utf-8")
    r = run(str(proj), "--scan-code")
    assert "K01" in codes(r)
    assert r.stdout.count("K01") == 2, r.stdout     # sparkle + crossfade, not the allowed shake


def test_missing_plan_is_an_input_error(tmp_path):
    r = run(str(tmp_path))
    assert r.returncode == 2
    assert "vo_length.py" in r.stderr


def test_timeline_gaps_are_errors(tmp_path):
    """A gap between scenes must FAIL, not pass silently (overlap and gap are both S02)."""
    import shutil
    proj = tmp_path / "gap"
    shutil.copytree(GOOD, proj)
    beats = json.loads((proj / "plan" / "beats.json").read_text(encoding="utf-8"))
    beats["scenes"][1]["start"] += 0.5          # leave a 0.5 s hole after scene 1
    (proj / "plan" / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
    r = run(str(proj))
    assert r.returncode == 1, r.stdout
    assert "S02" in codes(r) and "gap" in r.stdout


def test_scan_code_covers_tsx(tmp_path):
    """Remotion templates are .tsx — the banned-look scan must read them too."""
    proj = tmp_path / "scan-ts"
    (proj / "plan").mkdir(parents=True)
    (proj / "plan" / "beats.json").write_text(
        (GOOD / "plan" / "beats.json").read_text(encoding="utf-8"), encoding="utf-8")
    (proj / "src").mkdir()
    (proj / "src" / "Scene.tsx").write_text(
        "export const S = () => <div>{confetti()}</div>;\n", encoding="utf-8")
    r = run(str(proj), "--scan-code")
    assert "K01" in codes(r), r.stdout


def test_raw_text_drawing_is_blocked_and_directed_helper_passes(tmp_path):
    import shutil
    proj = tmp_path / "raw-text"
    shutil.copytree(GOOD, proj)
    (proj / "scenes.py").write_text(
        "def draw(ctx):\n    ctx.fillText('عنوان', 10, 10)\n", encoding="utf-8")
    r = run(str(proj), "--scan-code")
    assert r.returncode == 1 and "T04" in codes(r), r.stdout
    (proj / "scenes.py").write_text(
        "from captions import draw_directed_text\n"
        "def draw(fr):\n    draw_directed_text(fr, 'عنوان', direction=D, scene=1, role='title',\n"
        "                                    t=0, start=0, end=1, cx=0, cy=0)\n", encoding="utf-8")
    r = run(str(proj), "--scan-code")
    assert "T04" not in codes(r), r.stdout


def test_every_lint_rule_is_documented():
    """The doc cannot drift from the tool: every code it can emit is in docs/craft.md."""
    import re
    doc = (ROOT / "docs" / "craft.md").read_text(encoding="utf-8")
    src = TOOL.read_text(encoding="utf-8")
    codes = sorted(set(re.findall(r'rep\.\w+\("([SCMKUT]\d{2})"', src)))
    assert len(codes) >= 18
    missing = [c for c in codes if c not in doc]
    assert not missing, f"undocumented lint codes: {missing}"


def test_the_name_slot_belongs_to_the_user(tmp_path):
    """A name/title/episode the user asked for is his copy, not a studio default.

    C07 still guards the studio's own wording (`نقدم لكم`, a filled-in `اسم السلسلة`), but a
    fragment the plan marks `approvedByUser` is executed word for word (AGENTS.md rule 1).
    """
    proj = tmp_path / "name"
    (proj / "plan").mkdir(parents=True)
    beats = {"duration": 8.0, "fps": 30,
             "scenes": [{"index": 1, "start": 0.0, "end": 8.0,
                         "events": [{"t": 0.2, "what": "title"}, {"t": 4.0, "what": "close"}]}]}
    (proj / "plan" / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
    copy = {"pace": "calm", "bpm": 100,
            "copy": [{"scene": 1, "text": "اسم السلسلة هنا", "start": 0.4, "end": 2.0, "mode": "build"}]}
    (proj / "plan" / "copy.json").write_text(json.dumps(copy, ensure_ascii=False), encoding="utf-8")
    assert "C07" in codes(run(str(proj))), "the studio's own placeholder wording must still fail"

    copy["copy"][0]["approvedByUser"] = True          # exactly what the user asked for
    (proj / "plan" / "copy.json").write_text(json.dumps(copy, ensure_ascii=False), encoding="utf-8")
    assert "C07" not in codes(run(str(proj)))
