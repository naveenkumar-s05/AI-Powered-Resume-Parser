import re
from datetime import date


def validate_dob(value: date | None) -> date | None:
    if value is None:
        return None
    if value > date.today():
        raise ValueError("Date of birth cannot be in the future")
    if value < date(1900, 1, 1):
        raise ValueError("Date of birth is not valid")
    return value


def normalize_phone(raw: str) -> str:
    """Normalize a phone number to E.164-ish form (defaults to India +91 for 10 digits)."""
    if not raw or not raw.strip():
        raise ValueError("Phone number is required")

    digits = re.sub(r"[^\d]", "", raw)
    if not digits:
        raise ValueError("Phone number must contain digits")

    if raw.strip().startswith("+"):
        normalized = digits
    elif len(digits) == 10:
        normalized = "91" + digits
    elif len(digits) == 11 and digits.startswith("0"):
        normalized = "91" + digits[1:]
    else:
        normalized = digits

    if len(normalized) < 10 or len(normalized) > 15:
        raise ValueError("Phone number must be between 10 and 15 digits")

    return "+" + normalized


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain an uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain a lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain a digit")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("Password must contain a special character")
    return password
