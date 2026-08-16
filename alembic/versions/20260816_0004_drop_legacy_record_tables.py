"""Drop legacy per-type record tables now that medical_records is the source of truth.

All five tables are leaves - nothing else has a foreign key to them - so they can be
dropped in any order. Run only after 20260816_0003 has backfilled their data into
medical_records and the row counts have been verified to match.

downgrade() recreates the (empty) tables so the ORM models/migrations stay consistent if
rolled back, but does NOT restore data - like every other destructive migration in this
project, downgrading past this point does not resurrect what was deleted.

Revision ID: 20260816_0004
Revises: 20260816_0003
Create Date: 2026-08-16
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260816_0004"
down_revision = "20260816_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("medications")
    op.drop_table("lab_results")
    op.drop_table("allergies")
    op.drop_table("vaccinations")
    op.drop_table("surgeries")


def downgrade() -> None:
    op.create_table(
        "allergies",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("substance", sa.String(length=255), nullable=False),
        sa.Column("reaction", sa.String(length=255), nullable=True),
        sa.Column("severity", sa.String(length=50), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_allergies_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_allergies")),
    )
    op.create_index(op.f("ix_allergies_user_id"), "allergies", ["user_id"], unique=False)
    op.create_index(op.f("ix_allergies_substance"), "allergies", ["substance"], unique=False)

    op.create_table(
        "lab_results",
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_name", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("value_text", sa.String(length=100), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("reference_range", sa.String(length=100), nullable=True),
        sa.Column("observed_date", sa.Date(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["medical_visits.id"], name=op.f("fk_lab_results_visit_id_medical_visits")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lab_results")),
    )
    op.create_index(op.f("ix_lab_results_visit_id"), "lab_results", ["visit_id"], unique=False)
    op.create_index(op.f("ix_lab_results_test_name"), "lab_results", ["test_name"], unique=False)

    op.create_table(
        "medications",
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("dosage", sa.String(length=100), nullable=True),
        sa.Column("dosage_value", sa.Float(), nullable=True),
        sa.Column("dosage_unit", sa.String(length=50), nullable=True),
        sa.Column("frequency", sa.String(length=100), nullable=True),
        sa.Column("duration", sa.String(length=100), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["medical_visits.id"], name=op.f("fk_medications_visit_id_medical_visits")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medications")),
    )
    op.create_index(op.f("ix_medications_visit_id"), "medications", ["visit_id"], unique=False)
    op.create_index(op.f("ix_medications_name"), "medications", ["name"], unique=False)

    op.create_table(
        "surgeries",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_surgeries_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_surgeries")),
    )
    op.create_index(op.f("ix_surgeries_user_id"), "surgeries", ["user_id"], unique=False)

    op.create_table(
        "vaccinations",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("date_administered", sa.DateTime(), nullable=False),
        sa.Column("is_next_due", sa.Boolean(), nullable=False),
        sa.Column("next_due_date", sa.DateTime(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_vaccinations_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vaccinations")),
    )
