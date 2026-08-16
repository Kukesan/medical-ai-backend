"""Drop medical_record_versions and medical_record_field_provenance.

The human-in-the-loop review system keeps its audit trail via versioning and
per-field provenance/confidence tracking. Both are being removed - medical_records
(with its own status/current_version columns) is now the sole storage for the
review workflow. This is a straight drop, not a migration to another home - the
32 version rows and 123 provenance rows in the live DB are intentionally not
preserved anywhere.

record_change_source and record_field_provenance_source enum types are exclusive
to these two tables and are dropped too. medical_record_status is NOT touched -
it's still used by medical_records.status.

Revision ID: 20260816_0008
Revises: 20260816_0007
Create Date: 2026-08-16
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260816_0008"
down_revision = "20260816_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(
        op.f("ix_medical_record_field_provenance_medical_record_id"), table_name="medical_record_field_provenance"
    )
    op.drop_table("medical_record_field_provenance")

    op.drop_index(op.f("ix_medical_record_versions_medical_record_id"), table_name="medical_record_versions")
    op.drop_table("medical_record_versions")

    op.execute("DROP TYPE IF EXISTS record_field_provenance_source")
    op.execute("DROP TYPE IF EXISTS record_change_source")


def downgrade() -> None:
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

    bind = op.get_bind()
    record_change_source.create(bind, checkfirst=True)
    record_field_provenance_source.create(bind, checkfirst=True)

    op.create_table(
        "medical_record_versions",
        sa.Column("medical_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", medical_record_status, nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("change_source", record_change_source, nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["medical_record_id"],
            ["medical_records.id"],
            name=op.f("fk_medical_record_versions_medical_record_id_medical_records"),
        ),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], name=op.f("fk_medical_record_versions_changed_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medical_record_versions")),
        sa.UniqueConstraint("medical_record_id", "version", name="uq_medical_record_versions_record_version"),
    )
    op.create_index(
        op.f("ix_medical_record_versions_medical_record_id"), "medical_record_versions", ["medical_record_id"], unique=False
    )

    op.create_table(
        "medical_record_field_provenance",
        sa.Column("medical_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_path", sa.String(length=255), nullable=False),
        sa.Column("source", record_field_provenance_source, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["medical_record_id"],
            ["medical_records.id"],
            name=op.f("fk_medical_record_field_provenance_medical_record_id_medical_records"),
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["medical_documents.id"],
            name=op.f("fk_medical_record_field_provenance_source_document_id_medical_documents"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medical_record_field_provenance")),
        sa.UniqueConstraint("medical_record_id", "field_path", name="uq_medical_record_field_provenance_record_field"),
    )
    op.create_index(
        op.f("ix_medical_record_field_provenance_medical_record_id"),
        "medical_record_field_provenance",
        ["medical_record_id"],
        unique=False,
    )
