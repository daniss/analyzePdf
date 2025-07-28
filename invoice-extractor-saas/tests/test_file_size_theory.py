#!/usr/bin/env python3
"""
Test if file size affects frontend behavior
"""

import requests
import os

API_BASE = "http://localhost:8000"
EMAIL = "fresh@invoiceai.com"
PASSWORD = "freshpassword123"

def test_file_sizes():
    """Test different file sizes to see if that's the issue"""
    
    # Login
    response = requests.post(f"{API_BASE}/api/auth/token", data={'username': EMAIL, 'password': PASSWORD})
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json()['access_token']
    print("✅ Login successful")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Origin': 'http://localhost:3000'
    }
    
    # Test files with different sizes
    test_files = [
        {
            "path": "/home/danis/code/analyzePdf/invoice-extractor-saas/facture_test_siret_valide_20250727_191733.pdf",
            "name": "Problematic small file (2.7KB)"
        },
        {
            "path": "/home/danis/code/analyzePdf/invoice-extractor-saas/uploads/01cd828b-7c11-4aa1-b9ec-436de86c6cd4_invoice_Bill Eplett_14021.pdf",
            "name": "Working larger file (14.7KB)"
        }
    ]
    
    for test_file in test_files:
        if not os.path.exists(test_file["path"]):
            print(f"⏭️  Skipping {test_file['name']} - file not found")
            continue
            
        file_size = os.path.getsize(test_file["path"])
        
        print(f"\n📁 Testing: {test_file['name']}")
        print(f"📏 Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        with open(test_file["path"], 'rb') as f:
            files = {'files': (os.path.basename(test_file["path"]), f, 'application/pdf')}
            
            try:
                # Test with debug endpoint first
                response = requests.post(
                    f"{API_BASE}/api/batch/batch-process-debug",
                    headers=headers,
                    files=files,
                    timeout=5
                )
                
                print(f"📡 Debug response: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Debug success - Body received: {data.get('body_length')} bytes")
                    
                    # Now test actual batch process
                    f.seek(0)  # Reset file pointer
                    files = {'files': (os.path.basename(test_file["path"]), f, 'application/pdf')}
                    
                    response2 = requests.post(
                        f"{API_BASE}/api/batch/batch-process",
                        headers=headers,
                        files=files,
                        timeout=10
                    )
                    
                    print(f"📡 Batch response: {response2.status_code}")
                    if response2.status_code == 200:
                        print(f"✅ Batch success!")
                    else:
                        print(f"❌ Batch failed: {response2.text[:100]}...")
                else:
                    print(f"❌ Debug failed: {response.text[:100]}...")
                    
            except requests.exceptions.Timeout:
                print(f"❌ Request timed out")
            except Exception as e:
                print(f"❌ Request failed: {str(e)}")
    
    return True

if __name__ == "__main__":
    print("🔍 Testing file size theory")
    print("Comparing small vs large PDF files")
    print("=" * 60)
    
    test_file_sizes()
    
    print("\n" + "=" * 60)
    print("📊 ANALYSIS:")
    print("If both files work in backend tests but behave differently in frontend,")
    print("the issue might be browser-specific handling of small vs large files")
    print("=" * 60)