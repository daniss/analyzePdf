"""
Duplicate Detection Tracking Models

This module provides database models for tracking duplicate detection and resolution
decisions, supporting GDPR audit requirements and French business compliance.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from typing import Optional
import uuid

from core.database import Base


class DuplicateDetectionLog(Base):
    """
    Track duplicate detection events and user resolutions for audit compliance
    
    This table stores:
    - When duplicates were detected
    - What type of duplicates they were
    - How users resolved them
    - Audit information for GDPR compliance
    """
    __tablename__ = "duplicate_detection_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to original invoice (if exists)
    original_invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    
    # User who made the decision
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Duplicate detection details
    detection_type = Column(String(50), nullable=False)  # 'file_duplicate', 'invoice_duplicate', 'cross_period_duplicate'
    duplicate_file_hash = Column(String(64), nullable=True)  # SHA-256 hash of duplicate file
    duplicate_invoice_key = Column(String(255), nullable=True)  # supplier_siret + invoice_number
    
    # User resolution
    user_action = Column(String(20), nullable=False)  # 'skip', 'replace', 'allow'
    user_reason = Column(String(500), nullable=True)  # User-provided reason
    user_notes = Column(Text, nullable=True)  # Additional user notes
    
    # Batch processing context
    batch_id = Column(String(100), nullable=True)  # For batch upload tracking
    
    # Detection metadata
    severity_level = Column(String(20), nullable=True)  # 'error', 'warning', 'info'
    confidence_score = Column(Integer, nullable=True)  # 0-100 confidence in duplicate detection
    
    # French business context
    supplier_name = Column(String(255), nullable=True)  # For easier French reporting
    invoice_number = Column(String(100), nullable=True)  # For easier French reporting
    invoice_amount = Column(String(20), nullable=True)  # Stored as string to avoid precision issues
    
    # System context
    detection_method = Column(String(50), nullable=True)  # 'automatic', 'user_initiated'
    system_recommendation = Column(String(20), nullable=True)  # What system recommended
    
    # Audit and compliance
    legal_basis = Column(String(100), default="legitimate_interest")
    processing_purpose = Column(String(200), default="duplicate_prevention")
    
    # Additional metadata as JSON
    metadata = Column(JSON, nullable=True)
    
    # Timestamps
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    original_invoice = relationship("Invoice", foreign_keys=[original_invoice_id])
    user = relationship("User", foreign_keys=[user_id])


class DuplicateStatistics(Base):
    """
    Daily statistics for duplicate detection performance and French compliance reporting
    
    This table aggregates duplicate detection data for:
    - Performance monitoring
    - French compliance reporting
    - User behavior analysis
    """
    __tablename__ = "duplicate_statistics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Date and user context
    statistics_date = Column(DateTime(timezone=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # File duplicate statistics
    total_files_uploaded = Column(Integer, default=0)
    file_duplicates_detected = Column(Integer, default=0)
    file_duplicates_skipped = Column(Integer, default=0)
    file_duplicates_replaced = Column(Integer, default=0)
    
    # Invoice business logic duplicates
    invoice_duplicates_detected = Column(Integer, default=0)
    invoice_duplicates_allowed = Column(Integer, default=0)  # Legitimate reprocessing
    invoice_duplicates_rejected = Column(Integer, default=0)
    
    # Export deduplication
    export_duplicates_removed = Column(Integer, default=0)  # Critical for accounting
    sage_pnm_duplicates_prevented = Column(Integer, default=0)  # Specific to French accounting
    
    # French business metrics
    cross_period_duplicates = Column(Integer, default=0)  # Same invoice, different periods
    siret_based_matches = Column(Integer, default=0)  # French SIRET-based duplicate detection
    
    # User behavior
    user_decisions_required = Column(Integer, default=0)
    automatic_resolutions = Column(Integer, default=0)
    user_override_count = Column(Integer, default=0)  # User disagreed with system recommendation
    
    # Performance metrics
    average_detection_time_ms = Column(Integer, nullable=True)
    false_positive_count = Column(Integer, default=0)  # User reported as false positive
    
    # Compliance and audit
    gdpr_log_entries_created = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])


class DuplicateFeedback(Base):
    """
    User feedback on duplicate detection accuracy for continuous improvement
    
    Supports French accountant feedback on duplicate detection quality
    """
    __tablename__ = "duplicate_feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Reference to the detection log
    detection_log_id = Column(UUID(as_uuid=True), ForeignKey("duplicate_detection_logs.id"), nullable=False)
    
    # User providing feedback
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Feedback details
    is_accurate = Column(Boolean, nullable=False)  # Was the duplicate detection correct?
    feedback_type = Column(String(50), nullable=False)  # 'false_positive', 'false_negative', 'correct'
    
    # French business context feedback
    french_message = Column(Text, nullable=True)  # Feedback in French
    business_impact = Column(String(100), nullable=True)  # 'high', 'medium', 'low'
    accounting_impact = Column(String(200), nullable=True)  # Impact on French accounting
    
    # Improvement suggestions
    suggested_improvement = Column(Text, nullable=True)
    system_response = Column(Text, nullable=True)  # How system addressed the feedback
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    detection_log = relationship("DuplicateDetectionLog", foreign_keys=[detection_log_id])
    user = relationship("User", foreign_keys=[user_id])


# Index definitions for performance (would be added in migration)
"""
Recommended indexes for production:

CREATE INDEX idx_dup_detection_user_date ON duplicate_detection_logs(user_id, detected_at);
CREATE INDEX idx_dup_detection_invoice_key ON duplicate_detection_logs(duplicate_invoice_key);
CREATE INDEX idx_dup_detection_file_hash ON duplicate_detection_logs(duplicate_file_hash);
CREATE INDEX idx_dup_detection_batch ON duplicate_detection_logs(batch_id);
CREATE INDEX idx_dup_detection_type ON duplicate_detection_logs(detection_type);

CREATE INDEX idx_dup_stats_user_date ON duplicate_statistics(user_id, statistics_date);
CREATE INDEX idx_dup_stats_date ON duplicate_statistics(statistics_date);

CREATE INDEX idx_dup_feedback_log ON duplicate_feedback(detection_log_id);
CREATE INDEX idx_dup_feedback_user ON duplicate_feedback(user_id, created_at);
"""