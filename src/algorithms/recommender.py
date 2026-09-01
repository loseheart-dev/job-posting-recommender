import pandas as pd

from src.data.schema import StudentProfile


def recommend_jobs(profile: StudentProfile | dict[str, object], jobs: pd.DataFrame, top_k: int = 5) -> pd.DataFrame:
    """丁伟哲负责：输出 Top-K 岗位、匹配技能和缺失技能。"""
    raise NotImplementedError("TF-IDF 推荐模块待丁伟哲实现")
