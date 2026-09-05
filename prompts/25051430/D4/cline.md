# D4 提示词记录（Cline 辅助）

> 我使用 Cline（AI 编程助手）辅助完成 Z5/Z6。我负责核对真实数据与算法接口、做设计决策并跟进 review，Cline 辅助实现验证脚本、服务封装与测试。

## 1. 真实数据接入验证（Z5）

我先确认验证口径：真实清洗数据字段多、量大，不能沿用 12 行样例的假设，需逐键断言并覆盖空数据/缺文件。

提示词：
「请在 tests 下新增 verify_real_data.py：优先读 data/processed/jobs.csv，缺文件回退 tests/fixtures/expanded_jobs.csv（8608 行）。用 load_jobs 断言列对齐 JOB_COLUMNS；用 filter_jobs 覆盖 9 个筛选键并断言无结果/未知键抛 ValueError/不修改输入；用 summarize_jobs 断言统计键；用 salary_distribution 断言桶计数总和==salary_count；补充空数据与缺文件案例。跑通后勾选 todos 的 Z5。」

## 2. 算法调用适配（Z6）

我确认页面不应直接读原始数据、也不应重复写模型逻辑，因此把郑维豪、丁伟哲的算法统一收口到服务层。

提示词：
「新增 src/services/analysis_service.py，把郑维豪的三类分析/聚类/随机森林（salary_factor_analysis/salary_prediction/job_cluster/skill_graph/company_profile）与丁伟哲的推荐（recommend_jobs/recommend_jobs_multifactor）统一封装，页面只 import 本模块、不直接 import src.algorithms。空数据契约：分析类空表抛中文 ValueError，推荐类空表/空画像返回空表不抛错。」

## 3. 补充 unittest 测试

提示词：
「新增 tests/test_analysis_service.py（unittest）：用 12 行样例覆盖 7 个函数的正常与空数据/缺字段案例，校验输出列与 schema 常量（SALARY_FACTOR_COLUMNS/COMPANY_PROFILE_COLUMNS/RECOMMENDATION_COLUMNS 等）一致。运行 python -m unittest tests.test_analysis_service 通过后提交。」

## 4. 跟进 review 修复

提示词：
「组长 review：推荐接口空数据契约需在模块说明、测试、文档三处一致。请把 analysis_service 模块 docstring、测试与 docs/25051430/服务层调用说明.md 同步为"分析类抛错、推荐类空表"的空数据契约说明，并勾选 todos 的 Z6。」

## 5. 验证

我运行 `python -m tests.verify_real_data` 与 `python -m unittest tests.test_analysis_service` 确认通过，并请 Cline 检查 diff 只涉及目标文件、没有无关改动。
