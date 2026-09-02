"""算法模块共享的内部工具（郑维豪维护）。

这些函数仅供 src/algorithms 包内部使用，不构成对外接口。
对外契约以《接口约定》和 src/data/schema.py 为准。

设计要点：
- 岗位表必填字段缺失或为空时，抛出具名明确错误；
- 可选分析字段（公司性质、公司规模、行业等）存在则参与分析，
  缺失则优雅跳过，保证冻结的 JOB_COLUMNS 也能运行。
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

import pandas as pd

# 必填字段：缺失时直接报错，避免后续静默出错
REQUIRED_COLUMNS = ("job_id", "title", "skills")

# 可选因子字段：存在才参与因素分析 / 特征编码
OPTIONAL_FACTOR_COLUMNS = (
    "city",
    "work_type",
    "experience",
    "education",
    "company_nature",
    "company_size",
    "industry",
)


def validate_jobs(jobs: pd.DataFrame) -> None:
    """校验输入岗位表：必须是 DataFrame、非空、含必填字段。"""
    if not isinstance(jobs, pd.DataFrame):
        raise ValueError("输入必须是 pandas.DataFrame")
    if jobs.empty:
        raise ValueError("岗位数据为空，无法进行分析")
    missing = [column for column in REQUIRED_COLUMNS if column not in jobs.columns]
    if missing:
        raise ValueError(f"岗位表缺少必填字段: {', '.join(missing)}")


def available_columns(jobs: pd.DataFrame, names: Iterable[str]) -> list[str]:
    """返回实际存在于输入表中的字段名列表。"""
    return [name for name in names if name in jobs.columns]


def split_skills(skills: object) -> list[str]:
    """将 skills 按英文分号拆分，去空并保序去重。"""
    if skills is None:
        return []
    if isinstance(skills, (list, tuple, set)):
        values = [str(skill) for skill in skills]
    else:
        values = str(skills).split(";")
    seen: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def top_skills(jobs: pd.DataFrame, n: int = 10) -> list[tuple[str, int]]:
    """统计技能频次，按 (频次降序, 名称) 返回前 n 个 (技能, 次数)。"""
    counts: Counter[str] = Counter()
    for raw in jobs["skills"].dropna():
        for skill in split_skills(raw):
            counts[skill] += 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:n]


def education_level(value: object) -> int:
    """学历映射为有序数值；未知或缺失返回 0。"""
    if value is None:
        return 0
    text = str(value)
    if "博士" in text:
        return 5
    if "硕士" in text or "研究生" in text:
        return 4
    if "本科" in text:
        return 3
    if "大专" in text or "专科" in text:
        return 2
    if "高中" in text or "中专" in text or "初中" in text:
        return 1
    return 0


def experience_years(value: object) -> float:
    """经验文本映射为年限（区间取中点）；未知返回 0。"""
    if value is None:
        return 0.0
    text = str(value)
    if "经验不限" in text or "在校生" in text or "应届" in text:
        return 0.0
    if "10年" in text:
        return 12.0
    if "5-10" in text or "5~10" in text:
        return 7.5
    if "3-5" in text or "3~5" in text:
        return 4.0
    if "1-3" in text or "1~3" in text:
        return 2.0
    if "1年" in text:
        return 1.0
    if "3年" in text:
        return 3.0
    if "5年" in text:
        return 5.0
    return 0.0


def company_size_level(value: object) -> float:
    """公司规模文本提取人数下限（如“100-499人”→100）；未知返回 0。"""
    if value is None:
        return 0.0
    numbers = re.findall(r"\d+", str(value))
    return float(numbers[0]) if numbers else 0.0


def salary_stats(series: pd.Series) -> dict[str, object]:
    """薪资列统计摘要（只统计非空），样本为 0 时返回空标记。"""
    valid = pd.to_numeric(series, errors="coerce").dropna()
    if valid.empty:
        return {"count": 0, "mean": None, "min": None, "max": None}
    return {
        "count": int(valid.size),
        "mean": round(float(valid.mean()), 2),
        "min": round(float(valid.min()), 2),
        "max": round(float(valid.max()), 2),
    }


def encode_job_features(
    jobs: pd.DataFrame,
    top_skills_n: int = 10,
    top_cities_n: int = 5,
    include_salary: bool = True,
) -> pd.DataFrame:
    """把岗位表编码为数值特征矩阵（KMeans 与随机森林共用）。

    - 技能：Top N 技能 one-hot；
    - 学历、经验、公司规模：有序数值；
    - 城市、公司性质、行业：Top 取值 one-hot，其余归入其他；
    - include_salary=True 时加入 salary_avg（聚类用），预测薪资时应为 False。

    返回 DataFrame 与输入同索引，首列为 job_id 便于对回结果。
    """
    validate_jobs(jobs)
    features: dict[str, pd.Series] = {}

    skill_top = [skill for skill, _ in top_skills(jobs, top_skills_n)]
    for skill in skill_top:
        features[f"skill_{skill}"] = jobs["skills"].fillna("").map(
            lambda raw: 1.0 if skill in split_skills(raw) else 0.0
        )

    features["education_level"] = jobs["education"].map(education_level).astype(float)
    features["experience_years"] = jobs["experience"].map(experience_years).astype(float)
    if "company_size" in jobs.columns:
        features["company_size_level"] = (
            jobs["company_size"].map(company_size_level).astype(float)
        )

    if "city" in jobs.columns:
        city_counts = jobs["city"].fillna("").astype(str).value_counts()
        city_top = [city for city in city_counts.index[:top_cities_n] if city]
        for city in city_top:
            features[f"city_{city}"] = (
                jobs["city"].fillna("").astype(str) == city
            ).astype(float)
        features["city_other"] = (
            ~jobs["city"].fillna("").astype(str).isin(city_top)
        ).astype(float)

    for column, top_n in (("company_nature", 5), ("industry", 5)):
        if column in jobs.columns:
            value_counts = jobs[column].fillna("").astype(str).value_counts()
            value_top = [value for value in value_counts.index[:top_n] if value]
            for value in value_top:
                features[f"{column}_{value}"] = (
                    jobs[column].fillna("").astype(str) == value
                ).astype(float)

    if include_salary and "salary_avg" in jobs.columns:
        salary = pd.to_numeric(jobs["salary_avg"], errors="coerce")
        fallback = salary.median() if salary.notna().any() else 0.0
        features["salary_avg"] = salary.fillna(fallback)

    result = pd.DataFrame(features, index=jobs.index)
    result.insert(0, "job_id", jobs["job_id"].astype(str).values)
    return result
