"""算法模块共享的内部工具（郑维豪维护）。

这些函数仅供 src/algorithms 包内部使用，不构成对外接口。
对外契约以《接口约定》和 src/data/schema.py 为准。

设计要点：
- 岗位表必填字段缺失或为空时，抛出具名明确错误；
- 可选分析字段（公司性质、公司规模、行业等）存在则参与分析，
  缺失则优雅跳过，保证冻结的 JOB_COLUMNS 也能运行。
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

import pandas as pd

# 必填字段：缺失时直接报错，避免后续静默出错
REQUIRED_COLUMNS = ("job_id", "title", "skills")

# 可选因子字段：存在才参与因素分析 / 特征编码
OPTIONAL_FACTOR_COLUMNS = (
    "city",
    "work_type",
    "experience",
    "education",
    "company_nature",
    "company_size",
    "industry",
)
# 技能白名单：只保留真实技能词，过滤“要求xx经验/非外包类/不接受居家办公”等噪声，
# 用于降噪技能图谱、企业画像技能摘要与聚类/预测的特征编码。
SKILL_WHITELIST: frozenset[str] = frozenset({
    # --- 常见编程语言与开发工具 ---
    "Python", "SQL", "Java", "C++", "C", "C#", "Go", "Scala", "R", "MATLAB",
    "JavaScript", "TypeScript", "Node.js", "React", "Vue", "HTML", "CSS",
    "Shell", "Bash", "PowerShell", "Vim", "Regex", "Git", "Linux",
    "Docker", "Kubernetes", "Nginx", "Spring", "SpringBoot", "SpringCloud",
    "MyBatis", "Hibernate", "FastAPI", "Flask", "Django", "Tornado", "Celery",
    # --- 数据处理 / 大数据 / 数据库 ---
    "Excel", "pandas", "NumPy", "SciPy", "Matplotlib", "Seaborn", "Plotly",
    "Spark", "PySpark", "Hadoop", "Hive", "Flink", "Kafka", "HDFS", "HBase",
    "Zookeeper", "Storm", "Pulsar", "RocketMQ", "RabbitMQ", "ETL", "DataX",
    "Sqoop", "Flume", "Oozie", "Azkaban", "Airflow", "Presto", "Trino",
    "MySQL", "Oracle", "PostgreSQL", "MongoDB", "Redis", "Memcached",
    "Cassandra", "Elasticsearch", "ClickHouse", "Snowflake", "Vertica",
    "Doris", "Iceberg", "Hudi", "Neo4j", "DataGrip",
    # --- 机器学习 / 深度学习 / 数据分析工具 ---
    "PyTorch", "TensorFlow", "Keras", "PaddlePaddle", "OpenCV", "scikit-learn",
    "XGBoost", "LightGBM", "CatBoost", "GBDT", "SVM", "MLflow", "Tableau",
    "PowerBI", "Superset", "ECharts", "NLP",
    # --- 测试 / 运维 / 工程化 ---
    "Selenium", "Scrapy", "BeautifulSoup", "lxml", "Jenkins", "GitLab",
    "Ansible", "Terraform", "Prometheus", "Grafana", "RESTful", "GraphQL",
    "gRPC", "WebSocket", "DevOps", "CI/CD", "微服务", "分布式", "高并发",
    "消息队列", "性能优化", "自动化测试", "接口测试", "云计算",
    # --- 中文通用技能 / 业务技能（与样例数据保持一致） ---
    "机器学习", "深度学习", "数据分析", "数据挖掘", "数据标注", "数据治理",
    "数据架构", "数据库调优", "特征工程", "统计建模", "推荐系统", "大模型",
    "协同过滤", "分布式训练", "用户增长", "产品设计", "元数据", "金融工程",
    "A/B测试", "数据仓库", "数据采集", "数据可视化", "自然语言处理",
    "计算机视觉", "语音识别", "强化学习", "知识图谱", "图神经网络",
    "迁移学习", "联邦学习", "数据安全", "数据产品", "商业分析", "需求分析",
    "用户研究", "爬虫", "大数据", "数据开发", "数仓", "埋点", "漏斗分析",
    "留存分析", "算法优化", "数据清洗", "数据建模", "数据报表", "经营分析",
    "数据中台", "数据湖", "数据管道", "推荐算法", "排序算法", "风控算法",
    "广告算法", "搜索算法", "数据运营", "指标体系", "数据结构", "算法",
    "统计学", "概率论", "项目管理", "敏捷开发",
    # --- 财务 / 销售 / 行政 / 制造 / 运营岗位技能 ---
    "财务", "会计", "会计核算", "财务分析", "成本", "成本控制", "总账", "收入账",
    "应收应付", "应收账款", "应付账款", "预算", "资金管理", "结算", "税务", "税务筹划",
    "审计", "内部审计", "外部审计", "固定资产核算", "代理记账", "CPA", "金蝶", "用友",
    "电话销售", "面销/陌拜", "网络销售", "企业服务", "金融产品", "客户签约", "客户开发",
    "客户邀约", "客户关系维护", "会展销售", "渠道关系维护", "渠道客户开发", "商务谈判",
    "沟通能力", "沟通协调", "招商拓展", "门店销售", "售前服务", "售后服务", "营销策划",
    "行政", "行政前台", "行政管理", "客服", "电话客服", "线上客服", "售前客服", "售后客服",
    "人力资源", "招聘", "薪酬绩效", "培训", "办公软件", "ERP", "B端产品", "C端产品",
    "产品运营", "用户运营", "内容运营", "产品设计", "数据产品", "市场调研", "市场推广",
    "教育培训", "线下教育", "教师", "课程设计", "平面设计", "物流管理", "库存控制",
    "货物验收", "货物出库", "SolidWorks", "AutoCAD", "PLC", "UG", "CAD", "电工证",
    "QC七大手法", "CATIA", "Pro/E", "生产计划", "生产成本管理", "生产设备管理", "质量管理",
    "自动化", "设备维护", "供应链管理", "仓储管理", "机械制图", "焊接", "数控",
})

# 采集站点会把同一技能写成多个标签；只在白名单模式下归一化，避免
# known_only=False 的调用失去原始字段语义。
SKILL_ALIASES: dict[str, str] = {
    "C/C++": "C++",
    "Golang": "Go",
    "MySQL/SQL Server": "MySQL",
    "数据分析能力": "数据分析",
    "数据分析能力好": "数据分析",
    "数据分析能力强": "数据分析",
    "掌握财务知识": "财务",
    "中级会计师": "会计",
    "初级会计师": "会计",
    "会计从业资格证": "会计",
    "注册税务师": "税务",
    "税务代理/咨询": "税务",
    "税务筹划代理公司": "税务筹划",
    "渠道/机构客户开发": "渠道客户开发",
    "较强的沟通协调能力": "沟通协调",
    "较强的渠道拓展能力": "渠道客户开发",
    "熟练使用ERP系统": "ERP",
    "生产计划与物流控制": "生产计划",
    "PQE经验（制程）": "质量管理",
    "CQE经验（客户）": "质量管理",
    "PLC工程师": "PLC",
}


def validate_jobs(jobs: pd.DataFrame) -> None:
    """校验输入岗位表：必须是 DataFrame、非空、含必填字段。"""
    if not isinstance(jobs, pd.DataFrame):
        raise ValueError("输入必须是 pandas.DataFrame")
    if jobs.empty:
        raise ValueError("岗位数据为空，无法进行分析")
    missing = [column for column in REQUIRED_COLUMNS if column not in jobs.columns]
    if missing:
        raise ValueError(f"岗位表缺少必填字段: {', '.join(missing)}")


def available_columns(jobs: pd.DataFrame, names: Iterable[str]) -> list[str]:
    """返回实际存在于输入表中的字段名列表。"""
    return [name for name in names if name in jobs.columns]


def split_skills(skills: object, known_only: bool = True) -> list[str]:
    """将 skills 按英文分号拆分，去空并保序去重。

    known_only=True 时只保留白名单内的真实技能词，过滤
    “要求xx经验/非外包类/不接受居家办公/计算机相关专业”等非技能噪声。
    """
    if skills is None:
        return []
    if isinstance(skills, (list, tuple, set)):
        values = [str(skill) for skill in skills]
    else:
        values = str(skills).split(";")
    seen: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        canonical = SKILL_ALIASES.get(cleaned, cleaned) if known_only else cleaned
        if canonical in seen:
            continue
        if known_only and canonical not in SKILL_WHITELIST:
            continue
        seen.append(canonical)
    return seen


def top_skills(jobs: pd.DataFrame, n: int = 10) -> list[tuple[str, int]]:
    """统计技能频次，按 (频次降序, 名称) 返回前 n 个 (技能, 次数)。"""
    counts: Counter[str] = Counter()
    for raw in jobs["skills"].dropna():
        for skill in split_skills(raw):
            counts[skill] += 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:n]


def _feature_skill_vocabulary(jobs: pd.DataFrame, n: int) -> list[str]:
    """Use each job category's frequent skills instead of one global Top-N list."""
    if "job_category" not in jobs.columns:
        return [skill for skill, _ in top_skills(jobs, n)]
    categories = sorted(
        category
        for category in jobs["job_category"].fillna("").astype(str).unique()
        if category
    )
    vocabulary: list[str] = []
    for category in categories:
        group = jobs[jobs["job_category"].fillna("").astype(str) == category]
        for skill, _ in top_skills(group, n):
            if skill not in vocabulary:
                vocabulary.append(skill)
    return vocabulary or [skill for skill, _ in top_skills(jobs, n)]


