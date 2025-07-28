"""Add duplicate detection tracking tables

Revision ID: 2c4f8b9e1d7a
Revises: 83e4b81e4a3c
Create Date: 2025-07-28 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision = '2c4f8b9e1d7a'
down_revision = '83e4b81e4a3c'
branch_labels = None
depends_on = None


def upgrade():
    """Add duplicate detection tracking tables"""
    
    # Create duplicate_detection_logs table
    op.create_table('duplicate_detection_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('original_invoice_id', UUID(as_uuid=True), sa.ForeignKey('invoices.id'), nullable=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('detection_type', sa.String(50), nullable=False),
        sa.Column('duplicate_file_hash', sa.String(64), nullable=True),
        sa.Column('duplicate_invoice_key', sa.String(255), nullable=True),
        sa.Column('user_action', sa.String(20), nullable=False),
        sa.Column('user_reason', sa.String(500), nullable=True),
        sa.Column('user_notes', sa.Text(), nullable=True),
        sa.Column('batch_id', sa.String(100), nullable=True),
        sa.Column('severity_level', sa.String(20), nullable=True),
        sa.Column('confidence_score', sa.Integer(), nullable=True),
        sa.Column('supplier_name', sa.String(255), nullable=True),
        sa.Column('invoice_number', sa.String(100), nullable=True),
        sa.Column('invoice_amount', sa.String(20), nullable=True),
        sa.Column('detection_method', sa.String(50), nullable=True),
        sa.Column('system_recommendation', sa.String(20), nullable=True),
        sa.Column('legal_basis', sa.String(100), default='legitimate_interest'),
        sa.Column('processing_purpose', sa.String(200), default='duplicate_prevention'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create duplicate_statistics table
    op.create_table('duplicate_statistics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('statistics_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('total_files_uploaded', sa.Integer(), default=0),
        sa.Column('file_duplicates_detected', sa.Integer(), default=0),
        sa.Column('file_duplicates_skipped', sa.Integer(), default=0),
        sa.Column('file_duplicates_replaced', sa.Integer(), default=0),
        sa.Column('invoice_duplicates_detected', sa.Integer(), default=0),
        sa.Column('invoice_duplicates_allowed', sa.Integer(), default=0),
        sa.Column('invoice_duplicates_rejected', sa.Integer(), default=0),
        sa.Column('export_duplicates_removed', sa.Integer(), default=0),
        sa.Column('sage_pnm_duplicates_prevented', sa.Integer(), default=0),
        sa.Column('cross_period_duplicates', sa.Integer(), default=0),
        sa.Column('siret_based_matches', sa.Integer(), default=0),
        sa.Column('user_decisions_required', sa.Integer(), default=0),
        sa.Column('automatic_resolutions', sa.Integer(), default=0),
        sa.Column('user_override_count', sa.Integer(), default=0),
        sa.Column('average_detection_time_ms', sa.Integer(), nullable=True),
        sa.Column('false_positive_count', sa.Integer(), default=0),
        sa.Column('gdpr_log_entries_created', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # Create duplicate_feedback table
    op.create_table('duplicate_feedback',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('detection_log_id', UUID(as_uuid=True), sa.ForeignKey('duplicate_detection_logs.id'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('is_accurate', sa.Boolean(), nullable=False),
        sa.Column('feedback_type', sa.String(50), nullable=False),
        sa.Column('french_message', sa.Text(), nullable=True),
        sa.Column('business_impact', sa.String(100), nullable=True),
        sa.Column('accounting_impact', sa.String(200), nullable=True),
        sa.Column('suggested_improvement', sa.Text(), nullable=True),
        sa.Column('system_response', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create performance indexes
    op.create_index('idx_dup_detection_user_date', 'duplicate_detection_logs', ['user_id', 'detected_at'])
    op.create_index('idx_dup_detection_invoice_key', 'duplicate_detection_logs', ['duplicate_invoice_key'])
    op.create_index('idx_dup_detection_file_hash', 'duplicate_detection_logs', ['duplicate_file_hash'])
    op.create_index('idx_dup_detection_batch', 'duplicate_detection_logs', ['batch_id'])
    op.create_index('idx_dup_detection_type', 'duplicate_detection_logs', ['detection_type'])
    
    op.create_index('idx_dup_stats_user_date', 'duplicate_statistics', ['user_id', 'statistics_date'])
    op.create_index('idx_dup_stats_date', 'duplicate_statistics', ['statistics_date'])
    
    op.create_index('idx_dup_feedback_log', 'duplicate_feedback', ['detection_log_id'])
    op.create_index('idx_dup_feedback_user', 'duplicate_feedback', ['user_id', 'created_at'])


def downgrade():
    """Remove duplicate detection tracking tables"""
    
    # Drop indexes first
    op.drop_index('idx_dup_feedback_user', table_name='duplicate_feedback')
    op.drop_index('idx_dup_feedback_log', table_name='duplicate_feedback')
    op.drop_index('idx_dup_stats_date', table_name='duplicate_statistics')
    op.drop_index('idx_dup_stats_user_date', table_name='duplicate_statistics')
    op.drop_index('idx_dup_detection_type', table_name='duplicate_detection_logs')
    op.drop_index('idx_dup_detection_batch', table_name='duplicate_detection_logs')
    op.drop_index('idx_dup_detection_file_hash', table_name='duplicate_detection_logs')
    op.drop_index('idx_dup_detection_invoice_key', table_name='duplicate_detection_logs')
    op.drop_index('idx_dup_detection_user_date', table_name='duplicate_detection_logs')
    
    # Drop tables
    op.drop_table('duplicate_feedback')
    op.drop_table('duplicate_statistics')
    op.drop_table('duplicate_detection_logs')