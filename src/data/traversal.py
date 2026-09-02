"""用于组织 BOSS 搜索任务的 BFS/DFS 遍历。"""

from __future__ import annotations

from collections import deque
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True, slots=True)
class CrawlTask:
    task_id: str
    keyword: str
    city: str
    page: int = 1
    depth: int = 0
    url: str = ""

    def key(self) -> tuple[str, str, int, str]:
        return (self.keyword.strip(), self.city.strip(), self.page, self.url.strip())


@dataclass(frozen=True, slots=True)
class VisitResult:
    result_count: int = 0
    children: tuple[CrawlTask, ...] = ()


@dataclass(frozen=True, slots=True)
class TraversalRecord:
    task_id: str
    keyword: str
    city: str
    page: int
    depth: int
    strategy: str
    status: str
    result_count: int
    error_message: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def append_traversal_record(record: TraversalRecord, path: str | Path) -> Path:
    """追加一条遍历记录，不覆盖已有记录。"""

    record_path = Path(path)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with record_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    return record_path


def build_search_tasks(
    keywords: Iterable[str], cities: Iterable[str], pages: int = 1
) -> list[CrawlTask]:
    """按关键词和城市生成任务，page 表示本次上游请求的总页数。"""

    if pages < 1:
        raise ValueError("采集页数必须大于 0")
    tasks: list[CrawlTask] = []
    index = 0
    for keyword in keywords:
        for city in cities:
            index += 1
            tasks.append(
                CrawlTask(
                    task_id=f"search-{index}",
                    keyword=str(keyword).strip(),
                    city=str(city).strip(),
                    page=pages,
                )
            )
    return tasks


def traverse_tasks(
    tasks: Iterable[CrawlTask],
    strategy: str,
    visit: Callable[[CrawlTask], VisitResult],
    *,
    max_depth: int = 0,
    record_path: str | Path | None = None,
) -> list[TraversalRecord]:
    """按 BFS 或 DFS 访问任务，并记录节点、结果数量和错误。"""

    strategy = strategy.strip().lower()
    if strategy not in {"bfs", "dfs"}:
        raise ValueError("遍历策略只能是 bfs 或 dfs")
    if max_depth < 0:
        raise ValueError("最大深度不能小于 0")

    initial_tasks = list(tasks)
    pending: deque[CrawlTask] = deque(initial_tasks)
    if strategy == "dfs":
        pending = deque(reversed(initial_tasks))
    visited: set[tuple[str, str, int, str]] = set()
    records: list[TraversalRecord] = []

    def save(record: TraversalRecord) -> None:
        records.append(record)
        if record_path is not None:
            append_traversal_record(record, record_path)

    while pending:
        task = pending.popleft() if strategy == "bfs" else pending.pop()
        if task.key() in visited:
            continue
        visited.add(task.key())
        try:
            outcome = visit(task)
            if not isinstance(outcome, VisitResult):
                raise TypeError("visit 必须返回 VisitResult")
            save(
                TraversalRecord(
                    task_id=task.task_id,
                    keyword=task.keyword,
                    city=task.city,
                    page=task.page,
                    depth=task.depth,
                    strategy=strategy,
                    status="success",
                    result_count=max(0, int(outcome.result_count)),
                )
            )
            children = [child for child in outcome.children if child.depth <= max_depth]
            if strategy == "bfs":
                pending.extend(children)
            else:
                pending.extend(reversed(children))
        except (TypeError, ValueError, OSError, RuntimeError) as error:
            save(
                TraversalRecord(
                    task_id=task.task_id,
                    keyword=task.keyword,
                    city=task.city,
                    page=task.page,
                    depth=task.depth,
                    strategy=strategy,
                    status="failed",
                    result_count=0,
                    error_message=str(error),
                )
            )
    return records
