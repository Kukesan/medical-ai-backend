"""reshape-analysis-results-to-medication-alert

Revision ID: 20260804_0002
Revises: 15eb08cb6d1c
Create Date: 2026-08-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260804_0002"
down_revision = "15eb08cb6d1c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_category') THEN
                CREATE TYPE alert_category AS ENUM (
                    'drug_interaction',
                    'duplicate_medication',
                    'allergy_conflict',
                    'dosage_conflict',
                    'medication_change',
                    'lab_abnormality'
                );
            END IF;
        END
        $$;
        """
    )

    op.add_column(
        "analysis_results",
        sa.Column(
            "category",
            postgresql.ENUM(
                "drug_interaction",
                "duplicate_medication",
                "allergy_conflict",
                "dosage_conflict",
                "medication_change",
                "lab_abnormality",
                name="alert_category",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column("analysis_results", sa.Column("title", sa.Text(), nullable=True))
    op.add_column("analysis_results", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("analysis_results", sa.Column("clinical_reason", sa.Text(), nullable=True))
    op.add_column("analysis_results", sa.Column("timeline", sa.JSON(), nullable=True, server_default=sa.text("'[]'::json")))
    op.add_column("analysis_results", sa.Column("recommendation", sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE analysis_results
        SET
            category = 'medication_change',
            title = COALESCE(result_type, 'Medication alert'),
            description = COALESCE(explanation, ''),
            clinical_reason = COALESCE(explanation, ''),
            recommendation = 'Discuss with healthcare professional',
            timeline = COALESCE(timeline, '[]'::json)
        """
    )

    op.alter_column("analysis_results", "category", nullable=False)
    op.alter_column("analysis_results", "title", nullable=False)
    op.alter_column("analysis_results", "description", nullable=False)
    op.alter_column("analysis_results", "clinical_reason", nullable=False)
    op.alter_column("analysis_results", "timeline", nullable=False, server_default=None)
    op.alter_column("analysis_results", "recommendation", nullable=False)

    op.drop_column("analysis_results", "result_type")
    op.drop_column("analysis_results", "explanation")


def downgrade() -> None:
    op.add_column("analysis_results", sa.Column("result_type", sa.Text(), nullable=True))
    op.add_column("analysis_results", sa.Column("explanation", sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE analysis_results
        SET
            result_type = COALESCE(title, 'medication_alert'),
            explanation = COALESCE(clinical_reason, description, '')
        """
    )

    op.alter_column("analysis_results", "result_type", nullable=False)
    op.alter_column("analysis_results", "explanation", nullable=False)

    op.drop_column("analysis_results", "recommendation")
    op.drop_column("analysis_results", "timeline")
    op.drop_column("analysis_results", "clinical_reason")
    op.drop_column("analysis_results", "description")
    op.drop_column("analysis_results", "title")
    op.drop_column("analysis_results", "category")

    op.execute("DROP TYPE IF EXISTS alert_category")
