from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import require_active_user
from app.models.user import User
from app.schemas.profile import ProfileUpdateRequest
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("")
async def get_profile(
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await profile_service.get_profile(db, user)
    return {"success": True, "message": "Profile fetched", "data": data}


@router.patch("")
async def update_profile(
    payload: ProfileUpdateRequest,
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await profile_service.update_profile(db, user, payload)
    return {"success": True, "message": "Profile updated", "data": data}
