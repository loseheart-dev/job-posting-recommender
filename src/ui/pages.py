import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.schema import StudentProfile
from src.services import analysis_service, site_service, task_service
from src.services.job_service import filter_jobs, salary_distribution, summarize_jobs

# 视觉规范色彩 Token（来自 docs/团队/前端设计说明.md）
COLORS = {
    "page_bg": "#F5F8FD",
    "surface": "#FFFFFF",
    "text": "#102B63",
    "muted": "#60708F",
    "primary": "#2878F0",
    "success": "#2FB77A",
    "salary": "#F1A52B",
    "warning": "#D96C52",
    "border": "#DCE6F4",
}


def _apply_style() -> None:
    st.markdown(
        f"""
        <style>
        .main > div {{
            background-color: {COLORS['page_bg']} !important;
        }}
        body {{
            background-color: {COLORS['page_bg']} !important;
        }}
        .block-container {{
            padding-top: 1.5rem !important;
        }}
        h1, h2, h3 {{
            color: {COLORS['text']} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_home(jobs: pd.DataFrame) -> None:
    st.set_page_config(page_title="岗位数据分析与个性化推荐", layout="wide")
    _apply_style()
    page = st.sidebar.radio(
        "导航",
        ["市场概览", "岗位检索", "分析洞察", "个性化推荐", "采集管理"],
    )
    st.title("面向大学生求职的岗位数据分析与个性化推荐系统")
    st.caption(f"数据来源：data/processed/jobs.csv · 共 {len(jobs)} 条岗位记录")
    if jobs.empty:
        st.info("尚未找到清洗后岗位数据，请将 jobs.csv 放入 data/processed/。")
        return
    if page == "市场概览":
        _render_overview(jobs)
    elif page == "岗位检索":
        _render_search(jobs)
    elif page == "分析洞察":
        _render_analysis(jobs)
    elif page == "个性化推荐":
        _render_recommendation(jobs)
    elif page == "采集管理":
        _render_collection(jobs)


def _render_overview(jobs: pd.DataFrame) -> None:
    summary = summarize_jobs(jobs)
    job_count = summary["job_count"]
    salary_avg = summary["salary_avg"]
    salary_count = summary["salary_count"]
    top_skills = summary["top_skills"]
    salary_coverage = (salary_count / job_count * 100) if job_count else 0.0
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("岗位总量", job_count)
    col2.metric("平均月薪", f"{salary_avg:,.0f} 元" if salary_avg is not None else "暂无数据")
    col3.metric("薪资数据覆盖率", f"{salary_coverage:.1f}%")
    col4.metric("高频技能 Top1", top_skills[0][0] if top_skills else "暂无数据")
    st.subheader("高频技能")
    if top_skills:
        skill_df = pd.DataFrame(top_skills, columns=["技能", "出现次数"])
        st.table(skill_df.head(5))
    else:
        st.info("暂无技能数据")
    st.subheader("城市岗位分布")
    city_counts = jobs["city"].fillna("未知").value_counts().head(10)
    if not city_counts.empty:
        city_df = city_counts.reset_index()
        city_df.columns = ["城市", "岗位数量"]
        st.table(city_df)
    else:
        st.info("暂无城市数据")


def _render_search(jobs: pd.DataFrame) -> None:
    st.subheader("岗位检索")
    with st.form("search_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            keyword = st.text_input("关键词", placeholder="岗位名称、公司、技能或描述")
            city = st.text_input("城市", placeholder="如：杭州")
            work_type = st.selectbox("工作方式", ["", "全职", "实习", "校招", "远程"])
        with col2:
            experience = st.text_input("经验要求", placeholder="如：1-3年")
            education = st.text_input("学历", placeholder="如：本科")
            industry = st.text_input("行业", placeholder="如：大数据")
        with col3:
            company_nature = st.text_input("公司性质", placeholder="如：民营")
            salary_min = st.number_input("薪资下限（元/月）", min_value=0, step=1000, value=0)
            salary_max = st.number_input("薪资上限（元/月）", min_value=0, step=1000, value=0)
        submitted = st.form_submit_button("筛选")
    if not submitted:
        st.info("设置筛选条件后点击“筛选”查看结果。")
        return
    filters = {
        "keyword": keyword,
        "city": city,
        "work_type": work_type,
        "experience": experience,
        "education": education,
        "industry": industry,
        "company_nature": company_nature,
        "salary_min": salary_min if salary_min > 0 else None,
        "salary_max": salary_max if salary_max > 0 else None,
    }
    try:
        result = filter_jobs(jobs, filters)
    except ValueError as exc:
        st.error(str(exc))
        return
    if result.empty:
        st.warning("没有找到符合条件的岗位，请放宽筛选条件。")
        return
    st.success(f"共找到 {len(result)} 个岗位")
    display_columns = [
        "title", "company", "city", "work_type", "experience",
        "education", "salary_text", "skills", "source",
    ]
    st.dataframe(result[display_columns], use_container_width=True)

    st.markdown("### 岗位详情")
    selected_index = st.selectbox(
        "选择一个岗位查看详情",
        range(len(result)),
        format_func=lambda i: f"{result.iloc[i]['title']} · {result.iloc[i]['company']}",
    )
    if selected_index is not None:
        row = result.iloc[selected_index]
        with st.container(border=True):
            st.markdown(f"**{row['title']}** · {row['company']}")
            st.write(f"城市：{row['city'] or '未知'}")
            st.write(f"工作方式：{row['work_type'] or '未知'}")
            st.write(f"经验要求：{row['experience'] or '未知'}")
            st.write(f"学历要求：{row['education'] or '未知'}")
            st.write(f"薪资：{row['salary_text'] or '未知'}")
            st.write(f"技能：{row['skills'] or '未知'}")
            st.write(f"福利：{row['benefits'] or '未知'}")
            st.write(f"来源：{row['source'] or '未知'}")
            if row['description']:
                st.write(f"岗位描述：{row['description']}")
    csv = result.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="下载当前筛选结果 CSV",
        data=csv,
        file_name="filtered_jobs.csv",
        mime="text/csv",
    )


def _render_analysis(jobs: pd.DataFrame) -> None:
    st.subheader("分析洞察")
    st.markdown("### 薪资分布")
    try:
        buckets = salary_distribution(jobs)
        if buckets:
            dist_df = pd.DataFrame(buckets).sort_values("min").reset_index(drop=True)
            dist_df["区间"] = dist_df["range"]
            fig = px.bar(
                dist_df,
                x="区间",
                y="count",
                labels={"区间": "薪资区间（元/月）", "count": "岗位数量"},
                title="薪资分布",
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无有效薪资数据，无法绘制薪资分布。")
    except ValueError as exc:
        st.error(str(exc))
    st.markdown("### 薪资影响因素")
    try:
        salary_factors = analysis_service.salary_factor_analysis(jobs)
        st.dataframe(salary_factors, use_container_width=True)
    except Exception as exc:
        st.warning(f"薪资因素分析不可用：{exc}")
    st.markdown("### 岗位能力需求图谱")
    try:
        graph = analysis_service.skill_graph(jobs)
        freq = graph["skill_frequency"][:15]
        if freq:
            freq_df = pd.DataFrame(freq, columns=["技能", "出现次数"])
            fig = px.bar(freq_df, x="技能", y="出现次数", title="高频技能 Top 15")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无技能数据")
    except Exception as exc:
        st.warning(f"能力需求图谱不可用：{exc}")
    st.markdown("### 招聘企业画像")
    try:
        profiles = analysis_service.company_profile(jobs)
        st.dataframe(profiles.head(20), use_container_width=True)
    except Exception as exc:
        st.warning(f"企业画像不可用：{exc}")
    st.markdown("### 岗位聚类")
    try:
        clustered, summaries = analysis_service.job_cluster(jobs)
        cluster_df = clustered[["title", "company", "city", "salary_avg", "cluster_id"]].head(20)
        st.dataframe(cluster_df, use_container_width=True)
        for cluster_id, info in summaries.items():
            with st.container(border=True):
                st.markdown(f"**群组 {cluster_id}**")
                st.write(f"岗位数量：{info.get('count', '未知')}")
                st.write(f"平均薪资：{info.get('salary_avg', '未知')}")
                st.write(f"薪资范围：{info.get('salary_range', '未知')}")
                st.write(f"代表城市：{info.get('dominant_city', '未知')}")
                st.write(f"高频技能：{', '.join(info.get('top_skills', [])) or '未知'}")
    except Exception as exc:
        st.warning(f"岗位聚类不可用：{exc}")
    st.markdown("### 薪资预测模型评估")
    try:
        _, metrics = analysis_service.salary_prediction(jobs)
        col1, col2 = st.columns(2)
        col1.metric("MAE", metrics["mae"])
        col2.metric("R²", metrics["r2"])
        st.caption("随机森林模型在独立测试集上的评估指标。")
    except Exception as exc:
        st.warning(f"薪资预测不可用：{exc}")


def _render_recommendation(jobs: pd.DataFrame) -> None:
    st.subheader("个性化推荐")
    with st.form("profile_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            target_role = st.text_input("目标岗位", placeholder="如：数据分析师")
            education = st.text_input("学历", placeholder="如：本科")
            major = st.text_input("专业", placeholder="如：数据科学与大数据技术")
        with col2:
            school = st.text_input("学校", placeholder="如：某某大学")
            preferred_city = st.text_input("期望城市", placeholder="如：杭州")
            work_years = st.number_input("工作年限", min_value=0.0, step=1.0, value=0.0)
        with col3:
            skills = st.text_input("已掌握技能", placeholder="多个技能用英文分号分隔，如：Python;SQL")
            expected_salary_min = st.number_input("期望月薪下限", min_value=0, step=1000, value=0)
            expected_salary_max = st.number_input("期望月薪上限", min_value=0, step=1000, value=0)
        work_experience = st.text_area("工作或项目经历", placeholder="简要描述相关经历")
        submitted = st.form_submit_button("生成推荐")
    if not submitted:
        st.info("填写学生画像后点击“生成推荐”。")
        if "recommendations" in st.session_state and not st.session_state["recommendations"].empty:
            _display_recommendations(st.session_state["recommendations"])
        return
    try:
        profile = StudentProfile.from_mapping({
            "target_role": target_role,
            "education": education,
            "major": major,
            "school": school,
            "preferred_city": preferred_city,
            "work_years": work_years if work_years > 0 else None,
            "skills": skills,
            "work_experience": work_experience,
            "expected_salary_min": expected_salary_min if expected_salary_min > 0 else None,
            "expected_salary_max": expected_salary_max if expected_salary_max > 0 else None,
        })
    except ValueError as exc:
        st.error(str(exc))
        return
    st.markdown("### 当前画像")
    st.json({
        "target_role": profile.target_role,
        "education": profile.education,
        "major": profile.major,
        "school": profile.school,
        "preferred_city": profile.preferred_city,
        "work_years": profile.work_years,
        "skills": profile.skills,
        "work_experience": profile.work_experience,
        "expected_salary_min": profile.expected_salary_min,
        "expected_salary_max": profile.expected_salary_max,
    })
    st.markdown("### 推荐结果")
    try:
        recommendations = analysis_service.recommend_jobs_multifactor(profile, jobs, top_k=5)
    except Exception as exc:
        st.error(f"推荐接口调用失败：{exc}")
        return
    if recommendations.empty:
        st.warning("没有生成推荐结果，请检查画像是否填写完整。")
        return
    st.session_state["recommendations"] = recommendations
    _display_recommendations(recommendations)


def _display_recommendations(recommendations: pd.DataFrame) -> None:
    for _, row in recommendations.iterrows():
        with st.container(border=True):
            st.markdown(f"**{row['title']}** · {row['company']}")
            st.write(f"公司规模：{row['company_size'] or '未知'}")
            st.write(f"公司性质：{row['company_nature'] or '未知'}")
            st.write(f"行业：{row['industry'] or '未知'}")
            st.write(f"薪资区间：{row['salary_range'] or '未知'}")
            st.write(f"匹配概率：{row['match_probability']:.1%}")
            st.write(f"匹配技能：{row['matched_skills'] or '无'}")
            st.write(f"缺失技能：{row['missing_skills'] or '无'}")
            st.write(f"推荐理由：{row['reason']}")


def _render_collection(jobs: pd.DataFrame) -> None:
    st.subheader("采集管理")
    try:
        site_service.ensure_default_site()
    except Exception as exc:
        st.error(f"站点初始化失败: {exc}")
        return
    sites = site_service.list_sites()
    st.markdown("### 网站配置")
    if not sites:
        st.info("暂无网站配置")
    else:
        for site in sites:
            with st.expander(f"{site.site_name}（{site.site_id}）"):
                st.write(f"启用状态：{'开启' if site.enabled else '停用'}")
                st.write(f"关键词：{', '.join(site.keywords) if site.keywords else '未设置'}")
                st.write(f"城市：{', '.join(site.cities) if site.cities else '未设置'}")
                st.write(f"采集策略：{site.crawl_strategy}")
                st.write(f"最大深度：{site.max_depth}")
                st.write(f"开始时间：{site.start_at or '未设置'}")
                st.write(f"频率：{site.frequency}")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("触发采集任务", key=f"trigger_{site.site_id}"):
                        try:
                            task = task_service.trigger_task(site.site_id)
                            st.success(f"已创建任务：{task.task_id}")
                        except Exception as exc:
                            st.error(str(exc))
                with col2:
                    action_label = "停用" if site.enabled else "启用"
                    if st.button(action_label, key=f"toggle_{site.site_id}"):
                        try:
                            site_service.set_site_enabled(site.site_id, not site.enabled)
                            st.success(f"站点已{action_label}")
                        except Exception as exc:
                            st.error(str(exc))
                with col3:
                    if st.button("删除", key=f"remove_{site.site_id}"):
                        try:
                            site_service.remove_site(site.site_id)
                            st.success(f"已删除站点：{site.site_name}")
                        except Exception as exc:
                            st.error(str(exc))
    st.markdown("### 修改网站配置")
    site_ids = [site.site_id for site in site_service.list_sites()]
    if site_ids:
        edit_site_id = st.selectbox("选择要修改的站点", site_ids, key="edit_site_select")
        edit_site = site_service.get_site(edit_site_id)
        with st.form("edit_site_form"):
            col1, col2 = st.columns(2)
            with col1:
                edit_site_name = st.text_input("站点名称", value=edit_site.site_name)
                edit_base_url = st.text_input("Base URL", value=edit_site.base_url)
                edit_keywords = st.text_input("关键词", value=",".join(edit_site.keywords))
            with col2:
                edit_cities = st.text_input("城市", value=",".join(edit_site.cities))
                edit_strategy = st.selectbox("采集策略", ["bfs", "dfs"], index=0 if edit_site.crawl_strategy == "bfs" else 1)
                edit_frequency = st.selectbox("频率", ["once", "daily", "twice_daily"], index=["once", "daily", "twice_daily"].index(edit_site.frequency) if edit_site.frequency in ["once", "daily", "twice_daily"] else 0)
            edit_max_depth = st.number_input("最大深度", min_value=0, step=1, value=edit_site.max_depth)
            edit_start_at = st.text_input("开始时间", value=edit_site.start_at)
            edit_submitted = st.form_submit_button("保存修改")
        if edit_submitted:
            try:
                site_service.update_site(edit_site_id, {
                    "site_name": edit_site_name,
                    "base_url": edit_base_url,
                    "keywords": edit_keywords,
                    "cities": edit_cities,
                    "crawl_strategy": edit_strategy,
                    "frequency": edit_frequency,
                    "max_depth": edit_max_depth,
                    "start_at": edit_start_at,
                })
                st.success(f"已保存站点修改：{edit_site_id}")
            except Exception as exc:
                st.error(str(exc))

    st.markdown("### 新增网站配置")
    with st.form("add_site_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_site_id = st.text_input("站点 ID", placeholder="如：zhilian_zhaopin")
            new_site_name = st.text_input("站点名称", placeholder="如：智联招聘")
            new_base_url = st.text_input("Base URL", placeholder="如：https://www.zhaopin.com")
        with col2:
            new_keywords = st.text_input("关键词", placeholder="逗号分隔，如：大数据,数据分析")
            new_cities = st.text_input("城市", placeholder="逗号分隔，如：杭州,上海")
            new_strategy = st.selectbox("采集策略", ["bfs", "dfs"])
            new_frequency = st.selectbox("频率", ["once", "daily", "twice_daily"])
        new_max_depth = st.number_input("最大深度", min_value=0, step=1, value=1)
        new_start_at = st.text_input("开始时间", placeholder="ISO 格式，如：2026-09-04T08:00:00")
        submitted = st.form_submit_button("新增站点")
    if submitted:
        try:
            site_service.add_site({
                "site_id": new_site_id,
                "site_name": new_site_name,
                "base_url": new_base_url,
                "keywords": new_keywords,
                "cities": new_cities,
                "crawl_strategy": new_strategy,
                "start_at": new_start_at,
                "frequency": new_frequency,
                "max_depth": new_max_depth,
            })
            st.success(f"已新增站点：{new_site_name}")
        except Exception as exc:
            st.error(str(exc))
    st.markdown("### 采集任务记录")
    tasks = task_service.list_tasks()
    if not tasks:
        st.info("暂无采集任务记录")
    else:
        rows = [task.to_dict() for task in tasks]
        task_df = pd.DataFrame(rows)
        st.dataframe(task_df, use_container_width=True)



