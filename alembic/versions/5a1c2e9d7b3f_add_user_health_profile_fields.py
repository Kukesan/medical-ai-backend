"""add-user-health-profile-fields

Revision ID: 5a1c2e9d7b3f
Revises: fa6767fcb9e5
Create Date: 2026-08-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '5a1c2e9d7b3f'
down_revision = 'fa6767fcb9e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('age', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('height', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('weight', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('blood_group', sa.String(length=5), nullable=True))
    op.add_column('users', sa.Column('pressure', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('blood_sugar', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'blood_sugar')
    op.drop_column('users', 'pressure')
    op.drop_column('users', 'blood_group')
    op.drop_column('users', 'weight')
    op.drop_column('users', 'height')
    op.drop_column('users', 'age')
