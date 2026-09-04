from pathlib import Path
import re
import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from src.data.boss_adapter import (
    detect_salary_unit,
    normalize_delimited,
    normalize_skills,
    parse_salary,
)
from src.data.schema import JOB_COLUMNS


_TEXT_COLUMNS = tuple(
    column
    for column in JOB_COLUMNS
    if column not in {"salary_min", "salary_max", "salary_avg"}
)
_SALARY_COLUMNS = ("salary_min", "salary_max", "salary_avg")


def _text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_city(value: Any) -> str:
    """统一城市文本，保留无法识别的非空值。"""

    city = _text(value)
    if not city:
        return ""
    city = re.split(r"\s*[·•|｜/]\s*", city, maxsplit=1)[0].strip()
    return city.removesuffix("市").strip()


def _missing_count(series: pd.Series) -> int:
    return int(series.astype("string").fillna("").str.strip().eq("").sum())


def clean_jobs_with_report(raw_jobs: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """清洗岗位表并返回可供任务记录使用的统计信息。"""

    if not isinstance(raw_jobs, pd.DataFrame):
        raise TypeError("岗位数据必须是 pandas.DataFrame")
    result = raw_jobs.copy()
    input_count = len(result)
    for column in JOB_COLUMNS:
        if column not in result.columns:
            result[column] = ""
    result = result.loc[:, JOB_COLUMNS].copy()

    for column in _TEXT_COLUMNS:
        result[column] = result[column].map(_text)
    result["city"] = result["city"].map(normalize_city)
    result["skills"] = result["skills"].map(normalize_skills)
    result["benefits"] = result["benefits"].map(normalize_delimited)

    for column in _SALARY_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    parsed_salary_count = 0
    legacy_salary_values_cleared = pd.Series(False, index=result.index)
    for index, salary_text in result["salary_text"].items():
        if not salary_text:
            continue
        had_salary_value = result.loc[index, list(_SALARY_COLUMNS)].notna().any()
        minimum, maximum, average = parse_salary(salary_text)
        result.at[index, "salary_min"] = minimum
        result.at[index, "salary_max"] = maximum
        result.at[index, "salary_avg"] = average
        if average is not None:
            parsed_salary_count += 1
        elif had_salary_value:
            legacy_salary_values_cleared.at[index] = True
    result.loc[result["salary_min"] > result["salary_max"], ["salary_min", "salary_max"]] = result.loc[
        result["salary_min"] > result["salary_max"], ["salary_max", "salary_min"]
    ].to_numpy()
    missing_average = result["salary_avg"].isna() & result["salary_min"].notna() & result["salary_max"].notna()
    result.loc[missing_average, "salary_avg"] = (
        result.loc[missing_average, "salary_min"] + result.loc[missing_average, "salary_max"]
    ) / 2

    duplicate_mask = result["job_id"].ne("") & result["job_id"].duplicated(keep="first")
    duplicate_count = int(duplicate_mask.sum())
    legacy_salary_values_cleared = legacy_salary_values_cleared.loc[~duplicate_mask]
    result = result.loc[~duplicate_mask].reset_index(drop=True)
    salary_units = result["salary_text"].map(detect_salary_unit)
    salary_text_present = result["salary_text"].ne("")
    salary_unit_counts = {
        unit: int((salary_text_present & salary_units.eq(unit)).sum())
        for unit in ("month", "hour", "day", "week", "year", "piece", "negotiable", "unknown")
    }
    missing_counts = {column: _missing_count(result[column]) for column in JOB_COLUMNS}
    invalid_salary_count = int((result["salary_text"].ne("") & result["salary_avg"].isna()).sum())
    report = {
        "input_count": input_count,
        "output_count": len(result),
        "duplicate_count": duplicate_count,
        "parsed_salary_count": parsed_salary_count,
        "invalid_salary_count": invalid_salary_count,
        "salary_unit_counts": salary_unit_counts,
        "non_monthly_salary_excluded": int(
            (salary_text_present & salary_units.ne("month")).sum()
        ),
        "legacy_salary_values_cleared": int(legacy_salary_values_cleared.sum()),
        "valid_monthly_salary_count": int(
            (salary_units.eq("month") & result["salary_avg"].notna()).sum()
        ),
        "missing_counts": missing_counts,
    }
    return result, report


def clean_jobs(raw_jobs: pd.DataFrame) -> pd.DataFrame:
    """返回统一列顺序的清洗岗位表，不修改输入表。"""

    result, _ = clean_jobs_with_report(raw_jobs)
    return result


def write_clean_jobs(
    raw_jobs: pd.DataFrame, output_path: str | Path
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """清洗并写出项目约定的 CSV，同时返回结果和统计。"""

    cleaned, report = clean_jobs_with_report(raw_jobs)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(path, index=False, encoding="utf-8-sig")
    return cleaned, report


def write_cleaning_record(
    report: dict[str, Any],
    record_path: str | Path,
    *,
    source_path: str = "",
    cleaned_path: str = "",
    source: str = "BOSS直聘",
) -> Path:
    """保存一次清洗统计和输入输出路径。"""

    path = Path(record_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "source_path": source_path,
        "cleaned_path": cleaned_path,
        "rules": {
            "deduplicate": "按非空 job_id 保留首次记录",
            "missing_text": "文本字段保留为空",
            "missing_salary": "薪资无法解析或不是月薪时保留 salary_text，并将数值列置空",
            "salary_unit": "只解析明确人民币月薪，不根据标题或工时假设折算时薪、日薪、周薪和年薪",
            "city": "取城市名称并去除末尾‘市’",
            "skills_and_benefits": "统一使用英文分号分隔并去重",
        },
        "statistics": report,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
