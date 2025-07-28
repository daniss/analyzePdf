#!/usr/bin/env python3
"""
Test batch-process-debug endpoint
"""

import requests
import os

API_BASE = "http://localhost:8000"
EMAIL = "fresh@invoiceai.com"
PASSWORD = "freshpassword123"

def test_batch_debug():
    """Test batch-process-debug endpoint with FormData"""
    
    # Login
    response = requests.post(f"{API_BASE}/api/auth/token", data={'username': EMAIL, 'password': PASSWORD})
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json()['access_token']
    print("✅ Login successful")
    
    # Test with FormData (like frontend does)
    headers = {
        'Authorization': f'Bearer {token}',
        'Origin': 'http://localhost:3000'
    }
    
    file_path = "/tmp/problem_invoice.pdf"
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    with open(file_path, 'rb') as f:
        files = {'files': ('facture_test_siret_valide_20250727_191733.pdf', f, 'application/pdf')}
        
        print("📤 Testing batch-process-debug with FormData...")
        response = requests.post(
            f"{API_BASE}/api/batch/batch-process-debug",
            headers=headers,
            files=files
        )
        
        print(f"📡 Response: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Batch debug works!")
            print(f"📋 Response: {response.json()}")
            return True
        else:
            print(f"❌ Batch debug failed: {response.text}")
            return False

def test_original_batch():
    """Test original batch-process endpoint"""
    
    # Login
    response = requests.post(f"{API_BASE}/api/auth/token", data={'username': EMAIL, 'password': PASSWORD})
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json()['access_token']
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Origin': 'http://localhost:3000'
    }
    
    file_path = "/tmp/problem_invoice.pdf"
    with open(file_path, 'rb') as f:
        files = {'files': ('facture_test_siret_valide_20250727_191733.pdf', f, 'application/pdf')}
        
        print("📤 Testing original batch-process...")
        try:
            response = requests.post(
                f"{API_BASE}/api/batch/batch-process",
                headers=headers,
                files=files,
                timeout=10
            )
            
            print(f"📡 Response: {response.status_code}")
            if response.status_code == 200:
                print(f"✅ Original batch works!")
                print(f"📋 Response: {response.json()}")
                return True
            else:
                print(f"❌ Original batch failed: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"❌ Original batch timed out!")
            return False

if __name__ == "__main__":
    print("🔧 Testing batch endpoints")
    print("=" * 50)
    
    test1 = test_batch_debug()
    print()
    test2 = test_original_batch()
    
    print("\n" + "=" * 50)
    print(f"Batch debug: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Original batch: {'✅ PASS' if test2 else '❌ FAIL'}")