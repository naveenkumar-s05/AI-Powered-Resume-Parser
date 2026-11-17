import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    JSON,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserStatus

if TYPE_CHECKING:
    from app.models.otp import OtpChallenge
    from app.models.resume import UserResume


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    phone: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    skills: Mapped[list] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), default=list, nullable=False
    )
    experience: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qualification: Mapped[str | None] = mapped_column(String(255), nullable=True)

    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    education: Mapped[list] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), default=list, nullable=False
    )
    projects: Mapped[list] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), default=list, nullable=False
    )
    internships: Mapped[list] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), default=list, nullable=False
    )
    experience_entries: Mapped[list] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), default=list, nullable=False
    )
    applied_role: Mapped[str | None] = mapped_column(String(150), nullable=True)
    application_status: Mapped[str] = mapped_column(
        String(30), default="submitted", nullable=False
    )

    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus, name="user_status", native_enum=False, length=20),
        default=UserStatus.pending,
        nullable=False,
        index=True,
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    whatsapp_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_secret_encrypted: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    resumes: Mapped[list["UserResume"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    otp_challenges: Mapped[list["OtpChallenge"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.active
