# Job Posting Recommender

面向大学生求职的岗位数据分析与个性化推荐系统。

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

没有清洗后数据时，页面会显示数据准备提示；数据文件放入 `data/processed/jobs.csv` 后即可由后端模块接入。

## 并行开发边界

| 分支 | 负责人 | 主要任务 | 当前第一步 |
|---|---|---|---|
| `feat/lushihao-algorithm` | 卢世豪 | KMeans 聚类、随机森林薪资预测 | 确认清洗数据字段和模型输入 |
| `feat/dingweizhe-recommendation` | 丁伟哲 | TF-IDF 推荐、匹配技能和缺失技能解释 | 确认岗位文本字段和学生画像 |
| `feat/zhengweihao-data-cleaning` | 郑维豪 | 数据采集、清洗、数据字典 | 确认公开数据源并统计原始字段 |
| `feat/xuzhiling-backend-integration` | 徐挚凌 | 数据读取、筛选、统计、算法调用 | 固定数据路径和服务函数签名 |
| `feat/wangyujie-frontend` | 王宇杰 | Streamlit 页面、交互和图表 | 搭好四个页面功能区 |

共享接口先在模块函数签名中固定，跨模块改动先在群内确认。每人只提交自己分支负责目录的修改，`main` 只保留可运行和可演示版本。

每个人的详细任务顺序、交接对象和验收标准见 [五人任务分工与验收清单.md](五人任务分工与验收清单.md)。

## 共享接口

岗位表、学生画像、筛选参数和算法返回字段已经固定，详见 [接口约定.md](docs/接口约定.md)。代码中的字段常量和数据类位于 `src/data/schema.py`，组员不需要互相等待确认列名。卢世豪负责审核契约变更，变更前先说明原因。

联调按“数据基线 → 算法基线 → 服务基线 → 页面联调”进行。每个人先在自己的分支完成正常和异常案例，卢世豪审核后再合并到 `main`，未通过上一阶段不进入下一阶段。

## 目录说明

```text
app.py                    Streamlit 启动入口
src/data/                 数据读取和清洗
src/algorithms/           聚类、薪资预测、个性化推荐
src/services/             筛选、统计和模块联调
src/ui/                   页面展示和图表
data/raw/                 原始数据，不提交真实敏感数据
data/processed/           清洗后数据
```

项目规范见 [AGENTS.md](AGENTS.md)，任务和验收边界见 [五人任务分工与验收清单.md](五人任务分工与验收清单.md)。
