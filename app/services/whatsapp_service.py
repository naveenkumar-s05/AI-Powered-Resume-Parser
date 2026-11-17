import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def is_configured() -> bool:
    return bool(settings.whatsapp_phone_number_id and settings.whatsapp_access_token)


async def send_otp_whatsapp(
    phone: str, otp: str, full_name: str | None = None
) -> bool:
    if not is_configured():
        logger.warning(
            "WhatsApp API not configured. WhatsApp OTP for %s is %s (dev fallback)",
            phone,
            otp,
        )
        return False

    to = phone.lstrip("+")
    url = (
        f"{settings.whatsapp_api_url.rstrip('/')}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }

    if settings.whatsapp_otp_template:
        components: list[dict] = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": otp}],
            }
        ]
        if settings.whatsapp_otp_button_index >= 0:
            components.append(
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": str(settings.whatsapp_otp_button_index),
                    "parameters": [{"type": "text", "text": otp}],
                }
            )
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": settings.whatsapp_otp_template,
                "language": {"code": settings.whatsapp_template_lang},
                "components": components,
            },
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {
                "body": f"Your verification code is {otp}. Do not share it with anyone."
            },
        }

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            logger.error(
                "WhatsApp API error %s: %s", response.status_code, response.text
            )
            return False
        logger.info("WhatsApp OTP sent to %s", phone)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send WhatsApp OTP to %s: %s", phone, exc)
        return False
