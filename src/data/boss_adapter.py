"""BOSS 直聘上游结果导入和标准字段适配。"""

from __future__ import annotations

import csv
import json
import re
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.data.schema import JOB_COLUMNS


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
    if source_path.stat().st_size == 0:
        raise ValueError("上游结果文件为空")
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


_EDUCATION_VALUES = (
    "初中及以下",
    "中专/中技",
    "高中",
    "大专",
    "本科",
    "硕士",
    "博士",
    "学历不限",
)
_WORK_TYPE_VALUES = ("全职", "实习", "校招", "兼职", "远程")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return " | ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _split_values(value: Any) -> list[str]:
    return [part.strip() for part in re.split(r"\s*[|｜,，;；]\s*", _text(value)) if part.strip()]


def normalize_delimited(value: Any) -> str:
    """把上游标签统一成项目约定的英文分号格式。"""

    seen: list[str] = []
    for part in _split_values(value):
        if part not in seen:
            seen.append(part)
    return ";".join(seen)


def parse_salary(text: Any) -> tuple[float | None, float | None, float | None]:
    """解析 BOSS 月薪或日薪文本，结果统一为人民币元/月。"""

    salary_text = _text(text).replace(" ", "")
    numbers = [float(item) for item in re.findall(r"\d+(?:\.\d+)?", salary_text)]
    if not numbers:
        return None, None, None
    values = numbers[:2]
    if "元/天" in salary_text or "元/日" in salary_text:
        values = [value * 21.75 for value in values]
    elif "万" in salary_text and not re.search(r"[Kk千]", salary_text):
        values = [value * 10000 for value in values]
    elif re.search(r"[Kk千]", salary_text):
        values = [value * 1000 for value in values]
    lower, upper = min(values), max(values)
    return lower, upper, (lower + upper) / 2


def _location_city(value: Any) -> str:
    location = _text(value)
    return re.split(r"\s*[·•|｜/]\s*", location, maxsplit=1)[0].removesuffix("市").strip()


def _tag_fields(value: Any) -> tuple[str, str, str]:
    experience: list[str] = []
    education: list[str] = []
    work_type: list[str] = []
    for tag in _split_values(value):
        if tag in _EDUCATION_VALUES:
            education.append(tag)
        elif tag in _WORK_TYPE_VALUES:
            work_type.append(tag)
        else:
            experience.append(tag)
    return ";".join(experience), ";".join(education), ";".join(work_type)


def _record_id(record: dict[str, Any]) -> str:
    return _text(record.get("job_id") or record.get("encrypt_job_id") or record.get("encryptJobId"))


def map_boss_records(
    records: Iterable[dict[str, Any]],
    details: Iterable[dict[str, Any]] | None = None,
    *,
    crawled_at: str | None = None,
) -> list[dict[str, Any]]:
    """把上游列表和详情记录转换为项目标准岗位字段。"""

    detail_by_id = {_record_id(item): item for item in (details or ()) if _record_id(item)}
    timestamp = crawled_at or utc_now()
    mapped: list[dict[str, Any]] = []
    for raw in records:
        if not isinstance(raw, dict):
            continue
        job_id = _record_id(raw)
        detail = detail_by_id.get(job_id, {})
        salary_text = _text(raw.get("salary") or raw.get("salaryDesc"))
        salary_min, salary_max, salary_avg = parse_salary(salary_text)
        tags = raw.get("tags") or raw.get("tags_list") or raw.get("job_labels")
        experience, education, work_type = _tag_fields(tags)
        mapped.append(
            {
                "job_id": job_id,
                "title": _text(raw.get("title") or raw.get("jobName") or detail.get("title")),
                "company": _text(
                    raw.get("company")
                    or raw.get("boss_name")
                    or raw.get("brand_name")
                    or raw.get("brandName")
                    or detail.get("company")
                ),
                "company_intro": _text(raw.get("company_intro") or raw.get("companyIntro")),
                "company_size": _text(raw.get("company_scale") or raw.get("brandScaleName")),
                "company_nature": _text(raw.get("company_nature") or raw.get("companyNature")),
                "industry": _text(
                    raw.get("company_industry") or raw.get("brandIndustry") or raw.get("industry")
                ),
                "city": _location_city(raw.get("location") or detail.get("location")),
                "work_type": work_type,
                "experience": experience,
                "education": education,
                "skills": normalize_delimited(raw.get("skills") or detail.get("skill_tags")),
                "description": _text(raw.get("description") or detail.get("jd")),
                "benefits": normalize_delimited(raw.get("welfare") or raw.get("benefits")),
                "salary_text": salary_text,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_avg": salary_avg,
                "source": BOSS_SOURCE,
                "source_url": _text(raw.get("job_link") or raw.get("source_url") or detail.get("job_link")),
                "crawled_at": timestamp,
            }
        )
    return [{column: row.get(column, "") for column in JOB_COLUMNS} for row in mapped]
