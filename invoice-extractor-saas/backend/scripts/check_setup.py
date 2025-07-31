#!/usr/bin/env python3
"""Check if ComptaFlow is properly configured for MVP"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.database import async_session_maker, engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_setup():
    """Check all required configurations for MVP"""
    
    print("🔍 ComptaFlow MVP Setup Check\n")
    
    errors = []
    warnings = []
    
    # 1. Check required API keys
    print("1. Checking API Keys...")
    
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("gsk_REPLACE"):
        errors.append("❌ GROQ_API_KEY not configured - This is REQUIRED for invoice processing!")
    else:
        print("   ✅ Groq API key configured")
    
    if not settings.INSEE_API_KEY or settings.INSEE_API_KEY == "REPLACE_WITH_YOUR_INSEE_API_KEY":
        warnings.append("⚠️  INSEE API not configured - SIRET validation will be limited")
    else:
        print("   ✅ INSEE API configured")
    
    # 2. Check database connection
    print("\n2. Checking Database Connection...")
    try:
        async with async_session_maker() as db:
            result = await db.execute(text("SELECT 1"))
            result.scalar()
            print("   ✅ Database connection successful")
    except Exception as e:
        errors.append(f"❌ Database connection failed: {str(e)}")
    
    # 3. Check Redis connection
    print("\n3. Checking Redis Connection...")
    try:
        import aioredis
        redis = await aioredis.from_url(settings.REDIS_URL)
        await redis.ping()
        await redis.close()
        print("   ✅ Redis connection successful")
    except ImportError:
        warnings.append("⚠️  aioredis not installed - Redis features disabled")
    except Exception as e:
        warnings.append(f"⚠️  Redis connection failed: {str(e)}")
    
    # 4. Check tables exist
    print("\n4. Checking Database Tables...")
    try:
        async with async_session_maker() as db:
            # Check if users table exists
            result = await db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                );
            """))
            if result.scalar():
                print("   ✅ Database tables exist")
            else:
                errors.append("❌ Database tables not found - Run migrations!")
    except Exception as e:
        errors.append(f"❌ Failed to check tables: {str(e)}")
    
    # 5. Check encryption keys
    print("\n5. Checking Security Configuration...")
    if len(settings.SECRET_KEY) < 32:
        warnings.append("⚠️  SECRET_KEY should be at least 32 characters")
    else:
        print("   ✅ Secret key configured")
    
    if len(settings.ENCRYPTION_KEY) < 32:
        warnings.append("⚠️  ENCRYPTION_KEY should be at least 32 characters")
    else:
        print("   ✅ Encryption key configured")
    
    # Summary
    print("\n" + "="*50)
    print("📊 SETUP SUMMARY\n")
    
    if errors:
        print("❌ CRITICAL ERRORS (Must fix for MVP):")
        for error in errors:
            print(f"   {error}")
        print()
    
    if warnings:
        print("⚠️  WARNINGS (Can work without these):")
        for warning in warnings:
            print(f"   {warning}")
        print()
    
    if not errors:
        print("✅ ComptaFlow is ready for MVP!")
        print("\nNext steps:")
        print("1. Run migrations: alembic upgrade head")
        print("2. Initialize TVA data: python scripts/init_tva_data.py")
        print("3. Create demo user: python scripts/create_demo_user.py")
        print("4. Start the app: docker-compose up")
    else:
        print("❌ Please fix the errors above before proceeding!")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(check_setup())
    sys.exit(0 if success else 1)