def education_level(value: object) -> int:
    """学历映射为有序数值；未知或缺失返回 0。"""
    if value is None:
        return 0
    text = str(value)
    if "博士" in text:
        return 5
    if "硕士" in text or "研究生" in text:
        return 4
    if "本科" in text:
        return 3
    if "大专" in text or "专科" in text:
        return 2
    if "高中" in text or "中专" in text or "初中" in text:
        return 1
    return 0


def experience_years(value: object) -> float:
    """经验文本映射为年限（区间取中点）；未知返回 0。"""
    if value is None:
        return 0.0
    text = str(value)
    if "经验不限" in text or "在校生" in text or "应届" in text:
        return 0.0
    if "5-10" in text or "5~10" in text:
        return 7.5
    if "10年" in text:
        return 12.0
    if "3-5" in text or "3~5" in text:
        return 4.0
    if "1-3" in text or "1~3" in text:
        return 2.0
    if "1年" in text:
        return 1.0
    if "3年" in text:
        return 3.0
    if "5年" in text:
        return 5.0
    return 0.0


def company_size_level(value: object) -> float:
    """公司规模文本提取人数下限（如“100-499人”→100）；未知返回 0。"""
    if value is None:
        return 0.0
    numbers = re.findall(r"\d+", str(value))
    return float(numbers[0]) if numbers else 0.0


