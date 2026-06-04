"""Add approval workflow tables and version enhancements

Revision ID: p2p3_approval_workflow
Revises: add_operator_registry_and_templates
Create Date: 2026-06-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = 'p2p3_approval_workflow'
down_revision = 'add_operator_registry'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # P3: Add version management enhancement columns to rule_versions
    op.add_column('rule_versions', sa.Column('change_log', sa.Text, nullable=True))
    op.add_column('rule_versions', sa.Column('change_request_id', sa.UUID(as_uuid=False),
                                              sa.ForeignKey('rule_change_requests.id', ondelete='SET NULL'),
                                              nullable=True))


def downgrade() -> None:
    op.drop_column('rule_versions', 'change_request_id')
    op.drop_column('rule_versions', 'change_log')

