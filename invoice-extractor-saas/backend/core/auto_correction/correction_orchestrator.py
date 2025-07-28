"""
Auto-Correction Orchestrator

This module integrates the intelligent auto-correction system with the existing
French compliance validation orchestrator. It provides seamless correction
capabilities within the validation workflow, ensuring expert-comptables get
clean, compliant results with minimal intervention.

Features:
- Integration with validation orchestrator
- Automated correction workflow
- Manual review queue integration
- Performance tracking and optimization
- Cost-aware correction decisions
- Complete audit trail
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from schemas.invoice import InvoiceData
from core.french_compliance.validation_orchestrator import (
    FrenchComplianceOrchestrator,
    ComprehensiveValidationResult,
    ValidationComponents
)
from core.french_compliance.error_taxonomy import (
    ErrorReport,
    ValidationError,
    ErrorContext
)
from core.auto_correction.auto_correction_engine import (
    IntelligentAutoCorrectionEngine,
    AutoCorrectionResult,
    CorrectionDecision,
    CorrectionStatus,
    CorrectionConfidence,
    auto_correct_invoice
)
from core.auto_correction.manual_review_queue import (
    ManualReviewQueueManager,
    ManualReviewItem,
    ReviewPriority,
    queue_correction_for_review
)
from core.gdpr_audit import log_audit_event
from models.french_compliance import ValidationTrigger

logger = logging.getLogger(__name__)

class CorrectionMode(str, Enum):
    """Correction processing modes"""
    DISABLED = "disabled"           # No auto-correction
    CONSERVATIVE = "conservative"   # Only high-confidence corrections
    BALANCED = "balanced"           # Balanced approach (default)
    AGGRESSIVE = "aggressive"       # More corrections, lower thresholds

class CorrectionTiming(str, Enum):
    """When to apply corrections"""
    BEFORE_VALIDATION = "before_validation"  # Correct then validate
    AFTER_VALIDATION = "after_validation"   # Validate then correct
    ITERATIVE = "iterative"                 # Correct and re-validate iteratively

@dataclass
class CorrectionSettings:
    """Settings for auto-correction behavior"""
    mode: CorrectionMode = CorrectionMode.BALANCED
    timing: CorrectionTiming = CorrectionTiming.AFTER_VALIDATION
    max_iterations: int = 3
    auto_apply_threshold: float = 0.90
    review_queue_threshold: float = 0.70
    cost_limit_per_invoice: float = 5.0  # Maximum cost in euros
    enable_learning: bool = True
    enable_manual_review: bool = True

@dataclass
class EnhancedValidationResult:
    """Enhanced validation result with auto-correction data"""
    validation_result: ComprehensiveValidationResult
    correction_result: Optional[AutoCorrectionResult] = None
    corrections_applied: int = 0
    corrections_queued: int = 0
    time_saved_minutes: float = 0.0
    cost_incurred: float = 0.0
    final_compliance_score: float = 0.0
    zero_decision_achieved: bool = False
    processing_summary: Dict[str, Any] = field(default_factory=dict)

class AutoCorrectionOrchestrator:
    """
    Orchestrates auto-correction within the French compliance validation workflow
    """
    
    def __init__(self, settings: Optional[CorrectionSettings] = None):
        self.settings = settings or CorrectionSettings()
        self.validation_orchestrator = FrenchComplianceOrchestrator()
        self.correction_engine = IntelligentAutoCorrectionEngine()
        self.review_queue_manager = ManualReviewQueueManager()
        
        # Override thresholds based on mode
        self._adjust_thresholds_for_mode()
    
    async def validate_and_correct_invoice(
        self,
        invoice: InvoiceData,
        db_session: AsyncSession,
        user_id: str,
        validation_trigger: ValidationTrigger = ValidationTrigger.USER,
        correction_settings: Optional[CorrectionSettings] = None
    ) -> EnhancedValidationResult:
        """
        Perform comprehensive validation with intelligent auto-correction
        
        Args:
            invoice: Invoice data to validate and correct
            db_session: Database session
            user_id: User ID
            validation_trigger: What triggered this validation
            correction_settings: Override default correction settings
            
        Returns:
            Enhanced validation result with correction data
        """
        
        start_time = datetime.utcnow()
        settings = correction_settings or self.settings
        invoice_id = str(invoice.id) if hasattr(invoice, 'id') else str(uuid.uuid4())
        
        # GDPR audit log
        await log_audit_event(
            db_session,
            user_id=user_id,
            operation_type="validation_with_auto_correction",
            data_categories=[
                "invoice_data", "validation_results", "automated_corrections",
                "compliance_data", "business_optimization"
            ],
            risk_level="medium",
            details={
                "invoice_id": invoice_id,
                "validation_trigger": validation_trigger.value,
                "correction_mode": settings.mode.value,
                "correction_timing": settings.timing.value,
                "purpose": "intelligent_validation_with_zero_decision_workflow"
            }
        )
        
        logger.info(f"Starting validation with auto-correction for invoice {invoice_id}")
        
        try:
            if settings.mode == CorrectionMode.DISABLED:
                # Just do validation without correction
                validation_result = await self.validation_orchestrator.validate_invoice_comprehensive(
                    invoice, db_session, validation_trigger
                )
                
                return EnhancedValidationResult(
                    validation_result=validation_result,
                    final_compliance_score=validation_result.compliance_score,
                    zero_decision_achieved=validation_result.overall_compliant,
                    processing_summary={
                        "correction_disabled": True,
                        "processing_time": (datetime.utcnow() - start_time).total_seconds()
                    }
                )
            
            # Choose correction workflow based on timing
            if settings.timing == CorrectionTiming.BEFORE_VALIDATION:
                result = await self._correct_then_validate(
                    invoice, db_session, user_id, validation_trigger, settings
                )
            elif settings.timing == CorrectionTiming.ITERATIVE:
                result = await self._iterative_correction_validation(
                    invoice, db_session, user_id, validation_trigger, settings
                )
            else:  # AFTER_VALIDATION
                result = await self._validate_then_correct(
                    invoice, db_session, user_id, validation_trigger, settings
                )
            
            # Calculate final metrics
            result.processing_summary.update({
                "total_processing_time": (datetime.utcnow() - start_time).total_seconds(),
                "zero_decision_workflow": {
                    "achieved": result.zero_decision_achieved,
                    "final_score": result.final_compliance_score,
                    "user_decisions_required": result.corrections_queued,
                    "time_saved_minutes": result.time_saved_minutes
                }
            })
            
            logger.info(
                f"Validation with auto-correction completed for invoice {invoice_id}: "
                f"Score {result.final_compliance_score:.1f}%, "
                f"Zero-decision: {result.zero_decision_achieved}, "
                f"Applied: {result.corrections_applied}, "
                f"Queued: {result.corrections_queued}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in validation with auto-correction: {e}")
            
            # Fallback to validation only
            try:
                validation_result = await self.validation_orchestrator.validate_invoice_comprehensive(
                    invoice, db_session, validation_trigger
                )
                
                return EnhancedValidationResult(
                    validation_result=validation_result,
                    final_compliance_score=validation_result.compliance_score,
                    processing_summary={
                        "error": str(e),
                        "fallback_to_validation_only": True
                    }
                )
            except Exception as fallback_error:
                logger.error(f"Fallback validation also failed: {fallback_error}")
                raise e
    
    async def _validate_then_correct(
        self,
        invoice: InvoiceData,
        db_session: AsyncSession,
        user_id: str,
        validation_trigger: ValidationTrigger,
        settings: CorrectionSettings
    ) -> EnhancedValidationResult:
        """Validate first, then apply corrections"""
        
        # Step 1: Initial validation
        validation_result = await self.validation_orchestrator.validate_invoice_comprehensive(
            invoice, db_session, validation_trigger
        )
        
        # Step 2: Apply corrections if errors found
        correction_result = None
        if validation_result.error_report.errors or validation_result.error_report.warnings:
            
            # Extract error messages for correction engine
            error_messages = []
            for error in validation_result.error_report.errors:
                error_messages.append(error.error_details.french_description)
            for warning in validation_result.error_report.warnings:
                error_messages.append(warning.error_details.french_description)
            
            # Apply corrections
            correction_result = await self.correction_engine.process_invoice_corrections(
                invoice,
                error_messages,
                {"validation_trigger": validation_trigger.value},
                db_session,
                user_id
            )
            
            # Queue uncertain corrections for manual review
            await self._process_correction_queue(
                correction_result, invoice, db_session, user_id
            )
            
            # Re-validate if corrections were applied
            if correction_result.corrections_applied and correction_result.corrected_invoice_data:
                validation_result = await self.validation_orchestrator.validate_invoice_comprehensive(
                    correction_result.corrected_invoice_data, db_session, validation_trigger
                )
        
        return self._build_enhanced_result(validation_result, correction_result)
    
    async def _correct_then_validate(
        self,
        invoice: InvoiceData,
        db_session: AsyncSession,
        user_id: str,
        validation_trigger: ValidationTrigger,
        settings: CorrectionSettings
    ) -> EnhancedValidationResult:
        """Apply preemptive corrections, then validate"""
        
        # Step 1: Apply format corrections and known patterns
        correction_result = await self._apply_preemptive_corrections(
            invoice, db_session, user_id
        )
        
        # Step 2: Validate the corrected invoice
        working_invoice = correction_result.corrected_invoice_data or invoice
        validation_result = await self.validation_orchestrator.validate_invoice_comprehensive(
            working_invoice, db_session, validation_trigger
        )
        
        # Step 3: Apply additional corrections if still needed
        if validation_result.error_report.errors:
            error_messages = [e.error_details.french_description for e in validation_result.error_report.errors]
            
            additional_correction = await self.correction_engine.process_invoice_corrections(
                working_invoice,
                error_messages,
                {"validation_trigger": validation_trigger.value},
                db_session,
                user_id
            )
            
            # Merge correction results
            correction_result = self._merge_correction_results(correction_result, additional_correction)
            
            # Queue for manual review
            await self._process_correction_queue(
                correction_result, working_invoice, db_session, user_id
            )
            
            # Final validation if more corrections applied
            if additional_correction.corrections_applied:
                final_invoice = additional_correction.corrected_invoice_data or working_invoice
                validation_result = await self.validation_orchestrator.validate_invoice_comprehensive(
                    final_invoice, db_session, validation_trigger
                )
        
        return self._build_enhanced_result(validation_result, correction_result)
    
    async def _iterative_correction_validation(
        self,
        invoice: InvoiceData,
        db_session: AsyncSession,
        user_id: str,
        validation_trigger: ValidationTrigger,
        settings: CorrectionSettings
    ) -> EnhancedValidationResult:
        """Iteratively correct and validate until clean or max iterations"""
        
        working_invoice = invoice
        all_corrections = []
        all_validation_results = []
        
        for iteration in range(settings.max_iterations):
            logger.info(f"Starting iteration {iteration + 1} of validation/correction")
            
            # Validate current state
            validation_result = await self.validation_orchestrator.validate_invoice_comprehensive(
                working_invoice, db_session, validation_trigger
            )
            all_validation_results.append(validation_result)
            
            # If clean, we're done
            if validation_result.overall_compliant:
                logger.info(f"Achieved compliance in iteration {iteration + 1}")
                break
            
            # Extract errors for correction
            error_messages = []
            for error in validation_result.error_report.errors:
                error_messages.append(error.error_details.french_description)
            for warning in validation_result.error_report.warnings:
                error_messages.append(warning.error_details.french_description)
            
            # Apply corrections
            correction_result = await self.correction_engine.process_invoice_corrections(
                working_invoice,
                error_messages,
                {
                    "validation_trigger": validation_trigger.value,
                    "iteration": iteration + 1
                },
                db_session,
                user_id
            )
            
            all_corrections.append(correction_result)
            
            # If no corrections applied, break to avoid infinite loop
            if not correction_result.corrections_applied:
                logger.info(f"No corrections applied in iteration {iteration + 1}, stopping")
                break
            
            # Update working invoice
            working_invoice = correction_result.corrected_invoice_data or working_invoice
        
        # Final processing
        final_validation = all_validation_results[-1]
        merged_corrections = self._merge_multiple_correction_results(all_corrections)
        
        # Queue remaining corrections for manual review
        if merged_corrections:
            await self._process_correction_queue(
                merged_corrections, working_invoice, db_session, user_id
            )
        
        return self._build_enhanced_result(final_validation, merged_corrections)
    
    async def _apply_preemptive_corrections(
        self,
        invoice: InvoiceData,
        db_session: AsyncSession,
        user_id: str
    ) -> AutoCorrectionResult:
        """Apply high-confidence format corrections preemptively"""
        
        # Generate format-based corrections without validation errors
        preemptive_errors = [
            "Format validation needed",
            "Preemptive correction scan"
        ]
        
        return await self.correction_engine.process_invoice_corrections(
            invoice,
            preemptive_errors,
            {"preemptive": True},
            db_session,
            user_id
        )
    
    async def _process_correction_queue(
        self,
        correction_result: AutoCorrectionResult,
        invoice: InvoiceData,
        db_session: AsyncSession,
        user_id: str
    ):
        """Process corrections that need manual review"""
        
        if not self.settings.enable_manual_review:
            return
        
        for decision in correction_result.corrections_queued:
            await self.review_queue_manager.queue_correction_for_review(
                decision,
                correction_result.invoice_id,
                db_session,
                user_id
            )
    
    def _merge_correction_results(
        self,
        result1: AutoCorrectionResult,
        result2: AutoCorrectionResult
    ) -> AutoCorrectionResult:
        """Merge two correction results"""
        
        merged = AutoCorrectionResult(invoice_id=result1.invoice_id)
        merged.corrections_applied = result1.corrections_applied + result2.corrections_applied
        merged.corrections_queued = result1.corrections_queued + result2.corrections_queued
        merged.corrections_failed = result1.corrections_failed + result2.corrections_failed
        merged.total_corrections_attempted = result1.total_corrections_attempted + result2.total_corrections_attempted
        merged.estimated_time_saved = result1.estimated_time_saved + result2.estimated_time_saved
        merged.corrected_invoice_data = result2.corrected_invoice_data or result1.corrected_invoice_data
        
        # Merge processing metrics
        merged.processing_metrics = {
            **result1.processing_metrics,
            **result2.processing_metrics,
            "merged_from_multiple_results": True
        }
        
        return merged
    
    def _merge_multiple_correction_results(
        self,
        results: List[AutoCorrectionResult]
    ) -> Optional[AutoCorrectionResult]:
        """Merge multiple correction results"""
        
        if not results:
            return None
        
        merged = results[0]
        for result in results[1:]:
            merged = self._merge_correction_results(merged, result)
        
        return merged
    
    def _build_enhanced_result(
        self,
        validation_result: ComprehensiveValidationResult,
        correction_result: Optional[AutoCorrectionResult]
    ) -> EnhancedValidationResult:
        """Build enhanced validation result"""
        
        corrections_applied = correction_result.corrections_applied if correction_result else []
        corrections_queued = correction_result.corrections_queued if correction_result else []
        
        time_saved = correction_result.estimated_time_saved if correction_result else 0.0
        zero_decision_achieved = (
            validation_result.overall_compliant and
            len(corrections_queued) == 0
        )
        
        return EnhancedValidationResult(
            validation_result=validation_result,
            correction_result=correction_result,
            corrections_applied=len(corrections_applied),
            corrections_queued=len(corrections_queued),
            time_saved_minutes=time_saved,
            final_compliance_score=validation_result.compliance_score,
            zero_decision_achieved=zero_decision_achieved,
            processing_summary={
                "auto_corrections_enabled": True,
                "correction_mode": self.settings.mode.value,
                "timing_strategy": self.settings.timing.value
            }
        )
    
    def _adjust_thresholds_for_mode(self):
        """Adjust correction thresholds based on mode"""
        
        if self.settings.mode == CorrectionMode.CONSERVATIVE:
            self.correction_engine.AUTO_APPLY_THRESHOLD = 0.95
            self.correction_engine.REVIEW_QUEUE_THRESHOLD = 0.80
        elif self.settings.mode == CorrectionMode.AGGRESSIVE:
            self.correction_engine.AUTO_APPLY_THRESHOLD = 0.85
            self.correction_engine.REVIEW_QUEUE_THRESHOLD = 0.60
        # BALANCED mode uses default thresholds
    
    async def get_correction_analytics(
        self,
        db_session: AsyncSession,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get analytics about auto-correction performance"""
        
        # This would query correction results and provide analytics
        # For now, return a placeholder structure
        
        return {
            "period_days": days_back,
            "total_invoices_processed": 0,
            "corrections": {
                "auto_applied": 0,
                "queued_for_review": 0,
                "failed": 0,
                "success_rate": 0.0
            },
            "time_savings": {
                "total_minutes_saved": 0.0,
                "average_per_invoice": 0.0
            },
            "compliance_improvement": {
                "before_correction_score": 0.0,
                "after_correction_score": 0.0,
                "improvement": 0.0
            },
            "zero_decision_workflow": {
                "achieved_count": 0,
                "total_processed": 0,
                "success_rate": 0.0
            },
            "cost_analysis": {
                "total_cost": 0.0,
                "average_per_invoice": 0.0,
                "cost_per_correction": 0.0
            }
        }

