"""
Production monitoring and health check system for ComptaFlow
"""
import time
import psutil
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from decimal import Decimal

from core.config import settings
from core.database import async_session_maker
from models.user import User
from models.subscription import Subscription, InvoiceQuotaUsage


class HealthChecker:
    """Health check and monitoring system"""
    
    @staticmethod
    async def get_system_health() -> Dict:
        """Get comprehensive system health status"""
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "checks": {},
            "metrics": {},
            "alerts": []
        }
        
        # Database health
        db_health = await HealthChecker._check_database()
        health_status["checks"]["database"] = db_health
        
        # Redis health
        redis_health = await HealthChecker._check_redis()
        health_status["checks"]["redis"] = redis_health
        
        # System resources
        system_health = await HealthChecker._check_system_resources()
        health_status["checks"]["system"] = system_health
        health_status["metrics"]["system"] = system_health.get("metrics", {})
        
        # Application metrics
        app_metrics = await HealthChecker._get_application_metrics()
        health_status["metrics"]["application"] = app_metrics
        
        # Service availability
        services_health = await HealthChecker._check_external_services()
        health_status["checks"]["external_services"] = services_health
        
        # Determine overall status
        all_checks = [db_health, redis_health, system_health, services_health]
        if any(check.get("status") == "critical" for check in all_checks):
            health_status["status"] = "critical"
        elif any(check.get("status") == "warning" for check in all_checks):
            health_status["status"] = "warning"
        
        # Generate alerts
        health_status["alerts"] = await HealthChecker._generate_alerts(health_status)
        
        return health_status
    
    @staticmethod
    async def _check_database() -> Dict:
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            
            async with async_session_maker() as session:
                # Basic connectivity test
                result = await session.execute(text("SELECT 1"))
                result.scalar()
                
                # Table existence check
                tables_result = await session.execute(
                    text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('users', 'subscriptions', 'invoices')")
                )
                table_count = tables_result.scalar()
                
                # Performance check - count users
                users_result = await session.execute(select(func.count(User.id)))
                user_count = users_result.scalar()
                
            response_time = (time.time() - start_time) * 1000  # ms
            
            status = "healthy"
            if response_time > 1000:  # > 1 second
                status = "warning"
            if response_time > 5000:  # > 5 seconds
                status = "critical"
            
            return {
                "status": status,
                "response_time_ms": round(response_time, 2),
                "tables_found": table_count,
                "total_users": user_count,
                "message": f"Database responsive in {response_time:.1f}ms"
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "message": "Database connection failed"
            }
    
    @staticmethod
    async def _check_redis() -> Dict:
        """Check Redis connectivity and performance"""
        try:
            start_time = time.time()
            
            redis_client = redis.from_url(settings.REDIS_URL)
            
            # Basic connectivity test
            ping_result = redis_client.ping()
            
            # Performance test
            test_key = "health_check_test"
            redis_client.set(test_key, "test_value", ex=10)
            retrieved_value = redis_client.get(test_key)
            redis_client.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            status = "healthy"
            if response_time > 100:  # > 100ms
                status = "warning"
            if response_time > 500:  # > 500ms
                status = "critical"
            
            # Get Redis info
            info = redis_client.info()
            
            return {
                "status": status,
                "response_time_ms": round(response_time, 2),
                "ping_successful": ping_result,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "message": f"Redis responsive in {response_time:.1f}ms"
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "message": "Redis connection failed"
            }
    
    @staticmethod
    async def _check_system_resources() -> Dict:
        """Check system resource utilization"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / 1024 / 1024 / 1024
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / 1024 / 1024 / 1024
            
            # Determine status
            status = "healthy"
            warnings = []
            
            if cpu_percent > 80:
                status = "warning"
                warnings.append(f"High CPU usage: {cpu_percent}%")
            if cpu_percent > 95:
                status = "critical"
            
            if memory_percent > 80:
                status = "warning"
                warnings.append(f"High memory usage: {memory_percent}%")
            if memory_percent > 95:
                status = "critical"
            
            if disk_percent > 80:
                status = "warning"
                warnings.append(f"High disk usage: {disk_percent:.1f}%")
            if disk_percent > 95:
                status = "critical"
            
            return {
                "status": status,
                "warnings": warnings,
                "metrics": {
                    "cpu_percent": round(cpu_percent, 1),
                    "memory_percent": round(memory_percent, 1),
                    "memory_available_gb": round(memory_available_gb, 2),
                    "disk_percent": round(disk_percent, 1),
                    "disk_free_gb": round(disk_free_gb, 2)
                },
                "message": f"System resources: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%, Disk {disk_percent:.1f}%"
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "message": "System resource check failed"
            }
    
    @staticmethod
    async def _get_application_metrics() -> Dict:
        """Get application-specific metrics"""
        try:
            async with async_session_maker() as session:
                # User statistics
                total_users = await session.execute(select(func.count(User.id)))
                active_users = await session.execute(
                    select(func.count(User.id)).where(User.is_active == True)
                )
                
                # Subscription statistics
                total_subscriptions = await session.execute(select(func.count(Subscription.id)))
                active_subscriptions = await session.execute(
                    select(func.count(Subscription.id)).where(Subscription.status == 'ACTIVE')
                )
                
                # Subscription by tier
                tier_counts = await session.execute(
                    select(Subscription.pricing_tier, func.count(Subscription.id))
                    .group_by(Subscription.pricing_tier)
                )
                tier_distribution = {tier.value: count for tier, count in tier_counts}
                
                # Recent usage (last 24 hours)
                yesterday = datetime.utcnow() - timedelta(days=1)
                recent_usage = await session.execute(
                    select(func.count(InvoiceQuotaUsage.id))
                    .where(InvoiceQuotaUsage.processed_at >= yesterday)
                )
                
                # Current month usage
                current_month = datetime.utcnow().strftime("%Y-%m")
                monthly_usage = await session.execute(
                    select(func.count(InvoiceQuotaUsage.id))
                    .where(InvoiceQuotaUsage.usage_month == current_month)
                )
                
                # Revenue estimation (active paid subscriptions)
                paid_subscriptions = await session.execute(
                    select(func.count(Subscription.id))
                    .where(
                        Subscription.status == 'ACTIVE',
                        Subscription.pricing_tier != 'FREE'
                    )
                )
                
                return {
                    "users": {
                        "total": total_users.scalar(),
                        "active": active_users.scalar()
                    },
                    "subscriptions": {
                        "total": total_subscriptions.scalar(),
                        "active": active_subscriptions.scalar(),
                        "paid": paid_subscriptions.scalar(),
                        "by_tier": tier_distribution
                    },
                    "usage": {
                        "last_24h": recent_usage.scalar(),
                        "current_month": monthly_usage.scalar()
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to collect application metrics"
            }
    
    @staticmethod
    async def _check_external_services() -> Dict:
        """Check external service availability"""
        services = {
            "groq_api": {
                "status": "unknown",
                "message": "Groq API key configured" if settings.GROQ_API_KEY else "Groq API key not configured"
            },
            "insee_api": {
                "status": "unknown", 
                "message": "INSEE API key configured" if settings.INSEE_API_KEY else "INSEE API key not configured"
            }
        }
        
        # Determine overall status
        all_configured = all(
            service["message"].endswith("configured") 
            for service in services.values()
        )
        
        overall_status = "healthy" if all_configured else "warning"
        
        return {
            "status": overall_status,
            "services": services,
            "message": "All external services configured" if all_configured else "Some services not configured"
        }
    
    @staticmethod
    async def _generate_alerts(health_status: Dict) -> List[Dict]:
        """Generate alerts based on health status"""
        alerts = []
        
        # Database alerts
        db_check = health_status["checks"].get("database", {})
        if db_check.get("response_time_ms", 0) > 1000:
            alerts.append({
                "severity": "warning",
                "component": "database",
                "message": f"Database response time high: {db_check['response_time_ms']:.1f}ms",
                "recommendation": "Check database performance and connections"
            })
        
        # System resource alerts
        system_check = health_status["checks"].get("system", {})
        system_metrics = system_check.get("metrics", {})
        
        if system_metrics.get("memory_percent", 0) > 90:
            alerts.append({
                "severity": "critical",
                "component": "system",
                "message": f"Memory usage critical: {system_metrics['memory_percent']}%",
                "recommendation": "Scale up memory or restart services"
            })
        
        if system_metrics.get("disk_percent", 0) > 90:
            alerts.append({
                "severity": "critical",
                "component": "system",
                "message": f"Disk usage critical: {system_metrics['disk_percent']:.1f}%",
                "recommendation": "Clean up disk space or scale storage"
            })
        
        # Usage alerts
        app_metrics = health_status["metrics"].get("application", {})
        usage_24h = app_metrics.get("usage", {}).get("last_24h", 0)
        
        if usage_24h > 10000:  # High volume alert
            alerts.append({
                "severity": "info",
                "component": "application",
                "message": f"High invoice processing volume: {usage_24h} in 24h",
                "recommendation": "Monitor performance and consider scaling"
            })
        
        return alerts


# FastAPI endpoint handler
async def get_health_status():
    """Get system health status for monitoring"""
    return await HealthChecker.get_system_health()


async def get_metrics():
    """Get Prometheus-style metrics"""
    health = await HealthChecker.get_system_health()
    app_metrics = health["metrics"]["application"]
    system_metrics = health["metrics"]["system"]
    
    # Format as Prometheus metrics
    metrics_text = f"""# HELP comptaflow_users_total Total number of users
