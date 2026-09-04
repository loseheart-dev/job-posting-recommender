# D5 提示词记录（Cline 辅助）

> 我使用 Cline（AI 编程助手）辅助完成 Z7 页面集中联调。我负责核对页面调用契约、做联调验证决策并跟进 review，Cline 辅助实现文档、联调脚本与改造。

## 1. README 启动说明与联调契约文档

我确认联调需要一份"页面如何调用服务层"的契约，且 README 需给出可复现的启动步骤。

提示词：
「在 README 补充运行启动步骤（pip install -r requirements.txt、把 tests/fixtures/expanded_jobs.csv 复制到 data/processed/jobs.csv、streamlit run app.py），并新增 docs/25051430/服务层调用说明.md 作为页面联调契约：列出 load_jobs/filter_jobs/summarize_jobs/salary_distribution、analysis_service 各函数、site_service/task_service 与最小调用示例；README 控制在 800 字内。」

## 2. 同步 main 并核对页面调用

提示词：
「把 main（含王宇杰五模块页面 PR #29、郑维豪算法 PR #33/#34）同步到个人分支，逐页核对 src/ui/pages.py 调用的 7 个 analysis_service 函数与 site_service/task_service/job_service 的签名是否与我的服务层一致，列出差异。」

## 3. AppTest 五模块联调脚本

提示词：
「新增 tests/verify_app_integration.py：用 Streamlit AppTest 遍历 app.py 的五个模块（市场概览/岗位检索/分析洞察/个性化推荐/采集管理），临时把 tests/fixtures/expanded_jobs.csv 前 300 行放入 data/processed/jobs.csv，测完用 finally 恢复原文件；断言页面无未捕获异常。注意 AppTest.from_file 需仓库根绝对路径，at.exception 用真值判断而非 is None。」

## 4. 跟进组长三条 review 意见

提示词：
「组长 review 三条意见：①只查未捕获异常无法证明页面与服务层联通，需为每个模块驱动真实交互并断言预期结果，同时检查 at.error 与非预期 at.warning；②验证脚本要能被 CI 执行；③恢复 jobs.csv 时需一并恢复 st_mtime_ns（页面把 mtime 显示为数据更新时间）。请按此补齐：市场概览断言"高频技能"、岗位检索点击"筛选"断言"共找到"+结果表、分析洞察断言 3 个数据表+MAE/R² 且无"不可用"warning、个性化推荐提交画像断言"推荐结果"、采集管理点击"触发采集任务"断言"已创建任务"；在 CI workflow 增加显式步骤 python -m tests.verify_app_integration；finally 恢复原文件后用 os.utime 恢复 atime/mtime 并断言 st_mtime_ns 一致。」

## 5. 验证

我运行 `python -m tests.verify_app_integration`、`python -m unittest discover -s tests -v` 与 `python -m compileall src app.py scripts tests` 确认通过，并请 Cline 检查 diff 只涉及目标文件、没有无关改动。
