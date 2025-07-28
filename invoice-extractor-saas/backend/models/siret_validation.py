"""
SIRET Validation Models for French Compliance

This module defines database models and enums for comprehensive SIRET validation
handling, including failure scenarios, user overrides, and compliance tracking.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from core.database import Base


class SIRETValidationStatus(str, Enum):
    """SIRET validation status for traffic light system"""
    VALID = "valid"                    # 🟢 Green - INSEE validated
    NOT_FOUND = "not_found"           # 🔴 Red - Not in INSEE database
    INACTIVE = "inactive"             # 🟡 Orange - Company ceased activity
    NAME_MISMATCH = "name_mismatch"   # 🟡 Orange - Name differs from INSEE
    MALFORMED = "malformed"           # 🔴 Red - Invalid format
    FOREIGN_SUPPLIER = "foreign"      # 🟡 Orange - Non-French supplier
    GOVERNMENT_ENTITY = "government"  # 🟡 Orange - Special entity
    ERROR = "error"                   # 🔴 Red - Technical error


class ExportBlockingLevel(str, Enum):
    """Export blocking level based on validation status"""
    AUTO_EXPORT_ALLOWED = "auto_allowed"          # 🟢 Automatic export OK
    WARNING_CONFIRMATION_REQUIRED = "warning"     # 🟡 Export with confirmation
    WARNING_EXPORT_ALLOWED = "warning_allowed"    # 🟡 Export with warning note
    BLOCKED_MANUAL_OVERRIDE_POSSIBLE = "blocked_override"  # 🔴 Blocked, override possible
    BLOCKED_CORRECTION_REQUIRED = "blocked_correction"     # 🔴 Blocked, must correct


class UserOverrideAction(str, Enum):
    """User actions for handling validation failures"""
    MANUAL_CORRECTION = "manual_correction"    # User corrected SIRET
    ACCEPT_WITH_WARNING = "accept_warning"     # Accept despite warning
    FORCE_OVERRIDE = "force_override"          # Accept despite error
    REJECT_INVOICE = "reject_invoice"          # Reject as invalid
    MARK_FOREIGN = "mark_foreign"             # Mark as foreign supplier
    DOCUMENT_EXCEPTION = "document_exception"  # Document special case


class ComplianceRisk(str, Enum):
    """Legal compliance risk levels"""
    LOW = "low"           # Minimal risk
    MEDIUM = "medium"     # Some audit risk
    HIGH = "high"         # Significant compliance risk
    CRITICAL = "critical" # Major liability exposure


class SIRETValidationRecord(Base):
    """
    Comprehensive SIRET validation record with audit trail
    """
    __tablename__ = "siret_validation_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Invoice reference
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # SIRET information
    extracted_siret = Column(String(14), nullable=False)
    cleaned_siret = Column(String(14), nullable=True)  # After auto-correction
    corrected_siret = Column(String(14), nullable=True)  # Manual correction
    
    # Validation results
    validation_status = Column(String, nullable=False)  # SIRETValidationStatus
    blocking_level = Column(String, nullable=False)     # ExportBlockingLevel
    compliance_risk = Column(String, nullable=False)    # ComplianceRisk
    
    # INSEE API response
    insee_response = Column(JSON, nullable=True)
    insee_company_name = Column(String(255), nullable=True)
    insee_company_status = Column(String(50), nullable=True)
    insee_activity_code = Column(String(10), nullable=True)
    insee_closure_date = Column(DateTime, nullable=True)
    
    # Extracted data comparison
    extracted_company_name = Column(String(255), nullable=True)
    name_similarity_score = Column(Integer, nullable=True)  # 0-100
    
    # User decision tracking
    user_action = Column(String, nullable=True)         # UserOverrideAction
    user_justification = Column(Text, nullable=True)
    override_timestamp = Column(DateTime, nullable=True)
    
    # Export status
    export_blocked = Column(Boolean, default=False)
    export_warnings = Column(JSON, nullable=True)
    export_notes = Column(Text, nullable=True)
    
    # Compliance documentation
    liability_warning_shown = Column(Boolean, default=False)
    liability_warning_acknowledged = Column(Boolean, default=False)
    compliance_notes = Column(Text, nullable=True)
    
    # Technical details
    auto_correction_attempted = Column(Boolean, default=False)
    auto_correction_success = Column(Boolean, default=False)
    validation_attempt_count = Column(Integer, default=1)
    last_validation_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="siret_validations")
    user = relationship("User")


class SIRETComplianceGuidance(Base):
    """
    French compliance guidance and legal implications for SIRET validation
    """
    __tablename__ = "siret_compliance_guidance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Scenario identification
    validation_status = Column(String, nullable=False)  # SIRETValidationStatus
    scenario_name = Column(String(100), nullable=False)
    
    # French compliance guidance
    legal_implications = Column(Text, nullable=False)
    tax_deduction_risk = Column(String, nullable=False)  # ComplianceRisk
    audit_risk_level = Column(String, nullable=False)    # ComplianceRisk
    
    # Recommended actions
    recommended_actions = Column(JSON, nullable=False)
    user_options = Column(JSON, nullable=False)
    documentation_requirements = Column(JSON, nullable=False)
    
    # Display messages
    error_message_fr = Column(Text, nullable=False)
    warning_message_fr = Column(Text, nullable=True)
    guidance_text_fr = Column(Text, nullable=False)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SIRETValidationSettings(Base):
    """
    Configuration settings for SIRET validation behavior
    """
    __tablename__ = "siret_validation_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Organization settings
    organization_id = Column(UUID(as_uuid=True), nullable=True)  # For multi-tenant
    
    # Auto-correction settings
    enable_auto_correction = Column(Boolean, default=True)
    auto_retry_count = Column(Integer, default=3)
    auto_clean_formatting = Column(Boolean, default=True)
    
    # Blocking behavior
    block_invalid_siret_export = Column(Boolean, default=True)
    require_manual_override = Column(Boolean, default=True)
    allow_foreign_supplier_bypass = Column(Boolean, default=True)
    
    # Name matching tolerance
    name_similarity_threshold = Column(Integer, default=80)  # 0-100
    require_exact_name_match = Column(Boolean, default=False)
    
    # Risk tolerance
    max_acceptable_risk = Column(String, default="medium")  # ComplianceRisk
    require_justification_for_overrides = Column(Boolean, default=True)
    
    # Compliance tracking
    enable_liability_warnings = Column(Boolean, default=True)
    require_warning_acknowledgment = Column(Boolean, default=True)
    track_all_decisions = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Helper functions for determining export status and risk

def determine_export_status(validation_status: SIRETValidationStatus) -> ExportBlockingLevel:
    """Determine export blocking level based on validation status - allows export with warnings for invalid SIRET"""
    status_mapping = {
        SIRETValidationStatus.VALID: ExportBlockingLevel.AUTO_EXPORT_ALLOWED,
        SIRETValidationStatus.NOT_FOUND: ExportBlockingLevel.WARNING_EXPORT_ALLOWED,  # Changed: Allow export with warning
        SIRETValidationStatus.INACTIVE: ExportBlockingLevel.WARNING_EXPORT_ALLOWED,   # Changed: Allow export with warning
        SIRETValidationStatus.NAME_MISMATCH: ExportBlockingLevel.WARNING_EXPORT_ALLOWED,
        SIRETValidationStatus.MALFORMED: ExportBlockingLevel.WARNING_EXPORT_ALLOWED,  # Changed: Allow export with warning
        SIRETValidationStatus.FOREIGN_SUPPLIER: ExportBlockingLevel.WARNING_EXPORT_ALLOWED,
        SIRETValidationStatus.GOVERNMENT_ENTITY: ExportBlockingLevel.WARNING_EXPORT_ALLOWED,
        SIRETValidationStatus.ERROR: ExportBlockingLevel.WARNING_EXPORT_ALLOWED,      # Changed: Allow export with warning
    }
    return status_mapping.get(validation_status, ExportBlockingLevel.WARNING_EXPORT_ALLOWED)


def assess_compliance_risk(validation_status: SIRETValidationStatus, user_action: Optional[UserOverrideAction] = None) -> ComplianceRisk:
    """Assess compliance risk based on validation status and user action"""
    
    # Base risk by validation status
    base_risk = {
        SIRETValidationStatus.VALID: ComplianceRisk.LOW,
        SIRETValidationStatus.NOT_FOUND: ComplianceRisk.HIGH,
        SIRETValidationStatus.INACTIVE: ComplianceRisk.MEDIUM,
        SIRETValidationStatus.NAME_MISMATCH: ComplianceRisk.LOW,
        SIRETValidationStatus.MALFORMED: ComplianceRisk.HIGH,
        SIRETValidationStatus.FOREIGN_SUPPLIER: ComplianceRisk.MEDIUM,
        SIRETValidationStatus.GOVERNMENT_ENTITY: ComplianceRisk.LOW,
        SIRETValidationStatus.ERROR: ComplianceRisk.CRITICAL,
    }.get(validation_status, ComplianceRisk.HIGH)
    
    # Adjust risk based on user action
    if user_action == UserOverrideAction.FORCE_OVERRIDE:
        if base_risk == ComplianceRisk.HIGH:
            return ComplianceRisk.CRITICAL
        elif base_risk == ComplianceRisk.MEDIUM:
            return ComplianceRisk.HIGH
    
    elif user_action == UserOverrideAction.DOCUMENT_EXCEPTION:
        # Proper documentation reduces risk
        if base_risk == ComplianceRisk.HIGH:
            return ComplianceRisk.MEDIUM
        elif base_risk == ComplianceRisk.CRITICAL:
            return ComplianceRisk.HIGH
    
    return base_risk


def get_traffic_light_color(validation_status: SIRETValidationStatus) -> str:
    """Get traffic light color for UI display"""
    green_statuses = [SIRETValidationStatus.VALID]
    orange_statuses = [
        SIRETValidationStatus.INACTIVE,
        SIRETValidationStatus.NAME_MISMATCH,
        SIRETValidationStatus.FOREIGN_SUPPLIER,
        SIRETValidationStatus.GOVERNMENT_ENTITY
    ]
    red_statuses = [
        SIRETValidationStatus.NOT_FOUND,
        SIRETValidationStatus.MALFORMED,
        SIRETValidationStatus.ERROR
    ]
    
    if validation_status in green_statuses:
        return "green"
    elif validation_status in orange_statuses:
        return "orange"
    elif validation_status in red_statuses:
        return "red"
    else:
        return "red"  # Default to red for unknown statuses