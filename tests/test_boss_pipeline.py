import json
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import scripts.run_boss_tasks as boss_runner
from src.data.boss_adapter import (
    detect_salary_unit,
    import_upstream_result,
    load_upstream_records,
    map_boss_records,
    parse_salary,
)
from src.data.cleaner import clean_jobs_with_report, write_clean_jobs
from src.data.loader import load_jobs
from src.data.schema import JOB_COLUMNS
from src.data.traversal import (
    CrawlTask,
    TraversalRecord,
    VisitResult,
    build_search_tasks,
    traverse_tasks,
)


def upstream_job(job_id: str = "job-1") -> dict[str, object]:
    return {
        "job_id": job_id,
        "title": "数据分析师",
        "boss_name": "示例科技",
        "company_scale": "100-499人",
        "company_industry": "互联网",
        "location": "上海·浦东新区·陆家嘴",
        "tags": "1-3年 | 本科",
        "skills": "Python | SQL | Python",
        "welfare": "五险一金 | 餐补",
        "salary": "10-15K",
        "job_link": "https://www.zhipin.com/job_detail/job-1.html",
    }


class BossPipelineTests(unittest.TestCase):
    def test_range_fixture_contract(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "jobs_range_sample.csv"
        jobs = load_jobs(fixture_path)
        self.assertEqual(len(jobs), 32)
        self.assertEqual(tuple(jobs.columns), JOB_COLUMNS)
        self.assertEqual(set(jobs["city"].dropna()), {"上海", "杭州"})
        self.assertEqual(jobs["job_id"].nunique(), 32)

    def test_json_csv_import_and_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture_dir = Path(__file__).parent / "fixtures"
            json_path = fixture_dir / "boss_sample.json"
            details = json.loads((fixture_dir / "boss_details_sample.json").read_text(encoding="utf-8"))
            records = load_upstream_records(json_path)
            self.assertEqual(len(records), 4)
            mapped = map_boss_records(
                records, details, crawled_at="2026-01-01T00:00:00Z"
            )
            self.assertEqual(tuple(mapped[0]), JOB_COLUMNS)
            self.assertEqual(mapped[0]["job_id"], "b61d9ca3dcd4ffde")
            self.assertEqual(mapped[0]["city"], "上海")
            self.assertEqual(mapped[0]["skills"], "Python;SQL;pandas")
            self.assertEqual(mapped[0]["salary_avg"], 18000)
            self.assertIn("3c3cddc8b3b3f20b0nJ92dq0GFVX", mapped[0]["source_url"])
            self.assertIn("数据整理", mapped[0]["description"])
            cleaned, report = clean_jobs_with_report(pd.DataFrame(mapped))
            self.assertEqual(report["output_count"], 4)
            self.assertTrue(pd.isna(cleaned.loc[2, "salary_avg"]))
            self.assertEqual(report["salary_unit_counts"]["day"], 1)
            self.assertEqual(report["non_monthly_salary_excluded"], 1)
            output_path = root / "processed" / "jobs.csv"
            written, written_report = write_clean_jobs(pd.DataFrame(mapped), output_path)
            self.assertEqual(len(written), 4)
            self.assertEqual(written_report["output_count"], 4)
            self.assertTrue(output_path.exists())

            csv_path = root / "jobs.csv"
            pd.DataFrame(records).to_csv(csv_path, index=False)
            self.assertEqual(len(load_upstream_records(csv_path)), 4)
            record, _ = import_upstream_result(
                json_path,
                root / "raw",
                root / "tasks.jsonl",
                keyword="大数据",
                city="上海",
                task_id="task-1",
            )
            self.assertEqual(record.status, "success")
            self.assertEqual(record.raw_count, 4)
            self.assertTrue(Path(record.raw_path).exists())
            self.assertIn('"task_id": "task-1"', (root / "tasks.jsonl").read_text(encoding="utf-8"))

    def test_empty_and_malformed_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            empty = root / "empty.json"
            empty.touch()
            with self.assertRaisesRegex(ValueError, "为空"):
                load_upstream_records(empty)
            malformed = root / "bad.json"
            malformed.write_text("{bad", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "格式错误"):
                load_upstream_records(malformed)
            empty_json = root / "empty_list.json"
            empty_json.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "没有岗位记录"):
                load_upstream_records(empty_json)
            header_only = root / "header_only.csv"
            header_only.write_text("job_id,title\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "没有岗位记录"):
                load_upstream_records(header_only)
            extra_column = root / "extra_column.csv"
            extra_column.write_text("job_id,title\n1,岗位,extra\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "字段过多"):
                load_upstream_records(extra_column)
            missing_column = root / "missing_column.csv"
            missing_column.write_text("job_id,title,city\n1,岗位\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "字段缺失"):
                load_upstream_records(missing_column)
            malformed_csv = root / "malformed.csv"
            malformed_csv.write_text('job_id,title\n1,"岗位\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "格式错误"):
                load_upstream_records(malformed_csv)

    def test_missing_fields_duplicate_and_invalid_salary(self) -> None:
        mapped = map_boss_records([
            {**upstream_job("job-1"), "salary": "面议", "company": ""},
            {**upstream_job("job-1"), "salary": "面议"},
            {"job_id": "job-2", "title": "缺字段岗位", "salary": ""},
        ])
        cleaned, report = clean_jobs_with_report(pd.DataFrame(mapped))
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(report["duplicate_count"], 1)
        self.assertEqual(report["invalid_salary_count"], 1)
        self.assertEqual(report["missing_counts"]["company"], 1)
        self.assertTrue(pd.isna(cleaned.loc[0, "salary_avg"]))

    def test_salary_parser_and_traversal(self) -> None:
        self.assertEqual(detect_salary_unit("20-30K"), "month")
        self.assertEqual(detect_salary_unit("500-550元/天"), "day")
        self.assertEqual(detect_salary_unit("5-20元/时"), "hour")
        self.assertEqual(detect_salary_unit("500-1000元/周"), "week")
        self.assertEqual(detect_salary_unit("20-30万/年"), "year")
        self.assertEqual(detect_salary_unit("面议"), "negotiable")

        self.assertEqual(parse_salary("20-30K"), (20000.0, 30000.0, 25000.0))
        self.assertEqual(parse_salary("1.5-2万"), (15000.0, 20000.0, 17500.0))
        self.assertEqual(parse_salary("20K·13薪"), (20000.0, 20000.0, 20000.0))
        self.assertEqual(parse_salary("100-200K·15薪"), (100000.0, 200000.0, 150000.0))
        self.assertEqual(parse_salary("5000-8000元/月"), (5000.0, 8000.0, 6500.0))
        self.assertEqual(parse_salary("500-550元/天"), (None, None, None))
        self.assertEqual(parse_salary("5-20元/时"), (None, None, None))
        self.assertEqual(parse_salary("500-1000元/周"), (None, None, None))
        self.assertEqual(parse_salary("20-30万/年"), (None, None, None))
        self.assertEqual(parse_salary("面议"), (None, None, None))

    def test_skill_filter_and_explicit_salary_repair(self) -> None:
        raw = upstream_job("hourly")
        raw.update(
            skills="Python | 要求数据开发经验 | 非外包类 | 不接受居家办公 | 计算机相关专业",
            salary="5-20元/时",
        )
        mapped = map_boss_records([raw])
        self.assertEqual(mapped[0]["skills"], "Python")

        # 旧映射结果可能已经把非月薪写入数值列，清洗时必须清除。
        mapped[0]["salary_min"] = 5.0
        mapped[0]["salary_max"] = 20.0
        mapped[0]["salary_avg"] = 12.5
        cleaned, report = clean_jobs_with_report(pd.DataFrame(mapped))
        self.assertTrue(pd.isna(cleaned.loc[0, "salary_min"]))
        self.assertTrue(pd.isna(cleaned.loc[0, "salary_max"]))
        self.assertTrue(pd.isna(cleaned.loc[0, "salary_avg"]))
        self.assertEqual(report["legacy_salary_values_cleared"], 1)

        mapped[0]["salary_text"] = "4900-5000元/时"
        mapped[0]["salary_min"] = 852600.0
        mapped[0]["salary_max"] = 870000.0
        mapped[0]["salary_avg"] = 861300.0
        cleaned, report = clean_jobs_with_report(pd.DataFrame(mapped))
        self.assertTrue(pd.isna(cleaned.loc[0, "salary_avg"]))
        self.assertEqual(report["legacy_salary_values_cleared"], 1)
        search_tasks = build_search_tasks(["大数据"], ["上海"], pages=2)
        self.assertEqual(len(search_tasks), 1)
        self.assertEqual(search_tasks[0].page, 2)
        roots = [
            CrawlTask("root-1", "大数据", "上海", page=1),
            CrawlTask("root-2", "大数据", "上海", page=2),
        ]

        def visit(task: CrawlTask) -> VisitResult:
            if task.page == 1 and task.depth == 0:
                child = CrawlTask(task.task_id + "-detail", task.keyword, task.city, task.page, 1, "detail")
                return VisitResult(task.page, (child,))
            return VisitResult(task.page)

        bfs = traverse_tasks(roots, "bfs", visit, max_depth=1)
        dfs = traverse_tasks(roots, "dfs", visit, max_depth=1)
        self.assertEqual([item.depth for item in bfs], [0, 0, 1])
        self.assertEqual([item.depth for item in dfs], [0, 1, 0])
        with tempfile.TemporaryDirectory() as directory:
            traversal_log = Path(directory) / "traversal_records.jsonl"
            logged = traverse_tasks(roots, "bfs", visit, max_depth=1, record_path=traversal_log)
            self.assertEqual(len(logged), 3)
            self.assertEqual(len(traversal_log.read_text(encoding="utf-8").splitlines()), 3)
        failed = traverse_tasks(
            roots[:1],
            "bfs",
            lambda task: (_ for _ in ()).throw(ValueError("bad task")),
        )
        self.assertEqual(failed[0].status, "failed")
        self.assertIn("bad task", failed[0].error_message)

    def test_runner_page_argument_and_failure_exit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream_script = root / "scripts" / "boss_cdp_raw.py"
            upstream_script.parent.mkdir()
            upstream_script.write_text("", encoding="utf-8")
            args = SimpleNamespace(
                upstream_repo=root,
                output_dir=root / "output",
                no_detail=True,
                python="python",
                cdp_port=9222,
                max_details=5,
            )
            with patch.object(
                boss_runner.subprocess, "run", return_value=SimpleNamespace(returncode=0)
            ) as run, patch.object(
                boss_runner, "load_upstream_records", return_value=[{"job_id": "1"}]
            ):
                result = boss_runner.collect_task(CrawlTask("task-1", "大数据", "上海", page=2), args)
            self.assertEqual(result.result_count, 1)
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--pages") + 1], "2")

        failed = TraversalRecord("task-1", "大数据", "上海", 1, 0, "bfs", "failed", 0, "bad")
        runner_args = SimpleNamespace(
            keywords=["大数据"],
            cities=["上海"],
            pages=1,
            strategy="bfs",
            max_details=5,
            no_detail=True,
            traversal_log=Path("/tmp/boss-runner-test.jsonl"),
        )
        with patch.object(boss_runner, "parse_args", return_value=runner_args), patch.object(
            boss_runner, "build_search_tasks", return_value=[]
        ), patch.object(boss_runner, "traverse_tasks", return_value=[failed]):
            with self.assertRaises(SystemExit) as error:
                boss_runner.main()
        self.assertEqual(error.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
