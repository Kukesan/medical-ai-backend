"""Add user_edited and accepted values to processing_status enum.

Revision ID: 20260819_0001
Revises: 20260817_0001
Create Date: 2026-08-19
"""

from alembic import op

revision = "20260819_0001"
down_revision = "20260817_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE processing_status ADD VALUE IF NOT EXISTS 'user_edited'")
    op.execute("ALTER TYPE processing_status ADD VALUE IF NOT EXISTS 'accepted'")


def downgrade() -> None:
    # Postgres does not support removing values from an enum type; no-op.
    pass
