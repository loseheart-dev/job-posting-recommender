"""招聘企业画像（郑维豪负责）。

对外接口：
- build_company_profiles(jobs) -> DataFrame[company, company_size, company_nature,
                                           industry, salary_summary, skill_summary]

按公司聚合：公司性质、规模、行业取最常见值；薪资与技能给出可 JSON
序列化的摘要。没有有效公司名的行不进入画像。
"""

from __future__ import annotations

import pandas as pd

from src.algorithms._common import salary_stats, top_skills, validate_jobs
from src.data.schema import COMPANY_PROFILE_COLUMNS


def _most_common(series: pd.Series) -> str:
    """取系列中出现次数最多的非空值；全为空返回空串，不做推断。"""
    values = series.fillna("").astype(str).str.strip()
    values = values[values != ""]
    if values.empty:
        return ""
    return str(values.mode().iloc[0])


def build_company_profiles(jobs: pd.DataFrame) -> pd.DataFrame:
    """构建招聘企业画像。

    每个公司一行；薪资摘要为 {count, mean, min, max}，
    技能摘要为 {技能: 出现次数}（取 Top 5）。
    """
    validate_jobs(jobs)
    if "company" not in jobs.columns:
        raise ValueError("岗位表缺少字段: company，无法生成企业画像")

    rows: list[dict[str, object]] = []
    companies = jobs["company"].fillna("").astype(str).str.strip()
    for company, group in jobs.groupby(companies, sort=False):
        if not company:
            continue
        row: dict[str, object] = {"company": company}
        for column in ("company_size", "company_nature", "industry"):
            value = (
                _most_common(group[column]) if column in group.columns else ""
            )
            # 公司性质全缺失时输出“未知”兜底，便于前端/业务识别信息缺失
            if column == "company_nature" and not value:
                value = "未知"
            row[column] = value
        if "salary_avg" in group.columns:
            row["salary_summary"] = salary_stats(group["salary_avg"])
        else:
            row["salary_summary"] = {"count": 0, "mean": None, "min": None, "max": None}
        row["skill_summary"] = {
            skill: count for skill, count in top_skills(group, 5)
        }
        rows.append(row)

    if not rows:
        raise ValueError("没有可用于生成企业画像的公司数据")
    return pd.DataFrame(rows, columns=list(COMPANY_PROFILE_COLUMNS))
