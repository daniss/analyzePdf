from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks
from typing import List
import uuid
from datetime import datetime
import os
import aiofiles

from schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceData
from api.auth import get_current_user
from core.config import settings
from core.pdf_processor import PDFProcessor
from core.ai.claude_processor import ClaudeProcessor

router = APIRouter()


@router.post("/upload", response_model=InvoiceResponse)
async def upload_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    # Validate file type
    if file.content_type not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # Read file content
    contents = await file.read()
    
    # Validate file size
    if len(contents) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Generate unique ID
    invoice_id = str(uuid.uuid4())
    
    # Create upload directory if it doesn't exist
    os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
    
    # Save file locally
    file_path = os.path.join(settings.LOCAL_STORAGE_PATH, f"{invoice_id}_{file.filename}")
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(contents)
    
    # Create initial response
    invoice_response = InvoiceResponse(
        id=invoice_id,
        filename=file.filename,
        status="processing",
        created_at=datetime.utcnow(),
        data=None
    )
    
    # Process invoice in background
    background_tasks.add_task(
        process_invoice_task,
        invoice_id,
        file_path,
        file.filename
    )
    
    return invoice_response


async def process_invoice_task(invoice_id: str, file_path: str, filename: str):
    """Background task to process invoice using Claude 4"""
    try:
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
        
        # TODO: Update invoice in database with extracted data
        # For now, we'll just log the results
        print(f"Invoice {invoice_id} processed successfully")
        print(f"Extracted data: {invoice_data}")
        print(f"Validation: {validation_results}")
        
    except Exception as e:
        print(f"Error processing invoice {invoice_id}: {str(e)}")
        # TODO: Update invoice status to 'failed' in database


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user)
):
    # TODO: Get invoice from database
    # Mock response for now
    return InvoiceResponse(
        id=invoice_id,
        filename="invoice.pdf",
        status="completed",
        created_at=datetime.utcnow(),
        data=InvoiceData(
            invoice_number="INV-001",
            date="2024-01-01",
            vendor_name="Acme Corp",
            vendor_address="123 Main St",
            customer_name="Customer Inc",
            customer_address="456 Oak Ave",
            line_items=[],
            subtotal=1000.00,
            tax=100.00,
            total=1100.00
        )
    )


@router.get("/", response_model=List[InvoiceResponse])
async def list_invoices(
    skip: int = 0,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    # TODO: Get invoices from database
    return []


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    invoice_data: InvoiceData,
    current_user: dict = Depends(get_current_user)
):
    # TODO: Update invoice in database
    return InvoiceResponse(
        id=invoice_id,
        filename="invoice.pdf",
        status="completed",
        created_at=datetime.utcnow(),
        data=invoice_data
    )


@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user)
):
    # TODO: Delete invoice from database and storage
    # Delete file from storage
    try:
        files = os.listdir(settings.LOCAL_STORAGE_PATH)
        for file in files:
            if file.startswith(invoice_id):
                os.remove(os.path.join(settings.LOCAL_STORAGE_PATH, file))
    except Exception as e:
        print(f"Error deleting file: {str(e)}")
    
    return {"message": "Invoice deleted"}