"""
Initialize TVA validation data

This script populates the database with French TVA product categories,
exemption rules, and rate history for comprehensive TVA validation.
"""

import asyncio
import sys
import os
from datetime import datetime, date
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_async_session
from models.tva_models import (
    TVAProductCategory,
    TVAExemptionRule,
    TVARateHistory,
    FRENCH_TVA_PRODUCT_CATEGORIES,
    FRENCH_TVA_EXEMPTION_RULES
)

async def init_tva_product_categories(db_session: AsyncSession):
    """Initialize TVA product categories"""
    
    print("Initializing TVA product categories...")
    
    for category_data in FRENCH_TVA_PRODUCT_CATEGORIES:
        # Check if category already exists
        result = await db_session.execute(
            select(TVAProductCategory).where(
                TVAProductCategory.category_code == category_data["category_code"]
            )
        )
        existing_category = result.scalar_one_or_none()
        
        if existing_category:
            print(f"Category {category_data['category_code']} already exists, skipping...")
            continue
        
        # Create new category
        category = TVAProductCategory(
            category_code=category_data["category_code"],
            category_name=category_data["category_name"],
            description=category_data["description"],
            standard_tva_rate=category_data["standard_tva_rate"],
            keywords=category_data.get("keywords", []),
            naf_codes=category_data.get("naf_codes", []),
            legal_reference=category_data.get("legal_reference"),
            category_level=category_data.get("category_level", 1),
            has_special_conditions=category_data.get("has_special_conditions", False),
            special_conditions=category_data.get("special_conditions"),
            exemption_conditions=category_data.get("exemption_conditions")
        )
        
        db_session.add(category)
        print(f"Added category: {category_data['category_code']} ({category_data['standard_tva_rate']}%)")
    
    await db_session.commit()
    print(f"Initialized {len(FRENCH_TVA_PRODUCT_CATEGORIES)} TVA product categories")

async def init_tva_exemption_rules(db_session: AsyncSession):
    """Initialize TVA exemption rules"""
    
    print("Initializing TVA exemption rules...")
    
    for rule_data in FRENCH_TVA_EXEMPTION_RULES:
        # Check if rule already exists
        result = await db_session.execute(
            select(TVAExemptionRule).where(
                TVAExemptionRule.exemption_code == rule_data["exemption_code"]
            )
        )
        existing_rule = result.scalar_one_or_none()
        
        if existing_rule:
            print(f"Rule {rule_data['exemption_code']} already exists, skipping...")
            continue
        
        # Create new rule
        rule = TVAExemptionRule(
            exemption_code=rule_data["exemption_code"],
            exemption_name=rule_data["exemption_name"],
            description=rule_data["description"],
            legal_reference=rule_data["legal_reference"],
            cgi_article=rule_data.get("cgi_article"),
            eu_directive=rule_data.get("eu_directive"),
            eligibility_conditions=rule_data["eligibility_conditions"],
            required_documents=rule_data.get("required_documents", []),
            validation_rules=rule_data["validation_rules"]
        )
        
        db_session.add(rule)
        print(f"Added exemption rule: {rule_data['exemption_code']}")
    
    await db_session.commit()
    print(f"Initialized {len(FRENCH_TVA_EXEMPTION_RULES)} TVA exemption rules")

