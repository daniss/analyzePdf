#!/usr/bin/env python3
"""
Clean up database - remove all test invoices and related data
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append('backend')

async def cleanup_database():
    """Clean up all test data from database"""
    
    try:
        from core.database import get_async_session
        from models.user import Invoice
        from models.gdpr_models import AuditLog, DataSubject
        from models.french_compliance import INSEEAPICall, FrenchComplianceValidation
        from sqlalchemy import delete
        
        print("🧹 Starting database cleanup...")
        
        async with get_async_session() as session:
            # Count existing records
            from sqlalchemy import select, func
            
            invoice_count = await session.scalar(select(func.count(Invoice.id)))
            audit_count = await session.scalar(select(func.count(AuditLog.id)))
            
            print(f"📊 Found {invoice_count} invoices and {audit_count} audit logs")
            
            if invoice_count == 0:
                print("✅ Database is already clean!")
                return
            
            # Delete all invoices (this should cascade to related records)
            print("🗑️ Deleting all invoices...")
            result = await session.execute(delete(Invoice))
            deleted_invoices = result.rowcount
            
            # Delete audit logs
            print("🗑️ Deleting audit logs...")
            result = await session.execute(delete(AuditLog))
            deleted_audits = result.rowcount
            
            # Delete INSEE API calls
            try:
                result = await session.execute(delete(INSEEAPICall))
                deleted_insee = result.rowcount
                print(f"🗑️ Deleted {deleted_insee} INSEE API call records")
            except Exception as e:
                print(f"ℹ️ INSEE API calls: {e}")
            
            # Delete French compliance validations
            try:
                result = await session.execute(delete(FrenchComplianceValidation))
                deleted_compliance = result.rowcount
                print(f"🗑️ Deleted {deleted_compliance} compliance validation records")
            except Exception as e:
                print(f"ℹ️ Compliance validations: {e}")
            
            # Delete data subjects (GDPR)
            try:
                result = await session.execute(delete(DataSubject))
                deleted_subjects = result.rowcount
                print(f"🗑️ Deleted {deleted_subjects} data subject records")
            except Exception as e:
                print(f"ℹ️ Data subjects: {e}")
            
            # Commit all changes
            await session.commit()
            
            print(f"✅ Database cleanup complete!")
            print(f"   📄 Deleted {deleted_invoices} invoices")
            print(f"   📋 Deleted {deleted_audits} audit logs")
            print("🎯 Database is now clean and ready for fresh testing")
            
    except Exception as e:
        print(f"❌ Database cleanup failed: {e}")
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    asyncio.run(cleanup_database())