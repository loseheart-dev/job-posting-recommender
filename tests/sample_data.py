"""生成符合《接口约定》的独立测试岗位数据（郑维豪算法模块使用）。

用法：
    python3 tests/sample_data.py            # 生成 tests/sample_jobs.csv
    python3 -c "from tests.sample_data import load_sample; df = load_sample()"

说明：
- 字段与《接口约定》岗位数据表保持一致（含公司性质/规模/行业等可选字段）；
- 样本模拟 BOSS 直聘大数据相关岗位，包含部分薪资缺失行，
  供正常数据、薪资缺失两类案例使用；
- 空数据、缺字段、样本不足案例在 test_algorithms.py 中构造。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

# 与《接口约定》岗位数据表一致的完整列
FULL_COLUMNS = (
    "job_id",
    "title",
    "company",
    "company_intro",
    "company_size",
    "company_nature",
    "industry",
    "city",
    "work_type",
    "experience",
    "education",
    "skills",
    "description",
    "benefits",
    "salary_text",
    "salary_min",
    "salary_max",
    "salary_avg",
    "source",
    "source_url",
    "crawled_at",
)

# (job_id, title, company, company_size, company_nature, industry, city, work_type,
#  experience, education, skills, salary_avg, source) —— 其余字段留空或由占位补齐
_ROWS: list[tuple[Any, ...]] = [
    ("j01", "数据分析师", "数海科技", "100-499人", "民营", "互联网", "杭州", "全职", "1-3年", "本科", "Python;SQL;pandas;Tableau", 15000, "BOSS直聘"),
    ("j02", "数据分析实习生", "数海科技", "100-499人", "民营", "互联网", "杭州", "实习", "在校生", "本科", "Python;SQL;Excel", None, "BOSS直聘"),
    ("j03", "数据开发工程师", "云帆数据", "500-999人", "民营", "大数据", "北京", "全职", "3-5年", "本科", "Python;Spark;Hadoop;Hive", 25000, "BOSS直聘"),
    ("j04", "算法工程师", "云帆数据", "500-999人", "民营", "大数据", "北京", "全职", "3-5年", "硕士", "Python;PyTorch;TensorFlow;机器学习", 32000, "BOSS直聘"),
    ("j05", "机器学习工程师", "智算未来", "1000-9999人", "上市公司", "人工智能", "上海", "全职", "5-10年", "硕士", "Python;PyTorch;深度学习;NLP", 38000, "BOSS直聘"),
    ("j06", "数据挖掘工程师", "智算未来", "1000-9999人", "上市公司", "人工智能", "上海", "全职", "1-3年", "本科", "Python;SQL;机器学习;scikit-learn", 20000, "BOSS直聘"),
    ("j07", "商业分析师", "蓝海咨询", "20-99人", "民营", "企业服务", "深圳", "全职", "3-5年", "本科", "SQL;Excel;PowerBI", 18000, "BOSS直聘"),
    ("j08", "BI 工程师", "蓝海咨询", "20-99人", "民营", "企业服务", "深圳", "全职", "1-3年", "本科", "SQL;Tableau;Python", 16000, "BOSS直聘"),
    ("j09", "大数据平台开发", "星图科技", "1000-9999人", "上市公司", "云计算", "广州", "全职", "5-10年", "本科", "Java;Spark;Flink;Kafka", 30000, "BOSS直聘"),
    ("j10", "数据仓库工程师", "星图科技", "1000-9999人", "上市公司", "云计算", "广州", "全职", "3-5年", "本科", "SQL;Hive;Spark;DataGrip", 22000, "BOSS直聘"),
    ("j11", "数据分析师", "橙子电商", "500-999人", "民营", "电子商务", "杭州", "全职", "1-3年", "本科", "Python;SQL;Excel;A/B测试", 14000, "BOSS直聘"),
    ("j12", "数据分析实习生", "橙子电商", "500-999人", "民营", "电子商务", "杭州", "实习", "在校生", "本科", "Excel;SQL", None, "BOSS直聘"),
    ("j13", "风控算法工程师", "信安金融", "1000-9999人", "国企", "金融", "上海", "全职", "3-5年", "硕士", "Python;机器学习;特征工程;SQL", 28000, "BOSS直聘"),
    ("j14", "量化研究员", "信安金融", "1000-9999人", "国企", "金融", "上海", "全职", "5-10年", "博士", "Python;C++;统计建模;金融工程", 45000, "BOSS直聘"),
    ("j15", "数据产品经理", "极客软件", "100-499人", "民营", "软件", "成都", "全职", "3-5年", "本科", "SQL;数据分析;产品设计", 19000, "BOSS直聘"),
    ("j16", "后端开发工程师", "极客软件", "100-499人", "民营", "软件", "成都", "全职", "1-3年", "本科", "Python;Django;MySQL;Redis", 16000, "BOSS直聘"),
    ("j17", "数据治理工程师", "政务云科技", "1000-9999人", "国企", "政务信息化", "北京", "全职", "3-5年", "本科", "SQL;数据治理;元数据;Python", 21000, "BOSS直聘"),
    ("j18", "数据分析师", "政务云科技", "1000-9999人", "国企", "政务信息化", "北京", "全职", "1-3年", "本科", "Python;SQL;Excel", 15000, "BOSS直聘"),
    ("j19", "推荐算法工程师", "桃桃视频", "1000-9999人", "上市公司", "内容社区", "武汉", "全职", "5-10年", "硕士", "Python;推荐系统;协同过滤;深度学习", 36000, "BOSS直聘"),
    ("j20", "增长数据分析师", "桃桃视频", "1000-9999人", "上市公司", "内容社区", "武汉", "全职", "1-3年", "本科", "SQL;Python;用户增长;A/B测试", 17000, "BOSS直聘"),
    ("j21", "数据工程师", "链家信息", "1000-9999人", "民营", "房产", "南京", "全职", "3-5年", "本科", "Python;Spark;Hive;Airflow", 23000, "BOSS直聘"),
    ("j22", "数据分析师", "链家信息", "1000-9999人", "民营", "房产", "南京", "全职", "应届", "本科", "SQL;Excel;Python", 12000, "BOSS直聘"),
    ("j23", "大模型训练工程师", "深智科技", "500-999人", "民营", "人工智能", "杭州", "全职", "5-10年", "硕士", "Python;PyTorch;大模型;分布式训练", 42000, "BOSS直聘"),
    ("j24", "数据标注质检", "深智科技", "500-999人", "民营", "人工智能", "杭州", "全职", "经验不限", "大专", "Excel;数据标注", 8000, "BOSS直聘"),
    ("j25", "数据分析师", "光年出行", "1000-9999人", "上市公司", "出行", "广州", "全职", "3-5年", "本科", "Python;SQL;机器学习;地图数据", 22000, "BOSS直聘"),
    ("j26", "数据分析实习生", "光年出行", "1000-9999人", "上市公司", "出行", "广州", "实习", "在校生", "本科", "SQL;Excel", None, "BOSS直聘"),
    ("j27", "数据产品经理", "小象教育", "100-499人", "民营", "教育", "北京", "全职", "1-3年", "本科", "SQL;数据分析;产品设计", 18000, "BOSS直聘"),
    ("j28", "BI 数据分析师", "小象教育", "100-499人", "民营", "教育", "北京", "全职", "1-3年", "本科", "SQL;Tableau;Excel", 15000, "BOSS直聘"),
    ("j29", "数据库管理员", "恒信证券", "1000-9999人", "国企", "金融", "上海", "全职", "3-5年", "本科", "MySQL;Oracle;SQL;数据库调优", 20000, "BOSS直聘"),
    ("j30", "数据架构师", "恒信证券", "1000-9999人", "国企", "金融", "上海", "全职", "10年以上", "硕士", "Spark;Hadoop;数据架构;Java", 48000, "BOSS直聘"),
]


def build_sample_frame() -> pd.DataFrame:
    """构造完整字段的测试岗位表。"""
    records: list[dict[str, Any]] = []
    for row in _ROWS:
        (
            job_id,
            title,
            company,
            company_size,
            company_nature,
            industry,
            city,
            work_type,
            experience,
            education,
            skills,
            salary_avg,
            source,
        ) = row
        records.append(
            {
                "job_id": job_id,
                "title": title,
                "company": company,
                "company_intro": "",
                "company_size": company_size,
                "company_nature": company_nature,
                "industry": industry,
                "city": city,
                "work_type": work_type,
                "experience": experience,
                "education": education,
                "skills": skills,
                "description": f"{title} 相关岗位职责",
                "benefits": "五险一金;带薪年假",
                "salary_text": f"{salary_avg * 12}-{salary_avg * 14} 薪" if salary_avg else "",
                "salary_min": salary_avg,
                "salary_max": salary_avg * 1.2 if salary_avg else None,
                "salary_avg": salary_avg,
                "source": source,
                "source_url": f"https://www.zhipin.com/job/{job_id}",
                "crawled_at": "2026-08-20T10:00:00+08:00",
            }
        )
    return pd.DataFrame(records, columns=list(FULL_COLUMNS))


def load_sample(csv_path: str | Path | None = None) -> pd.DataFrame:
    """读取样例 CSV；未指定路径时使用 tests/sample_jobs.csv。"""
    path = Path(csv_path) if csv_path else Path(__file__).parent / "sample_jobs.csv"
    if not path.exists():
        build_sample_frame().to_csv(path, index=False, encoding="utf-8")
    return pd.read_csv(path)


if __name__ == "__main__":
    output = Path(__file__).parent / "sample_jobs.csv"
    build_sample_frame().to_csv(output, index=False, encoding="utf-8")
    print(f"样例数据已生成: {output}（{len(build_sample_frame())} 行）")
