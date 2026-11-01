import json

from conftest import ROOT


def test_skillry_review_is_linked_from_the_agent_skill():
    review = ROOT / "docs" / "skillry-fit.md"
    assert review.is_file()
    skill = (ROOT / "medo-motion" / "SKILL.md").read_text(encoding="utf-8")
    assert "../docs/skillry-fit.md" in skill
    assert "--engine p|k|r|hybrid" in skill
    assert "no simultaneous engine layers" in skill


def test_skillry_adaptations_point_to_real_native_techniques():
    review = (ROOT / "docs" / "skillry-fit.md").read_text(encoding="utf-8")
    library = json.loads((ROOT / "assets" / "techniques.json").read_text(encoding="utf-8"))
    known_ids = {item["id"] for item in library["techniques"]}
    for technique in ("pd-cursor-does-the-demo", "ui-state-change-on-tap",
                      "pd-app-window-builds", "pd-before-after-hard-swap"):
        assert technique in known_ids
        assert technique in review


def test_review_recommends_audit_before_external_skill_installation():
    review = (ROOT / "docs" / "skillry-fit.md").read_text(encoding="utf-8").lower()
    assert "not recommended at this stage" in review
    assert "complete skill payload" in review
    assert "licence/redistribution terms" in review
