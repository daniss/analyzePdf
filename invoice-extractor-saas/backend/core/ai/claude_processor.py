import json
import uuid
from typing import Dict, Any, List, Optional
from anthropic import AsyncAnthropic
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from core.config import settings
from schemas.invoice import InvoiceData, LineItem
from core.gdpr_transfer_compliance import gdpr_transfer_compliance, TransferContext
from core.gdpr_audit import gdpr_audit
from core.gdpr_encryption import transit_encryption
from crud.invoice import store_extracted_data, update_invoice_status
from crud.data_subject import create_data_subject, link_invoice_to_data_subject
from core.gdpr_helpers import log_audit_event
from models.gdpr_models import AuditEventType, DataSubjectType, ProcessingPurpose, DataCategory


class ClaudeProcessor:
    """Handles invoice processing using Claude 4 Opus vision capabilities"""
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        
    async def process_invoice_images(
        self, 
        base64_images: List[str], 
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> InvoiceData:
        """
        Process invoice images using Claude 4 Opus vision API with GDPR compliance.
        Extracts structured data from the invoice and stores in database.
        
        Args:
            base64_images: List of base64 encoded images
            invoice_id: ID of the invoice to process
            user_id: ID of user making request for audit trail
            db: Database session for compliance logging and data storage
        
        Returns:
            InvoiceData: Extracted invoice data
        """
        
        # Update invoice status to processing
        await update_invoice_status(
            db=db,
            invoice_id=invoice_id,
            status="processing",
            user_id=user_id,
            processing_started_at=datetime.utcnow()
        )
        
        # Create transfer context for GDPR compliance
        transfer_context = TransferContext(
            transfer_id=str(uuid.uuid4()),
            purpose="invoice_data_extraction",
            data_categories=["identifying_data", "contact_data", "financial_data", "business_data"],
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
            # Log transfer assessment failure
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Transfer risk assessment failed: {str(e)}",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="claude_processor",
                risk_level="high"
            )
            raise
        
        # Log the transfer initiation
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description="Invoice data transfer to Claude API initiated",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="claude_processor",
            legal_basis="legitimate_interest",
            processing_purpose="invoice_data_extraction",
            data_categories_accessed=transfer_context.data_categories,
            risk_level="medium",
            operation_details={
                "transfer_id": transfer_context.transfer_id,
                "recipient_country": transfer_context.recipient_country,
                "recipient_organization": transfer_context.recipient_organization,
                "images_count": len(base64_images)
            }
        )
        
        # Build the message content with all images
        content = []
        
        # Add instruction text
        content.append({
            "type": "text",
            "text": self._get_extraction_prompt()
        })
        
        # Add all images
        for idx, img_base64 in enumerate(base64_images):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_base64
                }
            })
            
            if idx < len(base64_images) - 1:
                content.append({
                    "type": "text",
                    "text": f"Page {idx + 1} of the invoice shown above. Continue to the next page."
                })
        
        try:
            # Call Claude 4 Opus API
            response = await self.client.messages.create(
                model=settings.AI_MODEL,
                max_tokens=settings.MAX_TOKENS,
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
            
            # Validate the extraction
            validation_results = await self.validate_extraction(extracted_data)
            
            # Store extracted data in database with encryption
            extracted_data_dict = extracted_data.dict()
            extracted_data_dict["validation_results"] = validation_results
            
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
                event_description=f"Invoice data successfully extracted and stored",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="claude_processor",
                legal_basis="legitimate_interest",
                processing_purpose="invoice_data_extraction",
                data_categories_accessed=["business_data", "financial_data", "identifying_data", "contact_data"],
                risk_level="low",
                operation_details={
                    "confidence_score": validation_results.get("confidence_score", 0),
                    "validation_errors": len(validation_results.get("errors", [])),
                    "validation_warnings": len(validation_results.get("warnings", [])),
                    "line_items_count": len(extracted_data.line_items) if extracted_data.line_items else 0,
                    "total_amount": extracted_data.total,
                    "currency": extracted_data.currency
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
                event_description=f"Invoice processing failed: {str(e)}",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="claude_processor",
                risk_level="high",
                operation_details={"error": str(e)}
            )
            
            raise Exception(f"Claude API error: {str(e)}")
    
    def _get_extraction_prompt(self) -> str:
        """Get the prompt for invoice data extraction"""
        return """You are an expert invoice data extractor. Please analyze the invoice image(s) and extract all relevant information.

Extract the following fields from the invoice:
1. Invoice number
2. Invoice date
3. Due date (if present)
4. Vendor/Seller information (name, address, phone, email, tax ID)
5. Customer/Buyer information (name, address, phone, email)
6. Line items (description, quantity, unit price, total)
7. Subtotal
8. Tax amount and rate
9. Total amount
10. Currency
11. Payment terms
12. Any notes or special instructions

Return the data in the following JSON format:
{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD or null",
    "vendor_name": "string",
    "vendor_address": "string",
    "vendor_phone": "string or null",
    "vendor_email": "string or null",
    "vendor_tax_id": "string or null",
    "customer_name": "string",
    "customer_address": "string",
    "customer_phone": "string or null",
    "customer_email": "string or null",
    "line_items": [
        {
            "description": "string",
            "quantity": number,
            "unit_price": number,
            "total": number
        }
    ],
    "subtotal": number,
    "tax_rate": number or null,
    "tax": number,
    "total": number,
    "currency": "string",
    "payment_terms": "string or null",
    "notes": "string or null"
}

Important instructions:
- Extract monetary values as numbers (not strings)
- If a field is not present in the invoice, use null
- For dates, convert to YYYY-MM-DD format
- Be precise with line items - extract each one separately
- Verify that subtotal + tax = total
- If the invoice spans multiple pages, combine all information

Analyze the invoice carefully and provide accurate extraction."""
    
    def _parse_claude_response(self, response_text: str) -> InvoiceData:
        """Parse Claude's response into InvoiceData schema"""
        try:
            # Extract JSON from the response
            # Claude might include explanation text, so we need to find the JSON
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
            else:
                # If no JSON found, try to parse the entire response
                data = json.loads(response_text)
            
            # Convert to InvoiceData schema
            line_items = []
            for item in data.get('line_items', []):
                line_items.append(LineItem(
                    description=item['description'],
                    quantity=float(item['quantity']),
                    unit_price=float(item['unit_price']),
                    total=float(item['total'])
                ))
            
            invoice_data = InvoiceData(
                invoice_number=data.get('invoice_number'),
                date=data.get('date'),
                vendor_name=data.get('vendor_name'),
                vendor_address=data.get('vendor_address'),
                customer_name=data.get('customer_name'),
                customer_address=data.get('customer_address'),
                line_items=line_items,
                subtotal=float(data.get('subtotal', 0)) if data.get('subtotal') else None,
                tax=float(data.get('tax', 0)) if data.get('tax') else None,
                total=float(data.get('total', 0)) if data.get('total') else None,
                currency=data.get('currency', 'USD')
            )
            
            return invoice_data
            
        except Exception as e:
            raise Exception(f"Failed to parse Claude response: {str(e)}\nResponse: {response_text}")
    
    async def validate_extraction(self, invoice_data: InvoiceData) -> Dict[str, Any]:
        """
        Validate the extracted data for consistency and completeness.
        Returns validation results and confidence scores.
        """
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "confidence_score": 0.0
        }
        
        # Check required fields
        if not invoice_data.invoice_number:
            validation_results["warnings"].append("Invoice number is missing")
        
        if not invoice_data.date:
            validation_results["errors"].append("Invoice date is missing")
            validation_results["is_valid"] = False
        
        if not invoice_data.total:
            validation_results["errors"].append("Total amount is missing")
            validation_results["is_valid"] = False
        
        # Validate line items total matches subtotal
        if invoice_data.line_items and invoice_data.subtotal:
            calculated_subtotal = sum(item.total for item in invoice_data.line_items)
            if abs(calculated_subtotal - invoice_data.subtotal) > 0.01:
                validation_results["warnings"].append(
                    f"Line items total ({calculated_subtotal}) doesn't match subtotal ({invoice_data.subtotal})"
                )
        
        # Validate total calculation
        if invoice_data.subtotal and invoice_data.tax is not None and invoice_data.total:
            calculated_total = invoice_data.subtotal + invoice_data.tax
            if abs(calculated_total - invoice_data.total) > 0.01:
                validation_results["warnings"].append(
                    f"Calculated total ({calculated_total}) doesn't match invoice total ({invoice_data.total})"
                )
        
        # Calculate confidence score
        field_count = 0
        filled_count = 0
        
        for field_name, field_value in invoice_data.dict().items():
            if field_name != 'line_items':
                field_count += 1
                if field_value is not None:
                    filled_count += 1
        
        validation_results["confidence_score"] = (filled_count / field_count) * 100 if field_count > 0 else 0
        
        return validation_results
    
    async def _create_data_subjects_from_extraction(
        self,
        db: AsyncSession,
        invoice_id: uuid.UUID,
        extracted_data: InvoiceData,
        user_id: uuid.UUID
    ) -> None:
        """Create data subjects from extracted invoice data with GDPR compliance"""
        try:
            data_subjects_created = []
            
            # Create vendor data subject if we have enough information
            if extracted_data.vendor_name:
                vendor_data_subject = await create_data_subject(
                    db=db,
                    name=extracted_data.vendor_name,
                    email=getattr(extracted_data, 'vendor_email', None),
                    phone=getattr(extracted_data, 'vendor_phone', None),
                    address=getattr(extracted_data, 'vendor_address', None),
                    data_subject_type=DataSubjectType.BUSINESS_CONTACT,
                    processing_purposes=[ProcessingPurpose.LEGITIMATE_INTEREST, ProcessingPurpose.LEGAL_OBLIGATION],
                    data_categories=[DataCategory.IDENTIFYING_DATA, DataCategory.CONTACT_DATA, DataCategory.BUSINESS_DATA],
                    legal_basis="legitimate_interest",
                    created_by=user_id,
                    consent_given=False  # Business processing, no explicit consent needed
                )
                
                # Link to invoice
                await link_invoice_to_data_subject(
                    db=db,
                    invoice_id=invoice_id,
                    data_subject_id=vendor_data_subject.id,
                    role_in_invoice="vendor",
                    user_id=user_id
                )
                
                data_subjects_created.append(("vendor", vendor_data_subject.id))
            
            # Create customer data subject if we have enough information
            if extracted_data.customer_name:
                customer_data_subject = await create_data_subject(
                    db=db,
                    name=extracted_data.customer_name,
                    email=getattr(extracted_data, 'customer_email', None),
                    phone=getattr(extracted_data, 'customer_phone', None),
                    address=getattr(extracted_data, 'customer_address', None),
                    data_subject_type=DataSubjectType.BUSINESS_CONTACT,
                    processing_purposes=[ProcessingPurpose.LEGITIMATE_INTEREST, ProcessingPurpose.LEGAL_OBLIGATION],
                    data_categories=[DataCategory.IDENTIFYING_DATA, DataCategory.CONTACT_DATA, DataCategory.BUSINESS_DATA],
                    legal_basis="legitimate_interest",
                    created_by=user_id,
                    consent_given=False  # Business processing, no explicit consent needed
                )
                
                # Link to invoice
                await link_invoice_to_data_subject(
                    db=db,
                    invoice_id=invoice_id,
                    data_subject_id=customer_data_subject.id,
                    role_in_invoice="customer",
                    user_id=user_id
                )
                
                data_subjects_created.append(("customer", customer_data_subject.id))
            
            # Log data subject creation
            if data_subjects_created:
                await log_audit_event(
                    db=db,
                    event_type=AuditEventType.DATA_MODIFICATION,
                    event_description=f"Data subjects created from invoice: {', '.join([f'{role}({id})' for role, id in data_subjects_created])}",
                    user_id=user_id,
                    invoice_id=invoice_id,
                    system_component="claude_processor",
                    legal_basis="legitimate_interest",
                    processing_purpose="data_subject_creation",
                    data_categories_accessed=[DataCategory.IDENTIFYING_DATA.value, DataCategory.CONTACT_DATA.value, DataCategory.BUSINESS_DATA.value],
                    risk_level="medium",
                    operation_details={
                        "data_subjects_created": len(data_subjects_created),
                        "roles": [role for role, _ in data_subjects_created]
                    }
                )
                
        except Exception as e:
            # Log the failure but don't fail the entire process
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"Failed to create data subjects from extraction: {str(e)}",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="claude_processor",
                risk_level="medium",
                operation_details={"error": str(e)}
            )
            # Don't raise the exception - data subject creation is optional