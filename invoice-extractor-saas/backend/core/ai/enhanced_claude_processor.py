import json
import uuid
from typing import Dict, Any, List, Optional
from anthropic import AsyncAnthropic
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from core.config import settings
from schemas.invoice import InvoiceData, LineItem
from core.gdpr_transfer_compliance import gdpr_transfer_compliance, TransferContext
from core.gdpr_audit import gdpr_audit
from core.gdpr_encryption import transit_encryption
from crud.invoice import store_extracted_data, update_invoice_status
from crud.data_subject import create_data_subject
from core.gdpr_helpers import log_audit_event
from models.gdpr_models import AuditEventType, DataSubjectType, ProcessingPurpose, DataCategory
from core.ai.claude_processor import ClaudeProcessor

logger = logging.getLogger(__name__)


class EnhancedClaudeProcessor(ClaudeProcessor):
    """Enhanced Claude processor that works with pre-processed invoice data"""
    
    def __init__(self):
        super().__init__()
        self.logger = logger
    
    async def process_invoice(
        self, 
        enhanced_data: Dict[str, Any], 
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> InvoiceData:
        """
        Main entry point for enhanced invoice processing.
        Delegates to process_enhanced_invoice_data for consistency.
        """
        return await self.process_enhanced_invoice_data(enhanced_data, invoice_id, user_id, db)
    
    async def process_enhanced_invoice_data(
        self, 
        enhanced_data: Dict[str, Any], 
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> InvoiceData:
        """
        Process pre-extracted invoice data using Claude 4 Opus with optimized token usage.
        
        Args:
            enhanced_data: Pre-processed data from EnhancedPDFProcessor
            invoice_id: ID of the invoice to process
            user_id: ID of user making request for audit trail
            db: Database session for compliance logging and data storage
        
        Returns:
            InvoiceData: Extracted and validated invoice data
        """
        
        # Update invoice status to processing
        await update_invoice_status(
            db=db,
            invoice_id=invoice_id,
            status="processing",
            user_id=user_id,
            processing_started_at=datetime.utcnow()
        )
        
        # Log processing method
        self.logger.info(f"Processing invoice {invoice_id} using {enhanced_data['extraction_method']} method")
        
        # Check if we have enough pre-extracted data to skip Claude entirely
        if self._can_skip_claude_processing(enhanced_data):
            self.logger.info("Sufficient data pre-extracted, skipping Claude API call")
            try:
                # Build InvoiceData from pre-extracted fields
                invoice_data = await self._build_from_pre_extracted(enhanced_data)
                
                # Store extracted data
                await store_extracted_data(
                    db=db,
                    invoice_id=invoice_id,
                    extracted_data=invoice_data.dict(),
                    user_id=user_id
                )
                
                # Log successful extraction
                await log_audit_event(
                    db=db,
                    event_type=AuditEventType.DATA_MODIFICATION,
                    event_description="Invoice data extracted using local processing only",
                    user_id=user_id,
                    invoice_id=invoice_id,
                    system_component="enhanced_claude_processor",
                    risk_level="low",
                    operation_details={
                        "method": "pre_extraction_only",
                        "confidence": "high"
                    }
                )
                
                return invoice_data
                
            except Exception as e:
                self.logger.warning(f"Failed to build from pre-extracted data: {str(e)}, falling back to Claude")
        
        # Check if Claude API key is available when we need to use Claude
        if not self.api_key_available:
            await update_invoice_status(
                db=db,
                invoice_id=invoice_id,
                status="failed",
                user_id=user_id
            )
            raise Exception(
                "Claude API key not configured and local processing insufficient. "
                "Please set ANTHROPIC_API_KEY environment variable for AI-powered invoice processing."
            )
        
        # Create transfer context for GDPR compliance (reduced data categories)
        transfer_context = TransferContext(
            transfer_id=str(uuid.uuid4()),
            purpose="invoice_data_extraction",
            data_categories=self._determine_data_categories(enhanced_data),
            data_subjects_count=2,  # Typically vendor and customer
            recipient_country="US",
            recipient_organization="Anthropic PBC",
            legal_basis="legitimate_interest",
            urgency_level="normal",
            retention_period_days=1  # Claude doesn't retain data
        )
        
        # Conduct transfer risk assessment
        try:
            assessment_result = await gdpr_transfer_compliance.assess_transfer_risk(
                transfer_context, db
            )
            
            if not assessment_result["is_approved"]:
                await update_invoice_status(
                    db=db,
                    invoice_id=invoice_id,
                    status="failed",
                    user_id=user_id
                )
                raise Exception(f"Transfer not approved due to high risk: {assessment_result['risk_level']}")
        except Exception as e:
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Transfer risk assessment failed: {str(e)}",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="enhanced_claude_processor",
                risk_level="high"
            )
            raise
        
        # Log the transfer initiation
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description="Enhanced invoice data transfer to Claude API initiated",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="enhanced_claude_processor",
            legal_basis="legitimate_interest",
            processing_purpose="invoice_data_extraction",
            data_categories_accessed=transfer_context.data_categories,
            risk_level="medium",
            operation_details={
                "transfer_id": transfer_context.transfer_id,
                "extraction_method": enhanced_data["extraction_method"],
                "pre_extracted_fields": len(enhanced_data.get("pre_extracted_fields", {})),
                "has_images": "images" in enhanced_data
            }
        )
        
        # Build optimized message content
        content = []
        
        # Add instruction text with pre-extracted context
        content.append({
            "type": "text",
            "text": self._get_enhanced_extraction_prompt(enhanced_data)
        })
        
        # Add images only if OCR was used
        if "images" in enhanced_data:
            for idx, img_base64 in enumerate(enhanced_data["images"]):
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_base64
                    }
                })
                
                if idx < len(enhanced_data["images"]) - 1:
                    content.append({
                        "type": "text",
                        "text": f"Page {idx + 1} of the invoice shown above. Continue to the next page."
                    })
        
        try:
            # Estimate tokens before calling
            estimated_tokens = self._estimate_enhanced_tokens(enhanced_data)
            self.logger.info(f"Estimated tokens for Claude API: {estimated_tokens}")
            
            # Call Claude 4 Opus API with reduced token usage
            response = await self.client.messages.create(
                model=settings.AI_MODEL,
                max_tokens=min(settings.MAX_TOKENS, estimated_tokens * 2),  # Dynamic max tokens
                temperature=0.1,  # Low temperature for consistent extraction
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            )
            
            # Parse the response
            extracted_data = self._parse_claude_response(response.content[0].text)
            
            # Merge with pre-extracted data
            extracted_data = self._merge_with_pre_extracted(extracted_data, enhanced_data)
            
            # Validate the extraction
            validation_results = await self.validate_extraction(extracted_data)
            
            # Store extracted data in database with encryption
            extracted_data_dict = extracted_data.dict()
            extracted_data_dict["validation_results"] = validation_results
            extracted_data_dict["extraction_metadata"] = {
                "method": enhanced_data["extraction_method"],
                "processing_time": enhanced_data.get("processing_time_seconds", 0),
                "pre_extraction_used": True,
                "estimated_tokens": estimated_tokens
            }
            
            await store_extracted_data(
                db=db,
                invoice_id=invoice_id,
                extracted_data=extracted_data_dict,
                user_id=user_id
            )
            
            # Create data subjects if we have enough information
            await self._create_data_subjects_from_extraction(
                db=db,
                invoice_id=invoice_id,
                extracted_data=extracted_data,
                user_id=user_id
            )
            
            # Log successful extraction
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description="Invoice data successfully extracted with enhanced processing",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="enhanced_claude_processor",
                legal_basis="legitimate_interest",
                processing_purpose="invoice_data_extraction",
                data_categories_accessed=["business_data", "financial_data", "identifying_data", "contact_data"],
                risk_level="low",
                operation_details={
                    "extraction_method": enhanced_data["extraction_method"],
                    "confidence_score": validation_results.get("confidence_score", 0),
                    "validation_errors": len(validation_results.get("errors", [])),
                    "validation_warnings": len(validation_results.get("warnings", [])),
                    "line_items_count": len(extracted_data.line_items) if extracted_data.line_items else 0,
                    "total_amount": extracted_data.total,
                    "currency": extracted_data.currency,
                    "estimated_tokens": estimated_tokens
                }
            )
            
            return extracted_data
            
        except Exception as e:
            # Update invoice status to failed
            await update_invoice_status(
                db=db,
                invoice_id=invoice_id,
                status="failed",
                user_id=user_id
            )
            
            # Log the failure
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"Enhanced invoice processing failed: {str(e)}",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="enhanced_claude_processor",
                risk_level="high",
                operation_details={"error": str(e)}
            )
            
            raise Exception(f"Claude API error: {str(e)}")
    
    def _get_enhanced_extraction_prompt(self, enhanced_data: Dict[str, Any]) -> str:
        """Generate optimized prompt based on pre-extracted data"""
        
        # Start with context about pre-extraction
        prompt = f"""You are an expert French invoice data validator and extractor. 
I've already pre-processed this invoice using {'text extraction' if enhanced_data['extraction_method'] == 'native_text' else 'OCR'}.

PRE-EXTRACTED INFORMATION:
"""
        
        # Add pre-extracted fields
        if enhanced_data.get("pre_extracted_fields"):
            prompt += "\nFields already identified:\n"
            for field, value in enhanced_data["pre_extracted_fields"].items():
                prompt += f"- {field}: {value}\n"
        
        # Add detected line items
        if enhanced_data.get("line_items_detected"):
            prompt += f"\nLine items detected: {len(enhanced_data['line_items_detected'])}\n"
            for idx, item in enumerate(enhanced_data["line_items_detected"][:3]):  # Show first 3
                prompt += f"  Item {idx+1}: {item.get('description', 'N/A')} - {item.get('total', 'N/A')}€\n"
        
        # Add the text content if native extraction
        if enhanced_data["extraction_method"] == "native_text" and "text_content" in enhanced_data:
            prompt += f"\nFULL TEXT CONTENT:\n{enhanced_data['text_content'][:2000]}...\n"  # Limit text
        
        # Add validation request
        prompt += """
YOUR TASK:
1. VALIDATE the pre-extracted information above
2. FILL IN any missing required fields
3. CORRECT any errors in the pre-extracted data
4. ENSURE French invoice compliance

Focus especially on:
- Validating SIREN/SIRET numbers (must be 9/14 digits)
- Ensuring TVA calculations are correct
- Checking that all mandatory French fields are present
- Verifying line items match totals

Return the complete invoice data in the same JSON format as before, incorporating and correcting the pre-extracted information.

CRITICAL: If pre-extracted values look correct, USE THEM. Only modify if they're clearly wrong.
"""
        
        return prompt
    
    def _can_skip_claude_processing(self, enhanced_data: Dict[str, Any]) -> bool:
        """Check if we have enough pre-extracted data to skip Claude API"""
        # TEMPORARILY DISABLED: Always require Claude API key for proper validation
        # This prevents fake data from local processing when Claude API is not available
        
        # First check if Claude API is available
        if not self.api_key_available:
            return False  # Cannot skip if no API key - must show proper error
        
        required_fields = [
            "invoice_number", "date", "amount_ttc", "amount_ht", "amount_tva"
        ]
        
        pre_extracted = enhanced_data.get("pre_extracted_fields", {})
        
        # Check if all required fields are present
        has_required = all(field in pre_extracted for field in required_fields)
        
        # Check if we have line items
        has_line_items = len(enhanced_data.get("line_items_detected", [])) > 0
        
        # Check extraction confidence
        high_confidence = enhanced_data.get("extraction_confidence") == "high"
        
        return has_required and has_line_items and high_confidence
    
    async def _build_from_pre_extracted(self, enhanced_data: Dict[str, Any]) -> InvoiceData:
        """Build InvoiceData from pre-extracted fields only"""
        from schemas.invoice import FrenchBusinessInfo, FrenchTVABreakdown
        
        fields = enhanced_data["pre_extracted_fields"]
        
        # Parse amounts
        def parse_amount(value: str) -> float:
            if not value:
                return 0.0
            # Remove spaces and replace comma with dot
            clean_value = value.replace(" ", "").replace(",", ".")
            # Remove currency symbols
            clean_value = clean_value.replace("€", "").strip()
            return float(clean_value)
        
        # Build vendor info
        vendor_info = FrenchBusinessInfo(
            name=fields.get("vendor_name", ""),
            address=fields.get("vendor_address", ""),
            siren_number=fields.get("siren"),
            siret_number=fields.get("siret"),
            tva_number=fields.get("tva_number")
        )
        
        # Build line items from detected items
        line_items = []
        for item in enhanced_data.get("line_items_detected", []):
            line_items.append(LineItem(
                description=item.get("description", ""),
                quantity=item.get("quantity", 1),
                unit_price=item.get("unit_price", 0),
                total=item.get("total", 0),
                tva_rate=item.get("tva_rate")
            ))
        
        # Calculate TVA breakdown
        tva_breakdown = []
        if fields.get("amount_tva"):
            # Simple 20% TVA assumption if not specified
            tva_breakdown.append(FrenchTVABreakdown(
                rate=20.0,
                taxable_amount=parse_amount(fields.get("amount_ht", "0")),
                tva_amount=parse_amount(fields.get("amount_tva", "0"))
            ))
        
        # Create InvoiceData
        return InvoiceData(
            invoice_number=fields.get("invoice_number"),
            date=fields.get("date"),
            vendor=vendor_info,
            vendor_name=vendor_info.name,
            vendor_address=vendor_info.address,
            line_items=line_items,
            subtotal_ht=parse_amount(fields.get("amount_ht", "0")),
            total_tva=parse_amount(fields.get("amount_tva", "0")),
            total_ttc=parse_amount(fields.get("amount_ttc", "0")),
            tva_breakdown=tva_breakdown,
            currency="EUR"
        )
    
    def _merge_with_pre_extracted(self, claude_data: InvoiceData, enhanced_data: Dict[str, Any]) -> InvoiceData:
        """Merge Claude's extraction with pre-extracted data"""
        pre_extracted = enhanced_data.get("pre_extracted_fields", {})
        
        # If Claude didn't find something but we pre-extracted it, use pre-extracted
        if not claude_data.invoice_number and pre_extracted.get("invoice_number"):
            claude_data.invoice_number = pre_extracted["invoice_number"]
        
        if not claude_data.date and pre_extracted.get("date"):
            claude_data.date = pre_extracted["date"]
        
        # For vendor info
        if claude_data.vendor:
            if not claude_data.vendor.siren_number and pre_extracted.get("siren"):
                claude_data.vendor.siren_number = pre_extracted["siren"]
            if not claude_data.vendor.siret_number and pre_extracted.get("siret"):
                claude_data.vendor.siret_number = pre_extracted["siret"]
            if not claude_data.vendor.tva_number and pre_extracted.get("tva_number"):
                claude_data.vendor.tva_number = pre_extracted["tva_number"]
        
        return claude_data
    
    def _determine_data_categories(self, enhanced_data: Dict[str, Any]) -> List[str]:
        """Determine data categories based on extraction method"""
        if enhanced_data["extraction_method"] == "native_text":
            # Less sensitive - just text
            return ["business_data", "financial_data"]
        else:
            # OCR includes images
            return ["business_data", "financial_data", "identifying_data", "contact_data"]
    
    def _estimate_enhanced_tokens(self, enhanced_data: Dict[str, Any]) -> int:
        """Estimate tokens for enhanced processing"""
        tokens = 300  # Base prompt
        
        # Add tokens for pre-extracted fields
        tokens += len(json.dumps(enhanced_data.get("pre_extracted_fields", {}))) // 4
        
        # Add tokens for text content
        if "text_content" in enhanced_data:
            tokens += min(len(enhanced_data["text_content"]) // 4, 1000)  # Cap at 1000
        
        # Add tokens for images
        if "images" in enhanced_data:
            tokens += len(enhanced_data["images"]) * 1000
        
        return tokens