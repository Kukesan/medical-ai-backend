"""Backfill medical_records from the legacy allergy/medication/lab_result/vaccination/surgery tables.

Every existing row becomes a VERIFIED medical_record (version 1, change_source='import',
field provenance source='system', verified=true) - this data was already live, trusted
production data before this review system existed, so treating it as NEEDS_REVIEW would
regress the experience for existing users with no new information gained. Field names are
a straight copy: the record_types.schema seeded in 20260816_0002 were deliberately designed
to match these legacy columns exactly.

Run this, then verify medical_records row counts by record type match the legacy tables'
row counts, before running the follow-up drop-tables migration (20260816_0004).

Revision ID: 20260816_0003
Revises: 20260816_0002
Create Date: 2026-08-16
"""

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260816_0003"
down_revision = "20260816_0002"
branch_labels = None
depends_on = None

medical_record_status = postgresql.ENUM(
    "processing",
    "extracted",
    "needs_review",
    "user_edited",
    "verified",
    "rejected",
    "conflict_requires_review",
    name="medical_record_status",
    create_type=False,
)
record_change_source = postgresql.ENUM(
    "ai", "user", "system", "import", name="record_change_source", create_type=False
)
record_field_provenance_source = postgresql.ENUM(
    "ai", "user", "system", name="record_field_provenance_source", create_type=False
)

record_types_t = sa.table("record_types", sa.column("id", postgresql.UUID(as_uuid=True)), sa.column("code", sa.String))

allergies_t = sa.table(
    "allergies",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("user_id", postgresql.UUID(as_uuid=True)),
    sa.column("substance", sa.String),
    sa.column("reaction", sa.String),
    sa.column("severity", sa.String),
)

medical_visits_t = sa.table(
    "medical_visits",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("user_id", postgresql.UUID(as_uuid=True)),
    sa.column("document_id", postgresql.UUID(as_uuid=True)),
    sa.column("visit_date", sa.Date),
)

