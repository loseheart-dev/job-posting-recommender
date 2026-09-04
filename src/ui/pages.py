import pandas as pd
import streamlit as st

from src.data.schema import StudentProfile
from src.services import site_service, task_service
from src.services.job_service import filter_jobs, salary_distribution, summarize_jobs


def render_home(jobs: pd.DataFrame) -> None:
    st.set_page_config(page_title="岗位数据分析与个性化推荐", layout="wide")
    page = st.sidebar.radio(
        "导航",
        ["市场概览", "岗位检索", "分析洞察", "个性化推荐", "采集管理"],
    )
    st.title("面向大学生求职的岗位数据分析与个性化推荐系统")
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
    except ValueError as exc:
        st.error(str(exc))
        buckets = []
    if buckets:
        dist_df = pd.DataFrame(buckets)
        dist_df["区间"] = dist_df["range"]
        st.bar_chart(dist_df.set_index("区间")["count"])
    else:
        st.info("暂无有效薪资数据，无法绘制薪资分布。")
    st.markdown("### 薪资影响因素")
    st.info("等待郑维豪提供薪资因素分析接口后展示。")
    st.markdown("### 岗位能力需求图谱")
    st.info("等待郑维豪提供能力需求图谱接口后展示。")
    st.markdown("### 招聘企业画像")
    st.info("等待郑维豪提供企业画像接口后展示。")
    st.markdown("### 岗位聚类")
    st.info("等待郑维豪提供 KMeans 聚类接口后展示。")


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
    st.success("画像已生成，等待丁伟哲提供多因素推荐接口后展示推荐结果。")
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


def _render_collection(jobs: pd.DataFrame) -> None:
    st.subheader("采集管理")

    # 确保默认站点存在
    try:
        site_service.ensure_default_site()
    except Exception as exc:  # 页面不应因服务初始化失败整体崩溃
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
                if st.button("触发采集任务", key=f"trigger_{site.site_id}"):
                    try:
                        task = task_service.trigger_task(site.site_id)
                        st.success(f"已创建任务：{task.task_id}")
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
