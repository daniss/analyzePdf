#!/usr/bin/env python3
"""
Test frontend token refresh behavior that might cause issues
"""

import requests
import json
import time
import os

API_BASE = "http://localhost:8000"
EMAIL = "test@invoiceai.com"  
PASSWORD = "password123"

def test_token_refresh_scenario():
    """Test scenario where token might need refresh during upload"""
    
    session = requests.Session()
    
    # Step 1: Login and get initial token
    print("🔐 Step 1: Initial login")
    response = session.post(f"{API_BASE}/api/auth/token", data={'username': EMAIL, 'password': PASSWORD})
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json()['access_token']
    print("✅ Login successful")
    
    # Step 2: Test /auth/me endpoint like frontend does
    print("\n🔍 Step 2: Test auth/me endpoint (frontend does this)")
    headers = {'Authorization': f'Bearer {token}'}
    
    me_response = session.get(f"{API_BASE}/api/auth/me", headers=headers)
    print(f"📡 GET /auth/me: {me_response.status_code}")
    
    if me_response.status_code == 401:
        print("🔄 Token expired, trying refresh...")
        
        # Try refresh (this might not work since there's no refresh endpoint)
        refresh_response = session.post(
            f"{API_BASE}/api/auth/refresh",
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if refresh_response.status_code == 200:
            token = refresh_response.json()['access_token']
            headers = {'Authorization': f'Bearer {token}'}
            print("✅ Token refreshed")
        else:
            print(f"❌ Token refresh failed: {refresh_response.status_code}")
            return False
    
    # Step 3: Test with the problematic file after potential token refresh
    print("\n🎯 Step 3: Test batch-process with potentially refreshed token")
    
    file_path = "/tmp/problem_invoice.pdf"
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    with open(file_path, 'rb') as f:
        files = {'files': ('facture_test_siret_valide_20250727_191733.pdf', f, 'application/pdf')}
        
        print(f"📤 Sending POST with updated token...")
        
        try:
            response = session.post(
                f"{API_BASE}/api/batch/batch-process",
                headers=headers,
                files=files,
                timeout=30
            )
            
            print(f"📡 Response: {response.status_code}")
            
        except requests.exceptions.Timeout:
            print(f"❌ Request timed out!")
            return False
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
            return False
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Batch ID: {data.get('batch_id')}")
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        if response.status_code == 401:
            print("🔍 This could be the authentication issue!")
        try:
            error = response.json()
            print(f"📝 Error: {error}")
        except:
            print(f"📝 Raw response: {response.text}")
        return False

def test_multiple_concurrent_requests():
    """Test if multiple requests cause issues (like frontend might do)"""
    
    print("\n🔄 Testing concurrent request behavior")
    
    session = requests.Session()
    
    # Login
    response = session.post(f"{API_BASE}/api/auth/token", data={'username': EMAIL, 'password': PASSWORD})
    if response.status_code != 200:
        print(f"❌ Login failed")
        return False
    
    token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Simulate frontend making multiple requests quickly
    print("📡 Making rapid auth/me requests (like frontend)")
    for i in range(3):
        me_response = session.get(f"{API_BASE}/api/auth/me", headers=headers)
        print(f"  Auth check {i+1}: {me_response.status_code}")
        time.sleep(0.1)
    
    print("📡 Making rapid invoices requests (like frontend)")
    for i in range(3):
        invoices_response = session.get(f"{API_BASE}/api/invoices/", headers=headers)
        print(f"  Invoices check {i+1}: {invoices_response.status_code}")
        time.sleep(0.1)
    
    # Now try the problematic batch-process
    print("📤 Now trying batch-process after rapid requests...")
    
    file_path = "/tmp/problem_invoice.pdf"
    with open(file_path, 'rb') as f:
        files = {'files': ('facture_test_siret_valide_20250727_191733.pdf', f, 'application/pdf')}
        
        response = session.post(
            f"{API_BASE}/api/batch/batch-process",
            headers=headers,
            files=files,
            timeout=30
        )
        
        print(f"📡 Batch response: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Success even after rapid requests!")
            return True
        else:
            print(f"❌ Failed after rapid requests: {response.status_code}")
            return False

if __name__ == "__main__":
    print("🔍 FRONTEND TOKEN REFRESH TESTING")
    print("Testing scenarios that might cause frontend-specific issues")
    print("=" * 70)
    
    # Test 1: Token refresh scenario
    success1 = test_token_refresh_scenario()
    
    # Test 2: Multiple concurrent requests
    success2 = test_multiple_concurrent_requests()
    
    print("\n" + "=" * 70)
    print("📊 RESULTS:")
    print(f"  Token refresh scenario: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"  Concurrent requests: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print("\n🎉 All authentication scenarios work!")
        print("📝 The issue must be React/browser-specific timing or state management")
    else:
        print("\n💥 Found authentication issues!")
    print("=" * 70)