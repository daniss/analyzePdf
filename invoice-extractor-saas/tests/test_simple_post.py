#!/usr/bin/env python3
"""
Test simple POST request to debug endpoint
"""

import requests
import json

API_BASE = "http://localhost:8000"
EMAIL = "fresh@invoiceai.com"
PASSWORD = "freshpassword123"

def test_simple_post():
    """Test simple POST to debug endpoint"""
    
    # Login
    response = requests.post(f"{API_BASE}/api/auth/token", data={'username': EMAIL, 'password': PASSWORD})
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json()['access_token']
    print("✅ Login successful")
    
    # Test simple POST to debug endpoint
    headers = {
        'Authorization': f'Bearer {token}',
        'Origin': 'http://localhost:3000',
        'Content-Type': 'application/json'
    }
    
    data = {"test": "simple post"}
    
    print("📤 Testing simple POST to debug endpoint...")
    response = requests.post(
        f"{API_BASE}/api/batch/debug-test",
        headers=headers,
        json=data
    )
    
    print(f"📡 Response: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ Simple POST works!")
        print(f"📋 Response: {response.json()}")
        return True
    else:
        print(f"❌ Simple POST failed: {response.text}")
        return False

def test_formdata_post():
    """Test FormData POST to debug endpoint"""
    
    # Login
    response = requests.post(f"{API_BASE}/api/auth/token", data={'username': EMAIL, 'password': PASSWORD})
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json()['access_token']
    
    # Test FormData POST
    headers = {
        'Authorization': f'Bearer {token}',
        'Origin': 'http://localhost:3000'
        # Don't set Content-Type for FormData
    }
    
    files = {'test_file': ('test.txt', b'test file content', 'text/plain')}
    
    print("📤 Testing FormData POST to debug endpoint...")
    response = requests.post(
        f"{API_BASE}/api/batch/debug-test",
        headers=headers,
        files=files
    )
    
    print(f"📡 Response: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ FormData POST works!")
        print(f"📋 Response: {response.json()}")
        return True
    else:
        print(f"❌ FormData POST failed: {response.text}")
        return False

if __name__ == "__main__":
    print("🔧 Testing basic POST functionality")
    print("=" * 50)
    
    test1 = test_simple_post()
    print()
    test2 = test_formdata_post()
    
    print("\n" + "=" * 50)
    if test1 and test2:
        print("🎉 Both tests passed - POST functionality works!")
    else:
        print("💥 Some tests failed - there's an issue with POST requests")