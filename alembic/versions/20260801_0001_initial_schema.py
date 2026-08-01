"""Initial schema

Revision ID: 20260801_0001
Revises: 
Create Date: 2026-08-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260801_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    document_type = sa.Enum(
        "prescription", "lab_report", "discharge_summary", "clinical_note", "other", name="document_type"
    )
    processing_status = sa.Enum(
        "uploaded", "ocr_completed", "extracted", "analyzed", "failed", name="processing_status"
    )
    risk_level = sa.Enum("low", "medium", "high", name="risk_level")
    message_role = sa.Enum("user", "assistant", "system", name="message_role")

    bind = op.get_bind()
    document_type.create(bind, checkfirst=True)
    processing_status.create(bind, checkfirst=True)
    risk_level.create(bind, checkfirst=True)
    message_role.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "medical_documents",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column("processing_status", processing_status, nullable=False),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("ocr_metadata", sa.JSON(), nullable=True),
        sa.Column("extraction_result", sa.JSON(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_medical_documents_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medical_documents")),
    )
    op.create_index(op.f("ix_medical_documents_user_id"), "medical_documents", ["user_id"], unique=False)

    op.create_table(
        "medical_visits",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=True),
        sa.Column("doctor_name", sa.String(length=255), nullable=True),
        sa.Column("hospital_name", sa.String(length=255), nullable=True),
        sa.Column("diagnosis_text", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["medical_documents.id"], name=op.f("fk_medical_visits_document_id_medical_documents")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_medical_visits_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medical_visits")),
    )
    op.create_index(op.f("ix_medical_visits_document_id"), "medical_visits", ["document_id"], unique=False)
    op.create_index(op.f("ix_medical_visits_user_id"), "medical_visits", ["user_id"], unique=False)
    op.create_index(op.f("ix_medical_visits_visit_date"), "medical_visits", ["visit_date"], unique=False)

    op.create_table(
        "allergies",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("substance", sa.String(length=255), nullable=False),
        sa.Column("reaction", sa.String(length=255), nullable=True),
        sa.Column("severity", sa.String(length=50), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_allergies_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_allergies")),
    )
    op.create_index(op.f("ix_allergies_substance"), "allergies", ["substance"], unique=False)
    op.create_index(op.f("ix_allergies_user_id"), "allergies", ["user_id"], unique=False)

    op.create_table(
        "chat_sessions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_chat_sessions_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_sessions")),
    )
    op.create_index(op.f("ix_chat_sessions_user_id"), "chat_sessions", ["user_id"], unique=False)

    op.create_table(
        "patient_timeline",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeline_payload", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_patient_timeline_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patient_timeline")),
    )
    op.create_index(op.f("ix_patient_timeline_user_id"), "patient_timeline", ["user_id"], unique=False)

    op.create_table(
        "analysis_results",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_type", sa.Text(), nullable=False),
        sa.Column("risk_level", risk_level, nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_analysis_results_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_results")),
    )
    op.create_index(op.f("ix_analysis_results_user_id"), "analysis_results", ["user_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("warning", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], name=op.f("fk_chat_messages_session_id_chat_sessions")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_messages")),
    )
    op.create_index(op.f("ix_chat_messages_session_id"), "chat_messages", ["session_id"], unique=False)

    op.create_table(
        "clinical_notes",
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_text", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["medical_visits.id"], name=op.f("fk_clinical_notes_visit_id_medical_visits")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clinical_notes")),
    )
    op.create_index(op.f("ix_clinical_notes_visit_id"), "clinical_notes", ["visit_id"], unique=False)

    op.create_table(
        "embeddings",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", sa.String(length=255), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("vector_metadata", sa.JSON(), nullable=False),
        sa.Column("vector_index_position", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["medical_documents.id"], name=op.f("fk_embeddings_document_id_medical_documents")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_embeddings")),
    )
    op.create_index(op.f("ix_embeddings_chunk_id"), "embeddings", ["chunk_id"], unique=False)
    op.create_index(op.f("ix_embeddings_document_id"), "embeddings", ["document_id"], unique=False)

    op.create_table(
        "lab_results",
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_name", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("value_text", sa.String(length=100), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("reference_range", sa.String(length=100), nullable=True),
        sa.Column("observed_date", sa.Date(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["medical_visits.id"], name=op.f("fk_lab_results_visit_id_medical_visits")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lab_results")),
    )
    op.create_index(op.f("ix_lab_results_test_name"), "lab_results", ["test_name"], unique=False)
    op.create_index(op.f("ix_lab_results_visit_id"), "lab_results", ["visit_id"], unique=False)

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
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["medical_visits.id"], name=op.f("fk_medications_visit_id_medical_visits")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medications")),
    )
    op.create_index(op.f("ix_medications_name"), "medications", ["name"], unique=False)
    op.create_index(op.f("ix_medications_visit_id"), "medications", ["visit_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_medications_visit_id"), table_name="medications")
    op.drop_index(op.f("ix_medications_name"), table_name="medications")
    op.drop_table("medications")

    op.drop_index(op.f("ix_lab_results_visit_id"), table_name="lab_results")
    op.drop_index(op.f("ix_lab_results_test_name"), table_name="lab_results")
    op.drop_table("lab_results")

    op.drop_index(op.f("ix_embeddings_document_id"), table_name="embeddings")
    op.drop_index(op.f("ix_embeddings_chunk_id"), table_name="embeddings")
    op.drop_table("embeddings")

    op.drop_index(op.f("ix_clinical_notes_visit_id"), table_name="clinical_notes")
    op.drop_table("clinical_notes")

    op.drop_index(op.f("ix_chat_messages_session_id"), table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index(op.f("ix_analysis_results_user_id"), table_name="analysis_results")
    op.drop_table("analysis_results")

    op.drop_index(op.f("ix_patient_timeline_user_id"), table_name="patient_timeline")
    op.drop_table("patient_timeline")

    op.drop_index(op.f("ix_chat_sessions_user_id"), table_name="chat_sessions")
    op.drop_table("chat_sessions")

    op.drop_index(op.f("ix_allergies_user_id"), table_name="allergies")
    op.drop_index(op.f("ix_allergies_substance"), table_name="allergies")
    op.drop_table("allergies")

    op.drop_index(op.f("ix_medical_visits_visit_date"), table_name="medical_visits")
    op.drop_index(op.f("ix_medical_visits_user_id"), table_name="medical_visits")
    op.drop_index(op.f("ix_medical_visits_document_id"), table_name="medical_visits")
    op.drop_table("medical_visits")

    op.drop_index(op.f("ix_medical_documents_user_id"), table_name="medical_documents")
    op.drop_table("medical_documents")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    sa.Enum(name="message_role").drop(bind, checkfirst=True)
    sa.Enum(name="risk_level").drop(bind, checkfirst=True)
    sa.Enum(name="processing_status").drop(bind, checkfirst=True)
    sa.Enum(name="document_type").drop(bind, checkfirst=True)
