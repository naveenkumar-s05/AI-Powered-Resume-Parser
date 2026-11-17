from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import JOB
from app.models.user import User


async def get_student_dashboard(db: AsyncSession, user: User) -> dict:
    return {
        "id": str(user.id),
        "user_state": user.status.value,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "applied_role": user.applied_role,
        "application_status": user.application_status,
        "job": {
            "company": JOB["company"],
            "title": JOB["title"],
            "location": JOB["location"],
            "type": JOB["type"],
        },
        "dob": user.dob.isoformat() if user.dob else None,
        "skills": user.skills or [],
        "experience": user.experience,
        "qualification": user.qualification,
        "education": user.education or [],
        "projects": user.projects or [],
        "internships": user.internships or [],
        "experience_entries": user.experience_entries or [],
        "redirect_url": "/dashboard/student",
        "message": "Your application has been submitted",
    }
