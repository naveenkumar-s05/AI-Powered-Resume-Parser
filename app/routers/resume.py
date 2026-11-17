from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import resume_service

router = APIRouter(tags=["Resume"])


@router.post("/resume/parse")
async def parse_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await resume_service.process_upload(db, file)
    return {
        "success": True,
        "message": "Resume parsed successfully",
        "data": data,
    }
