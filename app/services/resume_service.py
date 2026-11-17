import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.models.enums import ParseStatus
from app.models.resume import UserResume
from app.services import resume_parser

logger = get_logger(__name__)

ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _validate_magic_bytes(suffix: str, content: bytes) -> bool:
    if suffix == ".pdf":
        return content.startswith(b"%PDF")
    if suffix == ".docx":
        return content.startswith(b"PK\x03\x04")
    return False


async def process_upload(db: AsyncSession, file: UploadFile) -> dict:
    filename = file.filename or "resume"
    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_TYPES:
        raise AppException(
            415,
            "UNSUPPORTED_FILE_TYPE",
            "Only PDF and DOCX resumes are supported",
        )

    content = await file.read()
    if not content:
        raise AppException(400, "EMPTY_FILE", "Uploaded file is empty")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise AppException(
            413,
            "FILE_TOO_LARGE",
            f"File exceeds the {settings.max_upload_size_mb} MB limit",
        )

    if not _validate_magic_bytes(suffix, content):
        raise AppException(
            415,
            "INVALID_FILE_CONTENT",
            "File content does not match its extension",
        )

    stored_name = f"{uuid.uuid4().hex}{suffix}"
    stored_path = settings.upload_path / stored_name
    stored_path.write_bytes(content)

    try:
        text = resume_parser.extract_text(stored_path, suffix)
        if not text.strip():
            raise AppException(
                422,
                "NO_TEXT_EXTRACTED",
                "No readable text could be extracted from the resume",
            )
        parsed, warnings = resume_parser.parse_fields(text, filename)
    except AppException:
        stored_path.unlink(missing_ok=True)
        raise
    except Exception as exc:  # noqa: BLE001
        stored_path.unlink(missing_ok=True)
        logger.exception("Resume parsing failed")
        raise AppException(
            422,
            "PARSE_FAILED",
            f"Could not parse the resume: {exc}",
        ) from exc

    resume = UserResume(
        original_filename=filename,
        stored_path=str(stored_path),
        mime_type=ALLOWED_TYPES[suffix],
        size_bytes=len(content),
        extracted_text=text,
        extracted_metadata=parsed,
        parse_status=ParseStatus.parsed,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    return {
        "resume_id": str(resume.id),
        "file_name": filename,
        "parsed": parsed,
        "warnings": warnings,
    }
