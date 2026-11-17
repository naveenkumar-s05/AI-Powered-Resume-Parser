from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.jobs import JOB
from app.core.exceptions import (
    AppException,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationAppError,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import OtpChannel, OtpPurpose, OtpStatus, UserStatus
from app.models.resume import UserResume
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ResendOTPRequest,
    Verify2FARequest,
)
from app.services import email_service, otp_service, totp_service, whatsapp_service


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return email
    return f"{local[:1]}***@{domain}"


def _mask_phone(phone: str) -> str:
    if len(phone) <= 6:
        return phone
    return f"{phone[:3]}****{phone[-3:]}"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _dump_entries(entries) -> list[dict]:
    return [entry.model_dump(exclude_none=True) for entry in entries]


def _apply_registration_fields(user: User, payload: RegisterRequest) -> None:
    user.full_name = payload.full_name
    user.email = payload.email
    user.phone = payload.phone
    user.password_hash = hash_password(payload.password)
    user.skills = payload.skills
    user.experience = payload.experience
    user.qualification = payload.qualification
    user.dob = payload.dob
    user.education = _dump_entries(payload.education)
    user.projects = _dump_entries(payload.projects)
    user.internships = _dump_entries(payload.internships)
    user.experience_entries = _dump_entries(payload.experience_entries)
    user.applied_role = payload.applied_role or JOB["title"]
    user.application_status = "submitted"
    user.status = UserStatus.pending
    user.email_verified = False
    user.whatsapp_verified = False


async def register_user(db: AsyncSession, payload: RegisterRequest) -> dict:
    existing = await db.execute(
        select(User).where(
            or_(User.email == payload.email, User.phone == payload.phone)
        )
    )
    existing_user = existing.scalar_one_or_none()
    if existing_user:
        if existing_user.email == payload.email:
            raise ConflictError("Email is already registered", "EMAIL_TAKEN")
        raise ConflictError("Phone number is already registered", "PHONE_TAKEN")

    user = User()
    _apply_registration_fields(user, payload)
    db.add(user)
    await db.flush()

    resume: UserResume | None = None
    if payload.resume_id:
        resume = await db.get(UserResume, payload.resume_id)
        if not resume:
            raise NotFoundError("Resume not found", "RESUME_NOT_FOUND")
        if resume.user_id is not None:
            raise ConflictError(
                "Resume is already linked to another account",
                "RESUME_ALREADY_LINKED",
            )
        resume.user_id = user.id
        metadata = dict(resume.extracted_metadata or {})
        metadata.update(
            {
                "full_name": payload.full_name,
                "email": payload.email,
                "phone": payload.phone,
                "skills": payload.skills,
                "experience": payload.experience,
                "qualification": payload.qualification,
                "dob": payload.dob.isoformat() if payload.dob else None,
                "education": _dump_entries(payload.education),
                "projects": _dump_entries(payload.projects),
                "internships": _dump_entries(payload.internships),
                "experience_entries": _dump_entries(payload.experience_entries),
                "applied_role": user.applied_role,
            }
        )
        resume.extracted_metadata = metadata

    _, email_otp = await otp_service.create_challenge(db, user, OtpChannel.email)

    whatsapp_otp: str | None = None
    if settings.whatsapp_verification_required:
        _, whatsapp_otp = await otp_service.create_challenge(
            db, user, OtpChannel.whatsapp
        )

    await db.commit()
    await db.refresh(user)

    email_sent = await email_service.send_otp_email(
        user.email, email_otp or "", user.full_name
    )
    whatsapp_sent = False
    if settings.whatsapp_verification_required:
        whatsapp_sent = await whatsapp_service.send_otp_whatsapp(
            user.phone, whatsapp_otp or "", user.full_name
        )

    warnings: list[str] = []
    if not email_sent:
        warnings.append(
            "Email OTP could not be delivered. Configure SMTP or use resend-otp."
        )
    if settings.whatsapp_verification_required and not whatsapp_sent:
        warnings.append(
            "WhatsApp OTP could not be delivered. Configure the WhatsApp API or use resend-otp."
        )

    required_channels = ["email"]
    challenges = [
        {
            "channel": "email",
            "expires_in": settings.otp_expire_seconds,
            "sent_to": _mask_email(user.email),
        }
    ]
    delivery = {"email": email_sent}
    if settings.whatsapp_verification_required:
        required_channels.append("whatsapp")
        challenges.append(
            {
                "channel": "whatsapp",
                "expires_in": settings.otp_expire_seconds,
                "sent_to": _mask_phone(user.phone),
            }
        )
        delivery["whatsapp"] = whatsapp_sent

    return {
        "user_id": str(user.id),
        "status": user.status.value,
        "applied_role": user.applied_role,
        "application_status": user.application_status,
        "verification": {
            "required": required_channels,
            "optional": ["totp"],
            "challenges": challenges,
        },
        "delivery": delivery,
        "warnings": warnings,
    }


