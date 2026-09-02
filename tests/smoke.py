from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.data.schema import JOB_COLUMNS, JobRecord, StudentProfile
from src.data.loader import load_jobs
from src.services.job_service import filter_jobs, summarize_jobs


def sample_jobs() -> pd.DataFrame:
    """构造符合《接口约定》第 2 节全部 21 列的样例岗位表。"""
    rows = [
        {
            "job_id": "1", "title": "数据分析实习生", "company": "示例公司",
            "company_intro": "数据服务", "company_size": "100-499人", "company_nature": "民营",
            "industry": "互联网", "city": "上海", "work_type": "实习", "experience": "在校生",
            "education": "本科", "skills": "Python;SQL;pandas", "description": "处理业务数据",
            "benefits": "弹性工作;下午茶", "salary_text": "3-5K", "salary_min": 3000,
            "salary_max": 5000, "salary_avg": 4000, "source": "BOSS直聘",
            "source_url": "https://example.com/job/1", "crawled_at": "2026-09-01T10:00:00+08:00",
        },
        {
            "job_id": "2", "title": "后端开发工程师", "company": "测试公司",
            "company_intro": "", "company_size": "1000-9999人", "company_nature": "国企",
            "industry": "金融", "city": "杭州", "work_type": "全职", "experience": "应届",
            "education": "硕士", "skills": "Python;Linux", "description": "开发服务接口",
            "benefits": "五险一金", "salary_text": "9-12K", "salary_min": 9000,
            "salary_max": 12000, "salary_avg": 10500, "source": "BOSS直聘",
            "source_url": "https://example.com/job/2", "crawled_at": "2026-09-01T11:00:00+08:00",
        },
    ]
    return pd.DataFrame(rows)[list(JOB_COLUMNS)]


def main() -> None:
    jobs = sample_jobs()
    assert tuple(jobs.columns) == JOB_COLUMNS

    # StudentProfile 按《接口约定》第 3 节字段解析。
    profile = StudentProfile.from_mapping({
        "target_role": "数据分析", "skills": "Python;SQL", "education": "本科",
        "major": "计算机", "school": "示例大学", "work_years": "1.5",
        "work_experience": "一段实习", "expected_salary_min": "8000",
    })
    assert profile.skills == ("Python", "SQL")
    assert profile.education == "本科"
    assert profile.major == "计算机"
    assert profile.school == "示例大学"
    assert profile.work_years == 1.5
    assert profile.work_experience == "一段实习"
    assert profile.expected_salary_min == 8000.0
    try:
        StudentProfile.from_mapping({"work_years": "abc"})
    except ValueError:
        pass
    else:
        raise AssertionError("work_years 无法转 float 时应报错")
    try:
        StudentProfile.from_mapping({"experience": "应届"})
    except ValueError as error:
        assert "work_experience" in str(error)
    else:
        raise AssertionError("旧字段 experience 应被明确拒绝")

    record = JobRecord(job_id="1", title="测试岗位", company="测试公司", skills="Python")
    assert record.to_dict()["skills"] == "Python"
    assert record.to_dict()["company"] == "测试公司"
    assert tuple(record.to_dict()) == JOB_COLUMNS

    # 回归测试：保留原有位置参数语义，第三个位置参数仍是 skills。
    positional = JobRecord("1", "测试岗位", "Python")
    assert positional.skills == "Python"
    assert positional.company == ""

    # load_jobs：文件缺失返回空表（仍带全部标准列）；空文件报错；缺必填字段报错。
    assert tuple(load_jobs("data/processed/not-found.csv").columns) == JOB_COLUMNS
    with TemporaryDirectory() as directory:
        csv_path = Path(directory) / "jobs.csv"
        csv_path.write_text(
            "job_id,title,company,skills,salary_min,salary_max,salary_avg,source,crawled_at\n"
            "3,测试岗位,示例公司,Python,1,2,1.5,BOSS直聘,2026-09-01T10:00:00+08:00\n",
            encoding="utf-8",
        )
        loaded = load_jobs(csv_path)
        assert tuple(loaded.columns) == JOB_COLUMNS
        assert loaded.iloc[0]["company"] == "示例公司"
        assert loaded.iloc[0]["source"] == "BOSS直聘"
        assert loaded.iloc[0]["crawled_at"] == "2026-09-01T10:00:00+08:00"

        missing_company_path = Path(directory) / "missing_company.csv"
        missing_company_path.write_text(
            "job_id,title,skills,salary_min,salary_max,salary_avg,source,crawled_at\n"
            "3,测试岗位,Python,1,2,1.5,BOSS直聘,2026-09-01T10:00:00+08:00\n",
            encoding="utf-8",
        )
        try:
            load_jobs(missing_company_path)
        except ValueError as error:
            assert "company" in str(error)
        else:
            raise AssertionError("缺少必填字段 company 时应报错")

        missing_source_path = Path(directory) / "missing_source.csv"
        missing_source_path.write_text(
            "job_id,title,company,skills,salary_min,salary_max,salary_avg,crawled_at\n"
            "4,测试岗位,示例公司,Python,1,2,1.5,2026-09-01T10:00:00+08:00\n",
            encoding="utf-8",
        )
        try:
            load_jobs(missing_source_path)
        except ValueError as error:
            assert "source" in str(error)
        else:
            raise AssertionError("缺少必填字段 source 时应报错")

        missing_crawled_path = Path(directory) / "missing_crawled_at.csv"
        missing_crawled_path.write_text(
            "job_id,title,company,skills,salary_min,salary_max,salary_avg,source\n"
            "5,测试岗位,示例公司,Python,1,2,1.5,BOSS直聘\n",
            encoding="utf-8",
        )
        try:
            load_jobs(missing_crawled_path)
        except ValueError as error:
            assert "crawled_at" in str(error)
        else:
            raise AssertionError("缺少必填字段 crawled_at 时应报错")

        empty_path = Path(directory) / "empty.csv"
        empty_path.touch()
        try:
            load_jobs(empty_path)
        except ValueError as error:
            assert "为空" in str(error)
        else:
            raise AssertionError("empty csv should fail clearly")

    # 筛选：新增的 education / industry / company_nature 均生效，且不修改输入。
    filtered = filter_jobs(jobs, {"city": "上海", "salary_max": 6000})
    assert filtered["job_id"].tolist() == ["1"]
    assert filter_jobs(jobs, {"education": "硕士"})["job_id"].tolist() == ["2"]
    assert filter_jobs(jobs, {"industry": "互联网"})["job_id"].tolist() == ["1"]
    assert filter_jobs(jobs, {"company_nature": "国企"})["job_id"].tolist() == ["2"]
    assert filter_jobs(jobs, {"keyword": "不存在"}).empty
    assert len(jobs) == 2  # 输入未被修改
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

