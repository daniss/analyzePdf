"""
Admin-only cost monitoring endpoints
For internal business analytics and cost tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid

from core.database import get_db
from core.cost_tracker import CostTracker
from api.auth import get_current_user
from models.user import User

router = APIRouter()

def verify_admin_access(current_user: User = Depends(get_current_user)):
    """
    Verify admin access for cost monitoring
    Only allow access to users with admin role or specific admin email
    """
    # Add your admin email or implement admin role system
    admin_emails = [
        "admin@facturepro.fr",
        "support@facturepro.fr",
        # Add your admin email here
    ]
    
    if not current_user.is_admin and current_user.email not in admin_emails:
        raise HTTPException(
            status_code=403, 
            detail="Access denied. Admin privileges required for cost monitoring."
        )
    return current_user

@router.get("/cost-summary/daily")
async def get_daily_cost_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    admin_user: User = Depends(verify_admin_access)
):
    """
    Get daily cost breakdown for specified date range
    Admin only - for internal cost monitoring
    """
    try:
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        
        cost_data = await CostTracker.get_daily_costs(start_datetime, end_datetime)
        
        # Calculate totals
        total_cost = sum(day["total_cost_eur"] for day in cost_data["daily_costs"])
        total_invoices = sum(day["total_invoices"] for day in cost_data["daily_costs"])
        total_requests = sum(day["total_requests"] for day in cost_data["daily_costs"])
        
        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": len(cost_data["daily_costs"])
            },
            "summary": {
                "total_cost_eur": round(total_cost, 6),
                "total_invoices": total_invoices,
                "total_requests": total_requests,
                "avg_cost_per_invoice": round(total_cost / max(1, total_invoices), 6),
                "avg_cost_per_day": round(total_cost / max(1, len(cost_data["daily_costs"])), 6)
            },
            "daily_breakdown": cost_data["daily_costs"],
            "provider_breakdown": cost_data["provider_breakdown"]
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cost summary: {str(e)}")

@router.get("/cost-summary/monthly/{year}/{month}")
async def get_monthly_cost_summary(
    year: int,
    month: int,
    admin_user: User = Depends(verify_admin_access)
):
    """
    Get monthly cost summary for specified month
    Admin only - for business reporting
    """
    try:
        if month < 1 or month > 12:
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
        
        if year < 2020 or year > datetime.now().year + 1:
            raise HTTPException(status_code=400, detail="Invalid year")
        
        summary = await CostTracker.get_monthly_summary(year, month)
        
        if not summary:
            raise HTTPException(status_code=404, detail="No data found for specified month")
        
        return {
            "period": f"{year}-{month:02d}",
            "summary": summary,
            "projections": {
                "monthly_cost_eur": summary["total_cost_eur"],
                "yearly_projection_eur": summary["total_cost_eur"] * 12,
                "cost_efficiency": {
                    "cost_per_invoice": summary["cost_per_invoice"],
                    "cost_per_user": summary["total_cost_eur"] / max(1, summary["active_users"]),
                    "processing_speed": f"{summary['avg_duration']:.2f}s avg"
                }
            }
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Failed to get monthly summary: {str(e)}")

@router.get("/cost-summary/current-month")
async def get_current_month_summary(
    admin_user: User = Depends(verify_admin_access)
):
    """
    Get current month cost summary
    Quick view for dashboard
    """
    now = datetime.now()
    return await get_monthly_cost_summary(now.year, now.month, admin_user)

@router.get("/cost-analytics/trends")
async def get_cost_trends(
    months_back: int = Query(6, description="Number of months to analyze"),
    admin_user: User = Depends(verify_admin_access)
):
    """
    Get cost trends over time for analytics
    """
    try:
        trends = []
        current_date = datetime.now()
        
        for i in range(months_back):
            month_date = current_date - timedelta(days=30 * i)
            year = month_date.year
            month = month_date.month
            
            summary = await CostTracker.get_monthly_summary(year, month)
            if summary:
                trends.append({
                    "period": f"{year}-{month:02d}",
                    "cost_eur": summary["total_cost_eur"],
                    "invoices": summary["total_invoices"],
                    "users": summary["active_users"],
                    "efficiency": summary["cost_per_invoice"]
                })
        
        # Reverse to show oldest first
        trends.reverse()
        
        # Calculate growth rates
        if len(trends) > 1:
            latest = trends[-1]
            previous = trends[-2]
            
            cost_growth = ((latest["cost_eur"] - previous["cost_eur"]) / max(0.01, previous["cost_eur"])) * 100
            invoice_growth = ((latest["invoices"] - previous["invoices"]) / max(1, previous["invoices"])) * 100
            user_growth = ((latest["users"] - previous["users"]) / max(1, previous["users"])) * 100
        else:
            cost_growth = invoice_growth = user_growth = 0
        
        return {
            "trends": trends,
            "growth_metrics": {
                "cost_growth_pct": round(cost_growth, 2),
                "invoice_growth_pct": round(invoice_growth, 2),
                "user_growth_pct": round(user_growth, 2)
            },
            "recommendations": _get_cost_recommendations(trends)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cost trends: {str(e)}")

def _get_cost_recommendations(trends: list) -> list:
    """
    Generate cost optimization recommendations
    """
    recommendations = []
    
    if not trends:
        return recommendations
    
    latest = trends[-1] if trends else {}
    cost_per_invoice = latest.get("efficiency", 0)
    
    if cost_per_invoice > 0.01:  # More than 1 cent per invoice
        recommendations.append({
            "type": "cost_optimization",
            "message": "Coût par facture élevé. Considérez l'optimisation du modèle ou la négociation tarifaire.",
            "priority": "high"
        })
    
    if len(trends) >= 3:
        recent_costs = [t["cost_eur"] for t in trends[-3:]]
        if all(recent_costs[i] < recent_costs[i+1] for i in range(len(recent_costs)-1)):
            recommendations.append({
                "type": "growing_costs",
                "message": "Coûts en croissance constante sur 3 mois. Surveillez l'utilisation.",
                "priority": "medium"
            })
    
    return recommendations