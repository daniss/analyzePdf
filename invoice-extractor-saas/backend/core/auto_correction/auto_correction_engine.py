"""
Intelligent Error Recovery and Auto-Correction System

This module provides intelligent auto-correction capabilities for French invoice data,
enabling the "zero-decision workflow" for expert-comptables. It automatically fixes
common validation errors when confidence is high and queues uncertain corrections
for manual review.

Key Features:
- Confidence-based auto-correction decisions
- Machine learning from historical error patterns
- Complete audit trail for all corrections
- Manual review queue for uncertain cases
- Integration with French compliance validation
- Cost-effective processing optimization
"""

import asyncio
import logging
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_

from schemas.invoice import InvoiceData, FrenchBusinessInfo
from models.french_compliance import (
    ValidationErrorPattern,
    ErrorSeverity,
    FRENCH_TVA_RATES,
    FRENCH_ERROR_CODES
)
from core.french_compliance.error_taxonomy import (
    FrenchComplianceErrorTaxonomy,
    ErrorContext,
    ErrorReport,
    ValidationError,
    ErrorCategory,
    FixComplexity
)
from core.french_compliance.insee_client import INSEEAPIClient
from core.gdpr_audit import log_audit_event

logger = logging.getLogger(__name__)

class CorrectionConfidence(str, Enum):
    """Confidence levels for corrections"""
    HIGH = "high"           # 90%+ confidence - auto-apply
    MEDIUM = "medium"       # 70-89% confidence - review queue
    LOW = "low"             # 50-69% confidence - manual review
    UNCERTAIN = "uncertain" # <50% confidence - flag for expert review

class CorrectionAction(str, Enum):
    """Types of correction actions"""
    FORMAT_FIX = "format_fix"           # Format standardization
    VALUE_REPLACEMENT = "value_replacement"  # Replace with correct value
    FIELD_COMPLETION = "field_completion"    # Fill missing fields
    CALCULATION_FIX = "calculation_fix"      # Fix mathematical errors
    NORMALIZATION = "normalization"          # Standardize values
    VALIDATION_OVERRIDE = "validation_override"  # Override validation for special cases

class CorrectionStatus(str, Enum):
    """Status of correction attempts"""
    AUTO_APPLIED = "auto_applied"       # Automatically applied
    QUEUED_REVIEW = "queued_review"     # Waiting for manual review
    MANUAL_REVIEW = "manual_review"     # Requires expert review
    APPLIED_MANUAL = "applied_manual"   # Applied after manual approval
    REJECTED = "rejected"               # Correction rejected
    FAILED = "failed"                   # Correction attempt failed

@dataclass
class CorrectionSuggestion:
    """A specific correction suggestion"""
    field_name: str
    original_value: Any
    corrected_value: Any
    correction_action: CorrectionAction
    confidence: float
    reasoning: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    cost_estimate: Optional[float] = None
    requires_external_validation: bool = False

@dataclass
class CorrectionDecision:
    """Decision made about a correction"""
    suggestion: CorrectionSuggestion
    decision: CorrectionStatus
    confidence_level: CorrectionConfidence
    auto_apply: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    applied_by: Optional[str] = None
    review_notes: Optional[str] = None

@dataclass
class AutoCorrectionResult:
    """Result of auto-correction process"""
    invoice_id: str
    corrections_applied: List[CorrectionDecision] = field(default_factory=list)
    corrections_queued: List[CorrectionDecision] = field(default_factory=list)
    corrections_failed: List[CorrectionDecision] = field(default_factory=list)
    total_corrections_attempted: int = 0
    auto_correction_success_rate: float = 0.0
    estimated_time_saved: float = 0.0  # In minutes
    corrected_invoice_data: Optional[InvoiceData] = None
    processing_metrics: Dict[str, Any] = field(default_factory=dict)

