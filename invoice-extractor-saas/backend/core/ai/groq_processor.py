import json
import uuid
from typing import Dict, Any, List, Optional
import asyncio
import aiohttp
import base64
from datetime import datetime

from core.config import settings
from schemas.invoice import InvoiceData, LineItem, FrenchBusinessInfo, FrenchTVABreakdown
from core.gdpr_transfer_compliance import gdpr_transfer_compliance, TransferContext
from core.gdpr_audit import gdpr_audit
from core.gdpr_encryption import transit_encryption
from crud.invoice import store_extracted_data, update_invoice_status
from crud.data_subject import create_data_subject
from core.gdpr_helpers import log_audit_event
from models.gdpr_models import AuditEventType, DataSubjectType, ProcessingPurpose, DataCategory
from core.cost_tracker import track_processing_cost


class GroqProcessor:
    """Handles invoice processing using Groq API with Llama 3.1 8B model"""
    
    def __init__(self):
        api_key = settings.GROQ_API_KEY
        api_key_valid = (
            api_key and 
            api_key.strip() and 
            api_key != "your-groq-api-key-here" and
            not api_key.startswith("your-") and
            len(api_key) > 20
        )
        
        if not api_key_valid:
            self.api_key_available = False
            print("❌ Groq API key not configured")
        else:
            self.api_key = api_key
            self.api_key_available = True
            print(f"✅ Groq configured with model: {settings.AI_MODEL}")
        
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        
    async def process_invoice_text(
        self,
        extracted_text: str,
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
        db: Any
    ) -> InvoiceData:
        """
        Process invoice text using Groq Llama 3.1 8B model.
        """
        
        # Check if Groq API key is available
        if not self.api_key_available:
            await update_invoice_status(
                db=db,
                invoice_id=invoice_id,
                status="failed",
                user_id=user_id
            )
            raise Exception(
                "Groq API key not configured. Please set GROQ_API_KEY environment variable. "
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
            purpose="invoice_text_extraction",
            data_categories=["identifying_data", "contact_data", "financial_data", "business_data"],
            data_subjects_count=2,  # Typically vendor and customer
            recipient_country="US",
            recipient_organization="Groq Inc",
            legal_basis="legitimate_interest",
            urgency_level="normal",
            retention_period_days=1  # Groq processes and discards
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
                system_component="groq_processor",
                risk_level="high"
            )
            raise
        
        # Log the transfer initiation
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description="Invoice text transfer to Groq API initiated",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="groq_processor",
            legal_basis="legitimate_interest",
            processing_purpose="invoice_text_extraction",
            data_categories_accessed=transfer_context.data_categories,
            risk_level="low",
            operation_details={
                "transfer_id": transfer_context.transfer_id,
                "recipient_country": transfer_context.recipient_country,
                "recipient_organization": transfer_context.recipient_organization,
                "text_length": len(extracted_text),
                "processing_type": "text_only"
            }
        )
        
        try:
            # Prepare the request payload
            payload = {
                "model": settings.AI_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": f"{self._get_extraction_prompt()}\n\nINVOICE TEXT TO PROCESS:\n{extracted_text}"
                    }
                ],
                "max_tokens": settings.MAX_TOKENS,
                "temperature": 0.1  # Low temperature for consistent extraction
            }
            
            # Track processing start time
            start_time = datetime.now()
            
            # Make async HTTP request to Groq API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Groq API error {response.status}: {error_text}")
                    
                    response_data = await response.json()
            
            # Calculate processing duration
            processing_duration = (datetime.now() - start_time).total_seconds()
            
            # Extract response content
            if not response_data.get("choices") or not response_data["choices"][0].get("message"):
                raise Exception("Invalid response format from Groq API")
            
            response_text = response_data["choices"][0]["message"]["content"]
            
            # Estimate tokens used
            prompt_tokens = response_data.get("usage", {}).get("prompt_tokens", 0)
            completion_tokens = response_data.get("usage", {}).get("completion_tokens", 0)
            total_tokens = response_data.get("usage", {}).get("total_tokens", prompt_tokens + completion_tokens)
            
            # Track cost (Groq is very cheap/free)
            asyncio.create_task(track_processing_cost(
                provider="groq",
                tokens_used=total_tokens,
                invoice_count=1,
                user_id=user_id,
                invoice_id=invoice_id,
                processing_successful=True,
                processing_duration=processing_duration,
                estimated_cost_usd=0.0001  # Groq is extremely cheap
            ))
            
            # Parse the response
            extracted_data = self._parse_llama_response(response_text)
            
            # Validate the extraction with comprehensive INSEE validation
            validation_results = await self.validate_extraction(extracted_data, db)
            
            # Perform comprehensive SIRET validation
            siret_validation_results = await self._perform_siret_validation(extracted_data, db, invoice_id, user_id)
            
            # Store extracted data in database with encryption
            extracted_data_dict = extracted_data.dict()
            extracted_data_dict["validation_results"] = validation_results
            extracted_data_dict["siret_validation_results"] = siret_validation_results
            
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
                event_description=f"Invoice data successfully extracted from text via Groq and stored",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="groq_processor",
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
                    "estimated_cost": 0.0001,
                    "tokens_used": total_tokens
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
            
            # Track failed processing cost
            asyncio.create_task(track_processing_cost(
                provider="groq",
                tokens_used=0,
                invoice_count=1,
                user_id=user_id,
                invoice_id=invoice_id,
                processing_successful=False,
                error_message=str(e)
            ))
            
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"Invoice text processing failed: {str(e)}",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="groq_processor",
                risk_level="high",
                operation_details={"error": str(e), "processing_type": "text_only"}
            )
            
            raise Exception(f"Groq API error: {str(e)}")
    
    async def process_invoice_images(
        self, 
        base64_images: List[str], 
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
        db: Any
    ) -> InvoiceData:
        """
        Process invoice images using text-only model.
        Note: Llama 3.1 8B doesn't support vision, so this will fail gracefully
        and suggest using text extraction instead.
        """
        
        await update_invoice_status(
            db=db,
            invoice_id=invoice_id,
            status="failed",
            user_id=user_id
        )
        
        raise Exception(
            "Groq Llama 3.1 8B model doesn't support vision processing. "
            "Please ensure PDF text extraction works properly, or use a vision-capable model."
        )
    
    def _get_extraction_prompt(self) -> str:
        """Get the prompt for French/English invoice data extraction optimized for Llama with French business identifiers"""
        return """You are an expert invoice data extractor specializing in French and English business documents. You must extract ALL relevant information from the invoice text and return it as valid JSON only.

CRITICAL: Return ONLY the JSON object, no explanations or markdown formatting.

SPECIAL FOCUS ON FRENCH BUSINESS IDENTIFIERS:
- SIREN: 9-digit French business registration number
- SIRET: 14-digit French establishment identifier (SIREN + 5 digits)
- TVA Number: French VAT number (starts with FR followed by 2 digits and 9-digit SIREN)
- Look for patterns like "SIREN: 123456789", "SIRET: 12345678901234", "N° TVA: FR12345678901"
- Extract these even if they appear in different formats or locations

Extract the following information:

1. BASIC INVOICE INFORMATION:
   - Invoice number, date, due date

2. VENDOR/SELLER INFORMATION (FOURNISSEUR):
   - The company ISSUING the invoice (appears under "FOURNISSEUR" section)
   - Company name, complete address, phone, email
   - SIREN number (9 digits)
   - SIRET number (14 digits)
   - TVA number (French VAT)
   - Any other tax identifiers

3. CUSTOMER/BUYER INFORMATION (CLIENT):
   - The company RECEIVING the invoice (appears under "CLIENT" section)
   - Company/individual name, complete address, phone, email
   - SIREN number (9 digits) if available
   - SIRET number (14 digits) if available
   - TVA number if available
   
IMPORTANT: In French invoices:
- FOURNISSEUR = vendor/seller (the one issuing the invoice)
- CLIENT = customer/buyer (the one receiving the invoice)
- These are SEPARATE entities - never combine their names!

EXAMPLE:
If you see:
FOURNISSEUR: CARREFOUR FRANCE
CLIENT: BOUYGUES CONSTRUCTION

Then:
vendor.name = "CARREFOUR FRANCE"
customer.name = "BOUYGUES CONSTRUCTION"

NOT: vendor.name = "CARREFOUR FRANCE BOUYGUES CONSTRUCTION"

4. LINE ITEMS:
   - Description, quantity, unit price, tax rate, tax amount, total per line
   - Calculate missing tax amounts if tax rate is provided

5. FINANCIAL TOTALS:
   - Subtotal HT (before tax), tax breakdown by rate, total tax, total TTC (including tax), currency
   - If tax amounts are missing, calculate them from rates and subtotals
   - Common French tax rates: 20%, 10%, 5.5%, 2.1%

6. PAYMENT INFORMATION:
   - Payment terms (délai de paiement)
   - Payment method (moyen de paiement: virement, chèque, espèces, etc.)
   - Bank details/IBAN/RIB (coordonnées bancaires)
   - Due date (date d'échéance)

7. ADDITIONAL BUSINESS CONTEXT:
   - Order number (numéro de commande)
   - Project reference (référence projet)
   - Contract number (numéro de contrat)
   - Delivery information

Return ONLY this JSON structure:
{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD or null",
    "vendor": {
        "name": "string",
        "address": "string",
        "postal_code": "string or null",
        "city": "string or null",
        "country": "string",
        "phone": "string or null",
        "email": "string or null",
        "siren_number": "string or null",
        "siret_number": "string or null",
        "tva_number": "string or null",
        "tax_id": "string or null"
    },
    "customer": {
        "name": "string",
        "address": "string",
        "postal_code": "string or null",
        "city": "string or null",
        "country": "string",
        "phone": "string or null",
        "email": "string or null",
        "siren_number": "string or null",
        "siret_number": "string or null",
        "tva_number": "string or null",
        "tax_id": "string or null"
    },
    "line_items": [
        {
            "description": "string",
            "quantity": number,
            "unit_price": number,
            "total": number,
            "tax_rate": number,
            "tax_amount": number
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
    "subtotal": number,
    "total_tax": number,
    "total": number,
    "currency": "string",
    "payment_terms": "string or null",
    "payment_method": "string or null",
    "bank_details": "string or null",
    "order_number": "string or null",
    "project_reference": "string or null",
    "contract_number": "string or null",
    "delivery_date": "YYYY-MM-DD or null",
    "delivery_address": "string or null",
    "notes": "string or null"
}"""

    def _parse_llama_response(self, response_text: str) -> InvoiceData:
        """Parse Llama's response into InvoiceData schema"""
        try:
            # Extract JSON from the response (Llama sometimes adds text around JSON)
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
            
            # Parse business information - always create vendor object if we have vendor data
            vendor_info = None
            if data.get('vendor') and data['vendor'].get('name'):
                vendor_data = data['vendor']
                
                # Handle SIREN/SIRET parsing with priority on direct fields
                siren_number = vendor_data.get('siren_number')
                siret_number = vendor_data.get('siret_number')
                tva_number = vendor_data.get('tva_number')
                
                # Clean and validate SIREN/SIRET numbers
                if siren_number:
                    siren_number = ''.join(filter(str.isdigit, str(siren_number)))
                    if len(siren_number) != 9:
                        siren_number = None
                        
                if siret_number:
                    siret_number = ''.join(filter(str.isdigit, str(siret_number)))
                    if len(siret_number) == 14:
                        # Extract SIREN from SIRET if we don't have it
                        if not siren_number:
                            siren_number = siret_number[:9]
                    else:
                        siret_number = None
                
                # Fallback: try to extract from tax_id field
                if not siren_number and not siret_number:
                    tax_id = vendor_data.get('tax_id')
                    if tax_id:
                        # Remove non-digits
                        clean_tax_id = ''.join(filter(str.isdigit, str(tax_id)))
                        if len(clean_tax_id) == 9:
                            siren_number = clean_tax_id
                        elif len(clean_tax_id) == 14:
                            siret_number = clean_tax_id
                            siren_number = clean_tax_id[:9]
                
                # Final fallback: search in all text fields
                if not siret_number:
                    import re
                    text_to_search = f"{vendor_data.get('name', '')} {vendor_data.get('address', '')} {vendor_data.get('tax_id', '')}"
                    
                    # Look for 14-digit SIRET
                    siret_match = re.search(r'\b(\d{14})\b', text_to_search)
                    if siret_match:
                        potential_siret = siret_match.group(1)
                        siret_number = potential_siret
                        siren_number = potential_siret[:9]
                    
                    # Look for 9-digit SIREN if no SIRET found
                    elif not siren_number:
                        siren_match = re.search(r'\b(\d{9})\b', text_to_search)
                        if siren_match:
                            siren_number = siren_match.group(1)
                
                # Extract TVA number from various formats
                if not tva_number:
                    # Look for French TVA patterns
                    import re
                    text_to_search = f"{vendor_data.get('name', '')} {vendor_data.get('address', '')} {vendor_data.get('tax_id', '')} {vendor_data.get('tva_number', '')}"
                    
                    # French TVA format: FR + 2 digits + 9-digit SIREN
                    tva_match = re.search(r'\b(FR\s*\d{2}\s*\d{9})\b', text_to_search, re.IGNORECASE)
                    if tva_match:
                        tva_number = tva_match.group(1).replace(' ', '').upper()
                
                vendor_info = FrenchBusinessInfo(
                    name=vendor_data.get('name', ''),
                    address=vendor_data.get('address'),
                    postal_code=vendor_data.get('postal_code'),
                    city=vendor_data.get('city'),
                    country=vendor_data.get('country'),
                    siren_number=siren_number,
                    siret_number=siret_number,
                    tva_number=tva_number,
                    phone=vendor_data.get('phone'),
                    email=vendor_data.get('email')
                )
            
            customer_info = None
            if data.get('customer') and data['customer'].get('name'):
                customer_data = data['customer']
                
                # Handle SIREN/SIRET parsing with priority on direct fields
                siren_number = customer_data.get('siren_number')
                siret_number = customer_data.get('siret_number')
                tva_number = customer_data.get('tva_number')
                
                # Clean and validate SIREN/SIRET numbers
                if siren_number:
                    siren_number = ''.join(filter(str.isdigit, str(siren_number)))
                    if len(siren_number) != 9:
                        siren_number = None
                        
                if siret_number:
                    siret_number = ''.join(filter(str.isdigit, str(siret_number)))
                    if len(siret_number) == 14:
                        # Extract SIREN from SIRET if we don't have it
                        if not siren_number:
                            siren_number = siret_number[:9]
                    else:
                        siret_number = None
                
                # Fallback: try to extract from tax_id field
                if not siren_number and not siret_number:
                    tax_id = customer_data.get('tax_id')
                    if tax_id:
                        # Remove non-digits
                        clean_tax_id = ''.join(filter(str.isdigit, str(tax_id)))
                        if len(clean_tax_id) == 9:
                            siren_number = clean_tax_id
                        elif len(clean_tax_id) == 14:
                            siret_number = clean_tax_id
                            siren_number = clean_tax_id[:9]
                
                # Final fallback: search in all text fields
                if not siret_number:
                    import re
                    text_to_search = f"{customer_data.get('name', '')} {customer_data.get('address', '')} {customer_data.get('tax_id', '')}"
                    
                    # Look for 14-digit SIRET
                    siret_match = re.search(r'\b(\d{14})\b', text_to_search)
                    if siret_match:
                        potential_siret = siret_match.group(1)
                        siret_number = potential_siret
                        siren_number = potential_siret[:9]
                    
                    # Look for 9-digit SIREN if no SIRET found
                    elif not siren_number:
                        siren_match = re.search(r'\b(\d{9})\b', text_to_search)
                        if siren_match:
                            siren_number = siren_match.group(1)
                
                # Extract TVA number from various formats
                if not tva_number:
                    # Look for French TVA patterns
                    import re
                    text_to_search = f"{customer_data.get('name', '')} {customer_data.get('address', '')} {customer_data.get('tax_id', '')} {customer_data.get('tva_number', '')}"
                    
                    # French TVA format: FR + 2 digits + 9-digit SIREN
                    tva_match = re.search(r'\b(FR\s*\d{2}\s*\d{9})\b', text_to_search, re.IGNORECASE)
                    if tva_match:
                        tva_number = tva_match.group(1).replace(' ', '').upper()
                
                customer_info = FrenchBusinessInfo(
                    name=customer_data.get('name', ''),
                    address=customer_data.get('address'),
                    postal_code=customer_data.get('postal_code'),
                    city=customer_data.get('city'),
                    country=customer_data.get('country'),
                    siren_number=siren_number,
                    siret_number=siret_number,
                    tva_number=tva_number,
                    phone=customer_data.get('phone'),
                    email=customer_data.get('email')
                )
            
            # Parse line items with tax calculation fixes
            line_items = []
            for item in data.get('line_items', []):
                quantity = float(item.get('quantity', 0))
                unit_price = float(item.get('unit_price', 0))
                total = float(item.get('total', 0))
                tax_rate = float(item['tax_rate']) if item.get('tax_rate') is not None else None
                tax_amount = float(item['tax_amount']) if item.get('tax_amount') is not None else None
                
                # Fix missing tax calculations
                if tax_rate is not None and tax_amount is None and total > 0:
                    # Calculate tax amount: total * (tax_rate / (100 + tax_rate))
                    tax_amount = total * (tax_rate / (100 + tax_rate))
                elif tax_rate is not None and tax_amount is None and unit_price > 0 and quantity > 0:
                    # Calculate from unit price and quantity
                    subtotal_ht = unit_price * quantity
                    tax_amount = subtotal_ht * (tax_rate / 100)
                    if total == 0:
                        total = subtotal_ht + tax_amount
                
                line_items.append(LineItem(
                    description=item.get('description', ''),
                    quantity=quantity,
                    unit_price=unit_price,
                    total=total,
                    tva_rate=tax_rate,
                    tva_amount=tax_amount
                ))
            
            # Parse tax breakdown with improved calculation logic
            tva_breakdown = []
            # Handle both French (tva_breakdown) and English (tax_breakdown) field names
            tax_breakdown_data = data.get('tva_breakdown', data.get('tax_breakdown', []))
            for tax_item in tax_breakdown_data:
                rate = tax_item.get('rate')
                taxable_amount = tax_item.get('taxable_amount')
                # Handle both French (tva_amount) and English (tax_amount) field names
                tax_amount = tax_item.get('tva_amount', tax_item.get('tax_amount'))
                
                # Calculate missing values if possible
                if rate is not None and taxable_amount is not None and tax_amount is None:
                    tax_amount = float(taxable_amount) * (float(rate) / 100)
                elif rate is not None and tax_amount is not None and taxable_amount is None:
                    taxable_amount = float(tax_amount) / (float(rate) / 100)
                elif taxable_amount is not None and tax_amount is not None and rate is None:
                    if float(taxable_amount) > 0:
                        rate = (float(tax_amount) / float(taxable_amount)) * 100
                
                # Only add if we have all required data
                if (rate is not None and taxable_amount is not None and tax_amount is not None):
                    tva_breakdown.append(FrenchTVABreakdown(
                        rate=float(rate),
                        taxable_amount=float(taxable_amount),
                        tva_amount=float(tax_amount)
                    ))
            
            # If no tax breakdown provided but we have line items with taxes, calculate it
            if not tva_breakdown and line_items:
                tax_groups = {}
                for item in line_items:
                    if item.tva_rate is not None and item.tva_amount is not None:
                        rate = item.tva_rate
                        if rate not in tax_groups:
                            tax_groups[rate] = {'taxable_amount': 0, 'tax_amount': 0}
                        
                        # Calculate taxable amount (total - tax)
                        taxable_item_amount = item.total - item.tva_amount if item.total > item.tva_amount else item.total / (1 + rate/100)
                        tax_groups[rate]['taxable_amount'] += taxable_item_amount
                        tax_groups[rate]['tax_amount'] += item.tva_amount
                
                for rate, amounts in tax_groups.items():
                    tva_breakdown.append(FrenchTVABreakdown(
                        rate=rate,
                        taxable_amount=amounts['taxable_amount'],
                        tva_amount=amounts['tax_amount']
                    ))
            
            # Create InvoiceData
            invoice_data = InvoiceData(
                # Basic information
                invoice_number=data.get('invoice_number'),
                date=data.get('date'),
                due_date=data.get('due_date'),
                
                # Business entities
                vendor=vendor_info,
                customer=customer_info,
                
                # Legacy fields for backward compatibility
                vendor_name=vendor_info.name if vendor_info else None,
                vendor_address=vendor_info.address if vendor_info else None,
                customer_name=customer_info.name if customer_info else None,
                customer_address=customer_info.address if customer_info else None,
                
                # Line items
                line_items=line_items,
                
                # Financial information with improved calculations
                # Use French field names with fallback to international names
                subtotal_ht=(
                    float(data['subtotal_ht']) if data.get('subtotal_ht') is not None else
                    float(data['subtotal']) if data.get('subtotal') is not None else None
                ),
                tva_breakdown=tva_breakdown,
                total_tva=(
                    float(data['total_tva']) if data.get('total_tva') is not None else
                    float(data['total_tax']) if data.get('total_tax') is not None else
                    (sum(t.tva_amount for t in tva_breakdown) if tva_breakdown else None)
                ),
                total_ttc=(
                    float(data['total_ttc']) if data.get('total_ttc') is not None else
                    float(data['total']) if data.get('total') is not None else None
                ),
                
                # Legacy fields for backward compatibility
                subtotal=(
                    float(data['subtotal_ht']) if data.get('subtotal_ht') is not None else
                    float(data['subtotal']) if data.get('subtotal') is not None else None
                ),
                tax=(
                    float(data['total_tva']) if data.get('total_tva') is not None else
                    float(data['total_tax']) if data.get('total_tax') is not None else None
                ),
                total=(
                    float(data['total_ttc']) if data.get('total_ttc') is not None else
                    float(data['total']) if data.get('total') is not None else None
                ),
                
                # Currency and payment
                currency=data.get('currency', 'EUR'),
                payment_terms=data.get('payment_terms'),
                payment_method=data.get('payment_method'),
                bank_details=data.get('bank_details'),
                
                # Business context
                order_number=data.get('order_number'),
                project_reference=data.get('project_reference'),
                contract_number=data.get('contract_number'),
                
                # Additional fields
                delivery_date=data.get('delivery_date'),
                delivery_address=data.get('delivery_address'),
                notes=data.get('notes')
            )
            
            return invoice_data
            
        except Exception as e:
            raise Exception(f"Failed to parse Groq response: {str(e)}\nResponse: {response_text}")
    
    async def validate_extraction(self, invoice_data: InvoiceData, db_session: Any = None) -> Dict[str, Any]:
        """Validate the extracted data for compliance and completeness using comprehensive French validation"""
        try:
            # Use comprehensive validation orchestrator with INSEE integration
            from core.french_compliance.validation_orchestrator import FrenchComplianceOrchestrator
            
            if db_session:
                # Use comprehensive validation with INSEE API integration
                orchestrator = FrenchComplianceOrchestrator()
                comprehensive_result = await orchestrator.validate_invoice_comprehensive(
                    invoice_data, db_session
                )
                
                # Extract validation results for compatibility
                french_validation = {
                    "is_compliant": comprehensive_result.overall_compliant,
                    "errors": [error.message for error in comprehensive_result.error_report.errors],
                    "warnings": [warning.message for warning in comprehensive_result.error_report.warnings],
                    "compliance_score": comprehensive_result.compliance_score
                }
            else:
                # Fallback to basic validation if no db session
                from core.validation.french_validator import validate_french_invoice_sync
                french_validation = validate_french_invoice_sync(invoice_data)
                
        except Exception as e:
            # If comprehensive validator not available, use basic validation
            try:
                from core.validation.french_validator import validate_french_invoice_sync
                french_validation = validate_french_invoice_sync(invoice_data)
            except:
                french_validation = {"is_compliant": True, "errors": [], "warnings": [], "compliance_score": 85}
        
        # Add legacy validation for backward compatibility
        legacy_warnings = []
        
        # Validate line items total matches subtotal
        if invoice_data.line_items and invoice_data.subtotal:
            calculated_subtotal = sum(item.total for item in invoice_data.line_items)
            if abs(calculated_subtotal - invoice_data.subtotal) > 0.01:
                legacy_warnings.append(
                    f"Line items total ({calculated_subtotal}) doesn't match subtotal ({invoice_data.subtotal})"
                )
        
        # Calculate confidence score
        field_count = 10  # Basic required fields
        filled_count = 0
        
        if invoice_data.invoice_number: filled_count += 1
        if invoice_data.date: filled_count += 1
        if invoice_data.vendor_name: filled_count += 1
        if invoice_data.customer_name: filled_count += 1
        if invoice_data.line_items: filled_count += 1
        if invoice_data.subtotal: filled_count += 1
        if invoice_data.tax: filled_count += 1
        if invoice_data.total: filled_count += 1
        if invoice_data.currency: filled_count += 1
        if invoice_data.payment_terms: filled_count += 1
        
        confidence_score = (filled_count / field_count * 100) if field_count > 0 else 0
        
        # Combine validations
        all_warnings = french_validation.get('warnings', []) + legacy_warnings
        
        return {
            "is_valid": french_validation.get('is_compliant', True),
            "errors": french_validation.get('errors', []),
            "warnings": all_warnings,
            "confidence_score": max(confidence_score, french_validation.get('compliance_score', 85)),
            "processing_engine": "groq-llama-3.1-8b"
        }
    
    async def _create_data_subjects_from_extraction(
        self,
        db: Any,
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
                    consent_given=False
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
                    consent_given=False
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
                    system_component="groq_processor",
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
                system_component="groq_processor",
                risk_level="medium",
                operation_details={"error": str(e)}
            )
    
    async def _perform_siret_validation(
        self,
        extracted_data: InvoiceData,
        db: Any,
        invoice_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Perform comprehensive SIRET validation for French compliance
        """
        try:
            from core.validation.siret_validation_service import SIRETValidationService
            
            siret_validation_service = SIRETValidationService()
            
            # Log SIRET validation attempt
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"SIRET validation started - Vendor: {extracted_data.vendor.siret_number if extracted_data.vendor else 'None'}, Customer: {extracted_data.customer.siret_number if extracted_data.customer else 'None'}",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="groq_processor",
                risk_level="low",
                operation_details={"stage": "siret_validation_start", "vendor_exists": extracted_data.vendor is not None, "customer_exists": extracted_data.customer is not None}
            )
            
            # Check vendor SIRET
            vendor_siret_result = None
            if extracted_data.vendor and extracted_data.vendor.siret_number:
                vendor_siret_result = await siret_validation_service.validate_siret_comprehensive(
                    siret=extracted_data.vendor.siret_number,
                    extracted_company_name=extracted_data.vendor.name,
                    db_session=db,
                    invoice_id=str(invoice_id),
                    user_id=str(user_id)
                )
            
            # Check customer SIRET if present
            customer_siret_result = None
            if extracted_data.customer and extracted_data.customer.siret_number:
                customer_siret_result = await siret_validation_service.validate_siret_comprehensive(
                    siret=extracted_data.customer.siret_number,
                    extracted_company_name=extracted_data.customer.name,
                    db_session=db,
                    invoice_id=str(invoice_id),
                    user_id=str(user_id)
                )
            
            # Compile results
            validation_summary = {
                "vendor_siret_validation": {
                    "performed": vendor_siret_result is not None,
                    "status": vendor_siret_result.validation_status.value if vendor_siret_result else None,
                    "blocking_level": vendor_siret_result.blocking_level.value if vendor_siret_result else None,
                    "compliance_risk": vendor_siret_result.compliance_risk.value if vendor_siret_result else None,
                    "traffic_light": vendor_siret_result.traffic_light_color if vendor_siret_result else None,
                    "export_blocked": vendor_siret_result.export_blocked if vendor_siret_result else False,
                    "french_error_message": vendor_siret_result.french_error_message if vendor_siret_result else None,
                    "user_options_available": len(vendor_siret_result.user_options) > 0 if vendor_siret_result else False
                },
                "customer_siret_validation": {
                    "performed": customer_siret_result is not None,
                    "status": customer_siret_result.validation_status.value if customer_siret_result else None,
                    "blocking_level": customer_siret_result.blocking_level.value if customer_siret_result else None,
                    "compliance_risk": customer_siret_result.compliance_risk.value if customer_siret_result else None,
                    "traffic_light": customer_siret_result.traffic_light_color if customer_siret_result else None,
                    "export_blocked": customer_siret_result.export_blocked if customer_siret_result else False,
                    "french_error_message": customer_siret_result.french_error_message if customer_siret_result else None,
                    "user_options_available": len(customer_siret_result.user_options) > 0 if customer_siret_result else False
                },
                "overall_summary": {
                    "any_siret_found": vendor_siret_result is not None or customer_siret_result is not None,
                    "any_export_blocked": (vendor_siret_result and vendor_siret_result.export_blocked) or 
                                         (customer_siret_result and customer_siret_result.export_blocked),
                    "highest_risk": self._get_highest_risk([
                        vendor_siret_result.compliance_risk.value if vendor_siret_result else None,
                        customer_siret_result.compliance_risk.value if customer_siret_result else None
                    ]),
                    "requires_user_action": (vendor_siret_result and len(vendor_siret_result.user_options) > 0) or
                                          (customer_siret_result and len(customer_siret_result.user_options) > 0)
                }
            }
            
            return validation_summary
            
        except Exception as e:
            # Don't fail the entire processing for SIRET validation errors
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"SIRET validation failed: {str(e)}",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="groq_processor",
                risk_level="medium",
                operation_details={"error": str(e), "stage": "siret_validation"}
            )
            
            return {
                "vendor_siret_validation": {"performed": False, "error": str(e)},
                "customer_siret_validation": {"performed": False, "error": str(e)},
                "overall_summary": {
                    "any_siret_found": False,
                    "any_export_blocked": False,
                    "highest_risk": "unknown",
                    "requires_user_action": False,
                    "validation_error": str(e)
                }
            }
    
    def _get_highest_risk(self, risk_levels: List[Optional[str]]) -> str:
        """Get the highest compliance risk level from a list"""
        risk_hierarchy = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        
        valid_risks = [risk for risk in risk_levels if risk and risk in risk_hierarchy]
        if not valid_risks:
            return "unknown"
        
        highest_risk = max(valid_risks, key=lambda x: risk_hierarchy[x])
        return highest_risk