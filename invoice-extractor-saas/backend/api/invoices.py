from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
from datetime import datetime
import os
from enum import Enum

from schemas.invoice import (
    InvoiceCreate, InvoiceResponse, InvoiceData, SIRETValidationSummary,
    BulkUploadResponse, BatchUploadSummary, DuplicateInfo, DuplicateResolution
)
from api.auth import get_current_user
from models.user import User
from core.config import settings
from core.database import get_db
from core.pdf_processor import PDFProcessor
from core.ai.groq_processor import GroqProcessor
from crud.invoice import (
    create_invoice, get_invoice_by_id, get_user_invoices, 
    update_invoice_status, store_extracted_data, delete_invoice,
    get_extracted_data
)

# Simplified: Single processing mode for all invoices

router = APIRouter()


async def get_siret_validation_summary(db: AsyncSession, invoice_id: uuid.UUID) -> Optional[SIRETValidationSummary]:
    """Get SIRET validation summary for an invoice"""
    try:
        from sqlalchemy import select
        from models.siret_validation import SIRETValidationRecord
        
        # Query SIRET validation records for this invoice
        query = select(SIRETValidationRecord).where(SIRETValidationRecord.invoice_id == invoice_id)
        result = await db.execute(query)
        validation_records = result.scalars().all()
        
        if not validation_records:
            return None
        
        # Build summary data for frontend
        vendor_validation = None
        customer_validation = None
        
        # Group records by type (vendor/customer) based on extracted SIRET patterns
        for record in validation_records:
            validation_data = {
                "performed": True,
                "status": record.validation_status,
                "blocking_level": record.blocking_level,
                "compliance_risk": record.compliance_risk,
                "traffic_light": "green" if record.validation_status == "valid" else ("orange" if record.validation_status in ["inactive", "name_mismatch", "foreign"] else "red"),
                "export_blocked": record.export_blocked,
                "french_error_message": record.compliance_notes,
                "user_options_available": record.user_action is not None
            }
            
            # Simple heuristic: first record is vendor, second is customer
            if vendor_validation is None:
                vendor_validation = validation_data
            else:
                customer_validation = validation_data
        
        # Build overall summary
        overall_summary = {
            "any_siret_found": len(validation_records) > 0,
            "any_export_blocked": any(r.export_blocked for r in validation_records),
            "highest_risk": max((r.compliance_risk for r in validation_records), default="low"),
            "requires_user_action": any(r.user_action is None and r.validation_status != "valid" for r in validation_records)
        }
        
        return SIRETValidationSummary(
            vendor_siret_validation=vendor_validation,
            customer_siret_validation=customer_validation,
            overall_summary=overall_summary
        )
        
    except Exception as e:
        print(f"Error getting SIRET validation summary: {e}")
        return None


@router.get("/health")
async def check_health():
    """Check if Groq API is properly configured"""
    api_key = settings.GROQ_API_KEY
    groq_configured = (
        api_key and 
        api_key.strip() and 
        api_key != "your-groq-api-key-here" and
        not api_key.startswith("your-") and
        len(api_key) > 20
    )
    
    return {
        "groq_api_configured": groq_configured,
        "model": settings.AI_MODEL,
        "api_key_status": "real_key" if groq_configured else "placeholder_or_missing",
        "message": "Groq API key configured" if groq_configured else "Groq API key not configured - AI processing unavailable"
    }


@router.post("/upload", response_model=InvoiceResponse)
async def upload_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Validate file type
    if file.content_type not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # Read file content
    contents = await file.read()
    
    # Validate file size
    if len(contents) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    try:
        # Create invoice in database
        db_invoice = await create_invoice(
            db=db,
            filename=file.filename,
            file_content=contents,
            mime_type=file.content_type,
            data_controller_id=current_user.id,
            processing_purposes=["invoice_processing", "business_operations"],
            legal_basis="legitimate_interest"
        )
        
        # GDPR-COMPLIANT: Process file in memory without permanent storage
        # Store file content temporarily in database for background processing
        # This avoids GDPR issues with unencrypted filesystem storage
        
        # Create response
        invoice_response = InvoiceResponse(
            id=str(db_invoice.id),
            filename=db_invoice.filename,
            status=db_invoice.processing_status,
            created_at=db_invoice.created_at,
            data=None,
            review_status=getattr(db_invoice, 'review_status', None),
            processing_source=getattr(db_invoice, 'processing_source', 'individual'),
            batch_id=getattr(db_invoice, 'batch_id', None)
        )
        
        # Process invoice in background (GDPR-compliant - no file storage)
        print(f"🎯 Adding background task for invoice {db_invoice.id} with in-memory processing")
        background_tasks.add_task(
            process_invoice_task_memory,
            str(db_invoice.id),
            contents,  # Pass file content directly
            file.filename,
            current_user.id
        )
        print(f"📋 Background task added successfully for invoice {db_invoice.id}")
        
        return invoice_response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload invoice: {str(e)}"
        )


