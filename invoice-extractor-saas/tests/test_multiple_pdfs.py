#!/usr/bin/env python3
"""
Test script to test batch processing with multiple different PDF files
This will help determine if the issue is specific to certain PDF files
"""

import requests
import json
import time
import os
import shutil

API_BASE = "http://localhost:8000"

# Test credentials
EMAIL = "test@invoiceai.com"
PASSWORD = "password123"

class MultiplePDFTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        
    def login(self):
        """Login and get authentication token"""
        print("🔐 Testing login...")
        
        login_data = {
            'username': EMAIL,
            'password': PASSWORD
        }
        
        response = self.session.post(f"{API_BASE}/api/auth/token", data=login_data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.token = token_data['access_token']
            print(f"✅ Login successful")
            return True
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    
    def test_single_pdf(self, file_path, test_name):
        """Test batch processing with a single PDF file"""
        if not self.token:
            print("❌ No token available")
            return False
            
        print(f"\n🧪 Testing: {test_name}")
        print(f"📁 File: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False
        
        # Get file size for logging
        file_size = os.path.getsize(file_path)
        print(f"📏 File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Prepare FormData exactly like frontend does
        with open(file_path, 'rb') as f:
            files = {'files': (os.path.basename(file_path), f, 'application/pdf')}
            
            print("  📤 Uploading file...")
            start_time = time.time()
            
            try:
                response = self.session.post(
                    f"{API_BASE}/api/batch/batch-process",
                    headers=headers,
                    files=files,
                    timeout=30  # 30 second timeout
                )
                
                upload_time = time.time() - start_time
                print(f"  ⏱️  Upload took: {upload_time:.2f} seconds")
                
            except requests.exceptions.Timeout:
                print(f"  ❌ Upload timed out after 30 seconds")
                return False
            except Exception as e:
                print(f"  ❌ Upload failed with exception: {str(e)}")
                return False
        
        print(f"  📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            batch_data = response.json()
            print(f"  ✅ Batch processing started successfully!")
            print(f"    📋 Batch ID: {batch_data['batch_id']}")
            print(f"    📊 Status: {batch_data['status']}")
            print(f"    📄 Invoice count: {batch_data['invoice_count']}")
            
            # Test quick status check
            return self.quick_status_check(batch_data['batch_id'])
        else:
            print(f"  ❌ Batch processing failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"    📝 Error: {error_data}")
            except:
                print(f"    📝 Response: {response.text}")
            return False
    
    def quick_status_check(self, batch_id):
        """Quick status check to see if processing starts correctly"""
        print(f"  ⏳ Checking initial status...")
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = self.session.get(
                f"{API_BASE}/api/batch/batch-status/{batch_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                status_data = response.json()
                print(f"    📊 Initial status: {status_data['status']}")
                print(f"    📈 Progress: {status_data['processed_invoices']}/{status_data['total_invoices']}")
                
                # Wait a few seconds and check again
                time.sleep(3)
                
                response2 = self.session.get(
                    f"{API_BASE}/api/batch/batch-status/{batch_id}",
                    headers=headers,
                    timeout=10
                )
                
                if response2.status_code == 200:
                    status_data2 = response2.json()
                    print(f"    📊 Status after 3s: {status_data2['status']}")
                    print(f"    📈 Progress after 3s: {status_data2['processed_invoices']}/{status_data2['total_invoices']}")
                    
                    if status_data2['status'] != 'processing':
                        print(f"    ✅ Processing completed quickly")
                        return True
                    else:
                        print(f"    ⏳ Processing is running normally")
                        return True
                        
                return True
            else:
                print(f"    ❌ Status check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"    ❌ Status check exception: {str(e)}")
            return False
    
    def run_tests(self):
        """Run tests with multiple PDF files"""
        print("🚀 Starting multiple PDF test suite...")
        print("=" * 80)
        
        # Login first
        if not self.login():
            return False
        
        # Test files to try
        test_files = [
            {
                "path": "/home/danis/code/analyzePdf/invoice-extractor-saas/facture_test_siret_valide_20250727_191733.pdf",
                "name": "Problematic Generated Test File (User Reported Issue)"
            },
            {
                "path": "/home/danis/code/analyzePdf/invoice-extractor-saas/facture_test_siret_reel.pdf", 
                "name": "Other Generated Test File"
            },
            {
                "path": "/home/danis/code/analyzePdf/invoice-extractor-saas/uploads/cb9fb37b-0d71-4c05-8d95-423489042100_invoice_Scot Wooten_10963.pdf",
                "name": "Real Invoice File (Scot Wooten)"
            },
            {
                "path": "/home/danis/code/analyzePdf/invoice-extractor-saas/uploads/01cd828b-7c11-4aa1-b9ec-436de86c6cd4_invoice_Bill Eplett_14021.pdf",
                "name": "Real Invoice File (Bill Eplett)"
            }
        ]
        
        results = []
        
        for test_file in test_files:
            result = self.test_single_pdf(test_file["path"], test_file["name"])
            results.append({
                "name": test_file["name"],
                "path": test_file["path"],
                "success": result
            })
            
            # Add delay between tests to avoid overwhelming the system
            if test_file != test_files[-1]:  # Don't wait after last test
                print("\n⏸️  Waiting 5 seconds before next test...")
                time.sleep(5)
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS SUMMARY:")
        print("=" * 80)
        
        success_count = 0
        for i, result in enumerate(results, 1):
            status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
            print(f"{i}. {status} - {result['name']}")
            if result["success"]:
                success_count += 1
        
        print(f"\n📈 Overall Success Rate: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
        
        # Analysis
        if success_count == 0:
            print("\n🔍 ANALYSIS: All tests failed - likely a systematic issue")
        elif success_count == len(results):
            print("\n🔍 ANALYSIS: All tests passed - issue may have been resolved")
        else:
            print("\n🔍 ANALYSIS: Mixed results - issue may be file-specific")
            
            failed_files = [r for r in results if not r["success"]]
            successful_files = [r for r in results if r["success"]]
            
            if failed_files:
                print("\n❌ FAILED FILES:")
                for f in failed_files:
                    print(f"   - {f['name']}")
                    
            if successful_files:
                print("\n✅ SUCCESSFUL FILES:")
                for f in successful_files:
                    print(f"   - {f['name']}")
        
        return success_count > 0

if __name__ == "__main__":
    tester = MultiplePDFTester()
    success = tester.run_tests()
    
    if success:
        print("\n🎉 At least some tests passed!")
        exit(0)
    else:
        print("\n💥 All tests failed!")
        exit(1)