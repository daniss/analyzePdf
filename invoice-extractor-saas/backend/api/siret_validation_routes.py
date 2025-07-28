"""
SIRET Validation API Routes for French Compliance

This module provides API endpoints for comprehensive SIRET validation,
user override handling, and compliance risk management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.auth import get_current_user
from models.user import User
from models.siret_validation import (
    SIRETValidationRecord,
    SIRETValidationStatus,
    UserOverrideAction,
    ExportBlockingLevel,
    ComplianceRisk
)
from core.database import get_db
from core.validation.siret_validation_service import SIRETValidationService
from core.gdpr_audit import log_audit_event

router = APIRouter()


# Request/Response Models

class SIRETValidationRequest(BaseModel):
    siret: str = Field(..., description="SIRET number to validate")
    company_name: Optional[str] = Field(None, description="Extracted company name for comparison")
    invoice_id: Optional[str] = Field(None, description="Associated invoice ID")


class SIRETValidationResponse(BaseModel):
    # Basic validation info
    original_siret: str
    cleaned_siret: Optional[str]
    validation_status: str
    blocking_level: str
    compliance_risk: str
    traffic_light_color: str
    
    # INSEE information
    insee_company_name: Optional[str]
    company_is_active: Optional[bool]
    name_similarity_score: Optional[int]
    
    # Auto-correction details
    auto_correction_attempted: bool
    auto_correction_success: bool
    correction_details: List[str]
    
    # Error and guidance
    error_message: Optional[str]
    validation_warnings: List[str]
    french_error_message: str
    french_guidance: str
    recommended_actions: List[str]
    user_options: List[Dict[str, Any]]
    
    # Export implications
    export_blocked: bool
    export_warnings: List[str]
    liability_warning_required: bool
    
    # Metadata
    validation_record_id: Optional[str]


class UserOverrideRequest(BaseModel):
    validation_record_id: str = Field(..., description="ID of validation record to override")
    user_action: str = Field(..., description="User override action")
    justification: str = Field(..., min_length=10, description="User justification (minimum 10 characters)")
    corrected_siret: Optional[str] = Field(None, description="Corrected SIRET if applicable")


class UserOverrideResponse(BaseModel):
    success: bool
    export_allowed: bool
    compliance_risk: str
    message: str


# API Endpoints

@router.post("/validate", response_model=SIRETValidationResponse)
async def validate_siret(
    request: SIRETValidationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform comprehensive SIRET validation with French compliance handling
    
    This endpoint validates a SIRET number against the INSEE database and
    provides detailed French compliance guidance for handling failures.
    """
    
    try:
        # Initialize validation service
        validation_service = SIRETValidationService()
        
        # Perform comprehensive validation
        result = await validation_service.validate_siret_comprehensive(
            siret=request.siret,
            extracted_company_name=request.company_name,
            db_session=db,
            invoice_id=request.invoice_id,
            user_id=str(current_user.id)
        )
        
        # Get validation record ID if created
        validation_record_id = None
        if request.invoice_id:
            record_query = await db.execute(
                select(SIRETValidationRecord)
                .where(SIRETValidationRecord.invoice_id == request.invoice_id)
                .order_by(SIRETValidationRecord.created_at.desc())
                .limit(1)
            )
            record = record_query.scalar_one_or_none()
            if record:
                validation_record_id = str(record.id)
        
        # Convert to response format
        response = SIRETValidationResponse(
            original_siret=result.original_siret,
            cleaned_siret=result.cleaned_siret,
            validation_status=result.validation_status.value,
            blocking_level=result.blocking_level.value,
            compliance_risk=result.compliance_risk.value,
            traffic_light_color=result.traffic_light_color,
            insee_company_name=result.insee_company_name,
            company_is_active=result.insee_info.is_active if result.insee_info else None,
            name_similarity_score=result.name_similarity_score,
            auto_correction_attempted=result.auto_correction_attempted,
            auto_correction_success=result.auto_correction_success,
            correction_details=result.correction_details,
            error_message=result.error_message,
            validation_warnings=result.validation_warnings,
            french_error_message=result.french_error_message,
            french_guidance=result.french_guidance,
            recommended_actions=result.recommended_actions,
            user_options=result.user_options,
            export_blocked=result.export_blocked,
            export_warnings=result.export_warnings,
            liability_warning_required=result.liability_warning_required,
            validation_record_id=validation_record_id
        )
        
        return response
        
    except Exception as e:
        # Log error for debugging
        await log_audit_event(
            db,
            user_id=str(current_user.id),
            operation_type="siret_validation_error",
            data_categories=["system_error"],
            risk_level="high",
            details={"error": str(e), "siret": request.siret}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la validation SIRET: {str(e)}"
        )


