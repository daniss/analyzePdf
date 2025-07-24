import os
import tempfile
from typing import List, Union
from PIL import Image
import pypdfium2 as pdfium
from pdf2image import convert_from_path
import aiofiles
import base64
from io import BytesIO

from core.config import settings


class PDFProcessor:
    """Handles PDF to image conversion for Claude 4 vision processing"""
    
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
    async def process_uploaded_file(file_content: bytes, filename: str) -> List[str]:
        """
        Process an uploaded file (PDF or image) and return base64 encoded images.
        Returns a list of base64 strings ready for Claude 4 vision API.
        """
        file_extension = os.path.splitext(filename)[1].lower()
        
        if file_extension == '.pdf':
            # Save PDF temporarily
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name
            
            try:
                # Convert PDF pages to images
                images = await PDFProcessor.pdf_to_images(tmp_path)
                
                # Convert images to base64
                base64_images = []
                for img in images:
                    buffered = BytesIO()
                    img.save(buffered, format="PNG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    base64_images.append(img_base64)
                
                return base64_images
                
            finally:
                # Clean up temporary file
                os.unlink(tmp_path)
                
        elif file_extension in ['.jpg', '.jpeg', '.png']:
            # Handle image files directly
            img = Image.open(BytesIO(file_content))
            
            # Convert to PNG for consistency
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            return [img_base64]
        
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