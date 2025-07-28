"""
TVA-specific database models for French compliance

This module defines database models for TVA validation, product category mapping,
and TVA-specific compliance tracking.
"""

from sqlalchemy import Column, String, Boolean, Integer, Numeric, Date, DateTime, Text, JSON, ForeignKey, UUID, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from typing import Dict, List, Tuple, Any, Optional
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from enum import Enum

from core.database import Base

class TVAProductCategory(Base):
    """
    French TVA product categories for automatic rate determination
    Maps products/services to appropriate TVA rates based on French tax law
    """
    __tablename__ = "tva_product_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_code = Column(String(50), nullable=False, unique=True)
    category_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # TVA rate information
    standard_tva_rate = Column(Numeric(5, 2), nullable=False)  # 20.0, 10.0, 5.5, 2.1, 0.0
    rate_justification = Column(Text, nullable=True)
    
    # Product identification
    keywords = Column(JSON, nullable=True)  # Keywords for automatic detection
    naf_codes = Column(JSON, nullable=True)  # Associated NAF codes
    product_codes = Column(JSON, nullable=True)  # Product codes (EAN, etc.)
    
    # Classification
    parent_category_id = Column(UUID(as_uuid=True), ForeignKey("tva_product_categories.id"), nullable=True)
    category_level = Column(Integer, nullable=False, default=1)  # 1=main, 2=sub, 3=detailed
    
    # Legal references
    legal_reference = Column(String(200), nullable=True)  # CGI article, etc.
    effective_from = Column(Date, nullable=True)
    effective_until = Column(Date, nullable=True)
    
    # Special conditions
    has_special_conditions = Column(Boolean, nullable=False, default=False)
    special_conditions = Column(JSON, nullable=True)
    exemption_conditions = Column(JSON, nullable=True)
    
    # Usage tracking
    usage_count = Column(Integer, nullable=False, default=0)
    last_used = Column(DateTime(timezone=True), nullable=True)
    confidence_score = Column(Numeric(5, 2), nullable=True)  # ML confidence score
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    parent_category = relationship("TVAProductCategory", remote_side=[id])
    subcategories = relationship("TVAProductCategory", back_populates="parent_category")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_tva_category_rate', 'standard_tva_rate'),
        Index('idx_tva_category_active', 'is_active'),
        Index('idx_tva_category_level', 'category_level'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "category_code": self.category_code,
            "category_name": self.category_name,
            "description": self.description,
            "standard_tva_rate": float(self.standard_tva_rate),
            "rate_justification": self.rate_justification,
            "keywords": self.keywords or [],
            "naf_codes": self.naf_codes or [],
            "category_level": self.category_level,
            "legal_reference": self.legal_reference,
            "has_special_conditions": self.has_special_conditions,
            "special_conditions": self.special_conditions or {},
            "usage_count": self.usage_count,
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "is_active": self.is_active
        }

