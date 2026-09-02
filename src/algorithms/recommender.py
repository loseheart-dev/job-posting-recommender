"""多元职位推荐基线：TF-IDF 文本相似度 + 技能/城市/经验匹配。

丁伟哲负责。输出字段见 src/data/schema.py 的 RECOMMENDATION_COLUMNS。
基线版本使用 StudentProfile 现有字段（target_role、skills、preferred_city、
experience、期望薪资）；education/major/school/work_years/work_experience
等画像字段待卢世豪审核接口后扩展（见 todos.md 待确认项）。

排序依据组合分：combo = 文本余弦相似度 + 0.2 * 技能命中率 + 0.1 * 城市匹配
+ 0.05 * 经验匹配。similarity_score 列保留原始余弦相似度。
"""

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.data.schema import JOB_COLUMNS, RECOMMENDATION_COLUMNS, StudentProfile


def _canonical_jobs(jobs: pd.DataFrame) -> pd.DataFrame:
    """校验并裁剪为标准岗位表，不修改输入数据。"""
    missing = [column for column in JOB_COLUMNS if column not in jobs.columns]
    if missing:
        raise ValueError(f"岗位数据缺少必要字段: {', '.join(missing)}")
    return jobs.loc[:, JOB_COLUMNS].copy()


def _job_texts(jobs: pd.DataFrame) -> list[str]:
    """岗位侧 TF-IDF 文本：标题、技能、描述、公司。"""
    columns = ["title", "skills", "description", "company"]
    return [" ".join(str(value) for value in row if str(value).strip()) for row in jobs[columns].fillna("").values.tolist()]


def _profile_text(profile: StudentProfile) -> str:
    """画像侧 TF-IDF 文本：目标岗位、技能、期望城市、经验。"""
    parts = [profile.target_role, *profile.skills, profile.preferred_city, profile.experience]
    return " ".join(part for part in parts if str(part).strip())


def _skill_set(value: object) -> set[str]:
    return {skill.strip() for skill in str(value).split(";") if skill.strip()}


def _build_reason(
    score: float,
    matched: list[str],
    missing: list[str],
    city_ok: bool,
    experience_ok: bool,
) -> str:
    parts = [f"文本相似度 {score:.2f}"]
    if matched:
        parts.append("匹配技能 " + "、".join(matched))
    if missing:
        parts.append("缺失技能 " + "、".join(missing))
    if city_ok:
        parts.append("城市符合期望")
    if experience_ok:
        parts.append("经验要求匹配")
    return "；".join(parts)


def recommend_jobs(
    profile: StudentProfile | dict[str, object],
    jobs: pd.DataFrame,
    top_k: int = 5,
) -> pd.DataFrame:
    """按画像输出 Top-K 推荐岗位，返回 RECOMMENDATION_COLUMNS 标准列。

    正常输入返回按组合分降序的结果；空岗位表或画像无有效内容时返回空表；
    岗位表缺必要字段时抛出明确错误。与 filter_jobs 约定一致，不修改输入数据。
    """
    if isinstance(profile, dict):
        profile = StudentProfile.from_mapping(profile)
    result = _canonical_jobs(jobs)
    if result.empty or (not profile.target_role and not profile.skills):
        return pd.DataFrame(columns=RECOMMENDATION_COLUMNS)

    query_text = _profile_text(profile)
    job_texts = _job_texts(result)
    if not query_text or not any(job_texts):
        return pd.DataFrame(columns=RECOMMENDATION_COLUMNS)

    # char_wb 字符 n-gram：中文岗位标题与英文技能都能产生有效特征
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3))
    matrix = vectorizer.fit_transform([query_text, *job_texts])
    similarities = cosine_similarity(matrix[0:1], matrix[1:]).ravel()
    if not similarities.any():
        return pd.DataFrame(columns=RECOMMENDATION_COLUMNS)

    profile_skills = set(profile.skills)
    city = profile.preferred_city.strip()
    experience = profile.experience.strip()

    rows: list[dict[str, object]] = []
    for row, similarity in zip(result.itertuples(index=False), similarities, strict=False):
        job_skills = _skill_set(row.skills)
        matched = sorted(profile_skills & job_skills)
        missing = sorted(profile_skills - job_skills)
        hit_ratio = len(matched) / max(len(profile_skills), 1)
        city_ok = bool(city) and city.lower() in str(row.city).lower()
        experience_ok = bool(experience) and experience.lower() in str(row.experience).lower()
        combo = float(similarity) + 0.2 * hit_ratio + 0.1 * city_ok + 0.05 * experience_ok
        rows.append(
            {
                "job_id": row.job_id,
                "title": row.title,
                "company": row.company,
                "city": row.city,
                "similarity_score": float(similarity),
                "matched_skills": ";".join(matched),
                "missing_skills": ";".join(missing),
                "reason": _build_reason(float(similarity), matched, missing, city_ok, experience_ok),
            }
        )
        rows[-1]["_combo"] = combo
    rows.sort(key=lambda item: item["_combo"], reverse=True)
    ranked = pd.DataFrame(rows).drop(columns="_combo")[list(RECOMMENDATION_COLUMNS)].head(top_k)
    return ranked.reset_index(drop=True)
