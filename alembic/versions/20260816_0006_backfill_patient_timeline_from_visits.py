"""Backfill patient_timeline from medical_visits, then tighten document_id to NOT NULL + FK.

Straight column copy - patient_timeline.doctor_name/visit_date/hospital_name/diagnosis_text
already match medical_visits' columns exactly by name. Run this, then verify
patient_timeline's row count matches medical_visits' (12 in the live DB at the time this
was written), before running the follow-up drop-tables migration (20260816_0007).

Revision ID: 20260816_0006
Revises: 20260816_0005
Create Date: 2026-08-16
"""

import uuid
from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa

revision = "20260816_0006"
down_revision = "20260816_0005"
branch_labels = None
depends_on = None

medical_visits_t = sa.table(
    "medical_visits",
    sa.column("id", sa.UUID()),
    sa.column("user_id", sa.UUID()),
    sa.column("document_id", sa.UUID()),
    sa.column("visit_date", sa.Date()),
    sa.column("doctor_name", sa.String),
    sa.column("hospital_name", sa.String),
    sa.column("diagnosis_text", sa.Text),
)

patient_timeline_t = sa.table(
    "patient_timeline",
    sa.column("id", sa.UUID()),
    sa.column("user_id", sa.UUID()),
    sa.column("document_id", sa.UUID()),
    sa.column("doctor_name", sa.String),
    sa.column("visit_date", sa.Date()),
    sa.column("hospital_name", sa.String),
    sa.column("diagnosis_text", sa.Text),
    sa.column("generated_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(UTC)

    rows = bind.execute(sa.select(medical_visits_t)).fetchall()
    for row in rows:
        bind.execute(
            patient_timeline_t.insert().values(
                id=uuid.uuid4(),
                user_id=row.user_id,
                document_id=row.document_id,
                doctor_name=row.doctor_name,
                visit_date=row.visit_date,
                hospital_name=row.hospital_name,
                diagnosis_text=row.diagnosis_text,
                generated_at=now,
            )
        )

    op.alter_column("patient_timeline", "document_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_patient_timeline_document_id_medical_documents"),
        "patient_timeline",
        "medical_documents",
        ["document_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_patient_timeline_document_id_medical_documents"), "patient_timeline", type_="foreignkey"
    )
    op.alter_column("patient_timeline", "document_id", nullable=True)

    bind = op.get_bind()
    visit_document_ids = [row[0] for row in bind.execute(sa.select(medical_visits_t.c.document_id)).fetchall()]
    if visit_document_ids:
        bind.execute(patient_timeline_t.delete().where(patient_timeline_t.c.document_id.in_(visit_document_ids)))