class TVAValidationHistory(Base):
    """
    History of TVA validations for learning and improvement
    Tracks validation results to improve automatic rate detection
    """
    __tablename__ = "tva_validation_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    validation_id = Column(UUID(as_uuid=True), ForeignKey("french_compliance_validations.id", ondelete="SET NULL"), nullable=True)
    
    # Line item details
    line_item_index = Column(Integer, nullable=False)
    product_description = Column(Text, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    # TVA information
    declared_tva_rate = Column(Numeric(5, 2), nullable=True)
    detected_category_id = Column(UUID(as_uuid=True), ForeignKey("tva_product_categories.id"), nullable=True)
    suggested_tva_rate = Column(Numeric(5, 2), nullable=True)
    actual_tva_amount = Column(Numeric(10, 2), nullable=True)
    calculated_tva_amount = Column(Numeric(10, 2), nullable=True)
    
    # Validation results
    rate_is_correct = Column(Boolean, nullable=True)
    calculation_is_correct = Column(Boolean, nullable=True)
    confidence_score = Column(Numeric(5, 2), nullable=True)
    validation_errors = Column(JSON, nullable=True)
    validation_warnings = Column(JSON, nullable=True)
    
    # Learning data
    manual_override = Column(Boolean, nullable=False, default=False)
    correct_category_id = Column(UUID(as_uuid=True), ForeignKey("tva_product_categories.id"), nullable=True)
    correct_tva_rate = Column(Numeric(5, 2), nullable=True)
    feedback_provided = Column(Boolean, nullable=False, default=False)
    
    # Audit
    validated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    validated_by = Column(String(100), nullable=True)  # System or user ID
    
    # Relationships
    detected_category = relationship("TVAProductCategory", foreign_keys=[detected_category_id])
    correct_category = relationship("TVAProductCategory", foreign_keys=[correct_category_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_tva_history_invoice', 'invoice_id'),
        Index('idx_tva_history_category', 'detected_category_id'),
        Index('idx_tva_history_rate', 'declared_tva_rate'),
        Index('idx_tva_history_date', 'validated_at'),
    )

class TVAExemptionRule(Base):
    """
    TVA exemption rules and conditions
    Defines specific conditions for TVA exemptions under French law
    """
    __tablename__ = "tva_exemption_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exemption_code = Column(String(20), nullable=False, unique=True)
    exemption_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Legal basis
    legal_reference = Column(String(200), nullable=False)  # CGI article
    cgi_article = Column(String(50), nullable=True)
    eu_directive = Column(String(100), nullable=True)
    
    # Conditions
    eligibility_conditions = Column(JSON, nullable=False)
    required_documents = Column(JSON, nullable=True)
    validation_rules = Column(JSON, nullable=False)
    
    # Business context
    applicable_sectors = Column(JSON, nullable=True)  # NAF codes
    applicable_categories = Column(JSON, nullable=True)  # Product categories
    geographic_scope = Column(String(50), nullable=True)  # France, EU, International
    
    # Validation
    automatic_detection = Column(Boolean, nullable=False, default=False)
    detection_keywords = Column(JSON, nullable=True)
    confidence_threshold = Column(Numeric(5, 2), nullable=True)
    
    # Usage tracking
    usage_count = Column(Integer, nullable=False, default=0)
    success_rate = Column(Numeric(5, 2), nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    effective_from = Column(Date, nullable=True)
    effective_until = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def check_eligibility(self, invoice_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if invoice meets exemption conditions
        
        Args:
            invoice_data: Invoice data dictionary
            
        Returns:
            Tuple of (is_eligible, reasons)
        """
        reasons = []
        
        if not self.is_active:
            return False, ["Exemption rule is not active"]
        
        # Check effective dates
        if self.effective_from and datetime.now().date() < self.effective_from:
            return False, ["Exemption not yet effective"]
        
        if self.effective_until and datetime.now().date() > self.effective_until:
            return False, ["Exemption has expired"]
        
        # Validate against conditions (simplified - would need full implementation)
        for condition in self.eligibility_conditions:
            # This would contain the actual validation logic
            pass
        
        return len(reasons) == 0, reasons

class TVARateHistory(Base):
    """
    Historical TVA rates for audit and compliance
    Tracks changes in French TVA rates over time
    """
    __tablename__ = "tva_rate_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rate_type = Column(String(50), nullable=False)  # standard, reduced_1, reduced_2, super_reduced
    rate_value = Column(Numeric(5, 2), nullable=False)
    description = Column(Text, nullable=True)
    
    # Legal information
    legal_reference = Column(String(200), nullable=True)
    decree_number = Column(String(100), nullable=True)
    
    # Effective period
    effective_from = Column(Date, nullable=False)
    effective_until = Column(Date, nullable=True)
    
    # Context
    change_reason = Column(Text, nullable=True)
    affected_categories = Column(JSON, nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_tva_rate_type', 'rate_type'),
        Index('idx_tva_rate_effective', 'effective_from', 'effective_until'),
    )

# Default French TVA product categories data
FRENCH_TVA_PRODUCT_CATEGORIES = [
    # Standard rate (20%)
    {
        "category_code": "GENERAL_GOODS",
        "category_name": "Biens généraux",
        "description": "Marchandises générales soumises au taux normal",
        "standard_tva_rate": 20.0,
        "keywords": ["marchandise", "produit", "bien", "matériel", "équipement"],
        "legal_reference": "CGI art. 278",
        "category_level": 1
    },
    {
        "category_code": "SERVICES_GENERAL",
        "category_name": "Services généraux",
        "description": "Prestations de services soumises au taux normal",
        "standard_tva_rate": 20.0,
        "keywords": ["service", "prestation", "conseil", "maintenance", "réparation"],
        "legal_reference": "CGI art. 256",
        "category_level": 1
    },
    
    # Reduced rate 1 (10%)
    {
        "category_code": "RESTAURANT",
        "category_name": "Restauration",
        "description": "Services de restauration et consommation sur place",
        "standard_tva_rate": 10.0,
        "keywords": ["restaurant", "café", "bar", "repas", "consommation", "menu", "plat"],
        "naf_codes": ["5610A", "5610C", "5630Z"],
        "legal_reference": "CGI art. 279 bis",
        "category_level": 1
    },
    {
        "category_code": "ACCOMMODATION",
        "category_name": "Hébergement",
        "description": "Services d'hébergement touristique",
        "standard_tva_rate": 10.0,
        "keywords": ["hôtel", "chambre", "nuitée", "hébergement", "gîte", "camping"],
        "naf_codes": ["5510Z", "5520Z", "5530Z"],
        "legal_reference": "CGI art. 279 bis",
        "category_level": 1
    },
    
    # Reduced rate 2 (5.5%)
    {
        "category_code": "FOOD_BASIC",
        "category_name": "Produits alimentaires de base",
        "description": "Produits alimentaires de première nécessité",
        "standard_tva_rate": 5.5,
        "keywords": ["pain", "lait", "beurre", "œuf", "sucre", "farine", "riz", "pâtes"],
        "legal_reference": "CGI art. 278-0 bis",
        "category_level": 1
    },
    {
        "category_code": "BOOKS",
        "category_name": "Livres et publications",
        "description": "Livres, journaux et publications périodiques",
        "standard_tva_rate": 5.5,
        "keywords": ["livre", "journal", "magazine", "publication", "manuel", "guide"],
        "legal_reference": "CGI art. 278-0 bis",
        "category_level": 1
    },
    
    # Super reduced rate (2.1%)
    {
        "category_code": "PRESS",
        "category_name": "Presse quotidienne",
        "description": "Presse quotidienne et assimilée",
        "standard_tva_rate": 2.1,
        "keywords": ["journal quotidien", "presse quotidienne", "quotidien"],
        "legal_reference": "CGI art. 298 septies",
        "category_level": 1
    },
    {
        "category_code": "MEDICINE_REIMBURSED",
        "category_name": "Médicaments remboursables",
        "description": "Médicaments remboursés par la Sécurité Sociale",
        "standard_tva_rate": 2.1,
        "keywords": ["médicament remboursé", "prescription", "sécurité sociale"],
        "legal_reference": "CGI art. 278-0 bis",
        "category_level": 1,
        "has_special_conditions": True,
        "special_conditions": {
            "requires_prescription": True,
            "social_security_reimbursed": True
        }
    },
    
    # Exempt (0%)
    {
        "category_code": "MEDICAL_SERVICES",
        "category_name": "Services médicaux",
        "description": "Prestations médicales et paramédicales",
        "standard_tva_rate": 0.0,
        "keywords": ["consultation", "médecin", "dentiste", "kinésithérapeute", "infirmier"],
        "naf_codes": ["8610Z", "8621Z", "8622A", "8622B", "8622C"],
        "legal_reference": "CGI art. 261",
        "category_level": 1,
        "exemption_conditions": {
            "provider_qualification": "required",
            "medical_purpose": "required"
        }
    },
    {
        "category_code": "EDUCATION",
        "category_name": "Enseignement",
        "description": "Services d'enseignement et de formation",
        "standard_tva_rate": 0.0,
        "keywords": ["formation", "cours", "enseignement", "école", "université"],
        "naf_codes": ["8510Z", "8520Z", "8531Z", "8532Z"],
        "legal_reference": "CGI art. 261",
        "category_level": 1,
        "exemption_conditions": {
            "education_purpose": "required",
            "certified_provider": "preferred"
        }
    }
]

# Default exemption rules
FRENCH_TVA_EXEMPTION_RULES = [
    {
        "exemption_code": "EXPORT_EU",
        "exemption_name": "Export hors Union Européenne",
        "description": "Livraisons de biens exportés hors de l'Union Européenne",
        "legal_reference": "CGI art. 262 ter",
        "cgi_article": "262 ter",
        "eligibility_conditions": [
            "goods_physically_exported",
            "customer_outside_eu",
            "export_documentation"
        ],
        "required_documents": [
            "Déclaration d'exportation",
            "Preuve de sortie du territoire de l'UE",
            "Document de transport"
        ],
        "validation_rules": {
            "customer_country_check": "mandatory",
            "export_proof_check": "mandatory"
        }
    },
    {
        "exemption_code": "INTRA_EU",
        "exemption_name": "Livraisons intracommunautaires",
        "description": "Livraisons de biens entre assujettis de l'Union Européenne",
        "legal_reference": "CGI art. 262 ter",
        "eu_directive": "2006/112/CE",
        "eligibility_conditions": [
            "customer_eu_vat_number",
            "goods_transported_to_eu",
            "customer_identified_for_vat"
        ],
        "required_documents": [
            "Numéro de TVA intracommunautaire du client",
            "Justificatif de transport vers autre État membre"
        ],
        "validation_rules": {
            "eu_vat_number_format": "mandatory",
            "transport_proof": "recommended"
        }
    }
]