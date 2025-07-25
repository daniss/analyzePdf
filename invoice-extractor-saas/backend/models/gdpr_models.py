"""
GDPR-Compliant Database Models for InvoiceAI
Implements data protection by design and by default (GDPR Article 25)
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from core.database import Base


class DataSubjectType(enum.Enum):
    """Data subject types for GDPR compliance"""
    BUSINESS_CONTACT = "business_contact"
    INDIVIDUAL_CONTRACTOR = "individual_contractor" 
    EMPLOYEE = "employee"
    CUSTOMER_REPRESENTATIVE = "customer_representative"


class ProcessingPurpose(enum.Enum):
    """Legal basis and purposes for data processing under GDPR Article 6"""
    LEGITIMATE_INTEREST = "legitimate_interest"  # Article 6(1)(f) - invoice processing
    CONTRACT_PERFORMANCE = "contract_performance"  # Article 6(1)(b) - service delivery
    LEGAL_OBLIGATION = "legal_obligation"  # Article 6(1)(c) - accounting requirements
    CONSENT = "consent"  # Article 6(1)(a) - explicit consent


class DataCategory(enum.Enum):
    """Categories of personal data under GDPR"""
    IDENTIFYING_DATA = "identifying_data"  # Names, addresses
    CONTACT_DATA = "contact_data"  # Email, phone
    FINANCIAL_DATA = "financial_data"  # Tax IDs, payment info
    BUSINESS_DATA = "business_data"  # Company information


class RetentionStatus(enum.Enum):
    """Data retention lifecycle status"""
    ACTIVE = "active"
    RETENTION_PERIOD = "retention_period"
    SCHEDULED_DELETION = "scheduled_deletion"
    DELETED = "deleted"
    LEGAL_HOLD = "legal_hold"


class AuditEventType(enum.Enum):
    """Types of audit events for GDPR compliance"""
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    DATA_EXPORT = "data_export"
    CONSENT_GIVEN = "consent_given"
    CONSENT_WITHDRAWN = "consent_withdrawn"
    BREACH_DETECTED = "breach_detected"
    RETENTION_POLICY_APPLIED = "retention_policy_applied"


class DataSubject(Base):
    """
    Data subjects whose personal data is processed
    Implements GDPR Article 4(1) data subject definition
    """
    __tablename__ = "data_subjects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Encrypted personal data fields
    name_encrypted = Column(Text, nullable=False)  # AES encrypted
    email_encrypted = Column(Text, nullable=True)  # AES encrypted
    phone_encrypted = Column(Text, nullable=True)  # AES encrypted
    address_encrypted = Column(Text, nullable=True)  # AES encrypted
    
    # Non-encrypted metadata
    data_subject_type = Column(SQLEnum(DataSubjectType), nullable=False)
    source_system = Column(String(100), nullable=False, default="invoiceai")
    
    # GDPR compliance fields
    consent_given = Column(Boolean, default=False)
    consent_date = Column(DateTime(timezone=True), nullable=True)
    consent_withdrawn = Column(Boolean, default=False)
    consent_withdrawal_date = Column(DateTime(timezone=True), nullable=True)
    
    # Data minimization - only store necessary fields
    processing_purposes = Column(JSON, nullable=False)  # List of ProcessingPurpose values
    data_categories = Column(JSON, nullable=False)  # List of DataCategory values
    
    # Retention management
    retention_status = Column(SQLEnum(RetentionStatus), default=RetentionStatus.ACTIVE)
    retention_until = Column(DateTime(timezone=True), nullable=True)
    legal_basis = Column(String(100), nullable=False)  # GDPR Article 6 basis
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    invoices = relationship("Invoice", back_populates="data_subjects", secondary="invoice_data_subjects")
    audit_logs = relationship("AuditLog", back_populates="data_subject")


class Invoice(Base):
    """
    GDPR-compliant invoice storage with encryption and audit trails
    """
    __tablename__ = "invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # File metadata
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA-256 for integrity
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    
    # Encrypted storage path (for S3/R2)
    encrypted_storage_path = Column(Text, nullable=True)
    encryption_key_id = Column(String(255), nullable=True)  # KMS key ID
    
    # Processing status
    processing_status = Column(String(20), default="pending")
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Encrypted extracted data
    extracted_data_encrypted = Column(Text, nullable=True)  # JSON encrypted with AES
    
    # GDPR compliance
    legal_basis = Column(String(100), nullable=False, default="legitimate_interest")
    processing_purposes = Column(JSON, nullable=False)
    data_controller_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Retention management
    retention_policy_id = Column(UUID(as_uuid=True), ForeignKey("retention_policies.id"))
    retention_until = Column(DateTime(timezone=True), nullable=True)
    retention_status = Column(SQLEnum(RetentionStatus), default=RetentionStatus.ACTIVE)
    
    # Cross-border transfer tracking
    transferred_to_third_country = Column(Boolean, default=True)  # Claude API in US
    transfer_mechanism = Column(String(50), default="standard_contractual_clauses")
    transfer_risk_assessment_id = Column(UUID(as_uuid=True), ForeignKey("transfer_assessments.id"))
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    data_controller = relationship("User", foreign_keys=[data_controller_id])
    data_subjects = relationship("DataSubject", back_populates="invoices", secondary="invoice_data_subjects")
    retention_policy = relationship("RetentionPolicy")
    transfer_assessment = relationship("TransferRiskAssessment")
    audit_logs = relationship("AuditLog", back_populates="invoice")


class InvoiceDataSubject(Base):
    """
    Junction table linking invoices to data subjects
    """
    __tablename__ = "invoice_data_subjects"
    
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), primary_key=True)
    data_subject_id = Column(UUID(as_uuid=True), ForeignKey("data_subjects.id"), primary_key=True)
    role_in_invoice = Column(String(50), nullable=False)  # vendor, customer, contact
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RetentionPolicy(Base):
    """
    Data retention policies implementing GDPR Article 5(1)(e) storage limitation
    """
    __tablename__ = "retention_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Retention periods
    retention_period_months = Column(Integer, nullable=False)  # French accounting: 10 years = 120 months
    deletion_grace_period_days = Column(Integer, default=30)  # Grace period before deletion
    
    # Applicable data types
    applies_to_data_categories = Column(JSON, nullable=False)  # List of DataCategory values
    applies_to_processing_purposes = Column(JSON, nullable=False)
    
    # Legal basis for retention
    legal_basis = Column(Text, nullable=False)  # French Commercial Code Article L123-22
    jurisdiction = Column(String(10), default="FR")
    
    # Policy status
    is_active = Column(Boolean, default=True)
    effective_date = Column(DateTime(timezone=True), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))


class TransferRiskAssessment(Base):
    """
    Transfer risk assessments for third country transfers (GDPR Article 44-49)
    Required for Claude API transfers to US
    """
    __tablename__ = "transfer_assessments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Transfer details
    recipient_country = Column(String(2), nullable=False, default="US")
    recipient_organization = Column(String(100), nullable=False, default="Anthropic PBC")
    transfer_mechanism = Column(String(50), nullable=False)  # SCCs, adequacy_decision, etc.
    
    # Risk assessment
    risk_level = Column(String(10), nullable=False)  # low, medium, high
    risk_factors = Column(JSON, nullable=False)  # List of identified risks
    mitigation_measures = Column(JSON, nullable=False)  # List of safeguards
    
    # Legal documentation
    scc_version = Column(String(20), nullable=True)  # e.g., "2021/914/EU"
    adequacy_decision_date = Column(DateTime(timezone=True), nullable=True)
    
    # Assessment metadata
    assessment_date = Column(DateTime(timezone=True), nullable=False)
    assessor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    next_review_date = Column(DateTime(timezone=True), nullable=False)
    
    is_approved = Column(Boolean, default=False)
    approval_date = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """
    Comprehensive audit logging for GDPR Article 30 records of processing
    """
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event details
    event_type = Column(SQLEnum(AuditEventType), nullable=False)
    event_description = Column(Text, nullable=False)
    event_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # User context
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    user_ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Data context
    data_subject_id = Column(UUID(as_uuid=True), ForeignKey("data_subjects.id"), nullable=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    
    # Processing details
    processing_purpose = Column(String(100), nullable=True)
    legal_basis = Column(String(100), nullable=True)
    data_categories_accessed = Column(JSON, nullable=True)
    
    # Technical details
    system_component = Column(String(50), nullable=False)  # api, claude_processor, etc.
    operation_details = Column(JSON, nullable=True)  # Operation-specific metadata
    
    # Risk and compliance
    risk_level = Column(String(10), default="low")
    compliance_notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User")
    data_subject = relationship("DataSubject", back_populates="audit_logs")
    invoice = relationship("Invoice", back_populates="audit_logs")


class BreachIncident(Base):
    """
    Data breach incident tracking for GDPR Article 33/34 notifications
    """
    __tablename__ = "breach_incidents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Incident identification
    incident_reference = Column(String(50), nullable=False, unique=True)
    severity_level = Column(String(10), nullable=False)  # low, medium, high, critical
    
    # Breach details
    breach_type = Column(String(50), nullable=False)  # confidentiality, integrity, availability
    discovery_date = Column(DateTime(timezone=True), nullable=False)
    occurrence_date = Column(DateTime(timezone=True), nullable=True)
    
    # Affected data
    affected_data_categories = Column(JSON, nullable=False)
    estimated_affected_subjects = Column(Integer, nullable=True)
    data_subjects_identified = Column(Boolean, default=False)
    
    # Risk assessment
    likelihood_of_harm = Column(String(10), nullable=False)  # low, medium, high
    severity_of_harm = Column(String(10), nullable=False)
    risk_to_rights_freedoms = Column(Text, nullable=False)
    
    # Notification tracking
    supervisory_authority_notified = Column(Boolean, default=False)
    authority_notification_date = Column(DateTime(timezone=True), nullable=True)
    data_subjects_notified = Column(Boolean, default=False)
    subjects_notification_date = Column(DateTime(timezone=True), nullable=True)
    
    # Response and mitigation
    containment_measures = Column(Text, nullable=True)
    mitigation_measures = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(String(20), default="open")  # open, investigating, resolved, closed
    resolution_date = Column(DateTime(timezone=True), nullable=True)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ConsentRecord(Base):
    """
    Consent management for GDPR Article 7 requirements
    """
    __tablename__ = "consent_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Consent subject
    data_subject_id = Column(UUID(as_uuid=True), ForeignKey("data_subjects.id"), nullable=False)
    
    # Consent details
    consent_purposes = Column(JSON, nullable=False)  # Specific purposes
    consent_mechanism = Column(String(50), nullable=False)  # web_form, email, etc.
    consent_text = Column(Text, nullable=False)  # Exact consent text shown
    
    # Consent status
    is_active = Column(Boolean, default=True)
    consent_given_date = Column(DateTime(timezone=True), nullable=False)
    consent_withdrawn_date = Column(DateTime(timezone=True), nullable=True)
    withdrawal_reason = Column(Text, nullable=True)
    
    # Technical proof
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    consent_evidence = Column(JSON, nullable=True)  # Additional proof data
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    data_subject = relationship("DataSubject")