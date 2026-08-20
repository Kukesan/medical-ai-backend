"""Replace FAISS-backed embeddings with native Supabase pgvector storage.

Revision ID: 20260820_0001
Revises: 20260819_0001
Create Date: 2026-08-20
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260820_0001"
down_revision = "20260819_0001"
branch_labels = None
depends_on = None

EMBEDDING_DIMENSIONS = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    uuid_col = postgresql.UUID(as_uuid=True)
    op.add_column("embeddings", sa.Column("user_id", uuid_col, nullable=True))
    op.add_column("embeddings", sa.Column("record_id", uuid_col, nullable=True))
    op.add_column("embeddings", sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=True))

    # Existing rows point at a now-deleted FAISS index and cannot be backfilled with real
    # vectors; drop them rather than leaving rows with a null embedding.
    op.execute("DELETE FROM embeddings")

    op.alter_column("embeddings", "user_id", nullable=False)
    op.alter_column("embeddings", "embedding", nullable=False)
    op.alter_column("embeddings", "document_id", nullable=True)

    op.drop_column("embeddings", "vector_index_position")

    op.create_foreign_key(
        op.f("fk_embeddings_user_id_users"), "embeddings", "users", ["user_id"], ["id"]
    )
    op.create_foreign_key(
        op.f("fk_embeddings_record_id_medical_records"),
        "embeddings",
        "medical_records",
        ["record_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_embeddings_user_id"), "embeddings", ["user_id"], unique=False)
    op.create_index(op.f("ix_embeddings_record_id"), "embeddings", ["record_id"], unique=False)

    op.create_check_constraint(
        "document_xor_record",
        "embeddings",
        "(document_id IS NOT NULL AND record_id IS NULL) "
        "OR (document_id IS NULL AND record_id IS NOT NULL)",
    )

    op.execute(
        "CREATE INDEX ix_embeddings_embedding_hnsw ON embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_embeddings_embedding_hnsw")
    op.drop_constraint(op.f("ck_embeddings_document_xor_record"), "embeddings", type_="check")

    op.drop_index(op.f("ix_embeddings_record_id"), table_name="embeddings")
    op.drop_index(op.f("ix_embeddings_user_id"), table_name="embeddings")
    op.drop_constraint(
        op.f("fk_embeddings_record_id_medical_records"), "embeddings", type_="foreignkey"
    )
    op.drop_constraint(op.f("fk_embeddings_user_id_users"), "embeddings", type_="foreignkey")

    op.add_column("embeddings", sa.Column("vector_index_position", sa.Integer(), nullable=True))
    op.execute("DELETE FROM embeddings")
    op.alter_column("embeddings", "vector_index_position", nullable=False)
    op.alter_column("embeddings", "document_id", nullable=False)

    op.drop_column("embeddings", "embedding")
    op.drop_column("embeddings", "record_id")
    op.drop_column("embeddings", "user_id")
