from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def is_configured() -> bool:
    return bool(settings.smtp_user and settings.smtp_password)


async def send_otp_email(to_email: str, otp: str, full_name: str | None = None) -> bool:
    if not is_configured():
        logger.warning(
            "SMTP not configured. Email OTP for %s is %s (dev fallback)", to_email, otp
        )
        return False

    greeting = f"Hello {full_name}," if full_name else "Hello,"
    minutes = max(1, settings.otp_expire_seconds // 60)

    message = EmailMessage()
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = to_email
    message["Subject"] = "Your verification code"
    message.set_content(
        f"{greeting}\n\n"
        f"Your verification code is {otp}.\n"
        f"It expires in {minutes} minute(s).\n\n"
        "If you did not request this, you can safely ignore this email."
    )

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            start_tls=True,
            username=settings.smtp_user,
            password=settings.smtp_password,
            timeout=20,
        )
        logger.info("Email OTP sent to %s", to_email)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send email OTP to %s: %s", to_email, exc)
        return False
