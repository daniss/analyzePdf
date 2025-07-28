"""
French Compliance Validation Orchestrator

This module orchestrates all French compliance validations and integrates them with
the error taxonomy system. It provides a unified interface for expert-comptables
to get comprehensive validation results with professional French error reporting.

Features:
- Orchestrates all validation systems (INSEE, TVA, PCG, Sequential, etc.)
- Integrates with French error taxonomy for professional error reporting
- Provides unified validation interface
- Generates comprehensive compliance reports
- Tracks validation performance and patterns
- GDPR-compliant audit logging
"""

import asyncio
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from schemas.invoice import InvoiceData
from models.french_compliance import (
    FrenchComplianceValidation,
    ValidationTrigger,
    ValidationSource,
    ErrorSeverity
)
from core.validation.french_validator import (
    FrenchInvoiceValidator,
    validate_french_invoice
)
from core.validation.tva_validator import (
    FrenchTVAValidator,
    validate_invoice_tva,
    TVAValidationResult
)
from core.french_compliance.error_taxonomy import (
    FrenchComplianceErrorTaxonomy,
    ErrorContext,
    ErrorReport,
    ValidationError,
    process_french_compliance_errors
)
from core.french_compliance.insee_client import INSEEAPIClient
from core.pcg.pcg_service import PlanComptableGeneralService
from core.gdpr_audit import log_audit_event

logger = logging.getLogger(__name__)

@dataclass
class ValidationComponents:
    """Container for all validation results"""
    siren_validation: Dict[str, Any] = field(default_factory=dict)
    siret_validation: Dict[str, Any] = field(default_factory=dict)
    tva_validation: TVAValidationResult = None
    sequential_validation: Dict[str, Any] = field(default_factory=dict)
    mandatory_fields_validation: Dict[str, Any] = field(default_factory=dict)
    pcg_mapping_validation: Dict[str, Any] = field(default_factory=dict)
    business_rules_validation: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ComprehensiveValidationResult:
    """Comprehensive validation result with error taxonomy integration"""
    invoice_id: str
    validation_timestamp: datetime
    overall_compliant: bool
    compliance_score: float
    error_report: ErrorReport
    validation_components: ValidationComponents
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)

