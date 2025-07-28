"""
Tier 2 - Smart AI Validation
Validates low-confidence fields from Tier 1 using minimal Claude API calls
Focuses only on uncertain data to minimize token usage
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import anthropic
from anthropic import AsyncAnthropic

from core.config import settings
from core.processors.tier1_processor import Tier1Result, ExtractedField
from core.gdpr_audit import GDPRAuditService
from core.gdpr_transfer_compliance import GDPRTransferCompliance

logger = logging.getLogger(__name__)


@dataclass
class ValidationRequest:
    """Request for AI validation of specific fields"""
    field_name: str
    current_value: Any
    confidence: float
    context: str  # Surrounding text
    page: int
    validation_hints: List[str] = field(default_factory=list)


@dataclass
class Tier2Result:
    """Result from Tier 2 processing"""
    validated_fields: Dict[str, ExtractedField] = field(default_factory=dict)
    original_fields: Dict[str, ExtractedField] = field(default_factory=dict)
    corrections_made: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    token_usage: Dict[str, int] = field(default_factory=dict)
    processing_time: float = 0.0
    ai_calls_made: int = 0
    confidence_improvement: float = 0.0


class Tier2Processor:
    """Smart AI validation for low-confidence fields"""
    
    # Confidence threshold below which fields need validation
    CONFIDENCE_THRESHOLD = 0.7
    
    # Fields that are critical and should be validated even with higher confidence
    CRITICAL_FIELDS = ["invoice_number", "total_ttc", "siren", "tva_number"]
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.AI_MODEL
        
    async def process(self, tier1_result: Tier1Result, pdf_text: Optional[str] = None, 
                     invoice_id: Optional[str] = None, user_id: Optional[str] = None,
                     db: Optional[Any] = None) -> Tier2Result:
        """Process Tier 1 results and validate low-confidence fields"""
        start_time = datetime.now()
        result = Tier2Result()
        result.original_fields = tier1_result.fields.copy()
        
        try:
            # Identify fields needing validation
            validation_requests = self._identify_validation_needs(tier1_result)
            
            if not validation_requests:
                logger.info("No fields require AI validation")
                result.validated_fields = tier1_result.fields
                result.processing_time = (datetime.now() - start_time).total_seconds()
                return result
            
            # Assess GDPR transfer risk
            if db and user_id:
                # TODO: Fix GDPR transfer compliance
                # transfer_service = GDPRTransferCompliance()
                # risk_assessment = await transfer_service.assess_transfer_risk(...)
                pass
                
                # TODO: Fix risk assessment check
                # if not risk_assessment.get("approved", False):
                #     logger.warning("Transfer risk assessment not approved, skipping AI validation")
                #     result.validated_fields = tier1_result.fields
                #     return result
            
            # Group validation requests for efficient API usage
            grouped_requests = self._group_validation_requests(validation_requests, tier1_result)
            
            # Perform validations
            for group_name, requests in grouped_requests.items():
                await self._validate_field_group(requests, tier1_result, result, invoice_id, user_id, db)
            
            # Merge validated fields with high-confidence original fields
            result.validated_fields = self._merge_results(tier1_result.fields, result)
            
            # Calculate confidence improvement
            result.confidence_improvement = self._calculate_improvement(
                result.original_fields, 
                result.validated_fields
            )
            
            result.processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Tier 2 validation completed in {result.processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error in Tier 2 processing: {str(e)}")
            # Fallback to original fields
            result.validated_fields = tier1_result.fields
            
        return result
    
    def _identify_validation_needs(self, tier1_result: Tier1Result) -> List[ValidationRequest]:
        """Identify fields that need AI validation"""
        validation_requests = []
        
        for field_name, field in tier1_result.fields.items():
            needs_validation = False
            
            # Check if confidence is below threshold
            if field.confidence < self.CONFIDENCE_THRESHOLD:
                needs_validation = True
                
            # Check if it's a critical field with moderate confidence
            elif field_name in self.CRITICAL_FIELDS and field.confidence < 0.85:
                needs_validation = True
            
            if needs_validation:
                # Find context around the field
                context = self._get_field_context(field, tier1_result.text_blocks)
                
                # Add validation hints based on field type
                hints = self._get_validation_hints(field_name)
                
                validation_requests.append(ValidationRequest(
                    field_name=field_name,
                    current_value=field.value,
                    confidence=field.confidence,
                    context=context,
                    page=field.page,
                    validation_hints=hints
                ))
        
        return validation_requests
    
    def _get_field_context(self, field: ExtractedField, text_blocks: List[Dict]) -> str:
        """Get surrounding text context for a field"""
        # Find blocks near the field's position
        page_blocks = [b for b in text_blocks if b["page"] == field.page]
        
        # Sort by distance from field
        field_y = (field.bbox[1] + field.bbox[3]) / 2
        page_blocks.sort(key=lambda b: abs((b["bbox"][1] + b["bbox"][3]) / 2 - field_y))
        
        # Get nearby text (5 blocks before and after)
        context_blocks = page_blocks[:10]
        context = "\n".join(b["text"] for b in context_blocks)
        
        return context[:1000]  # Limit context size
    
    def _get_validation_hints(self, field_name: str) -> List[str]:
        """Get validation hints for specific field types"""
        hints_map = {
            "invoice_number": [
                "Look for patterns like 'FACTURE N°', 'Invoice #', 'FC-', 'FA-'",
                "Invoice numbers are usually alphanumeric and may contain dashes or slashes"
            ],
            "siren": [
                "SIREN is exactly 9 digits",
                "Often found near company information or footer"
            ],
            "siret": [
                "SIRET is exactly 14 digits (SIREN + 5 digits)",
                "Format: XXX XXX XXX XXXXX"
            ],
            "tva_number": [
                "French TVA starts with 'FR' followed by 11 characters",
                "Format: FR XX XXX XXX XXX"
            ],
            "total_ttc": [
                "Look for 'TOTAL TTC', 'NET À PAYER', 'MONTANT TOTAL'",
                "Should be the largest amount on the invoice"
            ],
            "total_ht": [
                "Look for 'TOTAL HT', 'SOUS-TOTAL', 'MONTANT HT'",
                "Should be less than total TTC"
            ],
            "vendor_name": [
                "Usually at the top of the invoice",
                "May be in larger font or bold"
            ],
            "customer_name": [
                "Look for 'CLIENT:', 'DESTINATAIRE:', 'FACTURÉ À:'",
                "Usually in a separate section from vendor"
            ]
        }
        
        return hints_map.get(field_name, [])
    
    def _group_validation_requests(self, requests: List[ValidationRequest], 
                                 tier1_result: Tier1Result) -> Dict[str, List[ValidationRequest]]:
        """Group validation requests for efficient API calls"""
        groups = {
            "identifiers": [],  # SIREN, SIRET, TVA, Invoice number
            "amounts": [],      # Monetary values
            "entities": [],     # Vendor, customer names
            "dates": [],        # Invoice date, due date
            "other": []
        }
        
        for request in requests:
            if request.field_name in ["siren", "siret", "tva_number", "invoice_number"]:
                groups["identifiers"].append(request)
            elif "total" in request.field_name or "amount" in request.field_name:
                groups["amounts"].append(request)
            elif "vendor" in request.field_name or "customer" in request.field_name:
                groups["entities"].append(request)
            elif "date" in request.field_name:
                groups["dates"].append(request)
            else:
                groups["other"].append(request)
        
        # Remove empty groups
        return {k: v for k, v in groups.items() if v}
    
    async def _validate_field_group(self, requests: List[ValidationRequest], 
                                  tier1_result: Tier1Result, result: Tier2Result,
                                  invoice_id: Optional[str], user_id: Optional[str],
                                  db: Optional[Any]):
        """Validate a group of related fields with a single API call"""
        if not requests:
            return
        
        # Build focused prompt
        prompt = self._build_validation_prompt(requests)
        
        try:
            # Log audit event
            if db and user_id:
                # TODO: Fix audit logging
                # audit_service = GDPRAuditService()
                # await audit_service.log_data_modification(...)
                pass
            
            # Call Claude API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=500,  # Keep responses concise
                temperature=0,  # Deterministic for validation
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            result.ai_calls_made += 1
            
            # Track token usage
            if hasattr(response, 'usage'):
                result.token_usage["input_tokens"] = result.token_usage.get("input_tokens", 0) + response.usage.input_tokens
                result.token_usage["output_tokens"] = result.token_usage.get("output_tokens", 0) + response.usage.output_tokens
            
            # Parse response
            validated_data = self._parse_validation_response(response.content[0].text, requests)
            
            # Update results
            for field_name, validated_value in validated_data.items():
                original_field = tier1_result.fields.get(field_name)
                if original_field:
                    new_confidence = min(0.95, original_field.confidence + 0.3)  # Boost confidence
                    
                    validated_field = ExtractedField(
                        value=validated_value["value"],
                        confidence=new_confidence,
                        page=original_field.page,
                        bbox=original_field.bbox,
                        method="ai_validated",
                        raw_text=original_field.raw_text
                    )
                    
                    result.validated_fields[field_name] = validated_field
                    
                    # Track corrections
                    if str(original_field.value) != str(validated_value["value"]):
                        result.corrections_made[field_name] = {
                            "original": original_field.value,
                            "corrected": validated_value["value"],
                            "reason": validated_value.get("reason", "AI validation")
                        }
                        
        except Exception as e:
            logger.error(f"Error validating field group: {str(e)}")
            # Keep original values on error
            for request in requests:
                if request.field_name in tier1_result.fields:
                    result.validated_fields[request.field_name] = tier1_result.fields[request.field_name]
    
    def _build_validation_prompt(self, requests: List[ValidationRequest]) -> str:
        """Build a focused prompt for field validation"""
        prompt = """You are validating extracted invoice fields. For each field below, confirm or correct the value based on the context provided.

