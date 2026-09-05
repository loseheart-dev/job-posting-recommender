"""KMeans 岗位聚类（郑维豪负责）。

对外接口：
- cluster_jobs(jobs, n_clusters=3) -> (DataFrame[..., cluster_id], {cluster_id: 群组说明})

基于技能/学历/经验/城市/薪资等编码特征做标准化后聚类，
返回带 cluster_id 的岗位表和每个群组的可读特征说明。
样本不足以支撑指定群组数或字段缺失时抛出明确中文错误。
"""

from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.algorithms._common import encode_job_features, top_skills, validate_jobs
from src.data.market import add_job_category
from src.data.schema import CLUSTER_OUTPUT_COLUMNS


def _cluster_summary(jobs: pd.DataFrame, cluster: int) -> dict[str, object]:
    """生成单个群组的可读说明。"""
    subset = jobs[jobs["cluster_id"] == cluster]
    summary: dict[str, object] = {"count": int(len(subset))}
    salary = pd.to_numeric(subset["salary_avg"], errors="coerce").dropna()
    if not salary.empty:
        summary["salary_avg"] = round(float(salary.mean()), 0)
        summary["salary_range"] = [
            round(float(salary.min()), 0),
            round(float(salary.max()), 0),
        ]
    else:
        summary["salary_avg"] = None
        summary["salary_range"] = None
    categorized = add_job_category(subset)
    summary["top_skills"] = [skill for skill, _ in top_skills(subset, 5)]
    summary["dominant_category"] = str(
        categorized["job_category"].value_counts().index[0]
    )
    top_skills_by_category: dict[str, list[str]] = {}
    for category, group in categorized.groupby("job_category", sort=True):
        category_top = top_skills(group, 3)
        if category_top:
            top_skills_by_category[str(category)] = [skill for skill, _ in category_top]
    summary["top_skills_by_category"] = top_skills_by_category
    if "education" in subset.columns:
        summary["dominant_education"] = str(
            subset["education"].fillna("未知").value_counts().index[0]
        )
    if "city" in subset.columns:
        summary["dominant_city"] = str(
            subset["city"].fillna("未知").value_counts().index[0]
        )
    return summary


def cluster_jobs(
    jobs: pd.DataFrame,
    n_clusters: int = 3,
    random_state: int = 42,
) -> tuple[pd.DataFrame, dict[int, dict[str, object]]]:
    """KMeans 岗位聚类。

    返回：
    - 岗位表：原字段 + cluster_id（保证包含 CLUSTER_OUTPUT_COLUMNS）；
    - 群组说明：{cluster_id: {count, salary_avg, salary_range, top_skills, ...}}。
    """
    validate_jobs(jobs)
    if n_clusters < 2:
        raise ValueError("n_clusters 至少为 2")
    if len(jobs) < n_clusters * 2:
        raise ValueError(
            f"岗位样本不足（{len(jobs)} 条，至少需要 {n_clusters * 2} 条）才能进行 {n_clusters} 类聚类"
        )

    # Derived category features keep a technology-heavy source from determining
    # every cluster through its global Top-N skills alone.
    feature_jobs = add_job_category(jobs)
    features = encode_job_features(feature_jobs, include_salary=True)
    feature_columns = [column for column in features.columns if column != "job_id"]
    X = features[feature_columns].astype(float)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = model.fit_predict(X_scaled)

    result = jobs.copy()
    result["cluster_id"] = labels
    descriptions = {
        int(cluster): _cluster_summary(result, int(cluster))
        for cluster in sorted(set(labels.tolist()))
    }
    return result, descriptions
