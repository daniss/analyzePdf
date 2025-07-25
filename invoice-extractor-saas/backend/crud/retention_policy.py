"""
Retention Policy CRUD operations for GDPR compliance
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timedelta

from models.gdpr_models import RetentionPolicy, AuditEventType, DataCategory, ProcessingPurpose
from core.gdpr_helpers import log_audit_event


async def create_retention_policy(
    db: AsyncSession,
    name: str,
    description: Optional[str],
    retention_period_months: int,
    applies_to_data_categories: List[DataCategory],
    applies_to_processing_purposes: List[ProcessingPurpose],
    legal_basis: str,
    jurisdiction: str,
    created_by: uuid.UUID,
    deletion_grace_period_days: int = 30
) -> RetentionPolicy:
    """Create new retention policy with audit logging"""
    try:
        # Convert enums to JSON-serializable format
        data_categories_json = [category.value for category in applies_to_data_categories]
        processing_purposes_json = [purpose.value for purpose in applies_to_processing_purposes]
        
        policy = RetentionPolicy(
            name=name,
            description=description,
            retention_period_months=retention_period_months,
            deletion_grace_period_days=deletion_grace_period_days,
            applies_to_data_categories=data_categories_json,
            applies_to_processing_purposes=processing_purposes_json,
            legal_basis=legal_basis,
            jurisdiction=jurisdiction,
            effective_date=datetime.utcnow(),
            created_by=created_by
        )
        
        db.add(policy)
        await db.flush()
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Retention policy created: {name}",
            user_id=created_by,
            system_component="retention_policy_crud",
            legal_basis="legal_obligation",
            processing_purpose="data_retention_management",
            risk_level="low",
            operation_details={
                "policy_name": name,
                "retention_months": retention_period_months,
                "data_categories": data_categories_json,
                "processing_purposes": processing_purposes_json
            }
        )
        
        await db.commit()
        await db.refresh(policy)
        return policy
        
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Failed retention policy creation: {str(e)}",
            user_id=created_by,
            system_component="retention_policy_crud",
            risk_level="medium"
        )
        raise


async def get_retention_policy_by_id(
    db: AsyncSession,
    policy_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[RetentionPolicy]:
    """Get retention policy by ID with access control"""
    try:
        result = await db.execute(
            select(RetentionPolicy).where(
                and_(
                    RetentionPolicy.id == policy_id,
                    RetentionPolicy.created_by == user_id
                )
            )
        )
        policy = result.scalar_one_or_none()
        
        if policy:
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Retention policy accessed: {policy.name}",
                user_id=user_id,
                system_component="retention_policy_crud",
                risk_level="low"
            )
        
        return policy
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Failed retention policy access: {str(e)}",
            user_id=user_id,
            system_component="retention_policy_crud",
            risk_level="medium"
        )
        raise


async def get_user_retention_policies(
    db: AsyncSession,
    user_id: uuid.UUID,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100
) -> List[RetentionPolicy]:
    """Get retention policies for a user with filtering"""
    try:
        query = select(RetentionPolicy).where(RetentionPolicy.created_by == user_id)
        
        if active_only:
            query = query.where(RetentionPolicy.is_active == True)
        
        query = query.offset(skip).limit(limit).order_by(RetentionPolicy.created_at.desc())
        
        result = await db.execute(query)
        policies = result.scalars().all()
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Retention policies list accessed ({len(policies)} records)",
            user_id=user_id,
            system_component="retention_policy_crud",
            risk_level="low",
            operation_details={
                "count": len(policies),
                "active_only": active_only
            }
        )
        
        return policies
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Failed retention policies access: {str(e)}",
            user_id=user_id,
            system_component="retention_policy_crud",
            risk_level="medium"
        )
        raise


async def update_retention_policy(
    db: AsyncSession,
    policy_id: uuid.UUID,
    user_id: uuid.UUID,
    **kwargs
) -> Optional[RetentionPolicy]:
    """Update retention policy with audit logging"""
    try:
        result = await db.execute(
            select(RetentionPolicy).where(
                and_(
                    RetentionPolicy.id == policy_id,
                    RetentionPolicy.created_by == user_id
                )
            )
        )
        policy = result.scalar_one_or_none()
        
        if not policy:
            return None
        
        updated_fields = []
        for key, value in kwargs.items():
            if hasattr(policy, key) and getattr(policy, key) != value:
                setattr(policy, key, value)
                updated_fields.append(key)
        
        if updated_fields:
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"Retention policy updated: {policy.name}. Fields: {', '.join(updated_fields)}",
                user_id=user_id,
                system_component="retention_policy_crud",
                risk_level="low",
                operation_details={"updated_fields": updated_fields}
            )
            
            await db.commit()
            await db.refresh(policy)
        
        return policy
        
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Failed retention policy update: {str(e)}",
            user_id=user_id,
            system_component="retention_policy_crud",
            risk_level="medium"
        )
        raise


async def deactivate_retention_policy(
    db: AsyncSession,
    policy_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[RetentionPolicy]:
    """Deactivate retention policy (soft delete)"""
    try:
        result = await db.execute(
            select(RetentionPolicy).where(
                and_(
                    RetentionPolicy.id == policy_id,
                    RetentionPolicy.created_by == user_id
                )
            )
        )
        policy = result.scalar_one_or_none()
        
        if not policy:
            return None
        
        policy.is_active = False
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Retention policy deactivated: {policy.name}",
            user_id=user_id,
            system_component="retention_policy_crud",
            risk_level="low"
        )
        
        await db.commit()
        await db.refresh(policy)
        return policy
        
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Failed retention policy deactivation: {str(e)}",
            user_id=user_id,
            system_component="retention_policy_crud",
            risk_level="medium"
        )
        raise


async def get_applicable_retention_policy(
    db: AsyncSession,
    data_categories: List[DataCategory],
    processing_purposes: List[ProcessingPurpose],
    user_id: uuid.UUID
) -> Optional[RetentionPolicy]:
    """Find the most specific retention policy for given data categories and purposes"""
    try:
        # Convert enums to values
        data_categories_values = [cat.value for cat in data_categories]
        processing_purposes_values = [purpose.value for purpose in processing_purposes]
        
        # Get all active policies for the user
        result = await db.execute(
            select(RetentionPolicy).where(
                and_(
                    RetentionPolicy.created_by == user_id,
                    RetentionPolicy.is_active == True
                )
            ).order_by(RetentionPolicy.created_at.desc())
        )
        policies = result.scalars().all()
        
        # Find the best matching policy
        best_match = None
        best_score = -1
        
        for policy in policies:
            # Check if policy applies to any of the data categories
            category_match = any(
                cat in policy.applies_to_data_categories 
                for cat in data_categories_values
            )
            
            # Check if policy applies to any of the processing purposes
            purpose_match = any(
                purpose in policy.applies_to_processing_purposes 
                for purpose in processing_purposes_values
            )
            
            if category_match and purpose_match:
                # Calculate match score (more specific = higher score)
                score = (
                    len(set(data_categories_values) & set(policy.applies_to_data_categories)) +
                    len(set(processing_purposes_values) & set(policy.applies_to_processing_purposes))
                )
                
                if score > best_score:
                    best_score = score
                    best_match = policy
        
        if best_match:
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Applicable retention policy found: {best_match.name}",
                user_id=user_id,
                system_component="retention_policy_crud",
                risk_level="low",
                operation_details={
                    "policy_name": best_match.name,
                    "retention_months": best_match.retention_period_months,
                    "match_score": best_score
                }
            )
        
        return best_match
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Failed to find applicable retention policy: {str(e)}",
            user_id=user_id,
            system_component="retention_policy_crud",
            risk_level="medium"
        )
        raise