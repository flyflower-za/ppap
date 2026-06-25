"""add_username_column

Merge migration to add username column and combine divergent heads.

Revision ID: add_username_column
Revises: add_operator_registry, add_verification_modules
Create Date: 2026-06-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_username_column'
down_revision: Union[str, Sequence[str], None] = ('add_operator_registry', 'add_verification_modules')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Add username column as nullable initially
    op.add_column('users', sa.Column('username', sa.String(255), nullable=True))

    # Step 2: Backfill username for existing users from email prefix
    conn = op.get_bind()
    if conn.engine.name == 'postgresql':
        result = conn.execute(
            sa.text("""
                SELECT id, email FROM users ORDER BY created_at ASC
            """)
        )
        for row in result:
            base = row[1].split('@')[0].strip().lower()
            username = base
            suffix = 2
            while True:
                check = conn.execute(
                    sa.text("SELECT COUNT(*) FROM users WHERE username = :u AND id != :id"),
                    {"u": username, "id": row[0]}
                ).scalar()
                if check == 0:
                    break
                username = f"{base}{suffix}"
                suffix += 1
            conn.execute(
                sa.text("UPDATE users SET username = :u WHERE id = :id"),
                {"u": username, "id": row[0]}
            )

    # Step 3: Make username NOT NULL and add unique constraint
    op.alter_column('users', 'username', nullable=False)
    op.create_index('idx_users_username', 'users', ['username'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_users_username', table_name='users')
    op.drop_column('users', 'username')
