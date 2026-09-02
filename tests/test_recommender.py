"""丁伟哲推荐模块测试：正常案例 + 异常/空数据案例。

运行：.venv/Scripts/python -m tests.test_recommender
"""

import pandas as pd

from src.algorithms.recommender import recommend_jobs, recommend_jobs_multifactor
from src.data.schema import JOB_COLUMNS, MULTI_FACTOR_RECOMMENDATION_COLUMNS, RECOMMENDATION_COLUMNS, StudentProfile


def sample_jobs() -> pd.DataFrame:
    """符合 JOB_COLUMNS（21 列）的小型岗位样例表。"""
    return pd.DataFrame(
        [
            {
                "job_id": "1", "title": "数据分析实习生", "company": "示例科技",
                "company_intro": "数据服务", "company_size": "100-499人", "company_nature": "民营",
                "industry": "互联网", "city": "上海", "work_type": "实习", "experience": "在校生",
                "education": "本科", "skills": "Python;SQL;pandas", "description": "处理业务数据、输出分析报告",
                "benefits": "五险一金", "salary_text": "3-5K", "salary_min": 3000, "salary_max": 5000,
                "salary_avg": 4000, "source": "test", "source_url": "https://example.com/job/1",
                "crawled_at": "2026-09-01T10:00:00",
            },
            {
                "job_id": "2", "title": "大数据开发工程师", "company": "示例数据",
                "company_intro": "大数据平台", "company_size": "1000人以上", "company_nature": "上市",
                "industry": "大数据", "city": "上海", "work_type": "全职", "experience": "应届",
                "education": "本科", "skills": "Spark;Hadoop;SQL", "description": "负责大数据平台开发",
                "benefits": "年终奖", "salary_text": "15-25K", "salary_min": 15000, "salary_max": 25000,
                "salary_avg": 20000, "source": "test", "source_url": "https://example.com/job/2",
                "crawled_at": "2026-09-01T10:00:00",
            },
            {
                "job_id": "3", "title": "后端开发工程师", "company": "测试公司",
                "company_intro": "软件外包", "company_size": "500-999人", "company_nature": "合资",
                "industry": "软件开发", "city": "杭州", "work_type": "全职", "experience": "应届",
                "education": "本科", "skills": "Python;Linux", "description": "开发服务接口",
                "benefits": "双休", "salary_text": "9-12K", "salary_min": 9000, "salary_max": 12000,
                "salary_avg": 10500, "source": "test", "source_url": "https://example.com/job/3",
                "crawled_at": "2026-09-01T10:00:00",
            },
        ]
    )


def test_normal_data_profile_returns_ranked_rows() -> None:
    jobs = sample_jobs()
    profile = StudentProfile.from_mapping(
        {"target_role": "数据分析", "skills": "Python;SQL", "preferred_city": "上海", "experience": "在校生"}
    )
    result = recommend_jobs(profile, jobs, top_k=5)
    assert not result.empty
    assert list(result.columns) == list(RECOMMENDATION_COLUMNS)
    assert len(result) == 3
    # 岗位 1 与画像（数据分析 + Python/SQL + 上海 + 在校生）最匹配，应排第一
    assert result.iloc[0]["job_id"] == "1"
    assert result.iloc[0]["matched_skills"] in ("Python;SQL", "SQL;Python")
    assert "文本相似度" in result.iloc[0]["reason"]
    assert "匹配技能" in result.iloc[0]["reason"]
    assert all(result["missing_skills"].notna())


def test_profile_change_changes_ranking() -> None:
    jobs = sample_jobs()
    data_profile = StudentProfile.from_mapping({"target_role": "数据分析", "skills": "Python;SQL"})
    java_profile = StudentProfile.from_mapping({"target_role": "后端开发", "skills": "Java;Spring"})
    data_result = recommend_jobs(data_profile, jobs)
    java_result = recommend_jobs(java_profile, jobs)
    # 画像变化必须引起排序或匹配技能变化，结果不能写死
    assert not data_result.equals(java_result)
    assert java_result.iloc[0]["matched_skills"] == ""
    assert java_result.iloc[0]["missing_skills"] == "Java;Spring"


def test_city_and_experience_boost_reason() -> None:
    jobs = sample_jobs()
    profile = StudentProfile.from_mapping({"target_role": "大数据", "skills": "Spark;SQL", "preferred_city": "上海", "experience": "应届"})
    result = recommend_jobs(profile, jobs)
    assert result.iloc[0]["job_id"] == "2"  # 大数据 + Spark + 上海 + 应届 → 岗位 2
    assert "城市符合期望" in result.iloc[0]["reason"]
    assert "经验要求匹配" in result.iloc[0]["reason"]


def test_empty_jobs_returns_empty_frame() -> None:
    empty = pd.DataFrame(columns=JOB_COLUMNS)
    profile = StudentProfile.from_mapping({"target_role": "数据分析", "skills": "Python"})
    result = recommend_jobs(profile, empty)
    assert result.empty
    assert list(result.columns) == list(RECOMMENDATION_COLUMNS)