@router.post("/revalidate/{invoice_id}")
async def revalidate_invoice_siret(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Re-validate SIRET numbers for an invoice after field updates
    
    This endpoint re-runs SIRET validation for both vendor and customer
    SIRET numbers found in the invoice data.
    """
    
    try:
        from crud.invoice import get_invoice_by_id, get_extracted_data
        
        # Get the invoice
        invoice = await get_invoice_by_id(
            db=db,
            invoice_id=uuid.UUID(invoice_id),
            user_id=current_user.id
        )
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get extracted data
        extracted_data_dict = await get_extracted_data(
            db=db,
            invoice_id=invoice.id,
            user_id=current_user.id
        )
        
        if not extracted_data_dict:
            raise HTTPException(status_code=404, detail="Invoice data not found")
        
        # Handle both old format (wrapped in "invoice_data") and new format (direct)
        if "invoice_data" in extracted_data_dict:
            invoice_data = extracted_data_dict["invoice_data"]
        else:
            invoice_data = extracted_data_dict
        
        # Initialize validation service
        validation_service = SIRETValidationService()
        
        validation_results = {}
        
        # Re-validate vendor SIRET if exists
        vendor_siret = None
        vendor_name = None
        
        if "vendor" in invoice_data and isinstance(invoice_data["vendor"], dict):
            vendor_siret = invoice_data["vendor"].get("siret_number")
            vendor_name = invoice_data["vendor"].get("name")
        else:
            # Check legacy fields
            vendor_name = invoice_data.get("vendor_name")
        
        if vendor_siret:
            try:
                vendor_result = await validation_service.validate_siret_comprehensive(
                    siret=vendor_siret,
                    extracted_company_name=vendor_name,
                    db_session=db,
                    invoice_id=invoice_id,
                    user_id=str(current_user.id)
                )
                validation_results["vendor"] = {
                    "siret": vendor_siret,
                    "status": vendor_result.validation_status.value,
                    "traffic_light": vendor_result.traffic_light_color,
                    "export_blocked": vendor_result.export_blocked,
                    "message": vendor_result.french_error_message
                }
            except Exception as e:
                validation_results["vendor"] = {
                    "siret": vendor_siret,
                    "status": "error",
                    "error": str(e)
                }
        
        # Re-validate customer SIRET if exists
        customer_siret = None
        customer_name = None
        
        if "customer" in invoice_data and isinstance(invoice_data["customer"], dict):
            customer_siret = invoice_data["customer"].get("siret_number")
            customer_name = invoice_data["customer"].get("name")
        else:
            # Check legacy fields
            customer_name = invoice_data.get("customer_name")
        
        if customer_siret:
            try:
                customer_result = await validation_service.validate_siret_comprehensive(
                    siret=customer_siret,
                    extracted_company_name=customer_name,
                    db_session=db,
                    invoice_id=invoice_id,
                    user_id=str(current_user.id)
                )
                validation_results["customer"] = {
                    "siret": customer_siret,
                    "status": customer_result.validation_status.value,
                    "traffic_light": customer_result.traffic_light_color,
                    "export_blocked": customer_result.export_blocked,
                    "message": customer_result.french_error_message
                }
            except Exception as e:
                validation_results["customer"] = {
                    "siret": customer_siret,
                    "status": "error",
                    "error": str(e)
                }
        
        # Log the re-validation event
        await log_audit_event(
            db,
            user_id=str(current_user.id),
            operation_type="siret_revalidation",
            data_categories=["invoice_validation"],
            risk_level="medium",
            details={
                "invoice_id": invoice_id,
                "validation_results": validation_results
            }
        )
        
        return {
            "success": True,
            "message": "Validation SIRET mise à jour avec succès",
            "validation_results": validation_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        await log_audit_event(
            db,
            user_id=str(current_user.id),
            operation_type="siret_revalidation_error",
            data_categories=["system_error"],
            risk_level="high",
            details={"error": str(e), "invoice_id": invoice_id}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la re-validation SIRET: {str(e)}"
        )


@router.post("/override", response_model=UserOverrideResponse)
async def handle_user_override(
    request: UserOverrideRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle user override actions for SIRET validation failures
    
    This endpoint allows expert-comptables to make informed decisions about
    SIRET validation failures with proper audit trail and liability tracking.
    """
    
    try:
        # Validate user action
        try:
            user_action = UserOverrideAction(request.user_action)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Action utilisateur invalide: {request.user_action}"
            )
        
        # Validate SIRET format if correction provided
        if user_action == UserOverrideAction.MANUAL_CORRECTION and request.corrected_siret:
            if not request.corrected_siret.isdigit() or len(request.corrected_siret) != 14:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="SIRET corrigé doit contenir exactement 14 chiffres"
                )
        
        # Initialize validation service
        validation_service = SIRETValidationService()
        
        # Handle the override
        result = await validation_service.handle_user_override(
            validation_record_id=request.validation_record_id,
            user_action=user_action,
            user_justification=request.justification,
            corrected_siret=request.corrected_siret,
            db_session=db,
            user_id=str(current_user.id)
        )
        
        return UserOverrideResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        # Log error for debugging
        await log_audit_event(
            db,
            user_id=str(current_user.id),
            operation_type="siret_override_error",
            data_categories=["system_error"],
            risk_level="high",
            details={"error": str(e), "validation_record_id": request.validation_record_id}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du traitement de l'action utilisateur: {str(e)}"
        )


