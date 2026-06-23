"""Add reference to severity enum

Revision ID: add_reference_to_severity
Revises: add_verification_modules
Create Date: 2026-06-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_reference_to_severity'
down_revision = 'add_verification_modules'
branch_labels = None
depends_on = None


def upgrade():
    # PostgreSQL requires COMMIT before ALTER TYPE if used in transaction,
    # but Alembic usually wraps in a transaction. We can execute it with commit.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE severity ADD VALUE IF NOT EXISTS 'reference';")


def downgrade():
    # PostgreSQL does not support dropping a value from an enum type easily.
    pass
