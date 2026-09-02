"""采集任务调度与记录服务（徐挚凌）。

字段名与《docs/接口约定.md》第 4 节一致，存储采用内存态。
首期不引入真实后台定时器，只提供手动触发、状态/记录查询与
下一次计划时间的纯计算（符合"不承诺持续实时更新"）。
"""
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Mapping

from src.services.site_service import SiteConfig, get_site

TASK_STATUSES = ("pending", "running", "success", "failed")
TASK_UPDATE_FIELDS = frozenset(
    {"started_at", "finished_at", "status", "raw_count", "parsed_count", "error_count", "error_message"}
)


@dataclass(frozen=True, slots=True)
class CollectionTask:
    """采集任务记录，字段与《接口约定》第 4 节一致。"""

    task_id: str
    site_id: str
    started_at: str = ""
    finished_at: str = ""
    status: str = "pending"
    raw_count: int = 0
    parsed_count: int = 0
    error_count: int = 0
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_TASKS: dict[str, CollectionTask] = {}


def reset_tasks() -> None:
    """清空全部任务记录（测试用）。"""
    _TASKS.clear()


def list_tasks(site_id: str | None = None) -> list[CollectionTask]:
    tasks = list(_TASKS.values())
    if site_id is not None:
        tasks = [task for task in tasks if task.site_id == site_id]
    return tasks


def get_task(task_id: str) -> CollectionTask:
    if task_id not in _TASKS:
        raise KeyError(f"任务不存在: {task_id}")
    return _TASKS[task_id]


def trigger_task(site_id: str, started_at: str | None = None) -> CollectionTask:
    """手动触发一次采集，生成 pending 状态的任务记录。

    未知站点抛 KeyError；停用站点抛 ValueError。
    """
    site = get_site(site_id)
    if not site.enabled:
        raise ValueError(f"网站已停用，不能触发采集: {site_id}")
    task = CollectionTask(
        task_id=uuid.uuid4().hex,
        site_id=site_id,
        started_at=started_at or _now_iso(),
        status="pending",
    )
    _TASKS[task.task_id] = task
    return task


def update_task(task_id: str, changes: Mapping[str, object]) -> CollectionTask:
    """更新任务状态/计数/错误信息，校验 status 取值。"""
    if task_id not in _TASKS:
        raise KeyError(f"任务不存在: {task_id}")
    unknown = set(changes) - TASK_UPDATE_FIELDS
    if unknown:
        raise ValueError(f"任务不可更新字段: {', '.join(sorted(unknown))}")
    current = _TASKS[task_id]
    data = {**current.to_dict(), **dict(changes), "task_id": task_id}
    status = str(data.get("status", "pending") or "pending")
    if status not in TASK_STATUSES:
        raise ValueError(f"status 只能是 {'/'.join(TASK_STATUSES)}，实际为: {status!r}")
    task = CollectionTask(
        task_id=str(data["task_id"]),
        site_id=str(data["site_id"]),
        started_at=str(data.get("started_at", "") or ""),
        finished_at=str(data.get("finished_at", "") or ""),
        status=status,
        raw_count=_as_int(data.get("raw_count")),
        parsed_count=_as_int(data.get("parsed_count")),
        error_count=_as_int(data.get("error_count")),
        error_message=str(data.get("error_message", "") or ""),
    )
    _TASKS[task_id] = task
    return task


def _as_int(value: object) -> int:
    if value in (None, ""):
        return 0
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"任务计数必须是整数，实际为: {value!r}") from error
    if result < 0:
        raise ValueError("任务计数不能为负数")
    return result


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def compute_next_run(site: SiteConfig, after: datetime | None = None) -> datetime | None:
    """按频率计算 ``after`` 之后的下一次计划采集时间（纯计算，不触发真实定时器）。

    - ``once``：手动单次，返回 None；
    - ``daily``：每天一次，时间取 ``start_at`` 的时分；
    - ``twice_daily``：每天两次，``start_at`` 时分与 +12 小时各一次。
    """
    if site.frequency == "once" or not site.start_at:
        return None
    base = _parse_datetime(site.start_at).replace(tzinfo=None)
    after = (after or datetime.now()).replace(tzinfo=None)
    slots = (0, 12) if site.frequency == "twice_daily" else (0,)
    start_of_after_day = datetime(after.year, after.month, after.day)
    for day_offset in range(8):  # 最多向后找 8 天，足够覆盖任意时刻
        day = start_of_after_day + timedelta(days=day_offset)
        for slot in slots:
            candidate = day.replace(
                hour=base.hour, minute=base.minute, second=base.second, microsecond=0
            ) + timedelta(hours=slot)
            if candidate > after:
                return candidate
    return None


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"start_at 不是合法的 ISO 时间: {value!r}") from error