async def init_tva_rate_history(db_session: AsyncSession):
    """Initialize TVA rate history"""
    
    print("Initializing TVA rate history...")
    
    # Current French TVA rates (as of 2024)
    current_rates = [
        {
            "rate_type": "standard",
            "rate_value": 20.0,
            "description": "Taux normal de TVA",
            "legal_reference": "CGI art. 278",
            "effective_from": date(2014, 1, 1),  # Last change
            "change_reason": "Augmentation du taux normal de 19,6% à 20%"
        },
        {
            "rate_type": "reduced_1",
            "rate_value": 10.0,
            "description": "Taux réduit - restauration, hôtellerie, transport",
            "legal_reference": "CGI art. 279 bis",
            "effective_from": date(2014, 1, 1),
            "change_reason": "Taux réduit maintenu à 10%"
        },
        {
            "rate_type": "reduced_2",
            "rate_value": 5.5,
            "description": "Taux réduit - produits de première nécessité",
            "legal_reference": "CGI art. 278-0 bis",
            "effective_from": date(2000, 4, 1),
            "change_reason": "Introduction du taux réduit de 5,5%"
        },
        {
            "rate_type": "super_reduced",
            "rate_value": 2.1,
            "description": "Taux super réduit - presse, médicaments remboursables",
            "legal_reference": "CGI art. 298 septies",
            "effective_from": date(1989, 9, 19),
            "change_reason": "Taux spécial pour la presse quotidienne"
        },
        {
            "rate_type": "exempt",
            "rate_value": 0.0,
            "description": "Exonération de TVA",
            "legal_reference": "CGI art. 261 et suivants",
            "effective_from": date(1968, 1, 1),
            "change_reason": "Exonérations diverses selon la nature de l'activité"
        }
    ]
    
    for rate_data in current_rates:
        # Check if rate already exists
        result = await db_session.execute(
            select(TVARateHistory).where(
                TVARateHistory.rate_type == rate_data["rate_type"],
                TVARateHistory.rate_value == rate_data["rate_value"],
                TVARateHistory.effective_from == rate_data["effective_from"]
            )
        )
        existing_rate = result.scalar_one_or_none()
        
        if existing_rate:
            print(f"Rate {rate_data['rate_type']} already exists, skipping...")
            continue
        
        # Create new rate history entry
        rate_history = TVARateHistory(
            rate_type=rate_data["rate_type"],
            rate_value=rate_data["rate_value"],
            description=rate_data["description"],
            legal_reference=rate_data["legal_reference"],
            effective_from=rate_data["effective_from"],
            change_reason=rate_data["change_reason"]
        )
        
        db_session.add(rate_history)
        print(f"Added rate history: {rate_data['rate_type']} = {rate_data['rate_value']}%")
    
    await db_session.commit()
    print(f"Initialized {len(current_rates)} TVA rate history entries")

