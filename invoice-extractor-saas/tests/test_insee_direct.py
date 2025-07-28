#!/usr/bin/env python3
"""
Test INSEE API directly to debug SIRET validation issues
"""

import asyncio
import httpx
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_insee_api_direct():
    """Test INSEE API calls directly"""
    
    # Read API key from backend .env
    insee_api_key = "936f6e1b-e7b5-4e01-af6e-1be7b57e014e"
    
    if not insee_api_key:
        print("❌ No INSEE API key found")
        return
    
    print(f"🔑 Using INSEE API key: {insee_api_key[:10]}...")
    
    # Test SIRET numbers from the invoice
    test_sirets = [
        "65202390200018",  # Fournisseur - CARREFOUR SA
        "57200024200015",  # Client - BOUYGUES SA
    ]
    
    base_url = "https://api.insee.fr/api-sirene/3.11"
    headers = {
        "X-INSEE-Api-Key-Integration": insee_api_key,
        "Accept": "application/json;charset=utf-8;qs=1"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for siret in test_sirets:
            print(f"\n🔍 Testing SIRET: {siret}")
            print("-" * 40)
            
            try:
                # Test direct SIRET endpoint
                url = f"{base_url}/siret/{siret}"
                print(f"📡 Calling: {url}")
                print(f"📋 Headers: {headers}")
                
                response = await client.get(url, headers=headers)
                
                print(f"📊 Status Code: {response.status_code}")
                print(f"📨 Response Headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    data = response.json()
                    print("✅ SUCCESS - SIRET found!")
                    
                    if "etablissement" in data:
                        etab = data["etablissement"]
                        print(f"   SIRET: {etab.get('siret', 'N/A')}")
                        print(f"   État: {etab.get('etatAdministratifEtablissement', 'N/A')}")
                        print(f"   Siège: {etab.get('etablissementSiege', 'N/A')}")
                        
                        if "uniteLegale" in etab:
                            ul = etab["uniteLegale"]
                            print(f"   Nom: {ul.get('denominationUniteLegale', 'N/A')}")
                            print(f"   État UL: {ul.get('etatAdministratifUniteLegale', 'N/A')}")
                    
                elif response.status_code == 404:
                    print("❌ NOT FOUND - SIRET not in INSEE database")
                    try:
                        error_data = response.json()
                        print(f"   Error details: {error_data}")
                    except:
                        print(f"   Raw response: {response.text}")
                        
                elif response.status_code == 401:
                    print("❌ UNAUTHORIZED - API key invalid")
                    print(f"   Response: {response.text}")
                    
                elif response.status_code == 429:
                    print("❌ RATE LIMITED")
                    print(f"   Response: {response.text}")
                    
                else:
                    print(f"❌ ERROR: {response.status_code}")
                    print(f"   Response: {response.text}")
                    
            except Exception as e:
                print(f"❌ Exception: {e}")
                print(f"   Type: {type(e)}")

async def test_api_key_validity():
    """Test if the API key is valid by making a simple request"""
    
    insee_api_key = "936f6e1b-e7b5-4e01-af6e-1be7b57e014e"
    
    print("🔑 Testing API key validity...")
    
    base_url = "https://api.insee.fr/api-sirene/3.11"
    headers = {
        "X-INSEE-Api-Key-Integration": insee_api_key,
        "Accept": "application/json;charset=utf-8;qs=1"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test with a known valid SIRET (Carrefour headquarters)
            test_siret = "65201405100033"  # Known Carrefour SIRET
            url = f"{base_url}/siret/{test_siret}"
            
            print(f"📡 Testing with known SIRET: {test_siret}")
            response = await client.get(url, headers=headers)
            
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ API key is valid and working!")
                return True
            elif response.status_code == 401:
                print("❌ API key is invalid or expired")
                return False
            else:
                print(f"❓ Unexpected response: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ API test failed: {e}")
            return False

async def main():
    """Main test function"""
    print("🧪 INSEE API Direct Test")
    print("=" * 50)
    
    # Test API key first
    api_valid = await test_api_key_validity()
    
    if not api_valid:
        print("\n❌ API key validation failed - cannot proceed with SIRET tests")
        return
    
    print("\n" + "=" * 50)
    # Test the actual SIRET numbers from the invoice
    await test_insee_api_direct()

if __name__ == "__main__":
    asyncio.run(main())