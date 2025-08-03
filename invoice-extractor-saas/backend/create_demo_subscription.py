#!/usr/bin/env python3
"""
Create subscription for demo user
"""
import asyncio
import uuid
from datetime import datetime, timedelta

from core.database import async_session_maker
from models.subscription import Subscription, PricingTier, SubscriptionStatus
from models.user import User
from sqlalchemy import select


async def create_demo_subscription():
    """Create subscription for demo user"""
    
    async with async_session_maker() as session:
        try:
            # Find demo user
            result = await session.execute(
                select(User).where(User.email == "demo@comptaflow.fr")
            )
            demo_user = result.scalar_one_or_none()
            
            if not demo_user:
                print("Demo user not found! Please run create_demo_user.py first")
                return
            
            # Check if subscription already exists
            existing_sub = await session.execute(
                select(Subscription).where(Subscription.user_id == demo_user.id)
            )
            if existing_sub.scalar_one_or_none():
                print("Demo user already has a subscription")
                return
            
            # Create subscription
            now = datetime.utcnow()
            subscription = Subscription(
                id=uuid.uuid4(),
                user_id=demo_user.id,
                pricing_tier=PricingTier.PRO,  # Give demo user Pro tier
                status=SubscriptionStatus.ACTIVE,
                monthly_invoice_limit=500,  # Pro tier limit
                monthly_invoices_processed=0,
                quota_reset_date=now + timedelta(days=30),
                current_period_start=now,
                current_period_end=now + timedelta(days=30)
            )
            
            session.add(subscription)
            await session.commit()
            
            print(f"Successfully created Pro subscription for demo user")
            print(f"- User: {demo_user.email}")
            print(f"- Company: {demo_user.company_name}")
            print(f"- Tier: PRO (500 factures/mois)")
            print(f"- Status: ACTIVE")
            print(f"- Period: {subscription.current_period_start} to {subscription.current_period_end}")
                
        except Exception as e:
            await session.rollback()
            print(f"Error creating demo subscription: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(create_demo_subscription())