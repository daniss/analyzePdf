"""
Progressive Invoice Processing API
Implements three-tier processing with WebSocket support for real-time updates
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid
import os
import aiofiles
import json
import logging

from schemas.invoice import InvoiceResponse
from api.auth import get_current_user
from models.user import User
from core.config import settings
from core.database import get_db
from core.processors.orchestrator import ProcessingOrchestrator, ProcessingTier, ProcessingStatus
from crud.invoice import create_invoice, get_invoice_by_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Global orchestrator instance
orchestrator = ProcessingOrchestrator()


@router.post("/upload-progressive", response_model=InvoiceResponse)
async def upload_invoice_progressive(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    max_tier: Optional[str] = Query("tier3", description="Maximum processing tier: tier1, tier2, or tier3"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload invoice for progressive processing
    
    - **tier1**: Local extraction only (fastest, no API calls)
    - **tier2**: Local + AI validation (moderate speed, minimal API calls)
    - **tier3**: Full AI extraction (slowest, full API usage)
    """
    # Validate file type
    if file.content_type not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # Parse max tier
    tier_map = {
        "tier1": ProcessingTier.TIER1_LOCAL,
        "tier2": ProcessingTier.TIER2_AI_VALIDATION,
        "tier3": ProcessingTier.TIER3_FULL_AI
    }
    
    max_processing_tier = tier_map.get(max_tier, ProcessingTier.TIER3_FULL_AI)
    
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
            status="processing",
            created_at=db_invoice.created_at,
            data=None
        )
        
        # Process invoice in background with progressive pipeline
        background_tasks.add_task(
            process_invoice_progressive,
            str(db_invoice.id),
            file_path,
            current_user.id,
            max_processing_tier
        )
        
        return invoice_response
        
    except Exception as e:
        logger.error(f"Error uploading invoice: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload invoice: {str(e)}"
        )


async def process_invoice_progressive(
    invoice_id: str, 
    file_path: str, 
    user_id: uuid.UUID,
    max_tier: ProcessingTier
):
    """Background task for progressive invoice processing"""
    from core.database import async_session_maker
    
    async with async_session_maker() as db:
        try:
            result = await orchestrator.process_invoice(
                invoice_id=invoice_id,
                file_path=file_path,
                db=db,
                user_id=user_id,
                max_tier=max_tier
            )
            
            if result.success:
                logger.info(f"Invoice {invoice_id} processed successfully through tiers: {result.processing_tiers}")
            else:
                logger.error(f"Invoice {invoice_id} processing failed: {result.errors}")
                
        except Exception as e:
            logger.error(f"Error in progressive processing: {str(e)}")


@router.websocket("/ws/{invoice_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time processing updates"""
    await websocket.accept()
    
    try:
        # Verify invoice belongs to user
        invoice = await get_invoice_by_id(
            db=db,
            invoice_id=uuid.UUID(invoice_id),
            user_id=current_user.id
        )
        
        if not invoice:
            await websocket.send_json({
                "type": "error",
                "message": "Invoice not found"
            })
            await websocket.close()
            return
        
        # Register connection with orchestrator
        orchestrator.active_connections[invoice_id] = websocket
        
        # Send initial status
        await websocket.send_json({
            "type": "connection_established",
            "invoice_id": invoice_id,
            "current_status": invoice.processing_status
        })
        
        # Keep connection alive
        while True:
            try:
                # Wait for messages (ping/pong or commands)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message.get("type") == "request_status":
                    # Send current processing status
                    invoice = await get_invoice_by_id(db, uuid.UUID(invoice_id), current_user.id)
                    await websocket.send_json({
                        "type": "status_update",
                        "status": invoice.processing_status if invoice else "unknown"
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
                break
                
    finally:
        # Clean up connection
        if invoice_id in orchestrator.active_connections:
            del orchestrator.active_connections[invoice_id]


@router.post("/{invoice_id}/upgrade-tier")
async def upgrade_processing_tier(
    invoice_id: str,
    target_tier: str = Query(..., description="Target tier: tier2 or tier3"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Request higher tier processing for an invoice
    Useful when initial processing didn't extract all required fields
    """
    # Validate target tier
    tier_map = {
        "tier2": ProcessingTier.TIER2_AI_VALIDATION,
        "tier3": ProcessingTier.TIER3_FULL_AI
    }
    
    if target_tier not in tier_map:
        raise HTTPException(status_code=400, detail="Invalid target tier")
    
    target_processing_tier = tier_map[target_tier]
    
    try:
        # Get invoice
        invoice = await get_invoice_by_id(
            db=db,
            invoice_id=uuid.UUID(invoice_id),
            user_id=current_user.id
        )
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if invoice.processing_status == "processing":
            raise HTTPException(status_code=400, detail="Invoice is already being processed")
        
        # Request higher tier processing
        result = await orchestrator.request_higher_tier(
            invoice_id=invoice_id,
            target_tier=target_processing_tier,
            db=db,
            user_id=current_user.id
        )
        
        return {
            "message": f"Invoice upgraded to {target_tier} processing",
            "processing_tiers": [tier.value for tier in result.processing_tiers],
            "success": result.success
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error upgrading tier: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upgrade tier: {str(e)}")


@router.get("/{invoice_id}/processing-details")
async def get_processing_details(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed processing information including tier results"""
    try:
        # Get invoice
        invoice = await get_invoice_by_id(
            db=db,
            invoice_id=uuid.UUID(invoice_id),
            user_id=current_user.id
        )
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get extracted data
        from crud.invoice import get_extracted_data
        extracted_data = await get_extracted_data(
            db=db,
            invoice_id=invoice.id,
            user_id=current_user.id
        )
        
        if not extracted_data:
            return {
                "invoice_id": invoice_id,
                "status": invoice.processing_status,
                "message": "No processing data available yet"
            }
        
        # Extract tier results
        tier_results = extracted_data.get("tier_results", {})
        processing_metadata = extracted_data.get("processing_metadata", {})
        
        return {
            "invoice_id": invoice_id,
            "status": invoice.processing_status,
            "processing_tiers": processing_metadata.get("processing_tiers", []),
            "extraction_method": processing_metadata.get("extraction_method", "unknown"),
            "total_processing_time": processing_metadata.get("total_processing_time", 0),
            "token_usage": processing_metadata.get("token_usage", {}),
            "confidence_scores": processing_metadata.get("confidence_scores", {}),
            "tier_details": {
                "tier1": tier_results.get("tier1", {}) if "tier1" in tier_results else None,
                "tier2": tier_results.get("tier2", {}) if "tier2" in tier_results else None,
                "tier3": {
                    "processed": "tier3" in tier_results,
                    "token_estimate": tier_results.get("tier3", {}).get("token_estimate", 0)
                } if "tier3" in tier_results else None
            }
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID format")
    except Exception as e:
        logger.error(f"Error getting processing details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing details: {str(e)}")