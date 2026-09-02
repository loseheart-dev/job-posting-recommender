"""多元职位推荐：TF-IDF 文本相似度基线 + 多因素加权推荐。

丁伟哲负责。输出字段见 src/data/schema.py 的 RECOMMENDATION_COLUMNS 与
MULTI_FACTOR_RECOMMENDATION_COLUMNS。

- recommend_jobs：TF-IDF 基线，技能/城市/经验加权，供联调契约使用；
- recommend_jobs_multifactor：多因素推荐，组合分权重之和为 1：
  0.3 文本相似度（target_role） + 0.2 技能命中率 + 0.1 城市 + 0.05 经验
  + 0.05 学历 + 0.05 专业 + 0.1 薪资区间；match_probability 为组合分的
  sigmoid 归一化（0-1）。学校、工作年限、工作经历用于画像说明，不直接
  匹配岗位；岗位表 company_size/company_nature/industry 列缺失时填空。
"""

import math

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.data.schema import JOB_COLUMNS, MULTI_FACTOR_RECOMMENDATION_COLUMNS, RECOMMENDATION_COLUMNS, StudentProfile


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


def _text_similarity(query_text: str, job_texts: list[str]) -> list[float] | None:
    """TF-IDF char_wb 相似度（中文与英文技能均有效）；无可比文本时返回 None。"""
    if not query_text or not any(job_texts):
        return None
    try:
        matrix = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3)).fit_transform([query_text, *job_texts])
    except ValueError:
        return None
    scores = cosine_similarity(matrix[0:1], matrix[1:]).ravel()
    return list(scores) if scores.any() else None


def _skill_set(value: object) -> set[str]:
    return {skill.strip() for skill in str(value).split(";") if skill.strip()}


