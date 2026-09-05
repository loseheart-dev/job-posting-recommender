# -*- coding: utf-8 -*-
"""Z7：页面集中联调验证 —— Streamlit AppTest 遍历五个模块（可复现脚本）。

用法：``python -m tests.verify_app_integration``

说明：会临时把已入库的 ``tests/fixtures/expanded_jobs.csv`` 前 300 行放入
``data/processed/jobs.csv``（该路径被 gitignore、不随仓库提交），用 Streamlit
AppTest 依次渲染 app.py 的五个页面模块，并执行岗位筛选、推荐提交、采集任务
触发等真实交互；无论结果如何都会恢复原先 jobs.csv 的内容和修改时间。
页面服务调用契约见 ``docs/25051430/服务层调用说明.md``。
"""
import os
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.services import task_service

ROOT = Path(__file__).resolve().parents[1]
JOBS_PATH = ROOT / "data" / "processed" / "jobs.csv"
APP_PATH = ROOT / "app.py"
FIXTURE = ROOT / "tests" / "fixtures" / "expanded_jobs.csv"
SLICE = 300
MODULES = ["市场概览", "岗位检索", "分析洞察", "个性化推荐", "采集管理"]


def main() -> None:
    original = JOBS_PATH.read_bytes() if JOBS_PATH.exists() else None
    original_stat = JOBS_PATH.stat() if JOBS_PATH.exists() else None
    try:
        full = pd.read_csv(FIXTURE)
        JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
        full.head(SLICE).to_csv(JOBS_PATH, index=False)
        at = AppTest.from_file(str(APP_PATH), default_timeout=180)
        at.run()
        at.sidebar.radio[0].set_value("市场概览").run()
        assert not at.exception, f"[市场概览] 页面抛异常: {at.exception}"
        assert any("城市分布（Top 10）" in item.value for item in at.markdown)
        assert any("学历要求分布" in item.value for item in at.markdown)

        at.sidebar.radio[0].set_value("岗位检索").run()
        assert not at.exception, f"[岗位检索] 页面抛异常: {at.exception}"
        next(item for item in at.button if item.label == "搜索").click().run()
        assert not at.exception, f"[岗位检索交互] 页面抛异常: {at.exception}"
        assert any("共找到" in item.value for item in at.markdown)
        assert at.dataframe, "[岗位检索交互] 未显示结果表"
        page_two = next((item for item in at.button if item.label == "2"), None)
        assert page_two is not None, "[岗位检索分页] 未显示第 2 页按钮"
        page_two.click().run()
        assert not at.exception, f"[岗位检索分页] 页面抛异常: {at.exception}"
        assert at.session_state["search_page"] == 2, "[岗位检索分页] 未切换到第 2 页"

        at.sidebar.radio[0].set_value("分析洞察").run()
        assert not at.exception, f"[分析洞察] 页面抛异常: {at.exception}"
        assert any("分析洞察" in item.value for item in at.markdown)
        assert len(at.dataframe) >= 2, "[分析洞察] 未生成关键数据表"
        assert any("MAE" in item.value for item in at.markdown), "[分析洞察] 未生成 MAE 指标"
        assert any("R²" in item.value for item in at.markdown), "[分析洞察] 未生成 R² 指标"
        unavailable = [item.value for item in at.warning if "不可用" in item.value]
        assert not unavailable, f"[分析洞察] 服务不可用: {unavailable}"

        at.sidebar.radio[0].set_value("个性化推荐").run()
        assert not at.exception, f"[个性化推荐] 页面抛异常: {at.exception}"
        mode = next(item for item in at.radio if item.label == "推荐模式")
        assert mode.value == "多因素推荐"
        next(item for item in at.text_input if item.label == "目标岗位").set_value("数据分析师")
        next(item for item in at.text_input if item.label == "已掌握技能").set_value("Python;SQL")
        next(item for item in at.button if item.label == "生成推荐").click().run()
        assert not at.exception, f"[个性化推荐交互] 页面抛异常: {at.exception}"
        assert any("推荐结果" in item.value for item in at.markdown)

        at.sidebar.radio[0].set_value("采集管理").run()
        assert not at.exception, f"[采集管理] 页面抛异常: {at.exception}"
        assert any("采集管理" in item.value for item in at.markdown)
        trigger = next(item for item in at.button if item.label == "触发采集任务")
        trigger.click().run()
        assert not at.exception, f"[采集任务交互] 页面抛异常: {at.exception}"
        assert any(task.status == "pending" for task in task_service.list_tasks()), "[采集任务交互] 未记录 pending 任务"

        for name in MODULES:
            print(f"[{name}] 渲染及交互无异常")
    finally:
        if original is None:
            JOBS_PATH.unlink(missing_ok=True)
        else:
            JOBS_PATH.write_bytes(original)
            os.utime(
                JOBS_PATH,
                ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
            )
            assert JOBS_PATH.stat().st_mtime_ns == original_stat.st_mtime_ns
    print("Z7 app module integration verification PASSED")


if __name__ == "__main__":
    main()
