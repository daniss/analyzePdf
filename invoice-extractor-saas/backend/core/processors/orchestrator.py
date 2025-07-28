"""
Processing Orchestrator
Manages the three-tier progressive PDF processing pipeline
Handles tier routing, result merging, and WebSocket updates
"""

import asyncio
import json
import logging
from typing import Dict, Optional, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from core.processors.tier1_processor import Tier1Processor, Tier1Result
from core.processors.tier2_processor import Tier2Processor, Tier2Result
from core.ai.claude_processor import ClaudeProcessor
from core.pdf_processor import PDFProcessor
from crud.invoice import update_invoice_status, store_extracted_data
from schemas.invoice import InvoiceData

logger = logging.getLogger(__name__)


class ProcessingTier(Enum):
    """Processing tier levels"""
    TIER1_LOCAL = "tier1_local"
    TIER2_AI_VALIDATION = "tier2_ai_validation"
    TIER3_FULL_AI = "tier3_full_ai"


class ProcessingStatus(Enum):
    """Processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some tiers completed


@dataclass
class ProcessingProgress:
    """Processing progress information"""
    invoice_id: str
    current_tier: ProcessingTier
    status: ProcessingStatus
    progress_percentage: int
    message: str
    tier_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OrchestratorResult:
    """Final result from orchestrator"""
    invoice_data: Optional[InvoiceData] = None
    processing_tiers: List[ProcessingTier] = field(default_factory=list)
    tier_results: Dict[str, Any] = field(default_factory=dict)
    total_processing_time: float = 0.0
    total_token_usage: Dict[str, int] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    extraction_method: str = "progressive"
    success: bool = True
    errors: List[str] = field(default_factory=list)


class ProcessingOrchestrator:
    """Orchestrates the three-tier progressive processing pipeline"""
    
    # Confidence thresholds for tier progression
    TIER1_SUCCESS_THRESHOLD = 0.85  # Overall confidence needed to skip Tier 2
    TIER2_SUCCESS_THRESHOLD = 0.90  # Overall confidence needed to skip Tier 3
    
    # Required fields for a valid invoice
    REQUIRED_FIELDS = ["invoice_number", "total_ttc", "vendor_name"]
    
    def __init__(self):
        self.tier1_processor = Tier1Processor()
        self.tier2_processor = Tier2Processor()
        self.claude_processor = ClaudeProcessor()
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def process_invoice(
        self,
        invoice_id: str,
        file_path: str,
        db: AsyncSession,
        user_id: uuid.UUID,
        websocket: Optional[WebSocket] = None,
        force_tier: Optional[ProcessingTier] = None,
        max_tier: ProcessingTier = ProcessingTier.TIER3_FULL_AI
    ) -> OrchestratorResult:
        """
        Process invoice through progressive tiers
        
        Args:
            invoice_id: Invoice UUID
            file_path: Path to PDF file
            db: Database session
            user_id: User UUID
            websocket: Optional WebSocket for real-time updates
            force_tier: Force processing to start at specific tier
            max_tier: Maximum tier to process (for cost control)
        """
        start_time = datetime.now()
        result = OrchestratorResult()
        
        try:
            # Register WebSocket if provided
            if websocket:
                self.active_connections[invoice_id] = websocket
            
            # Update invoice status
            await update_invoice_status(
                db=db,
                invoice_id=uuid.UUID(invoice_id),
                status="processing",
                user_id=user_id,
                processing_started_at=datetime.utcnow()
            )
            
            # Start with Tier 1 unless forced otherwise
            if not force_tier or force_tier == ProcessingTier.TIER1_LOCAL:
                await self._process_tier1(invoice_id, file_path, db, user_id, result)
                
                # Check if we need to proceed to Tier 2
                if self._should_proceed_to_tier2(result) and max_tier.value >= ProcessingTier.TIER2_AI_VALIDATION.value:
                    await self._process_tier2(invoice_id, file_path, db, user_id, result)
                    
                    # Check if we need to proceed to Tier 3
                    if self._should_proceed_to_tier3(result) and max_tier == ProcessingTier.TIER3_FULL_AI:
                        await self._process_tier3(invoice_id, file_path, db, user_id, result)
            
            elif force_tier == ProcessingTier.TIER2_AI_VALIDATION:
                # Run Tier 1 first to get base extraction
                await self._process_tier1(invoice_id, file_path, db, user_id, result)
                await self._process_tier2(invoice_id, file_path, db, user_id, result)
                
                if self._should_proceed_to_tier3(result) and max_tier == ProcessingTier.TIER3_FULL_AI:
                    await self._process_tier3(invoice_id, file_path, db, user_id, result)
            
            elif force_tier == ProcessingTier.TIER3_FULL_AI:
                # Skip to Tier 3 directly
                await self._process_tier3(invoice_id, file_path, db, user_id, result)
            
            # Convert to InvoiceData format
            if result.success:
                result.invoice_data = self._convert_to_invoice_data(result)
                
                # Store in database
                await self._store_results(invoice_id, db, user_id, result)
                
                # Send completion update
                await self._send_progress_update(
                    invoice_id,
                    ProcessingProgress(
                        invoice_id=invoice_id,
                        current_tier=result.processing_tiers[-1] if result.processing_tiers else ProcessingTier.TIER1_LOCAL,
                        status=ProcessingStatus.COMPLETED,
                        progress_percentage=100,
                        message="Processing completed successfully",
                        tier_results=result.tier_results
                    )
                )
            
            result.total_processing_time = (datetime.now() - start_time).total_seconds()
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {str(e)}")
            result.success = False
            result.errors.append(str(e))
            
            # Update invoice status to failed
            await update_invoice_status(
                db=db,
                invoice_id=uuid.UUID(invoice_id),
                status="failed",
                user_id=user_id,
                processing_completed_at=datetime.utcnow()
            )
            
            # Send error update
            await self._send_progress_update(
                invoice_id,
                ProcessingProgress(
                    invoice_id=invoice_id,
                    current_tier=result.processing_tiers[-1] if result.processing_tiers else ProcessingTier.TIER1_LOCAL,
                    status=ProcessingStatus.FAILED,
                    progress_percentage=0,
                    message=f"Processing failed: {str(e)}",
                    errors=[str(e)]
                )
            )
        
        finally:
            # Clean up WebSocket
            if invoice_id in self.active_connections:
                del self.active_connections[invoice_id]
        
        return result
    
    async def _process_tier1(self, invoice_id: str, file_path: str, 
                           db: AsyncSession, user_id: uuid.UUID, 
                           result: OrchestratorResult):
        """Process with Tier 1 (local extraction)"""
        await self._send_progress_update(
            invoice_id,
            ProcessingProgress(
                invoice_id=invoice_id,
                current_tier=ProcessingTier.TIER1_LOCAL,
                status=ProcessingStatus.PROCESSING,
                progress_percentage=10,
                message="Starting local text extraction..."
            )
        )
        
        try:
            tier1_result = await self.tier1_processor.process_pdf(file_path)
            
            result.processing_tiers.append(ProcessingTier.TIER1_LOCAL)
            result.tier_results["tier1"] = {
                "fields": {k: asdict(v) for k, v in tier1_result.fields.items()},
                "confidence": tier1_result.confidence_summary,
                "processing_time": tier1_result.processing_time,
                "page_count": tier1_result.page_count
            }
            
            # Update confidence scores
            result.confidence_scores.update(tier1_result.confidence_summary)
            
            await self._send_progress_update(
                invoice_id,
                ProcessingProgress(
                    invoice_id=invoice_id,
                    current_tier=ProcessingTier.TIER1_LOCAL,
                    status=ProcessingStatus.COMPLETED,
                    progress_percentage=30,
                    message=f"Local extraction completed. Confidence: {tier1_result.confidence_summary.get('overall', 0):.2%}"
                )
            )
            
        except Exception as e:
            logger.error(f"Tier 1 processing failed: {str(e)}")
            result.errors.append(f"Tier 1 error: {str(e)}")
            raise
    
    async def _process_tier2(self, invoice_id: str, file_path: str,
                           db: AsyncSession, user_id: uuid.UUID,
                           result: OrchestratorResult):
        """Process with Tier 2 (AI validation)"""
        await self._send_progress_update(
            invoice_id,
            ProcessingProgress(
                invoice_id=invoice_id,
                current_tier=ProcessingTier.TIER2_AI_VALIDATION,
                status=ProcessingStatus.PROCESSING,
                progress_percentage=40,
                message="Validating uncertain fields with AI..."
            )
        )
        
        try:
            # Get Tier 1 result
            tier1_data = result.tier_results.get("tier1", {})
            tier1_result = Tier1Result()
            
            # Reconstruct Tier1Result from stored data
            from core.processors.tier1_processor import ExtractedField
            for field_name, field_data in tier1_data.get("fields", {}).items():
                tier1_result.fields[field_name] = ExtractedField(**field_data)
            
            tier1_result.confidence_summary = tier1_data.get("confidence", {})
            
            # Process with Tier 2
            tier2_result = await self.tier2_processor.process(
                tier1_result, 
                invoice_id=invoice_id,
                user_id=str(user_id),
                db=db
            )
            
            result.processing_tiers.append(ProcessingTier.TIER2_AI_VALIDATION)
            result.tier_results["tier2"] = {
                "validated_fields": {k: asdict(v) for k, v in tier2_result.validated_fields.items()},
                "corrections": tier2_result.corrections_made,
                "token_usage": tier2_result.token_usage,
                "processing_time": tier2_result.processing_time,
                "confidence_improvement": tier2_result.confidence_improvement
            }
            
            # Update token usage
            for key, value in tier2_result.token_usage.items():
                result.total_token_usage[key] = result.total_token_usage.get(key, 0) + value
            
            # Update confidence scores
            for field_name, field in tier2_result.validated_fields.items():
                result.confidence_scores[field_name] = field.confidence
            
            # Recalculate overall confidence
            if tier2_result.validated_fields:
                overall_confidence = sum(f.confidence for f in tier2_result.validated_fields.values()) / len(tier2_result.validated_fields)
                result.confidence_scores["overall"] = overall_confidence
            
            await self._send_progress_update(
                invoice_id,
                ProcessingProgress(
                    invoice_id=invoice_id,
                    current_tier=ProcessingTier.TIER2_AI_VALIDATION,
                    status=ProcessingStatus.COMPLETED,
                    progress_percentage=60,
                    message=f"AI validation completed. Confidence improved by {tier2_result.confidence_improvement:.2%}"
                )
            )
            
        except Exception as e:
            logger.error(f"Tier 2 processing failed: {str(e)}")
            result.errors.append(f"Tier 2 error: {str(e)}")
            # Don't raise - we can still use Tier 1 results
    
    async def _process_tier3(self, invoice_id: str, file_path: str,
                           db: AsyncSession, user_id: uuid.UUID,
                           result: OrchestratorResult):
        """Process with Tier 3 (full AI extraction)"""
        await self._send_progress_update(
            invoice_id,
            ProcessingProgress(
                invoice_id=invoice_id,
                current_tier=ProcessingTier.TIER3_FULL_AI,
                status=ProcessingStatus.PROCESSING,
                progress_percentage=70,
                message="Processing with full AI extraction..."
            )
        )
        
        try:
            # Read file and convert to images
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            base64_images = await PDFProcessor.process_uploaded_file(
                file_content, 
                file_path.split('/')[-1]
            )
            
            # Process with Claude
            invoice_data = await self.claude_processor.process_invoice_images(
                base64_images,
                invoice_id=invoice_id,
                user_id=str(user_id),
                db=db
            )
            
            result.processing_tiers.append(ProcessingTier.TIER3_FULL_AI)
            result.tier_results["tier3"] = {
                "invoice_data": invoice_data,
                "image_count": len(base64_images) if base64_images else 0,
                "processing_time": (datetime.now() - datetime.now()).total_seconds()  # TODO: Track actual time
            }
            
            # Estimate token usage for Tier 3
            estimated_tokens = len(base64_images) * 1000 if base64_images else 0
            result.total_token_usage["tier3_estimated"] = estimated_tokens
            
            # Set high confidence for AI results
            result.confidence_scores["overall"] = 0.95
            
            await self._send_progress_update(
                invoice_id,
                ProcessingProgress(
                    invoice_id=invoice_id,
                    current_tier=ProcessingTier.TIER3_FULL_AI,
                    status=ProcessingStatus.COMPLETED,
                    progress_percentage=90,
                    message="Full AI extraction completed"
                )
            )
            
        except Exception as e:
            logger.error(f"Tier 3 processing failed: {str(e)}")
            result.errors.append(f"Tier 3 error: {str(e)}")
            raise
    
    def _should_proceed_to_tier2(self, result: OrchestratorResult) -> bool:
        """Determine if we should proceed to Tier 2"""
        overall_confidence = result.confidence_scores.get("overall", 0)
        
        # Check if overall confidence is below threshold
        if overall_confidence < self.TIER1_SUCCESS_THRESHOLD:
            return True
        
        # Check if any required fields are missing
        tier1_fields = result.tier_results.get("tier1", {}).get("fields", {})
        for required_field in self.REQUIRED_FIELDS:
            if required_field not in tier1_fields:
                return True
        
        return False
    
    def _should_proceed_to_tier3(self, result: OrchestratorResult) -> bool:
        """Determine if we should proceed to Tier 3"""
        overall_confidence = result.confidence_scores.get("overall", 0)
        
        # Check if overall confidence is still below threshold
        if overall_confidence < self.TIER2_SUCCESS_THRESHOLD:
            return True
        
        # Check if critical fields are still missing
        fields = {}
        if "tier2" in result.tier_results:
            fields = result.tier_results["tier2"].get("validated_fields", {})
        elif "tier1" in result.tier_results:
            fields = result.tier_results["tier1"].get("fields", {})
        
        for required_field in self.REQUIRED_FIELDS:
            if required_field not in fields:
                return True
        
        return False
    
    def _convert_to_invoice_data(self, result: OrchestratorResult) -> InvoiceData:
        """Convert tier results to InvoiceData format"""
        # Get the best available data (prefer higher tiers)
        fields = {}
        
        if "tier3" in result.tier_results:
            # Use Tier 3 data directly
            return result.tier_results["tier3"]["invoice_data"]
        
        elif "tier2" in result.tier_results:
            # Use Tier 2 validated fields
            tier2_fields = result.tier_results["tier2"]["validated_fields"]
            for field_name, field_data in tier2_fields.items():
                fields[field_name] = field_data["value"]
        
        elif "tier1" in result.tier_results:
            # Use Tier 1 fields
            tier1_fields = result.tier_results["tier1"]["fields"]
            for field_name, field_data in tier1_fields.items():
                fields[field_name] = field_data["value"]
        
        # Convert to InvoiceData
        from schemas.invoice import FrenchBusinessInfo
        
        invoice_data = InvoiceData(
            invoice_number=fields.get("invoice_number"),
            date=fields.get("invoice_date"),
            due_date=fields.get("due_date"),
            vendor_name=fields.get("vendor_name"),
            customer_name=fields.get("customer_name"),
            subtotal_ht=fields.get("total_ht"),
            total_tva=fields.get("total_tva"),
            total_ttc=fields.get("total_ttc"),
            currency="EUR"
        )
        
        # Add French business info if available
        if fields.get("siren") or fields.get("siret") or fields.get("tva_number"):
            invoice_data.vendor = FrenchBusinessInfo(
                name=fields.get("vendor_name", ""),
                address="",  # TODO: Extract address
                siren_number=fields.get("siren"),
                siret_number=fields.get("siret"),
                tva_number=fields.get("tva_number")
            )
        
        return invoice_data
    
    async def _store_results(self, invoice_id: str, db: AsyncSession, 
                           user_id: uuid.UUID, result: OrchestratorResult):
        """Store processing results in database"""
        extracted_data = {
            "invoice_data": result.invoice_data.dict() if result.invoice_data else None,
            "processing_metadata": {
                "processed_at": datetime.utcnow().isoformat(),
                "extraction_method": result.extraction_method,
                "processing_tiers": [tier.value for tier in result.processing_tiers],
                "total_processing_time": result.total_processing_time,
                "token_usage": result.total_token_usage,
                "confidence_scores": result.confidence_scores
            },
            "tier_results": result.tier_results
        }
        
        await store_extracted_data(
            db=db,
            invoice_id=uuid.UUID(invoice_id),
            extracted_data=extracted_data,
            user_id=user_id
        )
        
        # Update invoice status
        await update_invoice_status(
            db=db,
            invoice_id=uuid.UUID(invoice_id),
            status="completed" if result.success else "partial",
            user_id=user_id,
            processing_completed_at=datetime.utcnow()
        )
    
    async def _send_progress_update(self, invoice_id: str, progress: ProcessingProgress):
        """Send progress update via WebSocket if connected"""
        if invoice_id in self.active_connections:
            try:
                websocket = self.active_connections[invoice_id]
                await websocket.send_json({
                    "type": "progress_update",
                    "data": {
                        "invoice_id": progress.invoice_id,
                        "tier": progress.current_tier.value,
                        "status": progress.status.value,
                        "progress": progress.progress_percentage,
                        "message": progress.message,
                        "timestamp": progress.timestamp.isoformat()
                    }
                })
            except Exception as e:
                logger.error(f"Error sending WebSocket update: {str(e)}")
                # Remove dead connection
                del self.active_connections[invoice_id]
    
    async def request_higher_tier(self, invoice_id: str, target_tier: ProcessingTier,
                                db: AsyncSession, user_id: uuid.UUID) -> OrchestratorResult:
        """Request processing at a higher tier"""
        # Get invoice file path
        from crud.invoice import get_invoice_by_id
        invoice = await get_invoice_by_id(db, uuid.UUID(invoice_id), user_id)
        
        if not invoice:
            raise ValueError("Invoice not found")
        
        # GDPR-COMPLIANT: Files are processed in memory, no file path needed
        # This orchestrator method may need refactoring to support memory-based processing
        
        # TODO: Update orchestrator to use memory-based processing
        # For now, raise exception to indicate this method needs updating
        raise NotImplementedError(
            "GDPR Compliance: This orchestrator method needs to be updated for memory-based processing. "
            "Files are no longer stored on disk."
        )
            db=db,
            user_id=user_id,
            force_tier=target_tier
        )