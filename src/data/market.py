"""岗位市场分类与分层抽样工具。

岗位类别是由标题和行业推导的分析字段，不改变冻结的 21 列岗位接口。
分类优先使用岗位标题，行业只在标题无法判断时作为兜底，避免技能标签中的
“财务”“金融”等业务领域词把 Java/数据开发岗位误分类。
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.data.schema import JOB_COLUMNS

JOB_CATEGORIES = ("技术", "财务", "销售", "行政", "制造", "其他")

_CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    # 制造业先于技术业判断，避免“机械工程师”被通用工程词误归技术。
    "制造": (
        "机械", "电气", "电子", "汽车", "制造", "工艺", "设备", "生产", "质量",
        "自动化", "模具", "建筑", "土木", "化工", "材料", "厂长", "技师",
    ),
    "技术": (
        "AI", "人工智能", "算法", "数据", "开发", "程序", "软件", "Java", "Python",
        "前端", "后端", "测试", "运维", "数据库", "云计算", "网络", "架构", "研发",
        "信息化", "系统", "IT", "BI", "ETL", "数仓", "视觉", "NLP",
    ),
    "财务": ("财务", "会计", "出纳", "审计", "税务", "资金", "结算"),
    "销售": (
        "销售", "业务员", "商务", "BD", "渠道", "客户经理", "招商主管", "导购",
        "店长", "电话销售", "销售代表", "销售顾问",
    ),
    "行政": ("行政", "人事", "人力资源", "文员", "前台", "客服", "助理", "招聘", "采购"),
}

_OTHER_TITLE_KEYWORDS = (
    "产品", "运营", "物流", "供应链", "教师", "老师", "翻译", "法务", "医疗", "市场",
    "咨询", "研究员", "管培生",
)

_INDUSTRY_PATTERNS: dict[str, tuple[str, ...]] = {
    "技术": ("计算机软件", "互联网", "人工智能", "通信", "网络设备", "电子商务", "大数据", "智能硬件", "半导体", "信息技术"),
    "财务": ("财务", "审计", "税务", "银行", "证券", "保险", "金融"),
    "销售": ("批发/零售", "进出口贸易", "贸易", "销售"),
    "行政": ("人力资源", "物业", "专业服务", "咨询"),
    "制造": ("汽车", "机械", "电子/硬件", "自动化", "设备", "制造", "建筑", "化工", "材料"),
}


def _text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def _matches(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def classify_job_category(title: Any, industry: Any = "") -> str:
    """根据岗位标题和行业推导一个稳定的岗位类别。"""
    title_text = _text(title)
    industry_text = _text(industry)
    for category in ("制造", "销售", "行政", "技术", "财务"):
        if _matches(title_text, _CATEGORY_PATTERNS[category]):
            return category
    if _matches(title_text, _OTHER_TITLE_KEYWORDS):
        return "其他"
    for category in ("技术", "财务", "销售", "行政", "制造"):
        if _matches(industry_text, _INDUSTRY_PATTERNS[category]):
            return category
    return "其他"


def add_job_category(jobs: pd.DataFrame) -> pd.DataFrame:
    """返回带 ``job_category`` 分析列的副本，不修改输入数据。"""
    if not isinstance(jobs, pd.DataFrame):
        raise TypeError("岗位数据必须是 pandas.DataFrame")
    result = jobs.copy()
    title = result["title"] if "title" in result.columns else pd.Series("", index=result.index)
    industry = result["industry"] if "industry" in result.columns else pd.Series("", index=result.index)
    result["job_category"] = [
        classify_job_category(raw_title, raw_industry)
        for raw_title, raw_industry in zip(title, industry, strict=False)
    ]
    return result


def stratified_sample_jobs(
    jobs: pd.DataFrame,
    per_category: int = 500,
    random_state: int = 42,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """按岗位类别等额抽样，返回标准岗位列和可审计的抽样报告。

    每类最多抽 ``per_category`` 条；某类样本不足时保留该类全部记录，报告中
    的 ``shortfall`` 会明确指出未达到目标的类别。抽样使用固定随机种子并按
    原始行号恢复顺序，便于复现和与来源数据核对。
    """
    if not isinstance(jobs, pd.DataFrame):
        raise TypeError("岗位数据必须是 pandas.DataFrame")
    if isinstance(per_category, bool) or not isinstance(per_category, int) or per_category < 1:
        raise ValueError("per_category 必须是正整数")
    missing = [column for column in ("job_id", "title") if column not in jobs.columns]
    if missing:
        raise ValueError(f"岗位表缺少必填字段: {', '.join(missing)}")
    if jobs.empty:
        empty = jobs.loc[:, [column for column in JOB_COLUMNS if column in jobs.columns]].copy()
        return empty, {
            "input_count": 0,
            "output_count": 0,
            "target_per_category": per_category,
            "random_state": random_state,
            "before": {},
            "after": {},
            "shortfall": list(JOB_CATEGORIES),
        }

    categorized = add_job_category(jobs)
    before = categorized["job_category"].value_counts().reindex(JOB_CATEGORIES, fill_value=0).astype(int)
    pieces: list[pd.DataFrame] = []
    for category in JOB_CATEGORIES:
        group = categorized[categorized["job_category"] == category]
        if group.empty:
            continue
        count = min(per_category, len(group))
        pieces.append(group.sample(n=count, random_state=random_state))
    sampled = pd.concat(pieces).sort_index()
    output = sampled.loc[:, [column for column in JOB_COLUMNS if column in sampled.columns]].reset_index(drop=True)
    after = sampled["job_category"].value_counts().reindex(JOB_CATEGORIES, fill_value=0).astype(int)
    return output, {
        "input_count": int(len(jobs)),
        "output_count": int(len(output)),
        "target_per_category": per_category,
        "random_state": random_state,
        "before": {category: int(before[category]) for category in JOB_CATEGORIES},
        "after": {category: int(after[category]) for category in JOB_CATEGORIES},
        "shortfall": [category for category in JOB_CATEGORIES if int(before[category]) < per_category],
    }
