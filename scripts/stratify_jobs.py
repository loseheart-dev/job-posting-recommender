#!/usr/bin/env python3
"""从清洗后的岗位表生成按岗位类别平衡的市场样本。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.data.loader import load_jobs
from src.data.market import stratified_sample_jobs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按技术/财务/销售/行政/制造/其他类别分层抽样岗位")
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data/processed/jobs.csv")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/processed/jobs_market.csv")
    parser.add_argument("--report", type=Path, default=PROJECT_ROOT / "data/processed/market_sampling_record.json")
    parser.add_argument("--per-category", type=int, default=500)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    jobs = load_jobs(args.input)
    sampled, report = stratified_sample_jobs(
        jobs,
        per_category=args.per_category,
        random_state=args.random_state,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sampled.to_csv(args.output, index=False, encoding="utf-8-sig")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "report": str(args.report), **report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
