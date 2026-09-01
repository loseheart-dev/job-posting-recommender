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

| 分支 | 负责人 | 主要目录 |
|---|---|---|
| `feat/lushihao-algorithm` | 卢世豪 | `src/algorithms/clustering.py`、`src/algorithms/salary.py` |
| `feat/dingweizhe-recommendation` | 丁伟哲 | `src/algorithms/recommender.py` |
| `feat/zhengweihao-data-cleaning` | 郑维豪 | `src/data/cleaner.py`、`data/` |
| `feat/xuzhiling-backend-integration` | 徐挚凌 | `src/services/`、`src/data/loader.py` |
| `feat/wangyujie-frontend` | 王宇杰 | `app.py`、`src/ui/` |

共享接口先在模块函数签名中固定，跨模块改动先在群内确认。每人只提交自己分支负责目录的修改，`main` 只保留可运行和可演示版本。

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
