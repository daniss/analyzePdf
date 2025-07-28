#!/usr/bin/env python3
"""
Test the SIRET numbers from the sample invoice
"""

import asyncio
import httpx

async def test_sample_sirets():
    """Test SIRET numbers from the sample invoice"""
    
    insee_api_key = "936f6e1b-e7b5-4e01-af6e-1be7b57e014e"
    
    # SIRET numbers from the sample invoice
    test_sirets = [
        ("65201405100033", "CARREFOUR SA from sample"),
        ("54209118000023", "AUCHAN RETAIL FRANCE from sample"),
        ("65202390200018", "User's Fournisseur SIRET"),
        ("57200024200015", "User's Client SIRET"),
    ]
    
    base_url = "https://api.insee.fr/api-sirene/3.11"
    headers = {
        "X-INSEE-Api-Key-Integration": insee_api_key,
        "Accept": "application/json;charset=utf-8;qs=1"
    }
    
    print("🧪 Testing SIRET numbers from sample vs user data")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for siret, description in test_sirets:
            print(f"\n🔍 Testing: {siret} ({description})")
            print("-" * 50)
            
            try:
                url = f"{base_url}/siret/{siret}"
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    print("✅ FOUND in INSEE database!")
                    
                    etab = data.get("etablissement", {})
                    ul = etab.get("uniteLegale", {})
                    
                    print(f"   Nom: {ul.get('denominationUniteLegale', 'N/A')}")
                    print(f"   État établissement: {etab.get('etatAdministratifEtablissement', 'N/A')}")
                    print(f"   État unité légale: {ul.get('etatAdministratifUniteLegale', 'N/A')}")
                    
                elif response.status_code == 404:
                    print("❌ NOT FOUND in INSEE database")
                    error_data = response.json()
                    print(f"   Message: {error_data.get('header', {}).get('message', 'No message')}")
                    
                else:
                    print(f"❓ HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_sample_sirets())