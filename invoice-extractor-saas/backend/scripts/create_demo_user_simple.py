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
            print(f"Email: demo@example.com")
            print(f"Password: demo123456")
            return
        
        # Create user with hashed password
        db_user = User(
            email="demo@example.com",
            hashed_password=get_password_hash("demo123456"),
            company_name="Demo Company",
            is_active=True
        )
        
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        print(f"Demo user created successfully!")
        print(f"Email: demo@example.com")
        print(f"Password: demo123456")
        print(f"User ID: {db_user.id}")


if __name__ == "__main__":
    asyncio.run(create_demo_account())