@router.get("/validation-history/{invoice_id}")
async def get_validation_history(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get SIRET validation history for an invoice
    
    Returns complete audit trail of SIRET validation attempts and user actions.
    """
    
    try:
        # Validate UUID format
        invoice_uuid = uuid.UUID(invoice_id)
        
        # Get validation records
        result = await db.execute(
            select(SIRETValidationRecord)
            .where(SIRETValidationRecord.invoice_id == invoice_uuid)
            .order_by(SIRETValidationRecord.created_at.desc())
        )
        
        records = result.scalars().all()
        
        # Convert to response format
        history = []
        for record in records:
            history.append({
                "id": str(record.id),
                "extracted_siret": record.extracted_siret,
                "cleaned_siret": record.cleaned_siret,
                "corrected_siret": record.corrected_siret,
                "validation_status": record.validation_status,
                "blocking_level": record.blocking_level,
                "compliance_risk": record.compliance_risk,
                "insee_company_name": record.insee_company_name,
                "name_similarity_score": record.name_similarity_score,
                "user_action": record.user_action,
                "user_justification": record.user_justification,
                "export_blocked": record.export_blocked,
                "export_warnings": record.export_warnings,
                "auto_correction_attempted": record.auto_correction_attempted,
                "auto_correction_success": record.auto_correction_success,
                "liability_warning_acknowledged": record.liability_warning_acknowledged,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
                "override_timestamp": record.override_timestamp.isoformat() if record.override_timestamp else None
            })
        
        return {
            "invoice_id": invoice_id,
            "validation_count": len(history),
            "history": history
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format d'ID facture invalide"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération de l'historique: {str(e)}"
        )


@router.get("/compliance-guidance/{validation_status}")
async def get_compliance_guidance(
    validation_status: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get French compliance guidance for a specific SIRET validation status
    
    Returns detailed legal implications and recommended actions.
    """
    
    try:
        # Validate status
        try:
            status_enum = SIRETValidationStatus(validation_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Statut de validation invalide: {validation_status}"
            )
        
        # Generate guidance based on status
        guidance = {
            SIRETValidationStatus.VALID: {
                "legal_implications": "Aucun risque. SIRET validé par l'INSEE.",
                "tax_deduction_risk": "low",
                "audit_risk_level": "low",
                "recommendations": [
                    "Export automatique autorisé",
                    "Aucune action supplémentaire requise"
                ]
            },
            SIRETValidationStatus.NOT_FOUND: {
                "legal_implications": "Risque élevé de rejet de déduction TVA. Responsabilité professionnelle engagée.",
                "tax_deduction_risk": "high",
                "audit_risk_level": "high",
                "recommendations": [
                    "Vérifier SIRET sur document original",
                    "Contacter le fournisseur",
                    "Documenter toute décision d'acceptation",
                    "Considérer un contrôle supplémentaire"
                ]
            },
            SIRETValidationStatus.INACTIVE: {
                "legal_implications": "Risque modéré. Société peut facturer après cessation pour travaux antérieurs.",
                "tax_deduction_risk": "medium",
                "audit_risk_level": "medium",
                "recommendations": [
                    "Vérifier contexte de la prestation",
                    "Documenter la légitimité",
                    "Confirmer avec le fournisseur si nécessaire"
                ]
            },
            SIRETValidationStatus.NAME_MISMATCH: {
                "legal_implications": "Risque faible. Divergence nom commercial/raison sociale acceptée.",
                "tax_deduction_risk": "low",
                "audit_risk_level": "low",
                "recommendations": [
                    "Annoter la divergence",
                    "Export autorisé avec mention",
                    "Documenter l'explication"
                ]
            },
            SIRETValidationStatus.MALFORMED: {
                "legal_implications": "Erreur de forme. Correction obligatoire pour validité fiscale.",
                "tax_deduction_risk": "high",
                "audit_risk_level": "high",
                "recommendations": [
                    "Corriger le format SIRET",
                    "Vérifier sur document source",
                    "Ne pas exporter sans correction"
                ]
            }
        }
        
        result = guidance.get(status_enum, {
            "legal_implications": "Statut non reconnu",
            "tax_deduction_risk": "unknown",
            "audit_risk_level": "unknown",
            "recommendations": ["Contacter le support technique"]
        })
        
        return {
            "validation_status": validation_status,
            "guidance": result,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des conseils: {str(e)}"
        )


@router.get("/export-status/{validation_record_id}")
async def get_export_status(
    validation_record_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current export status for a SIRET validation record
    
    Returns whether export is allowed and any warnings or notes.
    """
    
    try:
        # Get validation record
        result = await db.execute(
            select(SIRETValidationRecord)
            .where(SIRETValidationRecord.id == validation_record_id)
        )
        
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enregistrement de validation non trouvé"
            )
        
        return {
            "validation_record_id": validation_record_id,
            "export_allowed": not record.export_blocked,
            "export_blocked": record.export_blocked,
            "export_warnings": record.export_warnings or [],
            "export_notes": record.export_notes,
            "compliance_risk": record.compliance_risk,
            "user_action_taken": record.user_action is not None,
            "user_action": record.user_action,
            "liability_warning_acknowledged": record.liability_warning_acknowledged,
            "last_updated": record.updated_at.isoformat() if record.updated_at else record.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la vérification du statut d'export: {str(e)}"
        )