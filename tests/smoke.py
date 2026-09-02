from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.data.schema import JOB_COLUMNS, JobRecord, StudentProfile
from src.data.loader import load_jobs
from src.services.job_service import filter_jobs, summarize_jobs


def sample_jobs() -> pd.DataFrame:
    return pd.DataFrame([
        JobRecord(
            "1", "数据分析实习生", "Python;SQL;pandas", company="示例公司", city="上海",
            work_type="实习", experience="在校生", education="本科", description="处理业务数据",
            salary_min=3000, salary_max=5000, salary_avg=4000, source="test",
            crawled_at="2026-01-01T00:00:00Z",
        ).to_dict(),
        JobRecord(
            "2", "后端开发工程师", "Python;Linux", company="测试公司", city="杭州",
            work_type="全职", experience="应届", education="本科", description="开发服务接口",
            salary_min=9000, salary_max=12000, salary_avg=10500, source="test",
            crawled_at="2026-01-01T00:00:00Z",
        ).to_dict(),
    ])


def main() -> None:
    jobs = sample_jobs()
    assert tuple(jobs.columns) == JOB_COLUMNS
    profile = StudentProfile.from_mapping({"target_role": "数据分析", "skills": "Python;SQL"})
    assert profile.skills == ("Python", "SQL")
    assert JobRecord("1", "测试岗位", "Python").to_dict()["skills"] == "Python"
    assert tuple(load_jobs("data/processed/not-found.csv").columns) == JOB_COLUMNS
    with TemporaryDirectory() as directory:
        csv_path = Path(directory) / "jobs.csv"
        pd.DataFrame([
            JobRecord(
                "3", "测试岗位", "Python", company="测试公司", source="test",
                crawled_at="2026-01-01T00:00:00Z",
            ).to_dict()
        ]).to_csv(csv_path, index=False)
        assert tuple(load_jobs(csv_path).columns) == JOB_COLUMNS
        empty_path = Path(directory) / "empty.csv"
        empty_path.touch()
        try:
            load_jobs(empty_path)
        except ValueError as error:
            assert "为空" in str(error)
        else:
            raise AssertionError("empty csv should fail clearly")
    filtered = filter_jobs(jobs, {"city": "上海", "salary_max": 6000})
    assert filtered["job_id"].tolist() == ["1"]
    assert filter_jobs(jobs, {"keyword": "不存在"}).empty
    try:
        filter_jobs(jobs, {"unknown": "value"})
    except ValueError:
        pass
    else:
        raise AssertionError("unknown filter should fail clearly")
    summary = summarize_jobs(jobs)
    assert summary["job_count"] == 2
    assert summary["top_skills"][0] == ("Python", 2)
    print("service contract smoke test passed")


if __name__ == "__main__":
    main()
