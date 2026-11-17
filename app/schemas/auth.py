from datetime import date
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.validation import (
    normalize_phone,
    validate_dob,
    validate_password_strength,
)
from app.models.enums import OtpChannel
from app.schemas.application import (
    EducationEntry,
    ExperienceEntry,
    InternshipEntry,
    ProjectEntry,
)


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str
    password: str
    skills: list[str] = Field(default_factory=list, max_length=50)
    experience: str | None = Field(default=None, max_length=255)
    qualification: str | None = Field(default=None, max_length=255)
    dob: date | None = None
    education: list[EducationEntry] = Field(default_factory=list, max_length=20)
    projects: list[ProjectEntry] = Field(default_factory=list, max_length=20)
    internships: list[InternshipEntry] = Field(default_factory=list, max_length=20)
    experience_entries: list[ExperienceEntry] = Field(
        default_factory=list, max_length=20
    )
    applied_role: str | None = Field(default=None, max_length=150)
    resume_id: UUID | None = None

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, value: list[str]) -> list[str]:
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
    def clean_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("dob")
    @classmethod
    def valid_dob(cls, value: date | None) -> date | None:
        return validate_dob(value)


class Verify2FARequest(BaseModel):
    user_id: UUID
    channel: OtpChannel
    code: str = Field(min_length=5, max_length=8)


class ResendOTPRequest(BaseModel):
    user_id: UUID
    channel: OtpChannel

    @field_validator("channel")
    @classmethod
    def only_messaging_channels(cls, value: OtpChannel) -> OtpChannel:
        if value not in {OtpChannel.email, OtpChannel.whatsapp}:
            raise ValueError("OTP can only be resent for email or whatsapp")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class TotpVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)
