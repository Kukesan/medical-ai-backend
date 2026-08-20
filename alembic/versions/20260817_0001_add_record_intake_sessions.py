"""Add record_intake_sessions table for conversational free-text record intake.

Revision ID: 20260817_0001
Revises: 20260816_0008
Create Date: 2026-08-17
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260817_0001"
down_revision = "20260816_0008"
branch_labels = None
depends_on = None


def _create_enum_if_not_exists(bind, enum_name: str, values: list[str]) -> None:
    existing = bind.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = :enum_name)"),
        {"enum_name": enum_name},
    ).scalar()
    if not existing:
        values_sql = ", ".join(f"'{value}'" for value in values)
        bind.execute(sa.text(f"CREATE TYPE {enum_name} AS ENUM ({values_sql})"))


def upgrade() -> None:
    record_intake_status = postgresql.ENUM(
        "awaiting_clarification",
        "awaiting_confirmation",
        "completed",
        "abandoned",
        name="record_intake_status",
        create_type=False,
    )

    bind = op.get_bind()
    _create_enum_if_not_exists(
        bind,
        "record_intake_status",
        ["awaiting_clarification", "awaiting_confirmation", "completed", "abandoned"],
    )

    op.create_table(
        "record_intake_sessions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("status", record_intake_status, nullable=False),
        sa.Column("record_type_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_new_record_type", sa.Boolean(), nullable=False),
        sa.Column("classification_confidence", sa.Float(), nullable=True),
        sa.Column("draft_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("missing_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("pending_field", sa.String(length=100), nullable=True),
        sa.Column("pending_question", sa.Text(), nullable=True),
        sa.Column("questions_asked", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.Date(), nullable=True),
        sa.Column("resulting_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_record_intake_sessions_user_id_users")),
        sa.ForeignKeyConstraint(
            ["record_type_id"],
            ["record_types.id"],
            name=op.f("fk_record_intake_sessions_record_type_id_record_types"),
        ),
        sa.ForeignKeyConstraint(
            ["resulting_record_id"],
            ["medical_records.id"],
            name=op.f("fk_record_intake_sessions_resulting_record_id_medical_records"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_record_intake_sessions")),
    )
    op.create_index(op.f("ix_record_intake_sessions_user_id"), "record_intake_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_record_intake_sessions_status"), "record_intake_sessions", ["status"], unique=False)
    op.create_index(
        op.f("ix_record_intake_sessions_record_type_id"), "record_intake_sessions", ["record_type_id"], unique=False
    )
    op.create_index(
        "ix_record_intake_sessions_user_status",
        "record_intake_sessions",
        ["user_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_record_intake_sessions_user_status", table_name="record_intake_sessions")
    op.drop_index(op.f("ix_record_intake_sessions_record_type_id"), table_name="record_intake_sessions")
    op.drop_index(op.f("ix_record_intake_sessions_status"), table_name="record_intake_sessions")
    op.drop_index(op.f("ix_record_intake_sessions_user_id"), table_name="record_intake_sessions")
    op.drop_table("record_intake_sessions")

    op.execute("DROP TYPE IF EXISTS record_intake_status")
