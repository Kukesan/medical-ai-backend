"""Add document/analysis-result grounding fields to chat sessions.

Chat conversations previously always used every piece of the patient's
data as context. This adds optional per-session grounding so a
conversation can instead be scoped to a single document or analysis
result, chosen once when the conversation is started.

Revision ID: 20260821_0002
Revises: 20260821_0001
Create Date: 2026-08-21
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260821_0002"
down_revision = "20260821_0001"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chat_context_type') THEN
                CREATE TYPE chat_context_type AS ENUM ('document', 'analysis_result');
            END IF;
        END
        $$;
        """
    )

    op.add_column(
        "chat_sessions",
        sa.Column(
            "context_type",
            postgresql.ENUM("document", "analysis_result", name="chat_context_type", create_type=False),
            nullable=True,
        ),
    )
    op.add_column("chat_sessions", sa.Column("context_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("chat_sessions", sa.Column("context_label", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_sessions", "context_label")
    op.drop_column("chat_sessions", "context_id")
    op.drop_column("chat_sessions", "context_type")
    op.execute("DROP TYPE IF EXISTS chat_context_type")
