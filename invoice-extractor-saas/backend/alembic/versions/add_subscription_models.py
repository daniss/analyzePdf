"""Add subscription and pricing tier models

Revision ID: sub_001
Revises: 83e4b81e4a3c
Create Date: 2025-08-02 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'sub_001'
down_revision: Union[str, None] = '83e4b81e4a3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create pricing_config table
    op.create_table('pricing_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tier', sa.Enum('FREE', 'PRO', 'BUSINESS', 'ENTERPRISE', name='pricingtier'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('price_monthly_eur', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('invoice_limit_monthly', sa.Integer(), nullable=False),
        sa.Column('unlimited_invoices', sa.Boolean(), nullable=True),
        sa.Column('priority_support', sa.Boolean(), nullable=True),
        sa.Column('api_access', sa.Boolean(), nullable=True),
        sa.Column('custom_export_formats', sa.Boolean(), nullable=True),
        sa.Column('bulk_processing', sa.Boolean(), nullable=True),
        sa.Column('advanced_validation', sa.Boolean(), nullable=True),
        sa.Column('stripe_price_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tier')
    )

    # Create subscriptions table
    op.create_table('subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pricing_tier', sa.Enum('FREE', 'PRO', 'BUSINESS', 'ENTERPRISE', name='pricingtier'), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'CANCELED', 'PAST_DUE', 'TRIALING', 'INCOMPLETE', name='subscriptionstatus'), nullable=False),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(), nullable=True),
        sa.Column('stripe_price_id', sa.String(), nullable=True),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('monthly_invoice_limit', sa.Integer(), nullable=False),
        sa.Column('monthly_invoices_processed', sa.Integer(), nullable=False),
        sa.Column('quota_reset_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create invoice_quota_usage table
    op.create_table('invoice_quota_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cost_eur', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('usage_month', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_subscriptions_user_id', 'subscriptions', ['user_id'], unique=False)
    op.create_index('idx_subscriptions_status', 'subscriptions', ['status'], unique=False)
    op.create_index('idx_quota_usage_user_month', 'invoice_quota_usage', ['user_id', 'usage_month'], unique=False)
    op.create_index('idx_quota_usage_subscription', 'invoice_quota_usage', ['subscription_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_quota_usage_subscription', table_name='invoice_quota_usage')
    op.drop_index('idx_quota_usage_user_month', table_name='invoice_quota_usage')
    op.drop_index('idx_subscriptions_status', table_name='subscriptions')
    op.drop_index('idx_subscriptions_user_id', table_name='subscriptions')
    
    # Drop tables
    op.drop_table('invoice_quota_usage')
    op.drop_table('subscriptions')
    op.drop_table('pricing_config')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS subscriptionstatus')
    op.execute('DROP TYPE IF EXISTS pricingtier')