import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import OtpChannel, OtpPurpose, OtpStatus

if TYPE_CHECKING:
    from app.models.user import User


class OtpChallenge(Base):
    __tablename__ = "otp_challenges"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel: Mapped[OtpChannel] = mapped_column(
        SAEnum(OtpChannel, name="otp_channel", native_enum=False, length=20),
        nullable=False,
    )
    purpose: Mapped[OtpPurpose] = mapped_column(
        SAEnum(OtpPurpose, name="otp_purpose", native_enum=False, length=30),
        default=OtpPurpose.registration,
        nullable=False,
    )
    otp_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[OtpStatus] = mapped_column(
        SAEnum(OtpStatus, name="otp_status", native_enum=False, length=20),
        default=OtpStatus.pending,
        nullable=False,
    )

    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    resend_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="otp_challenges")
