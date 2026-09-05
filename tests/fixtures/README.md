# BOSS 小范围测试数据

这组固定样例来自 2026-09-01 在关键词“大数据”、城市“上海”条件下的小范围采集结果，保留 BOSS 上游 JSON 的字段结构，用于导入、字段映射、清洗和联调测试。

样例只保留岗位、公司概况、薪资、标签、福利和详情字段；公开的公司名称、岗位 ID 和岗位详情链接保留原值，招聘者信息、Cookie、登录态、`security_id`、`lid` 和加密账号标识已移除。岗位链接可能需要登录或因平台状态变化而失效，不作为真实招聘信息保证。

- `boss_sample.json`：4 条列表结果；
- `boss_details_sample.json`：4 条详情结果；
- `jobs_range_sample.csv`：从本次 113 条清洗结果中固定的 32 条标准岗位样例，覆盖上海和杭州；
- `expanded_jobs.csv`：2026-09-03 扩大关键词和地域范围后固定的 8608 条清洗结果，覆盖 61 个岗位关键词和 32 个城市；上海、杭州原有数据完整保留，其他城市通过新增采集数据扩充，其他城市单城 235–299 条；
- `expanded_jobs_metadata.json`：对应的采集范围、时间、任务统计和清洗规则记录；
- `expanded_jobs_stats.json`：由 `scripts/fixture_stats.py` 根据 CSV 和元数据重新计算的行数、城市分布、关键词数、去重数和沪杭占比；
- `real_data_salary_verification.json`：基于 8608 条重洗数据复算的薪资分布、合法高薪保留断言和随机森林 MAE/R²；脚本为 `tests/verify_salary_real_data.py`；
- 原始完整采集结果仍保存在本机专用目录，不提交到仓库。

重新计算统计结果：

```bash
python3 scripts/fixture_stats.py --output tests/fixtures/expanded_jobs_stats.json
```
