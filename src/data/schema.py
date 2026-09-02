from dataclasses import dataclass
from typing import Mapping


# 与《docs/接口约定.md》第 2 节“岗位数据表 data/processed/jobs.csv”保持一致。
JOB_COLUMNS = (
    "job_id",
    "title",
    "company",
    "company_intro",
    "company_size",
    "company_nature",
    "industry",
    "city",
    "work_type",
    "experience",
    "education",
    "skills",
    "description",
    "benefits",
    "salary_text",
    "salary_min",
    "salary_max",
    "salary_avg",
    "source",
    "source_url",
    "crawled_at",
)

# 接口约定第 2 节中“必填=是”的字段。
REQUIRED_JOB_COLUMNS = ("job_id", "title", "company", "skills", "salary_min", "salary_max", "salary_avg")
# 接口约定第 5 节“服务层接口”允许的筛选键。
FILTER_KEYS = (
    "keyword",
    "city",
    "work_type",
    "experience",
    "education",
    "industry",
    "company_nature",
    "salary_min",
    "salary_max",
)
CLUSTER_OUTPUT_COLUMNS = (*JOB_COLUMNS, "cluster_id")
SALARY_OUTPUT_COLUMNS = (*JOB_COLUMNS, "predicted_salary")
SALARY_METRIC_KEYS = ("mae", "r2")
RECOMMENDATION_COLUMNS = (
    "job_id",
    "title",
    "company",
    "city",
    "similarity_score",
    "matched_skills",
    "missing_skills",
    "reason",
)


@dataclass(frozen=True, slots=True)
class JobRecord:
    """One canonical row from the cleaned job table (aligned with JOB_COLUMNS)."""

    job_id: str
    title: str
    company: str = ""
    company_intro: str = ""
    company_size: str = ""
    company_nature: str = ""
    industry: str = ""
    city: str = ""
    work_type: str = ""
    experience: str = ""
    education: str = ""
    skills: str = ""
    description: str = ""
    benefits: str = ""
    salary_text: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    salary_avg: float | None = None
    source: str = ""
    source_url: str = ""
    crawled_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {column: getattr(self, column) for column in JOB_COLUMNS}


@dataclass(frozen=True, slots=True)
class StudentProfile:
    """Input contract shared by the recommendation algorithm and page.

    Field names follow《docs/接口约定.md》第 3 节“学生画像”。
    """

    target_role: str = ""
    education: str = ""
    major: str = ""
    school: str = ""
    skills: tuple[str, ...] = ()
    preferred_city: str = ""
    work_years: float | None = None
    work_experience: str = ""
    expected_salary_min: float | None = None
    expected_salary_max: float | None = None

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "StudentProfile":
        raw_skills = values.get("skills", ()) or ()
        if isinstance(raw_skills, str):
            skills = tuple(skill.strip() for skill in raw_skills.split(";") if skill.strip())
        else:
            skills = tuple(str(skill).strip() for skill in raw_skills if str(skill).strip())

        def optional_float(value: object) -> float | None:
            if value in (None, ""):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                raise ValueError(f"字段需要可转换为 float 的值，实际为: {value!r}")

        return cls(
            target_role=str(values.get("target_role", "") or ""),
            education=str(values.get("education", "") or ""),
            major=str(values.get("major", "") or ""),
            school=str(values.get("school", "") or ""),
            skills=skills,
            preferred_city=str(values.get("preferred_city", "") or ""),
            work_years=optional_float(values.get("work_years")),
            work_experience=str(values.get("work_experience", "") or ""),
            expected_salary_min=optional_float(values.get("expected_salary_min")),
            expected_salary_max=optional_float(values.get("expected_salary_max")),
        )
