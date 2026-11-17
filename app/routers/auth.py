from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ResendOTPRequest,
    TotpVerifyRequest,
    Verify2FARequest,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=201)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await auth_service.register_user(db, payload)
    return {
        "success": True,
        "message": (
            "Registration successful. Verify your email and WhatsApp to "
            "activate your account."
        ),
        "data": data,
    }


@router.post("/verify-2fa")
async def verify_2fa(
    payload: Verify2FARequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await auth_service.verify_2fa(db, payload)
    if data.get("user_status") == "active":
        message = "Account activated successfully"
    else:
        message = f"{data['channel'].capitalize()} verified successfully"
    return {"success": True, "message": message, "data": data}


@router.post("/resend-otp")
async def resend_otp(
    payload: ResendOTPRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await auth_service.resend_otp(db, payload)
    return {"success": True, "message": "A new code has been sent", "data": data}


@router.post("/login")
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await auth_service.login(db, payload)
    return {"success": True, "message": "Login successful", "data": data}


@router.get("/totp/setup")
async def totp_setup(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await auth_service.setup_totp(db, user)
    return {
        "success": True,
        "message": "Scan the otpauth URI, then verify a code to enable TOTP",
        "data": data,
    }


@router.post("/totp/verify")
async def totp_verify(
    payload: TotpVerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await auth_service.verify_totp_setup(db, user, payload.code)
    return {"success": True, "message": "TOTP enabled", "data": data}


@router.post("/totp/disable")
async def totp_disable(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await auth_service.disable_totp(db, user)
    return {"success": True, "message": "TOTP disabled", "data": data}
