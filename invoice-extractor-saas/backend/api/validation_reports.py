"""
French Compliance Validation Reports API

This module provides API endpoints for French compliance validation reports,
error management, and expert-comptable tools. It offers comprehensive error
reporting with professional French messages and actionable fix suggestions.

Features:
- Comprehensive validation reports with French error taxonomy
- Error pattern analytics and insights
- Fix suggestions with step-by-step guidance
- Validation history and tracking
- Expert-comptable dashboard endpoints
- Error feedback and learning system
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from uuid import UUID

from core.database import get_db
from core.exceptions import ValidationError, handle_database_error
from models.user import User
from models.french_compliance import (
    FrenchComplianceValidation,
    ValidationErrorPattern,
    ErrorSeverity,
    ValidationTrigger
)
from schemas.invoice import InvoiceData
from core.french_compliance.validation_orchestrator import (
    validate_invoice_comprehensive,
    validate_for_export,
    quick_validation_check,
    ComprehensiveValidationResult
)
from core.french_compliance.error_taxonomy import (
    FrenchComplianceErrorTaxonomy,
    ErrorContext,
    ErrorCategory,
    get_error_catalog,
    search_error_solutions
)
from api.auth import get_current_user
from core.gdpr_audit import log_audit_event

router = APIRouter(prefix="/api/validation-reports", tags=["Validation Reports"])

# Pydantic models for request/response
from pydantic import BaseModel, Field
from typing import Literal

class ValidationRequest(BaseModel):
    """Request model for invoice validation"""
    invoice_data: InvoiceData
    validation_type: Literal["comprehensive", "export", "quick"] = "comprehensive"
    export_format: Optional[str] = None
    include_pcg_mapping: bool = True
    include_business_rules: bool = True

class ValidationSummary(BaseModel):
    """Summary model for validation results"""
    invoice_id: str
    validation_timestamp: datetime
    overall_compliant: bool
    compliance_score: float
    error_count: int
    warning_count: int
    info_count: int
    compliance_status: str
    estimated_fix_time: Optional[str]
    top_issues: List[str]

class ErrorDetailResponse(BaseModel):
    """Detailed error information response"""
    code: str
    category: str
    severity: str
    french_title: str
    french_description: str
    fix_suggestion: str
    fix_complexity: str
    regulatory_reference: Optional[str]
    examples: List[str]
    prevention_tips: List[str]
    estimated_fix_time: str

class FixSuggestionRequest(BaseModel):
    """Request for fix suggestions"""
    error_codes: List[str]
    context: Optional[Dict[str, Any]] = None

class FeedbackRequest(BaseModel):
    """Feedback on error resolution"""
    error_code: str
    success: bool
    fix_method: Optional[str] = None
    time_taken_minutes: Optional[int] = None
    user_comments: Optional[str] = None

class AnalyticsRequest(BaseModel):
    """Request for error analytics"""
    days_back: int = Field(default=30, ge=1, le=365)
    category: Optional[str] = None
    severity: Optional[str] = None

# Validation endpoints

@router.post("/validate", response_model=Dict[str, Any])
async def validate_invoice(
    request: ValidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Perform comprehensive French compliance validation on an invoice
    
    This endpoint provides professional-grade validation with French error taxonomy,
    designed specifically for expert-comptables.
    """
    try:
        # GDPR audit log
        await log_audit_event(
            db,
            user_id=current_user.id,
            operation_type="invoice_validation_request",
            data_categories=["invoice_data", "validation_results"],
            risk_level="medium",
            details={
                "invoice_number": request.invoice_data.invoice_number,
                "validation_type": request.validation_type,
                "user_id": str(current_user.id),
                "purpose": "french_compliance_validation"
            }
        )
        
        # Perform validation based on type
        if request.validation_type == "comprehensive":
            result = await validate_invoice_comprehensive(
                request.invoice_data,
                db,
                ValidationTrigger.USER,
                request.include_pcg_mapping,
                request.include_business_rules
            )
        elif request.validation_type == "export":
            result = await validate_for_export(
                request.invoice_data,
                db,
                request.export_format or "sage"
            )
        elif request.validation_type == "quick":
            quick_result = await quick_validation_check(request.invoice_data, db)
            return {"validation_result": quick_result}
        else:
            raise ValidationError("Type de validation non supporté")
        
        # Format response for frontend consumption
        response = {
            "validation_summary": {
                "invoice_id": result.invoice_id,
                "validation_timestamp": result.validation_timestamp.isoformat(),
                "overall_compliant": result.overall_compliant,
                "compliance_score": result.compliance_score,
                "error_count": len(result.error_report.errors),
                "warning_count": len(result.error_report.warnings),
                "info_count": len(result.error_report.infos),
                "compliance_status": result.error_report.compliance_status,
                "estimated_fix_time": result.error_report.estimated_fix_time,
                "top_issues": result.error_report.fix_priority_order[:5]
            },
            "error_details": [
                {
                    "code": error.error_details.code,
                    "category": error.error_details.category.value,
                    "severity": error.error_details.severity.value,
                    "french_title": error.error_details.french_title,
                    "french_description": error.error_details.french_description,
                    "fix_suggestion": error.error_details.fix_suggestion,
                    "field_name": error.field_name,
                    "field_value": error.field_value,
                    "context": error.context.value
                }
                for error in result.error_report.errors
            ],
            "warnings": [
                {
                    "code": warning.error_details.code,
                    "category": warning.error_details.category.value,
                    "severity": warning.error_details.severity.value,
                    "french_title": warning.error_details.french_title,
                    "french_description": warning.error_details.french_description,
                    "fix_suggestion": warning.error_details.fix_suggestion,
                    "field_name": warning.field_name
                }
                for warning in result.error_report.warnings
            ],
            "recommendations": result.recommendations,
            "next_actions": result.next_actions,
            "performance_metrics": result.performance_metrics,
            "validation_components": {
                "siren_validation": result.validation_components.siren_validation,
                "tva_validation": {
                    "is_valid": result.validation_components.tva_validation.is_valid if result.validation_components.tva_validation else None,
                    "compliance_score": result.validation_components.tva_validation.compliance_score if result.validation_components.tva_validation else None,
                    "errors": result.validation_components.tva_validation.errors if result.validation_components.tva_validation else [],
                    "warnings": result.validation_components.tva_validation.warnings if result.validation_components.tva_validation else []
                },
                "mandatory_fields": result.validation_components.mandatory_fields_validation,
                "pcg_mapping": result.validation_components.pcg_mapping_validation
            }
        }
        
        return response
        
    except Exception as e:
        raise handle_database_error("validation", e)

