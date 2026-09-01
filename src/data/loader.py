from pathlib import Path

import pandas as pd


def load_jobs(path: str | Path) -> pd.DataFrame:
    """Load cleaned job data; return an empty frame when the file is absent."""
    data_path = Path(path)
    if not data_path.exists():
        return pd.DataFrame()
    if data_path.suffix.lower() != ".csv":
        raise ValueError("当前基础版本只支持 CSV 岗位数据")
    return pd.read_csv(data_path)
