#!/usr/bin/env python3
"""按 BFS/DFS 顺序调用固定版本的 BOSS 上游脚本。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.boss_adapter import load_upstream_records  # noqa: E402
from src.data.traversal import (  # noqa: E402
    CrawlTask,
    VisitResult,
    build_search_tasks,
    traverse_tasks,
)


def collect_task(task: CrawlTask, args: argparse.Namespace) -> VisitResult:
    upstream_script = args.upstream_repo / "scripts" / "boss_cdp_raw.py"
    if not upstream_script.is_file():
        raise FileNotFoundError(f"上游脚本不存在: {upstream_script}")

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"jobs_{task.task_id}.json"
    detail_path = output_dir / f"details_{task.task_id}.json"
    if output_path.exists() or (not args.no_detail and detail_path.exists()):
        raise FileExistsError(f"任务输出已存在，拒绝覆盖: {output_path}")

    command = [
        args.python,
        str(upstream_script),
        "--keyword",
        task.keyword,
        "--city",
        task.city,
        "--pages",
        str(task.page),
        "--format",
        "json",
        "--output",
        str(output_path),
        "--cdp-port",
        str(args.cdp_port),
    ]
    if args.no_detail:
        command.append("--no-detail")
    else:
        command.extend(["--max-details", str(args.max_details), "--detail-output", str(detail_path)])

    completed = subprocess.run(command, cwd=args.upstream_repo, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"上游采集失败，退出码: {completed.returncode}")
    return VisitResult(result_count=len(load_upstream_records(output_path)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按 BFS/DFS 执行 BOSS 关键词和城市采集任务")
    parser.add_argument("--upstream-repo", type=Path, required=True)
    parser.add_argument("--python", default=sys.executable, help="运行上游脚本的 Python 路径")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data/raw/boss-range")
    parser.add_argument("--traversal-log", type=Path, default=PROJECT_ROOT / "data/raw/traversal_records.jsonl")
    parser.add_argument("--strategy", choices=("bfs", "dfs"), default="bfs")
    parser.add_argument("--keywords", nargs="+", required=True)
    parser.add_argument("--cities", nargs="+", required=True)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--max-details", type=int, default=5)
    parser.add_argument("--cdp-port", type=int, default=9222)
    parser.add_argument("--no-detail", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_details < 1 and not args.no_detail:
        raise SystemExit("--max-details 必须大于 0")
    tasks = build_search_tasks(args.keywords, args.cities, args.pages)
    records = traverse_tasks(
        tasks,
        args.strategy,
        lambda task: collect_task(task, args),
        record_path=args.traversal_log,
    )
    print(json.dumps([record.to_dict() for record in records], ensure_ascii=False, indent=2))
    if any(record.status == "failed" for record in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
