"""
Stripe payment integration for ComptaFlow subscriptions
"""
import stripe
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from core.config import settings
from models.user import User
from models.subscription import Subscription, PricingTier, SubscriptionStatus, PricingConfig
from core.gdpr_helpers import log_audit_event
from models.gdpr_models import AuditEventType


class StripeManager:
    """Manages Stripe payment integration"""
    
    def __init__(self):
        if hasattr(settings, 'STRIPE_SECRET_KEY') and settings.STRIPE_SECRET_KEY:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            self.stripe_configured = True
        else:
            self.stripe_configured = False
    
    async def create_customer(self, user: User) -> Optional[str]:
        """Create Stripe customer for user"""
        if not self.stripe_configured:
            return None
        
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.company_name or user.email,
                metadata={
                    'user_id': str(user.id),
                    'company_name': user.company_name or '',
                    'platform': 'comptaflow'
                }
            )
            return customer.id
        except Exception as e:
            print(f"Failed to create Stripe customer: {e}")
            return None
    
    async def create_checkout_session(
        self, 
        db: AsyncSession,
        user_id: uuid.UUID, 
        pricing_tier: PricingTier,
        success_url: str,
        cancel_url: str
    ) -> Dict:
        """Create Stripe checkout session for subscription upgrade"""
        if not self.stripe_configured:
            return {
                "error": "Stripe not configured",
                "message": "Payment processing unavailable"
            }
        
        try:
            # Get user
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                return {"error": "User not found"}
            
            # Get pricing config
            pricing_result = await db.execute(
                select(PricingConfig).where(PricingConfig.tier == pricing_tier)
            )
            pricing = pricing_result.scalar_one_or_none()
            if not pricing:
                return {"error": "Pricing tier not found"}
            
            # Create or get Stripe customer
            current_subscription = await db.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            subscription = current_subscription.scalar_one_or_none()
            
            customer_id = subscription.stripe_customer_id if subscription else None
            
            if not customer_id:
                customer_id = await self.create_customer(user)
                if not customer_id:
                    return {"error": "Failed to create customer"}
            
            # Create price if not exists (in production, create these via Stripe Dashboard)
            price_id = await self._ensure_stripe_price(pricing)
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                metadata={
                    'user_id': str(user_id),
                    'pricing_tier': pricing_tier.value,
                    'platform': 'comptaflow'
                },
                billing_address_collection='required',
                customer_update={
                    'address': 'auto',
                    'name': 'auto'
                },
                locale='fr',  # French localization
                tax_id_collection={
                    'enabled': True,  # For French business VAT numbers
                }
            )
            
            # Log audit event
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"Stripe checkout session created for {pricing_tier.value} plan",
                user_id=user_id,
                system_component="stripe_manager",
                risk_level="low",
                operation_details={
                    "session_id": session.id,
                    "pricing_tier": pricing_tier.value,
                    "amount": float(pricing.price_monthly_eur)
                }
            )
            
            return {
                "session_id": session.id,
                "checkout_url": session.url,
                "customer_id": customer_id
            }
            
        except Exception as e:
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"Failed to create Stripe checkout: {str(e)}",
                user_id=user_id,
                system_component="stripe_manager",
                risk_level="medium"
            )
            return {
                "error": str(e),
                "message": "Failed to create checkout session"
            }
    
    async def _ensure_stripe_price(self, pricing_config: PricingConfig) -> str:
        """Ensure Stripe price exists, create if not"""
        if pricing_config.stripe_price_id:
            return pricing_config.stripe_price_id
        
        # Create product if not exists
        product = stripe.Product.create(
            name=f"ComptaFlow {pricing_config.name}",
            description=pricing_config.description,
            metadata={
                'tier': pricing_config.tier.value,
                'platform': 'comptaflow'
            }
        )
        
        # Create price
        price = stripe.Price.create(
            unit_amount=int(pricing_config.price_monthly_eur * 100),  # Convert to cents
            currency='eur',
            recurring={'interval': 'month'},
            product=product.id,
            metadata={
                'tier': pricing_config.tier.value,
                'invoice_limit': pricing_config.invoice_limit_monthly
            }
        )
        
        return price.id
    
    async def handle_webhook_event(self, db: AsyncSession, event: Dict) -> Dict:
        """Handle Stripe webhook events"""
        if not self.stripe_configured:
            return {"error": "Stripe not configured"}
        
        try:
            event_type = event['type']
            
            if event_type == 'checkout.session.completed':
                return await self._handle_checkout_completed(db, event['data']['object'])
            elif event_type == 'invoice.payment_succeeded':
                return await self._handle_payment_succeeded(db, event['data']['object'])
            elif event_type == 'invoice.payment_failed':
                return await self._handle_payment_failed(db, event['data']['object'])
            elif event_type == 'customer.subscription.updated':
                return await self._handle_subscription_updated(db, event['data']['object'])
            elif event_type == 'customer.subscription.deleted':
                return await self._handle_subscription_cancelled(db, event['data']['object'])
            else:
                return {"message": f"Unhandled event type: {event_type}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_checkout_completed(self, db: AsyncSession, session_data: Dict) -> Dict:
        """Handle successful checkout completion"""
        try:
            user_id = uuid.UUID(session_data['metadata']['user_id'])
            pricing_tier = PricingTier(session_data['metadata']['pricing_tier'])
            
            # Get or create subscription
            subscription_result = await db.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            subscription = subscription_result.scalar_one_or_none()
            
            # Get pricing config
            pricing_result = await db.execute(
                select(PricingConfig).where(PricingConfig.tier == pricing_tier)
            )
            pricing = pricing_result.scalar_one_or_none()
            
            if not subscription:
                # Create new subscription
                subscription = Subscription(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    pricing_tier=pricing_tier,
                    status=SubscriptionStatus.ACTIVE,
                    stripe_customer_id=session_data['customer'],
                    stripe_subscription_id=session_data['subscription'],
                    monthly_invoice_limit=pricing.invoice_limit_monthly,
                    monthly_invoices_processed=0,
                    quota_reset_date=datetime.utcnow() + timedelta(days=30),
                    current_period_start=datetime.utcnow(),
                    current_period_end=datetime.utcnow() + timedelta(days=30)
                )
                db.add(subscription)
            else:
                # Update existing subscription
                subscription.pricing_tier = pricing_tier
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.stripe_customer_id = session_data['customer']
                subscription.stripe_subscription_id = session_data['subscription']
                subscription.monthly_invoice_limit = pricing.invoice_limit_monthly
                subscription.current_period_start = datetime.utcnow()
                subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
            
            await db.commit()
            
            # Log successful upgrade
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"Subscription upgraded to {pricing_tier.value}",
                user_id=user_id,
                system_component="stripe_webhook",
                risk_level="low",
                operation_details={
                    "subscription_id": session_data['subscription'],
                    "customer_id": session_data['customer'],
                    "amount_total": session_data.get('amount_total', 0) / 100
                }
            )
            
            return {"message": "Subscription created/updated successfully"}
            
        except Exception as e:
            await db.rollback()
            return {"error": str(e)}
    
    async def _handle_payment_succeeded(self, db: AsyncSession, invoice_data: Dict) -> Dict:
        """Handle successful subscription payment"""
        try:
            subscription_id = invoice_data['subscription']
            
            # Find subscription by Stripe ID
            subscription_result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
            )
            subscription = subscription_result.scalar_one_or_none()
            
            if subscription:
                # Reset monthly quota
                subscription.monthly_invoices_processed = 0
                subscription.quota_reset_date = datetime.utcnow() + timedelta(days=30)
                
                # Update billing period
                period_start = datetime.fromtimestamp(invoice_data['period_start'])
                period_end = datetime.fromtimestamp(invoice_data['period_end'])
                subscription.current_period_start = period_start
                subscription.current_period_end = period_end
                
                await db.commit()
                
                await log_audit_event(
                    db=db,
                    event_type=AuditEventType.DATA_MODIFICATION,
                    event_description="Subscription payment succeeded, quota reset",
                    user_id=subscription.user_id,
                    system_component="stripe_webhook",
                    risk_level="low",
                    operation_details={
                        "amount_paid": invoice_data.get('amount_paid', 0) / 100,
                        "period_start": period_start.isoformat(),
                        "period_end": period_end.isoformat()
                    }
                )
            
            return {"message": "Payment processed successfully"}
            
        except Exception as e:
            await db.rollback()
            return {"error": str(e)}
    
    async def _handle_payment_failed(self, db: AsyncSession, invoice_data: Dict) -> Dict:
        """Handle failed subscription payment"""
        try:
            subscription_id = invoice_data['subscription']
            
            # Find subscription by Stripe ID
            subscription_result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
            )
            subscription = subscription_result.scalar_one_or_none()
            
            if subscription:
                subscription.status = SubscriptionStatus.PAST_DUE
                await db.commit()
                
                await log_audit_event(
                    db=db,
                    event_type=AuditEventType.DATA_MODIFICATION,
                    event_description="Subscription payment failed",
                    user_id=subscription.user_id,
                    system_component="stripe_webhook",
                    risk_level="medium",
                    operation_details={
                        "failure_reason": invoice_data.get('failure_reason'),
                        "amount_due": invoice_data.get('amount_due', 0) / 100
                    }
                )
            
            return {"message": "Payment failure processed"}
            
        except Exception as e:
            await db.rollback()
            return {"error": str(e)}
    
    async def _handle_subscription_cancelled(self, db: AsyncSession, subscription_data: Dict) -> Dict:
        """Handle subscription cancellation"""
        try:
            stripe_subscription_id = subscription_data['id']
            
            # Find subscription by Stripe ID
            subscription_result = await db.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
            )
            subscription = subscription_result.scalar_one_or_none()
            
            if subscription:
                subscription.status = SubscriptionStatus.CANCELED
                subscription.canceled_at = datetime.utcnow()
                # Downgrade to FREE tier
                subscription.pricing_tier = PricingTier.FREE
                subscription.monthly_invoice_limit = 10
                
                await db.commit()
                
                await log_audit_event(
                    db=db,
                    event_type=AuditEventType.DATA_MODIFICATION,
                    event_description="Subscription cancelled, downgraded to FREE",
                    user_id=subscription.user_id,
                    system_component="stripe_webhook",
                    risk_level="low"
                )
            
            return {"message": "Subscription cancellation processed"}
            
        except Exception as e:
            await db.rollback()
            return {"error": str(e)}
    
    async def create_customer_portal_session(
        self, 
        db: AsyncSession,
        user_id: uuid.UUID,
        return_url: str
    ) -> Dict:
        """Create Stripe customer portal session for subscription management"""
        if not self.stripe_configured:
            return {"error": "Stripe not configured"}
        
        try:
            # Get user's subscription
            subscription_result = await db.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            subscription = subscription_result.scalar_one_or_none()
            
            if not subscription or not subscription.stripe_customer_id:
                return {"error": "No active subscription found"}
            
            # Create portal session
            session = stripe.billing_portal.Session.create(
                customer=subscription.stripe_customer_id,
                return_url=return_url,
                locale='fr'  # French localization
            )
            
            return {
                "portal_url": session.url
            }
            
        except Exception as e:
            return {"error": str(e)}


# Global Stripe manager instance
stripe_manager = StripeManager()