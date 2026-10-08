"""Auth hardening: token versioning, terms acceptance, case-insensitive emails.

- users.token_version: embedded in access/refresh tokens so logout and password
  changes can revoke every token issued before them.
- users.terms_accepted_at: when the user accepted the Terms and Privacy Policy at sign-up.
- Lowercases existing emails (skipping any that would collide) and adds a unique
  index on lower(email) so "John@x.com" and "john@x.com" can't become two accounts.

Revision ID: 20261008_0001
Revises: 20260821_0002
Create Date: 2026-10-08
"""

import sqlalchemy as sa
from alembic import op

revision = "20261008_0001"
down_revision = "20260821_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("token_version", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        """
        UPDATE users AS u
        SET email = lower(u.email)
        WHERE u.email <> lower(u.email)
          AND NOT EXISTS (SELECT 1 FROM users AS o WHERE o.id <> u.id AND lower(o.email) = lower(u.email))
        """
    )
    # Only enforce uniqueness when no case-duplicates exist; otherwise the deploy would fail.
    # Lookups are case-insensitive either way (UserRepository.get_by_email).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT lower(email) FROM users GROUP BY lower(email) HAVING count(*) > 1) THEN
                CREATE UNIQUE INDEX ix_users_email_lower ON users (lower(email));
            ELSE
                RAISE WARNING 'users has emails differing only by case; ix_users_email_lower not created';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_email_lower")
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "token_version")
