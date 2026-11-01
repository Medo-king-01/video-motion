"""Arabic shaping invariants (the part that silently breaks every Latin-first tool)."""
from __future__ import annotations

import arabic_shape as A
import numpy as np
import pytest
from PIL import Image

RT = "rtl"


def test_sprite_is_ink_tight_with_6px_pad(cairo_bold):
    spr = A.text_sprite(cairo_bold, "مرحبا", 58, (255, 255, 255), True, 0)
    assert spr.ndim == 3 and spr.shape[2] == 4
    h, w = spr.shape[:2]
    assert h > 20 and w > 60
    # the sprite exists because it has ink, and it is not the raw em box
    assert (spr[..., 3] > 0).any()
    assert h < 58 * 2 and w < 58 * 6


def test_joins_and_orders_rtl(cairo_bold):
    """Shaping must differ from isolated letters: joined Arabic is narrower."""
    whole = A.measure(cairo_bold, "سلام", 64)[0]
    letters = sum(A.measure(cairo_bold, ch, 64)[0] for ch in "سلام")
    assert whole < letters * 0.85, "letters look unjoined (isolated forms)"


def test_runs_are_visual_order(cairo_bold):
    runs = A._runs("كلمة English", True)
    assert runs[0] == ("English", False), "an LTR word must come first visually in RTL text"
    assert runs[-1][0] == "كلمة"


def test_number_separators_stay_inside_the_number(cairo_bold):
    texts = [t for t, _ in A._runs("سعر 25,000 ج.م", True)]
    assert "25,000" in texts, texts
    assert "12:30" in [t for t, _ in A._runs("الساعة 12:30", True)]


def test_empty_text_is_safe(cairo_bold):
    spr = A.text_sprite(cairo_bold, "", 58)
    assert spr.shape[0] >= 1 and spr.shape[1] >= 1
    assert not (spr[..., 3] > 0).any()


def test_stroke_adds_a_frame_but_keeps_counters(cairo_bold):
    plain = A.text_sprite(cairo_bold, "ب", 96, (255, 255, 255), True, 0)
    bold = A.text_sprite(cairo_bold, "ب", 96, (255, 255, 255), True, 6, (0, 0, 0))
    assert bold.shape[0] > plain.shape[0] and bold.shape[1] > plain.shape[1]
    # a dilated *fill* would cover ~everything; the inner counter must stay open
    inner = bold[18:-18, 18:-18, 3] if min(bold.shape[:2]) > 40 else bold[..., 3]
    assert (inner < 255).any(), "stroke filled the glyph: counters are gone"


def test_render_is_deterministic(cairo_bold):
    a = A.text_sprite(cairo_bold, "اختبار", 48)
    b = A.text_sprite(cairo_bold, "اختبار", 48)
    assert np.array_equal(a, b)


def test_draw_centers_the_ink(cairo_bold):
    img = Image.new("RGBA", (600, 300), (0, 0, 0, 0))
    A.draw(img, (300, 150), cairo_bold, "مرحبا", 64, (255, 255, 255), True, "mm")
    alpha = np.array(img)[..., 3]
    ys, xs = np.where(alpha > 0)
    assert len(xs) > 0
    assert abs(xs.mean() - 300) < 25 and abs(ys.mean() - 150) < 25


@pytest.mark.parametrize("text", ["مرحبا بالعالم", "25,000 ج.م", "ChatGPT في 2024", "أهلاً"])
def test_mixed_content_renders_without_error(cairo_bold, text):
    spr = A.text_sprite(cairo_bold, text, 58, (255, 255, 255), True, 6, (0, 0, 0))
    assert (spr[..., 3] > 0).any()