def test_empty_profile_returns_empty_frame() -> None:
    profile = StudentProfile()  # 无目标岗位且无技能
    result = recommend_jobs(profile, sample_jobs())
    assert result.empty


def test_no_common_text_returns_empty_frame() -> None:
    jobs = sample_jobs()
    profile = StudentProfile.from_mapping({"target_role": "zzzzqqqq", "skills": "xkyq"})
    result = recommend_jobs(profile, jobs)
    assert result.empty


def test_missing_columns_raise_clear_error() -> None:
    bad = pd.DataFrame([{"job_id": "1", "title": "岗位"}])  # 缺 skills 等必要字段
    profile = StudentProfile.from_mapping({"target_role": "数据分析"})
    try:
        recommend_jobs(profile, bad)
    except ValueError as error:
        assert "缺少必要字段" in str(error)
    else:
        raise AssertionError("缺字段应抛出明确错误")


def test_dict_profile_accepted() -> None:
    result = recommend_jobs({"target_role": "数据分析", "skills": "Python"}, sample_jobs())
    assert not result.empty


def test_multifactor_output_columns_and_probability() -> None:
    jobs = sample_jobs()
    profile = StudentProfile.from_mapping(
        {
            "target_role": "数据分析",
            "education": "本科",
            "major": "数据科学",
            "school": "某大学",
            "skills": "Python;SQL",
            "preferred_city": "上海",
            "work_years": 0,
            "work_experience": "课程项目",
            "expected_salary_min": 3000,
            "expected_salary_max": 6000,
            "experience": "在校生",
        }
    )
    result = recommend_jobs_multifactor(profile, jobs, top_k=5)
    assert not result.empty
    assert list(result.columns) == list(MULTI_FACTOR_RECOMMENDATION_COLUMNS)
    assert result.iloc[0]["job_id"] == "1"  # 数据画像 + 上海 + 在校生 + 薪资区间命中
    assert result.iloc[0]["company_size"] == "100-499人"
    assert result.iloc[0]["salary_range"] == "3000-5000 元/月"
    assert 0.0 <= result.iloc[0]["match_probability"] <= 1.0
    assert "学历符合（本科）" in result.iloc[0]["reason"]
    assert "薪资区间符合期望" in result.iloc[0]["reason"]
    assert "画像：学校某大学、工作年限0年、含工作经历" in result.iloc[0]["reason"]


def test_multifactor_profile_factors_change_ranking_and_reason() -> None:
    jobs = sample_jobs()
    data_profile = StudentProfile.from_mapping(
        {"target_role": "数据分析", "skills": "Python;SQL", "education": "硕士", "major": "统计学", "expected_salary_min": 5000, "expected_salary_max": 8000}
    )
    java_profile = StudentProfile.from_mapping(
        {"target_role": "后端开发", "skills": "Java;Spring", "education": "大专", "major": "计算机", "expected_salary_min": 20000, "expected_salary_max": 30000}
    )
    data_result = recommend_jobs_multifactor(data_profile, jobs)
    java_result = recommend_jobs_multifactor(java_profile, jobs)
    # 画像变化必须改变输出，不能写死
    assert not data_result.equals(java_result)
    assert data_result.iloc[0]["job_id"] == "1"  # 数据画像最匹配数据分析岗
    assert java_result.iloc[0]["missing_skills"] == "Java;Spring"  # Java 画像技能全缺失
    assert any("薪资区间低于期望" in reason for reason in java_result["reason"])  # 20-30K 期望高于部分岗位
    assert any("薪资区间符合期望" in reason for reason in java_result["reason"])  # 岗位 2 区间命中


def test_multifactor_empty_jobs_returns_empty_frame() -> None:
    empty = pd.DataFrame(columns=JOB_COLUMNS)
    result = recommend_jobs_multifactor({"target_role": "数据分析", "skills": "Python"}, empty)
    assert result.empty
    assert list(result.columns) == list(MULTI_FACTOR_RECOMMENDATION_COLUMNS)


def test_multifactor_missing_columns_raise_clear_error() -> None:
    bad = pd.DataFrame([{"job_id": "1", "title": "岗位"}])
    try:
        recommend_jobs_multifactor({"target_role": "数据分析"}, bad)
    except ValueError as error:
        assert "缺少必要字段" in str(error)
    else:
        raise AssertionError("缺字段应抛出明确错误")


def main() -> None:
    tests = [
        test_normal_data_profile_returns_ranked_rows,
        test_profile_change_changes_ranking,
        test_city_and_experience_boost_reason,
        test_empty_jobs_returns_empty_frame,
        test_empty_profile_returns_empty_frame,
        test_no_common_text_returns_empty_frame,
        test_missing_columns_raise_clear_error,
        test_dict_profile_accepted,
        test_multifactor_output_columns_and_probability,
        test_multifactor_profile_factors_change_ranking_and_reason,
        test_multifactor_empty_jobs_returns_empty_frame,
        test_multifactor_missing_columns_raise_clear_error,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"recommender contract tests passed ({len(tests)} cases)")


if __name__ == "__main__":
    main()