medications_t = sa.table(
    "medications",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("visit_id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("dosage", sa.String),
    sa.column("dosage_value", sa.Float),
    sa.column("dosage_unit", sa.String),
    sa.column("frequency", sa.String),
    sa.column("duration", sa.String),
    sa.column("start_date", sa.Date),
    sa.column("end_date", sa.Date),
)

lab_results_t = sa.table(
    "lab_results",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("visit_id", postgresql.UUID(as_uuid=True)),
    sa.column("test_name", sa.String),
    sa.column("value", sa.Float),
    sa.column("value_text", sa.String),
    sa.column("unit", sa.String),
    sa.column("reference_range", sa.String),
    sa.column("observed_date", sa.Date),
)

vaccinations_t = sa.table(
    "vaccinations",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("user_id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("date_administered", sa.DateTime),
    sa.column("is_next_due", sa.Boolean),
    sa.column("next_due_date", sa.DateTime),
)

surgeries_t = sa.table(
    "surgeries",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("user_id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("date", sa.Date),
    sa.column("notes", sa.Text),
)

medical_records_t = sa.table(
    "medical_records",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("user_id", postgresql.UUID(as_uuid=True)),
    sa.column("record_type_id", postgresql.UUID(as_uuid=True)),
    sa.column("source_document_id", postgresql.UUID(as_uuid=True)),
    sa.column("recorded_at", sa.Date),
    sa.column("status", medical_record_status),
    sa.column("data", postgresql.JSONB),
    sa.column("current_version", sa.Integer),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)

medical_record_versions_t = sa.table(
    "medical_record_versions",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("medical_record_id", postgresql.UUID(as_uuid=True)),
    sa.column("version", sa.Integer),
    sa.column("data", postgresql.JSONB),
    sa.column("status", medical_record_status),
    sa.column("changed_by", postgresql.UUID(as_uuid=True)),
    sa.column("change_source", record_change_source),
    sa.column("created_at", sa.DateTime(timezone=True)),
)

medical_record_field_provenance_t = sa.table(
    "medical_record_field_provenance",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("medical_record_id", postgresql.UUID(as_uuid=True)),
    sa.column("field_path", sa.String),
    sa.column("source", record_field_provenance_source),
    sa.column("confidence", sa.Float),
    sa.column("source_document_id", postgresql.UUID(as_uuid=True)),
    sa.column("page_number", sa.Integer),
    sa.column("verified", sa.Boolean),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)


def _iso(value):
    return value.isoformat() if value is not None else None


def _insert_medical_record(bind, now, record_type_id, user_id, data, source_document_id, recorded_at) -> None:
    record_id = uuid.uuid4()
    bind.execute(
        medical_records_t.insert().values(
            id=record_id,
            user_id=user_id,
            record_type_id=record_type_id,
            source_document_id=source_document_id,
            recorded_at=recorded_at,
            status="verified",
            data=data,
            current_version=1,
            created_at=now,
            updated_at=now,
        )
    )
    bind.execute(
        medical_record_versions_t.insert().values(
            id=uuid.uuid4(),
            medical_record_id=record_id,
            version=1,
            data=data,
            status="verified",
            changed_by=None,
            change_source="import",
            created_at=now,
        )
    )
    for field_path, value in data.items():
        if value is None:
            continue
        bind.execute(
            medical_record_field_provenance_t.insert().values(
                id=uuid.uuid4(),
                medical_record_id=record_id,
                field_path=field_path,
                source="system",
                confidence=None,
                source_document_id=source_document_id,
                page_number=None,
                verified=True,
                created_at=now,
                updated_at=now,
            )
        )


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(UTC)

    record_type_ids = {row.code: row.id for row in bind.execute(sa.select(record_types_t)).fetchall()}

    for row in bind.execute(sa.select(allergies_t)).fetchall():
        data = {"substance": row.substance, "reaction": row.reaction, "severity": row.severity}
        data = {k: v for k, v in data.items() if v is not None}
        _insert_medical_record(
            bind, now, record_type_ids["ALLERGY"], row.user_id, data, source_document_id=None, recorded_at=None
        )

    # medications/lab_results have no user_id column of their own - owned via medical_visits.user_id.
    medication_rows = bind.execute(
        sa.select(
            medications_t,
            medical_visits_t.c.user_id,
            medical_visits_t.c.document_id,
            medical_visits_t.c.visit_date,
        ).select_from(medications_t.join(medical_visits_t, medications_t.c.visit_id == medical_visits_t.c.id))
    ).fetchall()
    for row in medication_rows:
        data = {
            "name": row.name,
            "dosage": row.dosage,
            "dosage_value": row.dosage_value,
            "dosage_unit": row.dosage_unit,
            "frequency": row.frequency,
            "duration": row.duration,
            "start_date": _iso(row.start_date),
            "end_date": _iso(row.end_date),
        }
        data = {k: v for k, v in data.items() if v is not None}
        _insert_medical_record(
            bind,
            now,
            record_type_ids["MEDICATION"],
            row.user_id,
            data,
            source_document_id=row.document_id,
            recorded_at=row.start_date or row.visit_date,
        )

    lab_result_rows = bind.execute(
        sa.select(
            lab_results_t,
            medical_visits_t.c.user_id,
            medical_visits_t.c.document_id,
            medical_visits_t.c.visit_date,
        ).select_from(lab_results_t.join(medical_visits_t, lab_results_t.c.visit_id == medical_visits_t.c.id))
    ).fetchall()
    for row in lab_result_rows:
        data = {
            "test_name": row.test_name,
            "value": row.value,
            "value_text": row.value_text,
            "unit": row.unit,
            "reference_range": row.reference_range,
            "observed_date": _iso(row.observed_date),
        }
        data = {k: v for k, v in data.items() if v is not None}
        _insert_medical_record(
            bind,
            now,
            record_type_ids["LAB_RESULT"],
            row.user_id,
            data,
            source_document_id=row.document_id,
            recorded_at=row.observed_date or row.visit_date,
        )

    for row in bind.execute(sa.select(vaccinations_t)).fetchall():
        data = {
            "name": row.name,
            "date_administered": _iso(row.date_administered),
            "is_next_due": row.is_next_due,
            "next_due_date": _iso(row.next_due_date),
        }
        data = {k: v for k, v in data.items() if v is not None}
        recorded_at = row.date_administered.date() if row.date_administered else None
        _insert_medical_record(
            bind, now, record_type_ids["VACCINATION"], row.user_id, data, source_document_id=None, recorded_at=recorded_at
        )

    for row in bind.execute(sa.select(surgeries_t)).fetchall():
        data = {"name": row.name, "date": _iso(row.date), "notes": row.notes}
        data = {k: v for k, v in data.items() if v is not None}
        _insert_medical_record(
            bind, now, record_type_ids["SURGERY"], row.user_id, data, source_document_id=None, recorded_at=row.date
        )


def downgrade() -> None:
    bind = op.get_bind()
    result = bind.execute(
        sa.select(medical_record_versions_t.c.medical_record_id).where(
            medical_record_versions_t.c.version == 1,
            medical_record_versions_t.c.change_source == "import",
        )
    )
    record_ids = [row[0] for row in result.fetchall()]
    if not record_ids:
        return
    bind.execute(
        medical_record_field_provenance_t.delete().where(
            medical_record_field_provenance_t.c.medical_record_id.in_(record_ids)
        )
    )
    bind.execute(medical_record_versions_t.delete().where(medical_record_versions_t.c.medical_record_id.in_(record_ids)))
    bind.execute(medical_records_t.delete().where(medical_records_t.c.id.in_(record_ids)))
