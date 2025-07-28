#!/usr/bin/env python3
"""
Test that exactly mimics browser behavior including proper CORS headers
"""

import requests
import json
import time
import os

API_BASE = "http://localhost:8000"
FRONTEND_ORIGIN = "http://localhost:3000"
EMAIL = "test@invoiceai.com"
PASSWORD = "password123"

def test_browser_exact():
    """Test with exact browser headers and timing"""
    
    session = requests.Session()
    
    # Step 1: Login
    print("🔐 Step 1: Login")
    response = session.post(f"{API_BASE}/api/auth/token", data={'username': EMAIL, 'password': PASSWORD})
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json()['access_token']
    print("✅ Login successful")
    
    # Step 2: Test batch-process with exact browser CORS headers
    print("\n🎯 Step 2: Batch process with browser-exact headers")
    
    file_path = "/tmp/problem_invoice.pdf"
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    # CORS preflight request with exact browser headers
    print("📡 Sending CORS preflight request...")
    preflight_headers = {
        'Origin': FRONTEND_ORIGIN,
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'authorization',  # What browser sends for JWT auth
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Sec-Fetch-Dest': 'empty',
    }
    
    options_response = session.options(
        f"{API_BASE}/api/batch/batch-process",
        headers=preflight_headers
    )
    
    print(f"📡 OPTIONS response: {options_response.status_code}")
    print(f"📋 CORS headers: {[h for h in options_response.headers.items() if 'access-control' in h[0].lower()]}")
    
    if options_response.status_code != 200:
        print(f"❌ CORS preflight failed!")
        return False
    
    # Check if the required headers are allowed
    allowed_headers = options_response.headers.get('Access-Control-Allow-Headers', '').lower()
    if 'authorization' not in allowed_headers:
        print(f"❌ Authorization header not allowed in CORS! Allowed: {allowed_headers}")
        return False
    
    print("✅ CORS preflight succeeded")
    
    # Step 3: Actual POST request with browser-like headers
    print("\n📤 Step 3: Actual POST request")
    
    post_headers = {
        'Origin': FRONTEND_ORIGIN,
        'Authorization': f'Bearer {token}',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Sec-Fetch-Dest': 'empty',
        # Don't set Content-Type for multipart data - let requests handle it
    }
    
    with open(file_path, 'rb') as f:
        files = {'files': ('facture_test_siret_valide_20250727_191733.pdf', f, 'application/pdf')}
        
        print(f"📦 Sending POST with file: {os.path.basename(file_path)}")
        
        try:
            response = session.post(
                f"{API_BASE}/api/batch/batch-process",
                headers=post_headers,
                files=files,
                timeout=30
            )
            
            print(f"📡 POST response: {response.status_code}")
            
        except requests.exceptions.Timeout:
            print(f"❌ POST request timed out!")
            return False
        except Exception as e:
            print(f"❌ POST request failed: {str(e)}")
            return False
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ POST succeeded! Batch ID: {data.get('batch_id')}")
        
        # Step 4: Test status polling
        print("\n🔄 Step 4: Status polling")
        batch_id = data.get('batch_id')
        
        # CORS preflight for status
        status_options = session.options(
            f"{API_BASE}/api/batch/batch-status/{batch_id}",
            headers={
                'Origin': FRONTEND_ORIGIN,
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'authorization',
            }
        )
        print(f"📡 Status OPTIONS: {status_options.status_code}")
        
        # GET status
        status_response = session.get(
            f"{API_BASE}/api/batch/batch-status/{batch_id}",
            headers={
                'Origin': FRONTEND_ORIGIN,
                'Authorization': f'Bearer {token}',
            }
        )
        
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"📊 Status: {status.get('status')}")
            print(f"✅ Full workflow succeeded!")
            return True
        else:
            print(f"❌ Status check failed: {status_response.status_code}")
            return False
            
    else:
        print(f"❌ POST failed: {response.status_code}")
        try:
            error = response.json()
            print(f"📝 Error: {error}")
        except:
            print(f"📝 Raw response: {response.text}")
        return False

if __name__ == "__main__":
    print("🌐 BROWSER-EXACT SIMULATION")
    print("Testing with exact browser CORS headers and behavior")
    print("=" * 70)
    
    success = test_browser_exact()
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 BROWSER SIMULATION PASSED!")
        print("📝 The backend API works correctly with proper CORS headers")
        print("📝 Issue must be frontend-specific (React/Next.js environment)")
    else:
        print("💥 BROWSER SIMULATION FAILED!")
        print("📝 Found a reproducible issue with the API")
    print("=" * 70)