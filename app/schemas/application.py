from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _EntryBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class EducationEntry(_EntryBase):
    degree: str = Field(min_length=1, max_length=150)
    institution: str | None = Field(default=None, max_length=200)
    year: str | None = Field(default=None, max_length=50)
    cgpa: str | None = Field(default=None, max_length=50)
    details: str | None = Field(default=None, max_length=1000)


class ProjectEntry(_EntryBase):
    title: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    technologies: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("technologies")
    @classmethod
    def clean_technologies(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in value:
            cleaned = item.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                result.append(cleaned)
        return result


class InternshipEntry(_EntryBase):
    company: str | None = Field(default=None, max_length=150)
    role: str | None = Field(default=None, max_length=150)
    duration: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_one_field(self):
        if not any(self.model_dump().values()):
            raise ValueError("Internship entry cannot be empty")
        return self


class ExperienceEntry(_EntryBase):
    company: str | None = Field(default=None, max_length=150)
    role: str | None = Field(default=None, max_length=150)
    duration: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_one_field(self):
        if not any(self.model_dump().values()):
            raise ValueError("Experience entry cannot be empty")
        return self