def _is_missing(value: object) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


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
    排序依据 combo = 文本余弦相似度 + 0.2 * 技能命中率 + 0.1 * 城市匹配
    + 0.05 * 经验匹配；similarity_score 列保留原始余弦相似度。
    """
    if isinstance(profile, dict):
        profile = StudentProfile.from_mapping(profile)
    result = _canonical_jobs(jobs)
    if result.empty or (not profile.target_role and not profile.skills):
        return pd.DataFrame(columns=RECOMMENDATION_COLUMNS)

    similarities = _text_similarity(_profile_text(profile), _job_texts(result))
    if similarities is None:
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
                "_combo": combo,
            }
        )
    rows.sort(key=lambda item: item["_combo"], reverse=True)
    ranked = pd.DataFrame(rows).drop(columns="_combo")[list(RECOMMENDATION_COLUMNS)].head(top_k)
    return ranked.reset_index(drop=True)


def _salary_range(salary_min: object, salary_max: object) -> str:
    if _is_missing(salary_min) or _is_missing(salary_max):
        return ""
    return f"{int(salary_min)}-{int(salary_max)} 元/月"


def _salary_overlap(expected_min: object, expected_max: object, job_min: object, job_max: object) -> bool | None:
    """期望薪资区间与岗位薪资区间是否有交集；期望未填返回 None（中性不加分）。"""
    if _is_missing(expected_min) and _is_missing(expected_max):
        return None
    if _is_missing(job_min) and _is_missing(job_max):
        return False
    low = max(expected_min if not _is_missing(expected_min) else float("-inf"), job_min if not _is_missing(job_min) else float("-inf"))
    high = min(expected_max if not _is_missing(expected_max) else float("inf"), job_max if not _is_missing(job_max) else float("inf"))
    return low <= high


def _build_multifactor_reason(
    profile: StudentProfile,
    similarity: float,
    matched: list[str],
    missing_skills: list[str],
    city_ok: bool,
    experience_ok: bool,
    education_ok: bool,
    major_ok: bool,
    salary_ok: bool | None,
    salary_range: str,
) -> str:
    parts = []
    if profile.target_role:
        parts.append(f"岗位文本相似度 {similarity:.2f}")
    if matched:
        parts.append("匹配技能 " + "、".join(matched))
    if missing_skills:
        parts.append("缺失技能 " + "、".join(missing_skills))
    if city_ok:
        parts.append("城市符合期望")
    if experience_ok:
        parts.append("经验要求匹配")
    if education_ok:
        parts.append(f"学历符合（{profile.education}）")
    if major_ok:
        parts.append(f"专业相关（{profile.major}）")
    if salary_ok is True:
        parts.append(f"薪资区间符合期望（{salary_range}）")
    elif salary_ok is False:
        parts.append("薪资区间低于期望")
    profile_parts = []
    if profile.school:
        profile_parts.append(f"学校{profile.school}")
    if profile.work_years is not None:
        profile_parts.append(f"工作年限{profile.work_years:g}年")
    if profile.work_experience:
        profile_parts.append("含工作经历")
    if profile_parts:
        parts.append("画像：" + "、".join(profile_parts))
    return "；".join(parts)


def recommend_jobs_multifactor(
    profile: StudentProfile | dict[str, object],
    jobs: pd.DataFrame,
    top_k: int = 5,
) -> pd.DataFrame:
    """多因素推荐，返回 MULTI_FACTOR_RECOMMENDATION_COLUMNS 标准列。

    权重：0.3 文本相似度（target_role） + 0.2 技能命中率 + 0.1 城市 + 0.05
    经验 + 0.05 学历 + 0.05 专业 + 0.1 薪资区间。match_probability 为组合分
    sigmoid 归一化（0-1）。空岗位表或画像无有效内容返回空表；缺必要字段
    抛出明确错误；岗位表缺少 company_size/company_nature/industry 时填空。
    """
    if isinstance(profile, dict):
        profile = StudentProfile.from_mapping(profile)
    _canonical_jobs(jobs)  # 仅校验，保留附加列供多因素输出使用
    if jobs.empty or (not profile.target_role and not profile.skills):
        return pd.DataFrame(columns=MULTI_FACTOR_RECOMMENDATION_COLUMNS)

    profile_skills = set(profile.skills)
    similarities = _text_similarity(profile.target_role, _job_texts(jobs)) if profile.target_role else None

    rows: list[dict[str, object]] = []
    for index, row in enumerate(jobs.itertuples(index=False)):
        job_skills = _skill_set(row.skills)
        matched = sorted(profile_skills & job_skills)
        missing_skills = sorted(profile_skills - job_skills)
        hit_ratio = len(matched) / max(len(profile_skills), 1)
        city_ok = bool(profile.preferred_city) and profile.preferred_city.lower() in str(row.city).lower()
        experience_ok = bool(profile.experience) and profile.experience.lower() in str(row.experience).lower()
        education_ok = bool(profile.education) and profile.education.lower() in str(row.education).lower()
        searchable = f"{row.title} {row.skills} {row.description} {row.company}".lower()
        major_ok = bool(profile.major) and profile.major.lower() in searchable
        similarity = float(similarities[index]) if similarities is not None else 0.0
        salary_ok = _salary_overlap(profile.expected_salary_min, profile.expected_salary_max, row.salary_min, row.salary_max)
        combo = (
            0.3 * similarity
            + 0.2 * hit_ratio
            + 0.1 * city_ok
            + 0.05 * experience_ok
            + 0.05 * education_ok
            + 0.05 * major_ok
            + 0.1 * (1.0 if salary_ok else 0.0)
        )
        probability = round(1.0 / (1.0 + math.exp(-combo)), 3)
        salary_range = _salary_range(row.salary_min, row.salary_max)
        rows.append(
            {
                "job_id": row.job_id,
                "title": row.title,
                "company": row.company,
                "company_size": getattr(row, "company_size", "") or "",
                "company_nature": getattr(row, "company_nature", "") or "",
                "industry": getattr(row, "industry", "") or "",
                "salary_range": salary_range,
                "match_probability": probability,
                "matched_skills": ";".join(matched),
                "missing_skills": ";".join(missing_skills),
                "reason": _build_multifactor_reason(
                    profile, similarity, matched, missing_skills,
                    city_ok, experience_ok, education_ok, major_ok, salary_ok, salary_range,
                ),
            }
        )
    rows.sort(key=lambda item: item["match_probability"], reverse=True)
    return pd.DataFrame(rows)[list(MULTI_FACTOR_RECOMMENDATION_COLUMNS)].head(top_k).reset_index(drop=True)
