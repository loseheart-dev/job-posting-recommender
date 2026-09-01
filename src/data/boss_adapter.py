"""BOSS 直聘上游结果导入和标准字段适配。"""

from __future__ import annotations

import csv
import json
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


UPSTREAM_REPOSITORY = "https://github.com/eatmoreduck/boss-zhipin-scraper"
UPSTREAM_VERSION = "v2.2.0"
UPSTREAM_COMMIT = "2bc40f56a3ca3249ce3b98cdda0187e0bd612aa5"
BOSS_SOURCE = "BOSS直聘"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class CollectionTaskRecord:
    """One import or collection attempt, suitable for JSONL storage."""

    task_id: str
    source: str
    source_path: str
    raw_path: str
    keyword: str
    city: str
    crawl_strategy: str
    started_at: str
    finished_at: str
    status: str
    raw_count: int
    parsed_count: int
    error_count: int
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _records_from_json(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = payload.get("jobs", payload.get("data", payload))
    if not isinstance(payload, list):
        raise ValueError("BOSS JSON 必须是岗位列表，或包含 jobs/data 列表")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError("BOSS JSON 岗位记录必须都是对象")
    return payload


def load_upstream_records(path: str | Path) -> list[dict[str, Any]]:
    """读取上游 JSON/CSV，不修改文件内容。"""

    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(f"上游结果文件不存在: {source_path}")
    if source_path.suffix.lower() == ".json":
        try:
            return _records_from_json(json.loads(source_path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as error:
            raise ValueError(f"BOSS JSON 格式错误: {error.msg}") from error
    if source_path.suffix.lower() == ".csv":
        with source_path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise ValueError("BOSS CSV 缺少表头")
            return [dict(row) for row in reader]
    raise ValueError("上游结果只支持 JSON 或 CSV")


def save_raw_result(source_path: str | Path, raw_dir: str | Path, task_id: str) -> Path:
    """把上游原始结果复制到 raw_dir，目标文件不覆盖已有结果。"""

    source = Path(source_path)
    if not source.is_file():
        raise FileNotFoundError(f"上游结果文件不存在: {source}")
    destination_dir = Path(raw_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"boss_{task_id}_raw{source.suffix.lower()}"
    if destination.exists():
        raise FileExistsError(f"原始结果已存在，拒绝覆盖: {destination}")
    shutil.copy2(source, destination)
    return destination


def append_task_record(record: CollectionTaskRecord, path: str | Path) -> Path:
    """追加任务记录，不覆盖已有记录。"""

    record_path = Path(path)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with record_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    return record_path


def import_upstream_result(
    source_path: str | Path,
    raw_dir: str | Path,
    task_record_path: str | Path,
    *,
    keyword: str = "",
    city: str = "",
    crawl_strategy: str = "bfs",
    task_id: str | None = None,
) -> tuple[CollectionTaskRecord, list[dict[str, Any]]]:
    """校验、保存一份上游结果，并追加一条任务记录。"""

    task_id = task_id or uuid.uuid4().hex[:12]
    started_at = utc_now()
    source = Path(source_path)
    try:
        records = load_upstream_records(source)
        raw_path = save_raw_result(source, raw_dir, task_id)
    except (OSError, ValueError) as error:
        record = CollectionTaskRecord(
            task_id=task_id,
            source=BOSS_SOURCE,
            source_path=str(source),
            raw_path="",
            keyword=keyword,
            city=city,
            crawl_strategy=crawl_strategy,
            started_at=started_at,
            finished_at=utc_now(),
            status="failed",
            raw_count=0,
            parsed_count=0,
            error_count=1,
            error_message=str(error),
        )
        append_task_record(record, task_record_path)
        raise

    record = CollectionTaskRecord(
        task_id=task_id,
        source=BOSS_SOURCE,
        source_path=str(source),
        raw_path=str(raw_path),
        keyword=keyword,
        city=city,
        crawl_strategy=crawl_strategy,
        started_at=started_at,
        finished_at=utc_now(),
        status="success",
        raw_count=len(records),
        parsed_count=len(records),
        error_count=0,
    )
    append_task_record(record, task_record_path)
    return record, records
