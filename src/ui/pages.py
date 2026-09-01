import pandas as pd
import streamlit as st


def render_home(jobs: pd.DataFrame) -> None:
    """王宇杰负责：实现岗位检索、仪表盘、算法结果和推荐页面。"""
    st.set_page_config(page_title="岗位数据分析与个性化推荐", layout="wide")
    st.title("面向大学生求职的岗位数据分析与个性化推荐系统")
    if jobs.empty:
        st.info("尚未找到清洗后岗位数据，请将 jobs.csv 放入 data/processed/。")
        return
    st.dataframe(jobs, use_container_width=True)
