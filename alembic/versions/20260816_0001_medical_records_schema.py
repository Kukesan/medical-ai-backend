"""Add generic medical record review schema (record_types, medical_records, versions, provenance)

Revision ID: 20260816_0001
Revises: 5a1c2e9d7b3f
Create Date: 2026-08-16
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260816_0001"
down_revision = "5a1c2e9d7b3f"
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
    _create_enum_if_not_exists(
        bind,
        "medical_record_status",
        ["processing", "extracted", "needs_review", "user_edited", "verified", "rejected", "conflict_requires_review"],
    )
    _create_enum_if_not_exists(bind, "record_change_source", ["ai", "user", "system", "import"])
    _create_enum_if_not_exists(bind, "record_field_provenance_source", ["ai", "user", "system"])

    op.create_table(
        "record_types",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("identity_field", sa.String(length=100), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_record_types")),
        sa.UniqueConstraint("code", name=op.f("uq_record_types_code")),
    )
    op.create_index(op.f("ix_record_types_code"), "record_types", ["code"], unique=False)

    op.create_table(
        "medical_records",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recorded_at", sa.Date(), nullable=True),
        sa.Column("status", medical_record_status, nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("conflict_with_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_medical_records_user_id_users")),
        sa.ForeignKeyConstraint(
            ["record_type_id"], ["record_types.id"], name=op.f("fk_medical_records_record_type_id_record_types")
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["medical_documents.id"],
            name=op.f("fk_medical_records_source_document_id_medical_documents"),
        ),
        sa.ForeignKeyConstraint(
            ["conflict_with_record_id"],
            ["medical_records.id"],
            name=op.f("fk_medical_records_conflict_with_record_id_medical_records"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medical_records")),
    )
    op.create_index(op.f("ix_medical_records_user_id"), "medical_records", ["user_id"], unique=False)
    op.create_index(op.f("ix_medical_records_record_type_id"), "medical_records", ["record_type_id"], unique=False)
    op.create_index(
        op.f("ix_medical_records_source_document_id"), "medical_records", ["source_document_id"], unique=False
    )
    op.create_index(op.f("ix_medical_records_status"), "medical_records", ["status"], unique=False)
    op.create_index(op.f("ix_medical_records_created_at"), "medical_records", ["created_at"], unique=False)
    op.create_index(
        "ix_medical_records_user_type_status",
        "medical_records",
        ["user_id", "record_type_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_medical_records_data_gin",
        "medical_records",
        ["data"],
        unique=False,
        postgresql_using="gin",
    )

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
            ["medical_record_id"], ["medical_records.id"], name=op.f("fk_medical_record_versions_medical_record_id_medical_records")
        ),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], name=op.f("fk_medical_record_versions_changed_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medical_record_versions")),
        sa.UniqueConstraint(
            "medical_record_id", "version", name="uq_medical_record_versions_record_version"
        ),
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
        sa.UniqueConstraint(
            "medical_record_id", "field_path", name="uq_medical_record_field_provenance_record_field"
        ),
    )
    op.create_index(
        op.f("ix_medical_record_field_provenance_medical_record_id"),
        "medical_record_field_provenance",
        ["medical_record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_medical_record_field_provenance_medical_record_id"), table_name="medical_record_field_provenance"
    )
    op.drop_table("medical_record_field_provenance")

    op.drop_index(op.f("ix_medical_record_versions_medical_record_id"), table_name="medical_record_versions")
    op.drop_table("medical_record_versions")

    op.drop_index("ix_medical_records_data_gin", table_name="medical_records")
    op.drop_index("ix_medical_records_user_type_status", table_name="medical_records")
    op.drop_index(op.f("ix_medical_records_created_at"), table_name="medical_records")
    op.drop_index(op.f("ix_medical_records_status"), table_name="medical_records")
    op.drop_index(op.f("ix_medical_records_source_document_id"), table_name="medical_records")
    op.drop_index(op.f("ix_medical_records_record_type_id"), table_name="medical_records")
    op.drop_index(op.f("ix_medical_records_user_id"), table_name="medical_records")
    op.drop_table("medical_records")

    op.drop_index(op.f("ix_record_types_code"), table_name="record_types")
    op.drop_table("record_types")

    op.execute("DROP TYPE IF EXISTS record_field_provenance_source")
    op.execute("DROP TYPE IF EXISTS record_change_source")
    op.execute("DROP TYPE IF EXISTS medical_record_status")
