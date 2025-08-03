from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid
from datetime import datetime
import os
import aiofiles
import tempfile
import shutil
from enum import Enum

from schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceData
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
# BatchExporter removed - no automatic export generation
from core.cost_tracker import track_processing_cost
from core.quota_manager import enforce_quota_limit
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/debug-test")
async def debug_test(request: Request):
    """Simple debug endpoint to test POST requests"""
    print(f"🔧 DEBUG TEST REQUEST RECEIVED:")
    print(f"  Method: {request.method}")
    print(f"  URL: {request.url}")
    print(f"  Headers: {dict(request.headers)}")
    
    body = await request.body()
    print(f"  Body length: {len(body)} bytes")
    print(f"  Body preview: {body[:100]}...")
    
    return JSONResponse(content={
        "message": "Debug test successful",
        "method": request.method,
        "content_length": len(body),
        "headers_count": len(request.headers)
    })






class ExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    SAGE = "sage"
    EBP = "ebp"
    CIEL = "ciel"
    FEC = "fec"


@router.post("/batch-process-debug")
async def batch_process_debug(request: Request):
    """Simplified batch process for debugging"""
    print(f"🔧 BATCH PROCESS DEBUG REQUEST:")
    print(f"  Method: {request.method}")
    print(f"  URL: {request.url}")
    print(f"  Origin: {request.headers.get('origin', 'Not set')}")
    print(f"  Auth: {request.headers.get('authorization', 'Not set')[:30]}...")
    print(f"  Content-Type: {request.headers.get('content-type', 'Not set')}")
    
    body = await request.body()
    print(f"  Body length: {len(body)} bytes")
    
    return JSONResponse(content={
        "message": "Batch process debug successful",
        "body_length": len(body)
    })

