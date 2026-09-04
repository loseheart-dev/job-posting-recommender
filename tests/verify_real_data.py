# -*- coding: utf-8 -*-
"""Z5：数据读取/筛选/统计接入真实清洗数据 —— 可复现验证脚本。

用法：``python -m tests.verify_real_data``

数据来源：优先使用 ``data/processed/jobs.csv``（卢世豪清洗管道的标准输出，被 gitignore）；
若不存在，则回退到已入库的 ``tests/fixtures/expanded_jobs.csv``（8608 条真实 BOSS 直聘清洗结果，
覆盖 61 个岗位关键词、32 个城市，见 expanded_jobs_metadata.json）。
"""
import os

import pandas as pd

from src.data.loader import load_jobs
from src.data.schema import FILTER_KEYS, JOB_COLUMNS
from src.services.job_service import filter_jobs, salary_distribution, summarize_jobs

RUNTIME_PATH = "data/processed/jobs.csv"
FIXTURE_PATH = "tests/fixtures/expanded_jobs.csv"


def section(title: str) -> None:
    print("\n" + "=" * 20 + " " + title + " " + "=" * 20)


def main() -> None:
    # ---------- 1. 读取真实清洗数据 ----------
    section("1. load_jobs 读取真实清洗数据")
    path = RUNTIME_PATH if os.path.exists(RUNTIME_PATH) else FIXTURE_PATH
    print("使用数据:", path)
    jobs = load_jobs(path)
    print("rows:", len(jobs))
    print("columns==JOB_COLUMNS:", tuple(jobs.columns) == JOB_COLUMNS)
    print("城市数:", int(jobs["city"].nunique()))
    print("有 salary_avg 的行:", int(jobs["salary_avg"].notna().sum()))
    assert tuple(jobs.columns) == JOB_COLUMNS
    assert len(jobs) > 0

    # ---------- 2. 筛选（各键会改变结果） ----------
    section("2. filter_jobs 各筛选键")
    checks = [
        ("keyword=数据分析", {"keyword": "数据分析"}),
        ("city=上海", {"city": "上海"}),
        ("work_type=全职", {"work_type": "全职"}),
        ("experience=3-5年", {"experience": "3-5年"}),
        ("education=本科", {"education": "本科"}),
        ("industry=互联网金融", {"industry": "互联网金融"}),
        ("company_nature=民营", {"company_nature": "民营"}),
        ("salary_min=20000", {"salary_min": 20000}),
        ("salary_max=8000", {"salary_max": 8000}),
        ("组合=上海+本科+keyword=数据", {"city": "上海", "education": "本科", "keyword": "数据"}),
        ("无结果 keyword", {"keyword": "不存在的岗位xyz"}),
    ]
    checked_keys = {key for _, filters in checks for key in filters}
    assert checked_keys == set(FILTER_KEYS)
    print("筛选键覆盖:", sorted(checked_keys))
    for label, filters in checks:
        print(f"{label}: {len(filter_jobs(jobs, filters))} 行")
    assert filter_jobs(jobs, {"keyword": "不存在的岗位xyz"}).empty
    before = len(jobs)
    filter_jobs(jobs, {"city": "上海"})
    assert len(jobs) == before  # 不修改输入
    try:
        filter_jobs(jobs, {"bad_key": "x"})
    except ValueError:
        print("未知筛选键会抛 ValueError（校验通过）")
    else:
        raise AssertionError("unknown filter key should raise")

    # ---------- 3. 统计 ----------
    section("3. summarize_jobs")
    summary = summarize_jobs(jobs)
    for key in ("job_count", "salary_count", "salary_min", "salary_max", "salary_avg"):
        print(f"  {key}: {summary[key]}")
    print("  top_skills 前 5:", summary["top_skills"][:5])
    assert summary["job_count"] == len(jobs)

    # ---------- 4. 薪资分布 ----------
    section("4. salary_distribution")
    dist = salary_distribution(jobs)
    total = sum(bucket["count"] for bucket in dist)
    print("桶数:", len(dist))
    print("桶计数总和(=salary_count):", total)
    for bucket in dist[:3]:
        print("  首部桶:", bucket)
    for bucket in dist[-3:]:
        print("  尾部桶:", bucket)
    assert total == int(summary["salary_count"])

    # ---------- 5. 空数据 / 缺文件案例 ----------
    section("5. 空数据与缺文件案例")
    empty = pd.DataFrame(columns=JOB_COLUMNS)
    assert filter_jobs(empty, {"city": "上海"}).empty
    empty_summary = summarize_jobs(empty)
    assert empty_summary["job_count"] == 0
    assert empty_summary["salary_avg"] is None
    assert salary_distribution(empty) == []
    missing = load_jobs("data/processed/not-exist.csv")
    assert tuple(missing.columns) == JOB_COLUMNS
    assert missing.empty
    print("空数据筛选→空表；空统计→job_count=0/salary_avg=None；薪资分布→[]；缺文件→空表（带标准列）（校验通过）")

    print("\nZ5 real-data verification PASSED")


if __name__ == "__main__":
    main()
