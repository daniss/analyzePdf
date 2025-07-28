#!/usr/bin/env python3
"""
Create a fresh user account for testing
"""

import asyncio
import sys
import os
sys.path.append('/home/danis/code/analyzePdf/invoice-extractor-saas/backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from models.user import User
from core.config import settings
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_fresh_user():
    """Create a fresh user account"""
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # User details
    email = "fresh@invoiceai.com"
    password = "freshpassword123"
    
    async with async_session() as db:
        try:
            # Check if user already exists
            from sqlalchemy import select
            result = await db.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"🔄 User {email} already exists, deleting...")
                
                # Delete all user's invoices first
                from sqlalchemy import text
                await db.execute(text("DELETE FROM invoices WHERE user_id = :user_id"), {"user_id": existing_user.id})
                
                # Delete user
                await db.delete(existing_user)
                await db.commit()
                print(f"✅ Deleted existing user and all their data")
            
            # Create new user
            hashed_password = pwd_context.hash(password)
            
            new_user = User(
                id=uuid.uuid4(),
                email=email,
                hashed_password=hashed_password,
                is_active=True,
                company_name="Fresh Test Company"
            )
            
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            
            print(f"🎉 Created fresh user account:")
            print(f"  📧 Email: {email}")
            print(f"  🔑 Password: {password}")
            print(f"  🆔 User ID: {new_user.id}")
            print(f"  ✅ Status: Active")
            print(f"  🏢 Company: Fresh Test Company")
            print(f"\n🚀 Ready for testing!")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            await db.rollback()
            return False
        finally:
            await engine.dispose()

if __name__ == "__main__":
    print("🔧 Creating fresh user account for testing...")
    print("=" * 50)
    
    success = asyncio.run(create_fresh_user())
    
    if success:
        print("\n✅ SUCCESS: Fresh user account created!")
        print("You can now login with:")
        print("  Email: fresh@invoiceai.com")
        print("  Password: freshpassword123")
    else:
        print("\n❌ FAILED: Could not create fresh user account")