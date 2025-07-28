#!/usr/bin/env python3
"""
Debug frontend behavior by simulating browser environment exactly
"""

import requests
import json
import time
import os

API_BASE = "http://localhost:8000"
EMAIL = "test@invoiceai.com"
PASSWORD = "password123"

def simulate_frontend_behavior():
    """Simulate exact frontend behavior including preflight requests"""
    
    session = requests.Session()
    
    # Step 1: Login (same as frontend)
    print("🔐 Step 1: Login")
    login_data = {'username': EMAIL, 'password': PASSWORD}
    response = session.post(f"{API_BASE}/api/auth/token", data=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json()['access_token']
    print("✅ Login successful")
    
    # Step 2: Simulate auth/me check (frontend does this)
    print("\n🔍 Step 2: Auth check")
    headers = {'Authorization': f'Bearer {token}'}
    
    # OPTIONS preflight for auth/me
    options_response = session.options(f"{API_BASE}/api/auth/me")
    print(f"📡 OPTIONS /api/auth/me: {options_response.status_code}")
    
    # GET auth/me
    me_response = session.get(f"{API_BASE}/api/auth/me", headers=headers)
    print(f"📡 GET /api/auth/me: {me_response.status_code}")
    
    # Step 3: Simulate invoices list check (frontend does this)
    print("\n📋 Step 3: Invoices list check")
    
    # OPTIONS preflight for invoices
    options_response = session.options(f"{API_BASE}/api/invoices/")
    print(f"📡 OPTIONS /api/invoices/: {options_response.status_code}")
    
    # GET invoices
    invoices_response = session.get(f"{API_BASE}/api/invoices/", headers=headers)
    print(f"📡 GET /api/invoices/: {invoices_response.status_code}")
    
    # Step 4: Simulate the problematic batch-process request
    print("\n🎯 Step 4: Batch process (THE CRITICAL STEP)")
    
    file_path = "/tmp/problem_invoice.pdf"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    # OPTIONS preflight for batch-process (this is where issues might occur)
    print("📡 Sending OPTIONS preflight for batch-process...")
    options_start = time.time()
    
    options_response = session.options(f"{API_BASE}/api/batch/batch-process")
    options_time = time.time() - options_start
    
    print(f"📡 OPTIONS /api/batch/batch-process: {options_response.status_code} ({options_time:.3f}s)")
    print(f"📋 OPTIONS headers: {dict(options_response.headers)}")
    
    if options_response.status_code != 200:
        print(f"❌ OPTIONS preflight failed!")
        return False
    
    # Add delay like frontend might have
    time.sleep(0.1)
    
    # Now the actual POST request
    print("\n📤 Sending actual POST request...")
    
    # Prepare headers exactly like frontend ApiClient
    post_headers = {
        'Authorization': f'Bearer {token}',
        # Don't set Content-Type for multipart/form-data - let requests handle it
    }
    
    with open(file_path, 'rb') as f:
        files = {'files': ('facture_test_siret_valide_20250727_191733.pdf', f, 'application/pdf')}
        
        print(f"📦 FormData file: {os.path.basename(file_path)} ({os.path.getsize(file_path)} bytes)")
        
        post_start = time.time()
        
        try:
            # Use same timeout as frontend (30 seconds)
            response = session.post(
                f"{API_BASE}/api/batch/batch-process",
                headers=post_headers,
                files=files,
                timeout=30
            )
            
            post_time = time.time() - post_start
            print(f"⏱️  POST took: {post_time:.3f}s")
            
        except requests.exceptions.Timeout:
            print(f"❌ POST request timed out after 30 seconds")
            print("🔍 This matches the frontend timeout behavior!")
            return False
        except Exception as e:
            print(f"❌ POST request failed: {str(e)}")
            return False
    
    print(f"📡 POST response: {response.status_code}")
    print(f"📋 POST headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ POST succeeded! Batch ID: {data.get('batch_id')}")
        
        # Step 5: Status polling simulation
        print("\n🔄 Step 5: Status polling simulation")
        batch_id = data.get('batch_id')
        
        for i in range(5):  # Poll 5 times like frontend
            print(f"📊 Poll {i+1}/5...")
            
            # OPTIONS for status check
            options_response = session.options(f"{API_BASE}/api/batch/batch-status/{batch_id}")
            print(f"  📡 OPTIONS status: {options_response.status_code}")
            
            # GET status
            status_response = session.get(
                f"{API_BASE}/api/batch/batch-status/{batch_id}",
                headers=headers,
                timeout=10
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"  📊 Status: {status.get('status')}")
                print(f"  📈 Progress: {status.get('processed_invoices', 0)}/{status.get('total_invoices', 0)}")
                
                if status.get('status') in ['completed', 'failed']:
                    print(f"  🏁 Processing finished: {status.get('status')}")
                    return True
            else:
                print(f"  ❌ Status check failed: {status_response.status_code}")
                return False
            
            time.sleep(2)  # 2 second delay like frontend
        
        print("⏰ Polling completed")
        return True
        
    else:
        print(f"❌ POST failed: {response.status_code}")
        try:
            error = response.json()
            print(f"📝 Error: {error}")
        except:
            print(f"📝 Raw response: {response.text}")
        return False

if __name__ == "__main__":
    print("🌐 FRONTEND BEHAVIOR SIMULATION")
    print("Simulating exact frontend request sequence including preflight requests")
    print("=" * 80)
    
    success = simulate_frontend_behavior()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 FRONTEND SIMULATION PASSED: All steps worked correctly!")
        print("📝 This suggests the issue is specific to the actual browser environment")
    else:
        print("💥 FRONTEND SIMULATION FAILED: Found the issue!")
        print("📝 The problem is reproducible outside the browser")
    print("=" * 80)