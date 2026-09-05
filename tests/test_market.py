from src.algorithms._common import encode_job_features
from src.algorithms.clustering import cluster_jobs
from src.data.market import add_job_category, classify_job_category, stratified_sample_jobs
from src.data.schema import JOB_COLUMNS
from src.services.job_service import summarize_jobs
from tests.sample_data import build_sample_frame


def test_classify_job_category_prefers_title_over_industry() -> None:
    assert classify_job_category("Java开发工程师（财务系统）", "金融") == "技术"
    assert classify_job_category("财务专员", "互联网") == "财务"
    assert classify_job_category("销售顾问", "批发/零售") == "销售"
    assert classify_job_category("行政文员", "企业服务") == "行政"
    assert classify_job_category("机械工程师", "计算机软件") == "制造"
    assert classify_job_category("岗位", "财务/审计/税务") == "财务"


def test_stratified_sample_is_reproducible_and_reports_shortfall() -> None:
    jobs = build_sample_frame().head(6).copy()
    jobs["industry"] = ""
    jobs.loc[:5, "title"] = [
        "财务专员", "销售顾问", "行政文员", "机械工程师", "其他职位", "Java开发工程师"
    ]
    sampled_a, report_a = stratified_sample_jobs(jobs, per_category=2, random_state=7)
    sampled_b, report_b = stratified_sample_jobs(jobs, per_category=2, random_state=7)

    assert tuple(sampled_a.columns) == JOB_COLUMNS
    assert sampled_a["job_id"].tolist() == sampled_b["job_id"].tolist()
    assert report_a == report_b
    assert report_a["output_count"] == 6
    assert report_a["shortfall"] == ["技术", "财务", "销售", "行政", "制造", "其他"]
    assert set(report_a["after"].values()) == {1}


def test_cluster_uses_category_features_and_explains_category() -> None:
    jobs = build_sample_frame()
    categorized = add_job_category(jobs)
    features = encode_job_features(categorized, top_skills_n=1)
    assert any(column.startswith("job_category_") for column in features.columns)
    assert any(column.startswith("skill_") for column in features.columns)

    clustered, summaries = cluster_jobs(jobs, n_clusters=3)
    assert list(clustered.columns) == list(JOB_COLUMNS) + ["cluster_id"]
    assert all("dominant_category" in summary for summary in summaries.values())


def test_summary_uses_the_same_whitelisted_skills_as_analysis() -> None:
    jobs = build_sample_frame().head(2).copy()
    jobs.loc[0, "skills"] = "Python;要求数据开发经验;非外包类"
    summary = summarize_jobs(jobs)
    top = dict(summary["top_skills"])
    assert "要求数据开发经验" not in top
    assert "非外包类" not in top
    assert top["Python"] == 2
