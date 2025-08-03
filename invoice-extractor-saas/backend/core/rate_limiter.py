"""
Rate limiting middleware for ComptaFlow API
"""
import time
import redis
from fastapi import Request, HTTPException, status
from typing import Dict, Optional
import json
import hashlib

from core.config import settings


class RateLimiter:
    """Redis-based rate limiter with different limits for different tiers"""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique identifier for the client"""
        # Try to get user ID from JWT token if available
        if hasattr(request.state, 'user_id'):
            return f"user:{request.state.user_id}"
        
        # Fall back to IP address
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            ip = forwarded_for.split(',')[0].strip()
        else:
            ip = request.client.host if request.client else 'unknown'
        
        return f"ip:{ip}"
    
    def _get_rate_limit_config(self, tier: str = "FREE") -> Dict[str, int]:
        """Get rate limit configuration based on subscription tier"""
        configs = {
            "FREE": {
                "requests_per_minute": 60,
                "requests_per_hour": 500,
                "invoice_uploads_per_hour": 20,
                "export_requests_per_hour": 10
            },
            "PRO": {
                "requests_per_minute": 120,
                "requests_per_hour": 2000,
                "invoice_uploads_per_hour": 100,
                "export_requests_per_hour": 50
            },
            "BUSINESS": {
                "requests_per_minute": 300,
                "requests_per_hour": 5000,
                "invoice_uploads_per_hour": 500,
                "export_requests_per_hour": 200
            },
            "ENTERPRISE": {
                "requests_per_minute": 600,
                "requests_per_hour": 10000,
                "invoice_uploads_per_hour": 2000,
                "export_requests_per_hour": 1000
            }
        }
        return configs.get(tier, configs["FREE"])
    
    def _check_rate_limit(
        self, 
        client_id: str, 
        limit_type: str, 
        limit: int, 
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit
        Returns: (is_allowed, current_count, reset_time)
        """
        key = f"rate_limit:{client_id}:{limit_type}"
        current_time = int(time.time())
        window_start = current_time - (current_time % window_seconds)
        
        pipe = self.redis_client.pipeline()
        pipe.multi()
        
        # Get current count for this window
        pipe.hget(key, window_start)
        
        # Set expiry for the key (cleanup old windows)
        pipe.expire(key, window_seconds * 2)
        
        results = pipe.execute()
        current_count = int(results[0] or 0)
        
        if current_count >= limit:
            reset_time = window_start + window_seconds
            return False, current_count, reset_time
        
        # Increment counter
        pipe = self.redis_client.pipeline()
        pipe.multi()
        pipe.hincrby(key, window_start, 1)
        pipe.expire(key, window_seconds * 2)
        pipe.execute()
        
        reset_time = window_start + window_seconds
        return True, current_count + 1, reset_time
    
    async def check_general_rate_limit(
        self, 
        request: Request, 
        user_tier: str = "FREE"
    ) -> None:
        """Check general API rate limits"""
        client_id = self._get_client_id(request)
        config = self._get_rate_limit_config(user_tier)
        
        # Check per-minute limit
        allowed, count, reset_time = self._check_rate_limit(
            client_id,
            "general_minute",
            config["requests_per_minute"],
            60
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Trop de requêtes. Limite: {config['requests_per_minute']}/minute",
                    "reset_time": reset_time,
                    "current_count": count,
                    "limit": config["requests_per_minute"],
                    "window": "minute"
                },
                headers={
                    "X-RateLimit-Limit": str(config["requests_per_minute"]),
                    "X-RateLimit-Remaining": str(max(0, config["requests_per_minute"] - count)),
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time - int(time.time()))
                }
            )
        
        # Check per-hour limit
        allowed, count, reset_time = self._check_rate_limit(
            client_id,
            "general_hour",
            config["requests_per_hour"],
            3600
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Trop de requêtes. Limite: {config['requests_per_hour']}/heure",
                    "reset_time": reset_time,
                    "current_count": count,
                    "limit": config["requests_per_hour"],
                    "window": "hour"
                },
                headers={
                    "X-RateLimit-Limit": str(config["requests_per_hour"]),
                    "X-RateLimit-Remaining": str(max(0, config["requests_per_hour"] - count)),
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(max(1, reset_time - int(time.time())))
                }
            )
    
    async def check_invoice_upload_rate_limit(
        self, 
        request: Request, 
        user_tier: str = "FREE"
    ) -> None:
        """Check specific rate limits for invoice uploads"""
        client_id = self._get_client_id(request)
        config = self._get_rate_limit_config(user_tier)
        
        allowed, count, reset_time = self._check_rate_limit(
            client_id,
            "invoice_uploads",
            config["invoice_uploads_per_hour"],
            3600
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Upload rate limit exceeded",
                    "message": f"Trop d'envois de factures. Limite: {config['invoice_uploads_per_hour']}/heure",
                    "reset_time": reset_time,
                    "current_count": count,
                    "limit": config["invoice_uploads_per_hour"],
                    "window": "hour",
                    "suggestion": "Utilisez le traitement par lots pour optimiser vos envois"
                },
                headers={
                    "X-RateLimit-Limit": str(config["invoice_uploads_per_hour"]),
                    "X-RateLimit-Remaining": str(max(0, config["invoice_uploads_per_hour"] - count)),
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(max(1, reset_time - int(time.time())))
                }
            )
    
    async def check_export_rate_limit(
        self, 
        request: Request, 
        user_tier: str = "FREE"
    ) -> None:
        """Check specific rate limits for data exports"""
        client_id = self._get_client_id(request)
        config = self._get_rate_limit_config(user_tier)
        
        allowed, count, reset_time = self._check_rate_limit(
            client_id,
            "exports",
            config["export_requests_per_hour"],
            3600
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Export rate limit exceeded",
                    "message": f"Trop d'exports. Limite: {config['export_requests_per_hour']}/heure",
                    "reset_time": reset_time,
                    "current_count": count,
                    "limit": config["export_requests_per_hour"],
                    "window": "hour"
                },
                headers={
                    "X-RateLimit-Limit": str(config["export_requests_per_hour"]),
                    "X-RateLimit-Remaining": str(max(0, config["export_requests_per_hour"] - count)),
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(max(1, reset_time - int(time.time())))
                }
            )


# Global rate limiter instance
rate_limiter = RateLimiter()


async def get_user_tier_from_request(request: Request) -> str:
    """Extract user tier from authenticated request"""
    if hasattr(request.state, 'user') and request.state.user:
        user = request.state.user
        if hasattr(user, 'subscription') and user.subscription:
            return user.subscription.pricing_tier.value
    return "FREE"


# Middleware functions for different endpoints
async def general_rate_limit_middleware(request: Request):
    """Apply general rate limiting"""
    user_tier = await get_user_tier_from_request(request)
    await rate_limiter.check_general_rate_limit(request, user_tier)


async def invoice_upload_rate_limit_middleware(request: Request):
    """Apply invoice upload specific rate limiting"""
    user_tier = await get_user_tier_from_request(request)
    await rate_limiter.check_general_rate_limit(request, user_tier)
    await rate_limiter.check_invoice_upload_rate_limit(request, user_tier)


async def export_rate_limit_middleware(request: Request):
    """Apply export specific rate limiting"""
    user_tier = await get_user_tier_from_request(request)
    await rate_limiter.check_general_rate_limit(request, user_tier)
    await rate_limiter.check_export_rate_limit(request, user_tier)