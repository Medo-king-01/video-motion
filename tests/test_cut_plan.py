"""B4 cut plan: shots from deltas, a contract that refuses nonsense, and an executor that refuses to exist.

The planner is pure — most tests feed it a synthetic report so the arithmetic is visible. One
end-to-end test goes through a real encoded clip to prove the two CLIs still talk to each other.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import cut_plan  # noqa: E402
import video_ingest  # noqa: E402

FPS = 30
FRAMES = 90


def report(spikes: dict[int, float] | None = None) -> dict:
    """A 3-second, 90-frame report whose deltas spike at the given frame boundaries."""
    spikes = {29: 75.7, 59: 101.1} if spikes is None else spikes
    deltas = [round(0.4 + (i % 3) * 0.05, 3) for i in range(FRAMES - 1)]
    for index, value in spikes.items():
        deltas[index] = value
    return {
        "version": 1,
        "source": {"name": "clip.mp4", "sha256": "a3" * 32, "bytes": 4096},
        "video": {"width": 160, "height": 120, "fps": FPS, "duration": 3.0, "frames": FRAMES,
                  "vfr": False, "codec": "mpeg4", "container": "mp4"},
        "sampling": {"grid": [16, 9], "decoded": FRAMES, "step": 1, "maxFrames": 7200},
        "deltas": deltas,
    }


def plan() -> dict:
    return cut_plan.build_plan(report())


# ---------------------------------------------------------------- building
def test_the_plan_splits_on_delta_spikes() -> None:
    p = plan()
    assert [c["id"] for c in p["cuts"]] == ["cut-01", "cut-02", "cut-03"]
    assert [(c["in"], c["out"]) for c in p["cuts"]] == [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0)]
    assert [c["reason"] for c in p["cuts"]] == ["first-shot", "visual-cut", "visual-cut"]
    assert p["cuts"][1]["score"] == 75.7
    assert all(c["keep"] for c in p["cuts"])


def test_the_plan_tiles_the_source_and_counts_its_seconds() -> None:
    p = plan()
    assert p["cuts"][0]["in"] == 0
    assert p["cuts"][-1]["out"] == p["source"]["duration"]
    assert p["totals"] == {"shots": 3, "keptSeconds": 3.0, "rejectedSeconds": 0.0, "duration": 3.0}


def test_the_plan_is_deterministic() -> None:
    assert plan() == plan()


def test_the_source_hash_carries_over() -> None:
    assert plan()["source"]["sha256"] == report()["source"]["sha256"]


def test_no_spikes_means_one_shot() -> None:
    p = cut_plan.build_plan(report(spikes={}))
    assert len(p["cuts"]) == 1
    assert (p["cuts"][0]["in"], p["cuts"][0]["out"]) == (0.0, 3.0)
    assert p["cuts"][0]["reason"] == "first-shot"


def test_a_higher_threshold_finds_fewer_cuts() -> None:
    p = cut_plan.build_plan(report(), threshold=250)
    assert len(p["cuts"]) == 1


def test_min_shot_folds_short_shots_together() -> None:
    p = cut_plan.build_plan(report(), min_shot=1.5)
    assert len(p["cuts"]) == 1
    assert p["cuts"][0]["out"] == 3.0


def test_the_last_shot_is_pinned_to_the_measured_duration() -> None:
    odd = report()
    odd["video"]["duration"] = 3.01
    p = cut_plan.build_plan(odd)
    assert p["cuts"][-1]["out"] == pytest.approx(3.01)


# ---------------------------------------------------------------- contract
def test_a_fresh_plan_is_valid() -> None:
    assert cut_plan.validate(plan()) == []


def mutate(fn) -> dict:
    p = copy.deepcopy(plan())
    fn(p)
    return p


@pytest.mark.parametrize(("edit", "code", "needle"), [
    (lambda p: p.update(version=2), "C00", "version"),
    (lambda p: p.update(note="hello"), "C01", "unknown fields"),
    (lambda p: p.pop("totals"), "C01", "missing fields"),
    (lambda p: p["cuts"][1].update(id="cut-01"), "C02", "duplicate id"),
    (lambda p: p["cuts"][1].update(**{"in": 1.4}), "C02", "tile the source"),
    (lambda p: p["cuts"][2].update(out=4.0), "C03", "beyond source.duration"),
    (lambda p: p["cuts"][0].update(keep="yes"), "C04", "boolean"),
    (lambda p: p["cuts"][0].update(reason="magic"), "C02", "reason"),
    (lambda p: p["totals"].update(keptSeconds=9.0), "C06", "cuts give"),
    (lambda p: p["settings"].update(minShot=-1), "C05", "minShot"),
    (lambda p: p["source"].update(sha256="abc"), "C00", "sha256"),
    (lambda p: p["cuts"][0].update(out=0.0), "C03", "in < out"),
])
def test_broken_plans_are_refused_with_codes(edit, code: str, needle: str) -> None:
    errors = cut_plan.validate(mutate(edit))
    assert any(error.startswith(code) and needle in error for error in errors), errors


def test_a_plan_shorter_than_min_shot_is_refused() -> None:
    p = mutate(lambda q: q["settings"].update(minShot=2.0))
    p["totals"] = cut_plan.totals(p)
    errors = cut_plan.validate(p)
    assert any("shorter than settings.minShot" in error for error in errors), errors


def test_a_non_object_plan_is_refused() -> None:
    assert cut_plan.validate([]) == ["C00 root: plan must be an object"]


def test_a_report_with_wrong_delta_count_is_refused() -> None:
    bad = report()
    bad["deltas"] = bad["deltas"][:-1]
    with pytest.raises(cut_plan.PlanError, match="frames-1"):
        cut_plan.build_plan(bad)


# ---------------------------------------------------------------- review + edit
def test_review_prints_every_cut_and_the_totals() -> None:
    lines = cut_plan.review_lines(plan())
    text = "\n".join(lines)
    assert "cut-01" in text and "cut-03" in text
    assert "3 shots" in text and "kept 3.00s" in text


def test_set_keep_flips_one_cut_and_recounts() -> None:
    p = cut_plan.set_keep(plan(), "cut-02", False)
    assert p["cuts"][1]["keep"] is False
    assert p["totals"]["keptSeconds"] == 2.0
    assert p["totals"]["rejectedSeconds"] == 1.0
    assert cut_plan.validate(p) == []


def test_set_keep_rejects_an_unknown_id() -> None:
    with pytest.raises(cut_plan.PlanError, match="no cut with id"):
        cut_plan.set_keep(plan(), "cut-99", False)


# ---------------------------------------------------------------- preview
def test_the_preview_is_deterministic_svg() -> None:
    a = cut_plan.preview_svg(plan())
    b = cut_plan.preview_svg(plan())
    assert a == b
    assert a.count("<rect") == 4  # backdrop + three cuts
    assert "cut-02" in a


def test_the_preview_marks_rejected_cuts_red() -> None:
    p = cut_plan.set_keep(plan(), "cut-02", False)
    svg = cut_plan.preview_svg(p)
    assert cut_plan.PALETTE["red"] in svg and cut_plan.PALETTE["ink"] in svg


def test_the_html_preview_carries_the_table() -> None:
    html = cut_plan.preview_html(plan())
    assert "خطة القطع" in html
    assert html.count("<tr>") == 4  # header + three cuts
    assert "cut-01" in html


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "cut_plan.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=180)


def test_render_is_refused(tmp_path: Path) -> None:
    target = tmp_path / "plan.json"
    target.write_text(json.dumps(plan()), encoding="utf-8")
    result = run("render", str(target))
    assert result.returncode == 3
    assert "refused" in result.stderr


def test_the_cli_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "plan.json"
    source.write_text(json.dumps(plan()), encoding="utf-8")

    checked = run("check", str(source))
    assert checked.returncode == 0, checked.stderr
    assert "Valid plan" in checked.stdout

    reviewed = run("review", str(source))
    assert reviewed.returncode == 0 and "cut-02" in reviewed.stdout

    edited = run("set", str(source), "cut-03=reject")
    assert edited.returncode == 0, edited.stderr
    data = json.loads(source.read_text(encoding="utf-8"))
    assert data["cuts"][2]["keep"] is False
    assert data["totals"]["rejectedSeconds"] == 1.0

    out = tmp_path / "plan.html"
    previewed = run("preview", str(source), "-o", str(out))
    assert previewed.returncode == 0, previewed.stderr
    first = out.read_bytes()
    run("preview", str(source), "-o", str(out))
    assert out.read_bytes() == first
    assert b"cut-03" in first


def test_the_cli_reports_invalid_plans(tmp_path: Path) -> None:
    broken = mutate(lambda p: p["totals"].update(keptSeconds=99.0))
    target = tmp_path / "broken.json"
    target.write_text(json.dumps(broken), encoding="utf-8")
    result = run("check", str(target))
    assert result.returncode == 1
    assert "C06" in result.stderr


def test_the_cli_rejects_a_bad_set_value(tmp_path: Path) -> None:
    target = tmp_path / "plan.json"
    target.write_text(json.dumps(plan()), encoding="utf-8")
    assert run("set", str(target), "cut-01=maybe").returncode == 2
    assert run("set", str(target), "cut-01").returncode == 2
    assert run("set", str(target), "cut-99=reject").returncode == 2


# ---------------------------------------------------------------- end to end
def test_ingest_then_plan_on_a_real_clip(tmp_path: Path) -> None:
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    pytest.importorskip("av")
    clip = tmp_path / "clip.mp4"
    writer = cv2.VideoWriter(str(clip), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (160, 120))
    assert writer.isOpened()
    colors = [(20, 90, 20), (180, 40, 40), (200, 160, 40)]
    for index in range(90):
        frame = np.zeros((120, 160, 3), np.uint8)
        frame[:, :] = colors[index // 30]
        frame[40:70, (index * 3) % 130:(index * 3) % 130 + 30] = (30, 30, 30)
        writer.write(frame)
    writer.release()

    media = tmp_path / "media-report.json"
    assert video_ingest.main([str(clip), "-o", str(media)]) == 0
    target = tmp_path / "cut-plan.json"
    assert cut_plan.main(["build", str(media), "-o", str(target)]) == 0
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["source"]["sha256"] == video_ingest.sha256_file(clip)
    assert data["totals"]["shots"] >= 2
    assert cut_plan.validate(data) == []
    assert cut_plan.main(["check", str(target)]) == 0
