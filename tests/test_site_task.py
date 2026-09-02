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
    TASK_STATUSES,
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


def main() -> None:
    reset_sites()
    reset_tasks()

    # --- 网站配置：正常案例 ---
    site = add_site(sample_site_values())
    assert site.site_id == "boss_zhipin"
    assert site.enabled is True
    assert site.keywords == ("大数据", "数据分析")
    assert site.cities == ("北京", "上海")
    assert len(list_sites()) == 1
    assert get_site("boss_zhipin") is site

    updated = update_site("boss_zhipin", {"frequency": "twice_daily", "max_depth": 3})
    assert updated.frequency == "twice_daily"
    assert updated.max_depth == 3
    assert set_site_enabled("boss_zhipin", False).enabled is False
    set_site_enabled("boss_zhipin", True)

    # --- 网站配置：异常案例 ---
    try:
        add_site({"site_id": ""})
    except ValueError:
        pass
    else:
        raise AssertionError("site_id 为空应报错")
    try:
        add_site(sample_site_values())  # 重复 site_id
    except ValueError:
        pass
    else:
        raise AssertionError("重复 site_id 应报错")
    try:
        add_site({"site_id": "x", "crawl_strategy": "bad"})
    except ValueError as error:
        assert "crawl_strategy" in str(error)
    else:
        raise AssertionError("非法 crawl_strategy 应报错")
    try:
        add_site({"site_id": "x", "frequency": "hourly"})
    except ValueError as error:
        assert "frequency" in str(error)
    else:
        raise AssertionError("非法 frequency 应报错")
    try:
        add_site({"site_id": "x", "max_depth": -1})
    except ValueError:
        pass
    else:
        raise AssertionError("负数 max_depth 应报错")
    try:
        get_site("not-exists")
    except KeyError:
        pass
    else:
        raise AssertionError("未知 site_id 应报 KeyError")

    # --- 任务：正常案例 ---
    task = trigger_task("boss_zhipin")
    assert task.status == "pending"
    assert task.site_id == "boss_zhipin"
    assert get_task(task.task_id) is task
    assert update_task(task.task_id, {"status": "running"}).status == "running"
    done = update_task(task.task_id, {
        "status": "success", "raw_count": 100, "parsed_count": 95,
        "error_count": 5, "finished_at": "2026-09-02T09:30:00",
    })
    assert done.status == "success"
    assert done.raw_count == 100
    assert done.parsed_count == 95
    assert done.error_count == 5
    assert len(list_tasks("boss_zhipin")) == 1

    # --- 任务：异常案例 ---
    try:
        trigger_task("not-exists")
    except KeyError:
        pass
    else:
        raise AssertionError("触发未知网站应报 KeyError")
    set_site_enabled("boss_zhipin", False)
    try:
        trigger_task("boss_zhipin")
    except ValueError:
        pass
    else:
        raise AssertionError("触发停用网站应报错")
    set_site_enabled("boss_zhipin", True)
    try:
        update_task(task.task_id, {"status": "weird"})
    except ValueError as error:
        assert "status" in str(error)
    else:
        raise AssertionError("非法 status 应报错")
    try:
        get_task("missing")
    except KeyError:
        pass
    else:
        raise AssertionError("未知 task_id 应报 KeyError")

    # --- compute_next_run 纯计算 ---
    site = get_site("boss_zhipin")  # frequency=twice_daily, start_at=2026-09-02T09:00:00
    assert compute_next_run(site, datetime(2026, 9, 2, 10, 0)) == datetime(2026, 9, 2, 21, 0)
    assert compute_next_run(site, datetime(2026, 9, 2, 22, 0)) == datetime(2026, 9, 3, 9, 0)

    daily_site = add_site({
        "site_id": "daily_site", "site_name": "每日站",
        "frequency": "daily", "start_at": "2026-09-02T08:30:00",
    })
    assert compute_next_run(daily_site, datetime(2026, 9, 2, 8, 0)) == datetime(2026, 9, 2, 8, 30)
    assert compute_next_run(daily_site, datetime(2026, 9, 2, 9, 0)) == datetime(2026, 9, 3, 8, 30)

    once_site = add_site({
        "site_id": "once_site", "site_name": "手动站",
        "frequency": "once", "start_at": "2026-09-02T09:00:00",
    })
    assert compute_next_run(once_site, datetime(2026, 9, 2, 8, 0)) is None

    # --- 删除 ---
    assert remove_site("once_site").site_id == "once_site"
    try:
        get_site("once_site")
    except KeyError:
        pass
    else:
        raise AssertionError("删除后仍能读到应报 KeyError")

    # --- 默认站点 ---
    reset_sites()
    default = ensure_default_site()
    assert default.site_id == "boss_zhipin"
    assert default.site_name == "BOSS直聘"
    assert default.crawl_strategy in CRAWL_STRATEGIES
    assert default.frequency in FREQUENCIES
    assert "pending" in TASK_STATUSES

    print("site/task service smoke test passed")


if __name__ == "__main__":
    main()
