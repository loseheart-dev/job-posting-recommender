import unittest

from src.ui.pages import ABOUT_URL, _format_salary_summary, _format_skill_summary, _is_about_page_url


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


if __name__ == "__main__":
    unittest.main()
