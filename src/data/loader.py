from pathlib import Path

import pandas as pd

from src.data.schema import JOB_COLUMNS, REQUIRED_JOB_COLUMNS


def load_jobs(path: str | Path) -> pd.DataFrame:
    """Load cleaned job data; return an empty frame when the file is absent."""
    data_path = Path(path)
    if not data_path.exists():
        return pd.DataFrame(columns=JOB_COLUMNS)
    if data_path.suffix.lower() != ".csv":
        raise ValueError("当前基础版本只支持 CSV 岗位数据")
    try:
        jobs = pd.read_csv(data_path)
    except pd.errors.EmptyDataError as error:
        raise ValueError("岗位数据文件为空") from error
    missing = [column for column in REQUIRED_JOB_COLUMNS if column not in jobs.columns]
    if missing:
        raise ValueError(f"岗位数据缺少必要字段: {', '.join(missing)}")
    for column in JOB_COLUMNS:
        if column not in jobs.columns:
            jobs[column] = pd.NA
    return jobs.loc[:, JOB_COLUMNS]
