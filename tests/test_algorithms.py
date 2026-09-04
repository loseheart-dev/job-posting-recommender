"""郑维豪算法模块的验收测试。

覆盖《五人任务分工与验收清单》要求的案例：
- 正常数据：三类主题分析 + KMeans + 随机森林均可运行并输出；
- 空数据：明确报错；
- 缺字段：明确报错；
- 样本不足：聚类与薪资预测明确报错；
- 薪资缺失：薪资因素分析 / 薪资预测明确报错；
- 可选字段缺失（只有 JOB_COLUMNS）：仍可运行，因子按可用字段降级。

运行：
    python3 tests/test_algorithms.py
"""

from __future__ import annotations

import pandas as pd

from src.algorithms._common import experience_years, validate_jobs
from src.algorithms.clustering import cluster_jobs
from src.algorithms.company_profile import build_company_profiles
from src.algorithms.salary import analyze_salary_factors, predict_salary
from src.algorithms.skill_graph import build_skill_graph
from src.data.schema import JOB_COLUMNS
from tests.sample_data import build_sample_frame

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")


def expect_error(name: str, func: object, *args: object, keyword: str) -> None:
    """断言 func(*args) 抛出包含 keyword 的 ValueError。"""
    global PASS, FAIL
    try:
        func(*args)  # type: ignore[operator]
    except ValueError as error:
        if keyword in str(error):
            PASS += 1
            print(f"  [PASS] {name}（错误信息: {error}）")
        else:
            FAIL += 1
            print(f"  [FAIL] {name} 报错信息未含“{keyword}”: {error}")
    except Exception as error:  # noqa: BLE001
        FAIL += 1
        print(f"  [FAIL] {name} 抛出非预期异常: {type(error).__name__}: {error}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} 应抛出异常但没有")


def test_normal() -> None:
    print("[1/6] 正常数据案例")
    jobs = build_sample_frame()

    factors = analyze_salary_factors(jobs)
    check("薪资因素分析返回 4 个约定列", list(factors.columns) == ["factor", "impact_direction", "importance", "description"])
    check("薪资因素分析有输出", not factors.empty)
    check("方向取值合法", factors["impact_direction"].isin(["higher", "lower", "neutral"]).all())
    check("重要性在 0~1", factors["importance"].between(0, 1).all())

    graph = build_skill_graph(jobs)
    check("图谱返回 nodes/edges/skill_frequency", set(graph) == {"nodes", "edges", "skill_frequency"})
    check("技能频率非空", len(graph["skill_frequency"]) > 0)
    check("节点与频率一致", len(graph["nodes"]) == len(graph["skill_frequency"]))
    check("共现边权重为正", all(edge["weight"] > 0 for edge in graph["edges"]))

    profiles = build_company_profiles(jobs)
    check("企业画像返回 6 个约定列", list(profiles.columns) == ["company", "company_size", "company_nature", "industry", "salary_summary", "skill_summary"])
    check("企业画像有输出", not profiles.empty)
    check("薪资摘要有 mean", profiles["salary_summary"].iloc[0]["mean"] is not None)

    clustered, descriptions = cluster_jobs(jobs, n_clusters=3)
    check("聚类返回 cluster_id 列", "cluster_id" in clustered.columns)
    check("群组说明数量=3", len(descriptions) == 3)
    check("每个群组有说明", all("count" in info and "top_skills" in info for info in descriptions.values()))
    check("群组数量 ≤ 样本数", sum(info["count"] for info in descriptions.values()) == len(jobs))

    predicted, metrics = predict_salary(jobs)
    check("薪资预测返回 predicted_salary 列", "predicted_salary" in predicted.columns)
    check("指标键为 mae/r2", set(metrics) == {"mae", "r2"})
    check("MAE ≥ 0", metrics["mae"] >= 0)
    check("R² 为有限值", pd.notna(metrics["r2"]))


def test_empty() -> None:
    print("[2/6] 空数据案例")
    empty = pd.DataFrame(columns=JOB_COLUMNS)
    expect_error("空数据-因素分析", analyze_salary_factors, empty, keyword="为空")
    expect_error("空数据-能力图谱", build_skill_graph, empty, keyword="为空")
    expect_error("空数据-企业画像", build_company_profiles, empty, keyword="为空")
    expect_error("空数据-KMeans", cluster_jobs, empty, keyword="为空")
    expect_error("空数据-薪资预测", predict_salary, empty, keyword="为空")


def test_missing_columns() -> None:
    print("[3/6] 缺字段案例")
    jobs = build_sample_frame()
    missing = jobs.drop(columns=["skills"])
    expect_error("缺 skills 字段-因素分析", analyze_salary_factors, missing, keyword="skills")
    expect_error("缺 skills 字段-KMeans", cluster_jobs, missing, keyword="skills")
    missing_salary = jobs.drop(columns=["salary_avg"])
    expect_error("缺 salary_avg 字段-因素分析", analyze_salary_factors, missing_salary, keyword="salary_avg")
    expect_error("缺 salary_avg 字段-薪资预测", predict_salary, missing_salary, keyword="salary_avg")
    missing_company = jobs.drop(columns=["company"])
    expect_error("缺 company 字段-企业画像", build_company_profiles, missing_company, keyword="company")


