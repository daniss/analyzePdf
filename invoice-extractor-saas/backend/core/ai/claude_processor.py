import json
from typing import Dict, Any, List, Optional
from anthropic import AsyncAnthropic
import asyncio

from core.config import settings
from schemas.invoice import InvoiceData, LineItem


class ClaudeProcessor:
    """Handles invoice processing using Claude 4 Opus vision capabilities"""
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        
    async def process_invoice_images(self, base64_images: List[str]) -> InvoiceData:
        """
        Process invoice images using Claude 4 Opus vision API.
        Extracts structured data from the invoice.
        """
        
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
            
            return extracted_data
            
        except Exception as e:
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