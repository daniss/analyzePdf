"""
French compliance validation models
Handles SIREN/SIRET validation, TVA compliance, and Plan Comptable Général mapping
"""

from sqlalchemy import Column, String, Boolean, Integer, Numeric, Date, DateTime, Text, JSON, ForeignKey, UUID, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from enum import Enum

from core.database import Base

class ValidationTrigger(str, Enum):
    USER = "user"
    BATCH = "batch"
    AUTO = "auto"
    EXPORT = "export"

class ValidationSource(str, Enum):
    ALGORITHM = "algorithm"
    INSEE_API = "insee_api"
    CACHE = "cache"
    MANUAL = "manual"

class TVAValidationMethod(str, Enum):
    FORMAT = "format"
    API_CHECK = "api_check"
    CHECKSUM = "checksum"
    ALGORITHM = "algorithm"

class ErrorSeverity(str, Enum):
    CRITIQUE = "critique"
    ERREUR = "erreur"
    AVERTISSEMENT = "avertissement"
    INFO = "info"

class FrenchComplianceValidation(Base):
    """
    Comprehensive French compliance validation results for invoices
    Tracks SIREN/SIRET, TVA, sequential numbering, and mandatory fields validation
    """
    __tablename__ = "french_compliance_validations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    validation_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # SIREN validation results
    siren_number = Column(String(9), nullable=True)
    siren_is_valid = Column(Boolean, nullable=True)
    siren_validation_source = Column(String(20), nullable=True)  # ValidationSource
    siren_company_name = Column(Text, nullable=True)
    siren_legal_form = Column(String(100), nullable=True)
    siren_naf_code = Column(String(10), nullable=True)
    siren_creation_date = Column(Date, nullable=True)

    # SIRET validation results
    siret_number = Column(String(14), nullable=True)
    siret_is_valid = Column(Boolean, nullable=True)
    siret_establishment_active = Column(Boolean, nullable=True)
    siret_is_headquarters = Column(Boolean, nullable=True)
    siret_address_complete = Column(Text, nullable=True)
    siret_postal_code = Column(String(5), nullable=True)
    siret_city = Column(String(100), nullable=True)

    # TVA validation results
    tva_number = Column(String(15), nullable=True)
    tva_is_valid = Column(Boolean, nullable=True)
    tva_validation_method = Column(String(20), nullable=True)  # TVAValidationMethod
    tva_rate_expected = Column(Numeric(5, 2), nullable=True)
    tva_rate_found = Column(Numeric(5, 2), nullable=True)
    tva_calculation_valid = Column(Boolean, nullable=True)
    tva_amount_expected = Column(Numeric(10, 2), nullable=True)
    tva_amount_found = Column(Numeric(10, 2), nullable=True)

    # Sequential numbering validation
    invoice_sequence_number = Column(String(50), nullable=True)
    sequence_is_valid = Column(Boolean, nullable=True)
    sequence_gaps_detected = Column(JSON, nullable=True)
    sequence_series = Column(String(20), nullable=True)
    sequence_year = Column(Integer, nullable=True)

    # Mandatory fields validation
    mandatory_fields_score = Column(Numeric(5, 2), nullable=True)  # 0.00 to 100.00
    mandatory_fields_missing = Column(JSON, nullable=True)
    mandatory_fields_invalid = Column(JSON, nullable=True)

    # Overall compliance scores
    overall_compliance_score = Column(Numeric(5, 2), nullable=True)  # 0.00 to 100.00
    business_validation_score = Column(Numeric(5, 2), nullable=True)
    legal_requirements_score = Column(Numeric(5, 2), nullable=True)
    export_readiness_score = Column(Numeric(5, 2), nullable=True)

    # Validation errors and suggestions
    validation_errors = Column(JSON, nullable=True)
    validation_warnings = Column(JSON, nullable=True)
    validation_suggestions = Column(JSON, nullable=True)

    # Performance and audit tracking
    validation_duration_ms = Column(Integer, nullable=True)
    api_calls_made = Column(Integer, nullable=True, default=0)
    cache_hits = Column(Integer, nullable=True, default=0)
    validation_triggered_by = Column(String(50), nullable=True)  # ValidationTrigger

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    insee_api_calls = relationship("INSEEAPICall", back_populates="validation", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary"""
        return {
            "id": str(self.id),
            "invoice_id": str(self.invoice_id),
            "validation_timestamp": self.validation_timestamp.isoformat() if self.validation_timestamp else None,
            "siren": {
                "number": self.siren_number,
                "is_valid": self.siren_is_valid,
                "validation_source": self.siren_validation_source,
                "company_name": self.siren_company_name,
                "legal_form": self.siren_legal_form,
                "naf_code": self.siren_naf_code,
                "creation_date": self.siren_creation_date.isoformat() if self.siren_creation_date else None
            },
            "siret": {
                "number": self.siret_number,
                "is_valid": self.siret_is_valid,
                "establishment_active": self.siret_establishment_active,
                "is_headquarters": self.siret_is_headquarters,
                "address": self.siret_address_complete,
                "postal_code": self.siret_postal_code,
                "city": self.siret_city
            },
            "tva": {
                "number": self.tva_number,
                "is_valid": self.tva_is_valid,
                "validation_method": self.tva_validation_method,
                "rate_expected": float(self.tva_rate_expected) if self.tva_rate_expected else None,
                "rate_found": float(self.tva_rate_found) if self.tva_rate_found else None,
                "calculation_valid": self.tva_calculation_valid,
                "amount_expected": float(self.tva_amount_expected) if self.tva_amount_expected else None,
                "amount_found": float(self.tva_amount_found) if self.tva_amount_found else None
            },
            "sequence": {
                "number": self.invoice_sequence_number,
                "is_valid": self.sequence_is_valid,
                "gaps_detected": self.sequence_gaps_detected,
                "series": self.sequence_series,
                "year": self.sequence_year
            },
            "compliance_scores": {
                "overall": float(self.overall_compliance_score) if self.overall_compliance_score else None,
                "business_validation": float(self.business_validation_score) if self.business_validation_score else None,
                "legal_requirements": float(self.legal_requirements_score) if self.legal_requirements_score else None,
                "export_readiness": float(self.export_readiness_score) if self.export_readiness_score else None,
                "mandatory_fields": float(self.mandatory_fields_score) if self.mandatory_fields_score else None
            },
            "validation_results": {
                "errors": self.validation_errors or [],
                "warnings": self.validation_warnings or [],
                "suggestions": self.validation_suggestions or [],
                "missing_fields": self.mandatory_fields_missing or [],
                "invalid_fields": self.mandatory_fields_invalid or []
            },
            "performance": {
                "duration_ms": self.validation_duration_ms,
                "api_calls_made": self.api_calls_made,
                "cache_hits": self.cache_hits,
                "triggered_by": self.validation_triggered_by
            }
        }

class INSEEAPICall(Base):
    """
    Audit log for INSEE API calls
    Tracks API usage, performance, and responses for monitoring and compliance
    """
    __tablename__ = "insee_api_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    validation_id = Column(UUID(as_uuid=True), ForeignKey("french_compliance_validations.id", ondelete="SET NULL"), nullable=True)
    endpoint = Column(String(100), nullable=False)  # 'siren', 'siret', 'etablissements'
    request_identifier = Column(String(20), nullable=False)  # SIREN/SIRET number
    request_method = Column(String(10), nullable=False, default='GET')
    response_status = Column(Integer, nullable=True)
    response_data = Column(JSON, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    rate_limit_remaining = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    validation = relationship("FrenchComplianceValidation", back_populates="insee_api_calls")

class ComplianceSettings(Base):
    """
    Dynamic configuration for French compliance validation
    Allows updating validation rules without code changes
    """
    __tablename__ = "compliance_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setting_category = Column(String(50), nullable=False)  # 'tva_rates', 'mandatory_fields', etc.
    setting_name = Column(String(100), nullable=False)
    setting_value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('setting_category', 'setting_name', name='uq_compliance_settings_category_name'),
    )

    @classmethod
    def get_active_setting(cls, category: str, name: str, db_session) -> Optional['ComplianceSettings']:
        """Get active setting value"""
        now = datetime.utcnow()
        return db_session.query(cls).filter(
            cls.setting_category == category,
            cls.setting_name == name,
            cls.is_active == True,
            cls.effective_from <= now if cls.effective_from else True,
            cls.effective_until >= now if cls.effective_until else True
        ).first()

class PlanComptableGeneral(Base):
    """
    Plan Comptable Général account code mapping
    Maps invoice line items to French accounting chart of accounts
    """
    __tablename__ = "plan_comptable_general"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_code = Column(String(10), nullable=False, unique=True)
    account_name = Column(String(200), nullable=False)
    account_category = Column(String(50), nullable=False)  # 'charges', 'produits', 'actif', etc.
    account_subcategory = Column(String(100), nullable=True)
    vat_applicable = Column(Boolean, nullable=False, default=True)
    default_vat_rate = Column(Numeric(5, 2), nullable=True)
    keywords = Column(JSON, nullable=True)  # For automatic mapping
    sage_mapping = Column(String(20), nullable=True)  # Sage account code
    ebp_mapping = Column(String(20), nullable=True)   # EBP account code
    ciel_mapping = Column(String(20), nullable=True)  # Ciel account code
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def get_mapping_for_software(self, software: str) -> Optional[str]:
        """Get account code mapping for specific accounting software"""
        mapping_attr = f"{software.lower()}_mapping"
        return getattr(self, mapping_attr, None) if hasattr(self, mapping_attr) else None

class ValidationErrorPattern(Base):
    """
    Machine learning-based error pattern analysis
    Tracks common validation errors and their resolutions
    """
    __tablename__ = "validation_error_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    error_type = Column(String(50), nullable=False)
    error_subtype = Column(String(100), nullable=True)
    pattern_data = Column(JSON, nullable=False)
    suggested_fixes = Column(JSON, nullable=True)
    occurrence_count = Column(Integer, nullable=False, default=1)
    resolution_success_rate = Column(Numeric(5, 2), nullable=True)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def increment_occurrence(self):
        """Increment occurrence count and update last seen"""
        self.occurrence_count += 1
        self.last_seen = datetime.utcnow()

# French TVA rates as of 2024
FRENCH_TVA_RATES = {
    "STANDARD": 20.0,     # Taux normal
    "REDUCED_1": 10.0,    # Taux réduit (restauration, transport, hôtellerie)
    "REDUCED_2": 5.5,     # Taux réduit (alimentaire, livres, médicaments)
    "SUPER_REDUCED": 2.1, # Taux super réduit (presse, médicaments remboursables)
    "EXEMPT": 0.0         # Exonéré
}

# Mandatory fields for French invoice compliance
FRENCH_MANDATORY_FIELDS = {
    "invoice_number": {"required": True, "description": "Numéro de facture séquentiel"},
    "invoice_date": {"required": True, "description": "Date d'émission de la facture"},
    "vendor_name": {"required": True, "description": "Dénomination du fournisseur"},
    "vendor_address": {"required": True, "description": "Adresse du fournisseur"},
    "vendor_siren": {"required": True, "description": "Numéro SIREN du fournisseur"},
    "customer_name": {"required": True, "description": "Dénomination du client"},
    "customer_address": {"required": True, "description": "Adresse du client"},
    "amount_ht": {"required": True, "description": "Montant hors taxes"},
    "tva_amount": {"required": True, "description": "Montant de la TVA"},
    "amount_ttc": {"required": True, "description": "Montant toutes taxes comprises"},
    "tva_rate": {"required": True, "description": "Taux de TVA applicable"},
    "due_date": {"required": False, "description": "Date d'échéance de paiement"},
    "payment_terms": {"required": False, "description": "Conditions de paiement"}
}

# Error codes for French compliance validation
FRENCH_ERROR_CODES = {
    "SIREN_INVALID_FORMAT": {
        "code": "FR001",
        "severity": ErrorSeverity.ERREUR,
        "message": "Le numéro SIREN doit contenir exactement 9 chiffres",
        "fix_suggestion": "Vérifiez que le numéro SIREN contient 9 chiffres sans espaces ni caractères spéciaux"
    },
    "SIREN_INVALID_LUHN": {
        "code": "FR002", 
        "severity": ErrorSeverity.ERREUR,
        "message": "Le numéro SIREN ne respecte pas l'algorithme de Luhn",
        "fix_suggestion": "Vérifiez la saisie du numéro SIREN, il semble contenir une erreur de frappe"
    },
    "SIREN_NOT_FOUND_INSEE": {
        "code": "FR003",
        "severity": ErrorSeverity.AVERTISSEMENT,
        "message": "Le numéro SIREN n'existe pas dans la base INSEE",
        "fix_suggestion": "Vérifiez l'existence de l'entreprise ou contactez le fournisseur"
    },
    "SIRET_INVALID_FORMAT": {
        "code": "FR011",
        "severity": ErrorSeverity.ERREUR,
        "message": "Le numéro SIRET doit contenir exactement 14 chiffres",
        "fix_suggestion": "Vérifiez que le numéro SIRET contient 14 chiffres (SIREN + 5 chiffres)"
    },
    "SIRET_ESTABLISHMENT_CLOSED": {
        "code": "FR012",
        "severity": ErrorSeverity.AVERTISSEMENT,
        "message": "L'établissement correspondant au SIRET est fermé",
        "fix_suggestion": "Vérifiez avec le fournisseur son numéro SIRET actuel"
    },
    "TVA_RATE_INVALID": {
        "code": "FR021",
        "severity": ErrorSeverity.ERREUR,
        "message": "Le taux de TVA ne correspond pas aux taux français autorisés",
        "fix_suggestion": "Utilisez un taux de TVA français valide: 20%, 10%, 5.5%, 2.1% ou 0%"
    },
    "TVA_CALCULATION_ERROR": {
        "code": "FR022",
        "severity": ErrorSeverity.ERREUR,
        "message": "Le calcul de la TVA est incorrect",
        "fix_suggestion": "Vérifiez: Montant TTC = Montant HT + (Montant HT × Taux TVA)"
    },
    "SEQUENCE_NUMBER_GAP": {
        "code": "FR031",
        "severity": ErrorSeverity.CRITIQUE,
        "message": "Interruption détectée dans la numérotation séquentielle",
        "fix_suggestion": "Les factures doivent être numérotées de façon continue et chronologique"
    },
    "MANDATORY_FIELD_MISSING": {
        "code": "FR041",
        "severity": ErrorSeverity.ERREUR,
        "message": "Champ obligatoire manquant pour la conformité française",
        "fix_suggestion": "Complétez tous les champs obligatoires selon la réglementation française"
    }
}