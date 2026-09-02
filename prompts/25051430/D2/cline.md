# D2 提示词记录（Cline 辅助）

> 我使用 Cline（AI 编程助手）辅助完成网站配置与采集任务调度服务。我负责确定接口字段、存储方案与调度范围，Cline 辅助编写服务函数与测试。

## 1. 确认前置条件与设计决策

实现前，我先梳理《接口约定》第 4 节的字段，并确定存储方案（内存态）、调度范围（不做真实后台定时器）、任务状态枚举，再请 Cline 核对前置条件。

提示词：
「请确认网站配置与采集任务调度服务的前置条件是否具备。字段按《接口约定》第 4 节：站点配置含 site_id/site_name/base_url/enabled/keywords/cities/crawl_strategy/start_at/frequency/max_depth；任务记录含 task_id/site_id/started_at/finished_at/status/raw_count/parsed_count/error_count/error_message。存储用内存态，调度不做真实定时器，状态枚举 pending/running/success/failed。请先核对，不要擅自改动。」

## 2. 实现网站配置服务

提示词：
「在 src/services/site_service.py 实现 SiteConfig 数据类与网站列表的增删改查、启停、频率配置；crawl_strategy 只能是 bfs/dfs，frequency 只能是 once/daily/twice_daily，max_depth 不能为负。字段放 src/services/，不改 schema.py。附带测试用例。」

## 3. 实现采集任务调度服务

提示词：
「在 src/services/task_service.py 实现 CollectionTask 数据类与手动触发、状态/记录查询，并提供 compute_next_run 按频率计算下次计划时间（纯计算、不触发真实定时器）。触发时校验站点存在且启用；状态只能是 pending/running/success/failed。」

## 4. 改写为 unittest 并处理 review

提示词：
「把 tests/test_site_task.py 改写为 unittest.TestCase，使 `python -m unittest discover -s tests` 能自动发现并运行。随后按组长 review 意见补齐校验：site_name/base_url 必填、任务不可更新字段与负计数校验、experience 作为兼容字段保留。」

## 5. 验证

我运行 `python -m unittest discover -s tests -v` 与 `python -m tests.smoke` 确认通过，并请 Cline 完成语法检查（compileall）。