async def verify_2fa(db: AsyncSession, payload: Verify2FARequest) -> dict:
    user = await db.get(User, payload.user_id)
    if not user:
        raise NotFoundError("User not found", "USER_NOT_FOUND")
    if user.status == UserStatus.disabled:
        raise ForbiddenError("Account is disabled", "ACCOUNT_DISABLED")

    if payload.channel == OtpChannel.totp:
        if not user.totp_enabled or not user.totp_secret_encrypted:
            raise ValidationAppError(
                "TOTP is not enabled for this account", "TOTP_NOT_ENABLED"
            )
        secret = totp_service.decrypt_secret(user.totp_secret_encrypted)
        if not totp_service.verify_code(secret, payload.code):
            raise AppException(400, "INVALID_OTP", "Incorrect authenticator code")

        challenge, _ = await otp_service.create_challenge(
            db, user, OtpChannel.totp, OtpPurpose.totp_enrollment, invalidate=False
        )
        challenge.status = OtpStatus.verified
        challenge.verified_at = datetime.now(timezone.utc)
        await db.commit()
        verified_channel = OtpChannel.totp.value
    else:
        challenge = await otp_service.get_pending_challenge(
            db, user.id, payload.channel
        )
        if not challenge:
            raise NotFoundError(
                "No active verification challenge for this channel",
                "NO_ACTIVE_CHALLENGE",
            )
        try:
            otp_service.verify_challenge(challenge, payload.code)
        except AppException:
            await db.commit()
            raise

        if payload.channel == OtpChannel.email:
            user.email_verified = True
        elif payload.channel == OtpChannel.whatsapp:
            user.whatsapp_verified = True

        await db.commit()
        verified_channel = payload.channel.value

    whatsapp_verified = (
        user.whatsapp_verified or not settings.whatsapp_verification_required
    )
    if user.email_verified and whatsapp_verified:
        user.status = UserStatus.active
        if user.application_status == "submitted":
            user.application_status = "under_review"
        await db.commit()
    await db.refresh(user)

    if user.status == UserStatus.active:
        token, expires_in = create_access_token(
            str(user.id), {"email": user.email}
        )
        return {
            "channel": verified_channel,
            "verified": True,
            "user_status": user.status.value,
            "remaining_channels": [],
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "redirect_url": "/dashboard/student",
        }

    remaining: list[str] = []
    if not user.email_verified:
        remaining.append("email")
    if settings.whatsapp_verification_required and not user.whatsapp_verified:
        remaining.append("whatsapp")

    return {
        "channel": verified_channel,
        "verified": True,
        "user_status": user.status.value,
        "remaining_channels": remaining,
        "access_token": None,
        "token_type": None,
        "expires_in": None,
    }


