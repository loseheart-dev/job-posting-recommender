"""丁伟哲推荐模块测试：正常案例 + 异常/空数据案例。

运行：.venv/Scripts/python tests/test_recommender.py
"""

import pandas as pd

from src.algorithms.recommender import recommend_jobs
from src.data.schema import JOB_COLUMNS, RECOMMENDATION_COLUMNS, StudentProfile


def sample_jobs() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "job_id": "1", "title": "数据分析实习生", "company": "示例科技", "city": "上海",
                "work_type": "实习", "experience": "在校生", "education": "本科",
                "skills": "Python;SQL;pandas", "description": "处理业务数据、输出分析报告",
                "salary_min": 3000, "salary_max": 5000, "salary_avg": 4000, "source": "test",
            },
            {
                "job_id": "2", "title": "大数据开发工程师", "company": "示例数据", "city": "上海",
                "work_type": "全职", "experience": "应届", "education": "本科",
                "skills": "Spark;Hadoop;SQL", "description": "负责大数据平台开发",
                "salary_min": 15000, "salary_max": 25000, "salary_avg": 20000, "source": "test",
            },
            {
                "job_id": "3", "title": "后端开发工程师", "company": "测试公司", "city": "杭州",
                "work_type": "全职", "experience": "应届", "education": "本科",
                "skills": "Python;Linux", "description": "开发服务接口",
                "salary_min": 9000, "salary_max": 12000, "salary_avg": 10500, "source": "test",
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
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"recommender contract tests passed ({len(tests)} cases)")


if __name__ == "__main__":
    main()
