"""Drop medical_visits and clinical_notes now that patient_timeline is the visit-metadata record.

clinical_notes is dropped first since it has the FK to medical_visits. Clinical note text
is intentionally not preserved elsewhere (per decision: it stays available only in each
document's raw ocr_text/extraction_result). medical_visits' data was already backfilled
into patient_timeline by 20260816_0006 - verify row counts match before running this.

Revision ID: 20260816_0007
Revises: 20260816_0006
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa

revision = "20260816_0007"
down_revision = "20260816_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("clinical_notes")
    op.drop_table("medical_visits")


def downgrade() -> None:
    op.create_table(
        "medical_visits",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=True),
        sa.Column("doctor_name", sa.String(length=255), nullable=True),
        sa.Column("hospital_name", sa.String(length=255), nullable=True),
        sa.Column("diagnosis_text", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_medical_visits_user_id_users")),
        sa.ForeignKeyConstraint(
            ["document_id"], ["medical_documents.id"], name=op.f("fk_medical_visits_document_id_medical_documents")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medical_visits")),
    )
    op.create_index(op.f("ix_medical_visits_user_id"), "medical_visits", ["user_id"], unique=False)
    op.create_index(op.f("ix_medical_visits_document_id"), "medical_visits", ["document_id"], unique=False)
    op.create_index(op.f("ix_medical_visits_visit_date"), "medical_visits", ["visit_date"], unique=False)

    op.create_table(
        "clinical_notes",
        sa.Column("visit_id", sa.UUID(), nullable=False),
        sa.Column("note_text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["visit_id"], ["medical_visits.id"], name=op.f("fk_clinical_notes_visit_id_medical_visits")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clinical_notes")),
    )
    op.create_index(op.f("ix_clinical_notes_visit_id"), "clinical_notes", ["visit_id"], unique=False)
