#!/usr/bin/env python3
"""Script to create a demo user account"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from core.database import async_session_maker
from core.security import get_password_hash
from models.user import User
from models.gdpr_models import DataSubject
from crud.user import create_user
from schemas.auth import UserCreate


async def create_demo_account():
    async with async_session_maker() as db:
        # Check if demo user already exists
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.email == "demo@example.com"))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print("Demo user already exists!")
            return
        
        # Create demo user
        demo_user = UserCreate(
            email="demo@example.com",
            password="demo123456",
            company_name="Demo Company"
        )
        
        # Create user with hashed password
        db_user = User(
            email=demo_user.email,
            hashed_password=get_password_hash(demo_user.password),
            company_name=demo_user.company_name,
            is_active=True
        )
        
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        # Create associated GDPR data subject
        data_subject = DataSubject(
            user_id=db_user.id,
            email=db_user.email,
            full_name="Demo User",
            consent_given=True,
            consent_purposes=["invoice_processing", "data_analysis"],
            data_categories=["contact_info", "business_data"]
        )
        
        db.add(data_subject)
        await db.commit()
        
        print(f"Demo user created successfully!")
        print(f"Email: demo@example.com")
        print(f"Password: demo123456")
        print(f"User ID: {db_user.id}")


if __name__ == "__main__":
    asyncio.run(create_demo_account())