def test_insufficient_samples() -> None:
    print("[4/6] 样本不足 / 薪资缺失案例")
    small = build_sample_frame().head(4)
    expect_error("样本不足-KMeans(4条分3类)", cluster_jobs, small, 3, keyword="样本不足")
    expect_error("样本不足-薪资预测(4条)", predict_salary, small, keyword="薪资有效样本过少")
    no_salary = build_sample_frame().copy()
    no_salary["salary_avg"] = None
    no_salary["salary_min"] = None
    no_salary["salary_max"] = None
    expect_error("薪资全缺失-因素分析", analyze_salary_factors, no_salary, keyword="薪资数据为空")
    expect_error("薪资全缺失-薪资预测", predict_salary, no_salary, keyword="样本过少")


def test_optional_columns_degradation() -> None:
    print("[5/6] 可选字段缺失降级案例（仅 JOB_COLUMNS）")
    full = build_sample_frame()
    core = full.loc[:, list(JOB_COLUMNS)]
    core[["company_size", "company_nature", "industry"]] = ""
    validate_jobs(core)
    factors = analyze_salary_factors(core)
    check("仅核心字段-因素分析可运行且非空", not factors.empty)
    check("仅核心字段-因素分析不含可选因子", not factors["factor"].str.startswith(("company_nature-", "company_size-", "industry-")).any())
    graph = build_skill_graph(core)
    check("仅核心字段-图谱可运行", len(graph["skill_frequency"]) > 0)
    clustered, descriptions = cluster_jobs(core, n_clusters=3)
    check("仅核心字段-KMeans可运行", "cluster_id" in clustered.columns)
    predicted, metrics = predict_salary(core)
    check("仅核心字段-薪资预测可运行", "predicted_salary" in predicted.columns)
    # company 属于 JOB_COLUMNS，企业画像仍可运行，仅可选字段为空
    profiles = build_company_profiles(core)
    check("仅核心字段-企业画像可运行", not profiles.empty)
    check("仅核心字段-企业画像可选字段为空", (profiles["company_size"] == "").all())

    minimal = full.loc[:, ["job_id", "title", "skills", "salary_avg"]]
    clustered_minimal, _ = cluster_jobs(minimal, n_clusters=3)
    check("仅必需字段-KMeans可运行", "cluster_id" in clustered_minimal.columns)
    predicted_minimal, _ = predict_salary(minimal)
    check("仅必需字段-薪资预测可运行", "predicted_salary" in predicted_minimal.columns)


def test_experience_mapping() -> None:
    print("[6/6] 经验区间映射案例")
    check("5-10年取区间中点", experience_years("5-10年") == 7.5)
    check("10年以上取保守估计", experience_years("10年以上") == 12.0)


def test_skill_noise_filter() -> None:
    print("[7/7] 技能白名单降噪案例")
    from src.algorithms._common import SKILL_WHITELIST, split_skills
    noisy = ("要求数据开发经验;非外包类;Python;SQL;不接受居家办公;"
             "计算机相关专业;Excel;数据平台开发经验")
    kept = split_skills(noisy)
    check("白名单过滤后保留真实技能", kept == ["Python", "SQL", "Excel"], str(kept))
    check("噪声词被过滤", not any(word in kept for word in ("要求数据开发经验", "非外包类", "不接受居家办公", "计算机相关专业", "数据平台开发经验")))
    check("样例技能均在白名单", all(s in SKILL_WHITELIST for s in split_skills("Python;SQL;Excel;Spark;PyTorch;机器学习;pandas;Hadoop;Hive")))
    # 应用到图谱：噪声不进入节点
    jobs = build_sample_frame().copy()
    jobs.loc[0, "skills"] = "Python;要求数据开发经验;非外包类"
    graph = build_skill_graph(jobs)
    node_ids = {node["id"] for node in graph["nodes"]}
    check("图谱节点不含噪声词", "要求数据开发经验" not in node_ids and "非外包类" not in node_ids)
    check("图谱节点保留真实技能", "Python" in node_ids)
    # known_only=False 仍可拿到原始拆分（供需要原始文本的场景）
    raw = split_skills("Python;非外包类", known_only=False)
    check("known_only=False 返回原始拆分", raw == ["Python", "非外包类"], str(raw))

def main() -> None:
    print("郑维豪算法模块验收测试\n")
    test_normal()
    test_empty()
    test_missing_columns()
    test_insufficient_samples()
    test_optional_columns_degradation()
    test_experience_mapping()
    test_skill_noise_filter()
    print(f"\n结果: {PASS} 通过, {FAIL} 失败")
    if FAIL:
        raise SystemExit(1)
    print("全部用例通过")


if __name__ == "__main__":
    main()
