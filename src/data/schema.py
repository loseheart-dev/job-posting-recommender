from dataclasses import dataclass
from typing import Mapping


JOB_COLUMNS = (
    "job_id",
    "title",
    "company",
    "city",
    "work_type",
    "experience",
    "education",
    "skills",
    "description",
    "salary_min",
    "salary_max",
    "salary_avg",
    "source",
)

REQUIRED_JOB_COLUMNS = ("job_id", "title", "skills", "salary_min", "salary_max", "salary_avg")
FILTER_KEYS = ("keyword", "city", "work_type", "experience", "salary_min", "salary_max")
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
    """One canonical row from the cleaned job table."""

    job_id: str
    title: str
    skills: str
    company: str = ""
    city: str = ""
    work_type: str = ""
    experience: str = ""
    education: str = ""
    description: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    salary_avg: float | None = None
    source: str = ""

    def to_dict(self) -> dict[str, object]:
        return {column: getattr(self, column) for column in JOB_COLUMNS}


@dataclass(frozen=True, slots=True)
class StudentProfile:
    """Input contract shared by the recommendation algorithm and page."""

    target_role: str = ""
    skills: tuple[str, ...] = ()
    preferred_city: str = ""
    experience: str = ""
    expected_salary_min: float | None = None
    expected_salary_max: float | None = None

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "StudentProfile":
        raw_skills = values.get("skills", ()) or ()
        if isinstance(raw_skills, str):
            skills = tuple(skill.strip() for skill in raw_skills.split(";") if skill.strip())
        else:
            skills = tuple(str(skill).strip() for skill in raw_skills if str(skill).strip())
        return cls(
            target_role=str(values.get("target_role", "") or ""),
            skills=skills,
            preferred_city=str(values.get("preferred_city", "") or ""),
            experience=str(values.get("experience", "") or ""),
            expected_salary_min=values.get("expected_salary_min"),
            expected_salary_max=values.get("expected_salary_max"),
        )
