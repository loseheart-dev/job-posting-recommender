import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.data.boss_adapter import (
    import_upstream_result,
    load_upstream_records,
    map_boss_records,
    parse_salary,
)
from src.data.cleaner import clean_jobs_with_report
from src.data.schema import JOB_COLUMNS
from src.data.traversal import CrawlTask, VisitResult, build_search_tasks, traverse_tasks


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
    def test_json_csv_import_and_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_path = root / "jobs.json"
            json_path.write_text(json.dumps({"jobs": [upstream_job()]}), encoding="utf-8")
            self.assertEqual(len(load_upstream_records(json_path)), 1)
            details = [{"job_id": "job-1", "jd": "岗位描述"}]
            mapped = map_boss_records(
                load_upstream_records(json_path), details, crawled_at="2026-01-01T00:00:00Z"
            )
            self.assertEqual(tuple(mapped[0]), JOB_COLUMNS)
            self.assertEqual(mapped[0]["city"], "上海")
            self.assertEqual(mapped[0]["skills"], "Python;SQL")
            self.assertEqual(mapped[0]["salary_avg"], 12500)
            self.assertEqual(mapped[0]["description"], "岗位描述")

            csv_path = root / "jobs.csv"
            pd.DataFrame([upstream_job()]).to_csv(csv_path, index=False)
            self.assertEqual(len(load_upstream_records(csv_path)), 1)
            record, _ = import_upstream_result(
                json_path,
                root / "raw",
                root / "tasks.jsonl",
                keyword="大数据",
                city="上海",
                task_id="task-1",
            )
            self.assertEqual(record.status, "success")
            self.assertEqual(record.raw_count, 1)
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
        self.assertEqual(parse_salary("500-550元/天"), (10875.0, 11962.5, 11418.75))
        self.assertEqual(parse_salary("面议"), (None, None, None))
        roots = build_search_tasks(["大数据"], ["上海"], pages=2)

        def visit(task: CrawlTask) -> VisitResult:
            if task.page == 1 and task.depth == 0:
                child = CrawlTask(task.task_id + "-detail", task.keyword, task.city, task.page, 1, "detail")
                return VisitResult(task.page, (child,))
            return VisitResult(task.page)

        bfs = traverse_tasks(roots, "bfs", visit, max_depth=1)
        dfs = traverse_tasks(roots, "dfs", visit, max_depth=1)
        self.assertEqual([item.depth for item in bfs], [0, 0, 1])
        self.assertEqual([item.depth for item in dfs], [0, 1, 0])
        failed = traverse_tasks(
            roots[:1],
            "bfs",
            lambda task: (_ for _ in ()).throw(ValueError("bad task")),
        )
        self.assertEqual(failed[0].status, "failed")
        self.assertIn("bad task", failed[0].error_message)


if __name__ == "__main__":
    unittest.main()
