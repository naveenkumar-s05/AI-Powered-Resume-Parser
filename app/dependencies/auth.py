from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserStatus
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def _user_id_from_token(token: str) -> UUID:
    try:
        payload = decode_access_token(token)
        return UUID(payload["sub"])
    except Exception as exc:  # noqa: BLE001
        raise UnauthorizedError("Invalid or expired token", "INVALID_TOKEN") from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError()
    user_id = _user_id_from_token(credentials.credentials)
    user = await db.get(User, user_id)
    if not user:
        raise UnauthorizedError("User not found", "USER_NOT_FOUND")
    return user


async def require_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if user.status != UserStatus.active:
        raise ForbiddenError(
            "Account is not active. Complete verification first", "ACCOUNT_INACTIVE"
        )
    return user


async def get_user_from_request(request: Request, db: AsyncSession) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        header = request.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            token = header[7:]
    if not token:
        return None
    try:
        user_id = _user_id_from_token(token)
    except UnauthorizedError:
        return None
    return await db.get(User, user_id)
