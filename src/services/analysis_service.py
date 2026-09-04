"""分析与推荐调用适配服务（徐挚凌）。

把郑维豪的三类分析/KMeans/随机森林与丁伟哲的推荐封装为页面可统一调用的服务函数，
保证页面不直接读取原始数据、不重复写模型逻辑。算法输出结构与《docs/接口约定.md》
第 6 节一致。

空数据契约：
- 分析类函数（salary_factor_analysis / salary_prediction / job_cluster / skill_graph /
  company_profile）：空表时抛出明确中文 ValueError（空表前置检查 + 算法自身校验透传）；
- 推荐类函数（recommend_jobs / recommend_jobs_multifactor）：遵循丁伟哲推荐冻结契约，
  岗位表为空或画像无内容时返回空结果表（不抛错），页面按"无推荐结果"处理。

页面统一调用方式：先用 ``load_jobs`` / ``filter_jobs`` 得到标准岗位表，再调用本模块函数。
"""
import pandas as pd

from src.algorithms import clustering as _clustering
from src.algorithms import company_profile as _company_profile
from src.algorithms import recommender as _recommender
from src.algorithms import salary as _salary
from src.algorithms import skill_graph as _skill_graph
from src.data.schema import StudentProfile

__all__ = [
    "salary_factor_analysis",
    "salary_prediction",
    "job_cluster",
    "skill_graph",
    "company_profile",
    "recommend_jobs",
    "recommend_jobs_multifactor",
]


def _require_data(jobs: pd.DataFrame, action: str) -> None:
    if not isinstance(jobs, pd.DataFrame) or jobs.empty:
        raise ValueError(f"岗位数据为空，无法进行{action}（请先确认筛选结果非空）")


def _as_profile(profile: StudentProfile | dict[str, object]) -> StudentProfile:
    if isinstance(profile, dict):
        return StudentProfile.from_mapping(profile)
    return profile


def salary_factor_analysis(jobs: pd.DataFrame) -> pd.DataFrame:
    """薪资影响因素分析（郑维豪）。返回 ``SALARY_FACTOR_COLUMNS`` 标准列。"""
    _require_data(jobs, "薪资因素分析")
    return _salary.analyze_salary_factors(jobs)


def salary_prediction(jobs: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    """随机森林薪资预测（郑维豪）。

    返回 ``(带 predicted_salary 的岗位表, {mae, r2})``；模型为即时训练，
    薪资有效样本过少时抛出明确错误。
    """
    _require_data(jobs, "薪资预测")
    return _salary.predict_salary(jobs)


def job_cluster(jobs: pd.DataFrame, n_clusters: int = 3) -> tuple[pd.DataFrame, dict[int, dict[str, object]]]:
    """KMeans 岗位聚类（郑维豪）。返回 ``(带 cluster_id 的岗位表, 群组说明 dict)``。"""
    _require_data(jobs, "岗位聚类")
    return _clustering.cluster_jobs(jobs, n_clusters=n_clusters)


def skill_graph(jobs: pd.DataFrame) -> dict[str, object]:
    """岗位能力需求图谱（郑维豪）。返回 ``{nodes, edges, skill_frequency}``。"""
    _require_data(jobs, "能力需求图谱分析")
    return _skill_graph.build_skill_graph(jobs)


def company_profile(jobs: pd.DataFrame) -> pd.DataFrame:
    """招聘企业画像（郑维豪）。返回 ``COMPANY_PROFILE_COLUMNS`` 标准列。"""
    _require_data(jobs, "企业画像分析")
    return _company_profile.build_company_profiles(jobs)


def recommend_jobs(
    profile: StudentProfile | dict[str, object],
    jobs: pd.DataFrame,
    top_k: int = 5,
) -> pd.DataFrame:
    """TF-IDF 岗位推荐（丁伟哲）。返回 ``RECOMMENDATION_COLUMNS`` 标准列。

    岗位表为空或画像无内容时返回空结果表（遵循丁伟哲推荐冻结契约，不抛错）。
    """
    return _recommender.recommend_jobs(_as_profile(profile), jobs, top_k=top_k)


def recommend_jobs_multifactor(
    profile: StudentProfile | dict[str, object],
    jobs: pd.DataFrame,
    top_k: int = 5,
) -> pd.DataFrame:
    """多因素岗位推荐（丁伟哲，页面主用）。返回 ``MULTI_FACTOR_RECOMMENDATION_COLUMNS`` 标准列。

    岗位表为空或画像无内容时返回空结果表（遵循丁伟哲推荐冻结契约，不抛错）。
    """
    return _recommender.recommend_jobs_multifactor(_as_profile(profile), jobs, top_k=top_k)