async def init_extended_product_categories(db_session: AsyncSession):
    """Initialize extended product categories with more detailed mappings"""
    
    print("Initializing extended product categories...")
    
    # Additional detailed categories
    extended_categories = [
        # Food subcategories (5.5%)
        {
            "category_code": "FOOD_BEVERAGES",
            "category_name": "Boissons non alcoolisées",
            "description": "Eaux, jus de fruits, sodas, boissons chaudes",
            "standard_tva_rate": 5.5,
            "keywords": ["eau", "jus", "soda", "thé", "café", "infusion", "sirop"],
            "legal_reference": "CGI art. 278-0 bis A",
            "category_level": 2
        },
        {
            "category_code": "FOOD_DAIRY",
            "category_name": "Produits laitiers",
            "description": "Lait, fromage, yaourts, beurre, crème",
            "standard_tva_rate": 5.5,
            "keywords": ["lait", "fromage", "yaourt", "beurre", "crème", "lactose"],
            "legal_reference": "CGI art. 278-0 bis A",
            "category_level": 2
        },
        {
            "category_code": "FOOD_MEAT",
            "category_name": "Viandes et poissons",
            "description": "Viandes, volailles, poissons, fruits de mer",
            "standard_tva_rate": 5.5,
            "keywords": ["viande", "bœuf", "porc", "agneau", "volaille", "poisson", "saumon", "crevette"],
            "legal_reference": "CGI art. 278-0 bis A",
            "category_level": 2
        },
        
        # Services subcategories
        {
            "category_code": "SERVICES_IT",
            "category_name": "Services informatiques",
            "description": "Développement, maintenance, conseil informatique",
            "standard_tva_rate": 20.0,
            "keywords": ["développement", "programmation", "site web", "application", "software", "maintenance informatique"],
            "naf_codes": ["6201Z", "6202A", "6202B", "6203Z", "6209Z"],
            "legal_reference": "CGI art. 256",
            "category_level": 2
        },
        {
            "category_code": "SERVICES_CONSULTING",
            "category_name": "Conseil et expertise",
            "description": "Services de conseil, audit, expertise",
            "standard_tva_rate": 20.0,
            "keywords": ["conseil", "consulting", "audit", "expertise", "stratégie", "management"],
            "naf_codes": ["7022Z", "6920Z", "7112B"],
            "legal_reference": "CGI art. 256",
            "category_level": 2
        },
        {
            "category_code": "SERVICES_MARKETING",
            "category_name": "Marketing et communication",
            "description": "Publicité, marketing, communication, design",
            "standard_tva_rate": 20.0,
            "keywords": ["publicité", "marketing", "communication", "design", "graphisme", "brand"],
            "naf_codes": ["7311Z", "7312Z", "7320Z"],
            "legal_reference": "CGI art. 256",
            "category_level": 2
        },
        
        # Transport subcategories (10%)
        {
            "category_code": "TRANSPORT_PASSENGER",
            "category_name": "Transport de voyageurs",
            "description": "Transport public de voyageurs",
            "standard_tva_rate": 10.0,
            "keywords": ["transport", "voyageur", "bus", "métro", "tramway", "taxi"],
            "naf_codes": ["4931Z", "4932Z", "4939A"],
            "legal_reference": "CGI art. 279 bis",
            "category_level": 2
        },
        {
            "category_code": "TRANSPORT_GOODS",
            "category_name": "Transport de marchandises",
            "description": "Transport et livraison de marchandises",
            "standard_tva_rate": 20.0,  # Note: goods transport is standard rate
            "keywords": ["livraison", "transport marchandise", "fret", "logistique"],
            "naf_codes": ["4941A", "4941B", "4942Z"],
            "legal_reference": "CGI art. 256",
            "category_level": 2
        },
        
        # Culture and sports (10%)
        {
            "category_code": "CULTURE_MUSEUMS",
            "category_name": "Musées et monuments",
            "description": "Entrées musées, monuments, sites culturels",
            "standard_tva_rate": 10.0,
            "keywords": ["musée", "monument", "château", "exposition", "patrimoine"],
            "naf_codes": ["9103Z"],
            "legal_reference": "CGI art. 279 bis",
            "category_level": 2
        },
        {
            "category_code": "CULTURE_SHOWS",
            "category_name": "Spectacles et événements",
            "description": "Théâtre, concerts, spectacles, cinéma",
            "standard_tva_rate": 10.0,
            "keywords": ["théâtre", "concert", "spectacle", "cinéma", "festival", "show"],
            "naf_codes": ["9001Z", "9002Z", "5914Z"],
            "legal_reference": "CGI art. 279 bis",
            "category_level": 2
        }
    ]
    
    for category_data in extended_categories:
        # Check if category already exists
        result = await db_session.execute(
            select(TVAProductCategory).where(
                TVAProductCategory.category_code == category_data["category_code"]
            )
        )
        existing_category = result.scalar_one_or_none()
        
        if existing_category:
            print(f"Extended category {category_data['category_code']} already exists, skipping...")
            continue
        
        # Create new category
        category = TVAProductCategory(
            category_code=category_data["category_code"],
            category_name=category_data["category_name"],
            description=category_data["description"],
            standard_tva_rate=category_data["standard_tva_rate"],
            keywords=category_data.get("keywords", []),
            naf_codes=category_data.get("naf_codes", []),
            legal_reference=category_data.get("legal_reference"),
            category_level=category_data.get("category_level", 2)
        )
        
        db_session.add(category)
        print(f"Added extended category: {category_data['category_code']} ({category_data['standard_tva_rate']}%)")
    
    await db_session.commit()
    print(f"Initialized {len(extended_categories)} extended TVA product categories")

async def main():
    """Main initialization function"""
    
    print("=== TVA Data Initialization ===")
    print("This script will populate the database with French TVA validation data")
    print()
    
    try:
        # Get database session
        async for db_session in get_async_session():
            # Initialize all TVA data
            await init_tva_product_categories(db_session)
            await init_extended_product_categories(db_session)
            await init_tva_exemption_rules(db_session)
            await init_tva_rate_history(db_session)
            
            print()
            print("=== Initialization Complete ===")
            print("✅ TVA product categories initialized")
            print("✅ TVA exemption rules initialized")
            print("✅ TVA rate history initialized")
            print()
            print("The comprehensive TVA validation system is now ready for use!")
            break
    
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())