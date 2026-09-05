"""岗位能力需求图谱（郑维豪负责）。

对外接口：
- build_skill_graph(jobs, min_cooccurrence=1, category=None, balanced=False) -> {nodes, edges, skill_frequency}

统计技能出现频次与同一岗位内的技能共现关系，输出可被前端
渲染为图谱的节点、边和频率数据。
"""

from __future__ import annotations

from collections import Counter

import pandas as pd

from src.algorithms._common import balanced_top_skills, split_skills, validate_jobs
from src.data.market import add_job_category
from src.data.schema import SKILL_GRAPH_KEYS


def build_skill_graph(
    jobs: pd.DataFrame,
    min_cooccurrence: int = 1,
    category: str | None = None,
    balanced: bool = False,
) -> dict[str, object]:
    """构建岗位能力需求图谱。

    返回结构（SKILL_GRAPH_KEYS）：
    - nodes: [{id, label, count}]，技能节点及出现频次；
    - edges: [{source, target, weight}]，同一岗位共同出现的技能对及次数；
    - skill_frequency: [(skill, count), ...]，按频次降序；category 传入时只统计该岗位类别。
      balanced=True 且未指定 category 时，改为类别等权技能覆盖率排名。
    """
    validate_jobs(jobs)
    source = jobs
    if category:
        categorized = add_job_category(jobs)
        source = categorized[categorized["job_category"] == category]
    skill_counter: Counter[str] = Counter()
    pair_counter: Counter[tuple[str, str]] = Counter()

    for raw in source["skills"].dropna():
        skills = split_skills(raw)
        for skill in skills:
            skill_counter[skill] += 1
        for i in range(len(skills)):
            for j in range(i + 1, len(skills)):
                pair = tuple(sorted((skills[i], skills[j])))
                pair_counter[pair] += 1

    nodes = [
        {"id": skill, "label": skill, "count": count}
        for skill, count in skill_counter.most_common()
    ]
    edges = [
        {"source": a, "target": b, "weight": weight}
        for (a, b), weight in sorted(pair_counter.items(), key=lambda item: -item[1])
        if weight >= min_cooccurrence
    ]
    skill_frequency = (
        balanced_top_skills(jobs)
        if balanced and category is None
        else list(skill_counter.most_common())
    )
    return {
        "nodes": nodes,
        "edges": edges,
        "skill_frequency": skill_frequency,
    }
