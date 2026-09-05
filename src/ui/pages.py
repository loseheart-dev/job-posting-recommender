from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data.schema import StudentProfile
from src.data.market import JOB_CATEGORIES, add_job_category
from src.services import analysis_service, site_service, task_service
from src.services.job_service import (
    education_distribution,
    filter_jobs,
    paginate_jobs,
    salary_distribution,
    summarize_jobs,
)


COLORS = {
    "page_bg": "#F5F8FD", "surface": "#FFFFFF", "text": "#102B63",
    "muted": "#60708F", "primary": "#2878F0", "success": "#2FB77A",
    "salary": "#F1A52B", "warning": "#D96C52", "border": "#DCE6F4",
}
PAGES = ("市场概览", "岗位检索", "分析洞察", "个性化推荐", "采集管理")
DATA_PATH = Path("data/processed/jobs.csv")
ABOUT_PAGE_PATH = Path(__file__).resolve().parents[2] / "about.html"
ABOUT_URL = "/about.html"


def _is_about_page_url(url: object) -> bool:
    return str(url or "").rstrip("/").endswith("/about.html")


def _apply_style() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --page-bg:{COLORS['page_bg']}; --surface:{COLORS['surface']};
            --text:{COLORS['text']}; --muted:{COLORS['muted']};
            --primary:{COLORS['primary']}; --success:{COLORS['success']};
            --salary:{COLORS['salary']}; --warning:{COLORS['warning']};
            --border:{COLORS['border']};
        }}
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
            background:var(--page-bg); color:var(--text);
            font-family:Inter,-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
        }}
        [data-testid="stHeader"] {{ background:transparent; }}
        #MainMenu, footer {{ display:none!important; }}
        .block-container {{ max-width:1540px; padding:1.4rem 1.8rem 3rem; }}
        section[data-testid="stSidebar"] {{
            width:14rem!important; min-width:14rem!important; background:var(--surface);
            border-right:1px solid var(--border);
        }}
        section[data-testid="stSidebar"] > div {{ padding:1.45rem .85rem; }}
        [data-testid="stSidebar"] [role="radiogroup"] {{ gap:.35rem; }}
        [data-testid="stSidebar"] [role="radiogroup"] label {{
            min-height:2.9rem; padding:.7rem .9rem; border-radius:8px; color:var(--text);
            transition:background .16s ease,color .16s ease;
        }}
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {{ background:#EDF4FF; }}
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
            background:#E3EEFF; color:var(--primary); font-weight:650;
            box-shadow:inset 3px 0 0 var(--primary);
        }}
        [data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {{ display:none; }}
        .sidebar-about-link {{
            display:block; min-height:2.9rem; padding:.7rem .9rem; margin-top:.35rem;
            border-radius:8px; color:var(--text); text-decoration:none;
        }}
        .sidebar-about-link:hover {{ background:#EDF4FF; color:var(--primary); }}
        h1,h2,h3,h4,p {{ color:var(--text); }}
        h2 {{ font-size:1.28rem!important; }} h3 {{ font-size:1.02rem!important; }}
        [data-testid="stCaptionContainer"] {{ color:var(--muted); }}
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background:var(--surface); border-color:var(--border)!important; border-radius:8px;
            box-shadow:0 5px 18px rgba(16,43,99,.035);
        }}
        [data-testid="stForm"] {{
            background:var(--surface); border-color:var(--border); border-radius:8px;
            padding:1rem 1.05rem;
        }}
        [data-baseweb="input"] > div,[data-baseweb="select"] > div,[data-testid="stTextArea"] textarea {{
            background:#F7F9FC!important; border-color:var(--border)!important;
        }}
        .stButton > button,.stDownloadButton > button,[data-testid="stFormSubmitButton"] button {{
            min-height:2.45rem; border-radius:7px; border:1px solid var(--border); font-weight:600;
        }}
        .stButton > button:hover,.stDownloadButton > button:hover,[data-testid="stFormSubmitButton"] button:hover {{
            border-color:var(--primary); color:var(--primary);
        }}
        [data-testid="stFormSubmitButton"] button[kind="primary"],.stButton > button[kind="primary"] {{
            background:var(--primary); border-color:var(--primary); color:white;
        }}
        [data-testid="stDataFrame"] {{ border:1px solid var(--border); border-radius:8px; overflow:hidden; }}
        [data-testid="stAlert"] {{ border-radius:8px; }}
        .brand {{ padding:.1rem .55rem 1.2rem; }}
        .brand-name {{ color:var(--text); font-size:1.55rem; line-height:1.1; font-weight:780; letter-spacing:-.035em; }}
        .brand-subtitle {{ color:var(--muted); margin-top:.35rem; font-size:.86rem; }}
        .sidebar-status {{
            margin:3.2rem .15rem 0; padding:.9rem; border:1px solid var(--border);
            border-radius:8px; background:#FBFDFF; font-size:.78rem; line-height:1.65;
        }}
        .sidebar-status-title {{ font-weight:700; margin-bottom:.5rem; }}
        .status-dot {{ display:inline-block; width:.48rem; height:.48rem; border-radius:50%; background:var(--success); margin-right:.38rem; }}
        .page-header {{ display:flex; align-items:center; justify-content:space-between; gap:1rem; margin:0 0 1rem; }}
        .page-heading {{ display:flex; align-items:baseline; gap:1.2rem; min-width:0; }}
        .page-title {{ font-size:1.45rem; font-weight:760; color:var(--text); white-space:nowrap; }}
        .page-meta {{ color:var(--muted); font-size:.83rem; }}
        .page-actions {{ display:flex; align-items:center; gap:.7rem; flex-shrink:0; }}
        .about-link {{ color:var(--primary); font-size:.82rem; font-weight:650; text-decoration:none; white-space:nowrap; }}
        .about-link:hover {{ text-decoration:underline; }}
        .data-badge {{ border:1px solid #B9D3FA; border-radius:6px; padding:.42rem .68rem; color:var(--primary); background:#F6FAFF; font-size:.78rem; white-space:nowrap; }}
        .kpi-card {{ min-height:8rem; padding:1rem 1.12rem; border:1px solid var(--border); border-radius:8px; background:var(--surface); box-shadow:0 5px 18px rgba(16,43,99,.035); }}
        .kpi-label {{ color:var(--muted); font-size:.82rem; font-weight:600; }}
        .kpi-value {{ color:var(--text); font-size:1.85rem; font-weight:740; margin:.35rem 0; }}
        .kpi-value.salary,.salary {{ color:var(--salary); }}
        .kpi-value.success,.success {{ color:var(--success); }}
        .kpi-note {{ color:var(--muted); font-size:.76rem; line-height:1.45; }}
        .section-label {{ color:var(--text); font-size:1rem; font-weight:700; margin:.15rem 0 .65rem; }}
        .detail-title {{ color:var(--primary); font-size:1.14rem; font-weight:730; }}
        .detail-company {{ color:var(--text); font-weight:650; margin:.18rem 0 .5rem; }}
        .salary {{ font-size:1.25rem; font-weight:740; }} .success {{ font-weight:700; }}
        .warning {{ color:var(--warning); font-weight:650; }} .muted {{ color:var(--muted); }}
        .meta-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.4rem .8rem; margin:.75rem 0; color:var(--muted); font-size:.8rem; }}
        .chip {{ display:inline-block; padding:.2rem .48rem; margin:.15rem .18rem .15rem 0; border-radius:5px; border:1px solid #D7E4F8; background:#F1F5FB; color:var(--text); font-size:.72rem; }}
        .chip.good {{ background:#EDF9F4; border-color:#CDEDDD; color:#17845A; }}
        .chip.warn {{ background:#FFF3EF; border-color:#F4D7CF; color:#C0523B; }}
        .recommend-card,.site-card {{ border:1px solid var(--border); border-radius:8px; background:var(--surface); padding:1rem; margin-bottom:.75rem; }}
        .recommend-grid {{ display:grid; grid-template-columns:1.05fr .72fr 1fr 1.25fr; gap:1rem; align-items:start; }}
        .recommend-grid > div + div {{ border-left:1px solid var(--border); padding-left:1rem; }}
        .profile-summary {{ border:1px solid var(--border); border-radius:8px; padding:.85rem 1rem; background:#FBFDFF; margin-bottom:.8rem; }}
        .site-grid {{ display:grid; grid-template-columns:1.3fr 1fr 1fr .7fr .6fr .8fr; gap:1rem; margin-top:.75rem; color:var(--muted); font-size:.78rem; }}
        .site-grid strong {{ display:block; color:var(--text); margin-top:.2rem; font-weight:550; }}
.status-pill {{ display:inline-block; margin-left:.5rem; padding:.18rem .45rem; border-radius:5px; background:#EAF8F1; color:#17845A; font-size:.72rem; font-weight:700; }}
@media (max-width:900px) {{
            section[data-testid="stSidebar"] {{ width:12rem!important; min-width:12rem!important; }}
            .page-header,.page-heading {{ align-items:flex-start; flex-direction:column; gap:.3rem; }}
            .recommend-grid,.site-grid {{ grid-template-columns:1fr; }}
            .recommend-grid > div + div {{ border-left:0; border-top:1px solid var(--border); padding:.7rem 0 0; }}
        }}
        @media (prefers-reduced-motion:reduce) {{ * {{ transition:none!important; }} }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_about_page() -> None:
    if ABOUT_PAGE_PATH.exists():
        st.markdown(ABOUT_PAGE_PATH.read_text(encoding="utf-8"), unsafe_allow_html=True)
    else:
        st.error("项目介绍页面暂不可用。")


def _safe(value: object, fallback: str = "未知") -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return fallback
    try:
        if bool(pd.isna(value)):
            return fallback
    except (TypeError, ValueError):
        pass
    return html.escape(str(value))


def _tokens(value: object, limit: int = 6) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple, set)):
        try:
            if bool(pd.isna(value)):
                return []
        except (TypeError, ValueError):
            pass
    values = [str(item).strip() for item in value] if isinstance(value, (list, tuple, set)) else re.split(r"[,;；，、|]", "" if value is None else str(value))
    return [item for item in values if item and item.lower() not in {"nan", "none"}][:limit]


def _summary_mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _summary_number(summary: dict[str, object], key: str) -> float | None:
    value = summary.get(key)
    try:
        number = float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
    return number if number is not None and pd.notna(number) else None


def _display_text(value: object, fallback: str = "未提供") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return fallback
    return text


def _format_salary_summary(value: object) -> str:
    summary = _summary_mapping(value)
    count = _summary_number(summary, "count")
    if not count:
        return "暂无有效薪资"
    parts = [f"{int(count)} 个岗位"]
    mean = _summary_number(summary, "mean")
    low = _summary_number(summary, "min")
    high = _summary_number(summary, "max")
    if mean is not None:
        parts.append(f"平均 {mean:,.0f} 元/月")
    if low is not None and high is not None:
        parts.append(f"区间 {low:,.0f}–{high:,.0f} 元/月")
    return " · ".join(parts)


def _format_skill_summary(value: object) -> str:
    summary = _summary_mapping(value)
    if not summary:
        return "暂无技能记录"
    items = []
    for skill, count in summary.items():
        items.append(f"{skill}（{_display_text(count, '0')}）")
    return " · ".join(items)


def _compact_salary_distribution(dist_df: pd.DataFrame, cutoff: int = 40_000) -> pd.DataFrame:
    """将极少量高薪离群区间合并，避免图表被拉长到无法阅读。"""
    if dist_df.empty or "min" not in dist_df or "count" not in dist_df:
        return dist_df
    regular = dist_df[dist_df["min"] < cutoff].copy()
    high_count = int(dist_df.loc[dist_df["min"] >= cutoff, "count"].sum())
    if high_count:
        regular = pd.concat([regular, pd.DataFrame([{"min": cutoff, "max": None, "range": f"{cutoff}+", "count": high_count}])], ignore_index=True)
    return regular


def _chips(value: object, tone: str = "") -> str:
    class_name = f"chip {tone}".strip()
    return "".join(f'<span class="{class_name}">{html.escape(item)}</span>' for item in _tokens(value))


def _data_updated() -> str:
    return datetime.fromtimestamp(DATA_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M") if DATA_PATH.exists() else "未知"


def _sidebar(job_count: int) -> str:
    st.sidebar.markdown('<div class="brand"><div class="brand-name">Career Signal</div><div class="brand-subtitle">岗位智能工作台</div></div>', unsafe_allow_html=True)
    page = st.sidebar.radio("导航", PAGES, label_visibility="collapsed")
    st.sidebar.markdown(
        f'<a class="sidebar-about-link" href="{ABOUT_URL}" target="_self">项目介绍</a>',
        unsafe_allow_html=True,
    )
    site = site_service.ensure_default_site()
    tasks = task_service.list_tasks(site.site_id)
    active_tasks = [task for task in tasks if task.status in {"pending", "running"}]
    failed_tasks = [task for task in tasks if task.status == "failed"]
    if active_tasks:
        collection_status, status_class = "任务处理中", "success"
    elif failed_tasks:
        collection_status, status_class = "最近失败", "warning"
    else:
        collection_status, status_class = "按需采集", "muted"
    enabled_text = "已启用" if site.enabled else "已停用"
    st.sidebar.markdown(
        f"""<div class="sidebar-status"><div class="sidebar-status-title">数据链路</div>
        <div><span class="status-dot"></span>{_safe(site.site_name)}　<span class="{status_class}">{collection_status}</span></div>
        <hr style="border:0;border-top:1px solid var(--border);margin:.6rem 0">
        <div>启用状态　<span class="{status_class}">{enabled_text}</span></div><div>采集策略　{_safe(site.crawl_strategy.upper())}</div>
        <div>数据更新　{_data_updated()}</div><div>岗位记录　{job_count:,} 条</div></div>""",
        unsafe_allow_html=True,
    )
    return page


def _page_header(title: str, jobs: pd.DataFrame, subtitle: str = "") -> None:
    meta = subtitle or f"基于 BOSS直聘 岗位数据　数据更新时间：{_data_updated()}"
    st.markdown(
        f"""<div class="page-header"><div class="page-heading"><div class="page-title">{html.escape(title)}</div>
        <div class="page-meta">{html.escape(meta)}</div></div><div class="page-actions"><a class="about-link" href="{ABOUT_URL}" target="_self">项目介绍</a>
        <div class="data-badge">数据范围：已清洗岗位数据 · {len(jobs):,} 条</div></div></div>""",
        unsafe_allow_html=True,
    )


def _kpi(label: str, value: str, note: str, tone: str = "") -> None:
    tone_class = tone if tone in {"salary", "success"} else ""
    st.markdown(
        f"""<div class="kpi-card"><div class="kpi-label">{html.escape(label)}</div>
        <div class="kpi-value {tone_class}">{html.escape(value)}</div><div class="kpi-note">{html.escape(note)}</div></div>""",
        unsafe_allow_html=True,
    )


def _style_figure(fig, height: int = 300):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=25, b=10), paper_bgcolor=COLORS["surface"], plot_bgcolor=COLORS["surface"], font=dict(color=COLORS["muted"], size=11), legend_title_text="")
    fig.update_xaxes(gridcolor="#EDF2F8", linecolor=COLORS["border"])
    fig.update_yaxes(gridcolor="#EDF2F8", linecolor=COLORS["border"])
    return fig


def _filter_options(jobs: pd.DataFrame, column: str, all_label: str = "全部") -> list[str]:
    values = jobs[column].fillna("").astype(str).str.strip()
    options = sorted({value for value in values if value})
    return [all_label, *options]


def _parse_salary(value: str, label: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    try:
        amount = float(value)
    except ValueError as exc:
        raise ValueError(f"{label}必须是数字") from exc
    if amount < 0:
        raise ValueError(f"{label}不能为负数")
    return amount


def _page_numbers(page: int, total_pages: int) -> list[int | None]:
    if total_pages <= 7:
        return list(range(1, total_pages + 1))
    if page <= 4:
        return [1, 2, 3, 4, 5, None, total_pages]
    if page >= total_pages - 3:
        return [1, None, total_pages - 4, total_pages - 3, total_pages - 2, total_pages - 1, total_pages]
    return [1, None, page - 1, page, page + 1, None, total_pages]


def _render_pagination(meta: dict[str, object], key_prefix: str) -> None:
    total = int(meta["total"])
    page = int(meta["page"])
    total_pages = int(meta["total_pages"])
    if total_pages <= 1:
        st.caption(f"共 {total:,} 条岗位")
        return
    controls = st.columns([1.1, 4.8, 1.2])
    with controls[0]:
        st.caption(f"共 {total:,} 条")
    with controls[1]:
        page_cols = st.columns(len(_page_numbers(page, total_pages)))
        for column, number in zip(page_cols, _page_numbers(page, total_pages), strict=True):
            with column:
                if number is None:
                    st.markdown("<div style='text-align:center;padding:.45rem 0;color:var(--muted)'>…</div>", unsafe_allow_html=True)
                elif st.button(
                    str(number),
                    key=f"{key_prefix}_page_{number}",
                    type="primary" if number == page else "secondary",
                    use_container_width=True,
                ):
                    st.session_state[f"{key_prefix}_page"] = number
                    st.rerun()
    with controls[2]:
        st.selectbox(
            "每页条数",
            [10, 20, 50],
            key=f"{key_prefix}_page_size",
            label_visibility="collapsed",
        )


def render_home(jobs: pd.DataFrame) -> None:
    st.set_page_config(page_title="Career Signal", layout="wide", initial_sidebar_state="expanded")
    _apply_style()
    context = getattr(st, "context", None)
    if _is_about_page_url(getattr(context, "url", None)):
        _render_about_page()
        return
    page = _sidebar(len(jobs))
    if jobs.empty and page != "采集管理":
        _page_header(page, jobs)
        st.info("尚未找到清洗后岗位数据，请将 jobs.csv 放入 data/processed/。")
        return
    {"市场概览": _render_overview, "岗位检索": _render_search, "分析洞察": _render_analysis, "个性化推荐": _render_recommendation, "采集管理": _render_collection}[page](jobs)


def _render_overview(jobs: pd.DataFrame) -> None:
    _page_header("面向大学生求职的岗位数据分析与个性化推荐系统", jobs)
    summary = summarize_jobs(jobs)
    job_count, salary_avg, salary_count, top_skills = summary["job_count"], summary["salary_avg"], summary["salary_count"], summary["top_skills"]
    salary_coverage = salary_count / job_count * 100 if job_count else 0.0
    cols = st.columns(4, gap="small")
    with cols[0]: _kpi("岗位总量", f"{job_count:,}", "当前清洗后的有效岗位")
    with cols[1]: _kpi("平均月薪", f"¥{salary_avg:,.0f}" if salary_avg is not None else "暂无数据", "按有效月薪样本统计", "salary")
    with cols[2]: _kpi("薪资数据覆盖率", f"{salary_coverage:.1f}%", f"有效薪资 {salary_count:,} 条", "success")
    with cols[3]: _kpi("高频技能（Top 5）", top_skills[0][0] if top_skills else "暂无数据", "、".join(skill for skill, _ in top_skills[:5]) or "暂无数据")

    chart_cols = st.columns(3, gap="small")
    with chart_cols[0]:
        with st.container(border=True):
            st.markdown('<div class="section-label">城市分布（Top 10）</div>', unsafe_allow_html=True)
            city_df = jobs["city"].fillna("未知").value_counts().head(10).sort_values().rename_axis("城市").reset_index(name="岗位数量")
            fig = px.bar(city_df, x="岗位数量", y="城市", orientation="h", color_discrete_sequence=[COLORS["primary"]])
            st.plotly_chart(_style_figure(fig), use_container_width=True, config={"displayModeBar": False})
    with chart_cols[1]:
        with st.container(border=True):
            st.markdown('<div class="section-label">薪资区间分布</div>', unsafe_allow_html=True)
            dist_df = _compact_salary_distribution(pd.DataFrame(salary_distribution(jobs)))
            if dist_df.empty:
                st.info("暂无有效薪资数据。")
            else:
                dist_df = dist_df.sort_values("min")
                fig = px.bar(dist_df, x="range", y="count", labels={"range": "薪资区间（元/月）", "count": "岗位数量"}, color_discrete_sequence=[COLORS["primary"]])
                st.plotly_chart(_style_figure(fig), use_container_width=True, config={"displayModeBar": False})
    with chart_cols[2]:
        with st.container(border=True):
            st.markdown('<div class="section-label">学历要求分布</div>', unsafe_allow_html=True)
            edu_df = pd.DataFrame(education_distribution(jobs)).rename(columns={"education": "学历", "count": "岗位数量"})
            if edu_df.empty:
                st.info("暂无学历数据。")
            else:
                fig = px.pie(edu_df, names="学历", values="岗位数量", hole=.55, color_discrete_sequence=[COLORS["primary"], "#21B9A6", "#F4B740", "#8D72E1", "#AAB5C7", "#5C9CF5"])
                st.plotly_chart(_style_figure(fig), use_container_width=True, config={"displayModeBar": False})
    _render_overview_workspace(jobs)


def _render_overview_workspace(jobs: pd.DataFrame) -> None:
    search_col, recommendation_col = st.columns([2.35, 1], gap="small")
    with search_col:
        with st.container(border=True):
            st.markdown('<div class="section-label">岗位检索</div>', unsafe_allow_html=True)
            if "overview_page" not in st.session_state:
                st.session_state["overview_page"] = 1
            if "overview_page_size" not in st.session_state:
                st.session_state["overview_page_size"] = 10
            with st.form("overview_search_form"):
                fields = st.columns(6, gap="small")
                keyword = fields[0].text_input("关键词", placeholder="如：数据分析", key="overview_keyword")
                city_value = fields[1].selectbox("城市", _filter_options(jobs, "city", "全部城市"), key="overview_city")
                education_value = fields[2].selectbox("学历要求", _filter_options(jobs, "education"), key="overview_education")
                experience_value = fields[3].selectbox("工作经验", _filter_options(jobs, "experience"), key="overview_experience")
                industry_value = fields[4].selectbox("行业领域", _filter_options(jobs, "industry"), key="overview_industry")
                salary_choice = fields[5].selectbox("期望薪资", ["全部", "5K 以下", "5K-10K", "10K-15K", "15K-30K", "30K 以上"], key="overview_salary")
                salary_filters = {
                    "全部": {},
                    "5K 以下": {"salary_max": 5000},
                    "5K-10K": {"salary_min": 5000, "salary_max": 10000},
                    "10K-15K": {"salary_min": 10000, "salary_max": 15000},
                    "15K-30K": {"salary_min": 15000, "salary_max": 30000},
                    "30K 以上": {"salary_min": 30000},
                }[salary_choice]
                action_col, reset_col, _ = st.columns([1, 1, 7])
                submitted = action_col.form_submit_button("搜索", type="primary", use_container_width=True)
                reset = reset_col.form_submit_button("重置")
            if submitted:
                st.session_state["overview_results"] = filter_jobs(jobs, {
                    "keyword": keyword,
                    "city": "" if city_value == "全部城市" else city_value,
                    "education": "" if education_value == "全部" else education_value,
                    "experience": "" if experience_value == "全部" else experience_value,
                    "industry": "" if industry_value == "全部" else industry_value,
                    **salary_filters,
                })
                st.session_state["overview_page"] = 1
            if reset:
                st.session_state.pop("overview_results", None)
                st.session_state["overview_page"] = 1
            result = st.session_state.get("overview_results", jobs)
            if result.empty:
                st.warning("没有找到符合条件的岗位，请放宽筛选条件。")
                return
            page_meta = paginate_jobs(
                result,
                page=int(st.session_state["overview_page"]),
                page_size=int(st.session_state["overview_page_size"]),
            )
            st.session_state["overview_page"] = int(page_meta["page"])
            table_columns = ["title", "company", "city", "salary_text", "education", "experience", "skills"]
            labels = {"title": "职位名称", "company": "公司名称", "city": "城市", "salary_text": "薪资范围", "education": "学历", "experience": "经验", "skills": "技能要求"}
            st.markdown(f'<div class="muted" style="font-size:.78rem;margin:.45rem 0 .5rem">共找到 {int(page_meta["total"]):,} 条岗位</div>', unsafe_allow_html=True)
            st.dataframe(page_meta["items"][table_columns].rename(columns=labels), use_container_width=True, hide_index=True, height=330)
            _render_pagination(page_meta, "overview")
    with recommendation_col:
        with st.container(border=True):
            st.markdown('<div class="section-label">个性化推荐</div>', unsafe_allow_html=True)
            recommendations = st.session_state.get("recommendation_results", {}).get("multifactor")
            if recommendations is None or recommendations.empty:
                st.markdown(
                    '<div class="recommend-card"><div class="detail-title">等待学生画像</div><div class="muted" style="font-size:.8rem;line-height:1.7;margin-top:.45rem">进入“个性化推荐”填写目标岗位、技能和期望城市后，这里显示真实推荐结果。</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                _display_recommendations(recommendations.head(1), "multifactor")


def _reset_search_widgets() -> None:
    defaults = {
        "search_keyword": "",
        "search_city": "全部城市",
        "search_work_type": "全部",
        "search_experience": "全部",
        "search_education": "全部",
        "search_industry": "全部行业",
        "search_company_nature": "全部",
        "search_salary_min": "",
        "search_salary_max": "",
        "search_page": 1,
        "search_page_size": 10,
    }
    st.session_state.update(defaults)
    st.session_state.pop("search_results", None)


def _render_search(jobs: pd.DataFrame) -> None:
    _page_header("岗位检索", jobs)
    if "search_page" not in st.session_state:
        st.session_state["search_page"] = 1
    if "search_page_size" not in st.session_state:
        st.session_state["search_page_size"] = 10
    with st.form("search_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            keyword = st.text_input("关键词", placeholder="岗位名称、公司、技能或描述", key="search_keyword")
            city_value = st.selectbox("城市", _filter_options(jobs, "city", "全部城市"), key="search_city")
            work_type_value = st.selectbox("工作方式", _filter_options(jobs, "work_type"), key="search_work_type")
        with col2:
            experience_value = st.selectbox("经验要求", _filter_options(jobs, "experience"), key="search_experience")
            education_value = st.selectbox("学历", _filter_options(jobs, "education"), key="search_education")
            industry_value = st.selectbox("行业", _filter_options(jobs, "industry", "全部行业"), key="search_industry")
        with col3:
            company_nature_value = st.selectbox("公司性质", _filter_options(jobs, "company_nature"), key="search_company_nature")
            salary_min_value = st.text_input("薪资下限（元/月）", placeholder="最低薪资，如：10000", key="search_salary_min")
            salary_max_value = st.text_input("薪资上限（元/月）", placeholder="最高薪资，如：50000", key="search_salary_max")
        action1, action2, _ = st.columns([1, 1, 7])
        submitted = action1.form_submit_button("搜索", type="primary", use_container_width=True)
        reset = action2.form_submit_button("重置", on_click=_reset_search_widgets, use_container_width=True)
    if submitted:
        try:
            st.session_state["search_results"] = filter_jobs(jobs, {
                "keyword": keyword,
                "city": "" if city_value == "全部城市" else city_value,
                "work_type": "" if work_type_value == "全部" else work_type_value,
                "experience": "" if experience_value == "全部" else experience_value,
                "education": "" if education_value == "全部" else education_value,
                "industry": "" if industry_value == "全部行业" else industry_value,
                "company_nature": "" if company_nature_value == "全部" else company_nature_value,
                "salary_min": _parse_salary(salary_min_value, "薪资下限"),
                "salary_max": _parse_salary(salary_max_value, "薪资上限"),
            })
            st.session_state["search_page"] = 1
        except ValueError as exc:
            st.error(str(exc)); return
    if reset:
        st.session_state.pop("search_results", None)
    result = st.session_state.get("search_results", jobs)
    if result.empty:
        st.warning("没有找到符合条件的岗位，请放宽筛选条件。"); return
    st.markdown(f'<div class="section-label">共找到 {len(result):,} 个岗位</div>', unsafe_allow_html=True)
    page_meta = paginate_jobs(
        result,
        page=int(st.session_state.get("search_page", 1)),
        page_size=int(st.session_state.get("search_page_size", 10)),
    )
    page_result = page_meta["items"]
    st.session_state["search_page"] = int(page_meta["page"])
    table_col, detail_col = st.columns([2.35, 1], gap="small")
    display_columns = [column for column in ["title", "company", "city", "salary_text", "education", "experience", "skills"] if column in result.columns]
    labels = {"title": "职位名称", "company": "公司名称", "city": "城市", "salary_text": "薪资范围", "education": "学历", "experience": "经验", "skills": "技能要求"}
    with table_col:
        st.dataframe(page_result[display_columns].rename(columns=labels), use_container_width=True, hide_index=True, height=510)
        _render_pagination(page_meta, "search")
    with detail_col:
        selected_index = st.selectbox(
            "选择岗位查看详情",
            range(len(page_result)),
            format_func=lambda index: f"{_safe(page_result.iloc[index].get('title'))} · {_safe(page_result.iloc[index].get('company'))}",
            key=f"search_selected_index_{int(page_meta['page'])}",
        )
        row = page_result.iloc[selected_index]
        st.markdown(
            f"""<div class="recommend-card"><div class="section-label">岗位详情</div><div class="detail-title">{_safe(row.get('title'))}</div>
            <div class="detail-company">{_safe(row.get('company'))}</div><div class="salary">{_safe(row.get('salary_text'))}</div>
            <div class="meta-grid"><div>城市<br><strong>{_safe(row.get('city'))}</strong></div><div>工作方式<br><strong>{_safe(row.get('work_type'))}</strong></div>
            <div>学历要求<br><strong>{_safe(row.get('education'))}</strong></div><div>经验要求<br><strong>{_safe(row.get('experience'))}</strong></div></div>
            <div class="muted" style="font-size:.78rem">技能要求</div><div>{_chips(row.get('skills')) or '<span class="muted">暂无</span>'}</div>
            <hr style="border:0;border-top:1px solid var(--border);margin:.8rem 0"><div style="font-size:.8rem;line-height:1.65"><strong>职位描述</strong><br>{_safe(row.get('description'), '暂无职位描述')[:360]}</div>
            <div style="font-size:.8rem;margin-top:.65rem"><strong>福利待遇</strong><br>{_chips(row.get('benefits')) or '<span class="muted">暂无</span>'}</div>
            <div class="muted" style="font-size:.75rem;margin-top:.7rem">数据来源：{_safe(row.get('source'))}</div></div>""",
            unsafe_allow_html=True,
        )
        st.download_button("下载筛选结果 CSV", result.to_csv(index=False).encode("utf-8-sig"), file_name="filtered_jobs.csv", mime="text/csv", use_container_width=True)


def _render_analysis(jobs: pd.DataFrame) -> None:
    _page_header("分析洞察", jobs)
    chart_col, model_col = st.columns([1.35, 0.65], gap="medium")
    with chart_col:
        with st.container(border=True):
            st.markdown('<div class="section-label">薪资分布</div>', unsafe_allow_html=True)
            try:
                dist_df = _compact_salary_distribution(pd.DataFrame(salary_distribution(jobs))).sort_values("min")
                fig = px.bar(dist_df, x="count", y="range", orientation="h", labels={"range": "薪资区间（元/月）", "count": "岗位数量"}, color_discrete_sequence=[COLORS["salary"]])
                st.plotly_chart(_style_figure(fig, 360), use_container_width=True, config={"displayModeBar": False})
            except ValueError as exc: st.warning(str(exc))
    with model_col:
        with st.container(border=True):
            st.markdown('<div class="section-label">薪资预测模型评估</div>', unsafe_allow_html=True)
            try:
                _, metrics = analysis_service.salary_prediction(jobs)
                metric_cols = st.columns(2)
                with metric_cols[0]: _kpi("MAE", f"{metrics['mae']:,.2f}", "元/月", "salary")
                with metric_cols[1]: _kpi("R²", f"{metrics['r2']:.3f}", "拟合优度", "success")
                st.caption("预测岗位平均月薪，依据技能、学历、经验、城市、工作方式、企业性质、企业规模和行业等岗位信息；模型不把薪资字段作为输入。MAE 和 R² 来自独立测试集，反映样本关联，不代表因果关系。")
            except Exception as exc: st.warning(f"薪资预测不可用：{exc}")

    with st.container(border=True):
        st.markdown('<div class="section-label">薪资影响因素</div>', unsafe_allow_html=True)
        try:
            salary_factors = analysis_service.salary_factor_analysis(jobs).head(10).rename(
                columns={
                    "factor": "影响因素",
                    "impact_direction": "影响方向",
                    "importance": "重要性",
                    "description": "说明",
                }
            )
            factor_names = {
                "education": "学历",
                "experience": "经验",
                "city": "城市",
                "work_type": "工作方式",
                "company_nature": "公司性质",
                "company_size": "公司规模",
                "industry": "行业",
            }
            for raw_name, display_name in factor_names.items():
                salary_factors["影响因素"] = salary_factors["影响因素"].str.replace(
                    f"{raw_name}-", f"{display_name} · ", regex=False
                )
                salary_factors["说明"] = salary_factors["说明"].str.replace(
                    f"“{raw_name}”", f"“{display_name}”", regex=False
                )
            salary_factors["影响方向"] = salary_factors["影响方向"].replace(
                {"higher": "偏高", "lower": "偏低", "neutral": "接近整体水平"}
            )
            st.dataframe(salary_factors, use_container_width=True, hide_index=True, height=360)
        except Exception as exc: st.warning(f"薪资因素分析不可用：{exc}")

    analysis_category = st.selectbox(
        "分析岗位类别",
        ["全部岗位", *JOB_CATEGORIES],
        key="analysis_category",
        help="按类别统计技能并聚类，避免全量频次被技术岗位标签主导。",
    )
    selected_category = None if analysis_category == "全部岗位" else analysis_category
    category_jobs = jobs
    if selected_category:
        categorized_jobs = add_job_category(jobs)
        category_jobs = jobs.loc[categorized_jobs["job_category"] == selected_category]

    skill_col, cluster_col = st.columns([1.15, 0.85], gap="medium")
    with skill_col:
        with st.container(border=True):
            st.markdown('<div class="section-label">岗位能力需求图谱</div>', unsafe_allow_html=True)
            try:
                freq_df = pd.DataFrame(
                    analysis_service.skill_graph(jobs, category=selected_category)["skill_frequency"][:15],
                    columns=["技能", "出现次数"],
                ).sort_values("出现次数")
                fig = px.bar(freq_df, x="出现次数", y="技能", orientation="h", color_discrete_sequence=[COLORS["primary"]])
                st.plotly_chart(_style_figure(fig, 360), use_container_width=True, config={"displayModeBar": False})
            except Exception as exc: st.warning(f"能力需求图谱不可用：{exc}")
    with cluster_col:
        with st.container(border=True):
            st.markdown('<div class="section-label">岗位聚类</div>', unsafe_allow_html=True)
            try:
                _, summaries = analysis_service.job_cluster(category_jobs)
                for cluster_id, info in list(summaries.items())[:4]:
                    category_skills = info.get("top_skills_by_category", {})
                    skill_text = "；".join(
                        f"{category}：{'、'.join(skills)}"
                        for category, skills in category_skills.items()
                        if skills
                    ) or "、".join(info.get("top_skills", []))
                    st.markdown(f"""<div class="profile-summary"><strong>群组 {html.escape(str(cluster_id))}</strong><div class="meta-grid">
                    <div>岗位数量<br><strong>{_safe(info.get('count'))}</strong></div><div>岗位类别<br><strong>{_safe(info.get('dominant_category'))}</strong></div><div>平均薪资<br><strong class="salary">{_safe(info.get('salary_avg'))}</strong></div>
                    <div>代表城市<br><strong>{_safe(info.get('dominant_city'))}</strong></div><div>高频技能<br><strong>{_safe(skill_text)}</strong></div></div></div>""", unsafe_allow_html=True)
            except Exception as exc: st.warning(f"岗位聚类不可用：{exc}")

    with st.container(border=True):
        st.markdown('<div class="section-label">招聘企业画像</div>', unsafe_allow_html=True)
        try:
            company_profiles = analysis_service.company_profile(jobs).head(10).copy()
            company_profiles["company_size"] = company_profiles["company_size"].map(_display_text)
            company_profiles["company_nature"] = company_profiles["company_nature"].map(_display_text)
            company_profiles["industry"] = company_profiles["industry"].map(_display_text)
            company_profiles["salary_summary"] = company_profiles["salary_summary"].map(_format_salary_summary)
            company_profiles["skill_summary"] = company_profiles["skill_summary"].map(_format_skill_summary)
            company_profiles = company_profiles.rename(
                columns={
                    "company": "公司名称",
                    "company_size": "企业规模",
                    "company_nature": "企业性质",
                    "industry": "所属行业",
                    "salary_summary": "薪资概况（元/月）",
                    "skill_summary": "技能需求（出现次数）",
                }
            )
            st.dataframe(company_profiles, use_container_width=True, hide_index=True, height=360)
        except Exception as exc: st.warning(f"企业画像不可用：{exc}")


def _render_recommendation(jobs: pd.DataFrame) -> None:
    _page_header("个性化推荐", jobs, "推荐结果基于当前岗位数据与学生画像")
    form_col, result_col = st.columns([.78, 1.65], gap="small")
    recommendation_results = st.session_state.setdefault("recommendation_results", {})
    profile_summaries = st.session_state.setdefault("recommendation_profiles", {})
    with form_col:
        with st.container(border=True):
            st.markdown('<div class="section-label">学生画像</div>', unsafe_allow_html=True)
            recommendation_mode = st.radio("推荐模式", ["多因素推荐", "基础 TF-IDF 推荐"], horizontal=True)
            mode = "multifactor" if recommendation_mode == "多因素推荐" else "basic"
            with st.form("profile_form"):
                target_role = st.text_input("目标岗位", placeholder="如：数据分析师")
                col1, col2 = st.columns(2)
                education = col1.text_input("学历", placeholder="本科"); major = col2.text_input("专业", placeholder="数据科学")
                school = col1.text_input("学校", placeholder="某某大学"); preferred_city = col2.text_input("期望城市", placeholder="杭州")
                work_years = col1.number_input("工作年限", min_value=0.0, step=1.0, value=0.0); skills = col2.text_input("已掌握技能", placeholder="Python;SQL")
                work_experience = st.text_area("工作或项目经历", placeholder="简要描述相关经历", height=92)
                expected_salary_min = col1.number_input("期望月薪下限", min_value=0, step=1000, value=0)
                expected_salary_max = col2.number_input("期望月薪上限", min_value=0, step=1000, value=0)
                submitted = st.form_submit_button("生成推荐", type="primary", use_container_width=True)
    if submitted:
        try:
            profile = StudentProfile.from_mapping({"target_role": target_role, "education": education, "major": major, "school": school, "preferred_city": preferred_city, "work_years": work_years or None, "skills": skills, "work_experience": work_experience, "expected_salary_min": expected_salary_min or None, "expected_salary_max": expected_salary_max or None})
            recommendations = analysis_service.recommend_jobs(profile, jobs, top_k=5) if mode == "basic" else analysis_service.recommend_jobs_multifactor(profile, jobs, top_k=5)
            if recommendations.empty:
                recommendation_results.pop(mode, None); profile_summaries.pop(mode, None)
            else:
                recommendation_results[mode] = recommendations; profile_summaries[mode] = profile
        except ValueError as exc: st.error(str(exc))
        except Exception as exc: st.error(f"推荐接口调用失败：{exc}")
    with result_col:
        st.markdown('<div class="section-label">推荐结果</div>', unsafe_allow_html=True)
        current, profile = recommendation_results.get(mode), profile_summaries.get(mode)
        if profile is not None:
            st.markdown(f"""<div class="profile-summary"><strong>当前画像</strong><br><span class="chip">目标岗位：{_safe(profile.target_role)}</span>
            <span class="chip">期望城市：{_safe(profile.preferred_city)}</span><span class="chip">学历：{_safe(profile.education)}</span>{_chips(profile.skills, 'good')}</div>""", unsafe_allow_html=True)
        if current is None or current.empty: st.info("填写学生画像后点击“生成推荐”，结果会保留在当前会话中。")
        else: _display_recommendations(current, mode)


def _display_recommendations(recommendations: pd.DataFrame, mode: str) -> None:
    for rank, (_, row) in enumerate(recommendations.iterrows(), start=1):
        if mode == "basic":
            salary = _safe(row.get("salary_text"), "薪资未注明"); probability = f"{float(row.get('similarity_score', 0)):.1%}"; company_meta = f"城市：{_safe(row.get('city'))}"
        else:
            salary = _safe(row.get("salary_range"), "薪资未注明"); probability = f"{float(row.get('match_probability', 0)):.1%}"
            company_meta = f"公司规模：{_safe(row.get('company_size'))}<br>公司性质：{_safe(row.get('company_nature'))}<br>行业：{_safe(row.get('industry'))}"
        st.markdown(
            f"""<div class="recommend-card"><div class="recommend-grid"><div><div class="detail-title">{rank}　{_safe(row.get('title'))}</div><div class="detail-company">{_safe(row.get('company'))}</div><div class="muted" style="font-size:.78rem;line-height:1.7">{company_meta}</div></div>
            <div><div class="muted" style="font-size:.76rem">薪资区间</div><div class="salary">{salary}</div><div class="muted" style="font-size:.76rem;margin-top:.8rem">匹配概率</div><div class="success" style="font-size:1.25rem">{probability}</div></div>
            <div><div class="success" style="font-size:.76rem">匹配技能</div><div>{_chips(row.get('matched_skills'), 'good') or '<span class="muted">无</span>'}</div><div class="warning" style="font-size:.76rem;margin-top:.6rem">缺失技能</div><div>{_chips(row.get('missing_skills'), 'warn') or '<span class="muted">无</span>'}</div></div>
            <div><div class="success" style="font-size:.76rem">推荐理由</div><div style="font-size:.8rem;line-height:1.7;margin-top:.35rem">{_safe(row.get('reason'))}</div></div></div></div>""",
            unsafe_allow_html=True,
        )


def _render_collection(jobs: pd.DataFrame) -> None:
    _page_header("采集管理", jobs, "按需触发 / 定时批量采集，不代表实时更新")
    try:
        site_service.ensure_default_site(); sites = site_service.list_sites(); tasks = task_service.list_tasks()
    except Exception as exc:
        st.error(f"采集服务初始化失败：{exc}"); return
    successful = [task for task in tasks if task.status == "success"]
    recent_success = (successful[-1].finished_at or successful[-1].started_at) if successful else "暂无"
    summary_cols = st.columns(3)
    with summary_cols[0]: _kpi("已启用站点", str(sum(site.enabled for site in sites)), f"共配置 {len(sites)} 个站点", "success")
    with summary_cols[1]: _kpi("待处理任务", str(sum(task.status in {"pending", "running"} for task in tasks)), f"任务记录 {len(tasks)} 条", "salary")
    with summary_cols[2]: _kpi("最近成功采集", recent_success, "按任务记录显示")
    st.markdown('<div class="section-label" style="margin-top:1rem">网站配置</div>', unsafe_allow_html=True)
    if not sites: st.info("暂无网站配置。")
    for site in sites:
        state_label = "已启用" if site.enabled else "已停用"
        st.markdown(f"""<div class="site-card"><div><strong>{_safe(site.site_name)}</strong><span class="status-pill">{state_label}</span></div><div class="site-grid">
        <div>Base URL<strong>{_safe(site.base_url)}</strong></div><div>关键词<strong>{_safe('、'.join(site.keywords), '未设置')}</strong></div><div>城市<strong>{_safe('、'.join(site.cities), '未设置')}</strong></div>
        <div>采集策略<strong>{_safe(site.crawl_strategy.upper())}</strong></div><div>最大深度<strong>{site.max_depth}</strong></div><div>频率<strong>{_safe(site.frequency)}</strong></div></div></div>""", unsafe_allow_html=True)
        actions = st.columns([1.25, .75, .75, 6])
        if actions[0].button("触发采集任务", key=f"trigger_{site.site_id}", type="primary", use_container_width=True):
            try: task_service.trigger_task(site.site_id); st.rerun()
            except Exception as exc: st.error(str(exc))
        action_label = "停用" if site.enabled else "启用"
        if actions[1].button(action_label, key=f"toggle_{site.site_id}", use_container_width=True):
            try: site_service.set_site_enabled(site.site_id, not site.enabled); st.rerun()
            except Exception as exc: st.error(str(exc))
        if actions[2].button("删除", key=f"remove_{site.site_id}", use_container_width=True):
            try: site_service.remove_site(site.site_id); st.rerun()
            except Exception as exc: st.error(str(exc))
    form_cols = st.columns(2, gap="small")
    with form_cols[0]:
        st.markdown('<div class="section-label">修改网站配置</div>', unsafe_allow_html=True)
        site_ids = [site.site_id for site in site_service.list_sites()]
        if site_ids:
            edit_site_id = st.selectbox("选择要修改的站点", site_ids, key="edit_site_select"); edit_site = site_service.get_site(edit_site_id)
            with st.form("edit_site_form"):
                edit_site_name = st.text_input("站点名称", value=edit_site.site_name); edit_base_url = st.text_input("Base URL", value=edit_site.base_url)
                edit_keywords = st.text_input("关键词", value=",".join(edit_site.keywords)); edit_cities = st.text_input("城市", value=",".join(edit_site.cities))
                col1, col2 = st.columns(2)
                edit_strategy = col1.selectbox("采集策略", ["bfs", "dfs"], index=0 if edit_site.crawl_strategy == "bfs" else 1)
                frequencies = ["once", "daily", "twice_daily"]; edit_frequency = col2.selectbox("频率", frequencies, index=frequencies.index(edit_site.frequency))
                edit_max_depth = col1.number_input("最大深度", min_value=0, step=1, value=edit_site.max_depth); edit_start_at = col2.text_input("开始时间", value=edit_site.start_at)
                edit_submitted = st.form_submit_button("保存修改", type="primary", use_container_width=True)
            if edit_submitted:
                try:
                    site_service.update_site(edit_site_id, {"site_name": edit_site_name, "base_url": edit_base_url, "keywords": edit_keywords, "cities": edit_cities, "crawl_strategy": edit_strategy, "frequency": edit_frequency, "max_depth": edit_max_depth, "start_at": edit_start_at}); st.success("网站配置已保存。")
                except Exception as exc: st.error(str(exc))
        else: st.info("请先新增网站配置。")
    with form_cols[1]:
        st.markdown('<div class="section-label">新增网站配置</div>', unsafe_allow_html=True)
        with st.form("add_site_form"):
            col1, col2 = st.columns(2)
            new_site_id = col1.text_input("站点 ID", placeholder="如：example_jobs"); new_site_name = col2.text_input("站点名称", placeholder="招聘网站")
            new_base_url = st.text_input("Base URL", placeholder="https://example.com"); new_keywords = st.text_input("关键词", placeholder="逗号分隔"); new_cities = st.text_input("城市", placeholder="逗号分隔")
            new_strategy = col1.selectbox("采集策略", ["bfs", "dfs"], key="new_strategy"); new_frequency = col2.selectbox("频率", ["once", "daily", "twice_daily"], key="new_frequency")
            new_max_depth = col1.number_input("最大深度", min_value=0, step=1, value=1, key="new_depth"); new_start_at = col2.text_input("开始时间", placeholder="2026-09-04T08:00:00", key="new_start")
            add_submitted = st.form_submit_button("新增站点", use_container_width=True)
        if add_submitted:
            try:
                site_service.add_site({"site_id": new_site_id, "site_name": new_site_name, "base_url": new_base_url, "keywords": new_keywords, "cities": new_cities, "crawl_strategy": new_strategy, "start_at": new_start_at, "frequency": new_frequency, "max_depth": new_max_depth}); st.success("网站配置已新增。")
            except Exception as exc: st.error(str(exc))
    st.markdown('<div class="section-label" style="margin-top:1rem">采集任务记录</div>', unsafe_allow_html=True)
    if not tasks: st.info("暂无采集任务记录。")
    else:
        task_df = pd.DataFrame(task.to_dict() for task in tasks).rename(columns={"task_id": "任务 ID", "site_id": "站点", "status": "状态", "started_at": "开始时间", "finished_at": "结束时间", "raw_count": "原始记录数", "parsed_count": "解析成功数", "error_count": "异常数", "error_message": "错误信息"})
        st.dataframe(task_df, use_container_width=True, hide_index=True, height=260)
