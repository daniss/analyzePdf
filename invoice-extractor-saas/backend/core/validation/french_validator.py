"""
French Invoice Validation System

This module provides comprehensive validation for French invoice compliance,
including SIREN/SIRET validation, TVA number verification, and French
regulatory requirements validation.

Enhanced with comprehensive TVA validation engine for expert-comptable grade compliance.
"""

import re
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from schemas.invoice import InvoiceData, FrenchBusinessInfo, FrenchTVABreakdown
from core.validation.tva_validator import (
    FrenchTVAValidator, 
    TVAValidationResult,
    validate_invoice_tva
)
from core.french_compliance.validation_cache import get_validation_cache
from core.gdpr_audit import log_audit_event


class FrenchInvoiceValidator:
    """Validates French invoices for compliance with French regulations"""
    
    # Valid French TVA rates as of 2024
    VALID_TVA_RATES = [0.0, 2.1, 5.5, 10.0, 20.0]
    
    # French legal forms
    FRENCH_LEGAL_FORMS = [
        'SARL', 'SAS', 'SASU', 'EURL', 'SA', 'SNC', 'SCP', 'SEL',
        'SELARL', 'SELAFA', 'SELCA', 'SELAS', 'SEM', 'EPIC', 'EI',
        'EIRL', 'Micro-entreprise', 'Auto-entrepreneur'
    ]
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.tva_validator = FrenchTVAValidator()
        self.cache = get_validation_cache()
    
    async def validate_invoice(
        self, 
        invoice: InvoiceData, 
        db_session: AsyncSession,
        validation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive French invoice validation with enhanced TVA validation
        
        Args:
            invoice: Invoice data to validate
            db_session: Database session for audit logging
            validation_id: Optional validation ID for tracking
            
        Returns:
            Dict with validation results including errors, warnings, and compliance status
        """
        self.errors = []
        self.warnings = []
        
        # GDPR audit log
        await log_audit_event(
            db_session,
            user_id=None,
            operation_type="french_invoice_validation",
            data_categories=["invoice_data", "business_data", "financial_data"],
            risk_level="medium",
            details={
                "invoice_number": invoice.invoice_number,
                "validation_id": validation_id,
                "purpose": "french_compliance_validation"
            }
        )
        
        # Basic required fields validation
        self._validate_basic_fields(invoice)
        
        # French business information validation
        self._validate_vendor_info(invoice)
        self._validate_customer_info(invoice)
        
        # Enhanced TVA validation
        tva_result = await self._validate_comprehensive_tva(invoice, db_session, validation_id)
        
        # Sequential numbering validation
        self._validate_invoice_sequence(invoice)
        
        # Payment terms validation
        self._validate_payment_terms(invoice)
        
        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(tva_result)
        
        return {
            'is_compliant': len(self.errors) == 0 and tva_result.is_valid,
            'compliance_score': compliance_score,
            'errors': self.errors + tva_result.errors,
            'warnings': self.warnings + tva_result.warnings,
            'tva_validation': {
                'is_valid': tva_result.is_valid,
                'rate_valid': tva_result.rate_valid,
                'calculation_valid': tva_result.calculation_valid,
                'exemption_valid': tva_result.exemption_valid,
                'compliance_score': tva_result.compliance_score,
                'suggestions': tva_result.suggestions,
                'product_category': tva_result.product_category.value if tva_result.product_category else None,
                'exemption_type': tva_result.exemption_type.value if tva_result.exemption_type else None
            },
            'french_specific_validation': True
        }
    
    def _validate_basic_fields(self, invoice: InvoiceData) -> None:
        """Validate basic required fields for French invoices"""
        
        # Invoice number is mandatory
        if not invoice.invoice_number:
            self.errors.append("Numéro de facture manquant (Invoice number missing)")
        
        # Invoice date is mandatory
        if not invoice.date:
            self.errors.append("Date de facture manquante (Invoice date missing)")
        else:
            if not self._validate_french_date_format(invoice.date):
                self.warnings.append("Format de date non standard - recommandé DD/MM/YYYY")
        
        # Currency should be EUR for French market
        if invoice.currency != 'EUR':
            self.warnings.append(f"Devise non-EUR détectée: {invoice.currency}. EUR recommandé pour le marché français.")
    
    def _validate_vendor_info(self, invoice: InvoiceData) -> None:
        """Validate vendor information for French compliance"""
        
        vendor = invoice.vendor
        if not vendor and not invoice.vendor_name:
            self.errors.append("Informations vendeur manquantes (Vendor information missing)")
            return
        
        if vendor:
            # Vendor name is mandatory
            if not vendor.name:
                self.errors.append("Nom du vendeur manquant (Vendor name missing)")
            
            # Address is mandatory
            if not vendor.address:
                self.errors.append("Adresse du vendeur manquante (Vendor address missing)")
            
            # SIREN validation for French vendors
            if vendor.siren_number:
                if not self._validate_siren(vendor.siren_number):
                    self.errors.append(f"Numéro SIREN invalide: {vendor.siren_number}")
            else:
                self.warnings.append("Numéro SIREN manquant - obligatoire pour les entreprises françaises")
            
            # SIRET validation
            if vendor.siret_number:
                if not self._validate_siret(vendor.siret_number):
                    self.errors.append(f"Numéro SIRET invalide: {vendor.siret_number}")
                
                # Check SIRET consistency with SIREN
                if vendor.siren_number and not vendor.siret_number.startswith(vendor.siren_number):
                    self.errors.append("Incohérence entre SIREN et SIRET")
            
            # TVA number validation
            if vendor.tva_number:
                if not self._validate_french_tva_number(vendor.tva_number):
                    self.errors.append(f"Numéro TVA français invalide: {vendor.tva_number}")
            
            # NAF code validation
            if vendor.naf_code:
                if not self._validate_naf_code(vendor.naf_code):
                    self.errors.append(f"Code NAF/APE invalide: {vendor.naf_code}")
            
            # Legal form validation
            if vendor.legal_form and vendor.legal_form not in self.FRENCH_LEGAL_FORMS:
                self.warnings.append(f"Forme juridique non reconnue: {vendor.legal_form}")
    
    def _validate_customer_info(self, invoice: InvoiceData) -> None:
        """Validate customer information"""
        
        customer = invoice.customer
        if not customer and not invoice.customer_name:
            self.errors.append("Informations client manquantes (Customer information missing)")
            return
        
        if customer:
            # Customer name is mandatory
            if not customer.name:
                self.errors.append("Nom du client manquant (Customer name missing)")
            
            # Address is mandatory
            if not customer.address:
                self.errors.append("Adresse du client manquante (Customer address missing)")
            
            # For B2B transactions, SIREN is recommended
            if customer.siren_number:
                if not self._validate_siren(customer.siren_number):
                    self.errors.append(f"Numéro SIREN client invalide: {customer.siren_number}")
            
            # SIRET validation if provided
            if customer.siret_number:
                if not self._validate_siret(customer.siret_number):
                    self.errors.append(f"Numéro SIRET client invalide: {customer.siret_number}")
    
    async def _validate_comprehensive_tva(
        self, 
        invoice: InvoiceData, 
        db_session: AsyncSession,
        validation_id: Optional[str] = None
    ) -> TVAValidationResult:
        """
        Comprehensive TVA validation using the enhanced TVA validator
        
        Args:
            invoice: Invoice data to validate
            db_session: Database session
            validation_id: Optional validation ID
            
        Returns:
            TVA validation result
        """
        return await self.tva_validator.validate_invoice_tva(
            invoice, 
            db_session, 
            validation_id
        )
    
    def _validate_tva_compliance(self, invoice: InvoiceData) -> None:
        """Legacy TVA validation - now replaced by comprehensive TVA validator"""
        
        # This method is kept for backward compatibility but now uses simplified checks
        # The main TVA validation is done by _validate_comprehensive_tva
        
        # Check if TVA breakdown is provided
        if not invoice.tva_breakdown:
            self.warnings.append("Détail TVA par taux manquant - recommandé pour la conformité")
        
        # Basic rate validation
        for tva_item in invoice.tva_breakdown:
            if tva_item.rate not in self.VALID_TVA_RATES:
                self.errors.append(f"Taux de TVA invalide: {tva_item.rate}%. Taux valides: {self.VALID_TVA_RATES}")
        
        # Basic line item validation
        for i, item in enumerate(invoice.line_items):
            if item.tva_rate is None:
                self.warnings.append(f"Taux TVA manquant pour l'article {i+1}: {item.description}")
            elif item.tva_rate not in self.VALID_TVA_RATES:
                self.errors.append(f"Taux TVA invalide pour l'article {i+1}: {item.tva_rate}%")
    
    def _validate_invoice_sequence(self, invoice: InvoiceData) -> None:
        """Validate invoice sequential numbering (French requirement)"""
        
        if not invoice.invoice_sequence_number:
            self.warnings.append("Numéro séquentiel manquant - obligatoire pour la conformité française")
        
        # Sequential numbering pattern validation
        if invoice.invoice_number:
            # Check if invoice number contains year
            current_year = str(datetime.now().year)
            if current_year not in invoice.invoice_number:
                self.warnings.append("Année manquante dans le numéro de facture - recommandé pour la traçabilité")
    
    def _validate_payment_terms(self, invoice: InvoiceData) -> None:
        """Validate payment terms and mandatory clauses"""
        
        # Payment terms should be specified
        if not invoice.payment_terms:
            self.warnings.append("Conditions de paiement manquantes")
        
        # Late payment penalties clause is mandatory for B2B
        if not invoice.late_payment_penalties:
            self.errors.append("Clause de pénalités de retard manquante (obligatoire pour B2B)")
        
        # Recovery fees clause is mandatory for B2B
        if not invoice.recovery_fees:
            self.errors.append("Clause d'indemnité forfaitaire de recouvrement manquante (40€ obligatoire pour B2B)")
    
    def _validate_siren(self, siren: str) -> bool:
        """Validate SIREN number using Luhn algorithm"""
        
        if not re.match(r'^\d{9}$', siren):
            return False
        
        # Apply Luhn algorithm
        return self._luhn_check(siren)
    
    def _validate_siret(self, siret: str) -> bool:
        """Validate SIRET number"""
        
        if not re.match(r'^\d{14}$', siret):
            return False
        
        # SIRET = SIREN (9 digits) + NIC (5 digits)
        siren = siret[:9]
        nic = siret[9:]
        
        # Validate SIREN part
        if not self._validate_siren(siren):
            return False
        
        # Validate NIC part (simplified - full validation requires INSEE database)
        return len(nic) == 5 and nic.isdigit()
    
    def _validate_french_tva_number(self, tva_number: str) -> bool:
        """Validate French TVA number format"""
        
        if not re.match(r'^FR\d{11}$', tva_number):
            return False
        
        # Extract SIREN from TVA number (last 9 digits)
        siren = tva_number[4:]
        return self._validate_siren(siren)
    
    def _validate_naf_code(self, naf_code: str) -> bool:
        """Validate NAF/APE code format"""
        
        return bool(re.match(r'^\d{4}[A-Z]$', naf_code))
    
    def _validate_french_date_format(self, date_str: str) -> bool:
        """Check if date follows French format (DD/MM/YYYY)"""
        
        try:
            # Try French format first
            datetime.strptime(date_str, '%d/%m/%Y')
            return True
        except ValueError:
            try:
                # Try ISO format
                datetime.strptime(date_str, '%Y-%m-%d')
                return True
            except ValueError:
                return False
    
    def _luhn_check(self, number: str) -> bool:
        """Implement Luhn algorithm for SIREN validation"""
        
        def luhn_checksum(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d*2))
            return checksum % 10
        
        return luhn_checksum(number) == 0
    
    def _calculate_compliance_score(self, tva_result: TVAValidationResult) -> float:
        """Calculate compliance score based on errors, warnings, and TVA validation"""
        
        # Base score
        score = 100.0
        
        # Deduct for general errors (more severe)
        score -= len(self.errors) * 8
        
        # Deduct for general warnings (less severe)
        score -= len(self.warnings) * 2
        
        # Weight TVA compliance heavily (30% of total score)
        tva_weight = 0.3
        general_weight = 0.7
        
        # Calculate weighted score
        general_score = max(0.0, score)
        tva_score = tva_result.compliance_score
        
        weighted_score = (general_score * general_weight) + (tva_score * tva_weight)
        
        # Ensure score doesn't go below 0 or above 100
        return max(0.0, min(100.0, weighted_score))


async def validate_french_invoice(
    invoice: InvoiceData, 
    db_session: AsyncSession,
    validation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to validate a French invoice with comprehensive TVA validation
    
    Args:
        invoice: InvoiceData object to validate
        db_session: Database session for audit logging
        validation_id: Optional validation ID for tracking
        
    Returns:
        Dict with validation results including enhanced TVA validation
    """
    validator = FrenchInvoiceValidator()
    return await validator.validate_invoice(invoice, db_session, validation_id)

def validate_french_invoice_sync(invoice: InvoiceData) -> Dict[str, Any]:
    """
    Synchronous convenience function for backward compatibility
    Note: This provides basic validation without enhanced TVA features
    
    Args:
        invoice: InvoiceData object to validate
        
    Returns:
        Dict with basic validation results
    """
    validator = FrenchInvoiceValidator()
    
    # Run basic validation without database features
    validator._validate_basic_fields(invoice)
    validator._validate_vendor_info(invoice)
    validator._validate_customer_info(invoice)
    validator._validate_tva_compliance(invoice)  # Basic TVA validation only
    validator._validate_invoice_sequence(invoice)
    validator._validate_payment_terms(invoice)
    
    # Simple score calculation
    score = 100.0
    score -= len(validator.errors) * 10
    score -= len(validator.warnings) * 2
    
    return {
        'is_compliant': len(validator.errors) == 0,
        'compliance_score': max(0.0, score),
        'errors': validator.errors,
        'warnings': validator.warnings,
        'french_specific_validation': True,
        'note': 'Basic validation only - use async validate_french_invoice for full TVA validation'
    }


def check_mandatory_french_fields(invoice: InvoiceData) -> List[str]:
    """
    Quick check for mandatory French invoice fields
    
    Returns:
        List of missing mandatory fields
    """
    missing_fields = []
    
    # Basic fields
    if not invoice.invoice_number:
        missing_fields.append("Numéro de facture")
    if not invoice.date:
        missing_fields.append("Date de facture")
    
    # Vendor information
    if not (invoice.vendor or invoice.vendor_name):
        missing_fields.append("Informations vendeur")
    elif invoice.vendor:
        if not invoice.vendor.name:
            missing_fields.append("Nom vendeur")
        if not invoice.vendor.address:
            missing_fields.append("Adresse vendeur")
        if not invoice.vendor.siren_number:
            missing_fields.append("SIREN vendeur")
    
    # Customer information
    if not (invoice.customer or invoice.customer_name):
        missing_fields.append("Informations client")
    elif invoice.customer:
        if not invoice.customer.name:
            missing_fields.append("Nom client")
        if not invoice.customer.address:
            missing_fields.append("Adresse client")
    
    # Financial information
    if not invoice.total_ttc and not invoice.total:
        missing_fields.append("Montant total")
    
    # Mandatory clauses for B2B
    if not invoice.late_payment_penalties:
        missing_fields.append("Clause pénalités de retard")
    if not invoice.recovery_fees:
        missing_fields.append("Clause indemnité forfaitaire 40€")
    
    return missing_fields