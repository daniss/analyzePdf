"""
User CRUD operations with comprehensive error handling and validation
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from typing import Optional
import uuid

from models.user import User
from schemas.auth import UserCreate
from core.security import get_password_hash
from core.gdpr_helpers import log_audit_event
from models.gdpr_models import AuditEventType


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """Get user by ID with subscription data and audit logging"""
    try:
        result = await db.execute(
            select(User)
            .options(selectinload(User.subscription))
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"User profile accessed: {user.email}",
                user_id=user_id,
                system_component="user_crud",
                risk_level="low"
            )
        
        return user
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Failed to access user profile: {str(e)}",
            user_id=user_id,
            system_component="user_crud",
            risk_level="medium"
        )
        raise


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email address"""
    try:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Failed to access user by email: {str(e)}",
            system_component="user_crud",
            risk_level="medium"
        )
        raise


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """Create new user with password hashing and audit logging"""
    try:
        # Hash the password
        hashed_password = get_password_hash(user.password)
        
        # Create user instance
        db_user = User(
            email=user.email,
            hashed_password=hashed_password,
            company_name=user.company_name,
            is_active=True
        )
        
        # Add to database
        db.add(db_user)
        await db.flush()  # Get the ID without committing
        
        # Log user creation
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"New user account created: {user.email}",
            user_id=db_user.id,
            system_component="user_crud",
            risk_level="low",
            legal_basis="contract_performance",
            processing_purpose="user_registration",
            data_categories_accessed=["identifying_data", "contact_data"]
        )
        
        await db.commit()
        await db.refresh(db_user)
        return db_user
        
    except IntegrityError as e:
        await db.rollback()
        if "email" in str(e):
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"Failed user creation - email already exists: {user.email}",
                system_component="user_crud",
                risk_level="low"
            )
            raise ValueError("Email already registered")
        raise
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Failed user creation: {str(e)}",
            system_component="user_crud",
            risk_level="high"
        )
        raise


async def update_user(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> Optional[User]:
    """Update user information with audit logging"""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Track what fields are being updated
        updated_fields = []
        for key, value in kwargs.items():
            if hasattr(user, key) and getattr(user, key) != value:
                setattr(user, key, value)
                updated_fields.append(key)
        
        if updated_fields:
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"User profile updated. Fields: {', '.join(updated_fields)}",
                user_id=user_id,
                system_component="user_crud",
                risk_level="low",
                operation_details={"updated_fields": updated_fields}
            )
            
            await db.commit()
            await db.refresh(user)
        
        return user
        
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Failed user update: {str(e)}",
            user_id=user_id,
            system_component="user_crud",
            risk_level="medium"
        )
        raise


async def deactivate_user(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """Deactivate user account (soft delete) with audit logging"""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        user.is_active = False
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"User account deactivated: {user.email}",
            user_id=user_id,
            system_component="user_crud",
            risk_level="medium",
            legal_basis="legitimate_interest",
            processing_purpose="account_management"
        )
        
        await db.commit()
        await db.refresh(user)
        return user
        
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Failed user deactivation: {str(e)}",
            user_id=user_id,
            system_component="user_crud",
            risk_level="high"
        )
        raise


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate user with password verification and audit logging"""
    from core.security import verify_password
    
    try:
        user = await get_user_by_email(db, email)
        
        if not user:
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Authentication failed - user not found: {email}",
                system_component="user_crud",
                risk_level="medium"
            )
            return None
        
        if not user.is_active:
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Authentication failed - account inactive: {email}",
                user_id=user.id,
                system_component="user_crud",
                risk_level="medium"
            )
            return None
        
        if not verify_password(password, user.hashed_password):
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Authentication failed - invalid password: {email}",
                user_id=user.id,
                system_component="user_crud",
                risk_level="high"
            )
            return None
        
        # Successful authentication
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"User authenticated successfully: {email}",
            user_id=user.id,
            system_component="user_crud",
            risk_level="low",
            legal_basis="legitimate_interest",
            processing_purpose="authentication"
        )
        
        return user
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Authentication error: {str(e)}",
            system_component="user_crud",
            risk_level="high"
        )
        raise