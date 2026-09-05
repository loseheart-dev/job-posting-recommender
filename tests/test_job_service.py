import pandas as pd
import pytest

from src.data.schema import JOB_COLUMNS, JobRecord
from src.services.job_service import education_distribution, paginate_jobs


def _jobs() -> pd.DataFrame:
    rows = [
        JobRecord("1", "数据分析师", "Python;SQL", education="本科", salary_avg=15000).to_dict(),
        JobRecord("2", "后端工程师", "Python;Java", education="本科", salary_avg=12000).to_dict(),
        JobRecord("3", "算法工程师", "Python;机器学习", education="硕士", salary_avg=18000).to_dict(),
    ]
    return pd.DataFrame(rows)[list(JOB_COLUMNS)]


def test_education_distribution_returns_ranked_contract() -> None:
    assert education_distribution(_jobs()) == [
        {"education": "本科", "count": 2},
        {"education": "硕士", "count": 1},
    ]


def test_education_distribution_handles_empty_values_and_empty_data() -> None:
    jobs = _jobs()
    jobs.loc[0, "education"] = ""
    assert education_distribution(jobs, top_k=2)[0] == {"education": "不限", "count": 1}
    assert education_distribution(pd.DataFrame(columns=JOB_COLUMNS)) == []


def test_paginate_jobs_returns_items_and_consistent_metadata() -> None:
    result = paginate_jobs(_jobs(), page=2, page_size=2)
    assert result["total"] == 3
    assert result["page"] == 2
    assert result["page_size"] == 2
    assert result["total_pages"] == 2
    assert result["items"]["job_id"].tolist() == ["3"]


def test_paginate_jobs_clamps_after_filter_result_shrinks() -> None:
    result = paginate_jobs(_jobs(), page=99, page_size=2)
    assert result["page"] == 2
    assert result["items"]["job_id"].tolist() == ["3"]
    empty = paginate_jobs(pd.DataFrame(columns=JOB_COLUMNS), page=9, page_size=2)
    assert empty["page"] == 1
    assert empty["total_pages"] == 0
    assert empty["items"].empty


@pytest.mark.parametrize(
    ("function", "kwargs"),
    [
        (education_distribution, {"top_k": 0}),
        (paginate_jobs, {"page": 0}),
        (paginate_jobs, {"page_size": 0}),
    ],
)
def test_new_service_interfaces_reject_invalid_paging_arguments(function, kwargs) -> None:
    with pytest.raises(ValueError):
        function(_jobs(), **kwargs)
