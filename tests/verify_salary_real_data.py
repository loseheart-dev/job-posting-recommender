# -*- coding: utf-8 -*-
"""复算真实清洗数据的薪资分布和预测指标，并保存可审计结果。

默认优先读取 ``data/processed/jobs.csv``；该文件不存在时回退到仓库内的
``tests/fixtures/expanded_jobs.csv``。两者都必须是 8608 条标准岗位数据。

用法：``python -m tests.verify_salary_real_data``
也可用 ``--input`` 指定另一份已经清洗的标准岗位表。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.algorithms._common import flag_abnormal_salary
from src.algorithms.salary import predict_salary
from src.data.loader import load_jobs
from src.data.schema import JOB_COLUMNS
from src.services.job_service import salary_distribution

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = ROOT / "data/processed/jobs.csv"
FIXTURE_PATH = ROOT / "tests/fixtures/expanded_jobs.csv"
DEFAULT_OUTPUT = ROOT / "tests/fixtures/real_data_salary_verification.json"
EXPECTED_ROWS = 8608
HISTORICAL_R2 = 0.234


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _choose_input(requested: Path | None) -> Path:
    if requested is not None:
        return requested
    return RUNTIME_PATH if RUNTIME_PATH.exists() else FIXTURE_PATH


def verify(input_path: Path) -> dict[str, object]:
    jobs = load_jobs(str(input_path))
    assert len(jobs) == EXPECTED_ROWS, f"岗位数应为 {EXPECTED_ROWS}，实际为 {len(jobs)}"
    assert tuple(jobs.columns) == JOB_COLUMNS

    salary = pd.to_numeric(jobs["salary_avg"], errors="coerce")
    abnormal = flag_abnormal_salary(jobs)
    high_salary = salary >= 100000
    assert int(high_salary.sum()) > 0, "测试数据缺少合法高薪样本"
    assert not abnormal[high_salary].any(), "10万及以上月薪不应被算法高值阈值标记"

    distribution = salary_distribution(jobs)
    assert sum(int(bucket["count"]) for bucket in distribution) == int(salary.notna().sum())

    _, metrics = predict_salary(jobs)
    assert pd.notna(metrics["mae"]) and pd.notna(metrics["r2"])

    return {
        "verification": "passed",
        "input": _relative(input_path),
        "rows": int(len(jobs)),
        "columns": int(len(jobs.columns)),
        "salary_count": int(salary.notna().sum()),
        "missing_salary_count": int(salary.isna().sum()),
        "low_salary_flagged_count": int(abnormal.sum()),
        "high_salary_retained_count": int(high_salary.sum()),
        "salary_summary": {
            "min": float(salary.min()),
            "max": float(salary.max()),
            "mean": round(float(salary.mean()), 2),
        },
        "salary_distribution": distribution,
        "random_forest": {
            "mae": float(metrics["mae"]),
            "r2": float(metrics["r2"]),
            "test_size": 0.3,
            "random_state": 42,
        },
        "historical_comparison": {
            "reported_r2": HISTORICAL_R2,
            "current_r2_minus_reported": round(float(metrics["r2"]) - HISTORICAL_R2, 4),
            "source": "daily/25051408/D4.md",
            "status": "historical intermediate result, not a current algorithm threshold",
        },
        "salary_policy": {
            "monthly_unit": "RMB/month",
            "non_monthly_values": "cleaning side sets numeric salary columns to null",
            "algorithm_high_salary_threshold": None,
            "algorithm_low_salary_threshold": 500,
        },
        "note": "D4 中的 0.234 属于旧的高值阈值中间方案；本结果按当前终态复算，不恢复 10 万元硬阈值。",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="复算 8608 条真实岗位数据的薪资指标")
    parser.add_argument("--input", type=Path, help="清洗后的标准岗位 CSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="验证结果 JSON")
    args = parser.parse_args()

    input_path = _choose_input(args.input)
    result = verify(input_path)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n薪资复算 PASSED，结果已写入 {_relative(args.output)}")


if __name__ == "__main__":
    main()