async def resend_otp(db: AsyncSession, payload: ResendOTPRequest) -> dict:
    user = await db.get(User, payload.user_id)
    if not user:
        raise NotFoundError("User not found", "USER_NOT_FOUND")
    if user.status == UserStatus.active:
        raise ValidationAppError("Account is already active", "ACCOUNT_ALREADY_ACTIVE")
    if (
        payload.channel == OtpChannel.whatsapp
        and not settings.whatsapp_verification_required
    ):
        raise ValidationAppError(
            "WhatsApp verification is disabled",
            "WHATSAPP_VERIFICATION_DISABLED",
        )
    if payload.channel == OtpChannel.email and user.email_verified:
        raise ValidationAppError("Email is already verified", "EMAIL_ALREADY_VERIFIED")
    if payload.channel == OtpChannel.whatsapp and user.whatsapp_verified:
        raise ValidationAppError(
            "WhatsApp is already verified", "WHATSAPP_ALREADY_VERIFIED"
        )

    existing = await otp_service.get_pending_challenge(db, user.id, payload.channel)
    resend_count = 1
    if existing:
        remaining = otp_service.resend_cooldown_remaining(existing)
        if remaining > 0:
            raise AppException(
                429,
                "RESEND_COOLDOWN",
                f"Please wait {remaining} second(s) before requesting a new code",
            )
        if existing.resend_count >= 5:
            raise AppException(
                429,
                "RESEND_LIMIT",
                "Resend limit reached. Please try again later",
            )
        resend_count = existing.resend_count + 1

    _, otp = await otp_service.create_challenge(
        db, user, payload.channel, resend_count=resend_count
    )
    await db.commit()

    if payload.channel == OtpChannel.email:
        sent = await email_service.send_otp_email(user.email, otp or "", user.full_name)
        sent_to = _mask_email(user.email)
    else:
        sent = await whatsapp_service.send_otp_whatsapp(
            user.phone, otp or "", user.full_name
        )
        sent_to = _mask_phone(user.phone)

    return {
        "channel": payload.channel.value,
        "expires_in": settings.otp_expire_seconds,
        "sent_to": sent_to,
        "delivery": sent,
        "resend_count": resend_count,
    }


async def login(db: AsyncSession, payload: LoginRequest) -> dict:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password", "INVALID_CREDENTIALS")
    if user.status != UserStatus.active:
        raise ForbiddenError(
            "Account is not active. Complete verification first",
            "ACCOUNT_INACTIVE",
        )

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    token, expires_in = create_access_token(str(user.id), {"email": user.email})
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "redirect_url": "/dashboard/student",
        "user": {
            "id": str(user.id),
            "full_name": user.full_name,
            "email": user.email,
            "status": user.status.value,
        },
    }


async def setup_totp(db: AsyncSession, user: User) -> dict:
    if user.totp_enabled:
        raise ConflictError("TOTP is already enabled", "TOTP_ALREADY_ENABLED")
    secret = totp_service.generate_secret()
    user.totp_secret_encrypted = totp_service.encrypt_secret(secret)
    await db.commit()
    return {
        "secret": secret,
        "otpauth_uri": totp_service.provisioning_uri(secret, user.email),
        "note": "Scan the URI in an authenticator app, then verify a code to enable TOTP.",
    }


async def verify_totp_setup(db: AsyncSession, user: User, code: str) -> dict:
    if not user.totp_secret_encrypted:
        raise ValidationAppError("Run TOTP setup first", "TOTP_NOT_SETUP")
    secret = totp_service.decrypt_secret(user.totp_secret_encrypted)
    if not totp_service.verify_code(secret, code):
        raise AppException(400, "INVALID_OTP", "Incorrect authenticator code")
    user.totp_enabled = True
    await db.commit()
    return {"totp_enabled": True}


async def disable_totp(db: AsyncSession, user: User) -> dict:
    user.totp_enabled = False
    user.totp_secret_encrypted = None
    await db.commit()
    return {"totp_enabled": False}