# Convenience functions

async def validate_and_auto_correct(
    invoice: InvoiceData,
    db_session: AsyncSession,
    user_id: str,
    validation_trigger: ValidationTrigger = ValidationTrigger.USER,
    correction_mode: CorrectionMode = CorrectionMode.BALANCED
) -> EnhancedValidationResult:
    """
    Convenience function for validation with auto-correction
    
    Args:
        invoice: Invoice to validate and correct
        db_session: Database session
        user_id: User ID
        validation_trigger: What triggered validation
        correction_mode: Correction mode to use
        
    Returns:
        Enhanced validation result with corrections
    """
    settings = CorrectionSettings(mode=correction_mode)
    orchestrator = AutoCorrectionOrchestrator(settings)
    
    return await orchestrator.validate_and_correct_invoice(
        invoice, db_session, user_id, validation_trigger
    )

async def zero_decision_validation(
    invoice: InvoiceData,
    db_session: AsyncSession,
    user_id: str
) -> EnhancedValidationResult:
    """
    Attempt zero-decision validation workflow
    
    Args:
        invoice: Invoice to process
        db_session: Database session
        user_id: User ID
        
    Returns:
        Enhanced validation result optimized for zero decisions
    """
    settings = CorrectionSettings(
        mode=CorrectionMode.BALANCED,
        timing=CorrectionTiming.ITERATIVE,
        max_iterations=3,
        auto_apply_threshold=0.88,  # Slightly lower for better automation
        enable_learning=True
    )
    
    orchestrator = AutoCorrectionOrchestrator(settings)
    
    return await orchestrator.validate_and_correct_invoice(
        invoice, db_session, user_id, ValidationTrigger.AUTO, settings
    )