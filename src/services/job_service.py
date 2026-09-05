import math

import numpy as np
import pandas as pd

from src.algorithms._common import balanced_top_skills, split_skills
from src.data.market import JOB_CATEGORIES, add_job_category
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
    for key in ("city", "work_type", "experience", "education", "industry", "company_nature"):
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
        for skill in split_skills(value):
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
    return {
        "job_count": int(len(result)),
        "salary_count": int(len(salaries)),
        "salary_min": float(salaries.min()) if not salaries.empty else None,
        "salary_max": float(salaries.max()) if not salaries.empty else None,
        "salary_avg": float(salaries.mean()) if not salaries.empty else None,
        "top_skills": sorted(skill_counts.items(), key=lambda item: (-item[1], item[0]))[:10],
        "balanced_top_skills": balanced_top_skills(result, 10) if not result.empty else [],
        "category_metrics": category_metrics(result),
    }


def category_metrics(jobs: pd.DataFrame) -> list[dict[str, object]]:
    """返回各岗位类别的数量占比和有效技能覆盖率。"""
    result = add_job_category(_canonical_jobs(jobs))
    total = len(result)
    metrics: list[dict[str, object]] = []
    for category in JOB_CATEGORIES:
        group = result[result["job_category"] == category]
        covered = sum(bool(split_skills(value)) for value in group["skills"].fillna(""))
        count = len(group)
        metrics.append(
            {
                "category": category,
                "job_count": count,
                "job_share": count / total if total else 0.0,
                "skill_coverage": covered / count if count else 0.0,
            }
        )
    return metrics


def education_distribution(jobs: pd.DataFrame, top_k: int = 6) -> list[dict[str, object]]:
    """按学历统计岗位数量，供市场概览页绘制分布图。"""
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise ValueError(f"top_k 必须是正整数，实际为: {top_k!r}")
    result = _canonical_jobs(jobs)
    education = result["education"].fillna("").astype(str).str.strip().replace("", "不限")
    counts = education.value_counts().head(top_k)
    return [
        {"education": str(label), "count": int(count)}
        for label, count in counts.items()
    ]


def paginate_jobs(
    jobs: pd.DataFrame,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, object]:
    """返回岗位分页结果及稳定的分页元数据。

    ``page`` 从 1 开始；空结果的 ``total_pages`` 为 0；请求超过末页时
    自动落到最后一页，避免筛选条件变化后页面出现空白页。
    """
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise ValueError(f"page 必须是正整数，实际为: {page!r}")
    if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size < 1:
        raise ValueError(f"page_size 必须是正整数，实际为: {page_size!r}")
    result = _canonical_jobs(jobs)
    total = len(result)
    total_pages = math.ceil(total / page_size) if total else 0
    current_page = min(page, total_pages) if total_pages else 1
    start = (current_page - 1) * page_size
    items = result.iloc[start : start + page_size].reset_index(drop=True)
    return {
        "items": items,
        "total": total,
        "page": current_page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def salary_distribution(jobs: pd.DataFrame, step: float = 5000.0) -> list[dict[str, object]]:
    """按 ``salary_avg`` 生成薪资分桶分布，供页面绘图。

    - ``step``：分桶宽度（元/月），默认 5000，支持正数（含小数）步长；
    - ``step`` 非正数时始终抛出 ValueError（与数据是否为空无关）；
    - 空数据或没有有效薪资时返回空列表（统一空结果状态）；
    - 返回 ``[{"range": "0-5000", "min": 0, "max": 5000, "count": 1}, ...]``，
      每个桶覆盖左闭右开区间，分桶宽度为 ``step``。
    """
    step = float(step)
    if step <= 0:
        raise ValueError(f"step 必须为正数，实际为: {step!r}")
    result = _canonical_jobs(jobs)
    salaries = pd.to_numeric(result["salary_avg"], errors="coerce").dropna()
    if salaries.empty:
        return []
    values = salaries.to_numpy(dtype=float)
    low = math.floor(float(values.min()) / step) * step
    # 桶为左闭右开：[e_i, e_{i+1})；末边必须严格大于最大值，
    # 使恰好落在 step 整数倍边界（如 5000）的薪资归入下一个桶，
    # 而不是因 numpy.histogram 末桶右闭而被多算进前一个桶。
    span = (float(values.max()) - low) / step
    num_bins = int(round(span, 10)) + 1
    edges = [round(low + i * step, 6) for i in range(num_bins + 1)]
    counts, _ = np.histogram(values, bins=edges)
    return [
        {
            "range": f"{e0:.15g}-{e1:.15g}",
            "min": int(e0) if float(e0).is_integer() else e0,
            "max": int(e1) if float(e1).is_integer() else e1,
            "count": int(counts[i]),
        }
        for i, (e0, e1) in enumerate(zip(edges, edges[1:]))
    ]
