import pandas as pd


def cluster_jobs(jobs: pd.DataFrame, n_clusters: int = 3) -> tuple[pd.DataFrame, dict[int, dict[str, object]]]:
    """输出带 cluster_id 的岗位表和按群组整理的特征说明。"""
    raise NotImplementedError("KMeans 聚类模块待卢世豪实现")