class SIRENSIRETCorrector:
    """Specialized corrector for SIREN/SIRET numbers"""
    
    def __init__(self):
        self.insee_client = INSEEAPIClient()
    
    async def suggest_siren_correction(
        self, 
        siren: str, 
        context: Dict[str, Any],
        db_session: AsyncSession
    ) -> Optional[CorrectionSuggestion]:
        """Suggest SIREN correction based on format and validation"""
        
        if not siren:
            return None
            
        original_siren = siren
        
        # Format correction - remove spaces, dashes, and standardize
        cleaned_siren = re.sub(r'[^\d]', '', siren)
        
        # Check length
        if len(cleaned_siren) != 9:
            # Try to extract 9 consecutive digits
            digits_match = re.search(r'\d{9}', siren)
            if digits_match:
                cleaned_siren = digits_match.group(0)
            else:
                return None
        
        # Validate with Luhn algorithm
        if self._validate_luhn(cleaned_siren):
            confidence = 0.95 if cleaned_siren != original_siren else 1.0
            
            # Check with INSEE if we have network access
            try:
                validation_result = await self.insee_client.validate_siren(
                    cleaned_siren, db_session
                )
                
                if validation_result.get("is_valid"):
                    confidence = 0.98
                    evidence = {
                        "luhn_valid": True,
                        "insee_validated": True,
                        "company_name": validation_result.get("company_data", {}).get("name"),
                        "format_cleaned": cleaned_siren != original_siren
                    }
                else:
                    confidence = 0.7  # Format correct but doesn't exist
                    evidence = {
                        "luhn_valid": True,
                        "insee_validated": False,
                        "format_cleaned": cleaned_siren != original_siren
                    }
                    
            except Exception as e:
                logger.warning(f"Could not validate SIREN with INSEE: {e}")
                confidence = 0.85
                evidence = {
                    "luhn_valid": True,
                    "insee_validated": None,
                    "format_cleaned": cleaned_siren != original_siren
                }
            
            return CorrectionSuggestion(
                field_name="siren_number",
                original_value=original_siren,
                corrected_value=cleaned_siren,
                correction_action=CorrectionAction.FORMAT_FIX,
                confidence=confidence,
                reasoning=f"SIREN formaté et validé selon l'algorithme de Luhn",
                evidence=evidence
            )
        
        return None
    
    async def suggest_siret_correction(
        self, 
        siret: str, 
        siren: Optional[str],
        context: Dict[str, Any],
        db_session: AsyncSession
    ) -> Optional[CorrectionSuggestion]:
        """Suggest SIRET correction"""
        
        if not siret:
            return None
            
        original_siret = siret
        
        # Format correction
        cleaned_siret = re.sub(r'[^\d]', '', siret)
        
        # Check length
        if len(cleaned_siret) != 14:
            # Try to extract 14 consecutive digits
            digits_match = re.search(r'\d{14}', siret)
            if digits_match:
                cleaned_siret = digits_match.group(0)
            else:
                return None
        
        # Validate SIREN part if provided
        siret_siren = cleaned_siret[:9]
        if siren and siret_siren != siren:
            # SIRET doesn't match provided SIREN
            if self._validate_luhn(siren):
                # Use correct SIREN + keep NIC part
                nic = cleaned_siret[9:]
                cleaned_siret = siren + nic
            else:
                return None
        
        # Validate SIRET
        if self._validate_luhn(siret_siren):
            confidence = 0.9 if cleaned_siret != original_siret else 0.95
            
            # Check with INSEE if possible
            try:
                validation_result = await self.insee_client.validate_siret(
                    cleaned_siret, db_session
                )
                
                if validation_result.get("is_valid"):
                    confidence = 0.97
                    evidence = {
                        "luhn_valid": True,
                        "insee_validated": True,
                        "establishment_active": validation_result.get("establishment_active"),
                        "format_cleaned": cleaned_siret != original_siret
                    }
                else:
                    confidence = 0.75
                    evidence = {
                        "luhn_valid": True,
                        "insee_validated": False,
                        "format_cleaned": cleaned_siret != original_siret
                    }
                    
            except Exception as e:
                logger.warning(f"Could not validate SIRET with INSEE: {e}")
                confidence = 0.85
                evidence = {
                    "luhn_valid": True,
                    "insee_validated": None,
                    "format_cleaned": cleaned_siret != original_siret
                }
            
            return CorrectionSuggestion(
                field_name="siret_number",
                original_value=original_siret,
                corrected_value=cleaned_siret,
                correction_action=CorrectionAction.FORMAT_FIX,
                confidence=confidence,
                reasoning=f"SIRET formaté et validé",
                evidence=evidence
            )
        
        return None
    
    def _validate_luhn(self, number: str) -> bool:
        """Validate number using Luhn algorithm"""
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

