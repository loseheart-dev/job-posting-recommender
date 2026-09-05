import unittest

import pandas as pd

from src.data.schema import (
    CLUSTER_OUTPUT_COLUMNS,
    COMPANY_PROFILE_COLUMNS,
    JOB_COLUMNS,
    JobRecord,
    MULTI_FACTOR_RECOMMENDATION_COLUMNS,
    RECOMMENDATION_COLUMNS,
    SALARY_FACTOR_COLUMNS,
    SKILL_GRAPH_KEYS,
)
from src.services.analysis_service import (
    company_profile,
    job_cluster,
    recommend_jobs,
    recommend_jobs_multifactor,
    salary_factor_analysis,
    salary_prediction,
    skill_graph,
)


def _sample_jobs(size: int = 12) -> pd.DataFrame:
    """构造符合 21 列标准岗位表的小型样例（含薪资、城市、学历、公司等差异）。"""
    cities = ["上海", "北京", "杭州", "深圳"]
    educations = ["本科", "硕士"]
    titles = ["数据分析工程师", "后端开发工程师", "算法工程师", "数据开发工程师"]
    skills = ["Python;SQL", "Python;Java", "SQL;Excel", "Python;机器学习"]
    rows = []
    for i in range(1, size + 1):
        rows.append(JobRecord(
            f"j{i:02d}",
            titles[i % len(titles)],
            skills[i % len(skills)],
            company=f"示例公司{i % 5}",
            city=cities[i % len(cities)],
            work_type="全职",
            experience="1-3年" if i % 2 else "3-5年",
            education=educations[i % len(educations)],
            description="负责数据相关岗位的日常工作与项目交付",
            salary_min=8000,
            salary_max=20000,
            salary_avg=10000 + i * 500,
            source="BOSS直聘",
            crawled_at="2026-01-01T00:00:00Z",
        ).to_dict())
    return pd.DataFrame(rows)[list(JOB_COLUMNS)]


def _empty_jobs() -> pd.DataFrame:
    return pd.DataFrame(columns=JOB_COLUMNS)


class AnalysisServiceNormalTest(unittest.TestCase):
    def setUp(self):
        self.jobs = _sample_jobs()

    def test_salary_factor_analysis(self):
        out = salary_factor_analysis(self.jobs)
        self.assertFalse(out.empty)
        self.assertEqual(list(out.columns), list(SALARY_FACTOR_COLUMNS))

    def test_salary_prediction(self):
        out, metrics = salary_prediction(self.jobs)
        self.assertIn("predicted_salary", out.columns)
        self.assertIn("mae", metrics)
        self.assertIn("r2", metrics)
        self.assertEqual(len(out), len(self.jobs))

    def test_job_cluster(self):
        out, descriptions = job_cluster(self.jobs, n_clusters=3)
        self.assertEqual(list(out.columns), list(CLUSTER_OUTPUT_COLUMNS))
        self.assertTrue(descriptions)

    def test_skill_graph(self):
        out = skill_graph(self.jobs)
        self.assertEqual(set(out), set(SKILL_GRAPH_KEYS))
        self.assertTrue(out["skill_frequency"])
        technical = skill_graph(self.jobs, category="技术")
        self.assertTrue(technical["skill_frequency"])

    def test_company_profile(self):
        out = company_profile(self.jobs)
        self.assertFalse(out.empty)
        self.assertEqual(list(out.columns), list(COMPANY_PROFILE_COLUMNS))

    def test_recommend_jobs_with_dict_profile(self):
        profile = {"target_role": "数据分析工程师", "skills": "Python;SQL", "preferred_city": "上海"}
        out = recommend_jobs(profile, self.jobs, top_k=5)
        self.assertFalse(out.empty)
        self.assertEqual(list(out.columns), list(RECOMMENDATION_COLUMNS))
        self.assertLessEqual(len(out), 5)

    def test_recommend_jobs_multifactor_with_dict_profile(self):
        profile = {
            "target_role": "数据分析", "skills": "Python;SQL", "preferred_city": "上海",
            "education": "本科", "expected_salary_min": 10000,
        }
        out = recommend_jobs_multifactor(profile, self.jobs, top_k=5)
        self.assertFalse(out.empty)
        self.assertEqual(list(out.columns), list(MULTI_FACTOR_RECOMMENDATION_COLUMNS))
        self.assertLessEqual(len(out), 5)

    def test_recommend_empty_data_returns_empty_by_contract(self):
        # 推荐函数遵循冻结契约：空表/空画像时返回空结果表（不抛错），页面按"无推荐结果"处理。
        empty = _empty_jobs()
        profile = {"target_role": "数据分析", "skills": "Python"}
        out = recommend_jobs(profile, empty)
        self.assertTrue(out.empty)
        self.assertEqual(list(out.columns), list(RECOMMENDATION_COLUMNS))
        out2 = recommend_jobs_multifactor(profile, empty)
        self.assertTrue(out2.empty)
        self.assertEqual(list(out2.columns), list(MULTI_FACTOR_RECOMMENDATION_COLUMNS))


class AnalysisServiceAbnormalTest(unittest.TestCase):
    def test_empty_data_raises_for_analysis(self):
        empty = _empty_jobs()
        for call in (
            lambda: salary_factor_analysis(empty),
            lambda: salary_prediction(empty),
            lambda: job_cluster(empty),
            lambda: skill_graph(empty),
            lambda: company_profile(empty),
        ):
            with self.assertRaises(ValueError):
                call()

    def test_insufficient_salary_raises(self):
        few = _sample_jobs(size=3)  # 薪资样本不足（<6）
        with self.assertRaises(ValueError):
            salary_prediction(few)


if __name__ == "__main__":
    unittest.main()
