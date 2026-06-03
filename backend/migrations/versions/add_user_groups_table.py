"""add_user_groups_table

Revision ID: c7f8d3e2a1b9
Revises: 664c02f918be
Create Date: 2026-05-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'c7f8d3e2a1b9'
down_revision: Union[str, Sequence[str], None] = '664c02f918be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Smart migration that checks if tables already exist."""
    conn = op.get_bind()
    try:
        inspector = inspect(conn)
        tables = inspector.get_table_names()

        if 'user_groups' in tables:
            print("user_groups table exists - skipping migration")
            return

        print("Creating user_groups and user_group_members tables...")
        # Create user_groups table
        op.create_table('user_groups',
            sa.Column('id', sa.String(255), nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('ldap_group_dn', sa.String(1000), nullable=True),
            sa.Column('role', sa.String(50), nullable=False, server_default='USER'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index(op.f('ix_user_groups_id'), 'user_groups', ['id'], unique=False)
        op.create_index(op.f('ix_user_groups_name'), 'user_groups', ['name'], unique=True)

        # Create user_group_members association table
        op.create_table('user_group_members',
            sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column('group_id', sa.String(255), nullable=False),
            sa.Column('joined_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['group_id'], ['user_groups.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('user_id', 'group_id')
        )
        op.create_index(op.f('ix_user_group_members_user_id'), 'user_group_members', ['user_id'], unique=False)
        op.create_index(op.f('ix_user_group_members_group_id'), 'user_group_members', ['group_id'], unique=False)
    except Exception as e:
        print(f"User groups migration: {e}")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_group_members_group_id'), table_name='user_group_members')
    op.drop_index(op.f('ix_user_group_members_user_id'), table_name='user_group_members')
    op.drop_table('user_group_members')
    op.drop_index(op.f('ix_user_groups_name'), table_name='user_groups')
    op.drop_index(op.f('ix_user_groups_id'), table_name='user_groups')
    op.drop_table('user_groups')
