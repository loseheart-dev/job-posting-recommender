"""薪资因素分析与随机森林薪资预测（郑维豪负责）。

对外接口：
- analyze_salary_factors(jobs) -> DataFrame[factor, impact_direction, importance, description]
- predict_salary(jobs) -> (DataFrame[..., predicted_salary], {mae, r2})

设计约束（对齐《接口约定》与《五人任务分工与验收清单》）：
- 只读清洗后的标准岗位表，不读文件、不调用页面；
- 薪资因素分析输出的是采集样本中的统计关联，不表述为因果结论；
- 薪资缺失、样本不足、字段缺失时抛出明确中文错误。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from src.algorithms._common import available_columns, encode_job_features, validate_jobs
from src.data.schema import SALARY_FACTOR_COLUMNS, SALARY_METRIC_KEYS

# 因素分析考虑的因素字段（可选字段存在才参与）
FACTOR_FIELDS = (
    "education",
    "experience",
    "city",
    "work_type",
    "company_nature",
    "company_size",
    "industry",
)

MIN_FACTOR_SAMPLES = 2  # 单个因子取值至少需要的薪资样本数


def _factor_groups(
    jobs: pd.DataFrame, column: str
) -> tuple[list[str], np.ndarray, np.ndarray]:
    """按因子取值统计平均月薪与样本数（只统计薪资非空的岗位）。"""
    salary = pd.to_numeric(jobs["salary_avg"], errors="coerce")
    temp = jobs[[column]].copy()
    temp["_salary"] = salary
    temp = temp.dropna(subset=["_salary"])
    temp[column] = temp[column].fillna("未知").astype(str).str.strip()
    grouped = temp.groupby(column, dropna=False)["_salary"]
    means = grouped.mean()
    counts = grouped.size()
    return list(means.index), means.values.astype(float), counts.values.astype(float)


def analyze_salary_factors(jobs: pd.DataFrame, min_samples: int = MIN_FACTOR_SAMPLES) -> pd.DataFrame:
    """薪资影响因素分析。

    对每个可用因子按取值分组统计平均月薪，相对整体均值给出方向
    （higher / lower / neutral），以组间加权离散度归一化得到重要性，
    并输出可读说明。只描述统计关联，不作因果结论。
    """
    validate_jobs(jobs)
    if "salary_avg" not in jobs.columns:
        raise ValueError("岗位表缺少字段: salary_avg，无法进行薪资因素分析")
    salary = pd.to_numeric(jobs["salary_avg"], errors="coerce")
    if salary.notna().sum() < 1:
        raise ValueError("薪资数据为空，无法进行薪资因素分析")
    overall_mean = float(salary.mean())

    rows: list[dict[str, object]] = []
    for column in available_columns(jobs, FACTOR_FIELDS):
        values, means, counts = _factor_groups(jobs, column)
        if len(values) < 2 or int(counts.min()) < min_samples:
            continue  # 有效取值或样本不足的因子直接跳过
        weighted_var = np.average((means - overall_mean) ** 2, weights=counts)
        importance = float(min(1.0, np.sqrt(weighted_var) / max(overall_mean, 1.0)))
        for value, mean, count in zip(values, means, counts):
            if mean > overall_mean * 1.05:
                direction = "higher"
            elif mean < overall_mean * 0.95:
                direction = "lower"
            else:
                direction = "neutral"
            rows.append(
                {
                    "factor": f"{column}-{value}",
                    "impact_direction": direction,
                    "importance": round(importance, 4),
                    "description": (
                        f"该组岗位平均月薪 {mean:.0f} 元（样本 {int(count)}），"
                        f"整体均值 {overall_mean:.0f} 元；"
                        f"“{column}”因素的重要性为 {importance:.2f}。"
                    ),
                }
            )
    if not rows:
        raise ValueError("可分析的薪资因子不足，无法输出薪资因素分析")
    return pd.DataFrame(rows, columns=list(SALARY_FACTOR_COLUMNS))


def predict_salary(
    jobs: pd.DataFrame,
    test_size: float = 0.3,
    random_state: int = 42,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """随机森林薪资预测。

    使用技能/学历/经验/城市/公司等编码特征（不含薪资列）预测 salary_avg，
    划分独立测试集并报告 MAE 与 R²；返回带 predicted_salary 的岗位表。
    薪资有效样本不足时抛出明确错误。
    """
    validate_jobs(jobs)
    if "salary_avg" not in jobs.columns:
        raise ValueError("岗位表缺少字段: salary_avg，无法进行薪资预测")
    salary = pd.to_numeric(jobs["salary_avg"], errors="coerce")
    valid_count = int(salary.notna().sum())
    if valid_count < 6:
        raise ValueError(f"薪资有效样本过少（{valid_count} < 6），无法划分训练集和测试集")

    features = encode_job_features(jobs, include_salary=False)
    feature_columns = [column for column in features.columns if column != "job_id"]
    X = features[feature_columns].astype(float)
    mask = salary.notna().values
    X_train, X_test, y_train, y_test = train_test_split(
        X[mask], salary[mask], test_size=test_size, random_state=random_state
    )
    if len(y_test) < 2:
        raise ValueError("测试集样本过少，请提供更多数据")

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    model = RandomForestRegressor(n_estimators=100, random_state=random_state)
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    metrics = {
        "mae": round(float(mean_absolute_error(y_test, y_pred)), 2),
        "r2": round(float(r2_score(y_test, y_pred)), 4),
    }

    # 对全部岗位给出预测薪资（含薪资缺失行，方便页面展示参考值）
    predicted = model.predict(scaler.transform(X))
    result = jobs.copy()
    result["predicted_salary"] = np.round(predicted, 0)
    return result, metrics
