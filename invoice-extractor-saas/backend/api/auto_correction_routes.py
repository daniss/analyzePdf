"""
Auto-Correction API Routes

This module provides API endpoints for the intelligent auto-correction system,
allowing expert-comptables to access auto-correction features, review queues,
and correction analytics through the REST API.

Features:
- Auto-correction endpoints
- Manual review queue management
- Expert review interfaces
- Correction analytics and reporting
- Zero-decision workflow endpoints
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from core.database import get_db
from api.auth import get_current_user
from schemas.invoice import InvoiceData
from core.auto_correction.correction_orchestrator import (
    AutoCorrectionOrchestrator,
    CorrectionSettings,
    CorrectionMode,
    CorrectionTiming,
    EnhancedValidationResult,
    validate_and_auto_correct,
    zero_decision_validation
)
from core.auto_correction.auto_correction_engine import (
    AutoCorrectionResult,
    CorrectionSuggestion,
    CorrectionDecision,
    CorrectionStatus,
    CorrectionConfidence,
    CorrectionAction,
    get_correction_suggestions_only
)
from core.auto_correction.manual_review_queue import (
    ManualReviewQueueManager,
    ManualReviewItem,
    ReviewPriority,
    ReviewStatus,
    ExpertAction,
    get_expert_review_queue
)
from models.french_compliance import ValidationTrigger
from crud.invoice import get_invoice_by_id

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/auto-correction", tags=["auto-correction"])
security = HTTPBearer()

# Pydantic models for API

class CorrectionSettingsRequest(BaseModel):
    """Request model for correction settings"""
    mode: CorrectionMode = CorrectionMode.BALANCED
    timing: CorrectionTiming = CorrectionTiming.AFTER_VALIDATION
    max_iterations: int = Field(default=3, ge=1, le=5)
    auto_apply_threshold: float = Field(default=0.90, ge=0.5, le=1.0)
    review_queue_threshold: float = Field(default=0.70, ge=0.5, le=1.0)
    cost_limit_per_invoice: float = Field(default=5.0, ge=0.0, le=50.0)
    enable_learning: bool = True
    enable_manual_review: bool = True

class ValidationWithCorrectionRequest(BaseModel):
    """Request model for validation with auto-correction"""
    invoice_id: str
    correction_settings: Optional[CorrectionSettingsRequest] = None
    validation_trigger: ValidationTrigger = ValidationTrigger.USER

class CorrectionSuggestionResponse(BaseModel):
    """Response model for correction suggestions"""
    field_name: str
    original_value: Optional[str] = None
    corrected_value: str
    correction_action: CorrectionAction
    confidence: float
    reasoning: str
    evidence: Dict[str, Any] = {}
    cost_estimate: Optional[float] = None
    requires_external_validation: bool = False

class CorrectionDecisionResponse(BaseModel):
    """Response model for correction decisions"""
    suggestion: CorrectionSuggestionResponse
    decision: CorrectionStatus
    confidence_level: CorrectionConfidence
    auto_apply: bool
    timestamp: datetime
    applied_by: Optional[str] = None
    review_notes: Optional[str] = None

class AutoCorrectionResultResponse(BaseModel):
    """Response model for auto-correction results"""
    invoice_id: str
    corrections_applied: List[CorrectionDecisionResponse] = []
    corrections_queued: List[CorrectionDecisionResponse] = []
    corrections_failed: List[CorrectionDecisionResponse] = []
    total_corrections_attempted: int = 0
    auto_correction_success_rate: float = 0.0
    estimated_time_saved: float = 0.0
    processing_metrics: Dict[str, Any] = {}

class EnhancedValidationResultResponse(BaseModel):
    """Response model for enhanced validation results"""
    invoice_id: str
    validation_result: Dict[str, Any]  # ComprehensiveValidationResult as dict
    correction_result: Optional[AutoCorrectionResultResponse] = None
    corrections_applied: int = 0
    corrections_queued: int = 0
    time_saved_minutes: float = 0.0
    cost_incurred: float = 0.0
    final_compliance_score: float = 0.0
    zero_decision_achieved: bool = False
    processing_summary: Dict[str, Any] = {}

class ExpertReviewRequest(BaseModel):
    """Request model for expert review submission"""
    action: ExpertAction
    expert_notes: Optional[str] = None
    modified_value: Optional[str] = None
    modified_reasoning: Optional[str] = None
    expert_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    time_spent_minutes: Optional[int] = Field(None, ge=0, le=480)

class ReviewQueueResponse(BaseModel):
    """Response model for review queue"""
    expert_id: str
    pending_items: List[Dict[str, Any]] = []
    completed_items: List[Dict[str, Any]] = []
    queue_stats: Dict[str, Any] = {}
    expert_stats: Dict[str, Any] = {}

# API Endpoints

@router.post("/validate-and-correct", response_model=EnhancedValidationResultResponse)
async def validate_and_correct_invoice(
    request: ValidationWithCorrectionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Validate invoice with intelligent auto-correction
    
    This endpoint performs comprehensive French compliance validation
    with automatic error correction when confidence is high.
    """
    
    try:
        # Get invoice data
        invoice = await get_invoice_by_id(db, uuid.UUID(request.invoice_id), current_user.id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        
        # Convert to InvoiceData (simplified)
        invoice_data = InvoiceData(
            id=invoice.id,
            invoice_number=invoice.extracted_data.get("invoice_number"),
            date=invoice.extracted_data.get("date"),
            vendor_name=invoice.extracted_data.get("vendor_name"),
            customer_name=invoice.extracted_data.get("customer_name"),
            total_ttc=invoice.extracted_data.get("total_ttc"),
            # Add other fields as needed
        )
        
        # Build correction settings
        settings = None
        if request.correction_settings:
            settings = CorrectionSettings(
                mode=request.correction_settings.mode,
                timing=request.correction_settings.timing,
                max_iterations=request.correction_settings.max_iterations,
                auto_apply_threshold=request.correction_settings.auto_apply_threshold,
                review_queue_threshold=request.correction_settings.review_queue_threshold,
                cost_limit_per_invoice=request.correction_settings.cost_limit_per_invoice,
                enable_learning=request.correction_settings.enable_learning,
                enable_manual_review=request.correction_settings.enable_manual_review
            )
        
        # Perform validation with auto-correction
        orchestrator = AutoCorrectionOrchestrator(settings)
        result = await orchestrator.validate_and_correct_invoice(
            invoice_data,
            db,
            str(current_user.id),
            request.validation_trigger,
            settings
        )
        
        # Convert correction decisions to response format
        def convert_correction_decision(decision: CorrectionDecision) -> CorrectionDecisionResponse:
            return CorrectionDecisionResponse(
                suggestion=CorrectionSuggestionResponse(
                    field_name=decision.suggestion.field_name,
                    original_value=str(decision.suggestion.original_value) if decision.suggestion.original_value else None,
                    corrected_value=str(decision.suggestion.corrected_value),
                    correction_action=decision.suggestion.correction_action,
                    confidence=decision.suggestion.confidence,
                    reasoning=decision.suggestion.reasoning,
                    evidence=decision.suggestion.evidence,
                    cost_estimate=decision.suggestion.cost_estimate,
                    requires_external_validation=decision.suggestion.requires_external_validation
                ),
                decision=decision.decision,
                confidence_level=decision.confidence_level,
                auto_apply=decision.auto_apply,
                timestamp=decision.timestamp,
                applied_by=decision.applied_by,
                review_notes=decision.review_notes
            )
        
        # Build response
        correction_response = None
        if result.correction_result:
            correction_response = AutoCorrectionResultResponse(
                invoice_id=result.correction_result.invoice_id,
                corrections_applied=[convert_correction_decision(d) for d in result.correction_result.corrections_applied],
                corrections_queued=[convert_correction_decision(d) for d in result.correction_result.corrections_queued],
                corrections_failed=[convert_correction_decision(d) for d in result.correction_result.corrections_failed],
                total_corrections_attempted=result.correction_result.total_corrections_attempted,
                auto_correction_success_rate=result.correction_result.auto_correction_success_rate,
                estimated_time_saved=result.correction_result.estimated_time_saved,
                processing_metrics=result.correction_result.processing_metrics
            )
        
        response = EnhancedValidationResultResponse(
            invoice_id=request.invoice_id,
            validation_result=result.validation_result.to_dict() if hasattr(result.validation_result, 'to_dict') else {},
            correction_result=correction_response,
            corrections_applied=result.corrections_applied,
            corrections_queued=result.corrections_queued,
            time_saved_minutes=result.time_saved_minutes,
            cost_incurred=result.cost_incurred,
            final_compliance_score=result.final_compliance_score,
            zero_decision_achieved=result.zero_decision_achieved,
            processing_summary=result.processing_summary
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in validate_and_correct_invoice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-correction failed: {str(e)}"
        )

@router.post("/zero-decision-workflow", response_model=EnhancedValidationResultResponse)
async def zero_decision_workflow(
    invoice_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Attempt zero-decision workflow for expert-comptables
    
    This endpoint optimizes for minimal user intervention,
    automatically fixing errors when confidence is high.
    """
    
    try:
        # Get invoice data
        invoice = await get_invoice_by_id(db, uuid.UUID(invoice_id), current_user.id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        
        # Convert to InvoiceData
        invoice_data = InvoiceData(
            id=invoice.id,
            invoice_number=invoice.extracted_data.get("invoice_number"),
            date=invoice.extracted_data.get("date"),
            vendor_name=invoice.extracted_data.get("vendor_name"),
            customer_name=invoice.extracted_data.get("customer_name"),
            total_ttc=invoice.extracted_data.get("total_ttc"),
        )
        
        # Perform zero-decision validation
        result = await zero_decision_validation(
            invoice_data,
            db,
            str(current_user.id)
        )
        
        # Convert and return response (similar to above)
        return _convert_to_response(result, invoice_id)
        
    except Exception as e:
        logger.error(f"Error in zero_decision_workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Zero-decision workflow failed: {str(e)}"
        )

@router.get("/suggestions/{invoice_id}", response_model=List[CorrectionSuggestionResponse])
async def get_correction_suggestions(
    invoice_id: str,
    validation_errors: List[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get correction suggestions for an invoice without applying them
    
    This endpoint provides suggestions that can be reviewed before applying.
    """
    
    try:
        # Get invoice data
        invoice = await get_invoice_by_id(db, uuid.UUID(invoice_id), current_user.id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        
        # Convert to InvoiceData
        invoice_data = InvoiceData(
            id=invoice.id,
            invoice_number=invoice.extracted_data.get("invoice_number"),
            date=invoice.extracted_data.get("date"),
            vendor_name=invoice.extracted_data.get("vendor_name"),
            customer_name=invoice.extracted_data.get("customer_name"),
            total_ttc=invoice.extracted_data.get("total_ttc"),
        )
        
        # Get suggestions
        suggestions = await get_correction_suggestions_only(
            invoice_data,
            validation_errors,
            db,
            {"user_id": str(current_user.id)}
        )
        
        # Convert to response format
        response = []
        for suggestion in suggestions:
            response.append(CorrectionSuggestionResponse(
                field_name=suggestion.field_name,
                original_value=str(suggestion.original_value) if suggestion.original_value else None,
                corrected_value=str(suggestion.corrected_value),
                correction_action=suggestion.correction_action,
                confidence=suggestion.confidence,
                reasoning=suggestion.reasoning,
                evidence=suggestion.evidence,
                cost_estimate=suggestion.cost_estimate,
                requires_external_validation=suggestion.requires_external_validation
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting correction suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}"
        )

@router.get("/review-queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    include_completed: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get expert's manual review queue
    
    Returns pending corrections that require manual review.
    """
    
    try:
        queue_data = await get_expert_review_queue(
            str(current_user.id),
            db,
            include_completed
        )
        
        return ReviewQueueResponse(**queue_data)
        
    except Exception as e:
        logger.error(f"Error getting review queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review queue: {str(e)}"
        )

@router.post("/review-queue/{review_item_id}/review")
async def submit_expert_review(
    review_item_id: str,
    review_request: ExpertReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Submit expert review for a correction
    
    Allows expert-comptables to approve, reject, or modify corrections.
    """
    
    try:
        manager = ManualReviewQueueManager()
        
        success = await manager.submit_expert_review(
            review_item_id=review_item_id,
            expert_id=str(current_user.id),
            action=review_request.action,
            expert_notes=review_request.expert_notes,
            modified_value=review_request.modified_value,
            modified_reasoning=review_request.modified_reasoning,
            expert_confidence=review_request.expert_confidence,
            time_spent_minutes=review_request.time_spent_minutes,
            db_session=db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to submit review"
            )
        
        return {"message": "Review submitted successfully", "review_item_id": review_item_id}
        
    except Exception as e:
        logger.error(f"Error submitting expert review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit review: {str(e)}"
        )

@router.get("/analytics/corrections")
async def get_correction_analytics(
    days_back: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get auto-correction analytics and performance metrics
    
    Provides insights into correction effectiveness and time savings.
    """
    
    try:
        orchestrator = AutoCorrectionOrchestrator()
        analytics = await orchestrator.get_correction_analytics(db, days_back)
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting correction analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )

@router.post("/settings/update")
async def update_correction_settings(
    settings: CorrectionSettingsRequest,
    current_user = Depends(get_current_user)
):
    """
    Update user's auto-correction settings
    
    Allows customization of correction behavior per user.
    """
    
    try:
        # In a full implementation, you'd store these settings per user
        # For now, return the settings as confirmation
        
        return {
            "message": "Correction settings updated successfully",
            "settings": settings.dict(),
            "user_id": str(current_user.id)
        }
        
    except Exception as e:
        logger.error(f"Error updating correction settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )

# Helper functions

def _convert_to_response(result: EnhancedValidationResult, invoice_id: str) -> EnhancedValidationResultResponse:
    """Convert EnhancedValidationResult to API response format"""
    
    correction_response = None
    if result.correction_result:
        correction_response = AutoCorrectionResultResponse(
            invoice_id=result.correction_result.invoice_id,
            corrections_applied=[],  # Convert as needed
            corrections_queued=[],   # Convert as needed
            corrections_failed=[],   # Convert as needed
            total_corrections_attempted=result.correction_result.total_corrections_attempted,
            auto_correction_success_rate=result.correction_result.auto_correction_success_rate,
            estimated_time_saved=result.correction_result.estimated_time_saved,
            processing_metrics=result.correction_result.processing_metrics
        )
    
    return EnhancedValidationResultResponse(
        invoice_id=invoice_id,
        validation_result={},  # Convert validation result to dict
        correction_result=correction_response,
        corrections_applied=result.corrections_applied,
        corrections_queued=result.corrections_queued,
        time_saved_minutes=result.time_saved_minutes,
        cost_incurred=result.cost_incurred,
        final_compliance_score=result.final_compliance_score,
        zero_decision_achieved=result.zero_decision_achieved,
        processing_summary=result.processing_summary
    )