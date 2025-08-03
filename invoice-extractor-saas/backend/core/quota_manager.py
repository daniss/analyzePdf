"""
Invoice quota management and enforcement for ComptaFlow
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from models.user import User
from models.subscription import Subscription, InvoiceQuotaUsage, PricingTier
from core.gdpr_helpers import log_audit_event
from models.gdpr_models import AuditEventType


class QuotaManager:
    """Manages invoice processing quotas for users"""
    
    @staticmethod
    async def check_can_process_invoice(
        db: AsyncSession, 
        user_id: uuid.UUID,
        cost_estimate: Optional[Decimal] = None
    ) -> Tuple[bool, str, dict]:
        """
        Check if user can process another invoice
        Returns: (can_process, message, quota_info)
        """
        try:
            # Get user with subscription
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False, "Utilisateur non trouvé", {}
            
            # Get subscription
            subscription_result = await db.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            subscription = subscription_result.scalar_one_or_none()
            
            if not subscription:
                # Create default FREE subscription
                subscription = await QuotaManager._create_default_subscription(db, user_id)
            
            # Check if subscription is active
            if subscription.status.value.upper() != "ACTIVE":
                await log_audit_event(
                    db=db,
                    event_type=AuditEventType.DATA_ACCESS,
                    event_description=f"Invoice processing blocked - inactive subscription: {subscription.status.value}",
                    user_id=user_id,
                    system_component="quota_manager",
                    risk_level="medium"
                )
                return False, f"Abonnement inactif ({subscription.status.value})", {
                    "subscription_status": subscription.status.value,
                    "pricing_tier": subscription.pricing_tier.value
                }
            
            # Check monthly quota
            current_month = datetime.utcnow().strftime("%Y-%m")
            
            # Get current month usage
            usage_result = await db.execute(
                select(func.count(InvoiceQuotaUsage.id))
                .where(
                    InvoiceQuotaUsage.user_id == user_id,
                    InvoiceQuotaUsage.usage_month == current_month
                )
            )
            current_usage = usage_result.scalar() or 0
            
            quota_info = {
                "monthly_limit": subscription.monthly_invoice_limit,
                "current_usage": current_usage,
                "remaining": subscription.monthly_invoice_limit - current_usage,
                "pricing_tier": subscription.pricing_tier.value,
                "subscription_status": subscription.status.value,
                "reset_date": subscription.quota_reset_date.isoformat() if subscription.quota_reset_date else None
            }
            
            # Check if unlimited (Enterprise tier typically)
            if subscription.pricing_tier == PricingTier.ENTERPRISE and subscription.monthly_invoice_limit >= 10000:
                return True, "Quota illimité", quota_info
            
            # Check quota limit
            if current_usage >= subscription.monthly_invoice_limit:
                await log_audit_event(
                    db=db,
                    event_type=AuditEventType.DATA_ACCESS,
                    event_description=f"Invoice processing blocked - quota exceeded: {current_usage}/{subscription.monthly_invoice_limit}",
                    user_id=user_id,
                    system_component="quota_manager",
                    risk_level="low",
                    operation_details={
                        "current_usage": current_usage,
                        "monthly_limit": subscription.monthly_invoice_limit,
                        "pricing_tier": subscription.pricing_tier.value
                    }
                )
                
                # Suggest upgrade for free users
                upgrade_message = ""
                if subscription.pricing_tier == PricingTier.FREE:
                    upgrade_message = " Passez au plan Pro pour traiter jusqu'à 500 factures/mois."
                
                return False, f"Quota mensuel épuisé ({current_usage}/{subscription.monthly_invoice_limit}).{upgrade_message}", quota_info
            
            # Quota OK
            return True, f"Quota disponible ({current_usage}/{subscription.monthly_invoice_limit})", quota_info
            
        except Exception as e:
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Error checking quota: {str(e)}",
                user_id=user_id,
                system_component="quota_manager",
                risk_level="high"
            )
            # In case of error, allow processing but log it
            return True, "Erreur de vérification du quota, traitement autorisé", {}
    
    @staticmethod
    async def record_invoice_usage(
        db: AsyncSession,
        user_id: uuid.UUID,
        invoice_id: Optional[uuid.UUID] = None,
        cost_eur: Decimal = Decimal("0.0")
    ) -> InvoiceQuotaUsage:
        """Record invoice processing usage"""
        try:
            # Get subscription
            subscription_result = await db.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            subscription = subscription_result.scalar_one_or_none()
            
            if not subscription:
                subscription = await QuotaManager._create_default_subscription(db, user_id)
            
            current_month = datetime.utcnow().strftime("%Y-%m")
            
            # Create usage record
            usage_record = InvoiceQuotaUsage(
                id=uuid.uuid4(),
                user_id=user_id,
                subscription_id=subscription.id,
                invoice_id=invoice_id,
                usage_month=current_month,
                cost_eur=cost_eur,
                processed_at=datetime.utcnow()
            )
            
            db.add(usage_record)
            
            # Update subscription usage counter
            subscription.monthly_invoices_processed += 1
            
            await db.commit()
            
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"Invoice usage recorded: {subscription.monthly_invoices_processed}/{subscription.monthly_invoice_limit}",
                user_id=user_id,
                system_component="quota_manager",
                risk_level="low",
                operation_details={
                    "cost_eur": float(cost_eur),
                    "usage_month": current_month,
                    "new_total_usage": subscription.monthly_invoices_processed
                }
            )
            
            return usage_record
            
        except Exception as e:
            await db.rollback()
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"Error recording invoice usage: {str(e)}",
                user_id=user_id,
                system_component="quota_manager",
                risk_level="high"
            )
            raise
    
    @staticmethod
    async def _create_default_subscription(
        db: AsyncSession, 
        user_id: uuid.UUID
    ) -> Subscription:
        """Create default FREE subscription for user"""
        from models.subscription import SubscriptionStatus
        
        now = datetime.utcnow()
        subscription = Subscription(
            id=uuid.uuid4(),
            user_id=user_id,
            pricing_tier=PricingTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            monthly_invoice_limit=10,  # FREE tier default
            monthly_invoices_processed=0,
            quota_reset_date=now + timedelta(days=30),
            current_period_start=now,
            current_period_end=now + timedelta(days=30)
        )
        
        db.add(subscription)
        await db.commit()
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description="Default FREE subscription created",
            user_id=user_id,
            system_component="quota_manager",
            risk_level="low"
        )
        
        return subscription
    
    @staticmethod
    async def get_quota_status(
        db: AsyncSession, 
        user_id: uuid.UUID
    ) -> dict:
        """Get detailed quota status for user"""
        try:
            # Get subscription
            subscription_result = await db.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            subscription = subscription_result.scalar_one_or_none()
            
            if not subscription:
                return {
                    "has_subscription": False,
                    "pricing_tier": "FREE",
                    "monthly_limit": 10,
                    "current_usage": 0,
                    "remaining": 10,
                    "usage_percentage": 0,
                    "status": "NEEDS_SUBSCRIPTION"
                }
            
            current_month = datetime.utcnow().strftime("%Y-%m")
            
            # Get current usage
            usage_result = await db.execute(
                select(func.count(InvoiceQuotaUsage.id))
                .where(
                    InvoiceQuotaUsage.user_id == user_id,
                    InvoiceQuotaUsage.usage_month == current_month
                )
            )
            current_usage = usage_result.scalar() or 0
            
            # Get cost for current month
            cost_result = await db.execute(
                select(func.coalesce(func.sum(InvoiceQuotaUsage.cost_eur), 0))
                .where(
                    InvoiceQuotaUsage.user_id == user_id,
                    InvoiceQuotaUsage.usage_month == current_month
                )
            )
            total_cost = float(cost_result.scalar() or 0)
            
            remaining = max(0, subscription.monthly_invoice_limit - current_usage)
            usage_percentage = (current_usage / subscription.monthly_invoice_limit * 100) if subscription.monthly_invoice_limit > 0 else 0
            
            return {
                "has_subscription": True,
                "pricing_tier": subscription.pricing_tier.value,
                "status": subscription.status.value,
                "monthly_limit": subscription.monthly_invoice_limit,
                "current_usage": current_usage,
                "remaining": remaining,
                "usage_percentage": round(usage_percentage, 1),
                "total_cost_eur": total_cost,
                "reset_date": subscription.quota_reset_date.isoformat() if subscription.quota_reset_date else None,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "is_unlimited": subscription.monthly_invoice_limit >= 10000 and subscription.pricing_tier == PricingTier.ENTERPRISE
            }
            
        except Exception as e:
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Error getting quota status: {str(e)}",
                user_id=user_id,
                system_component="quota_manager",
                risk_level="medium"
            )
            raise


# Convenience function for middleware/dependency injection
async def enforce_quota_limit(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """
    Enforce quota limit and raise HTTPException if exceeded
    Returns quota info if OK
    """
    can_process, message, quota_info = await QuotaManager.check_can_process_invoice(db, user_id)
    
    if not can_process:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "Quota exceeded",
                "message": message,
                "quota_info": quota_info,
                "upgrade_available": quota_info.get("pricing_tier") == "FREE"
            }
        )
    
    return quota_info