# BOSS 直聘采集基线

## 1. 上游项目版本

- 项目：`eatmoreduck/boss-zhipin-scraper`
- 地址：<https://github.com/eatmoreduck/boss-zhipin-scraper>
- 上游版本：`v2.2.0`
- 固定 commit：`2bc40f56a3ca3249ce3b98cdda0187e0bd612aa5`
- 固定日期：`2026-09-01`
- 运行环境：Python `3.12.13`、macOS；上游依赖为 `requests` 和 `websocket-client`

本项目使用上游项目的 Chrome DevTools Protocol 连接和 BOSS 岗位列表响应读取能力，不直接跟随上游 `master`。项目自己的 BOSS 适配、字段转换、BFS/DFS 任务遍历和数据清洗仍在本仓库中完成。

## 2. 独立浏览器环境

- Chrome 用户目录：`/Users/lushihao/.boss-zhipin-scraper/chrome-profile`
- CDP 端口：`9222`
- 登录方式：在专用 Chrome 窗口中手动登录 BOSS 直聘
- 主 Chrome 状态：未复制
- Cookie、账号凭据和验证码：不写入项目仓库

已运行 `--setup-chrome --login-timeout 300`。CDP 启动成功，并检测到登录态和可用的明文薪资字段。

## 3. 限定范围验证

### 采集条件

- 关键词：`大数据`
- 城市：`上海`
- 页数：`1`
- 详情数上限：`5`
- 详情采集：开启
- 采集方式：单次手动触发，列表页逐页读取，详情页按顺序访问

### 执行命令

```bash
env PYTHONPATH=/tmp/boss-zhipin-scraper-review.P9R1od/repo/.deps \
  /opt/homebrew/opt/python@3.12/libexec/bin/python3 \
  scripts/boss_cdp_raw.py \
  --keyword "大数据" \
  --city "上海" \
  --pages 1 \
  --max-details 5 \
  --format json \
  --output /Users/lushihao/.boss-zhipin-scraper/job-result/project_boss_jobs_20260901_2242.json \
  --detail-output /Users/lushihao/.boss-zhipin-scraper/job-result/project_boss_details_20260901_2242.json
```

### 验证时间和结果

- 列表采集时间：`2026-09-01T22:41:03+08:00`
- 列表结果：15 条岗位
- 详情采集结束：`2026-09-01T22:43:42+08:00`
- 详情尝试：5 条
- 有效详情：4 条
- 跳过详情：1 条，原因是详情文本不足，未写入有效 JD
- 列表结果文件：`/Users/lushihao/.boss-zhipin-scraper/job-result/project_boss_jobs_20260901_2242.json`
- 详情结果文件：`/Users/lushihao/.boss-zhipin-scraper/job-result/project_boss_details_20260901_2242.json`

列表结果包含职位、薪资、地区、经验/学历标签、技能、福利、公司规模、融资阶段、行业和岗位链接等字段。详情结果包含岗位描述和技能标签。原始结果文件位于仓库外，不提交到 Git。

## 4. 访问规则和停止条件

1. 仅采集岗位公开信息，用于课程学习和技术研究，遵守 BOSS 直聘用户协议、robots/页面规则及相关法律法规。
2. 由使用者在独立 Chrome 中手动登录，不复制主浏览器登录状态，不保存账号密码、Cookie、验证码和个人联系方式。
3. 采用限定关键词、限定城市、单页和详情数上限，按顺序访问；不并发轰击页面，不设置高频循环任务。
4. 遇到验证码、登录失效、访问频率限制、异常响应或平台明确禁止自动采集时立即停止，记录错误，不尝试绕过。
5. 原始结果先保存在仓库外的专用目录；进入项目的数据还要经过字段解析、去重、缺失标记和清洗，不能用采集结果覆盖原始文件。

## 5. 当前结论

上游项目在本机可以启动，独立 Chrome CDP 和手动登录流程可以运行，BOSS 限定范围列表采集已验证。该结果只证明采集链路可用，不代表已经完成本项目的标准字段转换、清洗和服务接入。下一步在 `feat/lushihao-data-cleaning` 分支完成 BOSS 适配器和 `jobs.csv` 输出。
