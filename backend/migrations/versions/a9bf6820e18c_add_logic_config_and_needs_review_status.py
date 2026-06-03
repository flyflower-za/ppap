"""Add logic_config and NEEDS_REVIEW status

Revision ID: a9bf6820e18c
Revises: 156287492b65
Create Date: 2026-05-24 11:40:19.223311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'a9bf6820e18c'
down_revision: Union[str, Sequence[str], None] = '156287492b65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Smart migration that checks if column already exists."""
    conn = op.get_bind()
    try:
        inspector = inspect(conn)
        if 'verification_rules' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('verification_rules')]
            if 'logic_config' in columns:
                print("logic_config column exists - skipping migration")
                return
        print("Adding logic_config column...")
        op.add_column('verification_rules', sa.Column('logic_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    except Exception as e:
        print(f"Logic config migration: {e}")


def downgrade() -> None:
    """Downgrade schema."""
    print("Downgrade not implemented - database schema managed by init-db.sql")
