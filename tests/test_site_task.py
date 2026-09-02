import unittest
from datetime import datetime

from src.services.site_service import (
    CRAWL_STRATEGIES,
    FREQUENCIES,
    add_site,
    ensure_default_site,
    get_site,
    list_sites,
    remove_site,
    reset_sites,
    set_site_enabled,
    update_site,
)
from src.services.task_service import (
    compute_next_run,
    get_task,
    list_tasks,
    reset_tasks,
    trigger_task,
    update_task,
)


def sample_site_values() -> dict:
    return {
        "site_id": "boss_zhipin",
        "site_name": "BOSS直聘",
        "base_url": "https://www.zhipin.com",
        "keywords": ["大数据", "数据分析"],
        "cities": ["北京", "上海"],
        "crawl_strategy": "bfs",
        "start_at": "2026-09-02T09:00:00",
        "frequency": "daily",
        "max_depth": 2,
    }


class SiteServiceTest(unittest.TestCase):
    def setUp(self):
        reset_sites()
        reset_tasks()

    def test_add_and_query_site(self):
        site = add_site(sample_site_values())
        self.assertEqual(site.site_id, "boss_zhipin")
        self.assertTrue(site.enabled)
        self.assertEqual(site.keywords, ("大数据", "数据分析"))
        self.assertEqual(site.cities, ("北京", "上海"))
        self.assertEqual(len(list_sites()), 1)
        self.assertIs(get_site("boss_zhipin"), site)

    def test_update_and_toggle_site(self):
        add_site(sample_site_values())
        updated = update_site("boss_zhipin", {"frequency": "twice_daily", "max_depth": 3})
        self.assertEqual(updated.frequency, "twice_daily")
        self.assertEqual(updated.max_depth, 3)
        self.assertFalse(set_site_enabled("boss_zhipin", False).enabled)
        self.assertTrue(set_site_enabled("boss_zhipin", True).enabled)

    def test_add_site_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            add_site({"site_id": ""})
        add_site(sample_site_values())
        with self.assertRaises(ValueError):
            add_site(sample_site_values())  # 重复 site_id
        with self.assertRaises(ValueError):
            add_site({"site_id": "x", "crawl_strategy": "bad"})
        with self.assertRaises(ValueError):
            add_site({"site_id": "x", "frequency": "hourly"})
        with self.assertRaises(ValueError):
            add_site({"site_id": "x", "max_depth": -1})

    def test_get_unknown_site_raises(self):
        with self.assertRaises(KeyError):
            get_site("not-exists")

    def test_remove_site(self):
        add_site(sample_site_values())
        self.assertEqual(remove_site("boss_zhipin").site_id, "boss_zhipin")
        with self.assertRaises(KeyError):
            get_site("boss_zhipin")

    def test_ensure_default_site(self):
        default = ensure_default_site()
        self.assertEqual(default.site_id, "boss_zhipin")
        self.assertEqual(default.site_name, "BOSS直聘")
        self.assertIn(default.crawl_strategy, CRAWL_STRATEGIES)
        self.assertIn(default.frequency, FREQUENCIES)


class TaskServiceTest(unittest.TestCase):
    def setUp(self):
        reset_sites()
        reset_tasks()
        add_site(sample_site_values())

    def test_trigger_and_update_task(self):
        task = trigger_task("boss_zhipin")
        self.assertEqual(task.status, "pending")
        self.assertEqual(task.site_id, "boss_zhipin")
        self.assertIs(get_task(task.task_id), task)
        self.assertEqual(update_task(task.task_id, {"status": "running"}).status, "running")
        done = update_task(task.task_id, {
            "status": "success", "raw_count": 100, "parsed_count": 95,
            "error_count": 5, "finished_at": "2026-09-02T09:30:00",
        })
        self.assertEqual(done.status, "success")
        self.assertEqual(done.raw_count, 100)
        self.assertEqual(done.parsed_count, 95)
        self.assertEqual(done.error_count, 5)
        self.assertEqual(len(list_tasks("boss_zhipin")), 1)

    def test_trigger_unknown_or_disabled_site(self):
        with self.assertRaises(KeyError):
            trigger_task("not-exists")
        set_site_enabled("boss_zhipin", False)
        with self.assertRaises(ValueError):
            trigger_task("boss_zhipin")

    def test_update_task_validations(self):
        task = trigger_task("boss_zhipin")
        with self.assertRaises(ValueError):
            update_task(task.task_id, {"status": "weird"})
        with self.assertRaises(KeyError):
            get_task("missing")


class NextRunTest(unittest.TestCase):
    def setUp(self):
        reset_sites()
        reset_tasks()

    def test_twice_daily(self):
        site = add_site({
            "site_id": "boss_zhipin", "site_name": "BOSS直聘",
            "frequency": "twice_daily", "start_at": "2026-09-02T09:00:00",
        })
        self.assertEqual(compute_next_run(site, datetime(2026, 9, 2, 10, 0)), datetime(2026, 9, 2, 21, 0))
        self.assertEqual(compute_next_run(site, datetime(2026, 9, 2, 22, 0)), datetime(2026, 9, 3, 9, 0))

    def test_daily(self):
        site = add_site({
            "site_id": "daily_site", "site_name": "每日站",
            "frequency": "daily", "start_at": "2026-09-02T08:30:00",
        })
        self.assertEqual(compute_next_run(site, datetime(2026, 9, 2, 8, 0)), datetime(2026, 9, 2, 8, 30))
        self.assertEqual(compute_next_run(site, datetime(2026, 9, 2, 9, 0)), datetime(2026, 9, 3, 8, 30))

    def test_once_returns_none(self):
        site = add_site({
            "site_id": "once_site", "site_name": "手动站",
            "frequency": "once", "start_at": "2026-09-02T09:00:00",
        })
        self.assertIsNone(compute_next_run(site, datetime(2026, 9, 2, 8, 0)))


if __name__ == "__main__":
    unittest.main()
