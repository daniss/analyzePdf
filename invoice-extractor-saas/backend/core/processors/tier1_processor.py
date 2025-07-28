"""
Tier 1 - Local Extraction Service
Fast, local PDF text extraction with pattern matching for French invoices
No external API calls - designed for speed and efficiency
"""

import re
import fitz  # PyMuPDF
import pypdfium2 as pdfium
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


@dataclass
class ExtractedField:
    """Represents an extracted field with position and confidence"""
    value: Any
    confidence: float  # 0.0 to 1.0
    page: int
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    method: str  # 'regex', 'keyword', 'position'
    raw_text: Optional[str] = None


@dataclass
class Tier1Result:
    """Result from Tier 1 processing"""
    fields: Dict[str, ExtractedField] = field(default_factory=dict)
    text_blocks: List[Dict[str, Any]] = field(default_factory=list)
    processing_time: float = 0.0
    page_count: int = 0
    extraction_method: str = "local_patterns"
    confidence_summary: Dict[str, float] = field(default_factory=dict)


class FrenchInvoicePatterns:
    """French invoice-specific regex patterns and keywords"""
    
    # SIREN/SIRET patterns
    SIREN_PATTERN = re.compile(r'\b(\d{3}[\s\-]?\d{3}[\s\-]?\d{3})\b')
    SIRET_PATTERN = re.compile(r'\b(\d{3}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{5})\b')
    
    # TVA number pattern
    TVA_PATTERN = re.compile(r'\b(FR[\s]?[0-9A-Z]{2}[\s]?\d{3}[\s]?\d{3}[\s]?\d{3})\b', re.IGNORECASE)
    
    # Invoice number patterns (various French formats)
    INVOICE_PATTERNS = [
        re.compile(r'(?:facture|fact\.?|invoice)[\s\-:]*(?:n[°o]?)?[\s\-:]*([A-Z0-9\-/]+)', re.IGNORECASE),
        re.compile(r'(?:numéro|numero|n[°o]?)[\s\-:]*(?:de\s+facture)?[\s\-:]*([A-Z0-9\-/]+)', re.IGNORECASE),
        re.compile(r'\b(FC|FA|FV|INV)[\-\s]?(\d{4,})\b', re.IGNORECASE),
    ]
    
    # Date patterns (French format DD/MM/YYYY or DD-MM-YYYY)
    DATE_PATTERN = re.compile(r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b')
    
    # Amount patterns (French format with spaces and comma)
    AMOUNT_PATTERNS = [
        # Format: 1 234,56 € or 1234,56€
        re.compile(r'(\d{1,3}(?:\s?\d{3})*(?:,\d{1,2})?)\s*€'),
        # Format: EUR 1.234,56 or 1234,56 EUR
        re.compile(r'(?:EUR\s*)(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)|(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s*EUR'),
    ]
    
    # TVA rate patterns
    TVA_RATE_PATTERN = re.compile(r'(?:TVA|T\.V\.A\.?)\s*(?:à)?\s*(\d{1,2}(?:,\d{1,2})?)\s*%', re.IGNORECASE)
    
    # Keywords for field identification
    VENDOR_KEYWORDS = ['vendeur', 'fournisseur', 'émetteur', 'de:', 'expéditeur', 'société']
    CUSTOMER_KEYWORDS = ['client', 'destinataire', 'à:', 'facturé à', 'livré à', 'acheteur']
    TOTAL_KEYWORDS = ['total ttc', 'total général', 'net à payer', 'montant total', 'total']
    SUBTOTAL_KEYWORDS = ['total ht', 'sous-total', 'montant ht', 'base ht']
    TVA_KEYWORDS = ['tva', 'taxe', 't.v.a.', 'montant tva']
    DATE_KEYWORDS = ['date', 'émise le', 'établie le', 'le']
    DUE_DATE_KEYWORDS = ['échéance', 'date limite', 'à payer avant', 'payable le']


class Tier1Processor:
    """Fast local PDF processor for French invoices"""
    
    def __init__(self):
        self.patterns = FrenchInvoicePatterns()
        
    async def process_pdf(self, pdf_path: str) -> Tier1Result:
        """Process PDF and extract invoice data using local patterns"""
        start_time = datetime.now()
        result = Tier1Result()
        
        try:
            # Extract text with positions using PyMuPDF
            text_blocks = await self._extract_text_with_positions(pdf_path)
            result.text_blocks = text_blocks
            result.page_count = len(set(block['page'] for block in text_blocks))
            
            # Extract fields using pattern matching
            await self._extract_invoice_number(text_blocks, result)
            await self._extract_dates(text_blocks, result)
            await self._extract_business_identifiers(text_blocks, result)
            await self._extract_amounts(text_blocks, result)
            await self._extract_entities(text_blocks, result)
            
            # Calculate overall confidence
            self._calculate_confidence_summary(result)
            
            # Calculate processing time
            result.processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Tier 1 processing completed in {result.processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error in Tier 1 processing: {str(e)}")
            raise
            
        return result
    
    async def _extract_text_with_positions(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract text blocks with positions from PDF"""
        text_blocks = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num, page in enumerate(doc):
                # Get text blocks with positions
                blocks = page.get_text("dict")
                
                for block in blocks.get("blocks", []):
                    if block.get("type") == 0:  # Text block
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                text = span.get("text", "").strip()
                                if text:
                                    text_blocks.append({
                                        "text": text,
                                        "page": page_num,
                                        "bbox": span.get("bbox", [0, 0, 0, 0]),
                                        "font": span.get("font", ""),
                                        "size": span.get("size", 0),
                                        "flags": span.get("flags", 0),  # Bold, italic, etc.
                                    })
                                    
            doc.close()
            
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            # Fallback to pypdfium2
            text_blocks = await self._extract_text_pypdfium(pdf_path)
            
        return text_blocks
    
    async def _extract_text_pypdfium(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Fallback text extraction using pypdfium2"""
        text_blocks = []
        
        pdf = pdfium.PdfDocument(pdf_path)
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            textpage = page.get_textpage()
            
            # Get all text with basic positioning
            text = textpage.get_text_range()
            if text:
                text_blocks.append({
                    "text": text,
                    "page": page_num,
                    "bbox": [0, 0, page.get_width(), page.get_height()],
                    "font": "unknown",
                    "size": 0,
                    "flags": 0,
                })
                
        pdf.close()
        return text_blocks
    
    async def _extract_invoice_number(self, text_blocks: List[Dict], result: Tier1Result):
        """Extract invoice number using patterns"""
        for block in text_blocks:
            text = block["text"]
            
            for pattern in self.patterns.INVOICE_PATTERNS:
                match = pattern.search(text)
                if match:
                    invoice_num = match.group(1) if match.lastindex else match.group(0)
                    
                    # Clean up the invoice number
                    invoice_num = invoice_num.strip()
                    
                    # Calculate confidence based on pattern match quality
                    confidence = 0.9 if len(invoice_num) > 4 else 0.7
                    
                    result.fields["invoice_number"] = ExtractedField(
                        value=invoice_num,
                        confidence=confidence,
                        page=block["page"],
                        bbox=block["bbox"],
                        method="regex",
                        raw_text=text
                    )
                    return
    
    async def _extract_dates(self, text_blocks: List[Dict], result: Tier1Result):
        """Extract dates from text blocks"""
        date_candidates = []
        
        for block in text_blocks:
            text = block["text"].lower()
            
            # Find all date matches
            matches = self.patterns.DATE_PATTERN.findall(block["text"])
            
            for match in matches:
                day, month, year = match
                try:
                    # Validate date
                    date_obj = datetime(int(year), int(month), int(day))
                    date_str = f"{day}/{month}/{year}"
                    
                    # Check context for date type
                    is_due_date = any(keyword in text for keyword in self.patterns.DUE_DATE_KEYWORDS)
                    is_invoice_date = any(keyword in text for keyword in self.patterns.DATE_KEYWORDS)
                    
                    confidence = 0.9 if (is_due_date or is_invoice_date) else 0.6
                    
                    field = ExtractedField(
                        value=date_str,
                        confidence=confidence,
                        page=block["page"],
                        bbox=block["bbox"],
                        method="regex",
                        raw_text=block["text"]
                    )
                    
                    if is_due_date and "due_date" not in result.fields:
                        result.fields["due_date"] = field
                    elif is_invoice_date and "invoice_date" not in result.fields:
                        result.fields["invoice_date"] = field
                    else:
                        date_candidates.append((date_obj, field))
                        
                except ValueError:
                    # Invalid date
                    pass
        
        # If no specific dates found, use heuristics
        if "invoice_date" not in result.fields and date_candidates:
            # Earliest date is likely invoice date
            date_candidates.sort(key=lambda x: x[0])
            result.fields["invoice_date"] = date_candidates[0][1]
            
        if "due_date" not in result.fields and len(date_candidates) > 1:
            # Latest date is likely due date
            result.fields["due_date"] = date_candidates[-1][1]
    
    async def _extract_business_identifiers(self, text_blocks: List[Dict], result: Tier1Result):
        """Extract SIREN, SIRET, and TVA numbers"""
        for block in text_blocks:
            text = block["text"]
            
            # SIRET (includes SIREN)
            siret_match = self.patterns.SIRET_PATTERN.search(text)
            if siret_match:
                siret = siret_match.group(1).replace(" ", "").replace("-", "")
                if len(siret) == 14:
                    result.fields["siret"] = ExtractedField(
                        value=siret,
                        confidence=0.95,
                        page=block["page"],
                        bbox=block["bbox"],
                        method="regex",
                        raw_text=text
                    )
                    # Extract SIREN from SIRET
                    result.fields["siren"] = ExtractedField(
                        value=siret[:9],
                        confidence=0.95,
                        page=block["page"],
                        bbox=block["bbox"],
                        method="regex",
                        raw_text=text
                    )
                    continue
            
            # SIREN only
            siren_match = self.patterns.SIREN_PATTERN.search(text)
            if siren_match and "siren" not in result.fields:
                siren = siren_match.group(1).replace(" ", "").replace("-", "")
                if len(siren) == 9:
                    result.fields["siren"] = ExtractedField(
                        value=siren,
                        confidence=0.9,
                        page=block["page"],
                        bbox=block["bbox"],
                        method="regex",
                        raw_text=text
                    )
            
            # TVA number
            tva_match = self.patterns.TVA_PATTERN.search(text)
            if tva_match and "tva_number" not in result.fields:
                tva = tva_match.group(1).replace(" ", "").upper()
                result.fields["tva_number"] = ExtractedField(
                    value=tva,
                    confidence=0.95,
                    page=block["page"],
                    bbox=block["bbox"],
                    method="regex",
                    raw_text=text
                )
    
    async def _extract_amounts(self, text_blocks: List[Dict], result: Tier1Result):
        """Extract monetary amounts"""
        amount_candidates = []
        
        for block in text_blocks:
            text = block["text"]
            text_lower = text.lower()
            
            # Find all amount matches
            for pattern in self.patterns.AMOUNT_PATTERNS:
                matches = pattern.findall(text)
                
                for match in matches:
                    # Handle tuple results from findall
                    amount_str = match[0] if isinstance(match, tuple) else match
                    
                    # Parse French number format
                    try:
                        amount = self._parse_french_amount(amount_str)
                        
                        # Determine amount type based on context
                        is_total = any(keyword in text_lower for keyword in self.patterns.TOTAL_KEYWORDS)
                        is_subtotal = any(keyword in text_lower for keyword in self.patterns.SUBTOTAL_KEYWORDS)
                        is_tva = any(keyword in text_lower for keyword in self.patterns.TVA_KEYWORDS)
                        
                        confidence = 0.9 if (is_total or is_subtotal or is_tva) else 0.6
                        
                        field = ExtractedField(
                            value=float(amount),
                            confidence=confidence,
                            page=block["page"],
                            bbox=block["bbox"],
                            method="regex",
                            raw_text=text
                        )
                        
                        if is_total and "total_ttc" not in result.fields:
                            result.fields["total_ttc"] = field
                        elif is_subtotal and "total_ht" not in result.fields:
                            result.fields["total_ht"] = field
                        elif is_tva and "total_tva" not in result.fields:
                            result.fields["total_tva"] = field
                        else:
                            amount_candidates.append((amount, field, text_lower))
                            
                    except (ValueError, InvalidOperation):
                        continue
        
        # Use heuristics for remaining amounts
        if amount_candidates:
            amount_candidates.sort(key=lambda x: x[0], reverse=True)
            
            if "total_ttc" not in result.fields and amount_candidates:
                # Largest amount is likely total TTC
                result.fields["total_ttc"] = amount_candidates[0][1]
    
    async def _extract_entities(self, text_blocks: List[Dict], result: Tier1Result):
        """Extract vendor and customer information"""
        # Group text blocks by proximity
        page_blocks = {}
        for block in text_blocks:
            page = block["page"]
            if page not in page_blocks:
                page_blocks[page] = []
            page_blocks[page].append(block)
        
        # Look for vendor and customer sections
        for page, blocks in page_blocks.items():
            # Sort blocks by vertical position
            blocks.sort(key=lambda b: b["bbox"][1])
            
            vendor_section = []
            customer_section = []
            
            for i, block in enumerate(blocks):
                text_lower = block["text"].lower()
                
                # Check for vendor keywords
                if any(keyword in text_lower for keyword in self.patterns.VENDOR_KEYWORDS):
                    # Collect next few blocks as vendor info
                    vendor_section = blocks[i:i+5]
                    
                # Check for customer keywords
                if any(keyword in text_lower for keyword in self.patterns.CUSTOMER_KEYWORDS):
                    # Collect next few blocks as customer info
                    customer_section = blocks[i:i+5]
            
            # Extract vendor name from section
            if vendor_section and "vendor_name" not in result.fields:
                # First non-keyword line is likely the name
                for block in vendor_section[1:]:
                    text = block["text"].strip()
                    if text and not any(kw in text.lower() for kw in self.patterns.VENDOR_KEYWORDS):
                        result.fields["vendor_name"] = ExtractedField(
                            value=text,
                            confidence=0.7,
                            page=page,
                            bbox=block["bbox"],
                            method="keyword",
                            raw_text=text
                        )
                        break
            
            # Extract customer name from section
            if customer_section and "customer_name" not in result.fields:
                # First non-keyword line is likely the name
                for block in customer_section[1:]:
                    text = block["text"].strip()
                    if text and not any(kw in text.lower() for kw in self.patterns.CUSTOMER_KEYWORDS):
                        result.fields["customer_name"] = ExtractedField(
                            value=text,
                            confidence=0.7,
                            page=page,
                            bbox=block["bbox"],
                            method="keyword",
                            raw_text=text
                        )
                        break
    
    def _parse_french_amount(self, amount_str: str) -> Decimal:
        """Parse French number format (1 234,56) to Decimal"""
        # Remove spaces (thousand separator)
        amount_str = amount_str.replace(" ", "").replace("\u00A0", "")
        # Replace comma with dot for decimal
        amount_str = amount_str.replace(",", ".")
        return Decimal(amount_str)
    
    def _calculate_confidence_summary(self, result: Tier1Result):
        """Calculate confidence summary for all fields"""
        if not result.fields:
            result.confidence_summary = {"overall": 0.0}
            return
            
        total_confidence = 0.0
        field_count = 0
        
        for field_name, field in result.fields.items():
            result.confidence_summary[field_name] = field.confidence
            total_confidence += field.confidence
            field_count += 1
        
        result.confidence_summary["overall"] = total_confidence / field_count if field_count > 0 else 0.0