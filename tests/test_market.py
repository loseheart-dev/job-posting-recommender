from src.algorithms._common import balanced_top_skills, encode_job_features
from src.algorithms.clustering import cluster_jobs
from src.data.market import (
    MARKET_SUPPLEMENT_CITIES,
    MARKET_SUPPLEMENT_KEYWORDS,
    add_job_category,
    classify_job_category,
)
from src.data.schema import JOB_COLUMNS
from src.services.job_service import category_metrics, summarize_jobs
from tests.sample_data import build_sample_frame


def test_classify_job_category_prefers_title_over_industry() -> None:
    assert classify_job_category("Java开发工程师（财务系统）", "金融") == "技术"
    assert classify_job_category("财务专员", "互联网") == "财务"
    assert classify_job_category("销售顾问", "批发/零售") == "销售"
    assert classify_job_category("行政文员", "企业服务") == "行政"
    assert classify_job_category("机械工程师", "计算机软件") == "制造"
    assert classify_job_category("岗位", "财务/审计/税务") == "财务"


def test_supplement_keywords_cover_shortfall_categories() -> None:
    assert set(("财务", "销售", "行政", "制造", "其他")) <= MARKET_SUPPLEMENT_KEYWORDS.keys()
    assert len(MARKET_SUPPLEMENT_CITIES) >= 10
    assert all(MARKET_SUPPLEMENT_KEYWORDS[category] for category in MARKET_SUPPLEMENT_KEYWORDS)


def test_cluster_uses_category_features_and_explains_category() -> None:
    jobs = build_sample_frame()
    categorized = add_job_category(jobs)
    features = encode_job_features(categorized, top_skills_n=1)
    assert any(column.startswith("job_category_") for column in features.columns)
    assert any(column.startswith("skill_") for column in features.columns)

    clustered, summaries = cluster_jobs(jobs, n_clusters=3)
    assert list(clustered.columns) == list(JOB_COLUMNS) + ["cluster_id"]
    assert all("dominant_category" in summary for summary in summaries.values())
    assert all("top_skills_by_category" in summary for summary in summaries.values())


def test_summary_uses_the_same_whitelisted_skills_as_analysis() -> None:
    jobs = build_sample_frame().head(2).copy()
    jobs.loc[0, "skills"] = "Python;要求数据开发经验;非外包类"
    summary = summarize_jobs(jobs)
    top = dict(summary["top_skills"])
    assert "要求数据开发经验" not in top
    assert "非外包类" not in top
    assert top["Python"] == 2


def test_category_metrics_and_balanced_skill_rank() -> None:
    jobs = build_sample_frame().head(5).copy()
    jobs.loc[:3, ["title", "skills"]] = ["后端开发工程师", "Python"]
    jobs.loc[4, ["title", "skills"]] = ["财务专员", "会计"]

    metrics = {item["category"]: item for item in category_metrics(jobs)}
    assert metrics["技术"]["job_count"] == 4
    assert metrics["财务"]["job_count"] == 1
    assert metrics["技术"]["skill_coverage"] == 1.0
    assert metrics["财务"]["skill_coverage"] == 1.0

    summary = summarize_jobs(jobs)
    assert summary["category_metrics"] == category_metrics(jobs)
    assert summary["balanced_top_skills"][:2] == [("Python", 0.5), ("会计", 0.5)]

    balanced = dict(balanced_top_skills(jobs, 2))
    assert balanced["Python"] == 0.5
    assert balanced["会计"] == 0.5
