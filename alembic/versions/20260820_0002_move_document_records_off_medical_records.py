"""Stop duplicating document-extracted records into medical_records.

Records extracted from an uploaded document (medical_records.source_document_id IS NOT
NULL) were living in two places at once: medical_records and the document's own
extraction pipeline output. This collapses them into a single source of truth -
medical_documents.classified_records (a JSON list of {record_type_code, data,
recorded_at}) - and drops medical_records.source_document_id entirely, since going
forward medical_records only ever holds user-entered records (always source-less).

Existing document-derived medical_records rows are backfilled into their document's
classified_records before being deleted; their embeddings cascade-delete via
embeddings.record_id's ON DELETE CASCADE.

Revision ID: 20260820_0002
Revises: 20260820_0001
Create Date: 2026-08-20
"""

import uuid
from datetime import UTC, date, datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260820_0002"
down_revision = "20260820_0001"
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

medical_documents_t = sa.table(
    "medical_documents",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("user_id", postgresql.UUID(as_uuid=True)),
    sa.column("classified_records", postgresql.JSON),
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

record_types_t = sa.table(
    "record_types",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("code", sa.String),
)


def _iso(value):
    return value.isoformat() if value is not None else None


def _parse_date(value):
    return date.fromisoformat(value[:10]) if value else None


def upgrade() -> None:
    op.add_column("medical_documents", sa.Column("classified_records", postgresql.JSON(), nullable=True))

    bind = op.get_bind()

    record_type_codes = {row.id: row.code for row in bind.execute(sa.select(record_types_t)).fetchall()}

    document_rows = bind.execute(
        sa.select(medical_records_t).where(medical_records_t.c.source_document_id.isnot(None))
    ).fetchall()

    by_document: dict[uuid.UUID, list[dict]] = {}
    for row in document_rows:
        entry = {
            "record_type_code": record_type_codes.get(row.record_type_id),
            "data": row.data,
            "recorded_at": _iso(row.recorded_at),
        }
        by_document.setdefault(row.source_document_id, []).append(entry)

    for document_id, entries in by_document.items():
        bind.execute(
            medical_documents_t.update()
            .where(medical_documents_t.c.id == document_id)
            .values(classified_records=entries)
        )

    bind.execute(medical_records_t.delete().where(medical_records_t.c.source_document_id.isnot(None)))

    op.drop_index(op.f("ix_medical_records_source_document_id"), table_name="medical_records")
    op.drop_constraint(
        op.f("fk_medical_records_source_document_id_medical_documents"), "medical_records", type_="foreignkey"
    )
    op.drop_column("medical_records", "source_document_id")


def downgrade() -> None:
    uuid_col = postgresql.UUID(as_uuid=True)
    op.add_column("medical_records", sa.Column("source_document_id", uuid_col, nullable=True))
    op.create_foreign_key(
        op.f("fk_medical_records_source_document_id_medical_documents"),
        "medical_records",
        "medical_documents",
        ["source_document_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_medical_records_source_document_id"), "medical_records", ["source_document_id"], unique=False
    )

    bind = op.get_bind()
    now = datetime.now(UTC)

    record_type_ids = {row.code: row.id for row in bind.execute(sa.select(record_types_t)).fetchall()}

    documents = bind.execute(
        sa.select(
            medical_documents_t.c.id, medical_documents_t.c.user_id, medical_documents_t.c.classified_records
        ).where(medical_documents_t.c.classified_records.isnot(None))
    ).fetchall()

    for document in documents:
        for entry in document.classified_records or []:
            record_type_id = record_type_ids.get(entry.get("record_type_code"))
            if record_type_id is None:
                continue
            recorded_at = _parse_date(entry.get("recorded_at"))
            bind.execute(
                medical_records_t.insert().values(
                    id=uuid.uuid4(),
                    user_id=document.user_id,
                    record_type_id=record_type_id,
                    source_document_id=document.id,
                    recorded_at=recorded_at,
                    status="verified",
                    data=entry.get("data") or {},
                    current_version=1,
                    created_at=now,
                    updated_at=now,
                )
            )

    op.drop_column("medical_documents", "classified_records")
