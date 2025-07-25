from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
from datetime import datetime
import os
import aiofiles

from schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceData
from api.auth import get_current_user
from models.user import User
from core.config import settings
from core.database import get_db
from core.pdf_processor import PDFProcessor
from core.ai.claude_processor import ClaudeProcessor
from crud.invoice import (
    create_invoice, get_invoice_by_id, get_user_invoices, 
    update_invoice_status, store_extracted_data, delete_invoice,
    get_extracted_data
)

router = APIRouter()


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
        
        # Create upload directory if it doesn't exist
        os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
        
        # Save file locally
        file_path = os.path.join(settings.LOCAL_STORAGE_PATH, f"{db_invoice.id}_{file.filename}")
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(contents)
        
        # Create response
        invoice_response = InvoiceResponse(
            id=str(db_invoice.id),
            filename=db_invoice.filename,
            status=db_invoice.processing_status,
            created_at=db_invoice.created_at,
            data=None
        )
        
        # Process invoice in background
        background_tasks.add_task(
            process_invoice_task,
            str(db_invoice.id),
            file_path,
            file.filename,
            current_user.id
        )
        
        return invoice_response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload invoice: {str(e)}"
        )


async def process_invoice_task(invoice_id: str, file_path: str, filename: str, user_id: uuid.UUID):
    """Background task to process invoice using Claude 4"""
    from core.database import async_session_maker
    
    async with async_session_maker() as db:
        try:
            # Update status to processing
            await update_invoice_status(
                db=db,
                invoice_id=uuid.UUID(invoice_id),
                status="processing",
                user_id=user_id,
                processing_started_at=datetime.utcnow()
            )
            
            # Read file content
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()
            
            # Convert to images
            base64_images = await PDFProcessor.process_uploaded_file(file_content, filename)
            
            # Process with Claude 4
            claude_processor = ClaudeProcessor()
            invoice_data = await claude_processor.process_invoice_images(base64_images)
            
            # Validate extraction
            validation_results = await claude_processor.validate_extraction(invoice_data)
            
            # Store extracted data in database
            await store_extracted_data(
                db=db,
                invoice_id=uuid.UUID(invoice_id),
                extracted_data={
                    "invoice_data": invoice_data,
                    "validation_results": validation_results,
                    "processing_metadata": {
                        "processed_at": datetime.utcnow().isoformat(),
                        "image_count": len(base64_images) if base64_images else 0,
                        "processor": "claude-3-opus-20240229"
                    }
                },
                user_id=user_id
            )
            
            print(f"Invoice {invoice_id} processed successfully")
            
        except Exception as e:
            print(f"Error processing invoice {invoice_id}: {str(e)}")
            # Update invoice status to failed
            try:
                await update_invoice_status(
                    db=db,
                    invoice_id=uuid.UUID(invoice_id),
                    status="failed",
                    user_id=user_id,
                    processing_completed_at=datetime.utcnow()
                )
            except Exception as update_error:
                print(f"Failed to update invoice status: {str(update_error)}")


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
            if extracted_data_dict and "invoice_data" in extracted_data_dict:
                invoice_data = extracted_data_dict["invoice_data"]
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
                    total=invoice_data.get("total", 0.0)
                )
        
        return InvoiceResponse(
            id=str(invoice.id),
            filename=invoice.filename,
            status=invoice.processing_status,
            created_at=invoice.created_at,
            data=extracted_data
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
            invoice_responses.append(InvoiceResponse(
                id=str(invoice.id),
                filename=invoice.filename,
                status=invoice.processing_status,
                created_at=invoice.created_at,
                data=None  # Don't include full data in list view
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
        
        # Delete file from storage
        try:
            files = os.listdir(settings.LOCAL_STORAGE_PATH)
            for file in files:
                if file.startswith(invoice_id):
                    os.remove(os.path.join(settings.LOCAL_STORAGE_PATH, file))
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
        
        return {"message": "Invoice deleted successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete invoice: {str(e)}")