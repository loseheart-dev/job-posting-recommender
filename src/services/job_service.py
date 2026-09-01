import pandas as pd

from src.data.schema import FILTER_KEYS, JOB_COLUMNS


def _canonical_jobs(jobs: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in JOB_COLUMNS if column not in jobs.columns]
    if missing:
        raise ValueError(f"岗位数据缺少必要字段: {', '.join(missing)}")
    return jobs.loc[:, JOB_COLUMNS].copy()


def filter_jobs(jobs: pd.DataFrame, filters: dict[str, object]) -> pd.DataFrame:
    """按固定筛选字段返回岗位，不修改输入数据。"""
    result = _canonical_jobs(jobs)
    unknown = set(filters) - set(FILTER_KEYS)
    if unknown:
        raise ValueError(f"不支持的筛选字段: {', '.join(sorted(unknown))}")

    keyword = str(filters.get("keyword", "") or "").strip()
    if keyword:
        searchable = result[["title", "company", "skills", "description"]].fillna("").agg(" ".join, axis=1)
        result = result[searchable.str.contains(keyword, case=False, regex=False)]
    for key in ("city", "work_type", "experience"):
        value = str(filters.get(key, "") or "").strip()
        if value:
            result = result[result[key].fillna("").astype(str).str.contains(value, case=False, regex=False)]
    if filters.get("salary_min") not in (None, ""):
        result = result[result["salary_max"].fillna(float("-inf")) >= float(filters["salary_min"])]
    if filters.get("salary_max") not in (None, ""):
        result = result[result["salary_min"].fillna(float("inf")) <= float(filters["salary_max"])]
    return result.reset_index(drop=True)


def summarize_jobs(jobs: pd.DataFrame) -> dict[str, object]:
    """Return JSON-friendly summary fields consumed by the page."""
    result = _canonical_jobs(jobs)
    salaries = pd.to_numeric(result["salary_avg"], errors="coerce").dropna()
    skill_counts: dict[str, int] = {}
    for value in result["skills"].fillna(""):
        for skill in str(value).split(";"):
            skill = skill.strip()
            if skill:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
    return {
        "job_count": int(len(result)),
        "salary_count": int(len(salaries)),
        "salary_min": float(salaries.min()) if not salaries.empty else None,
        "salary_max": float(salaries.max()) if not salaries.empty else None,
        "salary_avg": float(salaries.mean()) if not salaries.empty else None,
        "top_skills": sorted(skill_counts.items(), key=lambda item: (-item[1], item[0]))[:10],
    }
