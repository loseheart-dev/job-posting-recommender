#!/usr/bin/env python3
"""定向补采短缺岗位并把新结果合并回完整清洗表。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.boss_adapter import load_upstream_records, map_boss_records
from src.data.cleaner import clean_jobs_with_report
from src.data.loader import load_jobs
from src.data.market import (
    JOB_CATEGORIES,
    MARKET_SUPPLEMENT_CITIES,
    MARKET_SUPPLEMENT_KEYWORDS,
    add_job_category,
)


def _keywords(categories: list[str], per_category: int = 0) -> list[str]:
    seen: list[str] = []
    for category in categories:
        category_keywords = MARKET_SUPPLEMENT_KEYWORDS[category]
        if per_category:
            category_keywords = category_keywords[:per_category]
        for keyword in category_keywords:
            if keyword not in seen:
                seen.append(keyword)
    return seen


def collect(args: argparse.Namespace) -> None:
    keywords = _keywords(args.categories, args.keywords_per_category)
    raw_dir = args.raw_dir.resolve()
    traversal_log = args.traversal_log.resolve()
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_boss_tasks.py"),
        "--upstream-repo",
        str(args.upstream_repo),
        "--python",
        args.python,
        "--output-dir",
        str(raw_dir),
        "--traversal-log",
        str(traversal_log),
        "--strategy",
        args.strategy,
        "--keywords",
        *keywords,
        "--cities",
        *args.cities,
        "--pages",
        str(args.pages),
        "--max-details",
        str(args.max_details),
        "--cdp-port",
        str(args.cdp_port),
    ]
    if args.no_detail:
        command.append("--no-detail")
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)
    print(json.dumps({"categories": args.categories, "keywords": keywords, "raw_dir": str(raw_dir)}, ensure_ascii=False, indent=2))


def _optional_records(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload == []:
        return []
    return load_upstream_records(path)


def _supplement_frame(raw_dir: Path) -> tuple[pd.DataFrame, list[str], int]:
    frames: list[pd.DataFrame] = []
    files: list[str] = []
    raw_count = 0
    for jobs_path in sorted(raw_dir.glob("jobs_*.json")):
        payload = json.loads(jobs_path.read_text(encoding="utf-8"))
        records = load_upstream_records(jobs_path)
        details_path = jobs_path.with_name(jobs_path.name.replace("jobs_", "details_", 1))
        details = _optional_records(details_path)
        crawled_at = payload.get("scraped_at", "") if isinstance(payload, dict) else ""
        mapped = map_boss_records(records, details, crawled_at=str(crawled_at or "") or None)
        frames.append(pd.DataFrame(mapped))
        files.append(str(jobs_path))
        raw_count += len(records)
    if not frames:
        raise ValueError(f"补采目录没有 jobs_*.json: {raw_dir}")
    return pd.concat(frames, ignore_index=True), files, raw_count


def merge(args: argparse.Namespace) -> None:
    base = load_jobs(args.input)
    supplement, files, raw_count = _supplement_frame(args.raw_dir)
    combined = pd.concat([base, supplement], ignore_index=True)
    cleaned, cleaning_report = clean_jobs_with_report(combined)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(args.output, index=False, encoding="utf-8-sig")
    categorized = add_job_category(cleaned)
    category_counts = categorized["job_category"].value_counts().reindex(JOB_CATEGORIES, fill_value=0)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(args.input),
        "raw_dir": str(args.raw_dir),
        "output_path": str(args.output),
        "base_count": int(len(base)),
        "supplement_file_count": len(files),
        "supplement_raw_count": raw_count,
        "merged_input_count": int(len(combined)),
        "output_count": int(len(cleaned)),
        "category_counts": {category: int(category_counts[category]) for category in JOB_CATEGORIES},
        "source_files": files,
        "cleaning": cleaning_report,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="补采短缺岗位并合并到完整岗位表")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="按类别关键词调用 BOSS 采集器")
    collect_parser.add_argument("--upstream-repo", type=Path, required=True)
    collect_parser.add_argument(
        "--categories",
        nargs="+",
        choices=JOB_CATEGORIES,
        default=["财务", "销售", "行政", "制造", "其他"],
    )
    collect_parser.add_argument("--cities", nargs="+", default=list(MARKET_SUPPLEMENT_CITIES))
    collect_parser.add_argument(
        "--keywords-per-category",
        type=int,
        default=7,
        help="每类使用前 N 个关键词；传 0 使用该类全部关键词",
    )
    collect_parser.add_argument("--pages", type=int, default=1)
    collect_parser.add_argument("--max-details", type=int, default=5)
    collect_parser.add_argument("--no-detail", action="store_true", help="只采集列表，跳过详情页")
    collect_parser.add_argument("--cdp-port", type=int, default=9222)
    collect_parser.add_argument("--python", default=sys.executable, help="运行上游脚本的 Python 路径")
    collect_parser.add_argument("--strategy", choices=("bfs", "dfs"), default="bfs")
    collect_parser.add_argument("--raw-dir", type=Path, default=PROJECT_ROOT / "data/raw/market-supplement")
    collect_parser.add_argument("--traversal-log", type=Path, default=PROJECT_ROOT / "data/raw/market-supplement/traversal_records.jsonl")
    collect_parser.set_defaults(func=collect)

    merge_parser = subparsers.add_parser("merge", help="合并补采 JSON、清洗并去重")
    merge_parser.add_argument("--raw-dir", type=Path, default=PROJECT_ROOT / "data/raw/market-supplement")
    merge_parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data/processed/jobs.csv")
    merge_parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/processed/jobs.csv")
    merge_parser.add_argument("--report", type=Path, default=PROJECT_ROOT / "data/processed/market_supplement_record.json")
    merge_parser.set_defaults(func=merge)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "collect" and not 1 <= args.pages <= 10:
        raise SystemExit("--pages 必须在 1 到 10 之间")
    if args.command == "collect" and args.keywords_per_category < 0:
        raise SystemExit("--keywords-per-category 不能小于 0")
    args.func(args)


if __name__ == "__main__":
    main()
