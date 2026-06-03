"""Add dynamic rule tables

Revision ID: 156287492b65
Revises: 455ad299810f
Create Date: 2026-05-24 10:46:24.079486

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '156287492b65'
down_revision: Union[str, Sequence[str], None] = '455ad299810f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Smart migration that creates tables if they don't exist."""
    conn = op.get_bind()

    try:
        inspector = inspect(conn)
        tables = inspector.get_table_names()

        # Check if verification_rules table exists
        if 'verification_rules' in tables:
            print("Verification rules table exists - skipping table creation")
        else:
            print("Creating verification_rules table...")
            op.create_table('verification_rules',
                sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
                sa.Column('name', sa.String(), nullable=False),
                sa.Column('rule_type', sa.String(), nullable=False),
                sa.Column('severity', sa.String(), nullable=False),
                sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                sa.Column('is_active', sa.Boolean(), nullable=True),
                sa.Column('created_by', postgresql.UUID(as_uuid=False), nullable=True),
                sa.Column('created_at', sa.DateTime(), nullable=True),
                sa.Column('updated_at', sa.DateTime(), nullable=True),
                sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
                sa.PrimaryKeyConstraint('id')
            )
            op.create_index(op.f('ix_verification_rules_id'), 'verification_rules', ['id'], unique=False)
            op.create_index(op.f('ix_verification_rules_rule_type'), 'verification_rules', ['rule_type'], unique=False)

            print("Verification rules table created successfully")

    except Exception as e:
        print(f"Verification rules migration: {e}")


def downgrade() -> None:
    """Downgrade schema."""
    try:
        op.drop_index(op.f('ix_verification_rules_rule_type'), table_name='verification_rules')
        op.drop_index(op.f('ix_verification_rules_id'), table_name='verification_rules')
        op.drop_table('verification_rules')
        print("Verification rules table dropped successfully")
    except Exception as e:
        print(f"Verification rules downgrade: {e}")
