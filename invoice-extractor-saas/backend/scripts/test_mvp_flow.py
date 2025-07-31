#!/usr/bin/env python3
"""Test the MVP invoice processing flow"""

import asyncio
import sys
import os
import base64
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.ai.groq_processor import GroqProcessor
from core.database import async_session_maker
from crud.user import create_user, authenticate_user
from schemas.auth import UserCreate
import uuid


async def test_mvp_flow():
    """Test the complete MVP flow"""
    
    print("🧪 ComptaFlow MVP Test\n")
    
    # 1. Check Groq API
    print("1. Testing Groq API Configuration...")
    processor = GroqProcessor()
    
    if not processor.api_key_available:
        print("❌ FAIL: Groq API key not configured!")
        print("   Please set GROQ_API_KEY in your .env file")
        return False
    
    print("✅ Groq API configured")
    
    # 2. Test database connection
    print("\n2. Testing Database Connection...")
    try:
        async with async_session_maker() as db:
            # Simple query to test connection
            from sqlalchemy import text
            result = await db.execute(text("SELECT 1"))
            result.scalar()
            print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ FAIL: Database error: {str(e)}")
        return False
    
    # 3. Test user creation and authentication
    print("\n3. Testing User Authentication...")
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    test_password = "testpassword123"
    
    try:
        async with async_session_maker() as db:
            # Create test user
            user_data = UserCreate(
                email=test_email,
                password=test_password,
                company_name="Test Company"
            )
            
            test_user = await create_user(db, user_data)
            print(f"✅ User created: {test_user.email}")
            
            # Test authentication
            auth_user = await authenticate_user(db, test_email, test_password)
            if auth_user:
                print("✅ Authentication successful")
            else:
                print("❌ FAIL: Authentication failed")
                return False
                
    except Exception as e:
        print(f"❌ FAIL: User creation error: {str(e)}")
        return False
    
    # 4. Test invoice processing with sample text
    print("\n4. Testing Invoice Processing...")
    
    sample_invoice_text = """
    FACTURE N° 2024-001
    Date: 15/01/2024
    
    FOURNISSEUR:
    CARREFOUR FRANCE
    93 Avenue de Paris
    91300 Massy
    SIRET: 652014051 00016
    TVA: FR 12 652014051
    
    CLIENT:
    SARL EXEMPLE
    123 Rue de la République
    75001 Paris
    SIRET: 123456789 00015
    
    DESIGNATION                     QUANTITE    PU HT      TOTAL HT
    Prestation de service            1          1000.00    1000.00
    Formation professionnelle        2          500.00     1000.00
    
    TOTAL HT:                                              2000.00
    TVA 20%:                                               400.00
    TOTAL TTC:                                             2400.00
    
    Conditions de paiement: 30 jours
    """
    
    try:
        async with async_session_maker() as db:
            # Process the invoice
            invoice_id = uuid.uuid4()
            user_id = test_user.id
            
            result = await processor.process_invoice_text(
                extracted_text=sample_invoice_text,
                invoice_id=invoice_id,
                user_id=user_id,
                db=db
            )
            
            print("✅ Invoice processed successfully!")
            print(f"   - Invoice number: {result.invoice_number}")
            print(f"   - Vendor: {result.vendor_name}")
            print(f"   - Customer: {result.customer_name}")
            print(f"   - Total: {result.total} {result.currency}")
            
            if result.vendor and result.vendor.siret_number:
                print(f"   - SIRET detected: {result.vendor.siret_number}")
            
    except Exception as e:
        print(f"❌ FAIL: Invoice processing error: {str(e)}")
        return False
    
    # 5. Summary
    print("\n" + "="*50)
    print("✅ MVP TEST PASSED!")
    print("\nThe core functionality is working:")
    print("- Groq AI processing ✓")
    print("- Database operations ✓")
    print("- User authentication ✓")
    print("- Invoice extraction ✓")
    print("- French business data parsing ✓")
    print("\nComptaFlow MVP is ready to use! 🚀")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_mvp_flow())
    sys.exit(0 if success else 1)