class FrenchComplianceOrchestrator:
    """
    Orchestrates all French compliance validations with error taxonomy integration
    """
    
    def __init__(self):
        self.french_validator = FrenchInvoiceValidator()
        self.tva_validator = FrenchTVAValidator()
        self.error_taxonomy = FrenchComplianceErrorTaxonomy()
        self.insee_client = INSEEAPIClient()
        self.pcg_service = PlanComptableGeneralService()
        
        # Performance tracking
        self.validation_start_time = None
        self.component_timings = {}
    
    async def validate_invoice_comprehensive(
        self,
        invoice: InvoiceData,
        db_session: AsyncSession,
        validation_trigger: ValidationTrigger = ValidationTrigger.USER,
        include_pcg_mapping: bool = True,
        include_business_rules: bool = True
    ) -> ComprehensiveValidationResult:
        """
        Perform comprehensive French compliance validation with error taxonomy
        
        Args:
            invoice: Invoice data to validate
            db_session: Database session
            validation_trigger: What triggered this validation
            include_pcg_mapping: Whether to include PCG mapping validation
            include_business_rules: Whether to include business rules validation
            
        Returns:
            Comprehensive validation result with professional French error reporting
        """
        
        self.validation_start_time = datetime.utcnow()
        invoice_id = str(invoice.id) if hasattr(invoice, 'id') else invoice.invoice_number
        
        # GDPR audit log
        await log_audit_event(
            db_session,
            user_id=None,
            operation_type="comprehensive_french_validation",
            data_categories=[
                "invoice_data", "business_data", "financial_data", 
                "validation_results", "compliance_data"
            ],
            risk_level="medium",
            details={
                "invoice_number": invoice.invoice_number,
                "invoice_id": invoice_id,
                "validation_trigger": validation_trigger.value,
                "purpose": "french_compliance_comprehensive_validation"
            }
        )
        
        logger.info(f"Starting comprehensive validation for invoice {invoice.invoice_number}")
        
        # Initialize components
        components = ValidationComponents()
        all_errors = []
        all_warnings = []
        
        try:
            # 1. Core French Invoice Validation
            core_result = await self._validate_core_french_requirements(
                invoice, db_session, components
            )
            all_errors.extend(core_result.get("errors", []))
            all_warnings.extend(core_result.get("warnings", []))
            
            # 2. Enhanced TVA Validation
            tva_result = await self._validate_tva_comprehensive(
                invoice, db_session, components
            )
            all_errors.extend(tva_result.get("errors", []))
            all_warnings.extend(tva_result.get("warnings", []))
            
            # 3. SIREN/SIRET Validation with INSEE
            siren_siret_result = await self._validate_siren_siret_with_insee(
                invoice, db_session, components
            )
            all_errors.extend(siren_siret_result.get("errors", []))
            all_warnings.extend(siren_siret_result.get("warnings", []))
            
            # 4. Sequential Numbering Validation
            sequential_result = await self._validate_sequential_numbering(
                invoice, db_session, components
            )
            all_errors.extend(sequential_result.get("errors", []))
            all_warnings.extend(sequential_result.get("warnings", []))
            
            # 5. Mandatory Fields Validation
            mandatory_result = await self._validate_mandatory_fields(
                invoice, db_session, components
            )
            all_errors.extend(mandatory_result.get("errors", []))
            all_warnings.extend(mandatory_result.get("warnings", []))
            
            # 6. PCG Mapping Validation (optional)
            if include_pcg_mapping:
                pcg_result = await self._validate_pcg_mapping(
                    invoice, db_session, components
                )
                all_warnings.extend(pcg_result.get("warnings", []))
            
            # 7. Business Rules Validation (optional)
            if include_business_rules:
                business_result = await self._validate_business_rules(
                    invoice, db_session, components
                )
                all_warnings.extend(business_result.get("warnings", []))
            
            # 8. Process errors through taxonomy system
            error_report = await self._process_errors_with_taxonomy(
                all_errors + all_warnings,
                ErrorContext.INVOICE_VALIDATION,
                invoice_id,
                db_session
            )
            
            # 9. Calculate overall compliance
            overall_compliant = len(error_report.errors) == 0
            compliance_score = error_report.overall_score
            
            # 10. Generate recommendations and next actions
            recommendations = await self._generate_recommendations(
                error_report, components
            )
            next_actions = await self._generate_next_actions(
                error_report, validation_trigger
            )
            
            # 11. Store validation results
            await self._store_validation_results(
                invoice, components, error_report, db_session, validation_trigger
            )
            
            # 12. Performance metrics
            performance_metrics = self._calculate_performance_metrics()
            
            result = ComprehensiveValidationResult(
                invoice_id=invoice_id,
                validation_timestamp=self.validation_start_time,
                overall_compliant=overall_compliant,
                compliance_score=compliance_score,
                error_report=error_report,
                validation_components=components,
                performance_metrics=performance_metrics,
                recommendations=recommendations,
                next_actions=next_actions
            )
            
            logger.info(
                f"Comprehensive validation completed for invoice {invoice.invoice_number}: "
                f"Compliant={overall_compliant}, Score={compliance_score:.1f}%, "
                f"Errors={len(error_report.errors)}, Warnings={len(error_report.warnings)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Comprehensive validation failed for invoice {invoice.invoice_number}: {e}")
            
            # Create error report for the validation failure
            error_report = await self._create_validation_failure_report(
                str(e), invoice_id, db_session
            )
            
            return ComprehensiveValidationResult(
                invoice_id=invoice_id,
                validation_timestamp=self.validation_start_time or datetime.utcnow(),
                overall_compliant=False,
                compliance_score=0.0,
                error_report=error_report,
                validation_components=components,
                performance_metrics={"validation_failed": True}
            )
    
    async def _validate_core_french_requirements(
        self,
        invoice: InvoiceData,
        db_session: AsyncSession,
        components: ValidationComponents
    ) -> Dict[str, List[str]]:
        """Validate core French invoice requirements"""
        
        start_time = datetime.utcnow()
        
        try:
            # Use existing French validator
            result = await validate_french_invoice(invoice, db_session)
            
            # Store in components
            components.mandatory_fields_validation = {
                "is_compliant": result.get("is_compliant", False),
                "compliance_score": result.get("compliance_score", 0.0),
                "validation_method": "french_invoice_validator",
                "validation_timestamp": start_time.isoformat()
            }
            
            return {
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", [])
            }
            
        except Exception as e:
            logger.error(f"Core French validation failed: {e}")
            return {
                "errors": [f"Erreur lors de la validation française de base: {str(e)}"],
                "warnings": []
            }
        
        finally:
            self.component_timings["core_french"] = (
                datetime.utcnow() - start_time
            ).total_seconds()
    
    async def _validate_tva_comprehensive(
        self,
        invoice: InvoiceData,
        db_session: AsyncSession,
        components: ValidationComponents
    ) -> Dict[str, List[str]]:
        """Comprehensive TVA validation"""
        
        start_time = datetime.utcnow()
        
        try:
            # Use enhanced TVA validator
            tva_result = await validate_invoice_tva(invoice, db_session)
            
            # Store in components
            components.tva_validation = tva_result
            
            return {
                "errors": tva_result.errors,
                "warnings": tva_result.warnings
            }
            
        except Exception as e:
            logger.error(f"TVA validation failed: {e}")
            return {
                "errors": [f"Erreur lors de la validation TVA: {str(e)}"],
                "warnings": []
            }
        
        finally:
            self.component_timings["tva_validation"] = (
                datetime.utcnow() - start_time
            ).total_seconds()
    
    async def _validate_siren_siret_with_insee(
        self,
        invoice: InvoiceData,
        db_session: AsyncSession,
        components: ValidationComponents
    ) -> Dict[str, List[str]]:
        """Validate SIREN/SIRET with INSEE API"""
        
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        
        try:
            # Validate vendor SIREN/SIRET
            if invoice.vendor and invoice.vendor.siren_number:
                siren_result = await self.insee_client.validate_siren(
                    invoice.vendor.siren_number, db_session
                )
                
                components.siren_validation = {
                    "siren_number": invoice.vendor.siren_number,
                    "is_valid": siren_result.get("is_valid", False),
                    "validation_source": siren_result.get("source", "api"),
                    "company_data": siren_result.get("company_data", {}),
                    "validation_timestamp": start_time.isoformat()
                }
                
                if not siren_result.get("is_valid"):
                    errors.append(f"SIREN invalide: {invoice.vendor.siren_number}")
                elif siren_result.get("warnings"):
                    warnings.extend(siren_result["warnings"])
            
            # Validate vendor SIRET if present
            if invoice.vendor and invoice.vendor.siret_number:
                siret_result = await self.insee_client.validate_siret(
                    invoice.vendor.siret_number, db_session
                )
                
                components.siret_validation = {
                    "siret_number": invoice.vendor.siret_number,
                    "is_valid": siret_result.get("is_valid", False),
                    "establishment_active": siret_result.get("establishment_active", False),
                    "establishment_data": siret_result.get("establishment_data", {}),
                    "validation_timestamp": start_time.isoformat()
                }
                
                if not siret_result.get("is_valid"):
                    errors.append(f"SIRET invalide: {invoice.vendor.siret_number}")
                elif not siret_result.get("establishment_active"):
                    warnings.append(f"Établissement fermé pour SIRET: {invoice.vendor.siret_number}")
            
            return {"errors": errors, "warnings": warnings}
            
        except Exception as e:
            logger.error(f"SIREN/SIRET validation failed: {e}")
            return {
                "errors": [f"Erreur lors de la validation SIREN/SIRET: {str(e)}"],
                "warnings": []
            }
        
        finally:
            self.component_timings["siren_siret_validation"] = (
                datetime.utcnow() - start_time
            ).total_seconds()
    
    async def _validate_sequential_numbering(
        self,
        invoice: InvoiceData,
        db_session: AsyncSession,
        components: ValidationComponents
    ) -> Dict[str, List[str]]:
        """Validate sequential numbering compliance"""
        
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        
        try:
            # Check if sequential number is provided
            if not invoice.invoice_sequence_number and not invoice.invoice_number:
                errors.append("Numéro séquentiel ou numéro de facture manquant")
                return {"errors": errors, "warnings": warnings}
            
            # Use invoice number if sequence number not provided
            sequence_number = invoice.invoice_sequence_number or invoice.invoice_number
            
            # Basic format validation
            if not sequence_number.strip():
                errors.append("Numéro de facture vide")
                return {"errors": errors, "warnings": warnings}
            
            # Check for year in numbering (recommended)
            current_year = str(datetime.now().year)
            has_year = current_year in sequence_number
            
            if not has_year:
                warnings.append(
                    "Année manquante dans la numérotation - recommandé pour la traçabilité"
                )
            
            # TODO: Implement gap detection by querying previous invoices
            # This would require access to invoice history
            
            components.sequential_validation = {
                "sequence_number": sequence_number,
                "has_year": has_year,
                "format_valid": True,
                "gaps_detected": [],  # Would be populated by gap detection
                "validation_timestamp": start_time.isoformat()
            }
            
            return {"errors": errors, "warnings": warnings}
            
        except Exception as e:
            logger.error(f"Sequential numbering validation failed: {e}")
            return {
                "errors": [f"Erreur lors de la validation de numérotation: {str(e)}"],
                "warnings": []
            }
        
        finally:
            self.component_timings["sequential_validation"] = (
                datetime.utcnow() - start_time
            ).total_seconds()
    
    async def _validate_mandatory_fields(
        self,
        invoice: InvoiceData,
        db_session: AsyncSession,
        components: ValidationComponents
    ) -> Dict[str, List[str]]:
        """Validate mandatory fields according to French regulations"""
        
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        missing_fields = []
        
        try:
            # Check all mandatory fields
            if not invoice.invoice_number:
                missing_fields.append("Numéro de facture")
            
            if not invoice.date:
                missing_fields.append("Date d'émission")
            
            # Vendor information
            if not invoice.vendor_name and not (invoice.vendor and invoice.vendor.name):
                missing_fields.append("Nom du vendeur")
            
            if invoice.vendor:
                if not invoice.vendor.address:
                    missing_fields.append("Adresse du vendeur")
                if not invoice.vendor.siren_number:
                    warnings.append("Numéro SIREN du vendeur manquant")
            
            # Customer information
            if not invoice.customer_name and not (invoice.customer and invoice.customer.name):
                missing_fields.append("Nom du client")
            
            if invoice.customer and not invoice.customer.address:
                missing_fields.append("Adresse du client")
            
            # Financial information
            if not invoice.total_ttc and not invoice.total:
                missing_fields.append("Montant total TTC")
            
            if not invoice.total_tva:
                warnings.append("Montant TVA manquant")
            
            # B2B mandatory clauses
            if not invoice.late_payment_penalties:
                errors.append("Clause de pénalités de retard manquante (obligatoire B2B)")
            
            if not invoice.recovery_fees:
                errors.append("Clause d'indemnité forfaitaire de recouvrement manquante (40€ obligatoire B2B)")
            
            # Add missing fields to errors
            if missing_fields:
                for field in missing_fields:
                    errors.append(f"Champ obligatoire manquant: {field}")
            
            components.mandatory_fields_validation = {
                "missing_fields": missing_fields,
                "mandatory_score": max(0, 100 - len(missing_fields) * 10),
                "b2b_clauses_present": bool(invoice.late_payment_penalties and invoice.recovery_fees),
                "validation_timestamp": start_time.isoformat()
            }
            
            return {"errors": errors, "warnings": warnings}
            
        except Exception as e:
            logger.error(f"Mandatory fields validation failed: {e}")
            return {
                "errors": [f"Erreur lors de la validation des champs obligatoires: {str(e)}"],
                "warnings": []
            }
        
        finally:
            self.component_timings["mandatory_fields"] = (
                datetime.utcnow() - start_time
            ).total_seconds()
    
    async def _validate_pcg_mapping(
        self,
        invoice: InvoiceData,
        db_session: AsyncSession,
        components: ValidationComponents
    ) -> Dict[str, List[str]]:
        """Validate PCG (Plan Comptable Général) mapping"""
        
        start_time = datetime.utcnow()
        warnings = []
        
        try:
            mappings = []
            unmapped_items = []
            
            # Try to map each line item to PCG accounts
            for i, item in enumerate(invoice.line_items):
                mapping = await self.pcg_service.map_item_to_pcg(item.description)
                
                if mapping:
                    mappings.append({
                        "line_item_index": i,
                        "description": item.description,
                        "pcg_account": mapping.get("account_code"),
                        "pcg_name": mapping.get("account_name"),
                        "confidence": mapping.get("confidence", 0)
                    })
                else:
                    unmapped_items.append({
                        "line_item_index": i,
                        "description": item.description
                    })
                    warnings.append(
                        f"Aucun compte PCG identifié pour l'article {i+1}: {item.description}"
                    )
            
            components.pcg_mapping_validation = {
                "mappings": mappings,
                "unmapped_items": unmapped_items,
                "mapping_success_rate": len(mappings) / len(invoice.line_items) * 100 if invoice.line_items else 0,
                "validation_timestamp": start_time.isoformat()
            }
            
            return {"errors": [], "warnings": warnings}
            
        except Exception as e:
            logger.error(f"PCG mapping validation failed: {e}")
            return {
                "errors": [],
                "warnings": [f"Erreur lors du mappage PCG: {str(e)}"]
            }
        
        finally:
            self.component_timings["pcg_mapping"] = (
                datetime.utcnow() - start_time
            ).total_seconds()
    
    async def _validate_business_rules(
        self,
        invoice: InvoiceData,
        db_session: AsyncSession,
        components: ValidationComponents
    ) -> Dict[str, List[str]]:
        """Validate business rules and best practices"""
        
        start_time = datetime.utcnow()
        warnings = []
        
        try:
            # Check payment terms
            if invoice.due_date and invoice.date:
                payment_days = (invoice.due_date - invoice.date).days
                if payment_days > 60:
                    warnings.append(
                        f"Délai de paiement anormalement long: {payment_days} jours "
                        "(maximum légal: 60 jours)"
                    )
                elif payment_days > 45:
                    warnings.append(
                        f"Délai de paiement élevé: {payment_days} jours "
                        "(recommandé: 30-45 jours)"
                    )
            
            # Check currency
            if invoice.currency and invoice.currency != "EUR":
                warnings.append(
                    f"Devise non-EUR: {invoice.currency} "
                    "(EUR recommandé pour le marché français)"
                )
            
            # Check amounts consistency
            if invoice.total_ht and invoice.total_tva and invoice.total_ttc:
                calculated_ttc = invoice.total_ht + invoice.total_tva
                difference = abs(calculated_ttc - invoice.total_ttc)
                if difference > 0.02:  # 2 cents tolerance
                    warnings.append(
                        f"Incohérence dans les totaux: HT+TVA={calculated_ttc:.2f}€, "
                        f"TTC={invoice.total_ttc:.2f}€ (différence: {difference:.2f}€)"
                    )
            
            components.business_rules_validation = {
                "payment_days_check": payment_days if invoice.due_date and invoice.date else None,
                "currency_check": invoice.currency == "EUR" if invoice.currency else True,
                "amounts_consistent": difference <= 0.02 if invoice.total_ht and invoice.total_tva and invoice.total_ttc else True,
                "validation_timestamp": start_time.isoformat()
            }
            
            return {"errors": [], "warnings": warnings}
            
        except Exception as e:
            logger.error(f"Business rules validation failed: {e}")
            return {
                "errors": [],
                "warnings": [f"Erreur lors de la validation des règles métier: {str(e)}"]
            }
        
        finally:
            self.component_timings["business_rules"] = (
                datetime.utcnow() - start_time
            ).total_seconds()
    
    async def _process_errors_with_taxonomy(
        self,
        all_messages: List[str],
        context: ErrorContext,
        invoice_id: str,
        db_session: AsyncSession
    ) -> ErrorReport:
        """Process all error messages through the error taxonomy system"""
        
        try:
            return await process_french_compliance_errors(
                all_messages,
                context,
                invoice_id,
                db_session
            )
        except Exception as e:
            logger.error(f"Error taxonomy processing failed: {e}")
            
            # Create fallback error report
            from core.french_compliance.error_taxonomy import ErrorReport
            report = ErrorReport(
                invoice_id=invoice_id,
                validation_timestamp=datetime.utcnow()
            )
            report.errors = []
            report.warnings = []
            report.overall_score = 50.0  # Neutral score when processing fails
            report.compliance_status = "processing_failed"
            
            return report
    
    async def _generate_recommendations(
        self,
        error_report: ErrorReport,
        components: ValidationComponents
    ) -> List[str]:
        """Generate recommendations based on validation results"""
        
        recommendations = []
        
        # Recommendations based on error patterns
        if error_report.errors:
            critical_errors = [e for e in error_report.errors 
                             if e.error_details.severity == ErrorSeverity.CRITIQUE]
            if critical_errors:
                recommendations.append(
                    "PRIORITÉ CRITIQUE: Corrigez immédiatement les erreurs critiques "
                    "avant toute utilisation de la facture"
                )
        
        # SIREN/SIRET recommendations
        if not components.siren_validation.get("is_valid", True):
            recommendations.append(
                "Mettez à jour votre base de données fournisseurs avec les informations "
                "SIREN/SIRET correctes"
            )
        
        # TVA recommendations
        if components.tva_validation and not components.tva_validation.is_valid:
            recommendations.append(
                "Formez vos équipes sur l'application correcte des taux de TVA français"
            )
        
        # PCG mapping recommendations
        pcg_success_rate = components.pcg_mapping_validation.get("mapping_success_rate", 100)
        if pcg_success_rate < 80:
            recommendations.append(
                "Standardisez les descriptions d'articles pour faciliter "
                "le mappage comptable automatique"
            )
        
        # Business rules recommendations
        if components.business_rules_validation:
            payment_days = components.business_rules_validation.get("payment_days_check")
            if payment_days and payment_days > 45:
                recommendations.append(
                    "Négociez des délais de paiement plus courts avec vos fournisseurs "
                    "pour améliorer votre trésorerie"
                )
        
        return recommendations
    
    async def _generate_next_actions(
        self,
        error_report: ErrorReport,
        validation_trigger: ValidationTrigger
    ) -> List[str]:
        """Generate next actions based on validation results and trigger"""
        
        next_actions = []
        
        if error_report.compliance_status == "fully_compliant":
            if validation_trigger == ValidationTrigger.EXPORT:
                next_actions.append("✅ Facture prête pour l'export comptable")
            else:
                next_actions.append("✅ Facture conforme - Validation réussie")
        
        elif error_report.compliance_status == "compliant_with_warnings":
            next_actions.append("⚠️ Examinez les avertissements pour améliorer la qualité")
            if validation_trigger == ValidationTrigger.EXPORT:
                next_actions.append("📤 Export possible avec réserves")
        
        else:
            next_actions.append("❌ Corrigez les erreurs avant de continuer")
            
            # Specific actions based on error priority
            if error_report.fix_priority_order:
                next_actions.append(
                    f"🔧 Commencez par: {error_report.fix_priority_order[0]}"
                )
            
            if validation_trigger == ValidationTrigger.EXPORT:
                next_actions.append("🚫 Export bloqué jusqu'à correction des erreurs")
        
        # Time estimation
        if error_report.estimated_fix_time:
            next_actions.append(f"⏱️ Temps estimé de correction: {error_report.estimated_fix_time}")
        
        return next_actions
    
    async def _store_validation_results(
        self,
        invoice: InvoiceData,
        components: ValidationComponents,
        error_report: ErrorReport,
        db_session: AsyncSession,
        validation_trigger: ValidationTrigger
    ):
        """Store comprehensive validation results in database"""
        
        try:
            # Create comprehensive validation record
            validation_record = FrenchComplianceValidation(
                invoice_id=invoice.id if hasattr(invoice, 'id') else None,
                validation_timestamp=datetime.utcnow(),
                
                # SIREN validation
                siren_number=components.siren_validation.get("siren_number"),
                siren_is_valid=components.siren_validation.get("is_valid"),
                siren_validation_source=components.siren_validation.get("validation_source"),
                siren_company_name=components.siren_validation.get("company_data", {}).get("name"),
                
                # SIRET validation
                siret_number=components.siret_validation.get("siret_number"),
                siret_is_valid=components.siret_validation.get("is_valid"),
                siret_establishment_active=components.siret_validation.get("establishment_active"),
                
                # TVA validation
                tva_is_valid=components.tva_validation.is_valid if components.tva_validation else None,
                tva_calculation_valid=components.tva_validation.calculation_valid if components.tva_validation else None,
                
                # Sequential numbering
                invoice_sequence_number=components.sequential_validation.get("sequence_number"),
                sequence_is_valid=components.sequential_validation.get("format_valid"),
                sequence_gaps_detected=components.sequential_validation.get("gaps_detected"),
                
                # Mandatory fields
                mandatory_fields_score=components.mandatory_fields_validation.get("mandatory_score"),
                mandatory_fields_missing=components.mandatory_fields_validation.get("missing_fields"),
                
                # Overall scores
                overall_compliance_score=error_report.overall_score,
                legal_requirements_score=max(0, 100 - len(error_report.errors) * 15),
                export_readiness_score=error_report.overall_score,
                
                # Validation results
                validation_errors=[e.error_details.french_description for e in error_report.errors],
                validation_warnings=[w.error_details.french_description for w in error_report.warnings],
                validation_suggestions=getattr(error_report, 'recommendations', []),
                
                # Metadata
                validation_triggered_by=validation_trigger.value,
                validation_duration_ms=sum(self.component_timings.values()) * 1000
            )
            
            db_session.add(validation_record)
            await db_session.commit()
            
            logger.info(f"Validation results stored for invoice {invoice.invoice_number}")
            
        except Exception as e:
            logger.error(f"Failed to store validation results: {e}")
            await db_session.rollback()
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics for the validation"""
        
        total_time = sum(self.component_timings.values())
        
        return {
            "total_validation_time_seconds": total_time,
            "component_timings": self.component_timings,
            "average_component_time": total_time / len(self.component_timings) if self.component_timings else 0,
            "validation_timestamp": self.validation_start_time.isoformat() if self.validation_start_time else None
        }
    
    async def _create_validation_failure_report(
        self,
        error_message: str,
        invoice_id: str,
        db_session: AsyncSession
    ) -> ErrorReport:
        """Create error report when validation itself fails"""
        
        from core.french_compliance.error_taxonomy import ErrorReport, ValidationError, ErrorDetails, ErrorCategory, FixComplexity
        
        error_details = ErrorDetails(
            code="FR997",
            category=ErrorCategory.DATA_QUALITY,
            severity=ErrorSeverity.CRITIQUE,
            french_title="Échec de la validation",
            french_description=f"La validation automatique a échoué: {error_message}",
            technical_explanation="Une erreur système a empêché la validation complète de la facture.",
            fix_suggestion="Contactez le support technique ou réessayez ultérieurement.",
            fix_complexity=FixComplexity.SYSTEMATIC
        )
        
        validation_error = ValidationError(
            error_details=error_details,
            context=ErrorContext.INVOICE_VALIDATION,
            additional_info={"system_error": True, "error_message": error_message}
        )
        
        report = ErrorReport(
            invoice_id=invoice_id,
            validation_timestamp=datetime.utcnow()
        )
        report.errors = [validation_error]
        report.overall_score = 0.0
        report.compliance_status = "validation_failed"
        
        return report

# Convenience functions for easy integration

async def validate_invoice_comprehensive(
    invoice: InvoiceData,
    db_session: AsyncSession,
    validation_trigger: ValidationTrigger = ValidationTrigger.USER,
    include_pcg_mapping: bool = True,
    include_business_rules: bool = True
) -> ComprehensiveValidationResult:
    """
    Convenience function for comprehensive French invoice validation
    
    Args:
        invoice: Invoice data to validate
        db_session: Database session
        validation_trigger: What triggered this validation
        include_pcg_mapping: Whether to include PCG mapping validation
        include_business_rules: Whether to include business rules validation
        
    Returns:
        Comprehensive validation result with professional French error reporting
    """
    orchestrator = FrenchComplianceOrchestrator()
    return await orchestrator.validate_invoice_comprehensive(
        invoice, db_session, validation_trigger, include_pcg_mapping, include_business_rules
    )

async def validate_for_export(
    invoice: InvoiceData,
    db_session: AsyncSession,
    export_format: str = "sage"
) -> ComprehensiveValidationResult:
    """
    Validate invoice specifically for accounting export
    
    Args:
        invoice: Invoice data to validate
        db_session: Database session
        export_format: Target export format
        
    Returns:
        Validation result optimized for export requirements
    """
    orchestrator = FrenchComplianceOrchestrator()
    return await orchestrator.validate_invoice_comprehensive(
        invoice, 
        db_session, 
        ValidationTrigger.EXPORT,
        include_pcg_mapping=True,  # Always include for export
        include_business_rules=True
    )

async def quick_validation_check(
    invoice: InvoiceData,
    db_session: AsyncSession
) -> Dict[str, Any]:
    """
    Quick validation check for basic compliance
    
    Args:
        invoice: Invoice data to validate
        db_session: Database session
        
    Returns:
        Quick validation summary
    """
    result = await validate_invoice_comprehensive(
        invoice, db_session, ValidationTrigger.AUTO, 
        include_pcg_mapping=False, include_business_rules=False
    )
    
    return {
        "is_compliant": result.overall_compliant,
        "compliance_score": result.compliance_score,
        "error_count": len(result.error_report.errors),
        "warning_count": len(result.error_report.warnings),
        "top_issues": result.error_report.fix_priority_order[:3],
        "estimated_fix_time": result.error_report.estimated_fix_time
    }