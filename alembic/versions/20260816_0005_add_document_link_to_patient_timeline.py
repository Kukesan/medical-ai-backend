"""Add document link + diagnosis_text to patient_timeline; fix visit_date column type.

patient_timeline is becoming the per-document visit-metadata row (replacing
medical_visits): it already had doctor_name/visit_date/hospital_name but no link back to
the source document. document_id is added nullable here so the follow-up backfill
migration (20260816_0006) can populate it before tightening to NOT NULL + FK.

visit_date was declared as `DateTime(timezone=True)` but every value that will ever
populate it (ExtractedMedicalVisit.visit_date, matching medical_visits.visit_date before
it) is a plain `date` - asyncpg rejects binding a `date` to a `timestamptz` column. Since
patient_timeline has 0 rows today (confirmed live - the only code path that ever wrote to
it was already broken), this is a safe in-place type change with no data to convert.

Revision ID: 20260816_0005
Revises: 20260816_0004
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa

revision = "20260816_0005"
down_revision = "20260816_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("patient_timeline", sa.Column("document_id", sa.UUID(), nullable=True))
    op.add_column("patient_timeline", sa.Column("diagnosis_text", sa.Text(), nullable=True))
    op.create_index(op.f("ix_patient_timeline_document_id"), "patient_timeline", ["document_id"], unique=False)
    op.alter_column(
        "patient_timeline",
        "visit_date",
        type_=sa.Date(),
        postgresql_using="visit_date::date",
    )


def downgrade() -> None:
    op.alter_column(
        "patient_timeline",
        "visit_date",
        type_=sa.DateTime(timezone=True),
        postgresql_using="visit_date::timestamptz",
    )
    op.drop_index(op.f("ix_patient_timeline_document_id"), table_name="patient_timeline")
    op.drop_column("patient_timeline", "diagnosis_text")
    op.drop_column("patient_timeline", "document_id")