# Privacy-first processing removed - single pipeline approach for MVP simplicity


async def process_invoice_task_memory(invoice_id: str, file_content: bytes, filename: str, user_id: uuid.UUID):
    """GDPR-compliant background task to process invoice from memory (no file storage)"""
    import traceback
    import logging
    
    # Set up logging for background tasks
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info(f"🚀 Starting GDPR-compliant background processing for invoice {invoice_id}")
    
    # Import modules needed for background task
    from core.database import async_session_maker
    from core.pdf_processor import PDFProcessor
    from core.ai.groq_processor import GroqProcessor
    
    try:
        async with async_session_maker() as db:
            logger.info(f"📊 Database connection established for invoice {invoice_id}")
            
            try:
                # Update status to processing
                await update_invoice_status(
                    db=db,
                    invoice_id=uuid.UUID(invoice_id),
                    status="processing",
                    user_id=user_id,
                    processing_started_at=datetime.utcnow()
                )
                
                # Process file content directly from memory (GDPR-compliant)
                extracted_text, base64_images = await PDFProcessor.process_uploaded_file(file_content, filename)
                
                groq_processor = GroqProcessor()
                
                if extracted_text:
                    # Use Groq with text-only processing (very fast and cheap)
                    invoice_data = await groq_processor.process_invoice_text(
                        extracted_text,
                        invoice_id=uuid.UUID(invoice_id),
                        user_id=user_id,
                        db=db
                    )
                    processing_method = "groq_llama_text_extraction"
                    estimated_cost = 0.0001  # Groq is extremely cheap/free
                else:
                    # Groq Llama doesn't support vision, so this will fail gracefully
                    try:
                        invoice_data = await groq_processor.process_invoice_images(
                            base64_images, 
                            invoice_id=uuid.UUID(invoice_id),
                            user_id=user_id,
                            db=db
                        )
                        processing_method = "groq_vision_processing"
                        estimated_cost = 0.0001
                    except Exception as vision_error:
                        # If vision fails, extract text from images and try again
                        logger.warning(f"Vision processing failed, trying OCR: {vision_error}")
                        
                        # Try to extract text using OCR
                        ocr_text = await PDFProcessor.extract_text_from_images(base64_images)
                        if ocr_text and len(ocr_text.strip()) > 50:
                            invoice_data = await groq_processor.process_invoice_text(
                                ocr_text,
                                invoice_id=uuid.UUID(invoice_id),
                                user_id=user_id,
                                db=db
                            )
                            processing_method = "groq_ocr_fallback"
                            estimated_cost = 0.0001
                        else:
                            raise Exception("No processable content found in invoice")
                
                # Validate invoice data for French compliance
                try:
                    from core.validation.french_validator import validate_french_invoice_sync
                    validation_results = validate_french_invoice_sync(invoice_data)
                    french_compliance_result = invoice_data.validate_french_compliance() if hasattr(invoice_data, 'validate_french_compliance') else None
                    logger.info(f"French validation completed for invoice {invoice_id}")
                except Exception as validation_error:
                    logger.warning(f"French validation failed for invoice {invoice_id}: {validation_error}")
                    validation_results = {"error": str(validation_error)}
                    french_compliance_result = None
                
                # Store extracted data in database (encrypted)
                await store_extracted_data(
                    db=db,
                    invoice_id=uuid.UUID(invoice_id),
                    extracted_data={
                        "invoice_data": invoice_data.dict() if hasattr(invoice_data, 'dict') else invoice_data,
                        "validation_results": validation_results,
                        "french_compliance": french_compliance_result,
                        "processing_metadata": {
                            "processed_at": datetime.utcnow().isoformat(),
                            "image_count": len(base64_images) if base64_images else 0,
                            "text_length": len(extracted_text) if extracted_text else 0,
                            "processor": "groq-llama-3.1-8b-instant",
                            "extraction_method": processing_method,
                            "cost_per_invoice": estimated_cost,
                            "french_validation_included": french_compliance_result is not None,
                            "gdpr_compliant_processing": True,  # Flag for GDPR compliance
                            "file_stored_on_disk": False  # GDPR: No permanent file storage
                        }
                    },
                    user_id=user_id
                )
                
                # Update status to completed
                await update_invoice_status(
                    db=db,
                    invoice_id=uuid.UUID(invoice_id),
                    status="completed",
                    user_id=user_id,
                    processing_completed_at=datetime.utcnow()
                )
                
                logger.info(f"✅ Successfully processed invoice {invoice_id} using GDPR-compliant memory processing")
                
            except Exception as e:
                logger.error(f"❌ Error processing invoice {invoice_id}: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Update status to failed
                await update_invoice_status(
                    db=db,
                    invoice_id=uuid.UUID(invoice_id),
                    status="failed",
                    user_id=user_id,
                    error_message=str(e),
                    processing_completed_at=datetime.utcnow()
                )
    
    except Exception as e:
        logger.error(f"❌ Critical error in background task for invoice {invoice_id}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")


# Legacy function kept for backward compatibility - will be removed after migration

@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Get invoice from database
        invoice = await get_invoice_by_id(
            db=db,
            invoice_id=uuid.UUID(invoice_id),
            user_id=current_user.id
        )
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get extracted data if available
        extracted_data = None
        if invoice.processing_status == "completed" and invoice.extracted_data_encrypted:
            extracted_data_dict = await get_extracted_data(
                db=db,
                invoice_id=invoice.id,
                user_id=current_user.id
            )
            if extracted_data_dict:
                # Handle both old format (wrapped in "invoice_data") and new format (direct)
                if "invoice_data" in extracted_data_dict:
                    invoice_data = extracted_data_dict["invoice_data"]
                else:
                    # New format - data is stored directly
                    invoice_data = extracted_data_dict
                
                # Create full InvoiceData object with all French fields
                try:
                    extracted_data = InvoiceData(**invoice_data)
                except Exception as e:
                    # Fallback for older data format
                    print(f"Warning: Using fallback data construction for invoice {invoice_id}: {e}")
                    extracted_data = InvoiceData(
                        invoice_number=invoice_data.get("invoice_number", ""),
                        date=invoice_data.get("date", ""),
                        vendor_name=invoice_data.get("vendor_name", ""),
                        vendor_address=invoice_data.get("vendor_address", ""),
                        customer_name=invoice_data.get("customer_name", ""),
                        customer_address=invoice_data.get("customer_address", ""),
                        line_items=invoice_data.get("line_items", []),
                        subtotal=invoice_data.get("subtotal", 0.0),
                        tax=invoice_data.get("tax", 0.0),
                        total=invoice_data.get("total", 0.0),
                        # Add French fields with fallback values
                        subtotal_ht=invoice_data.get("subtotal_ht", invoice_data.get("subtotal", 0.0)),
                        total_tva=invoice_data.get("total_tva", invoice_data.get("tax", 0.0)),
                        total_ttc=invoice_data.get("total_ttc", invoice_data.get("total", 0.0)),
                        currency=invoice_data.get("currency", "EUR"),
                        tva_breakdown=invoice_data.get("tva_breakdown", [])
                    )
        
        # Get SIRET validation results if available
        siret_validation_summary = await get_siret_validation_summary(db, invoice.id)
        
        return InvoiceResponse(
            id=str(invoice.id),
            filename=invoice.filename,
            status=invoice.processing_status,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
            data=extracted_data,
            siret_validation_results=siret_validation_summary,
            error_message=getattr(invoice, 'error_message', None)
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get invoice: {str(e)}")


@router.get("/", response_model=List[InvoiceResponse])
async def list_invoices(
    skip: int = 0,
    limit: int = 10,
    status: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Get invoices from database
        invoices = await get_user_invoices(
            db=db,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            status_filter=status
        )
        
        # Convert to response format
        invoice_responses = []
        for invoice in invoices:
            # Get SIRET validation summary for each invoice
            siret_validation_summary = await get_siret_validation_summary(db, invoice.id)
            
            # Include extracted data if invoice is completed
            extracted_data = None
            if invoice.processing_status == "completed" and invoice.extracted_data_encrypted:
                try:
                    extracted_data_dict = await get_extracted_data(
                        db=db,
                        invoice_id=invoice.id,
                        user_id=current_user.id
                    )
                    if extracted_data_dict:
                        # Handle both old format (wrapped in "invoice_data") and new format (direct)
                        if "invoice_data" in extracted_data_dict:
                            invoice_data = extracted_data_dict["invoice_data"]
                        else:
                            # New format - data is stored directly
                            invoice_data = extracted_data_dict
                        try:
                            extracted_data = InvoiceData(**invoice_data)
                        except Exception as parse_error:
                            print(f"Warning: Using fallback data construction for invoice {invoice.id}: {parse_error}")
                            # Create InvoiceData with available fields and French field mappings
                            extracted_data = InvoiceData(
                                invoice_number=invoice_data.get("invoice_number", ""),
                                date=invoice_data.get("date", ""),
                                vendor_name=invoice_data.get("vendor_name", ""),
                                vendor_address=invoice_data.get("vendor_address", ""),
                                customer_name=invoice_data.get("customer_name", ""),
                                customer_address=invoice_data.get("customer_address", ""),
                                line_items=invoice_data.get("line_items", []),
                                subtotal=invoice_data.get("subtotal", 0.0),
                                tax=invoice_data.get("tax", 0.0),
                                total=invoice_data.get("total", 0.0),
                                # Map French fields properly
                                subtotal_ht=invoice_data.get("subtotal_ht", invoice_data.get("subtotal", 0.0)),
                                total_tva=invoice_data.get("total_tva", invoice_data.get("tax", 0.0)),
                                total_ttc=invoice_data.get("total_ttc", invoice_data.get("total", 0.0)),
                                currency=invoice_data.get("currency", "EUR"),
                                tva_breakdown=invoice_data.get("tva_breakdown", [])
                            )
                except Exception as e:
                    # For old invoices with decryption issues, create placeholder data
                    print(f"Failed to get extracted data for invoice {invoice.id}: {str(e)}")
                    extracted_data = InvoiceData(
                        invoice_number="N/A (Extraction Error)",
                        date=None,
                        due_date=None,
                        vendor_name="N/A (Extraction Error)",
                        customer_name="N/A (Extraction Error)",
                        subtotal_ht=None,
                        total_tva=None,
                        total_ttc=None,
                        currency="EUR",
                        line_items=[],
                        tva_breakdown=[]
                    )
            
            invoice_responses.append(InvoiceResponse(
                id=str(invoice.id),
                filename=invoice.filename,
                status=invoice.processing_status,
                created_at=invoice.created_at,
                updated_at=invoice.updated_at,
                data=extracted_data,  # Include extracted data for completed invoices
                siret_validation_results=siret_validation_summary,
                error_message=getattr(invoice, 'error_message', None),
                # Include new review workflow and batch processing fields
                review_status=getattr(invoice, 'review_status', None),
                processing_source=getattr(invoice, 'processing_source', 'individual'),
                batch_id=getattr(invoice, 'batch_id', None)
            ))
        
        return invoice_responses
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list invoices: {str(e)}")


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    invoice_data: InvoiceData,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Get existing invoice
        invoice = await get_invoice_by_id(
            db=db,
            invoice_id=uuid.UUID(invoice_id),
            user_id=current_user.id
        )
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Update extracted data
        updated_data = {
            "invoice_data": {
                "invoice_number": invoice_data.invoice_number,
                "date": invoice_data.date,
                "vendor_name": invoice_data.vendor_name,
                "vendor_address": invoice_data.vendor_address,
                "customer_name": invoice_data.customer_name,
                "customer_address": invoice_data.customer_address,
                "line_items": invoice_data.line_items,
                "subtotal": invoice_data.subtotal,
                "tax": invoice_data.tax,
                "total": invoice_data.total
            },
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": str(current_user.id)
        }
        
        # Store updated data
        updated_invoice = await store_extracted_data(
            db=db,
            invoice_id=invoice.id,
            extracted_data=updated_data,
            user_id=current_user.id
        )
        
        return InvoiceResponse(
            id=str(updated_invoice.id),
            filename=updated_invoice.filename,
            status=updated_invoice.processing_status,
            created_at=updated_invoice.created_at,
            data=invoice_data
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update invoice: {str(e)}")


@router.put("/{invoice_id}/update-field", response_model=InvoiceResponse)
async def update_invoice_field(
    invoice_id: str,
    field_update: dict,  # {"field": "field_name", "value": "new_value"}
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a specific field in an invoice's extracted data"""
    try:
        # Get the invoice
        invoice = await get_invoice_by_id(
            db=db,
            invoice_id=uuid.UUID(invoice_id),
            user_id=current_user.id
        )
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get current extracted data
        extracted_data_dict = await get_extracted_data(
            db=db,
            invoice_id=invoice.id,
            user_id=current_user.id
        )
        
        if not extracted_data_dict:
            raise HTTPException(status_code=404, detail="No extracted data found")
        
        # Handle both old format (wrapped in "invoice_data") and new format (direct)
        if "invoice_data" in extracted_data_dict:
            invoice_data = extracted_data_dict["invoice_data"]
        else:
            invoice_data = extracted_data_dict
        
        # Update the specific field
        field_name = field_update.get("field")
        field_value = field_update.get("value")
        change_reason = field_update.get("reason", "user_correction")
        user_notes = field_update.get("notes")
        
        if not field_name:
            raise HTTPException(status_code=400, detail="Field name is required")
        
        # Get original value for audit trail
        original_value = None
        if "." in field_name:
            parent_field, child_field = field_name.split(".", 1)
            if parent_field in invoice_data and isinstance(invoice_data[parent_field], dict):
                original_value = invoice_data[parent_field].get(child_field)
        else:
            original_value = invoice_data.get(field_name)
        
        # Only update if value actually changed
        if str(original_value) != str(field_value):
            # Handle nested fields (e.g., "vendor.name", "customer.siret_number")
            if "." in field_name:
                parent_field, child_field = field_name.split(".", 1)
                if parent_field not in invoice_data:
                    invoice_data[parent_field] = {}
                if not isinstance(invoice_data[parent_field], dict):
                    invoice_data[parent_field] = {}
                invoice_data[parent_field][child_field] = field_value
                
                # Also update legacy fields for backward compatibility
                if parent_field == "vendor" and child_field == "name":
                    invoice_data["vendor_name"] = field_value
                elif parent_field == "customer" and child_field == "name":
                    invoice_data["customer_name"] = field_value
                elif parent_field == "vendor" and child_field == "address":
                    invoice_data["vendor_address"] = field_value
                elif parent_field == "customer" and child_field == "address":
                    invoice_data["customer_address"] = field_value
            else:
                invoice_data[field_name] = field_value
                
                # Handle legacy to nested field mapping
                if field_name == "vendor_name":
                    if "vendor" not in invoice_data:
                        invoice_data["vendor"] = {}
                    invoice_data["vendor"]["name"] = field_value
                elif field_name == "customer_name":
                    if "customer" not in invoice_data:
                        invoice_data["customer"] = {}
                    invoice_data["customer"]["name"] = field_value
                elif field_name == "vendor_address":
                    if "vendor" not in invoice_data:
                        invoice_data["vendor"] = {}
                    invoice_data["vendor"]["address"] = field_value
                elif field_name == "customer_address":
                    if "customer" not in invoice_data:
                        invoice_data["customer"] = {}
                    invoice_data["customer"]["address"] = field_value
            
            # Create audit trail record
            try:
                from models.review_models import create_field_edit_record
                from sqlalchemy import insert
                from models.review_models import InvoiceFieldEdit
                
                # Create field edit record
                edit_record = InvoiceFieldEdit(
                    invoice_id=invoice.id,
                    user_id=current_user.id,
                    field_name=field_name,
                    original_value=str(original_value) if original_value is not None else None,
                    new_value=str(field_value) if field_value is not None else None,
                    change_reason=change_reason,
                    user_notes=user_notes,
                    triggers_siret_revalidation=field_name in ["vendor.siret_number", "customer.siret_number", "vendor.siren_number", "customer.siren_number"],
                    triggers_tva_recalculation=field_name in ["total_tva", "subtotal_ht", "total_ttc", "tva_breakdown"]
                )
                
                db.add(edit_record)
                await db.commit()
                
                # Update invoice review status to IN_REVIEW if it was PENDING_REVIEW
                if invoice.review_status == "pending_review":
                    from sqlalchemy import update
                    from models.gdpr_models import Invoice as InvoiceModel
                    from datetime import datetime
                    
                    await db.execute(
                        update(InvoiceModel)
                        .where(InvoiceModel.id == invoice.id)
                        .values(
                            review_status="in_review",
                            review_started_at=datetime.utcnow(),
                            reviewed_by=current_user.id,
                            fields_modified_count=InvoiceModel.fields_modified_count + 1
                        )
                    )
                    await db.commit()
                
            except Exception as audit_error:
                print(f"Failed to create audit trail: {audit_error}")
                # Don't fail the whole operation if audit trail fails
        
        # Update the extracted data in database
        await store_extracted_data(
            db=db,
            invoice_id=invoice.id,
            extracted_data=invoice_data,  # Store the updated data directly
            user_id=current_user.id
        )
        
        # Re-run SIRET validation if SIREN/SIRET fields were updated
        if field_name in ["vendor.siren_number", "vendor.siret_number", "customer.siren_number", "customer.siret_number"]:
            try:
                from core.validation.siret_validation_service import SIRETValidationService
                siret_service = SIRETValidationService()
                
                # Re-validate vendor SIRET if updated
                if field_name.startswith("vendor.") and field_value:
                    vendor_name = invoice_data.get("vendor", {}).get("name") or invoice_data.get("vendor_name")
                    await siret_service.validate_siret_comprehensive(
                        siret=field_value,
                        extracted_company_name=vendor_name,
                        db_session=db,
                        invoice_id=str(invoice.id)
                    )
                
                # Re-validate customer SIRET if updated  
                elif field_name.startswith("customer.") and field_value:
                    customer_name = invoice_data.get("customer", {}).get("name") or invoice_data.get("customer_name")
                    await siret_service.validate_siret_comprehensive(
                        siret=field_value,
                        extracted_company_name=customer_name,
                        db_session=db,
                        invoice_id=str(invoice.id)
                    )
                    
            except Exception as validation_error:
                print(f"SIRET validation error after field update: {validation_error}")
        
        # Return updated invoice
        return await get_invoice(invoice_id, current_user, db)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update field: {str(e)}")


@router.put("/{invoice_id}/review-status", response_model=InvoiceResponse)
async def update_invoice_review_status(
    invoice_id: str,
    status_update: dict,  # {"status": "approved", "notes": "optional"}
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update the review status of an invoice"""
    try:
        from sqlalchemy import update
        from models.gdpr_models import Invoice as InvoiceModel, ReviewStatus
        from datetime import datetime
        
        # Validate status
        new_status = status_update.get("status")
        if new_status not in ["pending_review", "in_review", "reviewed", "approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Invalid review status")
        
        # Get the invoice to verify ownership
        invoice = await get_invoice_by_id(
            db=db,
            invoice_id=uuid.UUID(invoice_id),
            user_id=current_user.id
        )
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Update the review status
        update_values = {
            "review_status": new_status,
            "reviewed_by": current_user.id
        }
        
        if new_status == "approved":
            update_values["approved_at"] = datetime.utcnow()
            update_values["approved_by"] = current_user.id
        elif new_status == "reviewed":
            update_values["reviewed_at"] = datetime.utcnow()
        elif new_status == "in_review" and invoice.review_status == "pending_review":
            update_values["review_started_at"] = datetime.utcnow()
        
        await db.execute(
            update(InvoiceModel)
            .where(InvoiceModel.id == invoice.id)
            .values(**update_values)
        )
        await db.commit()
        
        # Return updated invoice
        return await get_invoice(invoice_id, current_user, db)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update review status: {str(e)}")


@router.delete("/{invoice_id}")
async def delete_invoice_endpoint(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Delete invoice from database
        deleted = await delete_invoice(
            db=db,
            invoice_id=uuid.UUID(invoice_id),
            user_id=current_user.id,
            deletion_reason="user_request"
        )
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # GDPR-COMPLIANT: No files to delete from storage since we don't store them
        # Files are processed in memory and discarded immediately
        print(f"✅ GDPR-compliant deletion: No files stored on disk for invoice {invoice_id}")
        
        return {"message": "Invoice deleted successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete invoice: {str(e)}")


# ==========================================
# BULK UPLOAD WITH DUPLICATE DETECTION
# ==========================================

@router.post("/upload/bulk", response_model=BulkUploadResponse)
async def upload_invoices_bulk(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    handle_duplicates: str = "warn",  # "warn", "skip", "replace"
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload multiple invoices with smart duplicate detection
    
    French business logic:
    - Auto-skip identical files (same content)
    - Warn about invoice number duplicates
    - Let user decide on edge cases
    """
    import uuid as uuid_lib
    from core.duplicate_detector import DuplicateDetector
    
    # Generate unique batch ID
    batch_id = str(uuid_lib.uuid4())
    
    try:
        # Initialize duplicate detector
        duplicate_detector = DuplicateDetector(db)
        
        # Validate files
        for file in files:
            if file.content_type not in settings.ALLOWED_FILE_TYPES:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Type de fichier non autorisé: {file.filename} ({file.content_type})"
                )
            
            # Read and validate file size
            contents = await file.read()
            if len(contents) > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"Fichier trop volumineux: {file.filename} ({len(contents)} bytes > {settings.MAX_FILE_SIZE})"
                )
            await file.seek(0)  # Reset file pointer
        
        # Perform batch duplicate analysis
        duplicate_report = await duplicate_detector.get_batch_duplicates(files, current_user.id)
        
        # Convert duplicate report to response format
        duplicates_detected = []
        for filename, result in duplicate_report.file_duplicates + duplicate_report.invoice_duplicates:
            duplicate_info = DuplicateInfo(
                filename=filename,
                is_duplicate=result.is_duplicate,
                duplicate_type=result.duplicate_type.value if result.duplicate_type else "unknown",
                severity=result.severity.value,
                existing_invoice_id=str(result.existing_invoice_id) if result.existing_invoice_id else None,
                existing_filename=result.existing_filename,
                existing_created_at=result.existing_created_at,
                french_message=result.french_message,
                recommended_action=result.recommended_action.value,
                metadata=result.metadata
            )
            duplicates_detected.append(duplicate_info)
        
        # Process files based on duplicate analysis and user preferences
        successful_uploads = []
        failed_uploads = []
        
        for file in files:
            filename = file.filename
            
            # Check if this file should be processed
            recommendation = duplicate_report.processing_recommendations.get(filename, "allow")
            
            if handle_duplicates == "skip" and recommendation == "skip":
                # Skip duplicates automatically
                failed_uploads.append({
                    "filename": filename,
                    "error": "Fichier ignoré - doublon détecté",
                    "reason": "duplicate_skipped"
                })
                continue
            
            if recommendation == "user_choice" and handle_duplicates == "warn":
                # Return to user for decision - don't process yet
                continue
            
            try:
                # Read file content
                contents = await file.read()
                await file.seek(0)
                
                # Create invoice in database
                db_invoice = await create_invoice(
                    db=db,
                    filename=filename,
                    file_content=contents,
                    mime_type=file.content_type,
                    data_controller_id=current_user.id,
                    processing_purposes=["invoice_processing", "business_operations"],
                    legal_basis="legitimate_interest",
                    processing_source="batch",
                    batch_id=batch_id
                )
                
                # GDPR-COMPLIANT: Process file in memory without permanent storage
                # No local file storage needed - process directly from memory
                
                # Create response
                invoice_response = InvoiceResponse(
                    id=str(db_invoice.id),
                    filename=db_invoice.filename,
                    status=db_invoice.processing_status,
                    created_at=db_invoice.created_at,
                    data=None,
                    review_status=getattr(db_invoice, 'review_status', None),
                    processing_source="batch",
                    batch_id=batch_id
                )
                
                successful_uploads.append(invoice_response)
                
                # Process invoice in background only if not waiting for user decision (GDPR-compliant)
                if recommendation != "user_choice":
                    background_tasks.add_task(
                        process_invoice_task_memory,
                        str(db_invoice.id),
                        contents,  # Pass file content directly
                        filename,
                        current_user.id
                    )
                
            except Exception as e:
                failed_uploads.append({
                    "filename": filename,
                    "error": f"Erreur de traitement: {str(e)}",
                    "reason": "processing_error"
                })
        
        # Create upload summary
        upload_summary = BatchUploadSummary(
            total_files=duplicate_report.total_files,
            unique_files=duplicate_report.unique_files,
            duplicate_count=duplicate_report.duplicate_count,
            requires_user_action=duplicate_report.requires_user_action,
            french_summary=duplicate_report.french_summary,
            processing_recommendations=duplicate_report.processing_recommendations
        )
        
        # Determine overall status
        if duplicate_report.requires_user_action and handle_duplicates == "warn":
            status_message = f"⚠️ {len(successful_uploads)} fichier(s) traité(s), {len(duplicates_detected)} doublon(s) nécessitent une action utilisateur."
            requires_resolution = True
        elif len(failed_uploads) > 0:
            status_message = f"✅ {len(successful_uploads)} fichier(s) traité(s), {len(failed_uploads)} échec(s)."
            requires_resolution = False
        else:
            status_message = f"✅ {len(successful_uploads)} fichier(s) traité(s) avec succès en lot."
            requires_resolution = False
        
        return BulkUploadResponse(
            batch_id=batch_id,
            upload_summary=upload_summary,
            duplicates_detected=duplicates_detected,
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads,
            requires_duplicate_resolution=requires_resolution,
            french_status_message=status_message
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'upload en lot: {str(e)}"
        )


@router.post("/check-duplicates")
async def check_duplicates_before_upload(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check for duplicates before upload without processing files
    
    Useful for frontend to show warnings before actual upload
    """
    try:
        from core.duplicate_detector import DuplicateDetector
        
        # Initialize duplicate detector
        duplicate_detector = DuplicateDetector(db)
        
        # Perform batch duplicate analysis
        duplicate_report = await duplicate_detector.get_batch_duplicates(files, current_user.id)
        
        # Convert to response format
        duplicates_detected = []
        for filename, result in duplicate_report.file_duplicates + duplicate_report.invoice_duplicates:
            duplicate_info = DuplicateInfo(
                filename=filename,
                is_duplicate=result.is_duplicate,
                duplicate_type=result.duplicate_type.value if result.duplicate_type else "unknown",
                severity=result.severity.value,
                existing_invoice_id=str(result.existing_invoice_id) if result.existing_invoice_id else None,
                existing_filename=result.existing_filename,
                existing_created_at=result.existing_created_at,
                french_message=result.french_message,
                recommended_action=result.recommended_action.value,
                metadata=result.metadata
            )
            duplicates_detected.append(duplicate_info)
        
        return {
            "total_files": duplicate_report.total_files,
            "unique_files": duplicate_report.unique_files,
            "duplicate_count": duplicate_report.duplicate_count,
            "requires_user_action": duplicate_report.requires_user_action,
            "french_summary": duplicate_report.french_summary,
            "duplicates_detected": duplicates_detected,
            "processing_recommendations": duplicate_report.processing_recommendations
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la vérification des doublons: {str(e)}"
        )


@router.post("/resolve-duplicates")
async def resolve_duplicate_conflicts(
    background_tasks: BackgroundTasks,
    batch_id: str,
    resolutions: List[DuplicateResolution],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Process user's duplicate resolution decisions
    
    Used when user has made decisions about duplicate handling
    """
    try:
        from core.duplicate_detector import DuplicateDetector, DuplicateType, DuplicateAction
        
        # Initialize duplicate detector
        duplicate_detector = DuplicateDetector(db)
        
        processed_files = []
        resolution_errors = []
        
        for resolution in resolutions:
            try:
                # Find the original uploaded files (would need to be stored temporarily)
                # For now, return success - full implementation would require file caching
                
                # Log the resolution decision
                await duplicate_detector.log_duplicate_resolution(
                    original_invoice_id=None,  # Would be populated with actual data
                    duplicate_file_hash="",  # Would be calculated from actual file
                    duplicate_invoice_key="",  # Would be extracted from invoice data
                    detection_type=DuplicateType.FILE_DUPLICATE,  # Would be actual type
                    user_action=DuplicateAction(resolution.action),
                    user_id=current_user.id,
                    metadata={
                        "batch_id": batch_id,
                        "user_reason": resolution.reason,
                        "user_notes": resolution.user_notes
                    }
                )
                
                processed_files.append(resolution.filename)
                
            except Exception as e:
                resolution_errors.append({
                    "filename": resolution.filename,
                    "error": f"Erreur de résolution: {str(e)}"
                })
        
        return {
            "batch_id": batch_id,
            "processed_files": processed_files,
            "resolution_errors": resolution_errors,
            "french_message": f"✅ {len(processed_files)} résolution(s) de doublons traitée(s), {len(resolution_errors)} erreur(s)."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la résolution des doublons: {str(e)}"
        )