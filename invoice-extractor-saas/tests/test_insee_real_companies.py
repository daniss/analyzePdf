#!/usr/bin/env python3
"""
Test INSEE API with definitely real French companies to verify API functionality
"""

import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_insee_with_search():
    """Test INSEE API using search instead of direct SIRET lookup"""
    
    insee_api_key = "936f6e1b-e7b5-4e01-af6e-1be7b57e014e"
    
    base_url = "https://api.insee.fr/api-sirene/3.11"
    headers = {
        "X-INSEE-Api-Key-Integration": insee_api_key,
        "Accept": "application/json;charset=utf-8;qs=1"
    }
    
    # Test with company name search first to find real SIRETs
    test_companies = [
        "CARREFOUR",
        "BOUYGUES",
        "RENAULT",
        "TOTAL"
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for company in test_companies:
            print(f"\n🔍 Searching for: {company}")
            print("-" * 40)
            
            try:
                # Search by company name
                url = f"{base_url}/siret"
                params = {
                    "q": f"denominationUniteLegale:{company}",
                    "nombre": 3  # Get first 3 results
                }
                
                print(f"📡 URL: {url}")
                print(f"📋 Params: {params}")
                
                response = await client.get(url, params=params, headers=headers)
                
                print(f"📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print("✅ Search successful!")
                    
                    if "etablissements" in data and data["etablissements"]:
                        print(f"   Found {len(data['etablissements'])} establishments")
                        
                        for i, etab in enumerate(data["etablissements"][:2]):
                            print(f"\n   📍 Establishment {i+1}:")
                            print(f"      SIRET: {etab.get('siret', 'N/A')}")
                            print(f"      État: {etab.get('etatAdministratifEtablissement', 'N/A')}")
                            
                            ul = etab.get('uniteLegale', {})
                            print(f"      Nom: {ul.get('denominationUniteLegale', 'N/A')}")
                            print(f"      SIREN: {ul.get('siren', 'N/A')}")
                            print(f"      État UL: {ul.get('etatAdministratifUniteLegale', 'N/A')}")
                            
                            # Now test direct SIRET lookup with this real SIRET
                            real_siret = etab.get('siret')
                            if real_siret:
                                await test_direct_siret_lookup(client, real_siret, headers)
                    else:
                        print("   No establishments found")
                        
                elif response.status_code == 404:
                    print(f"   No results for {company}")
                elif response.status_code == 401:
                    print("   ❌ UNAUTHORIZED - API key issue")
                    print(f"   Response: {response.text}")
                    break
                else:
                    print(f"   ❌ Error: {response.status_code}")
                    print(f"   Response: {response.text}")
                    
            except Exception as e:
                print(f"❌ Exception searching {company}: {e}")

async def test_direct_siret_lookup(client, siret, headers):
    """Test direct SIRET lookup"""
    print(f"\n      🔍 Testing direct lookup for SIRET: {siret}")
    
    try:
        base_url = "https://api.insee.fr/api-sirene/3.11"
        url = f"{base_url}/siret/{siret}"
        
        response = await client.get(url, headers=headers)
        print(f"      📊 Direct lookup status: {response.status_code}")
        
        if response.status_code == 200:
            print("      ✅ Direct lookup successful!")
        elif response.status_code == 404:
            print("      ❌ Not found in direct lookup (strange)")
        else:
            print(f"      ❌ Direct lookup error: {response.text}")
            
    except Exception as e:
        print(f"      ❌ Direct lookup exception: {e}")

async def main():
    """Main test"""
    print("🧪 INSEE API Real Companies Test")
    print("=" * 50)
    
    await test_insee_with_search()

if __name__ == "__main__":
    asyncio.run(main())