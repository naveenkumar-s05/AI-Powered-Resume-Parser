from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError
from app.models.resume import UserResume
from app.models.user import User
from app.schemas.profile import ProfileUpdateRequest


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


async def _latest_resume(db: AsyncSession, user_id) -> UserResume | None:
    result = await db.execute(
        select(UserResume)
        .where(UserResume.user_id == user_id)
        .order_by(UserResume.created_at.desc())
    )
    return result.scalars().first()


async def get_profile(db: AsyncSession, user: User) -> dict:
    resume = await _latest_resume(db, user.id)
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "status": user.status.value,
        "email_verified": user.email_verified,
        "whatsapp_verified": user.whatsapp_verified,
        "whatsapp_verification_required": settings.whatsapp_verification_required,
        "totp_enabled": user.totp_enabled,
        "skills": user.skills or [],
        "experience": user.experience,
        "qualification": user.qualification,
        "dob": user.dob.isoformat() if user.dob else None,
        "education": user.education or [],
        "projects": user.projects or [],
        "internships": user.internships or [],
        "experience_entries": user.experience_entries or [],
        "applied_role": user.applied_role,
        "application_status": user.application_status,
        "resume": (
            {
                "file_name": resume.original_filename,
                "parsed_at": _iso(resume.created_at),
            }
            if resume
            else None
        ),
        "created_at": _iso(user.created_at),
        "updated_at": _iso(user.updated_at),
    }


async def update_profile(
    db: AsyncSession, user: User, payload: ProfileUpdateRequest
) -> dict:
    data = payload.model_dump(exclude_unset=True)

    if data.get("full_name") is not None:
        user.full_name = data["full_name"]

    if data.get("phone") is not None and data["phone"] != user.phone:
        existing = await db.execute(
            select(User).where(User.phone == data["phone"], User.id != user.id)
        )
        if existing.scalar_one_or_none():
            raise ConflictError("Phone number is already in use", "PHONE_TAKEN")
        user.phone = data["phone"]

    if data.get("skills") is not None:
        user.skills = data["skills"]
    if "experience" in data:
        user.experience = data["experience"]
    if "qualification" in data:
        user.qualification = data["qualification"]
    if "dob" in data:
        user.dob = data["dob"]
    if "education" in data:
        user.education = data["education"] or []
    if "projects" in data:
        user.projects = data["projects"] or []
    if "internships" in data:
        user.internships = data["internships"] or []
    if "experience_entries" in data:
        user.experience_entries = data["experience_entries"] or []

    resume = await _latest_resume(db, user.id)
    if resume is not None:
        metadata = dict(resume.extracted_metadata or {})
        metadata.update(
            {
                "full_name": user.full_name,
                "phone": user.phone,
                "skills": user.skills or [],
                "experience": user.experience,
                "qualification": user.qualification,
                "dob": user.dob.isoformat() if user.dob else None,
                "education": user.education or [],
                "projects": user.projects or [],
                "internships": user.internships or [],
                "experience_entries": user.experience_entries or [],
                "applied_role": user.applied_role,
            }
        )
        resume.extracted_metadata = metadata

    await db.commit()
    await db.refresh(user)
    return await get_profile(db, user)
