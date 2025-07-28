#!/usr/bin/env python3
"""
Simple focused test for the problematic PDF file to isolate the exact issue
"""

import requests
import json
import time
import os

API_BASE = "http://localhost:8000"
EMAIL = "test@invoiceai.com"
PASSWORD = "password123"

def test_problem_file():
    """Test the problematic file with minimal overhead"""
    
    # Login
    print("🔐 Logging in...")
    login_data = {'username': EMAIL, 'password': PASSWORD}
    response = requests.post(f"{API_BASE}/api/auth/token", data=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return False
    
    token = response.json()['access_token']
    print("✅ Login successful")
    
    # Test with the specific problematic file
    file_path = "/tmp/problem_invoice.pdf"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"📁 Testing file: {file_path}")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test with exact same parameters as frontend
    with open(file_path, 'rb') as f:
        files = {'files': ('facture_test_siret_valide_20250727_191733.pdf', f, 'application/pdf')}
        
        print("🚀 Making POST request to batch-process...")
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{API_BASE}/api/batch/batch-process",
                headers=headers,
                files=files,
                timeout=10  # Short timeout to catch hanging
            )
            
            request_time = time.time() - start_time
            print(f"⏱️  Request took: {request_time:.3f}s")
            
        except requests.exceptions.Timeout:
            print(f"❌ Request timed out after 10 seconds")
            return False
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
            return False
    
    print(f"📡 Response status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Batch ID: {data.get('batch_id')}")
        
        # Quick status check
        batch_id = data.get('batch_id')
        if batch_id:
            print(f"🔄 Checking status...")
            status_response = requests.get(
                f"{API_BASE}/api/batch/batch-status/{batch_id}",
                headers=headers,
                timeout=5
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"📊 Status: {status.get('status')}")
                print(f"📈 Progress: {status.get('processed_invoices', 0)}/{status.get('total_invoices', 0)}")
                return True
            else:
                print(f"❌ Status check failed: {status_response.status_code}")
                return False
        else:
            print(f"❌ No batch_id in response")
            return False
    else:
        print(f"❌ Request failed: {response.status_code}")
        try:
            error = response.json()
            print(f"📝 Error: {error}")
        except:
            print(f"📝 Raw response: {response.text}")
        return False

if __name__ == "__main__":
    print("🎯 Testing problematic PDF file with minimal test")
    print("=" * 60)
    
    success = test_problem_file()
    
    if success:
        print("\n✅ TEST PASSED: File processed successfully!")
    else:
        print("\n❌ TEST FAILED: File has issues!")