class TVACorrector:
    """Specialized corrector for TVA-related errors"""
    
    def __init__(self):
        self.valid_rates = list(FRENCH_TVA_RATES.values())
    
    def suggest_tva_rate_correction(
        self, 
        rate: float, 
        product_category: Optional[str] = None,
        context: Dict[str, Any] = None
    ) -> Optional[CorrectionSuggestion]:
        """Suggest TVA rate correction"""
        
        if rate in self.valid_rates:
            return None  # Already valid
        
        # Find closest valid rate
        closest_rate = min(self.valid_rates, key=lambda x: abs(x - rate))
        difference = abs(closest_rate - rate)
        
        # High confidence if very close (rounding error)
        if difference <= 0.5:
            confidence = 0.95
            reasoning = f"Taux TVA {rate}% arrondi au taux français valide le plus proche"
        elif difference <= 2.0:
            confidence = 0.85
            reasoning = f"Taux TVA {rate}% corrigé vers le taux français standard"
        else:
            confidence = 0.6
            reasoning = f"Taux TVA {rate}% semble incorrect, suggestion basée sur les taux français"
        
        # Enhance confidence based on product category
        if product_category:
            expected_rate = self._get_expected_rate_for_category(product_category)
            if expected_rate == closest_rate:
                confidence = min(0.98, confidence + 0.1)
                reasoning += f" (cohérent avec la catégorie '{product_category}')"
        
        return CorrectionSuggestion(
            field_name="tva_rate",
            original_value=rate,
            corrected_value=closest_rate,
            correction_action=CorrectionAction.VALUE_REPLACEMENT,
            confidence=confidence,
            reasoning=reasoning,
            evidence={
                "original_rate": rate,
                "closest_valid_rate": closest_rate,
                "difference": difference,
                "product_category": product_category,
                "valid_french_rates": self.valid_rates
            }
        )
    
    def suggest_tva_calculation_correction(
        self, 
        amount_ht: float, 
        tva_rate: float, 
        tva_amount: float,
        total_ttc: float
    ) -> Optional[CorrectionSuggestion]:
        """Suggest TVA calculation correction"""
        
        # Calculate expected values
        expected_tva = round(amount_ht * tva_rate / 100, 2)
        expected_ttc = round(amount_ht + expected_tva, 2)
        
        # Check which values are incorrect
        tva_error = abs(tva_amount - expected_tva)
        ttc_error = abs(total_ttc - expected_ttc)
        
        corrections = []
        
        # TVA amount correction
        if tva_error > 0.02:  # More than 2 cents difference
            confidence = 0.98 if tva_error < 1.0 else 0.95
            corrections.append(CorrectionSuggestion(
                field_name="total_tva",
                original_value=tva_amount,
                corrected_value=expected_tva,
                correction_action=CorrectionAction.CALCULATION_FIX,
                confidence=confidence,
                reasoning=f"Montant TVA recalculé: {amount_ht}€ × {tva_rate}% = {expected_tva}€",
                evidence={
                    "amount_ht": amount_ht,
                    "tva_rate": tva_rate,
                    "original_tva": tva_amount,
                    "expected_tva": expected_tva,
                    "error_amount": tva_error
                }
            ))
        
        # TTC amount correction
        if ttc_error > 0.02:
            confidence = 0.98 if ttc_error < 1.0 else 0.95
            corrections.append(CorrectionSuggestion(
                field_name="total_ttc",
                original_value=total_ttc,
                corrected_value=expected_ttc,
                correction_action=CorrectionAction.CALCULATION_FIX,
                confidence=confidence,
                reasoning=f"Montant TTC recalculé: {amount_ht}€ + {expected_tva}€ = {expected_ttc}€",
                evidence={
                    "amount_ht": amount_ht,
                    "expected_tva": expected_tva,
                    "original_ttc": total_ttc,
                    "expected_ttc": expected_ttc,
                    "error_amount": ttc_error
                }
            ))
        
        return corrections[0] if corrections else None
    
    def _get_expected_rate_for_category(self, category: str) -> float:
        """Get expected TVA rate for product category"""
        category_lower = category.lower()
        
        # Simple category mapping
        if any(term in category_lower for term in ['livre', 'médicament', 'alimentation']):
            return 5.5
        elif any(term in category_lower for term in ['restaurant', 'hôtel', 'transport']):
            return 10.0
        elif any(term in category_lower for term in ['presse']):
            return 2.1
        else:
            return 20.0  # Default standard rate

