"""p2p3_approval_workflow (stub)

This is a stub migration to resolve orphaned migration dependencies.
No actual schema changes — serves as a placeholder for the chain.

Revision ID: p2p3_approval_workflow
Revises: None
Create Date: 2026-06-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'p2p3_approval_workflow'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No changes — stub only."""
    pass


def downgrade() -> None:
    """No changes — stub only."""
    pass
