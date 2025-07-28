#!/usr/bin/env python3
"""
Test the final SIRET validation by directly uploading the problematic PDF
"""

import requests
import json
import os

def test_backend_health():
    """Test backend health"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def login_demo_user():
    """Login with demo user"""
    login_data = {
        "username": "demo@invoiceai.com", 
        "password": "demopassword123"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_invoice_processing(token, pdf_path):
    """Test processing the problematic PDF"""
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        with open(pdf_path, "rb") as f:
            files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
            
            print(f"🚀 Uploading {pdf_path} for processing...")
            response = requests.post(
                "http://localhost:8000/api/invoices/upload",
                files=files,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Invoice processing successful!")
                print(f"Invoice ID: {result.get('invoice_id', 'N/A')}")
                
                # Check SIRET validation status
                if 'supplier_siret_validation' in result:
                    supplier_validation = result['supplier_siret_validation']
                    print(f"📋 Supplier SIRET: {supplier_validation.get('siret', 'N/A')}")
                    print(f"   Status: {supplier_validation.get('status', 'N/A')}")
                    print(f"   Valid: {supplier_validation.get('is_valid', 'N/A')}")
                
                if 'client_siret_validation' in result:
                    client_validation = result['client_siret_validation']
                    print(f"📋 Client SIRET: {client_validation.get('siret', 'N/A')}")
                    print(f"   Status: {client_validation.get('status', 'N/A')}")
                    print(f"   Valid: {client_validation.get('is_valid', 'N/A')}")
                
                return True
            else:
                print(f"❌ Processing failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Processing error: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Final SIRET Validation Test")
    print("=" * 50)
    
    # Test backend health
    if not test_backend_health():
        print("❌ Backend is not healthy")
        return
    
    print("✅ Backend is healthy")
    
    # Login
    token = login_demo_user()
    if not token:
        print("❌ Could not login")
        return
    
    print("✅ Login successful")
    
    # Test the problematic PDF
    pdf_path = "facture_test_siret_valide_20250727_191733.pdf"
    if not os.path.exists(pdf_path):
        print(f"❌ Test PDF not found: {pdf_path}")
        print("Available files:")
        for f in os.listdir("."):
            if f.endswith(".pdf"):
                print(f"  - {f}")
        return
    
    # Process the invoice
    success = test_invoice_processing(token, pdf_path)
    
    if success:
        print("\n🎉 SUCCESS: SIRET validation is now working correctly!")
        print("The problematic PDF file can now be processed without validation failures.")
    else:
        print("\n❌ FAILED: SIRET validation still has issues")

if __name__ == "__main__":
    main()