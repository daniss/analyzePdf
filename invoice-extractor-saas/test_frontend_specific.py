#!/usr/bin/env python3
"""
Comprehensive frontend-specific test for the problematic PDF file
This simulates exact frontend behavior and monitors backend responses
"""

import requests
import json
import time
import os
import threading
import subprocess
import signal
import sys

API_BASE = "http://localhost:8000"
EMAIL = "test@invoiceai.com"
PASSWORD = "password123"

class FrontendSpecificTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.backend_log_process = None
        
    def start_backend_monitoring(self):
        """Start monitoring backend logs in real-time"""
        print("📊 Starting backend log monitoring...")
        try:
            # Start docker logs in the background
            self.backend_log_process = subprocess.Popen(
                ['docker-compose', 'logs', '-f', 'backend'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            def log_reader():
                print("📋 Backend log monitoring started...")
                for line in iter(self.backend_log_process.stdout.readline, ''):
                    if line.strip():
                        print(f"🔍 BACKEND: {line.strip()}")
            
            # Start log reading in a separate thread
            log_thread = threading.Thread(target=log_reader)
            log_thread.daemon = True
            log_thread.start()
            
            time.sleep(2)  # Let monitoring start
            print("✅ Backend monitoring ready\n")
            
        except Exception as e:
            print(f"⚠️  Could not start backend monitoring: {e}")
    
    def stop_backend_monitoring(self):
        """Stop backend log monitoring"""
        if self.backend_log_process:
            try:
                self.backend_log_process.terminate()
                self.backend_log_process.wait(timeout=5)
            except:
                self.backend_log_process.kill()
            print("🛑 Backend monitoring stopped")
    
    def login(self):
        """Login with detailed logging"""
        print("🔐 Attempting login...")
        
        login_data = {
            'username': EMAIL,
            'password': PASSWORD
        }
        
        print(f"📤 POST {API_BASE}/api/auth/token")
        start_time = time.time()
        
        response = self.session.post(f"{API_BASE}/api/auth/token", data=login_data)
        
        login_time = time.time() - start_time
        print(f"⏱️  Login response time: {login_time:.3f}s")
        print(f"📡 Login response: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            self.token = token_data['access_token']
            print(f"✅ Login successful")
            return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"📝 Response: {response.text}")
            return False
    
    def test_problematic_file_detailed(self):
        """Test the problematic file with maximum detail"""
        file_path = "/tmp/problem_invoice.pdf"
        
        print(f"\n🎯 TESTING PROBLEMATIC FILE: {file_path}")
        print("=" * 80)
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False
        
        file_size = os.path.getsize(file_path)
        print(f"📁 File: {os.path.basename(file_path)}")
        print(f"📏 Size: {file_size} bytes")
        print(f"🔑 Token: {self.token[:20] if self.token else 'None'}...")
        
        # Prepare headers exactly like frontend
        headers = {
            'Authorization': f'Bearer {self.token}'
        }
        
        print(f"\n📦 Creating FormData exactly like frontend...")
        
        with open(file_path, 'rb') as f:
            # Create FormData exactly like frontend does
            files = {
                'files': ('facture_test_siret_valide_20250727_191733.pdf', f, 'application/pdf')
            }
            
            print(f"📤 FormData contents:")
            print(f"  - files: facture_test_siret_valide_20250727_191733.pdf ({file_size} bytes)")
            
            print(f"\n🚀 Starting POST request to /api/batch/batch-process")
            print(f"📍 URL: {API_BASE}/api/batch/batch-process")
            print(f"🔐 Auth: Bearer {self.token[:20]}...")
            print(f"📦 Content-Type: multipart/form-data (auto)")
            
            # Make request with detailed timing
            start_time = time.time()
            
            try:
                print(f"⏳ Sending request...")
                response = self.session.post(
                    f"{API_BASE}/api/batch/batch-process",
                    headers=headers,
                    files=files,
                    timeout=60  # Longer timeout for debugging
                )
                
                request_time = time.time() - start_time
                print(f"⏱️  Request completed in: {request_time:.3f}s")
                
            except requests.exceptions.Timeout:
                print(f"❌ Request timed out after 60 seconds")
                return False
            except Exception as e:
                print(f"❌ Request failed with exception: {str(e)}")
                return False
        
        # Analyze response in detail
        print(f"\n📡 RESPONSE ANALYSIS:")
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"✅ Response JSON: {json.dumps(response_data, indent=2)}")
                
                batch_id = response_data.get('batch_id')
                if batch_id:
                    print(f"\n🔄 Starting detailed status monitoring for batch: {batch_id}")
                    return self.monitor_batch_processing(batch_id)
                else:
                    print(f"❌ No batch_id in response")
                    return False
                    
            except Exception as e:
                print(f"❌ Failed to parse response JSON: {e}")
                print(f"📝 Raw response: {response.text}")
                return False
        else:
            print(f"❌ Request failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"📝 Error JSON: {json.dumps(error_data, indent=2)}")
            except:
                print(f"📝 Raw error response: {response.text}")
            return False
    
    def monitor_batch_processing(self, batch_id):
        """Monitor batch processing with detailed polling"""
        print(f"\n📊 MONITORING BATCH: {batch_id}")
        print("-" * 60)
        
        headers = {'Authorization': f'Bearer {self.token}'}
        poll_count = 0
        max_polls = 120  # 4 minutes maximum (120 * 2 seconds)
        
        while poll_count < max_polls:
            poll_count += 1
            print(f"\n🔄 Poll #{poll_count}/{max_polls}")
            
            try:
                poll_start = time.time()
                response = self.session.get(
                    f"{API_BASE}/api/batch/batch-status/{batch_id}",
                    headers=headers,
                    timeout=10
                )
                poll_time = time.time() - poll_start
                
                print(f"⏱️  Status poll time: {poll_time:.3f}s")
                
                if response.status_code == 200:
                    status_data = response.json()
                    print(f"📊 Status: {status_data.get('status', 'unknown')}")
                    print(f"📈 Progress: {status_data.get('processed_invoices', 0)}/{status_data.get('total_invoices', 0)}")
                    
                    if status_data.get('error'):
                        print(f"❌ Error: {status_data['error']}")
                    
                    if status_data.get('message'):
                        print(f"💬 Message: {status_data['message']}")
                    
                    # Check completion
                    if status_data.get('status') == 'completed':
                        print(f"\n✅ BATCH COMPLETED SUCCESSFULLY!")
                        print(f"📊 Final stats: {json.dumps(status_data, indent=2)}")
                        return True
                    elif status_data.get('status') == 'failed':
                        print(f"\n❌ BATCH FAILED!")
                        print(f"📊 Final stats: {json.dumps(status_data, indent=2)}")
                        return False
                    else:
                        print(f"⏳ Still processing...")
                        
                else:
                    print(f"❌ Status poll failed: {response.status_code}")
                    print(f"📝 Response: {response.text}")
                    
            except Exception as e:
                print(f"❌ Status poll exception: {str(e)}")
            
            # Wait between polls
            if poll_count < max_polls:
                print(f"⏸️  Waiting 2 seconds...")
                time.sleep(2)
        
        print(f"\n⏰ POLLING TIMEOUT after {max_polls * 2} seconds")
        return False
    
    def run_comprehensive_test(self):
        """Run comprehensive test with backend monitoring"""
        print("🚀 COMPREHENSIVE FRONTEND-SPECIFIC TEST")
        print("=" * 80)
        
        # Setup signal handler for clean exit
        def signal_handler(sig, frame):
            print("\n🛑 Test interrupted by user")
            self.stop_backend_monitoring()
            sys.exit(1)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            # Start backend monitoring
            self.start_backend_monitoring()
            
            # Login
            if not self.login():
                return False
            
            # Test the problematic file
            result = self.test_problematic_file_detailed()
            
            return result
            
        finally:
            # Always stop monitoring
            self.stop_backend_monitoring()

if __name__ == "__main__":
    print("🎯 Testing the specific problematic PDF file with frontend simulation")
    print("This will monitor backend logs in real-time to see exactly what happens")
    print("\nPress Ctrl+C to stop at any time\n")
    
    tester = FrontendSpecificTester()
    success = tester.run_comprehensive_test()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 TEST PASSED: The problematic file processed successfully!")
    else:
        print("💥 TEST FAILED: The problematic file has issues!")
    print("=" * 80)