class DateCorrector:
    """Specialized corrector for date fields"""
    
    def suggest_date_format_correction(
        self, 
        date_str: str, 
        field_name: str
    ) -> Optional[CorrectionSuggestion]:
        """Suggest date format correction"""
        
        if not date_str:
            return None
        
        # Try to parse various date formats
        date_patterns = [
            (r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', '%d/%m/%Y'),  # DD/MM/YYYY
            (r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})', '%Y/%m/%d'),  # YYYY/MM/DD
            (r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})', '%d/%m/%y'),  # DD/MM/YY
        ]
        
        for pattern, format_str in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if format_str == '%d/%m/%Y':
                        day, month, year = match.groups()
                        parsed_date = datetime(int(year), int(month), int(day))
                        corrected_value = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                    elif format_str == '%Y/%m/%d':
                        year, month, day = match.groups()
                        parsed_date = datetime(int(year), int(month), int(day))
                        corrected_value = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                    elif format_str == '%d/%m/%y':
                        day, month, year = match.groups()
                        full_year = f"20{year}" if int(year) < 50 else f"19{year}"
                        parsed_date = datetime(int(full_year), int(month), int(day))
                        corrected_value = f"{day.zfill(2)}/{month.zfill(2)}/{full_year}"
                    
                    # Validate date is reasonable
                    current_year = datetime.now().year
                    if 1990 <= parsed_date.year <= current_year + 2:
                        confidence = 0.95 if corrected_value != date_str else 0.98
                        
                        return CorrectionSuggestion(
                            field_name=field_name,
                            original_value=date_str,
                            corrected_value=corrected_value,
                            correction_action=CorrectionAction.FORMAT_FIX,
                            confidence=confidence,
                            reasoning=f"Date formatée au standard français DD/MM/YYYY",
                            evidence={
                                "parsed_date": parsed_date.isoformat(),
                                "original_format": pattern,
                                "standardized": corrected_value
                            }
                        )
                
                except (ValueError, IndexError):
                    continue
        
        return None

class AmountCorrector:
    """Specialized corrector for monetary amounts"""
    
    def suggest_amount_format_correction(
        self, 
        amount_str: str, 
        field_name: str
    ) -> Optional[CorrectionSuggestion]:
        """Suggest amount format correction"""
        
        if not amount_str:
            return None
        
        # Remove currency symbols and extra spaces
        cleaned = re.sub(r'[€$£]', '', amount_str).strip()
        
        # Handle French number format (spaces as thousands separator, comma as decimal)
        french_pattern = r'(\d{1,3}(?:\s\d{3})*(?:,\d{1,2})?)'
        match = re.search(french_pattern, cleaned)
        
        if match:
            amount_text = match.group(1)
            
            # Convert French format to decimal
            # Remove spaces (thousands separator) and replace comma with dot
            decimal_str = amount_text.replace(' ', '').replace(',', '.')
            
            try:
                amount_value = float(decimal_str)
                
                # Format back to standard French format
                if amount_value >= 1000:
                    # Add space as thousands separator
                    formatted = f"{amount_value:,.2f}".replace(',', ' ').replace('.', ',')
                else:
                    formatted = f"{amount_value:.2f}".replace('.', ',')
                
                formatted += " €"
                
                confidence = 0.95 if formatted != amount_str else 0.98
                
                return CorrectionSuggestion(
                    field_name=field_name,
                    original_value=amount_str,
                    corrected_value=amount_value,  # Store as float for calculations
                    correction_action=CorrectionAction.FORMAT_FIX,
                    confidence=confidence,
                    reasoning=f"Montant formaté au standard français: {formatted}",
                    evidence={
                        "original_text": amount_str,
                        "decimal_value": amount_value,
                        "formatted_display": formatted
                    }
                )
                
            except (ValueError, InvalidOperation):
                pass
        
        return None

