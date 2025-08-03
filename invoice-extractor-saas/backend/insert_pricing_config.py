#!/usr/bin/env python3
"""
Insert default pricing configuration data
"""
import asyncio
import uuid
from decimal import Decimal

from core.database import async_session_maker
from models.subscription import PricingConfig, PricingTier
from sqlalchemy import text, select, func


async def insert_pricing_config():
    """Insert default pricing configuration"""
    
    pricing_tiers = [
        {
            "tier": PricingTier.FREE,
            "name": "Gratuit",
            "description": "Parfait pour découvrir ComptaFlow",
            "price_monthly_eur": Decimal("0.00"),
            "invoice_limit_monthly": 10,
            "unlimited_invoices": False,
            "priority_support": False,
            "api_access": False,
            "custom_export_formats": False,
            "bulk_processing": False,
            "advanced_validation": False,
            "stripe_price_id": None
        },
        {
            "tier": PricingTier.PRO,
            "name": "Pro",
            "description": "Pour les cabinets en croissance",
            "price_monthly_eur": Decimal("29.00"),
            "invoice_limit_monthly": 500,
            "unlimited_invoices": False,
            "priority_support": True,
            "api_access": False,
            "custom_export_formats": True,
            "bulk_processing": True,
            "advanced_validation": True,
            "stripe_price_id": "price_pro_monthly"  # To be set with real Stripe price ID
        },
        {
            "tier": PricingTier.BUSINESS,
            "name": "Business",
            "description": "Pour les cabinets établis",
            "price_monthly_eur": Decimal("59.00"),
            "invoice_limit_monthly": 2000,
            "unlimited_invoices": False,
            "priority_support": True,
            "api_access": True,
            "custom_export_formats": True,
            "bulk_processing": True,
            "advanced_validation": True,
            "stripe_price_id": "price_business_monthly"  # To be set with real Stripe price ID
        },
        {
            "tier": PricingTier.ENTERPRISE,
            "name": "Enterprise",
            "description": "Pour les gros cabinets et fiduciaires",
            "price_monthly_eur": Decimal("99.00"),
            "invoice_limit_monthly": 10000,
            "unlimited_invoices": True,
            "priority_support": True,
            "api_access": True,
            "custom_export_formats": True,
            "bulk_processing": True,
            "advanced_validation": True,
            "stripe_price_id": "price_enterprise_monthly"  # To be set with real Stripe price ID
        }
    ]
    
    async with async_session_maker() as session:
        try:
            # Check if pricing config already exists
            existing_count = await session.execute(select(func.count()).select_from(PricingConfig))
            count = existing_count.scalar()
            
            if count > 0:
                print(f"Pricing configuration already exists ({count} tiers)")
                return
            
            # Insert pricing configurations
            for tier_config in pricing_tiers:
                pricing = PricingConfig(
                    id=uuid.uuid4(),
                    **tier_config
                )
                session.add(pricing)
            
            await session.commit()
            print(f"Successfully inserted {len(pricing_tiers)} pricing tiers")
            
            # Display inserted tiers
            for tier in pricing_tiers:
                print(f"- {tier['name']}: {tier['price_monthly_eur']}€/mois, {tier['invoice_limit_monthly']} factures")
                
        except Exception as e:
            await session.rollback()
            print(f"Error inserting pricing config: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(insert_pricing_config())