from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.core.validation import normalize_phone, validate_dob
from app.schemas.application import (
    EducationEntry,
    ExperienceEntry,
    InternshipEntry,
    ProjectEntry,
)


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = None
    skills: list[str] | None = Field(default=None, max_length=50)
    experience: str | None = Field(default=None, max_length=255)
    qualification: str | None = Field(default=None, max_length=255)
    dob: date | None = None
    education: list[EducationEntry] | None = Field(default=None, max_length=20)
    projects: list[ProjectEntry] | None = Field(default=None, max_length=20)
    internships: list[InternshipEntry] | None = Field(default=None, max_length=20)
    experience_entries: list[ExperienceEntry] | None = Field(
        default=None, max_length=20
    )

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_phone(value)

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        seen: set[str] = set()
        result: list[str] = []
        for skill in value:
            cleaned = skill.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                result.append(cleaned)
        return result

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.split())

    @field_validator("dob")
    @classmethod
    def valid_dob(cls, value: date | None) -> date | None:
        return validate_dob(value)