class IntelligentAutoCorrectionEngine:
    """
    Main auto-correction engine that orchestrates all correction specialists
    """
    
    # Confidence thresholds for decision making
    AUTO_APPLY_THRESHOLD = 0.90      # Apply automatically
    REVIEW_QUEUE_THRESHOLD = 0.70    # Queue for review
    MANUAL_REVIEW_THRESHOLD = 0.50   # Require manual review
    
    def __init__(self):
        self.siren_corrector = SIRENSIRETCorrector()
        self.tva_corrector = TVACorrector()
        self.date_corrector = DateCorrector()
        self.amount_corrector = AmountCorrector()
        self.error_taxonomy = FrenchComplianceErrorTaxonomy()
    
    async def process_invoice_corrections(
        self,
        invoice_data: InvoiceData,
        validation_errors: List[str],
        context: Dict[str, Any],
        db_session: AsyncSession,
        user_id: Optional[str] = None
    ) -> AutoCorrectionResult:
        """
        Process an invoice and suggest/apply corrections automatically
        
        Args:
            invoice_data: Original invoice data
            validation_errors: List of validation errors found
            context: Additional context for corrections
            db_session: Database session
            user_id: User requesting corrections
            
        Returns:
            Auto-correction result with applied and queued corrections
        """
        
        start_time = datetime.utcnow()
        invoice_id = str(invoice_data.id) if hasattr(invoice_data, 'id') else str(context.get('invoice_id', 'unknown'))
        
        result = AutoCorrectionResult(invoice_id=invoice_id)
        
        # GDPR audit log
        await log_audit_event(
            db_session,
            user_id=user_id,
            operation_type="auto_correction_processing",
            data_categories=[
                "invoice_data", "validation_errors", "correction_suggestions",
                "automated_decisions", "business_data"
            ],
            risk_level="medium",
            details={
                "invoice_id": invoice_id,
                "error_count": len(validation_errors),
                "user_id": user_id,
                "purpose": "intelligent_auto_correction_for_french_compliance"
            }
        )
        
        logger.info(f"Starting auto-correction for invoice {invoice_id} with {len(validation_errors)} errors")
        
        try:
            # Create a working copy of invoice data
            corrected_data = self._deep_copy_invoice_data(invoice_data)
            
            # Generate all correction suggestions
            suggestions = await self._generate_correction_suggestions(
                corrected_data, validation_errors, context, db_session
            )
            
            # Process each suggestion and make decisions
            for suggestion in suggestions:
                decision = await self._make_correction_decision(
                    suggestion, context, db_session
                )
                
                result.total_corrections_attempted += 1
                
                if decision.auto_apply:
                    # Apply correction automatically
                    success = await self._apply_correction(
                        corrected_data, suggestion, db_session, user_id
                    )
                    
                    if success:
                        decision.decision = CorrectionStatus.AUTO_APPLIED
                        result.corrections_applied.append(decision)
                        logger.info(f"Auto-applied correction for {suggestion.field_name}: {suggestion.original_value} → {suggestion.corrected_value}")
                    else:
                        decision.decision = CorrectionStatus.FAILED
                        result.corrections_failed.append(decision)
                        logger.warning(f"Failed to apply correction for {suggestion.field_name}")
                
                elif decision.confidence_level in [CorrectionConfidence.MEDIUM, CorrectionConfidence.LOW]:
                    # Queue for manual review
                    decision.decision = CorrectionStatus.QUEUED_REVIEW
                    result.corrections_queued.append(decision)
                    
                    # Store in manual review queue
                    await self._queue_for_manual_review(decision, db_session, user_id)
                    
                else:
                    # Uncertain - requires expert review
                    decision.decision = CorrectionStatus.MANUAL_REVIEW
                    result.corrections_failed.append(decision)
            
            # Update corrected invoice data
            result.corrected_invoice_data = corrected_data
            
            # Calculate metrics
            result.auto_correction_success_rate = (
                len(result.corrections_applied) / result.total_corrections_attempted * 100
                if result.total_corrections_attempted > 0 else 0
            )
            
            result.estimated_time_saved = self._estimate_time_saved(result.corrections_applied)
            
            result.processing_metrics = {
                "processing_time_seconds": (datetime.utcnow() - start_time).total_seconds(),
                "suggestions_generated": len(suggestions),
                "auto_applied": len(result.corrections_applied),
                "queued_review": len(result.corrections_queued),
                "failed": len(result.corrections_failed),
                "success_rate": result.auto_correction_success_rate
            }
            
            # Store correction results for machine learning
            await self._store_correction_results(result, db_session)
            
            logger.info(
                f"Auto-correction completed for invoice {invoice_id}: "
                f"{len(result.corrections_applied)} applied, "
                f"{len(result.corrections_queued)} queued, "
                f"{len(result.corrections_failed)} failed"
            )
            
        except Exception as e:
            logger.error(f"Error in auto-correction processing: {e}")
            result.processing_metrics = {"error": str(e)}
        
        return result
    
    async def _generate_correction_suggestions(
        self,
        invoice_data: InvoiceData,
        validation_errors: List[str],
        context: Dict[str, Any],
        db_session: AsyncSession
    ) -> List[CorrectionSuggestion]:
        """Generate all possible correction suggestions"""
        
        suggestions = []
        
        # SIREN/SIRET corrections
        if invoice_data.vendor and invoice_data.vendor.siren_number:
            siren_suggestion = await self.siren_corrector.suggest_siren_correction(
                invoice_data.vendor.siren_number, context, db_session
            )
            if siren_suggestion:
                suggestions.append(siren_suggestion)
        
        if invoice_data.vendor and invoice_data.vendor.siret_number:
            siret_suggestion = await self.siren_corrector.suggest_siret_correction(
                invoice_data.vendor.siret_number,
                invoice_data.vendor.siren_number,
                context,
                db_session
            )
            if siret_suggestion:
                suggestions.append(siret_suggestion)
        
        # TVA corrections
        if hasattr(invoice_data, 'tva_rate') and invoice_data.tva_rate:
            tva_rate_suggestion = self.tva_corrector.suggest_tva_rate_correction(
                invoice_data.tva_rate,
                context.get('product_category'),
                context
            )
            if tva_rate_suggestion:
                suggestions.append(tva_rate_suggestion)
        
        # TVA calculation corrections
        if all(hasattr(invoice_data, attr) and getattr(invoice_data, attr) for attr in 
               ['subtotal_ht', 'tva_rate', 'total_tva', 'total_ttc']):
            tva_calc_suggestion = self.tva_corrector.suggest_tva_calculation_correction(
                invoice_data.subtotal_ht,
                invoice_data.tva_rate,
                invoice_data.total_tva,
                invoice_data.total_ttc
            )
            if tva_calc_suggestion:
                suggestions.append(tva_calc_suggestion)
        
        # Date corrections
        if invoice_data.date:
            date_suggestion = self.date_corrector.suggest_date_format_correction(
                str(invoice_data.date), 'invoice_date'
            )
            if date_suggestion:
                suggestions.append(date_suggestion)
        
        if invoice_data.due_date:
            due_date_suggestion = self.date_corrector.suggest_date_format_correction(
                str(invoice_data.due_date), 'due_date'
            )
            if due_date_suggestion:
                suggestions.append(due_date_suggestion)
        
        # Amount corrections (if amounts are strings needing formatting)
        for field_name in ['subtotal_ht', 'total_tva', 'total_ttc']:
            value = getattr(invoice_data, field_name, None)
            if isinstance(value, str):
                amount_suggestion = self.amount_corrector.suggest_amount_format_correction(
                    value, field_name
                )
                if amount_suggestion:
                    suggestions.append(amount_suggestion)
        
        # Add pattern-based suggestions from historical data
        pattern_suggestions = await self._generate_pattern_based_suggestions(
            invoice_data, validation_errors, db_session
        )
        suggestions.extend(pattern_suggestions)
        
        return suggestions
    
    async def _make_correction_decision(
        self,
        suggestion: CorrectionSuggestion,
        context: Dict[str, Any],
        db_session: AsyncSession
    ) -> CorrectionDecision:
        """Make decision about whether to apply a correction"""
        
        confidence = suggestion.confidence
        
        # Determine confidence level
        if confidence >= self.AUTO_APPLY_THRESHOLD:
            confidence_level = CorrectionConfidence.HIGH
            auto_apply = True
        elif confidence >= self.REVIEW_QUEUE_THRESHOLD:
            confidence_level = CorrectionConfidence.MEDIUM
            auto_apply = False
        elif confidence >= self.MANUAL_REVIEW_THRESHOLD:
            confidence_level = CorrectionConfidence.LOW
            auto_apply = False
        else:
            confidence_level = CorrectionConfidence.UNCERTAIN
            auto_apply = False
        
        # Apply additional business rules
        if suggestion.requires_external_validation:
            auto_apply = False
            confidence_level = CorrectionConfidence.MEDIUM
        
        # Check cost implications
        if suggestion.cost_estimate and suggestion.cost_estimate > 0.10:  # More than 10 cents cost
            if confidence < 0.95:
                auto_apply = False
        
        # Check if field is critical
        critical_fields = ['siren_number', 'total_ttc', 'invoice_number']
        if suggestion.field_name in critical_fields and confidence < 0.95:
            auto_apply = False
        
        return CorrectionDecision(
            suggestion=suggestion,
            decision=CorrectionStatus.AUTO_APPLIED if auto_apply else CorrectionStatus.QUEUED_REVIEW,
            confidence_level=confidence_level,
            auto_apply=auto_apply
        )
    
    async def _apply_correction(
        self,
        invoice_data: InvoiceData,
        suggestion: CorrectionSuggestion,
        db_session: AsyncSession,
        user_id: Optional[str]
    ) -> bool:
        """Apply a correction to invoice data"""
        
        try:
            # Apply the correction based on field name
            if suggestion.field_name == "siren_number" and invoice_data.vendor:
                invoice_data.vendor.siren_number = suggestion.corrected_value
            elif suggestion.field_name == "siret_number" and invoice_data.vendor:
                invoice_data.vendor.siret_number = suggestion.corrected_value
            elif suggestion.field_name == "tva_rate":
                invoice_data.tva_rate = suggestion.corrected_value
            elif suggestion.field_name == "total_tva":
                invoice_data.total_tva = suggestion.corrected_value
            elif suggestion.field_name == "total_ttc":
                invoice_data.total_ttc = suggestion.corrected_value
            elif suggestion.field_name == "invoice_date":
                invoice_data.date = suggestion.corrected_value
            elif suggestion.field_name == "due_date":
                invoice_data.due_date = suggestion.corrected_value
            elif hasattr(invoice_data, suggestion.field_name):
                setattr(invoice_data, suggestion.field_name, suggestion.corrected_value)
            else:
                logger.warning(f"Unknown field for correction: {suggestion.field_name}")
                return False
            
            # Log the correction for audit
            await log_audit_event(
                db_session,
                user_id=user_id,
                operation_type="auto_correction_applied",
                data_categories=["invoice_data", "automated_correction"],
                risk_level="low",
                details={
                    "field_name": suggestion.field_name,
                    "original_value": str(suggestion.original_value),
                    "corrected_value": str(suggestion.corrected_value),
                    "confidence": suggestion.confidence,
                    "reasoning": suggestion.reasoning,
                    "correction_action": suggestion.correction_action.value
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying correction for {suggestion.field_name}: {e}")
            return False
    
    async def _generate_pattern_based_suggestions(
        self,
        invoice_data: InvoiceData,
        validation_errors: List[str],
        db_session: AsyncSession
    ) -> List[CorrectionSuggestion]:
        """Generate suggestions based on historical error patterns"""
        
        suggestions = []
        
        try:
            # Query historical patterns for similar errors
            for error in validation_errors:
                stmt = select(ValidationErrorPattern).where(
                    ValidationErrorPattern.pattern_data.ilike(f"%{error[:50]}%")
                ).order_by(ValidationErrorPattern.resolution_success_rate.desc()).limit(3)
                
                result = await db_session.execute(stmt)
                patterns = result.scalars().all()
                
                for pattern in patterns:
                    if pattern.resolution_success_rate and pattern.resolution_success_rate > 70.0:
                        # High success rate pattern - suggest its fix
                        if pattern.suggested_fixes:
                            for fix in pattern.suggested_fixes:
                                # Parse fix and create suggestion
                                suggestion = self._create_suggestion_from_pattern(
                                    fix, pattern, invoice_data
                                )
                                if suggestion:
                                    suggestions.append(suggestion)
        
        except Exception as e:
            logger.error(f"Error generating pattern-based suggestions: {e}")
        
        return suggestions
    
    def _create_suggestion_from_pattern(
        self,
        fix: str,
        pattern: ValidationErrorPattern,
        invoice_data: InvoiceData
    ) -> Optional[CorrectionSuggestion]:
        """Create correction suggestion from historical pattern"""
        
        # This is a simplified implementation
        # In production, you'd have more sophisticated pattern parsing
        
        confidence = min(0.85, pattern.resolution_success_rate / 100.0)
        
        return CorrectionSuggestion(
            field_name="pattern_based",
            original_value="unknown",
            corrected_value=fix,
            correction_action=CorrectionAction.VALUE_REPLACEMENT,
            confidence=confidence,
            reasoning=f"Suggestion basée sur un pattern historique (taux de succès: {pattern.resolution_success_rate}%)",
            evidence={
                "pattern_id": str(pattern.id),
                "occurrence_count": pattern.occurrence_count,
                "success_rate": pattern.resolution_success_rate
            }
        )
    
    async def _queue_for_manual_review(
        self,
        decision: CorrectionDecision,
        db_session: AsyncSession,
        user_id: Optional[str]
    ):
        """Queue correction for manual review"""
        
        # In a full implementation, this would create a record in a manual review queue table
        # For now, we'll just log it
        
        await log_audit_event(
            db_session,
            user_id=user_id,
            operation_type="correction_queued_for_review",
            data_categories=["correction_queue", "manual_review"],
            risk_level="low",
            details={
                "field_name": decision.suggestion.field_name,
                "confidence": decision.suggestion.confidence,
                "confidence_level": decision.confidence_level.value,
                "reasoning": decision.suggestion.reasoning,
                "requires_review": True
            }
        )
    
    def _estimate_time_saved(self, applied_corrections: List[CorrectionDecision]) -> float:
        """Estimate time saved by auto-corrections (in minutes)"""
        
        time_per_correction = {
            CorrectionAction.FORMAT_FIX: 1.0,
            CorrectionAction.VALUE_REPLACEMENT: 2.0,
            CorrectionAction.FIELD_COMPLETION: 3.0,
            CorrectionAction.CALCULATION_FIX: 2.5,
            CorrectionAction.NORMALIZATION: 1.5,
            CorrectionAction.VALIDATION_OVERRIDE: 5.0
        }
        
        total_time = 0.0
        for decision in applied_corrections:
            action = decision.suggestion.correction_action
            total_time += time_per_correction.get(action, 2.0)
        
        return total_time
    
    async def _store_correction_results(
        self,
        result: AutoCorrectionResult,
        db_session: AsyncSession
    ):
        """Store correction results for machine learning improvement"""
        
        try:
            # Update error patterns with correction results
            for decision in result.corrections_applied:
                if decision.decision == CorrectionStatus.AUTO_APPLIED:
                    # Update success rate for similar patterns
                    # This is simplified - in production you'd have more sophisticated ML
                    pass
            
            await db_session.commit()
            
        except Exception as e:
            logger.error(f"Error storing correction results: {e}")
            await db_session.rollback()
    
    def _deep_copy_invoice_data(self, invoice_data: InvoiceData) -> InvoiceData:
        """Create a deep copy of invoice data for modifications"""
        
        # This is a simplified implementation
        # In production, you'd use a proper deep copy mechanism
        
        import copy
        return copy.deepcopy(invoice_data)

# Convenience functions for easy integration

async def auto_correct_invoice(
    invoice_data: InvoiceData,
    validation_errors: List[str],
    db_session: AsyncSession,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> AutoCorrectionResult:
    """
    Convenience function to auto-correct an invoice
    
    Args:
        invoice_data: Invoice data to correct
        validation_errors: List of validation errors
        db_session: Database session
        user_id: User requesting corrections
        context: Additional context
        
    Returns:
        Auto-correction result
    """
    engine = IntelligentAutoCorrectionEngine()
    return await engine.process_invoice_corrections(
        invoice_data, validation_errors, context or {}, db_session, user_id
    )

async def get_correction_suggestions_only(
    invoice_data: InvoiceData,
    validation_errors: List[str],
    db_session: AsyncSession,
    context: Optional[Dict[str, Any]] = None
) -> List[CorrectionSuggestion]:
    """
    Get correction suggestions without applying them
    
    Args:
        invoice_data: Invoice data to analyze
        validation_errors: List of validation errors
        db_session: Database session
        context: Additional context
        
    Returns:
        List of correction suggestions
    """
    engine = IntelligentAutoCorrectionEngine()
    return await engine._generate_correction_suggestions(
        invoice_data, validation_errors, context or {}, db_session
    )