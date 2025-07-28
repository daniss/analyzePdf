import os
import tempfile
from typing import List, Union, Tuple, Optional
from PIL import Image
import pypdfium2 as pdfium
from pdf2image import convert_from_path
import aiofiles
import base64
from io import BytesIO
import pdfplumber
import re
import logging

from core.config import settings

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class PDFProcessor:
    """Handles PDF processing with smart text extraction before falling back to vision processing"""
    
    @staticmethod
    async def pdf_to_images(pdf_path: str) -> List[Image.Image]:
        """
        Convert PDF pages to PIL Image objects.
        Uses pypdfium2 for better performance and quality.
        """
        images = []
        
        try:
            # Load PDF
            pdf = pdfium.PdfDocument(pdf_path)
            n_pages = min(len(pdf), settings.MAX_PAGES)
            
            for page_index in range(n_pages):
                page = pdf[page_index]
                
                # Render page to PIL Image
                bitmap = page.render(
                    scale=settings.PDF_DPI / 72,  # 72 is the default PDF DPI
                    rotation=0,
                )
                pil_image = bitmap.to_pil()
                images.append(pil_image)
            
            pdf.close()
            
        except Exception as e:
            # Fallback to pdf2image if pypdfium2 fails
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
    
    @staticmethod
    def extract_structured_data_from_pdf(pdf_path: str) -> dict:
        """Extract structured data including text, positions, tables from PDF using pdfplumber"""
        logger.info(f"Starting structured extraction from PDF: {pdf_path}")
        print(f"🔍 PDFPlumber: Starting structured extraction from {pdf_path}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"PDF opened successfully, {len(pdf.pages)} pages found")
                print(f"📄 PDFPlumber: PDF opened, {len(pdf.pages)} pages found")
                
                # Collect all structured data
                structured_data = {
                    "text_content": "",
                    "pages": [],
                    "tables": [],
                    "words_with_positions": [],
                    "metadata": {
                        "total_pages": len(pdf.pages),
                        "page_dimensions": []
                    }
                }
                
                max_pages = min(len(pdf.pages), settings.MAX_PAGES)
                logger.info(f"Processing first {max_pages} pages")
                
                for i, page in enumerate(pdf.pages[:max_pages]):
                    page_data = {
                        "page_number": i + 1,
                        "text": page.extract_text() or "",
                        "words": page.extract_words(),
                        "tables": page.extract_tables(),
                        "chars": len(page.chars),
                        "bbox": page.bbox  # Page bounding box
                    }
                    
                    print(f"📝 PDFPlumber: Page {i+1} structured analysis:")
                    print(f"  • Dimensions: {page.width:.1f} x {page.height:.1f}")
                    print(f"  • Characters: {len(page.chars)}")
                    print(f"  • Words: {len(page_data['words'])}")
                    print(f"  • Tables: {len(page_data['tables'])}")
                    
                    # Show detailed word positions for debugging
                    words = page_data['words']
                    if words:
                        print(f"  • Word positions (first 10 words):")
                        for j, word in enumerate(words[:10]):
                            print(f"    [{j:2d}] '{word['text']}' -> x:{word['x0']:.1f}-{word['x1']:.1f}, y:{word['top']:.1f}-{word['bottom']:.1f}")
                        
                        # Look for key invoice terms and show their positions
                        key_terms = [
                            # French terms
                            'facture', 'total', 'montant', 'tva', 'date', 'n°', 'numéro', 'ttc', 'ht',
                            # English terms  
                            'invoice', 'bill', 'receipt', 'total', 'amount', 'tax', 'vat', 'date', 'number'
                        ]
                        found_terms = []
                        for word in words:
                            word_lower = word['text'].lower()
                            if any(term in word_lower for term in key_terms):
                                found_terms.append(word)
                        
                        if found_terms:
                            print(f"  • Key invoice terms found:")
                            for word in found_terms:
                                print(f"    🎯 '{word['text']}' at x:{word['x0']:.1f}, y:{word['top']:.1f}")
                        
                        # Find potential amount patterns (multi-currency)
                        amount_words = []
                        currency_symbols = ['€', '$', '£', 'EUR', 'USD', 'GBP', 'CAD', 'AUD']
                        for word in words:
                            text = word['text']
                            has_currency = any(symbol in text for symbol in currency_symbols)
                            has_number_format = (any(c.isdigit() for c in text) and (',' in text or '.' in text))
                            
                            if has_currency or has_number_format:
                                amount_words.append(word)
                        
                        if amount_words:
                            print(f"  • Potential amounts:")
                            for word in amount_words:
                                print(f"    💰 '{word['text']}' at x:{word['x0']:.1f}, y:{word['top']:.1f}")
                    
                    # Show detailed table structure if found
                    tables = page_data['tables']
                    if tables:
                        for t_idx, table in enumerate(tables):
                            print(f"  • Table {t_idx + 1} structure: {len(table)} rows")
                            if table and table[0]:
                                print(f"    - Columns: {len(table[0])}")
                                print(f"    - First row: {table[0][:3]}..." if len(table[0]) > 3 else f"    - First row: {table[0]}")
                                if len(table) > 1:
                                    print(f"    - Second row: {table[1][:3]}..." if len(table[1]) > 3 else f"    - Second row: {table[1]}")
                    
                    # Add page text to combined content
                    if page_data["text"]:
                        structured_data["text_content"] += page_data["text"] + "\n"
                    
                    # Store page data
                    structured_data["pages"].append(page_data)
                    structured_data["tables"].extend(page_data["tables"])
                    structured_data["words_with_positions"].extend(page_data["words"])
                    structured_data["metadata"]["page_dimensions"].append({
                        "page": i + 1,
                        "width": page.width,
                        "height": page.height
                    })
                
                structured_data["text_content"] = structured_data["text_content"].strip()
                
                print(f"📊 PDFPlumber: Structured extraction complete:")
                print(f"  • Total text: {len(structured_data['text_content'])} characters")
                print(f"  • Total words: {len(structured_data['words_with_positions'])}")
                print(f"  • Total tables: {len(structured_data['tables'])}")
                
                return structured_data
                
        except Exception as e:
            logger.error(f"Error extracting structured data from PDF: {str(e)}")
            print(f"❌ PDFPlumber: Error - {str(e)}")
            return {"text_content": "", "pages": [], "tables": [], "words_with_positions": [], "metadata": {}}
    
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """Extract text from PDF using pdfplumber"""
        logger.info(f"Starting text extraction from PDF: {pdf_path}")
        print(f"🔍 PDFPlumber: Starting text extraction from {pdf_path}")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"PDF opened successfully, {len(pdf.pages)} pages found")
                print(f"📄 PDFPlumber: PDF opened, {len(pdf.pages)} pages found")
                text_content = ""
                # Limit to first few pages for text extraction test
                max_pages = min(len(pdf.pages), settings.MAX_PAGES)
                logger.info(f"Processing first {max_pages} pages")
                
                for i, page in enumerate(pdf.pages[:max_pages]):
                    logger.info(f"Extracting text from page {i+1}/{max_pages}")
                    
                    # Extract text with basic method
                    page_text = page.extract_text()
                    
                    # Extract structured data with positions
                    chars = page.chars  # Individual characters with positions
                    words = page.extract_words()  # Words with bounding boxes
                    tables = page.extract_tables()  # Tables if any
                    
                    print(f"📝 PDFPlumber: Page {i+1} analysis:")
                    print(f"  • Characters found: {len(chars)}")
                    print(f"  • Words found: {len(words)}")
                    print(f"  • Tables found: {len(tables)}")
                    
                    # Show detailed word positions for debugging
                    if words:
                        print(f"  • Word positions (first 10 words):")
                        for j, word in enumerate(words[:10]):
                            print(f"    [{j:2d}] '{word['text']}' -> x:{word['x0']:.1f}-{word['x1']:.1f}, y:{word['top']:.1f}-{word['bottom']:.1f}")
                        
                        # Look for key invoice terms and show their positions
                        key_terms = [
                            # French terms
                            'facture', 'total', 'montant', 'tva', 'date', 'n°', 'numéro', 'ttc', 'ht',
                            # English terms  
                            'invoice', 'bill', 'receipt', 'total', 'amount', 'tax', 'vat', 'date', 'number'
                        ]
                        print(f"  • Key invoice terms found:")
                        for word in words:
                            word_lower = word['text'].lower()
                            if any(term in word_lower for term in key_terms):
                                print(f"    🎯 '{word['text']}' at x:{word['x0']:.1f}, y:{word['top']:.1f}")
                        
                        # Find potential amount patterns (numbers with € or EUR)
                        print(f"  • Potential amounts:")
                        for word in words:
                            text = word['text']
                            if any(char in text for char in ['€', '€', 'EUR', '€']) or (any(c.isdigit() for c in text) and ',' in text):
                                print(f"    💰 '{text}' at x:{word['x0']:.1f}, y:{word['top']:.1f}")
                    
                    # Show table structure if found
                    if tables:
                        print(f"  • Table structure: {len(tables[0])} rows x {len(tables[0][0]) if tables[0] else 0} cols")
                    
                    if page_text:
                        page_char_count = len(page_text)
                        logger.info(f"Page {i+1}: extracted {page_char_count} characters")
                        print(f"  • Text extracted: {page_char_count} characters")
                        text_content += page_text + "\n"
                        
                        # Log first 200 characters of each page for debugging
                        preview = page_text[:200].replace('\n', ' ').strip()
                        logger.info(f"Page {i+1} preview: {preview}...")
                        print(f"  • Preview: {preview}...")
                    else:
                        logger.warning(f"Page {i+1}: no text extracted")
                        print(f"  ⚠️ No text extracted from page {i+1}")
                
                final_text = text_content.strip()
                logger.info(f"Total text extracted: {len(final_text)} characters")
                print(f"📊 PDFPlumber: Total extracted {len(final_text)} characters")
                
                if final_text:
                    # Log full text for debugging (first 500 chars)
                    preview = final_text[:500].replace('\n', ' ').strip()
                    logger.info(f"Full text preview (first 500 chars): {preview}...")
                    print(f"📖 PDFPlumber: Full text preview: {preview}...")
                
                return final_text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return ""
    
    @staticmethod
    def is_clean_extraction(structured_data: dict) -> bool:
        """Enhanced validation using both text and position data to determine extraction quality"""
        text = structured_data.get("text_content", "")
        words = structured_data.get("words_with_positions", [])
        pages = structured_data.get("pages", [])
        
        print(f"\n🔍 ENHANCED EXTRACTION QUALITY CHECK:")
        print(f"  • Text length: {len(text)} characters")
        print(f"  • Words with positions: {len(words)}")
        print(f"  • Pages analyzed: {len(pages)}")
        
        # 1. Basic text length check
        if not text or len(text.strip()) < 50:
            print(f"  ❌ FAIL: Text too short ({len(text)} chars, need ≥50)")
            return False
        
        # 2. Word count validation - good extraction should have reasonable word density
        if len(words) < 15:
            print(f"  ❌ FAIL: Too few words extracted ({len(words)}, need ≥15)")
            return False
        
        # 3. Enhanced invoice field detection using positions (French + English)
        invoice_score = 0
        required_fields = {
            'invoice_number': [
                # French
                'facture', 'n°', 'numéro', 'fact',
                # English
                'invoice', 'inv', 'bill', 'receipt', 'number', '#'
            ],
            'date': [
                # French
                'date', 'émis', 'émission',
                # English
                'date', 'issued', 'created', 'billed'
            ],
            'amounts': [
                # French
                'total', 'montant', '€', 'eur', 'ttc', 'ht', 'sous-total',
                # English
                'total', 'amount', 'sum', 'subtotal', 'sub-total', '$', 'usd', 'gbp', '£'
            ],
            'tax': [
                # French
                'tva', 'taxe',
                # English
                'tax', 'vat', 'gst', 'hst', 'sales tax'
            ],
            'vendor_info': [
                # French
                'siren', 'siret', 'entreprise', 'société',
                # English
                'company', 'corp', 'corporation', 'ltd', 'llc', 'inc', 'business'
            ]
        }
        
        detected_fields = {}
        text_lower = text.lower()
        
        for field_type, patterns in required_fields.items():
            field_found = False
            found_words = []
            
            for pattern in patterns:
                # Check in text
                if re.search(pattern, text_lower):
                    field_found = True
                
                # Check in positioned words for better validation
                for word in words:
                    if pattern in word['text'].lower():
                        found_words.append(word)
            
            if field_found:
                invoice_score += 1
                detected_fields[field_type] = found_words
                print(f"    ✅ {field_type}: Found {len(found_words)} positioned matches")
            else:
                print(f"    ❌ {field_type}: Not found")
        
        print(f"  • Invoice field score: {invoice_score}/5")
        
        # Need at least 3/5 invoice fields detected
        if invoice_score < 3:
            print(f"  ❌ FAIL: Insufficient invoice fields ({invoice_score}/5, need ≥3)")
            return False
        
        # 4. Text quality analysis
        total_chars = len(text)
        alphanumeric_chars = sum(1 for c in text if c.isalnum())
        alphanumeric_ratio = alphanumeric_chars / total_chars if total_chars > 0 else 0
        
        print(f"  • Character quality: {alphanumeric_ratio:.1%} alphanumeric")
        
        if alphanumeric_ratio < 0.6:
            print(f"  ❌ FAIL: Poor character quality ({alphanumeric_ratio:.1%}, need ≥60%)")
            return False
        
        # 5. OCR artifact detection
        repeated_char_pattern = r'([^\s])\1{4,}'
        repeated_matches = re.findall(repeated_char_pattern, text)
        
        print(f"  • OCR artifacts: {len(repeated_matches)} repeated patterns")
        
        if len(repeated_matches) > 3:
            print(f"  ❌ FAIL: Too many OCR artifacts ({len(repeated_matches)}, max 3)")
            return False
        
        # 6. Spatial consistency check (if words are positioned reasonably)
        if words:
            # Check if words have reasonable spatial distribution
            x_positions = [w['x0'] for w in words]
            y_positions = [w['top'] for w in words]
            
            x_range = max(x_positions) - min(x_positions)
            y_range = max(y_positions) - min(y_positions)
            
            print(f"  • Spatial spread: x={x_range:.1f}px, y={y_range:.1f}px")
            
            # Good invoices should have reasonable spatial distribution
            if x_range < 100 or y_range < 100:
                print(f"  ⚠️ WARNING: Limited spatial distribution (possible scan issue)")
                # Don't fail, but note the warning
        
        # 7. Advanced validation: Check for structured data patterns
        structured_score = 0
        
        # Look for amount patterns with positions (multi-currency)
        amount_patterns = []
        for word in words:
            text_word = word['text']
            # Multi-currency and format patterns:
            # French: 1,234.56 or 1 234,56 or 1234,56€
            # English: $1,234.56 or £1,234.56 or 1234.56 USD
            currency_pattern = re.search(r'\d+[\s,.]?\d*[,.]\d{2}', text_word)
            currency_symbols = ['€', '$', '£', 'EUR', 'USD', 'GBP', 'CAD', 'AUD']
            
            if currency_pattern or any(symbol in text_word for symbol in currency_symbols):
                amount_patterns.append(word)
        
        if amount_patterns:
            structured_score += 1
            print(f"    ✅ Found {len(amount_patterns)} amount patterns with positions")
        
        # Look for date patterns (multiple formats)
        date_patterns = []
        for word in words:
            text_word = word['text']
            # Multiple date formats:
            # DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY, DD.MM.YYYY
            # YYYY-MM-DD, Month DD, YYYY
            date_formats = [
                r'\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4}',  # DD/MM/YYYY or MM/DD/YYYY
                r'\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}',  # YYYY/MM/DD
                r'\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{4}',  # DD Month YYYY
                r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}'  # Month DD, YYYY
            ]
            
            if any(re.search(pattern, text_word.lower()) for pattern in date_formats):
                date_patterns.append(word)
        
        if date_patterns:
            structured_score += 1
            print(f"    ✅ Found {len(date_patterns)} date patterns with positions")
        
        print(f"  • Structure score: {structured_score}/2")
        
        # Final decision
        total_score = invoice_score + structured_score
        max_score = 7  # 5 from invoice fields + 2 from structure
        
        print(f"  • FINAL SCORE: {total_score}/{max_score}")
        
        if total_score >= 5:  # Need good score to use text-only
            print(f"  ✅ EXTRACTION QUALITY: EXCELLENT - Using text-only Claude API (€0.005)")
            return True
        else:
            print(f"  ❌ EXTRACTION QUALITY: INSUFFICIENT - Falling back to vision processing (€0.03)")
            return False
    
    @staticmethod
    def is_clean_text(text: str) -> bool:
        """Determine if extracted text is clean enough for text-only Claude processing"""
        if not text or len(text.strip()) < 50:
            return False
        
        # Check for basic invoice indicators in French
        invoice_indicators = [
            r'facture|invoice',
            r'num[ée]ro|number|n°',
            r'date',
            r'montant|total|amount',
            r'€|euro|eur',
            r'tva|tax|ht|ttc'
        ]
        
        text_lower = text.lower()
        found_indicators = 0
        
        for pattern in invoice_indicators:
            if re.search(pattern, text_lower):
                found_indicators += 1
        
        # Need at least 3 invoice indicators
        if found_indicators < 3:
            return False
        
        # Check text quality - should have reasonable character distribution
        total_chars = len(text)
        alphanumeric_chars = sum(1 for c in text if c.isalnum())
        alphanumeric_ratio = alphanumeric_chars / total_chars if total_chars > 0 else 0
        
        # At least 60% of text should be alphanumeric (good OCR quality)
        if alphanumeric_ratio < 0.6:
            return False
        
        # Check for excessive repeated characters (OCR artifacts)
        repeated_char_pattern = r'([^\s])\1{4,}'  # Same char repeated 5+ times
        if len(re.findall(repeated_char_pattern, text)) > 3:
            return False
        
        return True
    
    @staticmethod
    async def process_uploaded_file(file_content: bytes, filename: str) -> Tuple[Optional[str], List[str]]:
        """
        Process an uploaded file (PDF or image).
        For PDFs: First tries text extraction, falls back to image processing if text is poor quality.
        For images: Always returns images for vision processing.
        
        Returns:
            Tuple[Optional[str], List[str]]: (extracted_text, base64_images)
            - If text is clean: (text, [])
            - If text is poor or file is image: (None, [base64_images])
        """
        file_extension = os.path.splitext(filename)[1].lower()
        
        if file_extension == '.pdf':
            # Save PDF temporarily
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name
            
            try:
                # First, try structured extraction (includes text + positions)
                structured_data = PDFProcessor.extract_structured_data_from_pdf(tmp_path)
                extracted_text = structured_data["text_content"]
                
                # Log additional structured data for debugging
                if structured_data["tables"]:
                    print(f"📋 Found {len(structured_data['tables'])} tables in PDF")
                if structured_data["words_with_positions"]:
                    print(f"📍 Found {len(structured_data['words_with_positions'])} positioned words")
                
                if PDFProcessor.is_clean_extraction(structured_data):
                    logger.info(f"✅ {filename}: Clean text extracted, using text-only Claude API (cost: €0.005)")
                    print(f"✅ {filename}: Clean text → Claude Text API (€0.005)")
                    return (extracted_text, [])
                else:
                    logger.info(f"⚠️ {filename}: Poor text quality, falling back to vision processing (cost: €0.03)")
                    print(f"⚠️ {filename}: Poor text → Claude Vision API (€0.03)")
                    # Convert PDF pages to images as fallback
                    images = await PDFProcessor.pdf_to_images(tmp_path)
                    
                    # Convert images to base64
                    base64_images = []
                    for img in images:
                        buffered = BytesIO()
                        img.save(buffered, format="PNG")
                        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        base64_images.append(img_base64)
                    
                    return (None, base64_images)
                
            finally:
                # Clean up temporary file
                os.unlink(tmp_path)
                
        elif file_extension in ['.jpg', '.jpeg', '.png']:
            # Handle image files directly - always use vision processing
            logger.info(f"{filename}: Image file detected, using vision processing (cost: €0.03)")
            img = Image.open(BytesIO(file_content))
            
            # Convert to PNG for consistency
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            logger.info(f"{filename}: Converted to base64, {len(img_base64)} characters")
            return (None, [img_base64])
        
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    @staticmethod
    def estimate_tokens(images: List[str]) -> int:
        """
        Estimate token usage for Claude 4 vision API.
        Claude uses approximately 1,000 tokens per image at high detail.
        """
        # Base tokens for the prompt
        base_tokens = 500
        
        # Approximately 1000 tokens per image for Claude vision
        image_tokens = len(images) * 1000
        
        return base_tokens + image_tokens
    
    @staticmethod
    async def extract_text_from_images(base64_images: List[str]) -> str:
        """
        Extract text from images using OCR as fallback when vision API is not available.
        """
        try:
            import pytesseract
            from PIL import Image
            import base64
            import io
            
            logger.info(f"Starting OCR text extraction from {len(base64_images)} images")
            
            extracted_text = ""
            
            for i, img_base64 in enumerate(base64_images):
                try:
                    # Decode base64 image
                    img_data = base64.b64decode(img_base64)
                    img = Image.open(io.BytesIO(img_data))
                    
                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Extract text using Tesseract OCR
                    page_text = pytesseract.image_to_string(img, lang='eng+fra')
                    
                    if page_text.strip():
                        extracted_text += f"Page {i + 1}:\n{page_text}\n\n"
                        logger.info(f"OCR extracted {len(page_text)} characters from page {i + 1}")
                    
                except Exception as e:
                    logger.warning(f"OCR failed for page {i + 1}: {str(e)}")
                    continue
            
            if extracted_text.strip():
                logger.info(f"OCR extraction completed: {len(extracted_text)} total characters")
                return extracted_text.strip()
            else:
                logger.warning("OCR extraction produced no text")
                return ""
                
        except ImportError:
            logger.error("Tesseract OCR not available - install pytesseract and tesseract-ocr")
            return ""
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return ""