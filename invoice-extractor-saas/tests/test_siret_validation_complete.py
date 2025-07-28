#!/usr/bin/env python3
"""
Test the complete SIRET validation flow with the problematic PDF
"""

import asyncio
import sys
import os
import requests

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.core.validation.siret_validation_service import SIRETValidationService
from backend.core.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

async def test_siret_validation():
    """Test SIRET validation for the extracted numbers"""
    
    print("🔍 Testing complete SIRET validation service")
    print("=" * 60)
    
    # Test SIRET numbers from the problematic invoice
    test_sirets = [
        ("65202390200018", "Fournisseur - CARREFOUR SA"),
        ("57200024200015", "Client - BOUYGUES SA"),
        ("65201405100033", "Test - Real Carrefour SIRET from sample"),
        ("54209118000023", "Test - Real Auchan SIRET from sample"),
    ]
    
    service = SIRETValidationService()
    
    for siret, description in test_sirets:
        print(f"\n📋 Testing SIRET: {siret} ({description})")
        print("-" * 50)
        
        try:
            # Create a mock database session (simplified for testing)
            async with get_db_session() as db_session:
                result = await service.validate_siret_comprehensive(
                    siret=siret,
                    extracted_company_name=description.split(" - ")[1],
                    db_session=db_session,
                    invoice_id="test-invoice",
                    user_id="test-user"
                )
                
                print(f"Status: {result.validation_status.value}")
                print(f"Cleaned SIRET: {result.cleaned_siret}")
                print(f"Blocking Level: {result.blocking_level.value}")
                print(f"Traffic Light: {result.traffic_light_color}")
                print(f"Export Blocked: {result.export_blocked}")
                print(f"Auto-correction Success: {result.auto_correction_success}")
                
                if result.french_error_message:
                    print(f"Error: {result.french_error_message}")
                    
                if result.correction_details:
                    print(f"Corrections: {' | '.join(result.correction_details)}")
                
        except Exception as e:
            print(f"❌ Validation failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ SIRET validation testing complete")

def test_backend_health():
    """Test that backend is responding"""
    print("🏥 Testing backend health...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is healthy")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 SIRET Validation Complete Test")
    print("=" * 60)
    
    # Test backend health first
    if not test_backend_health():
        print("❌ Backend is not accessible, skipping SIRET validation test")
        return
    
    # Test SIRET validation
    await test_siret_validation()

if __name__ == "__main__":
    asyncio.run(main())