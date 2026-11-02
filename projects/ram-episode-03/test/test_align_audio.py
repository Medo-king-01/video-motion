import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "tools" / "align_audio.py"
SPEC = importlib.util.spec_from_file_location("align_audio", MODULE_PATH)
ALIGN = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ALIGN)


class ExtractWordsTests(unittest.TestCase):
    def test_extracts_and_sorts_measured_words(self):
        result = ALIGN.extract_words({
            "segments": [
                {"words": [{"word": "العالم", "start": 0.8, "end": 1.2}]},
                {"words": [{"word": "أهلاً", "start": 0.1, "end": 0.5}]},
            ]
        })
        self.assertEqual(result, [
            {"text": "أهلاً", "start": 0.1, "end": 0.5},
            {"text": "العالم", "start": 0.8, "end": 1.2},
        ])

    def test_ignores_unaligned_tokens(self):
        self.assertEqual(
            ALIGN.extract_words({"segments": [{"words": [{"word": "مرحبا"}]}]}),
            []
        )

    def test_rejects_overlaps_instead_of_fabricating_timings(self):
        with self.assertRaisesRegex(ValueError, "overlapping"):
            ALIGN.extract_words({"segments": [{"words": [
                {"word": "الأولى", "start": 0.0, "end": 0.7},
                {"word": "الثانية", "start": 0.6, "end": 1.0},
            ]}]})

    def test_rejects_invalid_intervals(self):
        with self.assertRaisesRegex(ValueError, "invalid timing"):
            ALIGN.extract_words({"segments": [{"words": [
                {"word": "كلمة", "start": 1.0, "end": 0.5}
            ]}]})

if __name__ == "__main__":
    unittest.main()
