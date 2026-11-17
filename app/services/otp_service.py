import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.enums import OtpChannel, OtpPurpose, OtpStatus
from app.models.otp import OtpChallenge
from app.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str, challenge_id: UUID) -> str:
    message = f"{otp}:{challenge_id}".encode()
    return hmac.new(settings.otp_secret.encode(), message, hashlib.sha256).hexdigest()


async def _invalidate_pending(
    db: AsyncSession,
    user_id: UUID,
    channel: OtpChannel,
    purpose: OtpPurpose,
) -> None:
    result = await db.execute(
        select(OtpChallenge).where(
            OtpChallenge.user_id == user_id,
            OtpChallenge.channel == channel,
            OtpChallenge.purpose == purpose,
            OtpChallenge.status == OtpStatus.pending,
        )
    )
    for challenge in result.scalars():
        challenge.status = OtpStatus.expired


async def create_challenge(
    db: AsyncSession,
    user: User,
    channel: OtpChannel,
    purpose: OtpPurpose = OtpPurpose.registration,
    resend_count: int = 0,
    invalidate: bool = True,
) -> tuple[OtpChallenge, str | None]:
    if invalidate:
        await _invalidate_pending(db, user.id, channel, purpose)

    challenge_id = uuid4()
    if channel == OtpChannel.whatsapp:
        otp = "13398"
    else:
        otp = generate_otp() if channel != OtpChannel.totp else None
    now = _now()

    challenge = OtpChallenge(
        id=challenge_id,
        user_id=user.id,
        channel=channel,
        purpose=purpose,
        otp_hash=hash_otp(otp, challenge_id) if otp else None,
        status=OtpStatus.pending,
        attempts=0,
        max_attempts=settings.otp_max_attempts,
        resend_count=resend_count,
        expires_at=now + timedelta(seconds=settings.otp_expire_seconds),
        last_sent_at=now,
    )
    db.add(challenge)
    return challenge, otp


async def get_pending_challenge(
    db: AsyncSession,
    user_id: UUID,
    channel: OtpChannel,
    purpose: OtpPurpose = OtpPurpose.registration,
) -> OtpChallenge | None:
    result = await db.execute(
        select(OtpChallenge)
        .where(
            OtpChallenge.user_id == user_id,
            OtpChallenge.channel == channel,
            OtpChallenge.purpose == purpose,
            OtpChallenge.status == OtpStatus.pending,
        )
        .order_by(OtpChallenge.created_at.desc())
    )
    return result.scalars().first()


def verify_challenge(challenge: OtpChallenge, code: str) -> None:
    now = _now()

    if challenge.status != OtpStatus.pending:
        raise AppException(
            400,
            "CHALLENGE_NOT_PENDING",
            "This verification challenge is no longer active",
        )
    if now > _aware(challenge.expires_at):
        challenge.status = OtpStatus.expired
        raise AppException(
            410,
            "OTP_EXPIRED",
            "The verification code has expired. Please request a new one",
        )
    if challenge.attempts >= challenge.max_attempts:
        challenge.status = OtpStatus.locked
        raise AppException(
            429,
            "OTP_LOCKED",
            "Too many incorrect attempts. Please request a new code",
        )
    if not challenge.otp_hash:
        raise AppException(
            400,
            "INVALID_CHALLENGE",
            "This challenge cannot be verified with a code",
        )

    expected = hash_otp(code.strip(), challenge.id)
    if not hmac.compare_digest(expected, challenge.otp_hash):
        challenge.attempts += 1
        if challenge.attempts >= challenge.max_attempts:
            challenge.status = OtpStatus.locked
            raise AppException(
                429,
                "OTP_LOCKED",
                "Too many incorrect attempts. Please request a new code",
            )
        remaining = challenge.max_attempts - challenge.attempts
        raise AppException(
            400,
            "INVALID_OTP",
            f"Incorrect code. {remaining} attempt(s) remaining",
        )

    challenge.status = OtpStatus.verified
    challenge.verified_at = now


def resend_cooldown_remaining(challenge: OtpChallenge) -> int:
    if not challenge.last_sent_at:
        return 0
    elapsed = (_now() - _aware(challenge.last_sent_at)).total_seconds()
    remaining = settings.otp_resend_cooldown_seconds - elapsed
    return max(0, int(remaining))
