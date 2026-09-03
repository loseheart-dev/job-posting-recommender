# D1 提示词记录（Cline 辅助）

> 我使用 Cline（AI 编程助手）辅助完成共享接口对齐。我负责阅读规范、核对差异并做决策，Cline 辅助修改代码与补充测试。

## 1. 核对接口字段差异

我先阅读《docs/接口约定.md》与 `src/data/schema.py`，发现二者字段不一致，请 Cline 帮助核对并列出差异，再由我确认对齐方案。

提示词：
「请核对《docs/接口约定.md》与 src/data/schema.py：岗位表应为 21 列、筛选键应为 9 个、StudentProfile 应为 11 个字段（含 experience 兼容字段）。请列出当前 schema.py 与约定的差异，并说明需要补齐哪些字段，先不要直接改代码。」

## 2. 对齐共享接口

确认差异后，我要求 Cline 按接口约定补齐字段常量与数据类，并强调保持 JobRecord 位置参数兼容。

提示词：
「按接口约定把 JOB_COLUMNS 补齐到 21 列、FILTER_KEYS 补齐到 9 个、StudentProfile 补齐到 11 个字段（含 experience 兼容字段），并更新 JobRecord。注意保持 JobRecord 的第 3 个位置参数是 skills，新增字段放在末尾，避免破坏旧的位置参数调用。同步更新 job_service.py 的筛选逻辑和 tests/smoke.py 的样例。」

## 3. 补充回归测试

提示词：
「请在 tests/smoke.py 补充新增筛选键（education/industry/company_nature）、必填字段（source/crawled_at）以及 StudentProfile 新字段的回归测试，覆盖正常与异常案例。」

## 4. 验证

我运行 `python -m tests.smoke` 确认通过，并请 Cline 检查 diff 是否只涉及目标文件、没有无关改动。
