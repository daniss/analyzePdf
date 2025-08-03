"""
Admin endpoints for ComptaFlow system management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict

from api.auth import get_current_user
from models.user import User
from core.database import get_db
from core.backup_manager import backup_manager
from core.monitoring import get_health_status, get_metrics


router = APIRouter()


async def verify_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Verify user has admin privileges"""
    # For now, check if user email contains 'admin' or specific admin emails
    admin_emails = ["admin@comptaflow.fr", "dpo@comptaflow.fr", "support@comptaflow.fr"]
    
    if current_user.email not in admin_emails and "admin" not in current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


@router.get("/system/health")
async def get_system_health(admin_user: User = Depends(verify_admin_user)):
    """Get detailed system health status"""
    return await get_health_status()


@router.get("/system/metrics")
async def get_system_metrics(admin_user: User = Depends(verify_admin_user)):
    """Get system metrics in JSON format"""
    health = await get_health_status()
    return {
        "application_metrics": health["metrics"]["application"],
        "system_metrics": health["metrics"]["system"],
        "checks": health["checks"],
        "alerts": health["alerts"],
        "timestamp": health["timestamp"]
    }


@router.post("/backup/create")
async def create_backup(
    backup_type: str = "manual",
    admin_user: User = Depends(verify_admin_user)
):
    """Create a new database backup"""
    result = await backup_manager.create_database_backup(backup_type)
    
    if result.get("status") == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup failed: {result.get('error')}"
        )
    
    return result


@router.get("/backup/list")
async def list_backups(
    limit: int = 10,
    admin_user: User = Depends(verify_admin_user)
):
    """List available backups"""
    return await backup_manager.list_backups(limit)


@router.get("/backup/status")
async def get_backup_status(admin_user: User = Depends(verify_admin_user)):
    """Get backup system status"""
    return await backup_manager.get_backup_status()


@router.post("/backup/restore/{backup_filename}")
async def restore_backup(
    backup_filename: str,
    admin_user: User = Depends(verify_admin_user)
):
    """Restore database from backup (DANGEROUS - use with caution)"""
    result = await backup_manager.restore_backup(backup_filename)
    
    if result.get("status") == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restore failed: {result.get('error')}"
        )
    
    return result


@router.post("/backup/cleanup")
async def cleanup_old_backups(
    retention_days: int = 30,
    admin_user: User = Depends(verify_admin_user)
):
    """Clean up old backups beyond retention period"""
    return await backup_manager.cleanup_old_backups(retention_days)


@router.get("/users/stats")
async def get_user_statistics(
    admin_user: User = Depends(verify_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user and subscription statistics"""
    from sqlalchemy import select, func
    from models.subscription import Subscription
    
    # User counts
    total_users = await db.execute(select(func.count(User.id)))
    active_users = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    
    # Subscription stats
    subscription_stats = await db.execute(
        select(Subscription.pricing_tier, func.count(Subscription.id))
        .group_by(Subscription.pricing_tier)
    )
    
    # Recent registrations (last 7 days)
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_users = await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    )
    
    return {
        "total_users": total_users.scalar(),
        "active_users": active_users.scalar(),
        "recent_registrations_7d": recent_users.scalar(),
        "subscription_distribution": {tier.value: count for tier, count in subscription_stats},
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/system/logs")
async def get_system_logs(
    lines: int = 100,
    admin_user: User = Depends(verify_admin_user)
):
    """Get recent system logs (if available)"""
    # This would typically read from log files or a logging service
    # For now, return a placeholder
    return {
        "message": "Log endpoint not implemented - use external log aggregation service",
        "recommendation": "Implement log aggregation with tools like ELK stack or CloudWatch",
        "lines_requested": lines
    }


@router.post("/system/cache/clear")
async def clear_system_cache(admin_user: User = Depends(verify_admin_user)):
    """Clear Redis cache"""
    try:
        import redis
        from core.config import settings
        
        redis_client = redis.from_url(settings.REDIS_URL)
        
        # Get current key count
        key_count_before = redis_client.dbsize()
        
        # Clear all keys
        redis_client.flushdb()
        
        # Get new key count
        key_count_after = redis_client.dbsize()
        
        return {
            "status": "success",
            "keys_cleared": key_count_before - key_count_after,
            "keys_before": key_count_before,
            "keys_after": key_count_after,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )