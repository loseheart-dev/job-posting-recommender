"""岗位市场分类与定向补采关键词。

岗位类别是由标题和行业推导的分析字段，不改变冻结的 21 列岗位接口。
分类优先使用岗位标题，行业只在标题无法判断时作为兜底，避免技能标签中的
“财务”“金融”等业务领域词把 Java/数据开发岗位误分类。
"""

from __future__ import annotations

from typing import Any

import pandas as pd

JOB_CATEGORIES = ("技术", "财务", "销售", "行政", "制造", "其他")

MARKET_SUPPLEMENT_CITIES = (
    "北京", "上海", "广州", "深圳", "杭州", "南京", "苏州", "武汉",
    "成都", "重庆", "西安", "天津", "昆明", "青岛", "沈阳", "南宁",
    "贵阳", "珠海", "海口", "厦门", "郑州", "东莞", "无锡", "济南",
)

MARKET_SUPPLEMENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "技术": ("Java开发", "Python开发", "数据分析", "测试工程师", "运维工程师", "前端开发"),
    "财务": (
        "财务专员", "会计", "出纳", "审计", "税务", "财务分析", "会计助理",
        "财务经理", "财务主管", "成本会计", "总账会计", "资金专员", "结算专员",
    ),
    "销售": (
        "销售代表", "销售顾问", "客户经理", "商务拓展", "渠道销售", "电话销售", "销售经理",
        "大客户销售", "销售支持", "海外销售", "招商主管", "置业顾问", "店员",
    ),
    "行政": (
        "行政专员", "人事专员", "招聘专员", "前台", "文员", "行政助理", "客服",
        "人力资源", "HRBP", "薪酬绩效", "培训专员", "采购专员", "客户成功",
    ),
    "制造": (
        "机械工程师", "电气工程师", "生产管理", "质量工程师", "工艺工程师", "设备工程师", "自动化工程师",
        "模具工程师", "维修工程师", "生产计划", "车间主任", "数控工程师", "焊接工程师",
    ),
    "其他": (
        "产品经理", "产品运营", "运营专员", "物流专员", "仓库管理员", "供应链专员", "市场专员",
        "市场营销", "教师", "老师", "护士", "医生", "药剂师", "律师", "法务",
        "平面设计", "UI设计", "室内设计", "翻译", "咨询顾问", "研究员", "酒店管理",
    ),
}

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
    "咨询", "研究员", "管培生", "护士", "医生", "药剂师", "律师", "设计",
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
