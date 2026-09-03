# 项目需求与待办清单

> 每日根据实际进展更新；过程记录按成员学号保存：`daily/25051408|25051413|25051415|25051430/`、`prompts/<学号>/D#/`（拼音目录已全部迁移为学号，main 上无拼音残留）

## 项目基础需求

- [x] R1 BOSS 直聘岗位采集、导入、字段解析和数据清洗（卢世豪）
- [x] R2 网站配置、采集任务启停、开始时间和频率配置（徐挚凌）
- [x] R3 BFS/DFS 两种自研任务遍历策略（卢世豪）
- [x] R4 薪资影响因素、能力需求图谱、企业画像、KMeans 和随机森林（郑维豪）
- [x] R5 求职者画像和多因素职位推荐（丁伟哲）
- [ ] R6 数据可视化、职位展示和个性化推荐页面（王宇杰）
- [ ] R7 采集、清洗、分析、推荐、展示完整链路

## 卢世豪任务（25051408）

- [x] L1 固定 BOSS 上游版本并完成限定范围验证
- [x] L2 接入 JSON/CSV，保存原始结果、来源、时间和任务记录
- [x] L3 实现 BFS/DFS 遍历并记录访问节点和结果
- [x] L4 完成岗位字段映射、统一、去重、空值标记和薪资/地区标准化
- [x] L5 输出 `data/processed/jobs.csv`、数据字典、清洗记录和异常案例
- [ ] L6 与分析、服务和页面完成真实数据集中联调

## 徐挚凌任务（25051430）

- [x] Z1 共享接口对齐：岗位表 21 列、筛选键 9 项、StudentProfile 11 字段（含 experience 兼容）、JobRecord 位置参数、必填 source/crawled_at
- [x] Z2 网站配置服务 `site_service.py`：增删改查、启停、频率校验，site_name/base_url 必填
- [x] Z3 采集任务调度服务 `task_service.py`：手动触发、状态/记录查询、不可更新字段与负计数校验、下次计划时间纯计算
- [x] Z4 服务层测试 `test_site_task.py` 改写为 unittest，`unittest discover` 可自动发现
- [ ] Z5 数据读取/筛选/统计接入真实清洗数据
- [ ] Z6 算法调用适配（郑维豪分析、丁伟哲推荐）
- [ ] Z7 与王宇杰页面集中联调 + README 启动说明

## 郑维豪任务（25051413）

- [x] ZW1 独立测试数据：符合《接口约定》的 30 行岗位表（含薪资缺失/样本不足场景），tests/sample_data.py + sample_jobs.csv
- [x] ZW2 固定三类分析输入字段、统计口径与输出结构（schema.py 新增 SALARY_FACTOR_COLUMNS / SKILL_GRAPH_KEYS / COMPANY_PROFILE_COLUMNS）
- [x] ZW3 薪资影响因素分析 analyze_salary_factors：输出 factor / impact_direction / importance / description
- [x] ZW4 岗位能力需求图谱 build_skill_graph：输出 nodes / edges / skill_frequency
- [x] ZW5 招聘企业画像 build_company_profiles：输出 company / company_size / company_nature / industry / salary_summary / skill_summary
- [x] ZW6 KMeans 岗位聚类 cluster_jobs：特征标准化 + 群组标签 + 每组可读说明（n_clusters≥2，样本≥2×n_clusters）
- [x] ZW7 随机森林薪资预测 predict_salary：独立训练/测试划分，输出 predicted_salary + MAE/R²（样例 MAE=3416.67, R²=0.7635）
- [x] ZW8 异常案例（空数据/缺字段/样本不足/薪资缺失）+ 个人验收记录 + 算法调用样例；44 项自动化测试全通过，冒烟测试通过

## 丁伟哲任务（25051415）

- [x] T1 独立测试样例：符合 JOB_COLUMNS 的小型岗位表 + 3 组画像（技术岗 / 数据岗 / 技能为空）
- [x] T2 recommender.py 基线：TF-IDF（char_wb n-gram）文本相似度 + 技能/城市/经验匹配，输出 RECOMMENDATION_COLUMNS
- [x] T3 多因素扩展：学历/专业/学校/工作年限/工作经历/薪资区间（StudentProfile 已在本分支补全字段）
- [x] T4 输出待遇区间、适配公司、匹配概率、推荐理由
- [x] T5 异常案例：空岗位表、缺失字段、无结果、技能为空画像（13 个测试全过）
- [x] T6 个人验收记录：调用方式、输出样例、已知限制（随 PR #4 描述提交）
- [x] T7 发起 PR #4 并合并进 main（2026-09-02 组长 APPROVED 后合并）；两轮 review 意见已在个人分支修复并复审通过

## 王宇杰任务

- [ ] 任务卡占位：待本人补充任务明细与勾选状态（已认领 R6 可视化与推荐页面）

## 期末材料

- [x] M1 README.md 控制在 800 字内
- [x] M2 创建 `docs/25051408/立项报告.md`
- [x] M3 创建 `docs/25051408/调研报告.md`
- [x] M4 创建 `docs/25051408/项目报告.md`
- [x] M5 创建 `daily/25051408/D2.md` 和 `prompts/25051408/D2/`
- [x] M6 整理并导出 D1、D2 的真实用户提示词（敏感凭据已删除）

## 待确认 / 风险

- [x] 接口差异：StudentProfile 已补全 education/major/school/work_years/work_experience，experience 兼容字段已写入《接口约定.md》第 3 节（两轮 review 后组长批准，随 PR #4 合并）
- [x] README ≤800 字简写版：已完成（见 M1，由组长统一处理）
- [ ] 课程提交目标：课程说明写的是 gitee 仓库，本组实际使用 GitHub 仓库 → 确认课程扫描系统覆盖 GitHub
- [ ] git 用户名：丁伟哲当前 `user.name=candleice`，需与报名时填写的一致（不一致会算到别人头上）

## 后续待办

- [x] 完成郑维豪三类分析和两个模型（见"郑维豪任务"卡）
- [ ] 完成王宇杰页面和可视化（见"王宇杰任务"卡）
- [ ] 接入真实清洗数据，完成集中联调和演示
- [ ] 每日补充本人的日报和提示词导出
