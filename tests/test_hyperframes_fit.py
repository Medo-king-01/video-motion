from conftest import ROOT

REVIEW = ROOT / "docs" / "hyperframes-fit.md"


def test_hyperframes_review_exists_and_is_linked():
    assert REVIEW.is_file()
    index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "`hyperframes-fit.md`" in index


def test_hyperframes_review_keeps_the_measured_numbers():
    """The review is an evidence document: the numbers must stay what was measured."""
    text = REVIEW.read_text(encoding="utf-8")
    for value in ("0.9.9", "١٢٠/١٢٠", "٨.١ ثانية", "٤٥٦", "١٤٥"):
        assert value in text, value


def test_hyperframes_is_rejected_as_an_engine_and_a_dependency():
    text = REVIEW.read_text(encoding="utf-8")
    assert "لا نتبنّى HyperFrames كمحرك ولا كتبعية" in text
    # The two adopted ideas must be native work, not a vendored dependency.
    assert "تباين WCAG" in text
    assert "first_frame_empty" in text
    # Licence and offline constraints are the reasons, so they must be stated.
    lower = text.lower()
    assert "gsap" in lower and "apache-2.0" in lower
    assert "cdn.jsdelivr.net" in text


def test_hyperframes_review_does_not_claim_a_fourth_engine():
    text = REVIEW.read_text(encoding="utf-8")
    assert "رابعًا للمحركات" in text
    # P/K/R stay the engines of record.
    for engine in ("P/K/R",):
        assert engine in text