Return your response in JSON format like:
{
  "field_name": {
    "value": "corrected_value",
    "reason": "brief explanation if changed"
  }
}

Fields to validate:
"""
        
        for request in requests:
            prompt += f"\n\nField: {request.field_name}"
            prompt += f"\nCurrent value: {request.current_value}"
            prompt += f"\nConfidence: {request.confidence:.2f}"
            
            if request.validation_hints:
                prompt += f"\nHints: {'; '.join(request.validation_hints)}"
            
            prompt += f"\nContext:\n{request.context[:500]}"
        
        prompt += "\n\nProvide the JSON response:"
        
        return prompt
    
    def _parse_validation_response(self, response_text: str, requests: List[ValidationRequest]) -> Dict[str, Any]:
        """Parse AI validation response"""
        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                validated_data = json.loads(json_text)
                return validated_data
            
        except Exception as e:
            logger.error(f"Error parsing validation response: {str(e)}")
        
        # Fallback: return original values
        return {req.field_name: {"value": req.current_value} for req in requests}
    
    def _merge_results(self, original_fields: Dict[str, ExtractedField], 
                      tier2_result: Tier2Result) -> Dict[str, ExtractedField]:
        """Merge validated fields with high-confidence original fields"""
        merged = original_fields.copy()
        
        # Update with validated fields
        for field_name, validated_field in tier2_result.validated_fields.items():
            merged[field_name] = validated_field
        
        return merged
    
    def _calculate_improvement(self, original: Dict[str, ExtractedField], 
                             validated: Dict[str, ExtractedField]) -> float:
        """Calculate overall confidence improvement"""
        if not original:
            return 0.0
        
        original_avg = sum(f.confidence for f in original.values()) / len(original)
        validated_avg = sum(f.confidence for f in validated.values()) / len(validated)
        
        return validated_avg - original_avg