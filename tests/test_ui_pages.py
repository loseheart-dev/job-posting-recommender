import unittest

import pandas as pd

from src.ui.pages import ABOUT_URL, _format_salary_summary, _format_skill_summary, _is_about_page_url
from src.ui.pages import _compact_salary_distribution, _tokens


class UiFormattingTest(unittest.TestCase):
    def test_salary_summary_is_readable(self) -> None:
        self.assertEqual(
            _format_salary_summary('{"count": 2, "mean": 12000, "min": 10000, "max": 14000}'),
            "2 个岗位 · 平均 12,000 元/月 · 区间 10,000–14,000 元/月",
        )

    def test_skill_summary_is_readable_and_handles_empty(self) -> None:
        self.assertEqual(_format_skill_summary('{"Python": 5, "SQL": 3}'), "Python（5） · SQL（3）")
        self.assertEqual(_format_skill_summary("{}"), "暂无技能记录")

    def test_about_page_url_is_exact(self) -> None:
        self.assertTrue(_is_about_page_url("http://localhost:8501/about.html"))
        self.assertFalse(_is_about_page_url("http://localhost:8501/"))
        self.assertEqual(ABOUT_URL, "/about.html")


class UiPagesTest(unittest.TestCase):
    def test_missing_tokens_are_hidden(self) -> None:
        self.assertEqual(_tokens(float("nan")), [])

    def test_high_salary_buckets_are_compacted(self) -> None:
        source = pd.DataFrame([
            {"min": 35_000, "max": 40_000, "range": "35000-40000", "count": 8},
            {"min": 40_000, "max": 45_000, "range": "40000-45000", "count": 2},
            {"min": 80_000, "max": 85_000, "range": "80000-85000", "count": 1},
        ])
        result = _compact_salary_distribution(source)
        self.assertEqual(result[["range", "count"]].to_dict("records"), [
            {"range": "35000-40000", "count": 8},
            {"range": "40000+", "count": 3},
        ])


if __name__ == "__main__":
    unittest.main()
