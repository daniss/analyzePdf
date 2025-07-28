import os
import tempfile
import re
from typing import List, Dict, Any, Optional, Tuple, Union
from PIL import Image
import pypdfium2 as pdfium
from pdf2image import convert_from_path
import aiofiles
import base64
from io import BytesIO
import json
import logging
from datetime import datetime

# Text extraction libraries
import pdfplumber
import PyPDF2
import pytesseract
from pytesseract import Output

from core.config import settings

logger = logging.getLogger(__name__)


class TextElement:
    """Represents a text element with position information"""
    
    def __init__(self, text: str, x: float, y: float, width: float, height: float, page: int = 0):
        self.text = text.strip()
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.page = page
        self.confidence = 1.0  # Default confidence for native text
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "bbox": {"x": self.x, "y": self.y, "width": self.width, "height": self.height},
            "page": self.page,
            "confidence": self.confidence
        }


class InvoiceFieldExtractor:
    """Pre-processes text to identify potential invoice fields"""
    
    # French invoice patterns
    PATTERNS = {
        "invoice_number": [
            r"(?:Facture|FACTURE|Invoice)\s*(?:n°|N°|#|:)?\s*([A-Z0-9\-/]+)",
            r"N°\s*(?:de\s*)?facture\s*:?\s*([A-Z0-9\-/]+)",
            r"Numéro\s*:?\s*([A-Z0-9\-/]+)"
        ],
        "date": [
            r"Date\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
            r"(?:Émise?\s*le|Date\s*d'émission)\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
            r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})"
        ],
        "siren": [
            r"SIREN\s*:?\s*(\d{3}\s?\d{3}\s?\d{3})",
            r"SIREN\s*:?\s*(\d{9})"
        ],
        "siret": [
            r"SIRET\s*:?\s*(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})",
            r"SIRET\s*:?\s*(\d{14})"
        ],
        "tva_number": [
            r"TVA\s*:?\s*(FR\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{3})",
            r"N°\s*TVA\s*:?\s*(FR\d{11})",
            r"TVA\s*(?:Intracom(?:munautaire)?|Intracommunautaire)\s*:?\s*(FR\d{11})"
        ],
        "amount_ht": [
            r"(?:Total|Montant)\s*HT\s*:?\s*([\d\s]+[,\.]\d{2})\s*€?",
            r"(?:Sous-total|Subtotal)\s*:?\s*([\d\s]+[,\.]\d{2})\s*€?"
        ],
        "amount_tva": [
            r"TVA\s*(?:20|10|5\.5|2\.1)\s*%?\s*:?\s*([\d\s]+[,\.]\d{2})\s*€?",
            r"Montant\s*TVA\s*:?\s*([\d\s]+[,\.]\d{2})\s*€?"
        ],
        "amount_ttc": [
            r"(?:Total|Montant)\s*TTC\s*:?\s*([\d\s]+[,\.]\d{2})\s*€?",
            r"(?:Net\s*à\s*payer|À\s*payer)\s*:?\s*([\d\s]+[,\.]\d{2})\s*€?"
        ],
        "postal_code": [
            r"\b(\d{5})\b\s*[A-Z][a-z]+"  # French postal code before city
        ]
    }
    
    @staticmethod
    def extract_fields(text_elements: List[TextElement]) -> Dict[str, List[Dict[str, Any]]]:
        """Extract potential invoice fields from text elements"""
        extracted_fields = {}
        
        # Concatenate all text for pattern matching
        full_text = " ".join([elem.text for elem in text_elements if elem.text])
        
        # Search for each field type
        for field_name, patterns in InvoiceFieldExtractor.PATTERNS.items():
            extracted_fields[field_name] = []
            
            for pattern in patterns:
                matches = re.finditer(pattern, full_text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    # Find the text element containing this match
                    match_start = match.start()
                    match_text = match.group(1) if match.groups() else match.group(0)
                    
                    # Find corresponding text element
                    char_count = 0
                    for elem in text_elements:
                        elem_length = len(elem.text) + 1  # +1 for space
                        if char_count <= match_start < char_count + elem_length:
                            extracted_fields[field_name].append({
                                "value": match_text.strip(),
                                "bbox": elem.to_dict()["bbox"],
                                "page": elem.page,
                                "confidence": elem.confidence,
                                "pattern": pattern
                            })
                            break
                        char_count += elem_length
        
        return extracted_fields
    
    @staticmethod
    def identify_table_structure(text_elements: List[TextElement]) -> List[Dict[str, Any]]:
        """Identify potential table structures (line items)"""
        tables = []
        
        # Group elements by vertical position (rows)
        rows_by_page = {}
        for elem in text_elements:
            if elem.page not in rows_by_page:
                rows_by_page[elem.page] = {}
            
            # Group by approximate Y position (within 5 pixels)
            y_key = round(elem.y / 5) * 5
            if y_key not in rows_by_page[elem.page]:
                rows_by_page[elem.page][y_key] = []
            rows_by_page[elem.page][y_key].append(elem)
        
        # Analyze rows for table patterns
        for page, rows in rows_by_page.items():
            sorted_rows = sorted(rows.items(), key=lambda x: x[0])
            
            for y_pos, elements in sorted_rows:
                # Sort elements by X position
                sorted_elements = sorted(elements, key=lambda x: x.x)
                
                # Check if this looks like a line item
                if len(sorted_elements) >= 3:  # At least description, quantity, amount
                    row_text = " ".join([elem.text for elem in sorted_elements])
                    
                    # Look for line item patterns
                    if any(keyword in row_text.lower() for keyword in ["€", "eur", ","]):
                        # Try to parse as line item
                        line_item = InvoiceFieldExtractor._parse_line_item(sorted_elements)
                        if line_item:
                            tables.append({
                                "type": "line_item",
                                "data": line_item,
                                "page": page,
                                "y_position": y_pos
                            })
        
        return tables
    
    @staticmethod
    def _parse_line_item(elements: List[TextElement]) -> Optional[Dict[str, Any]]:
        """Parse elements as a potential line item"""
        if len(elements) < 3:
            return None
        
        # Common line item structure: Description | Quantity | Unit Price | Total
        line_item = {
            "description": "",
            "quantity": None,
            "unit_price": None,
            "total": None,
            "tva_rate": None
        }
        
        # Simple heuristic: first element is description, look for numbers in others
        line_item["description"] = elements[0].text
        
        # Look for numeric values
        for elem in elements[1:]:
            text = elem.text.replace(" ", "").replace(",", ".")
            
            # Check for percentage (TVA rate)
            if "%" in text:
                try:
                    rate = float(text.replace("%", ""))
                    if rate in [20.0, 10.0, 5.5, 2.1]:
                        line_item["tva_rate"] = rate
                except:
                    pass
            
            # Check for currency amounts
            elif "€" in text or re.match(r"^\d+[.,]\d{2}$", text):
                try:
                    amount = float(text.replace("€", "").strip())
                    # Assume larger amounts are totals
                    if line_item["total"] is None or amount > line_item["total"]:
                        if line_item["total"] is not None:
                            line_item["unit_price"] = line_item["total"]
                        line_item["total"] = amount
                except:
                    pass
            
            # Check for quantities (integers or decimals without currency)
            elif re.match(r"^\d+[.,]?\d*$", text) and len(text) <= 5:
                try:
                    line_item["quantity"] = float(text)
                except:
                    pass
        
        # Validate line item
        if line_item["description"] and (line_item["total"] or line_item["unit_price"]):
            return line_item
        
        return None


class EnhancedPDFProcessor:
    """Enhanced PDF processor with text extraction, OCR fallback, and pre-processing"""
    
    def __init__(self):
        self.logger = logger
    
    async def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process PDF with intelligent text extraction and pre-processing.
        
        Returns:
            Dict containing:
            - method: "native_text" or "ocr"
            - text_elements: List of text elements with positions
            - extracted_fields: Pre-identified invoice fields
            - tables: Identified table structures
            - images: Base64 images (only for OCR fallback)
            - pages_info: Information about each page
        """
        result = {
            "method": None,
            "text_elements": [],
            "extracted_fields": {},
            "tables": [],
            "images": [],
            "pages_info": [],
            "processing_time": {}
        }
        
        start_time = datetime.now()
        
        # Try native text extraction first
        self.logger.info(f"Attempting native text extraction for: {pdf_path}")
        text_elements = await self._extract_native_text(pdf_path)
        
        if text_elements and len(text_elements) > 10:  # Threshold for meaningful text
            result["method"] = "native_text"
            result["text_elements"] = [elem.to_dict() for elem in text_elements]
            self.logger.info(f"Successfully extracted {len(text_elements)} text elements natively")
        else:
            # Fall back to OCR
            self.logger.info("Native text extraction insufficient, falling back to OCR")
            result["method"] = "ocr"
            text_elements, images = await self._extract_with_ocr(pdf_path)
            result["text_elements"] = [elem.to_dict() for elem in text_elements]
            result["images"] = images
            self.logger.info(f"OCR extracted {len(text_elements)} text elements")
        
        # Pre-process extracted text
        if text_elements:
            # Extract potential invoice fields
            result["extracted_fields"] = InvoiceFieldExtractor.extract_fields(text_elements)
            
            # Identify table structures
            result["tables"] = InvoiceFieldExtractor.identify_table_structure(text_elements)
        
        # Add page information
        result["pages_info"] = await self._get_pages_info(pdf_path)
        
        # Calculate processing time
        result["processing_time"]["total_seconds"] = (datetime.now() - start_time).total_seconds()
        
        return result
    
    async def _extract_native_text(self, pdf_path: str) -> List[TextElement]:
        """Extract text with positions using pdfplumber (primary) or PyPDF2 (fallback)"""
        text_elements = []
        
        try:
            # Try pdfplumber first (better position extraction)
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract words with positions
                    words = page.extract_words(
                        x_tolerance=3,
                        y_tolerance=3,
                        keep_blank_chars=False
                    )
                    
                    for word in words:
                        if word.get("text", "").strip():
                            text_elements.append(TextElement(
                                text=word["text"],
                                x=word["x0"],
                                y=word["top"],
                                width=word["x1"] - word["x0"],
                                height=word["bottom"] - word["top"],
                                page=page_num
                            ))
                    
                    # Also extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        # Tables are returned as list of rows
                        for row_idx, row in enumerate(table):
                            for col_idx, cell in enumerate(row):
                                if cell:
                                    # Approximate position for table cells
                                    text_elements.append(TextElement(
                                        text=str(cell),
                                        x=col_idx * 100,  # Approximate
                                        y=row_idx * 20,   # Approximate
                                        width=100,
                                        height=20,
                                        page=page_num
                                    ))
        
        except Exception as e:
            self.logger.warning(f"pdfplumber extraction failed: {str(e)}, trying PyPDF2")
            
            # Fallback to PyPDF2
            try:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    
                    for page_num in range(min(len(pdf_reader.pages), settings.MAX_PAGES)):
                        page = pdf_reader.pages[page_num]
                        
                        # Extract text (without positions)
                        text = page.extract_text()
                        if text:
                            # Create approximate text elements by lines
                            lines = text.split('\n')
                            for line_idx, line in enumerate(lines):
                                if line.strip():
                                    text_elements.append(TextElement(
                                        text=line,
                                        x=0,
                                        y=line_idx * 20,
                                        width=500,
                                        height=20,
                                        page=page_num
                                    ))
            
            except Exception as e2:
                self.logger.error(f"Both text extraction methods failed: {str(e2)}")
        
        return text_elements
    
    async def _extract_with_ocr(self, pdf_path: str) -> Tuple[List[TextElement], List[str]]:
        """Extract text using OCR on converted images"""
        text_elements = []
        base64_images = []
        
        # Convert PDF to images
        images = await self._pdf_to_images(pdf_path)
        
        for page_num, image in enumerate(images):
            # Convert to base64 for API
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            base64_images.append(img_base64)
            
            # Perform OCR with pytesseract
            try:
                # Get detailed OCR data
                ocr_data = pytesseract.image_to_data(
                    image,
                    output_type=Output.DICT,
                    lang='fra+eng'  # French + English
                )
                
                # Extract text elements with positions
                n_boxes = len(ocr_data['text'])
                for i in range(n_boxes):
                    text = ocr_data['text'][i].strip()
                    if text and int(ocr_data['conf'][i]) > 30:  # Confidence threshold
                        elem = TextElement(
                            text=text,
                            x=ocr_data['left'][i],
                            y=ocr_data['top'][i],
                            width=ocr_data['width'][i],
                            height=ocr_data['height'][i],
                            page=page_num
                        )
                        elem.confidence = int(ocr_data['conf'][i]) / 100.0
                        text_elements.append(elem)
            
            except Exception as e:
                self.logger.error(f"OCR failed for page {page_num}: {str(e)}")
        
        return text_elements, base64_images
    
    async def _pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """Convert PDF pages to PIL Image objects (from original implementation)"""
        images = []
        
        try:
            pdf = pdfium.PdfDocument(pdf_path)
            n_pages = min(len(pdf), settings.MAX_PAGES)
            
            for page_index in range(n_pages):
                page = pdf[page_index]
                bitmap = page.render(
                    scale=settings.PDF_DPI / 72,
                    rotation=0,
                )
                pil_image = bitmap.to_pil()
                images.append(pil_image)
            
            pdf.close()
            
        except Exception as e:
            # Fallback to pdf2image
            try:
                images = convert_from_path(
                    pdf_path,
                    dpi=settings.PDF_DPI,
                    first_page=1,
                    last_page=settings.MAX_PAGES
                )
            except Exception as fallback_error:
                raise Exception(f"Failed to convert PDF: {str(e)}, Fallback error: {str(fallback_error)}")
        
        return images
    
    async def _get_pages_info(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Get information about PDF pages"""
        pages_info = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages[:settings.MAX_PAGES]):
                    pages_info.append({
                        "page_number": page_num,
                        "width": page.width,
                        "height": page.height,
                        "rotation": page.rotation or 0
                    })
        except:
            # Fallback: just count pages
            try:
                pdf = pdfium.PdfDocument(pdf_path)
                n_pages = min(len(pdf), settings.MAX_PAGES)
                for i in range(n_pages):
                    pages_info.append({
                        "page_number": i,
                        "width": 595,  # A4 default
                        "height": 842,
                        "rotation": 0
                    })
                pdf.close()
            except:
                pass
        
        return pages_info
    
    async def prepare_for_claude(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare processed data for Claude API, minimizing token usage.
        
        Returns a structured prompt and data for Claude.
        """
        # Create a condensed representation
        claude_data = {
            "extraction_method": processed_data["method"],
            "pages_count": len(processed_data["pages_info"]),
            "pre_extracted_fields": {},
            "text_content": "",
            "line_items_detected": []
        }
        
        # Include pre-extracted fields with highest confidence
        for field_name, matches in processed_data["extracted_fields"].items():
            if matches:
                # Sort by confidence and take the best match
                best_match = max(matches, key=lambda x: x.get("confidence", 0))
                claude_data["pre_extracted_fields"][field_name] = best_match["value"]
        
        # Include detected line items
        for table in processed_data["tables"]:
            if table["type"] == "line_item":
                claude_data["line_items_detected"].append(table["data"])
        
        # Create structured text content
        if processed_data["method"] == "native_text":
            # For native text, provide structured text by page
            text_by_page = {}
            for elem in processed_data["text_elements"]:
                page = elem["page"]
                if page not in text_by_page:
                    text_by_page[page] = []
                text_by_page[page].append(elem["text"])
            
            # Create readable text representation
            for page, texts in sorted(text_by_page.items()):
                claude_data["text_content"] += f"\n--- Page {page + 1} ---\n"
                claude_data["text_content"] += " ".join(texts)
        
        # Add confidence indicators
        claude_data["extraction_confidence"] = "high" if processed_data["method"] == "native_text" else "medium"
        
        # Add processing metadata
        claude_data["processing_time_seconds"] = processed_data["processing_time"]["total_seconds"]
        
        return claude_data
    
    @staticmethod
    async def process_uploaded_file(file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Process an uploaded file with enhanced extraction.
        Returns structured data ready for Claude processing.
        """
        processor = EnhancedPDFProcessor()
        file_extension = os.path.splitext(filename)[1].lower()
        
        if file_extension == '.pdf':
            # Save PDF temporarily
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name
            
            try:
                # Process with enhanced extraction
                processed_data = await processor.process_pdf(tmp_path)
                
                # Prepare for Claude
                claude_ready_data = await processor.prepare_for_claude(processed_data)
                
                # Include images only if OCR was used
                if processed_data["method"] == "ocr":
                    claude_ready_data["images"] = processed_data["images"]
                
                return {
                    "success": True,
                    "data": claude_ready_data,
                    "raw_extraction": processed_data  # Keep raw data for debugging
                }
                
            finally:
                # Clean up temporary file
                os.unlink(tmp_path)
                
        elif file_extension in ['.jpg', '.jpeg', '.png']:
            # Handle image files directly with OCR
            processor = EnhancedPDFProcessor()
            
            # Convert to PIL Image
            img = Image.open(BytesIO(file_content))
            
            # Perform OCR
            text_elements = []
            try:
                ocr_data = pytesseract.image_to_data(
                    img,
                    output_type=Output.DICT,
                    lang='fra+eng'
                )
                
                n_boxes = len(ocr_data['text'])
                for i in range(n_boxes):
                    text = ocr_data['text'][i].strip()
                    if text and int(ocr_data['conf'][i]) > 30:
                        elem = TextElement(
                            text=text,
                            x=ocr_data['left'][i],
                            y=ocr_data['top'][i],
                            width=ocr_data['width'][i],
                            height=ocr_data['height'][i],
                            page=0
                        )
                        elem.confidence = int(ocr_data['conf'][i]) / 100.0
                        text_elements.append(elem)
            except Exception as e:
                raise Exception(f"OCR failed for image: {str(e)}")
            
            # Convert image to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Process extracted text
            extracted_fields = InvoiceFieldExtractor.extract_fields(text_elements)
            tables = InvoiceFieldExtractor.identify_table_structure(text_elements)
            
            return {
                "success": True,
                "data": {
                    "extraction_method": "ocr",
                    "pages_count": 1,
                    "pre_extracted_fields": {
                        field: matches[0]["value"] if matches else None
                        for field, matches in extracted_fields.items()
                    },
                    "line_items_detected": [t["data"] for t in tables if t["type"] == "line_item"],
                    "images": [img_base64],
                    "extraction_confidence": "medium"
                }
            }
        
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    @staticmethod
    def estimate_tokens(claude_data: Dict[str, Any]) -> int:
        """
        Estimate token usage for Claude API based on prepared data.
        More accurate estimation for the enhanced processor.
        """
        tokens = 0
        
        # Base tokens for the prompt
        tokens += 500
        
        # Tokens for pre-extracted fields (much smaller than full OCR)
        tokens += len(json.dumps(claude_data.get("pre_extracted_fields", {}))) // 4
        
        # Tokens for line items
        tokens += len(json.dumps(claude_data.get("line_items_detected", []))) // 4
        
        # Tokens for text content (if native extraction)
        if "text_content" in claude_data:
            tokens += len(claude_data["text_content"]) // 4
        
        # Tokens for images (if OCR was used)
        if "images" in claude_data:
            # Approximately 1000 tokens per image for Claude vision
            tokens += len(claude_data["images"]) * 1000
        
        return tokens