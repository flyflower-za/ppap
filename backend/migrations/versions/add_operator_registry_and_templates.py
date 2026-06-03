"""add_operator_registry_and_templates

Revision ID: add_operator_registry
Revises: 10dd2dcf16f5
Create Date: 2026-06-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_operator_registry'
down_revision: Union[str, Sequence[str], None] = '10dd2dcf16f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create operator_registry table
    op.create_table(
        'operator_registry',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('operator_key', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('operator_type', sa.String(50), nullable=True),
        sa.Column('parameters_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('supports_severity', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('default_severity', sa.String(20), nullable=True, server_default='fail'),
        sa.Column('priority', sa.Integer(), nullable=True, server_default='100'),
        sa.Column('is_heavy', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('is_deprecated', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('deprecated_by', sa.String(100), nullable=True),
        sa.Column('version', sa.String(20), nullable=True, server_default='1.0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('operator_key')
    )

    # Create operator_templates table
    op.create_table(
        'operator_templates',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('operator_key', sa.String(100), nullable=False),
        sa.Column('preset_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('use_case_description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_by', sa.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['operator_key'], ['operator_registry.operator_key']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create rule_templates table
    op.create_table(
        'rule_templates',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category_suggestions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('template_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_by', sa.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('is_public', sa.Boolean(), nullable=True, server_default='false'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create rule_change_requests table
    op.create_table(
        'rule_change_requests',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('rule_id', sa.UUID(as_uuid=False), nullable=True),
        sa.Column('change_type', sa.String(20), nullable=True),
        sa.Column('proposed_rule_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('impact_assessment', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'pending', 'approved', 'rejected', 'deployed', 'rolled_back', name='approvalstatus', native_enum=False), nullable=True, server_default='draft'),
        sa.Column('requested_by', sa.UUID(as_uuid=False), nullable=True),
        sa.Column('requested_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('reviewed_by', sa.UUID(as_uuid=False), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.Column('deployed_by', sa.UUID(as_uuid=False), nullable=True),
        sa.Column('deployed_at', sa.DateTime(), nullable=True),
        sa.Column('category_id', sa.UUID(as_uuid=False), nullable=True),
        sa.Column('priority', sa.String(20), nullable=True, server_default='normal'),
        sa.Column('test_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['rule_id'], ['verification_rules.id']),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['deployed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['category_id'], ['document_categories.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create approval_policies table
    op.create_table(
        'approval_policies',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('requires_approval', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('required_approvers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('min_approvals_required', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for operator_registry
    op.create_index(op.f('ix_operator_registry_operator_key'), 'operator_registry', ['operator_key'], unique=True)
    op.create_index(op.f('ix_operator_registry_category'), 'operator_registry', ['category'], unique=False)
    op.create_index(op.f('ix_operator_registry_is_active'), 'operator_registry', ['is_active'], unique=False)

    # Create indexes for rule_templates
    op.create_index(op.f('ix_rule_templates_is_public'), 'rule_templates', ['is_public'], unique=False)
    op.create_index(op.f('ix_rule_templates_is_system'), 'rule_templates', ['is_system'], unique=False)

    # Create indexes for rule_change_requests
    op.create_index(op.f('ix_rule_change_requests_status'), 'rule_change_requests', ['status'], unique=False)
    op.create_index(op.f('ix_rule_change_requests_requested_by'), 'rule_change_requests', ['requested_by'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order
    op.drop_table('approval_policies')
    op.drop_table('rule_change_requests')
    op.drop_table('rule_templates')
    op.drop_table('operator_templates')
    op.drop_table('operator_registry')