# TYPE comptaflow_users_total gauge
comptaflow_users_total {app_metrics["users"]["total"]}

# HELP comptaflow_users_active Active users
# TYPE comptaflow_users_active gauge
comptaflow_users_active {app_metrics["users"]["active"]}

# HELP comptaflow_subscriptions_total Total subscriptions
# TYPE comptaflow_subscriptions_total gauge
comptaflow_subscriptions_total {app_metrics["subscriptions"]["total"]}

# HELP comptaflow_subscriptions_paid Paid subscriptions
# TYPE comptaflow_subscriptions_paid gauge
comptaflow_subscriptions_paid {app_metrics["subscriptions"]["paid"]}

# HELP comptaflow_invoices_processed_24h Invoices processed in last 24h
# TYPE comptaflow_invoices_processed_24h gauge
comptaflow_invoices_processed_24h {app_metrics["usage"]["last_24h"]}

# HELP comptaflow_invoices_processed_month Invoices processed this month
# TYPE comptaflow_invoices_processed_month gauge
comptaflow_invoices_processed_month {app_metrics["usage"]["current_month"]}

# HELP comptaflow_system_cpu_percent CPU usage percentage
# TYPE comptaflow_system_cpu_percent gauge
comptaflow_system_cpu_percent {system_metrics["cpu_percent"]}

# HELP comptaflow_system_memory_percent Memory usage percentage
# TYPE comptaflow_system_memory_percent gauge
comptaflow_system_memory_percent {system_metrics["memory_percent"]}

# HELP comptaflow_system_disk_percent Disk usage percentage
# TYPE comptaflow_system_disk_percent gauge
comptaflow_system_disk_percent {system_metrics["disk_percent"]}
"""
    
    return metrics_text