@router.get("/invoice/{invoice_id}/reports", response_model=List[ValidationSummary])
async def get_invoice_validation_history(
    invoice_id: UUID = Path(..., description="Invoice ID"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get validation history for a specific invoice"""
    try:
        stmt = (
            select(FrenchComplianceValidation)
            .where(FrenchComplianceValidation.invoice_id == invoice_id)
            .order_by(desc(FrenchComplianceValidation.validation_timestamp))
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        validations = result.scalars().all()
        
        summaries = []
        for validation in validations:
            summary = ValidationSummary(
                invoice_id=str(validation.invoice_id),
                validation_timestamp=validation.validation_timestamp,
                overall_compliant=validation.overall_compliance_score >= 95.0,
                compliance_score=float(validation.overall_compliance_score or 0),
                error_count=len(validation.validation_errors or []),
                warning_count=len(validation.validation_warnings or []),
                info_count=0,  # Could be calculated from validation details
                compliance_status="compliant" if validation.overall_compliance_score >= 95.0 else "non_compliant",
                estimated_fix_time=None,  # Could be calculated
                top_issues=validation.validation_errors[:3] if validation.validation_errors else []
            )
            summaries.append(summary)
        
        return summaries
        
    except Exception as e:
        raise handle_database_error("get_validation_history", e)

# Error management endpoints

@router.get("/errors/catalog", response_model=Dict[str, Any])
async def get_error_catalog_endpoint(
    category: Optional[str] = Query(None, description="Filter by error category"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    search: Optional[str] = Query(None, description="Search term"),
    current_user: User = Depends(get_current_user)
):
    """Get the French error catalog with optional filtering"""
    try:
        catalog = get_error_catalog()
        
        if search:
            # Search for errors
            results = search_error_solutions(search)
            return {
                "search_term": search,
                "results": [
                    {
                        "code": error.code,
                        "category": error.category.value,
                        "severity": error.severity.value,
                        "french_title": error.french_title,
                        "french_description": error.french_description,
                        "fix_suggestion": error.fix_suggestion,
                        "fix_complexity": error.fix_complexity.value,
                        "regulatory_reference": error.regulatory_reference,
                        "examples": error.examples,
                        "prevention_tips": error.prevention_tips
                    }
                    for error in results
                ]
            }
        
        # Get all or filtered errors
        all_errors = list(catalog.error_catalog.values())
        
        if category:
            all_errors = [e for e in all_errors if e.category.value == category]
        
        if severity:
            all_errors = [e for e in all_errors if e.severity.value == severity]
        
        return {
            "total_errors": len(all_errors),
            "categories": list(set(e.category.value for e in all_errors)),
            "severities": list(set(e.severity.value for e in all_errors)),
            "errors": [
                {
                    "code": error.code,
                    "category": error.category.value,
                    "severity": error.severity.value,
                    "french_title": error.french_title,
                    "french_description": error.french_description,
                    "fix_complexity": error.fix_complexity.value
                }
                for error in all_errors
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du catalogue: {str(e)}")

@router.get("/errors/{error_code}", response_model=ErrorDetailResponse)
async def get_error_details(
    error_code: str = Path(..., description="Error code (e.g., FR001)"),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific error"""
    try:
        catalog = get_error_catalog()
        error_details = catalog.get_error_details(error_code)
        
        if not error_details:
            raise HTTPException(status_code=404, detail=f"Code d'erreur non trouvé: {error_code}")
        
        # Calculate estimated fix time
        time_mapping = {
            "simple": "1-5 minutes",
            "moderate": "10-30 minutes",
            "complex": "1-2 heures",
            "systematic": "Plusieurs heures à plusieurs jours"
        }
        
        return ErrorDetailResponse(
            code=error_details.code,
            category=error_details.category.value,
            severity=error_details.severity.value,
            french_title=error_details.french_title,
            french_description=error_details.french_description,
            fix_suggestion=error_details.fix_suggestion,
            fix_complexity=error_details.fix_complexity.value,
            regulatory_reference=error_details.regulatory_reference,
            examples=error_details.examples,
            prevention_tips=error_details.prevention_tips,
            estimated_fix_time=time_mapping.get(error_details.fix_complexity.value, "Temps indéterminé")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des détails: {str(e)}")

@router.post("/errors/fix-suggestions", response_model=Dict[str, Any])
async def get_fix_suggestions(
    request: FixSuggestionRequest,
    current_user: User = Depends(get_current_user)
):
    """Get detailed fix suggestions for multiple errors"""
    try:
        taxonomy = FrenchComplianceErrorTaxonomy()
        suggestions = await taxonomy.get_fix_suggestions(
            request.error_codes,
            request.context
        )
        
        return {
            "suggestions": suggestions,
            "total_errors": len(request.error_codes),
            "context": request.context
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération des suggestions: {str(e)}")

@router.post("/errors/feedback")
async def submit_fix_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit feedback on error resolution attempts"""
    try:
        taxonomy = FrenchComplianceErrorTaxonomy()
        
        await taxonomy.report_fix_feedback(
            error_code=request.error_code,
            success=request.success,
            fix_method=request.fix_method,
            time_taken=request.time_taken_minutes,
            db_session=db,
            user_comments=request.user_comments
        )
        
        return {
            "message": "Feedback enregistré avec succès",
            "error_code": request.error_code,
            "success": request.success
        }
        
    except Exception as e:
        raise handle_database_error("submit_feedback", e)

# Analytics and insights endpoints

@router.get("/analytics/error-patterns", response_model=Dict[str, Any])
async def get_error_analytics(
    days_back: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    category: Optional[str] = Query(None, description="Filter by error category"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analytics about error patterns and trends"""
    try:
        taxonomy = FrenchComplianceErrorTaxonomy()
        
        # Filter by category if specified
        category_enum = None
        if category:
            try:
                category_enum = ErrorCategory(category)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Catégorie invalide: {category}")
        
        insights = await taxonomy.get_error_analytics(db, days_back)
        
        return {
            "analysis_period": f"{days_back} jours",
            "category_filter": category,
            "insights": insights,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("get_analytics", e)

@router.get("/analytics/compliance-trends", response_model=Dict[str, Any])
async def get_compliance_trends(
    days_back: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get compliance trends and statistics"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get validation statistics
        stmt = (
            select(
                func.date(FrenchComplianceValidation.validation_timestamp).label('date'),
                func.avg(FrenchComplianceValidation.overall_compliance_score).label('avg_score'),
                func.count(FrenchComplianceValidation.id).label('validation_count'),
                func.sum(
                    func.case(
                        (FrenchComplianceValidation.overall_compliance_score >= 95, 1),
                        else_=0
                    )
                ).label('compliant_count')
            )
            .where(FrenchComplianceValidation.validation_timestamp >= cutoff_date)
            .group_by(func.date(FrenchComplianceValidation.validation_timestamp))
            .order_by(func.date(FrenchComplianceValidation.validation_timestamp))
        )
        
        result = await db.execute(stmt)
        daily_stats = result.all()
        
        # Calculate trends
        trends = []
        for stat in daily_stats:
            compliance_rate = (stat.compliant_count / stat.validation_count * 100) if stat.validation_count > 0 else 0
            trends.append({
                "date": stat.date.isoformat(),
                "average_score": float(stat.avg_score or 0),
                "validation_count": stat.validation_count,
                "compliance_rate": compliance_rate
            })
        
        # Overall statistics
        total_validations = sum(stat.validation_count for stat in daily_stats)
        total_compliant = sum(stat.compliant_count for stat in daily_stats)
        overall_compliance_rate = (total_compliant / total_validations * 100) if total_validations > 0 else 0
        
        return {
            "analysis_period": f"{days_back} jours",
            "daily_trends": trends,
            "overall_statistics": {
                "total_validations": total_validations,
                "overall_compliance_rate": overall_compliance_rate,
                "average_score": sum(float(stat.avg_score or 0) for stat in daily_stats) / len(daily_stats) if daily_stats else 0
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise handle_database_error("get_compliance_trends", e)

@router.get("/dashboard/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get summary data for expert-comptable dashboard"""
    try:
        # Last 30 days stats
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Recent validations
        recent_validations_stmt = (
            select(FrenchComplianceValidation)
            .where(FrenchComplianceValidation.validation_timestamp >= cutoff_date)
            .order_by(desc(FrenchComplianceValidation.validation_timestamp))
            .limit(10)
        )
        
        recent_result = await db.execute(recent_validations_stmt)
        recent_validations = recent_result.scalars().all()
        
        # Statistics
        stats_stmt = (
            select(
                func.count(FrenchComplianceValidation.id).label('total_validations'),
                func.avg(FrenchComplianceValidation.overall_compliance_score).label('avg_score'),
                func.sum(
                    func.case(
                        (FrenchComplianceValidation.overall_compliance_score >= 95, 1),
                        else_=0
                    )
                ).label('compliant_count')
            )
            .where(FrenchComplianceValidation.validation_timestamp >= cutoff_date)
        )
        
        stats_result = await db.execute(stats_stmt)
        stats = stats_result.first()
        
        # Most common errors
        error_patterns_stmt = (
            select(
                ValidationErrorPattern.error_type,
                ValidationErrorPattern.error_subtype,
                ValidationErrorPattern.occurrence_count
            )
            .where(ValidationErrorPattern.last_seen >= cutoff_date)
            .order_by(desc(ValidationErrorPattern.occurrence_count))
            .limit(5)
        )
        
        patterns_result = await db.execute(error_patterns_stmt)
        common_errors = patterns_result.all()
        
        compliance_rate = (stats.compliant_count / stats.total_validations * 100) if stats.total_validations > 0 else 0
        
        return {
            "period": "30 derniers jours",
            "statistics": {
                "total_validations": stats.total_validations or 0,
                "average_compliance_score": float(stats.avg_score or 0),
                "compliance_rate": compliance_rate,
                "compliant_invoices": stats.compliant_count or 0
            },
            "recent_validations": [
                {
                    "id": str(validation.id),
                    "invoice_id": str(validation.invoice_id) if validation.invoice_id else None,
                    "timestamp": validation.validation_timestamp.isoformat(),
                    "score": float(validation.overall_compliance_score or 0),
                    "is_compliant": validation.overall_compliance_score >= 95 if validation.overall_compliance_score else False,
                    "error_count": len(validation.validation_errors or [])
                }
                for validation in recent_validations
            ],
            "common_errors": [
                {
                    "error_type": error.error_type,
                    "error_code": error.error_subtype,
                    "occurrence_count": error.occurrence_count
                }
                for error in common_errors
            ],
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise handle_database_error("get_dashboard_summary", e)

# Export validation endpoints

@router.post("/validate-for-export", response_model=Dict[str, Any])
async def validate_invoice_for_export(
    invoice_data: InvoiceData,
    export_format: str = Query("sage", description="Export format (sage, ebp, ciel)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate invoice specifically for accounting software export"""
    try:
        result = await validate_for_export(invoice_data, db, export_format)
        
        # Format for export-specific response
        export_ready = result.overall_compliant and len(result.error_report.errors) == 0
        
        return {
            "export_ready": export_ready,
            "export_format": export_format,
            "validation_summary": {
                "invoice_id": result.invoice_id,
                "compliance_score": result.compliance_score,
                "error_count": len(result.error_report.errors),
                "warning_count": len(result.error_report.warnings),
                "blocking_errors": [
                    error.error_details.french_description 
                    for error in result.error_report.errors
                    if error.error_details.severity in [ErrorSeverity.CRITIQUE, ErrorSeverity.ERREUR]
                ]
            },
            "pcg_mapping": result.validation_components.pcg_mapping_validation,
            "export_recommendations": result.recommendations,
            "next_actions": result.next_actions
        }
        
    except Exception as e:
        raise handle_database_error("validate_for_export", e)