"""
Payment and subscription management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict
import stripe
import hmac
import hashlib

from api.auth import get_current_user
from models.user import User
from models.subscription import PricingTier
from core.database import get_db
from core.stripe_manager import stripe_manager
from core.config import settings


router = APIRouter()


@router.post("/create-checkout-session")
async def create_checkout_session(
    request_data: Dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create Stripe checkout session for subscription upgrade"""
    try:
        pricing_tier = PricingTier(request_data.get('pricing_tier'))
        success_url = request_data.get('success_url', 'http://localhost:3000/dashboard?payment=success')
        cancel_url = request_data.get('cancel_url', 'http://localhost:3000/dashboard?payment=cancelled')
        
        result = await stripe_manager.create_checkout_session(
            db=db,
            user_id=current_user.id,
            pricing_tier=pricing_tier,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result
            )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Invalid pricing tier: {request_data.get('pricing_tier')}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e)}
        )


@router.post("/create-portal-session")
async def create_portal_session(
    request_data: Dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create Stripe customer portal session for subscription management"""
    try:
        return_url = request_data.get('return_url', 'http://localhost:3000/dashboard')
        
        result = await stripe_manager.create_customer_portal_session(
            db=db,
            user_id=current_user.id,
            return_url=return_url
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e)}
        )


@router.get("/pricing-tiers")
async def get_pricing_tiers(db: AsyncSession = Depends(get_db)):
    """Get available pricing tiers"""
    from sqlalchemy import select
    from models.subscription import PricingConfig
    
    try:
        result = await db.execute(select(PricingConfig))
        pricing_configs = result.scalars().all()
        
        tiers = []
        for config in pricing_configs:
            tiers.append({
                "tier": config.tier.value,
                "name": config.name,
                "description": config.description,
                "price_monthly_eur": float(config.price_monthly_eur),
                "invoice_limit_monthly": config.invoice_limit_monthly,
                "features": {
                    "unlimited_invoices": config.unlimited_invoices,
                    "priority_support": config.priority_support,
                    "api_access": config.api_access,
                    "custom_export_formats": config.custom_export_formats,
                    "bulk_processing": config.bulk_processing,
                    "advanced_validation": config.advanced_validation
                }
            })
        
        return {"pricing_tiers": tiers}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e)}
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Stripe webhook events"""
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        if not sig_header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature"
            )
        
        # Verify webhook signature (if endpoint secret is configured)
        webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        if webhook_secret:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid payload"
                )
            except stripe.error.SignatureVerificationError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid signature"
                )
        else:
            # Parse without verification (for development)
            import json
            event = json.loads(payload)
        
        # Handle the event
        result = await stripe_manager.handle_webhook_event(db, event)
        
        return {"status": "success", "result": result}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e)}
        )