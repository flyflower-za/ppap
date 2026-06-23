"""
Add Verification Modules Tables

Revision ID: add_verification_modules
Create Date: 2026-06-23

This migration adds tables for the simplified verification module system,
which provides an alternative to complex logic graphs for rule configuration.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM


# revision identifiers, used by Alembic.
revision = 'add_verification_modules'
down_revision = 'p2p3_approval_workflow'
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing types if they exist due to a previous failed run
    op.execute("DROP TYPE IF EXISTS moduletype CASCADE")
    op.execute("DROP TYPE IF EXISTS moduleseverity CASCADE")

    # Create ENUM types
    module_type_enum = ENUM(
        'qr_scanner', 'signature_verifier', 'pdf_info', 'institution_sniffer',
        'revision_check', 'text_llm', 'vision_llm', 'url_fetch',
        'stamp_detection', 'document_diff', 'table_verification',
        'regex_match', 'keyword_match', 'comparison', 'variable_extractor',
        name='moduletype',
        create_type=True
    )

    module_severity_enum = ENUM(
        'critical', 'warning', 'info',
        name='moduleseverity',
        create_type=True
    )

    # Create verification_modules table
    op.create_table(
        'verification_modules',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('module_type', module_type_enum, nullable=False),
        sa.Column('severity', module_severity_enum, nullable=False, server_default='warning'),
        sa.Column('config', JSONB(), nullable=False, server_default='{}'),
        sa.Column('category_id', UUID(as_uuid=False), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['document_categories.id']),
    )

    # Create rule_modules junction table
    op.create_table(
        'rule_modules',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('rule_id', UUID(as_uuid=False), nullable=False),
        sa.Column('module_id', UUID(as_uuid=False), nullable=False),
        sa.Column('created_at', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['rule_id'], ['verification_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['module_id'], ['verification_modules.id'], ondelete='CASCADE'),
    )

    # Add module_id to verification_rules
    op.add_column('verification_rules', sa.Column('module_id', UUID(as_uuid=False), sa.ForeignKey('verification_modules.id'), nullable=True))

    # Create indexes
    op.create_index('ix_verification_modules_category_id', 'verification_modules', ['category_id'])
    op.create_index('ix_verification_modules_is_active', 'verification_modules', ['is_active'])
    op.create_index('ix_verification_modules_module_type', 'verification_modules', ['module_type'])

    op.create_index('ix_rule_modules_rule_id', 'rule_modules', ['rule_id'])
    op.create_index('ix_rule_modules_module_id', 'rule_modules', ['module_id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_rule_modules_module_id', table_name='rule_modules')
    op.drop_index('ix_rule_modules_rule_id', table_name='rule_modules')
    op.drop_index('ix_verification_modules_module_type', table_name='verification_modules')
    op.drop_index('ix_verification_modules_is_active', table_name='verification_modules')
    op.drop_index('ix_verification_modules_category_id', table_name='verification_modules')

    # Drop column from verification_rules
    op.drop_column('verification_rules', 'module_id')

    # Drop tables
    op.drop_table('rule_modules')
    op.drop_table('verification_modules')

    # Drop ENUM types
    ENUM(name='moduleseverity').drop(op.get_bind(), checkfirst=False)
    ENUM(name='moduletype').drop(op.get_bind(), checkfirst=False)
