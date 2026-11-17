"""add application profile fields

Revision ID: 0001_application_fields
Revises:
Create Date: 2026-11-17
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.base import Base

revision = "0001_application_fields"
down_revision = None
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column in {item["name"] for item in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        Base.metadata.create_all(bind)
        return

    if not _has_column("users", "dob"):
        op.add_column("users", sa.Column("dob", sa.Date(), nullable=True))
    if not _has_column("users", "education"):
        op.add_column(
            "users",
            sa.Column(
                "education",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
    if not _has_column("users", "projects"):
        op.add_column(
            "users",
            sa.Column(
                "projects",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
    if not _has_column("users", "internships"):
        op.add_column(
            "users",
            sa.Column(
                "internships",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
    if not _has_column("users", "experience_entries"):
        op.add_column(
            "users",
            sa.Column(
                "experience_entries",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
    if not _has_column("users", "applied_role"):
        op.add_column(
            "users", sa.Column("applied_role", sa.String(length=150), nullable=True)
        )
    if not _has_column("users", "application_status"):
        op.add_column(
            "users",
            sa.Column(
                "application_status",
                sa.String(length=30),
                nullable=False,
                server_default=sa.text("'submitted'"),
            ),
        )


def downgrade() -> None:
    for column in [
        "application_status",
        "applied_role",
        "experience_entries",
        "internships",
        "projects",
        "education",
        "dob",
    ]:
        if _has_column("users", column):
            op.drop_column("users", column)
