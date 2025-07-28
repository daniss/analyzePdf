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
from crud.data_subject import create_data_subject
from core.gdpr_helpers import log_audit_event
from models.gdpr_models import AuditEventType, DataSubjectType, ProcessingPurpose, DataCategory


class ClaudeProcessor:
    """Handles invoice processing using Claude 4 Opus vision capabilities"""
    
    def __init__(self):
        api_key = settings.ANTHROPIC_API_KEY
        api_key_valid = (
            api_key and 
            api_key.strip() and 
            api_key != "your-claude-api-key-here" and
            not api_key.startswith("your-") and
            api_key.startswith("sk-ant-")  # Claude API keys start with sk-ant-
        )
        
        if not api_key_valid:
            self.client = None
            self.api_key_available = False
        else:
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.api_key_available = True
        
    async def process_invoice_text(
        self,
        extracted_text: str,
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession
    ) -> InvoiceData:
        """
        Process invoice text using Claude 4 text API (cheaper than vision).
        Used when clean text can be extracted from PDF.
        
        Args:
            extracted_text: Clean text extracted from PDF
            invoice_id: ID of the invoice to process
            user_id: ID of user making request for audit trail
            db: Database session for compliance logging and data storage
        
        Returns:
            InvoiceData: Extracted invoice data
        """
        
        # Check if Claude API key is available
        if not self.api_key_available:
            await update_invoice_status(
                db=db,
                invoice_id=invoice_id,
                status="failed",
                user_id=user_id
            )
            raise Exception(
                "Claude API key not configured. Please set ANTHROPIC_API_KEY environment variable. "
                "Without this key, AI-powered invoice processing is not available."
            )
        
        # Update invoice status to processing
        await update_invoice_status(
            db=db,
            invoice_id=invoice_id,
            status="processing",
            user_id=user_id,
            processing_started_at=datetime.utcnow()
        )
        
        # Create transfer context for GDPR compliance (text processing)
        transfer_context = TransferContext(
            transfer_id=str(uuid.uuid4()),
            purpose="invoice_text_extraction",
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
            event_description="Invoice text transfer to Claude API initiated",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="claude_processor",
            legal_basis="legitimate_interest",
            processing_purpose="invoice_text_extraction",
            data_categories_accessed=transfer_context.data_categories,
            risk_level="low",  # Text processing is lower risk than images
            operation_details={
                "transfer_id": transfer_context.transfer_id,
                "recipient_country": transfer_context.recipient_country,
                "recipient_organization": transfer_context.recipient_organization,
                "text_length": len(extracted_text),
                "processing_type": "text_only"
            }
        )
        
        try:
            # Call Claude 4 API with text only (cheaper)
            response = await self.client.messages.create(
                model=settings.AI_MODEL,
                max_tokens=settings.MAX_TOKENS,
                temperature=0.1,  # Low temperature for consistent extraction
                messages=[
                    {
                        "role": "user",
                        "content": f"{self._get_extraction_prompt()}\n\nINVOICE TEXT TO PROCESS:\n{extracted_text}"
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
                event_description=f"Invoice data successfully extracted from text and stored",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="claude_processor",
                legal_basis="legitimate_interest",
                processing_purpose="invoice_text_extraction",
                data_categories_accessed=["business_data", "financial_data", "identifying_data", "contact_data"],
                risk_level="low",
                operation_details={
                    "confidence_score": validation_results.get("confidence_score", 0),
                    "validation_errors": len(validation_results.get("errors", [])),
                    "validation_warnings": len(validation_results.get("warnings", [])),
                    "line_items_count": len(extracted_data.line_items) if extracted_data.line_items else 0,
                    "total_amount": extracted_data.total,
                    "currency": extracted_data.currency,
                    "processing_type": "text_only",
                    "estimated_cost": 0.005  # Text processing is much cheaper
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
                event_description=f"Invoice text processing failed: {str(e)}",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="claude_processor",
                risk_level="high",
                operation_details={"error": str(e), "processing_type": "text_only"}
            )
            
            raise Exception(f"Claude API error: {str(e)}")
    
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
        
        # Check if Claude API key is available
        if not self.api_key_available:
            await update_invoice_status(
                db=db,
                invoice_id=invoice_id,
                status="failed",
                user_id=user_id
            )
            raise Exception(
                "Claude API key not configured. Please set ANTHROPIC_API_KEY environment variable. "
                "Without this key, AI-powered invoice processing is not available."
            )
        
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
        """Get the prompt for French invoice data extraction"""
        return """You are an expert French invoice data extractor specializing in French business documents and accounting compliance. Please analyze the French invoice image(s) and extract all relevant information with particular attention to French regulatory requirements.

FRENCH INVOICE EXPERTISE REQUIRED:
- Understand French business terminology (HT, TTC, TVA, SIREN, SIRET, etc.)
- Recognize French invoice layouts and formats
- Handle accented characters correctly (é, è, à, ç, etc.)
- Parse French addresses and postal codes
- Identify French business legal forms (SARL, SAS, SASU, EURL, etc.)
- Extract French-specific tax information (TVA rates: 20%, 10%, 5.5%, 2.1%)

MANDATORY FRENCH FIELDS TO EXTRACT:

1. BASIC INVOICE INFORMATION:
   - Invoice number (Numéro de facture)
   - Invoice date (Date de facture)
   - Due date (Date d'échéance) if present
   - Sequential invoice number if visible

2. VENDOR/SELLER INFORMATION (MANDATORY):
   - Company name (Raison sociale)
   - Complete address including postal code and city
   - SIREN number (9 digits - format: 123 456 789)
   - SIRET number (14 digits - format: 123 456 789 00123)
   - French TVA number (format: FR + 11 digits, e.g., FR12345678901)
   - NAF/APE code (4 digits + letter, e.g., 6201A)
   - Legal form (SARL, SAS, SASU, EURL, SA, etc.)
   - Share capital (Capital social) if mentioned
   - RCS number (if mentioned)
   - Phone, email if present

3. CUSTOMER/BUYER INFORMATION:
   - Company/individual name
   - Complete address
   - SIREN/SIRET if B2B transaction
   - TVA number if applicable
   - Phone, email if present

4. LINE ITEMS WITH FRENCH SPECIFICATIONS:
   - Description of goods/services
   - Quantity with unit (pièce, heure, kg, etc.)
   - Unit price HT (before TVA)
   - TVA rate for each line (20%, 10%, 5.5%, 2.1%, 0%)
   - TVA amount for each line
   - Total HT per line
   - Total TTC per line if shown

5. FINANCIAL TOTALS (FRENCH FORMAT):
   - Subtotal HT (Hors Taxes - before TVA)
   - TVA breakdown by rate:
     * TVA 20%: Base HT + TVA amount
     * TVA 10%: Base HT + TVA amount (if applicable)
     * TVA 5.5%: Base HT + TVA amount (if applicable)
     * TVA 2.1%: Base HT + TVA amount (if applicable)
   - Total TVA
   - Total TTC (Toutes Taxes Comprises - including TVA)

6. FRENCH MANDATORY CLAUSES:
   - Payment terms (Conditions de paiement)
   - Late payment penalties clause
   - €40 recovery fee clause (Indemnité forfaitaire de recouvrement)

Return the data in this FRENCH-COMPLIANT JSON format:
{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD or null",
    "invoice_sequence_number": number or null,
    "vendor": {
        "name": "string",
        "address": "string",
        "postal_code": "string or null",
        "city": "string or null",
        "country": "France",
        "siren_number": "string (9 digits) or null",
        "siret_number": "string (14 digits) or null",
        "tva_number": "string (FR + 11 digits) or null",
        "naf_code": "string (4 digits + letter) or null",
        "legal_form": "string or null",
        "share_capital": number or null,
        "rcs_number": "string or null",
        "rm_number": "string or null",
        "phone": "string or null",
        "email": "string or null"
    },
    "customer": {
        "name": "string",
        "address": "string",
        "postal_code": "string or null",
        "city": "string or null",
        "country": "string",
        "siren_number": "string or null",
        "siret_number": "string or null",
        "tva_number": "string or null",
        "phone": "string or null",
        "email": "string or null"
    },
    "line_items": [
        {
            "description": "string",
            "quantity": number,
            "unit": "string or null",
            "unit_price": number,
            "total": number,
            "tva_rate": number,
            "tva_amount": number
        }
    ],
    "subtotal_ht": number,
    "tva_breakdown": [
        {
            "rate": number,
            "taxable_amount": number,
            "tva_amount": number
        }
    ],
    "total_tva": number,
    "total_ttc": number,
    "currency": "EUR",
    "payment_terms": "string or null",
    "late_payment_penalties": "string or null",
    "recovery_fees": "string or null",
    "notes": "string or null",
    "delivery_date": "YYYY-MM-DD or null",
    "delivery_address": "string or null"
}

CRITICAL FRENCH REQUIREMENTS:
- Always extract SIREN/SIRET numbers if present (mandatory for French businesses)
- Parse TVA rates correctly (French rates only: 20%, 10%, 5.5%, 2.1%, 0%)
- Use comma as decimal separator in original French format but return as numbers
- Extract complete addresses with postal codes
- Identify legal forms correctly (SARL, SAS, etc.)
- Currency should be EUR for French invoices
- Handle multi-page French invoices by combining all information
- Look for mandatory clauses about late payment penalties and recovery fees

QUALITY CHECKS:
- Verify SIREN is 9 digits, SIRET is 14 digits
- Ensure TVA calculations are correct: Base × Rate = TVA Amount
- Check that sum of all TVA amounts equals total_tva
- Verify that subtotal_ht + total_tva = total_ttc
- Validate French postal codes (5 digits)

IMPORTANT: This is a French invoice processing system for experts-comptables (chartered accountants). Accuracy in French business data extraction is critical for regulatory compliance. Pay special attention to French-specific fields and formatting conventions."""
    
    def _parse_claude_response(self, response_text: str) -> InvoiceData:
        """Parse Claude's response into InvoiceData schema with French support"""
        try:
            # Extract JSON from the response
            # Claude might include explanation text, so we need to find the JSON
            import re
            from schemas.invoice import FrenchBusinessInfo, FrenchTVABreakdown, LineItem
            
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
            else:
                # If no JSON found, try to parse the entire response
                data = json.loads(response_text)
            
            # Parse French business information
            vendor_info = None
            if data.get('vendor'):
                vendor_data = data['vendor']
                vendor_info = FrenchBusinessInfo(
                    name=vendor_data.get('name', ''),
                    address=vendor_data.get('address', ''),
                    postal_code=vendor_data.get('postal_code'),
                    city=vendor_data.get('city'),
                    country=vendor_data.get('country', 'France'),
                    siren_number=vendor_data.get('siren_number'),
                    siret_number=vendor_data.get('siret_number'),
                    tva_number=vendor_data.get('tva_number'),
                    naf_code=vendor_data.get('naf_code'),
                    legal_form=vendor_data.get('legal_form'),
                    share_capital=float(vendor_data['share_capital']) if vendor_data.get('share_capital') else None,
                    rcs_number=vendor_data.get('rcs_number'),
                    rm_number=vendor_data.get('rm_number'),
                    phone=vendor_data.get('phone'),
                    email=vendor_data.get('email')
                )
            
            customer_info = None
            if data.get('customer'):
                customer_data = data['customer']
                customer_info = FrenchBusinessInfo(
                    name=customer_data.get('name', ''),
                    address=customer_data.get('address', ''),
                    postal_code=customer_data.get('postal_code'),
                    city=customer_data.get('city'),
                    country=customer_data.get('country', 'France'),
                    siren_number=customer_data.get('siren_number'),
                    siret_number=customer_data.get('siret_number'),
                    tva_number=customer_data.get('tva_number'),
                    phone=customer_data.get('phone'),
                    email=customer_data.get('email')
                )
            
            # Parse line items with French enhancements
            line_items = []
            for item in data.get('line_items', []):
                line_items.append(LineItem(
                    description=item.get('description', ''),
                    quantity=float(item.get('quantity', 0)),
                    unit_price=float(item.get('unit_price', 0)),
                    total=float(item.get('total', 0)),
                    tva_rate=float(item['tva_rate']) if item.get('tva_rate') is not None else None,
                    tva_amount=float(item['tva_amount']) if item.get('tva_amount') is not None else None,
                    unit=item.get('unit')
                ))
            
            # Parse TVA breakdown
            tva_breakdown = []
            for tva_item in data.get('tva_breakdown', []):
                tva_breakdown.append(FrenchTVABreakdown(
                    rate=float(tva_item['rate']),
                    taxable_amount=float(tva_item['taxable_amount']),
                    tva_amount=float(tva_item['tva_amount'])
                ))
            
            # Create InvoiceData with French enhancements
            invoice_data = InvoiceData(
                # Basic information
                invoice_number=data.get('invoice_number'),
                date=data.get('date'),
                due_date=data.get('due_date'),
                invoice_sequence_number=int(data['invoice_sequence_number']) if data.get('invoice_sequence_number') else None,
                
                # Business entities
                vendor=vendor_info,
                customer=customer_info,
                
                # Legacy fields for backward compatibility
                vendor_name=vendor_info.name if vendor_info else data.get('vendor_name'),
                vendor_address=vendor_info.address if vendor_info else data.get('vendor_address'),
                customer_name=customer_info.name if customer_info else data.get('customer_name'),
                customer_address=customer_info.address if customer_info else data.get('customer_address'),
                
                # Line items
                line_items=line_items,
                
                # French financial information
                subtotal_ht=float(data['subtotal_ht']) if data.get('subtotal_ht') is not None else None,
                tva_breakdown=tva_breakdown,
                total_tva=float(data['total_tva']) if data.get('total_tva') is not None else None,
                total_ttc=float(data['total_ttc']) if data.get('total_ttc') is not None else None,
                
                # Legacy fields for backward compatibility
                subtotal=float(data['subtotal_ht']) if data.get('subtotal_ht') is not None else None,
                tax=float(data['total_tva']) if data.get('total_tva') is not None else None,
                total=float(data['total_ttc']) if data.get('total_ttc') is not None else None,
                
                # Currency and payment
                currency=data.get('currency', 'EUR'),
                payment_terms=data.get('payment_terms'),
                late_payment_penalties=data.get('late_payment_penalties'),
                recovery_fees=data.get('recovery_fees'),
                
                # Additional fields
                notes=data.get('notes'),
                delivery_date=data.get('delivery_date'),
                delivery_address=data.get('delivery_address')
            )
            
            return invoice_data
            
        except Exception as e:
            raise Exception(f"Failed to parse Claude response: {str(e)}\nResponse: {response_text}")
    
    async def validate_extraction(self, invoice_data: InvoiceData) -> Dict[str, Any]:
        """
        Validate the extracted data for French compliance and completeness.
        Returns validation results and confidence scores.
        """
        from core.validation.french_validator import validate_french_invoice
        
        # Use French validator for comprehensive validation
        french_validation = validate_french_invoice(invoice_data)
        
        # Add legacy validation for backward compatibility
        legacy_warnings = []
        
        # Validate line items total matches subtotal (French HT validation)
        if invoice_data.line_items and invoice_data.subtotal_ht:
            calculated_subtotal_ht = sum(item.total for item in invoice_data.line_items)
            if abs(calculated_subtotal_ht - invoice_data.subtotal_ht) > 0.01:
                legacy_warnings.append(
                    f"Montant HT des articles ({calculated_subtotal_ht}€) ne correspond pas au sous-total HT ({invoice_data.subtotal_ht}€)"
                )
        
        # Validate TVA calculation
        if invoice_data.subtotal_ht and invoice_data.total_tva is not None and invoice_data.total_ttc:
            calculated_total_ttc = invoice_data.subtotal_ht + invoice_data.total_tva
            if abs(calculated_total_ttc - invoice_data.total_ttc) > 0.01:
                legacy_warnings.append(
                    f"Calcul total TTC incorrect ({calculated_total_ttc}€) vs montant facturé ({invoice_data.total_ttc}€)"
                )
        
        # Validate TVA breakdown consistency
        if invoice_data.tva_breakdown:
            calculated_total_tva = sum(item.tva_amount for item in invoice_data.tva_breakdown)
            if invoice_data.total_tva and abs(calculated_total_tva - invoice_data.total_tva) > 0.01:
                legacy_warnings.append(
                    f"Somme des TVA par taux ({calculated_total_tva}€) ne correspond pas au total TVA ({invoice_data.total_tva}€)"
                )
        
        # Calculate enhanced confidence score for French invoices
        french_field_count = 0
        french_filled_count = 0
        
        # Count French-specific fields
        if invoice_data.vendor:
            french_field_count += 8  # name, address, siren, siret, tva_number, naf_code, legal_form, etc.
            if invoice_data.vendor.name:
                french_filled_count += 1
            if invoice_data.vendor.address:
                french_filled_count += 1
            if invoice_data.vendor.siren_number:
                french_filled_count += 1
            if invoice_data.vendor.siret_number:
                french_filled_count += 1
            if invoice_data.vendor.tva_number:
                french_filled_count += 1
            if invoice_data.vendor.naf_code:
                french_filled_count += 1
            if invoice_data.vendor.legal_form:
                french_filled_count += 1
            if invoice_data.vendor.postal_code:
                french_filled_count += 1
        
        # Count financial fields
        french_field_count += 4  # subtotal_ht, total_tva, total_ttc, tva_breakdown
        if invoice_data.subtotal_ht:
            french_filled_count += 1
        if invoice_data.total_tva:
            french_filled_count += 1
        if invoice_data.total_ttc:
            french_filled_count += 1
        if invoice_data.tva_breakdown:
            french_filled_count += 1
        
        # Count mandatory clauses
        french_field_count += 2  # late_payment_penalties, recovery_fees
        if invoice_data.late_payment_penalties:
            french_filled_count += 1
        if invoice_data.recovery_fees:
            french_filled_count += 1
        
        # Calculate confidence score
        confidence_score = (french_filled_count / french_field_count * 100) if french_field_count > 0 else 0
        
        # Combine French validation with legacy warnings
        all_warnings = french_validation['warnings'] + legacy_warnings
        
        # Mark invoice as French compliant if no errors
        if french_validation['is_compliant']:
            invoice_data.is_french_compliant = True
            invoice_data.compliance_errors = []
        else:
            invoice_data.is_french_compliant = False
            invoice_data.compliance_errors = french_validation['errors']
        
        return {
            "is_valid": french_validation['is_compliant'],
            "is_french_compliant": french_validation['is_compliant'],
            "errors": french_validation['errors'],
            "warnings": all_warnings,
            "confidence_score": max(confidence_score, french_validation['compliance_score']),
            "french_compliance_score": french_validation['compliance_score'],
            "french_specific_validation": True
        }
    
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
                # TODO: Implement link_invoice_to_data_subject function
                # await link_invoice_to_data_subject(
                #     db=db,
                #     invoice_id=invoice_id,
                #     data_subject_id=vendor_data_subject.id,
                #     role_in_invoice="vendor",
                #     user_id=user_id
                # )
                
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
                # TODO: Implement link_invoice_to_data_subject function
                # await link_invoice_to_data_subject(
                #     db=db,
                #     invoice_id=invoice_id,
                #     data_subject_id=customer_data_subject.id,
                #     role_in_invoice="customer",
                #     user_id=user_id
                # )
                
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

# Privacy-first method removed - single pipeline approach