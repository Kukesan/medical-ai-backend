"""Replace user vitals/age columns with a dated vitals table and profile fields.

The profile page previously stored a single point-in-time snapshot of age,
height, weight, blood group, pressure, and blood sugar directly on users.
This moves those measurements into a new vitals table keyed by recorded_at
so a user's vitals can be tracked over time, and replaces age on users with
date_of_birth (computed age stays current) plus bio/notes fields.

Revision ID: 20260821_0001
Revises: 20260820_0002
Create Date: 2026-08-21
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260821_0001"
down_revision = "20260820_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vitals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recorded_at", sa.Date(), nullable=False),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("blood_group", sa.String(length=5), nullable=True),
        sa.Column("pressure", sa.String(length=20), nullable=True),
        sa.Column("blood_sugar", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_vitals_user_id", "vitals", ["user_id"])
    op.create_index("ix_vitals_recorded_at", "vitals", ["recorded_at"])

    op.execute(
        """
        INSERT INTO vitals (id, user_id, recorded_at, height, weight, blood_group, pressure, blood_sugar,
                             created_at, updated_at)
        SELECT gen_random_uuid(), id, updated_at::date, height, weight, blood_group, pressure, blood_sugar,
               updated_at, updated_at
        FROM users
        WHERE height IS NOT NULL OR weight IS NOT NULL OR blood_group IS NOT NULL
           OR pressure IS NOT NULL OR blood_sugar IS NOT NULL
        """
    )

    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("notes", sa.Text(), nullable=True))

    op.drop_column("users", "blood_sugar")
    op.drop_column("users", "pressure")
    op.drop_column("users", "blood_group")
    op.drop_column("users", "weight")
    op.drop_column("users", "height")
    op.drop_column("users", "age")


def downgrade() -> None:
    op.add_column("users", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("height", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("weight", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("blood_group", sa.String(length=5), nullable=True))
    op.add_column("users", sa.Column("pressure", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("blood_sugar", sa.Float(), nullable=True))

    op.execute(
        """
        UPDATE users
        SET height = v.height, weight = v.weight, blood_group = v.blood_group,
            pressure = v.pressure, blood_sugar = v.blood_sugar
        FROM (
            SELECT DISTINCT ON (user_id) user_id, height, weight, blood_group, pressure, blood_sugar
            FROM vitals
            ORDER BY user_id, recorded_at DESC, created_at DESC
        ) v
        WHERE users.id = v.user_id
        """
    )

    op.drop_column("users", "notes")
    op.drop_column("users", "bio")
    op.drop_column("users", "date_of_birth")

    op.drop_index("ix_vitals_recorded_at", table_name="vitals")
    op.drop_index("ix_vitals_user_id", table_name="vitals")
    op.drop_table("vitals")
