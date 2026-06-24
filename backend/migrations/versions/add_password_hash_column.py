"""add password_hash column to users table

Revision ID: add_password_hash
Create Date: 2026-06-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_password_hash'
down_revision = 'p2p3_approval_workflow'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'password_hash')
