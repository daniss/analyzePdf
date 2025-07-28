"""
Invoice Review and Audit Trail Models

Models for tracking manual data review and field edits by users.
Provides comprehensive audit trail for French compliance requirements.
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from typing import Optional, Any, Dict

from core.database import Base


class InvoiceFieldEdit(Base):
    """
    Audit trail for manual field edits during invoice review
    Tracks all changes made by users for compliance and accuracy
    """
    __tablename__ = "invoice_field_edits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Invoice and user references
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Field change details
    field_name = Column(String(255), nullable=False)  # e.g., "vendor.siret_number", "total_ttc"
    field_path = Column(String(500), nullable=True)   # JSON path for nested fields
    
    # Change tracking
    original_value = Column(Text, nullable=True)      # AI extracted value
    new_value = Column(Text, nullable=True)           # User edited value
    previous_value = Column(Text, nullable=True)      # Previous user edit (if multiple changes)
    
    # AI confidence and source
    ai_confidence = Column(Integer, nullable=True)    # 0-100 confidence score
    ai_source = Column(String(50), nullable=True)     # "groq", "claude", "ocr", etc.
    
    # Change metadata
    change_reason = Column(String(100), nullable=True)  # "accuracy_correction", "compliance_fix", "data_entry_error"
    user_notes = Column(Text, nullable=True)           # User explanation for the change
    validation_status = Column(String(50), nullable=True)  # "valid", "invalid", "pending"
    
    # French compliance tracking
    triggers_siret_revalidation = Column(Boolean, default=False)
    triggers_tva_recalculation = Column(Boolean, default=False)
    compliance_impact = Column(String(50), nullable=True)  # "none", "minor", "major", "critical"
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    invoice = relationship("Invoice", backref="field_edits")
    user = relationship("User")


class ReviewSession(Base):
    """
    Track review sessions for invoices
    Groups related field edits and tracks review progress
    """
    __tablename__ = "review_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Invoice and user references
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Session details
    session_type = Column(String(50), nullable=False)  # "initial_review", "correction", "approval"
    status = Column(String(50), nullable=False)        # "in_progress", "completed", "abandoned"
    
    # Progress tracking
    fields_reviewed = Column(Integer, default=0)
    fields_modified = Column(Integer, default=0)
    total_fields = Column(Integer, nullable=True)
    completion_percentage = Column(Integer, default=0)  # 0-100
    
    # Review outcomes
    review_decision = Column(String(50), nullable=True)  # "approved", "needs_changes", "rejected"
    reviewer_notes = Column(Text, nullable=True)
    confidence_score = Column(Integer, nullable=True)   # Overall confidence after review (0-100)
    
    # Quality metrics
    ai_accuracy_score = Column(Integer, nullable=True)  # How accurate was AI extraction (0-100)
    review_duration_seconds = Column(Integer, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    invoice = relationship("Invoice", backref="review_sessions")
    user = relationship("User")


class ReviewTemplate(Base):
    """
    Templates for systematic invoice review
    Defines checklists and validation rules for different invoice types
    """
    __tablename__ = "review_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Template metadata
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    template_type = Column(String(50), nullable=False)  # "french_b2b", "french_b2c", "international"
    
    # Review configuration
    required_fields = Column(JSON, nullable=False)      # List of fields that must be validated
    validation_rules = Column(JSON, nullable=False)     # Field-specific validation rules
    checklist_items = Column(JSON, nullable=False)      # Review checklist for users
    
    # French compliance settings
    requires_siret_validation = Column(Boolean, default=True)
    requires_tva_validation = Column(Boolean, default=True)
    minimum_confidence_threshold = Column(Integer, default=80)  # Minimum AI confidence required
    
    # Template status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)


def create_field_edit_record(
    invoice_id: str,
    user_id: str, 
    field_name: str,
    original_value: Any,
    new_value: Any,
    ai_confidence: Optional[int] = None,
    change_reason: Optional[str] = None,
    user_notes: Optional[str] = None
) -> InvoiceFieldEdit:
    """
    Helper function to create field edit audit records
    """
    return InvoiceFieldEdit(
        invoice_id=uuid.UUID(invoice_id),
        user_id=uuid.UUID(user_id),
        field_name=field_name,
        original_value=str(original_value) if original_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        ai_confidence=ai_confidence,
        change_reason=change_reason,
        user_notes=user_notes,
        triggers_siret_revalidation=field_name in ["vendor.siret_number", "customer.siret_number", "vendor.siren_number", "customer.siren_number"],
        triggers_tva_recalculation=field_name in ["total_tva", "subtotal_ht", "total_ttc", "tva_breakdown"]
    )