@router.post("/batch-process")
async def batch_process_invoices(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Batch process multiple invoice files for data extraction.
    Files are processed and sent to review queue - no export generation.
    """
    print(f"🚀 BATCH PROCESS REQUEST RECEIVED:")
    print(f"  👤 User: {current_user.email}")
    print(f"  📁 Files: {len(files)}")
    print(f"  🌐 Origin: {request.headers.get('origin', 'Not set')}")
    print(f"  🔑 Auth: {request.headers.get('authorization', 'Not set')[:30]}...")
    print(f"  📦 Content-Type: {request.headers.get('content-type', 'Not set')}")
    print(f"  🖥️  User-Agent: {request.headers.get('user-agent', 'Not set')}")
    for i, file in enumerate(files):
        print(f"    File {i+1}: {file.filename} ({file.content_type})")
    
    logger.info(f"Batch processing request from user {current_user.email} with {len(files)} files")
    
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # QUOTA ENFORCEMENT: Check if user can process this many files
    print(f"🔒 Checking quota before batch processing {len(files)} files...")
    for i in range(len(files)):
        try:
            quota_info = await enforce_quota_limit(db, current_user.id)
            print(f"✅ Quota check {i+1}/{len(files)} passed: {quota_info.get('current_usage', 0)}/{quota_info.get('monthly_limit', 0)}")
        except HTTPException as quota_error:
            print(f"❌ Quota enforcement blocked batch upload: {quota_error.detail}")
            raise HTTPException(
                status_code=402,
                detail=f"Quota dépassé après {i} fichiers traités. {quota_error.detail.get('message', 'Limite atteinte.')}"
            )
    
    if len(files) > 20:  # Reasonable limit
        raise HTTPException(status_code=400, detail="Too many files. Maximum 20 files per batch")
    
    # Validate all files before processing
    total_size = 0
    for file in files:
        if file.content_type not in settings.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type for {file.filename}: {file.content_type}"
            )
        
        # Read file to check size
        contents = await file.read()
        if len(contents) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File {file.filename} too large"
            )
        total_size += len(contents)
        
        # Reset file pointer
        await file.seek(0)
    
    if total_size > settings.MAX_FILE_SIZE * 10:  # 10x single file limit for batch
        raise HTTPException(status_code=400, detail="Total batch size too large")
    
    try:
        # Create batch processing session
        batch_id = str(uuid.uuid4())
        
        # Create temporary directory for this batch
        batch_temp_dir = os.path.join(tempfile.gettempdir(), f"batch_{batch_id}")
        os.makedirs(batch_temp_dir, exist_ok=True)
        
        # GDPR-COMPLIANT: Prepare file data for memory-only processing
        invoice_data_list = []
        
        for file in files:
            contents = await file.read()
            
            # Create invoice in database (mark as batch processing)
            db_invoice = await create_invoice(
                db=db,
                filename=file.filename,
                file_content=contents,
                mime_type=file.content_type,
                data_controller_id=current_user.id,
                processing_purposes=["batch_invoice_processing", "business_operations"],
                legal_basis="legitimate_interest",
                processing_source="batch",
                batch_id=batch_id
            )
            
            # GDPR-COMPLIANT: Keep file content in memory only
            invoice_data_list.append((str(db_invoice.id), contents, file.filename))
            
            # IMMEDIATE quota recording - no waiting for background tasks
            try:
                from core.quota_manager import QuotaManager
                from decimal import Decimal
                await QuotaManager.record_invoice_usage(
                    db=db,
                    user_id=current_user.id,
                    invoice_id=db_invoice.id,
                    cost_eur=Decimal("0.002")
                )
                print(f"✅ IMMEDIATE BATCH quota recorded for invoice {db_invoice.id}")
            except Exception as quota_error:
                print(f"❌ Failed to record batch quota for invoice {db_invoice.id}: {quota_error}")
        
        # Start batch processing in background
        background_tasks.add_task(
            process_batch_task,
            batch_id,
            invoice_data_list,
            current_user.id,
            batch_temp_dir
        )
        
        return JSONResponse(content={
            "batch_id": batch_id,
            "status": "processing",
            "invoice_count": len(invoice_data_list),
            "message": f"Processing {len(invoice_data_list)} invoices for review"
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start batch processing: {str(e)}"
        )


@router.get("/batch-status/{batch_id}")
async def get_batch_status(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get status of batch processing"""
    
    # Check if batch exists in temp storage or database
    batch_temp_dir = os.path.join(tempfile.gettempdir(), f"batch_{batch_id}")
    status_file = os.path.join(batch_temp_dir, "status.json")
    
    if not os.path.exists(status_file):
        raise HTTPException(status_code=404, detail="Batch not found")
    
    try:
        import json
        async with aiofiles.open(status_file, 'r') as f:
            status_data = json.loads(await f.read())
        
        return status_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get batch status: {str(e)}")


@router.get("/batch-download/{batch_id}")
async def download_batch_export(
    batch_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download the processed batch export file"""
    
    batch_temp_dir = os.path.join(tempfile.gettempdir(), f"batch_{batch_id}")
    export_file = None
    
    # Find the export file
    if os.path.exists(batch_temp_dir):
        for file in os.listdir(batch_temp_dir):
            if file.startswith("export_"):
                export_file = os.path.join(batch_temp_dir, file)
                break
    
    if not export_file or not os.path.exists(export_file):
        raise HTTPException(status_code=404, detail="Export file not found or not ready")
    
    from fastapi.responses import FileResponse
    
    # Get file extension for content type
    file_ext = export_file.split('.')[-1].lower()
    content_types = {
        'csv': 'text/csv',
        'json': 'application/json',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'pnm': 'text/plain',
        'txt': 'text/plain'
    }
    
    content_type = content_types.get(file_ext, 'application/octet-stream')
    
    return FileResponse(
        export_file,
        media_type=content_type,
        filename=os.path.basename(export_file),
        headers={"Content-Disposition": f"attachment; filename={os.path.basename(export_file)}"}
    )


async def process_batch_task(
    batch_id: str,
    invoice_data_list: List[tuple],  # (invoice_id, file_content, filename)
    user_id: uuid.UUID,
    batch_temp_dir: str
):
    """Background task to process batch of invoices"""
    from core.database import async_session_maker
    import json
    
    async with async_session_maker() as db:
        try:
            # Update status file
            status_data = {
                "batch_id": batch_id,
                "status": "processing",
                "total_invoices": len(invoice_data_list),
                "processed_invoices": 0,
                "failed_invoices": 0,
                "started_at": datetime.utcnow().isoformat()
            }
            
            status_file = os.path.join(batch_temp_dir, "status.json")
            async with aiofiles.open(status_file, 'w') as f:
                await f.write(json.dumps(status_data))
            
            # Process each invoice
            processed_data = []
            groq_processor = GroqProcessor()
            
            for i, (invoice_id, file_content, filename) in enumerate(invoice_data_list):
                try:
                    # Update status
                    status_data["processed_invoices"] = i
                    async with aiofiles.open(status_file, 'w') as f:
                        await f.write(json.dumps(status_data))
                    
                    # Update invoice status to processing
                    await update_invoice_status(
                        db=db,
                        invoice_id=uuid.UUID(invoice_id),
                        status="processing",
                        user_id=user_id,
                        processing_started_at=datetime.utcnow()
                    )
                    
                    # GDPR-COMPLIANT: Process file content directly from memory
                    
                    # Extract text and images
                    extracted_text, base64_images = await PDFProcessor.process_uploaded_file(
                        file_content, filename
                    )
                    
                    # Process with Groq
                    if extracted_text:
                        invoice_data = await groq_processor.process_invoice_text(
                            extracted_text,
                            invoice_id=uuid.UUID(invoice_id),
                            user_id=user_id,
                            db=db
                        )
                    else:
                        invoice_data = await groq_processor.process_invoice_images(
                            base64_images,
                            invoice_id=uuid.UUID(invoice_id),
                            user_id=user_id,
                            db=db
                        )
                    
                    # Store processed data for export
                    processed_data.append({
                        "invoice_id": invoice_id,
                        "filename": filename,
                        "data": invoice_data
                    })
                    
                    # Update invoice status to completed
                    await update_invoice_status(
                        db=db,
                        invoice_id=uuid.UUID(invoice_id),
                        status="completed",
                        user_id=user_id,
                        processing_completed_at=datetime.utcnow()
                    )
                    
                except Exception as e:
                    # Mark invoice as failed
                    status_data["failed_invoices"] += 1
                    try:
                        await update_invoice_status(
                            db=db,
                            invoice_id=uuid.UUID(invoice_id),
                            status="failed",
                            user_id=user_id,
                            processing_completed_at=datetime.utcnow(),
                            error_message=str(e)
                        )
                    except:
                        pass
            
            # No export generation - invoices go to review queue
            if processed_data:
                # Set all processed invoices to pending review status
                for invoice_data in processed_data:
                    try:
                        # Update review status directly via SQL
                        from sqlalchemy import text
                        await db.execute(
                            text("UPDATE invoices SET review_status = 'pending_review' WHERE id = :invoice_id"),
                            {"invoice_id": invoice_data["invoice_id"]}
                        )
                    except Exception as e:
                        print(f"Failed to set review status for invoice {invoice_data['invoice_id']}: {e}")
                
                # Commit the review status updates
                await db.commit()
                
                # Update final status - no export file generated
                status_data.update({
                    "status": "completed",
                    "processed_invoices": len(processed_data),
                    "completed_at": datetime.utcnow().isoformat(),
                    "message": f"Processed {len(processed_data)} invoices. Ready for review."
                })
            else:
                status_data.update({
                    "status": "failed",
                    "error": "No invoices processed successfully"
                })
            
            # Save final status
            async with aiofiles.open(status_file, 'w') as f:
                await f.write(json.dumps(status_data))
            
            # Keep invoices for user review instead of deleting them
            # These invoices will appear in "Factures en Attente de Révision"
            
        except Exception as e:
            # Update status with error
            status_data.update({
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat()
            })
            
            async with aiofiles.open(status_file, 'w') as f:
                await f.write(json.dumps(status_data))


@router.delete("/batch-cleanup/{batch_id}")
async def cleanup_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user)
):
    """Clean up batch temporary files"""
    
    batch_temp_dir = os.path.join(tempfile.gettempdir(), f"batch_{batch_id}")
    
    try:
        if os.path.exists(batch_temp_dir):
            shutil.rmtree(batch_temp_dir)
        return {"message": "Batch cleaned up successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup batch: {str(e)}")