# D3 提示词记录（Cline 辅助）

> 我使用 Cline（AI 编程助手）辅助完善统计函数。我负责核对接口契约、做设计决策并跟进 review，Cline 辅助实现函数、补充测试与文档。

## 1. 核对统计缺口与接口约束

我先对照分工清单 step 5 与 `summarize_jobs` 现状，确认缺少"薪资分布"，且 `summarize_jobs` 是《接口约定》§5 的冻结接口（返回键固定），确定采用"新增独立函数、不改动冻结接口"的方案，再请 Cline 核对。

提示词：
「请对照分工清单 step 5 与 src/services/job_service.py 的 summarize_jobs：当前缺少"薪资分布"，而 summarize_jobs 是《接口约定》§5 冻结接口、返回键固定。请先核对现状与约束，确认把薪资分布做成独立函数 salary_distribution（不改变冻结的 summarize_jobs 返回键），不要直接改代码。」

## 2. 实现独立薪资分布函数

提示词：
「在 src/services/job_service.py 新增 salary_distribution(jobs, step=5000.0)：按 salary_avg 分桶，返回 [{range,min,max,count}]；step 支持正数（含小数）；空数据或无有效薪资返回空列表；step 非正数抛 ValueError。在 tests/smoke.py 补充正常分桶、小数步长、空数据、非法 step 用例。」

## 3. 补充接口文档并提交 PR

提示词：
「在 docs/接口约定.md §5 服务层接口补充 salary_distribution 的签名与返回结构说明，与函数一起提交，并从个人分支发起 PR 到 main，等待审核。」

## 4. 跟进两轮 review 修复

提示词：
「按审核意见修复 salary_distribution：
① step 需支持正数浮点步长（不要用 int 截断导致 step=0.5 崩溃）；step 校验需提前到空数据判断之前，空数据+非法 step 也应抛 ValueError；
② 桶边界必须严格"左闭右开"：numpy.histogram 末桶右闭会把恰好命中 step 整数倍边界的薪资多算进前一桶，请修正边界生成，并补充"恰好命中桶上界"的测试。」

## 5. 验证

我运行 `python -m tests.smoke` 与 `python -m unittest discover -s tests` 确认通过，并请 Cline 检查 diff 只涉及目标文件、没有无关改动。
