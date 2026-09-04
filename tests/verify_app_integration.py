# -*- coding: utf-8 -*-
"""Z7：页面集中联调验证 —— Streamlit AppTest 遍历五个模块（可复现脚本）。

用法：``python -m tests.verify_app_integration``

说明：会临时把已入库的 ``tests/fixtures/expanded_jobs.csv`` 前 300 行放入
``data/processed/jobs.csv``（该路径被 gitignore、不随仓库提交），用 Streamlit
AppTest 依次渲染 app.py 的五个页面模块，断言不抛异常；无论结果如何都会恢复
原先的 jobs.csv。页面服务调用契约见 ``docs/25051430/服务层调用说明.md``。
"""
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
JOBS_PATH = ROOT / "data" / "processed" / "jobs.csv"
APP_PATH = ROOT / "app.py"
FIXTURE = ROOT / "tests" / "fixtures" / "expanded_jobs.csv"
SLICE = 300
MODULES = ["市场概览", "岗位检索", "分析洞察", "个性化推荐", "采集管理"]


def main() -> None:
    original = JOBS_PATH.read_bytes() if JOBS_PATH.exists() else None
    try:
        full = pd.read_csv(FIXTURE)
        full.head(SLICE).to_csv(JOBS_PATH, index=False)
        for name in MODULES:
            at = AppTest.from_file(str(APP_PATH), default_timeout=180)
            at.run()
            at.sidebar.radio[0].set_value(name)
            at.run()
            assert not at.exception, f"[{name}] 页面抛异常: {at.exception}"
            print(f"[{name}] 渲染无异常")
    finally:
        if original is None:
            JOBS_PATH.unlink(missing_ok=True)
        else:
            JOBS_PATH.write_bytes(original)
    print("Z7 app module integration verification PASSED")


if __name__ == "__main__":
    main()

