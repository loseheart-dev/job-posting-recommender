import pandas as pd


def filter_jobs(jobs: pd.DataFrame, filters: dict[str, object]) -> pd.DataFrame:
    """徐挚凌负责：统一封装岗位筛选，供页面调用。"""
    raise NotImplementedError("岗位筛选服务待徐挚凌实现")


def summarize_jobs(jobs: pd.DataFrame) -> dict[str, object]:
    """徐挚凌负责：统一封装岗位统计，供页面调用。"""
    raise NotImplementedError("岗位统计服务待徐挚凌实现")