def salary_stats(series: pd.Series) -> dict[str, object]:
    """薪资列统计摘要（只统计非空），样本为 0 时返回空标记。"""
    valid = pd.to_numeric(series, errors="coerce").dropna()
    if valid.empty:
        return {"count": 0, "mean": None, "min": None, "max": None}
    return {
        "count": int(valid.size),
        "mean": round(float(valid.mean()), 2),
        "min": round(float(valid.min()), 2),
        "max": round(float(valid.max()), 2),
    }
# 疑似异常低薪阈值（元/月）：低于该值的有效薪资大概率是“元/时”未折算等解析异常。
SALARY_ABNORMAL_LOW = 500.0

def flag_abnormal_salary(
    jobs: pd.DataFrame,
    low_threshold: float = SALARY_ABNORMAL_LOW,
) -> pd.Series:
    """标记疑似异常薪资（算法层兜底）。

    薪资有效但低于 low_threshold 视为 True，例如“5-20元/时”被解析成
    12.5 元/月（未折算）。高薪不能仅按金额判定异常，因为算法输入不含
    salary_text，无法区分合法高薪与错误折算值。
    用于在因素分析与薪资预测中剔除异常低薪，避免污染整体均值与因子方向。
    返回与输入同索引的布尔 Series；缺少 salary_avg 字段时全部为 False。
    """
    if "salary_avg" not in jobs.columns:
        return pd.Series(False, index=jobs.index)
    salary = pd.to_numeric(jobs["salary_avg"], errors="coerce")
    return salary.notna() & (salary < low_threshold)


