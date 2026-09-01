"""用于组织 BOSS 搜索任务的 BFS/DFS 遍历。"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
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


def build_search_tasks(
    keywords: Iterable[str], cities: Iterable[str], pages: int = 1
) -> list[CrawlTask]:
    """按关键词、城市和页码生成稳定的待采集任务。"""

    if pages < 1:
        raise ValueError("采集页数必须大于 0")
    tasks: list[CrawlTask] = []
    index = 0
    for keyword in keywords:
        for city in cities:
            for page in range(1, pages + 1):
                index += 1
                tasks.append(
                    CrawlTask(
                        task_id=f"search-{index}",
                        keyword=str(keyword).strip(),
                        city=str(city).strip(),
                        page=page,
                    )
                )
    return tasks


def traverse_tasks(
    tasks: Iterable[CrawlTask],
    strategy: str,
    visit: Callable[[CrawlTask], VisitResult],
    *,
    max_depth: int = 0,
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

    while pending:
        task = pending.popleft() if strategy == "bfs" else pending.pop()
        if task.key() in visited:
            continue
        visited.add(task.key())
        try:
            outcome = visit(task)
            if not isinstance(outcome, VisitResult):
                raise TypeError("visit 必须返回 VisitResult")
            records.append(
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
        except (TypeError, ValueError, OSError) as error:
            records.append(
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
