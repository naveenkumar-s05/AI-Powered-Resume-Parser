from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import require_active_user
from app.models.user import User
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/student")
async def student_dashboard(
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await dashboard_service.get_student_dashboard(db, user)
    return {"success": True, "message": data["message"], "data": data}