def encode_job_features(
    jobs: pd.DataFrame,
    top_skills_n: int = 10,
    top_cities_n: int = 5,
    include_salary: bool = True,
) -> pd.DataFrame:
    """把岗位表编码为数值特征矩阵（KMeans 与随机森林共用）。

    - 技能：Top N 技能 one-hot；
    - 学历、经验、公司规模：有序数值；
    - 城市、公司性质、行业：Top 取值 one-hot，其余归入其他；
    - include_salary=True 时加入 salary_avg（聚类用），预测薪资时应为 False。

    返回 DataFrame 与输入同索引，首列为 job_id 便于对回结果。
    """
    validate_jobs(jobs)
    features: dict[str, pd.Series] = {}

    skill_top = _feature_skill_vocabulary(jobs, top_skills_n)
    for skill in skill_top:
        features[f"skill_{skill}"] = jobs["skills"].fillna("").map(
            lambda raw: 1.0 if skill in split_skills(raw) else 0.0
        )

    empty_text = pd.Series("", index=jobs.index, dtype="object")
    education = jobs["education"] if "education" in jobs.columns else empty_text
    experience = jobs["experience"] if "experience" in jobs.columns else empty_text
    features["education_level"] = education.map(education_level).astype(float)
    features["experience_years"] = experience.map(experience_years).astype(float)
    if "company_size" in jobs.columns:
        features["company_size_level"] = (
            jobs["company_size"].map(company_size_level).astype(float)
        )

    if "city" in jobs.columns:
        city_counts = jobs["city"].fillna("").astype(str).value_counts()
        city_top = [city for city in city_counts.index[:top_cities_n] if city]
        for city in city_top:
            features[f"city_{city}"] = (
                jobs["city"].fillna("").astype(str) == city
            ).astype(float)
        features["city_other"] = (
            ~jobs["city"].fillna("").astype(str).isin(city_top)
        ).astype(float)

    for column, top_n in (("company_nature", 5), ("industry", 5)):
        if column in jobs.columns:
            value_counts = jobs[column].fillna("").astype(str).value_counts()
            value_top = [value for value in value_counts.index[:top_n] if value]
            for value in value_top:
                features[f"{column}_{value}"] = (
                    jobs[column].fillna("").astype(str) == value
                ).astype(float)

    if "job_category" in jobs.columns:
        categories = sorted(
            category
            for category in jobs["job_category"].fillna("").astype(str).unique()
            if category
        )
        for category in categories:
            features[f"job_category_{category}"] = (
                jobs["job_category"].fillna("").astype(str) == category
            ).astype(float)

    if include_salary and "salary_avg" in jobs.columns:
        salary = pd.to_numeric(jobs["salary_avg"], errors="coerce")
        fallback = salary.median() if salary.notna().any() else 0.0
        features["salary_avg"] = salary.fillna(fallback)

    result = pd.DataFrame(features, index=jobs.index)
    result.insert(0, "job_id", jobs["job_id"].astype(str).values)
    return result
