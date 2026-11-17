from enum import Enum


class UserStatus(str, Enum):
    pending = "pending"
    active = "active"
    disabled = "disabled"


class OtpChannel(str, Enum):
    email = "email"
    whatsapp = "whatsapp"
    totp = "totp"


class OtpStatus(str, Enum):
    pending = "pending"
    verified = "verified"
    expired = "expired"
    failed = "failed"
    locked = "locked"


class OtpPurpose(str, Enum):
    registration = "registration"
    login = "login"
    totp_enrollment = "totp_enrollment"


class ParseStatus(str, Enum):
    parsed = "parsed"
    failed = "failed"
