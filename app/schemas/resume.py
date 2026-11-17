from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.application import (
    EducationEntry,
    ExperienceEntry,
    InternshipEntry,
    ProjectEntry,
)


class ParsedResume(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    dob: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: str | None = None
    qualification: str | None = None
    education: list[EducationEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    internships: list[InternshipEntry] = Field(default_factory=list)
    experience_entries: list[ExperienceEntry] = Field(default_factory=list)


class ResumeParseData(BaseModel):
    resume_id: UUID
    file_name: str
    parsed: ParsedResume
    warnings: list[str] = Field(default_factory=list)
