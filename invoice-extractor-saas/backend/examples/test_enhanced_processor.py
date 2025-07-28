#!/usr/bin/env python3
"""
Example script to test the enhanced PDF processor.
This demonstrates the improved efficiency of the new processing pipeline.
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.enhanced_pdf_processor import EnhancedPDFProcessor
from core.pdf_processor import PDFProcessor


async def compare_processors(pdf_path: str):
    """Compare the original and enhanced PDF processors"""
    
    print(f"\n{'='*60}")
    print(f"Comparing PDF Processors for: {os.path.basename(pdf_path)}")
    print(f"{'='*60}\n")
    
    # Test original processor
    print("1. ORIGINAL PDF PROCESSOR")
    print("-" * 30)
    
    try:
        with open(pdf_path, 'rb') as f:
            file_content = f.read()
        
        original_processor = PDFProcessor()
        base64_images = await original_processor.process_uploaded_file(
            file_content, 
            os.path.basename(pdf_path)
        )
        
        original_tokens = PDFProcessor.estimate_tokens(base64_images)
        
        print(f"✓ Method: Image conversion (always)")
        print(f"✓ Pages converted: {len(base64_images)}")
        print(f"✓ Estimated tokens: {original_tokens}")
        print(f"✓ Estimated cost: ${original_tokens * 0.000015:.4f}")  # Claude pricing estimate
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    # Test enhanced processor
    print("\n2. ENHANCED PDF PROCESSOR")
    print("-" * 30)
    
    try:
        enhanced_processor = EnhancedPDFProcessor()
        result = await enhanced_processor.process_pdf(pdf_path)
        
        print(f"✓ Method: {result['method']}")
        print(f"✓ Text elements extracted: {len(result['text_elements'])}")
        print(f"✓ Processing time: {result['processing_time']['total_seconds']:.2f}s")
        
        # Show pre-extracted fields
        if result['extracted_fields']:
            print("\nPre-extracted fields:")
            for field, matches in result['extracted_fields'].items():
                if matches:
                    print(f"  - {field}: {matches[0]['value']}")
        
        # Show detected line items
        if result['tables']:
            line_items = [t for t in result['tables'] if t['type'] == 'line_item']
            print(f"\nLine items detected: {len(line_items)}")
            for i, item in enumerate(line_items[:3]):
                print(f"  - Item {i+1}: {item['data']['description'][:50]}...")
        
        # Prepare for Claude
        claude_data = await enhanced_processor.prepare_for_claude(result)
        enhanced_tokens = EnhancedPDFProcessor.estimate_tokens(claude_data)
        
        print(f"\n✓ Estimated tokens: {enhanced_tokens}")
        print(f"✓ Estimated cost: ${enhanced_tokens * 0.000015:.4f}")
        
        # Calculate savings
        if 'original_tokens' in locals():
            savings_tokens = original_tokens - enhanced_tokens
            savings_percent = (savings_tokens / original_tokens) * 100
            print(f"\n💰 TOKEN SAVINGS: {savings_tokens} tokens ({savings_percent:.1f}%)")
            print(f"💰 COST SAVINGS: ${savings_tokens * 0.000015:.4f}")
        
        # Show extraction confidence
        print(f"\n✓ Extraction confidence: {claude_data['extraction_confidence']}")
        
        # Save detailed results
        output_path = pdf_path.replace('.pdf', '_enhanced_result.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Detailed results saved to: {output_path}")
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_specific_features(pdf_path: str):
    """Test specific features of the enhanced processor"""
    
    print(f"\n{'='*60}")
    print("TESTING SPECIFIC FEATURES")
    print(f"{'='*60}\n")
    
    processor = EnhancedPDFProcessor()
    result = await processor.process_pdf(pdf_path)
    
    # Test French business number extraction
    print("1. French Business Number Extraction:")
    fields = result['extracted_fields']
    
    if fields.get('siren'):
        print(f"   ✓ SIREN: {fields['siren'][0]['value']}")
    if fields.get('siret'):
        print(f"   ✓ SIRET: {fields['siret'][0]['value']}")
    if fields.get('tva_number'):
        print(f"   ✓ TVA: {fields['tva_number'][0]['value']}")
    
    # Test amount extraction
    print("\n2. Financial Amount Extraction:")
    if fields.get('amount_ht'):
        print(f"   ✓ HT: {fields['amount_ht'][0]['value']}")
    if fields.get('amount_tva'):
        print(f"   ✓ TVA: {fields['amount_tva'][0]['value']}")
    if fields.get('amount_ttc'):
        print(f"   ✓ TTC: {fields['amount_ttc'][0]['value']}")
    
    # Test table/line item detection
    print(f"\n3. Table Structure Detection:")
    line_items = [t for t in result['tables'] if t['type'] == 'line_item']
    print(f"   ✓ Line items found: {len(line_items)}")
    
    total_from_items = sum(item['data'].get('total', 0) for item in line_items)
    print(f"   ✓ Total from line items: {total_from_items:.2f}€")


async def main():
    """Main function to run tests"""
    
    # Check if PDF path provided
    if len(sys.argv) < 2:
        print("Usage: python test_enhanced_processor.py <path_to_pdf>")
        print("\nExample PDFs to test:")
        print("- Native text PDF (e.g., digitally created invoice)")
        print("- Scanned PDF (will use OCR)")
        print("- Multi-page invoice")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    # Run comparisons
    await compare_processors(pdf_path)
    
    # Test specific features
    await test_specific_features(pdf_path)
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print("\nThe enhanced processor provides:")
    print("✓ Automatic text extraction from native PDFs")
    print("✓ OCR fallback for scanned documents")
    print("✓ Pre-extraction of common invoice fields")
    print("✓ Significant token/cost reduction")
    print("✓ Faster processing for text-based PDFs")
    print("✓ Better structure understanding")


if __name__ == "__main__":
    asyncio.run(main())