#!/usr/bin/env python3
"""
Test script to simulate frontend batch processing workflow
Tests the actual "Traiter les Factures" button functionality
"""

import requests
import json
import time
import os

API_BASE = "http://localhost:8000"
FRONTEND_BASE = "http://localhost:3000"

# Test credentials
EMAIL = "test@invoiceai.com"
PASSWORD = "password123"

class FrontendBatchTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        
    def login(self):
        """Login and get authentication token"""
        print("🔐 Testing login...")
        
        # Prepare login form data (same as frontend)
        login_data = {
            'username': EMAIL,
            'password': PASSWORD
        }
        
        response = self.session.post(f"{API_BASE}/api/auth/token", data=login_data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.token = token_data['access_token']
            print(f"✅ Login successful, token: {self.token[:20]}...")
            return True
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    
    def test_auth_header(self):
        """Test if auth token works"""
        if not self.token:
            print("❌ No token available")
            return False
            
        headers = {'Authorization': f'Bearer {self.token}'}
        response = self.session.get(f"{API_BASE}/api/auth/me", headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Authentication works, user: {user_data['email']}")
            return True
        else:
            print(f"❌ Auth test failed: {response.status_code} - {response.text}")
            return False
    
    def test_batch_processing(self):
        """Test the actual batch processing endpoint with FormData"""
        if not self.token:
            print("❌ No token available")
            return False
            
        print("📁 Testing batch processing with FormData...")
        
        # Create test file path - using the problematic file
        test_file_path = "/tmp/problem_invoice.pdf"
        if not os.path.exists(test_file_path):
            print(f"❌ Test file not found: {test_file_path}")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Prepare FormData exactly like frontend does
        with open(test_file_path, 'rb') as f:
            files = {'files': ('facture_test_siret_valide_20250727_191733.pdf', f, 'application/pdf')}
            
            print(f"  📤 Uploading file: {test_file_path}")
            print(f"  🔑 Using token: {self.token[:20]}...")
            
            response = self.session.post(
                f"{API_BASE}/api/batch/batch-process",
                headers=headers,
                files=files
            )
        
        print(f"  📡 Response status: {response.status_code}")
        print(f"  📝 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            batch_data = response.json()
            print(f"✅ Batch processing started successfully!")
            print(f"  📋 Batch ID: {batch_data['batch_id']}")
            print(f"  📊 Status: {batch_data['status']}")
            print(f"  📄 Invoice count: {batch_data['invoice_count']}")
            
            # Test status polling
            return self.test_status_polling(batch_data['batch_id'])
        else:
            print(f"❌ Batch processing failed: {response.status_code}")
            print(f"  📝 Response: {response.text}")
            return False
    
    def test_status_polling(self, batch_id):
        """Test batch status polling"""
        print(f"⏳ Testing status polling for batch: {batch_id}")
        
        headers = {'Authorization': f'Bearer {self.token}'}
        max_attempts = 10
        
        for attempt in range(max_attempts):
            print(f"  🔄 Attempt {attempt + 1}/{max_attempts}")
            
            response = self.session.get(
                f"{API_BASE}/api/batch/batch-status/{batch_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                status_data = response.json()
                print(f"    📊 Status: {status_data['status']}")
                print(f"    📈 Progress: {status_data['processed_invoices']}/{status_data['total_invoices']}")
                
                if status_data['status'] == 'completed':
                    print(f"✅ Batch processing completed successfully!")
                    print(f"  📄 Processed: {status_data['processed_invoices']}")
                    print(f"  ❌ Failed: {status_data['failed_invoices']}")
                    print(f"  💬 Message: {status_data.get('message', 'No message')}")
                    return True
                elif status_data['status'] == 'failed':
                    print(f"❌ Batch processing failed!")
                    print(f"  📝 Error: {status_data.get('error', 'Unknown error')}")
                    return False
                else:
                    print("    ⏳ Still processing, waiting 2 seconds...")
                    time.sleep(2)
            else:
                print(f"    ❌ Status check failed: {response.status_code}")
                return False
        
        print("❌ Batch processing timed out")
        return False
    
    def run_full_test(self):
        """Run complete frontend batch processing test"""
        print("🚀 Starting frontend batch processing test...")
        print("=" * 60)
        
        # Step 1: Login
        if not self.login():
            return False
        
        # Step 2: Test authentication
        if not self.test_auth_header():
            return False
            
        # Step 3: Test batch processing (this simulates clicking "Traiter les Factures")
        if not self.test_batch_processing():
            return False
        
        print("=" * 60)
        print("🎉 All tests passed! Frontend batch processing works correctly!")
        return True

if __name__ == "__main__":
    tester = FrontendBatchTester()
    success = tester.run_full_test()
    
    if success:
        print("\n✅ RESULT: The 'Traiter les Factures' button functionality is working!")
        exit(0)
    else:
        print("\n❌ RESULT: The 'Traiter les Factures' button functionality has issues!")
        exit(1)