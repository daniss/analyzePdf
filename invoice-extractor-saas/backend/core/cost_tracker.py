"""
Internal cost tracking service
Monitors API usage and costs for business analytics
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.sql import extract
import uuid
import logging

from models.cost_tracking import CostTracking, CostSummary, ProcessingProvider, ProcessingType
from core.database import async_session_maker

logger = logging.getLogger(__name__)

class CostTracker:
    """
    Internal cost tracking for API usage monitoring
    """
    
    # Current pricing (update as needed)
    PRICING = {
        "groq": {
            "input_tokens": 0.0000001,  # Groq is very cheap/free
            "output_tokens": 0.0000001,  # Extremely low cost
            "usd_to_eur": 0.85
        }
    }
    
    @classmethod
    async def track_processing_cost(
        cls,
        provider: str,
        processing_type: str,
        tokens_used: int = 1000,  # Default estimate
        invoice_count: int = 1,
        pages_processed: int = 1,
        file_size_mb: float = 1.0,
        user_id: Optional[uuid.UUID] = None,
        invoice_id: Optional[uuid.UUID] = None,
        batch_id: Optional[str] = None,
        processing_successful: bool = True,
        error_message: Optional[str] = None,
        processing_duration: float = 0.0
    ) -> Optional[uuid.UUID]:
        """
        Track processing cost for internal analytics
        """
        try:
            # Calculate estimated cost
            estimated_cost_usd = cls._calculate_cost_usd(provider, tokens_used)
            exchange_rate = cls.PRICING.get(provider, {}).get("usd_to_eur", 0.85)
            estimated_cost_eur = estimated_cost_usd * exchange_rate
            
            async with async_session_maker() as db:
                # Create cost tracking entry
                cost_entry = CostTracking(
                    provider=provider,
                    processing_type=processing_type,
                    tokens_used=tokens_used,
                    estimated_cost_usd=estimated_cost_usd,
                    estimated_cost_eur=estimated_cost_eur,
                    invoice_count=invoice_count,
                    pages_processed=pages_processed,
                    file_size_mb=file_size_mb,
                    user_id=user_id,
                    invoice_id=invoice_id,
                    batch_id=batch_id,
                    processing_successful=processing_successful,
                    error_message=error_message,
                    processing_duration_seconds=processing_duration
                )
                
                db.add(cost_entry)
                await db.commit()
                await db.refresh(cost_entry)
                
                logger.info(f"Cost tracked: {provider} - {estimated_cost_eur:.6f}€ for {invoice_count} invoice(s)")
                return cost_entry.id
                
        except Exception as e:
            logger.error(f"Failed to track cost: {str(e)}")
            return None
    
    @classmethod
    def _calculate_cost_usd(cls, provider: str, tokens_used: int) -> float:
        """
        Calculate cost in USD based on provider and tokens
        """
        pricing = cls.PRICING.get(provider, {})
        if not pricing:
            # Default pricing for unknown providers
            return tokens_used * 0.000001  # $1 per 1M tokens
        
        # Assume 80% input tokens, 20% output tokens
        input_tokens = int(tokens_used * 0.8)
        output_tokens = int(tokens_used * 0.2)
        
        cost = (
            input_tokens * pricing.get("input_tokens", 0.000001) +
            output_tokens * pricing.get("output_tokens", 0.000005)
        )
        
        return cost
    
    @classmethod
    async def get_daily_costs(cls, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get cost summary for date range (admin only)
        """
        try:
            async with async_session_maker() as db:
                # Get daily costs
                query = select(
                    func.date(CostTracking.created_at).label('date'),
                    func.count(CostTracking.id).label('total_requests'),
                    func.sum(CostTracking.estimated_cost_eur).label('total_cost_eur'),
                    func.sum(CostTracking.invoice_count).label('total_invoices'),
                    func.sum(CostTracking.tokens_used).label('total_tokens'),
                    func.avg(CostTracking.processing_duration_seconds).label('avg_duration')
                ).where(
                    and_(
                        CostTracking.created_at >= start_date,
                        CostTracking.created_at <= end_date
                    )
                ).group_by(
                    func.date(CostTracking.created_at)
                ).order_by(
                    func.date(CostTracking.created_at)
                )
                
                result = await db.execute(query)
                daily_costs = result.fetchall()
                
                # Get provider breakdown
                provider_query = select(
                    CostTracking.provider,
                    func.count(CostTracking.id).label('requests'),
                    func.sum(CostTracking.estimated_cost_eur).label('cost_eur'),
                    func.sum(CostTracking.invoice_count).label('invoices')
                ).where(
                    and_(
                        CostTracking.created_at >= start_date,
                        CostTracking.created_at <= end_date
                    )
                ).group_by(CostTracking.provider)
                
                provider_result = await db.execute(provider_query)
                provider_breakdown = provider_result.fetchall()
                
                return {
                    "daily_costs": [
                        {
                            "date": str(row.date),
                            "total_requests": row.total_requests,
                            "total_cost_eur": float(row.total_cost_eur or 0),
                            "total_invoices": row.total_invoices,
                            "total_tokens": row.total_tokens,
                            "avg_duration": float(row.avg_duration or 0)
                        }
                        for row in daily_costs
                    ],
                    "provider_breakdown": [
                        {
                            "provider": row.provider,
                            "requests": row.requests,
                            "cost_eur": float(row.cost_eur or 0),
                            "invoices": row.invoices
                        }
                        for row in provider_breakdown
                    ]
                }
                
        except Exception as e:
            logger.error(f"Failed to get daily costs: {str(e)}")
            return {"daily_costs": [], "provider_breakdown": []}
    
    @classmethod
    async def get_monthly_summary(cls, year: int, month: int) -> Dict[str, Any]:
        """
        Get monthly cost summary (admin only)
        """
        try:
            async with async_session_maker() as db:
                query = select(
                    func.count(CostTracking.id).label('total_requests'),
                    func.sum(CostTracking.estimated_cost_eur).label('total_cost_eur'),
                    func.sum(CostTracking.invoice_count).label('total_invoices'),
                    func.sum(CostTracking.tokens_used).label('total_tokens'),
                    func.count(func.distinct(CostTracking.user_id)).label('active_users'),
                    func.avg(CostTracking.processing_duration_seconds).label('avg_duration')
                ).where(
                    and_(
                        extract('year', CostTracking.created_at) == year,
                        extract('month', CostTracking.created_at) == month
                    )
                )
                
                result = await db.execute(query)
                summary = result.fetchone()
                
                if summary:
                    return {
                        "year": year,
                        "month": month,
                        "total_requests": summary.total_requests or 0,
                        "total_cost_eur": float(summary.total_cost_eur or 0),
                        "total_invoices": summary.total_invoices or 0,
                        "total_tokens": summary.total_tokens or 0,
                        "active_users": summary.active_users or 0,
                        "avg_duration": float(summary.avg_duration or 0),
                        "cost_per_invoice": float((summary.total_cost_eur or 0) / max(1, summary.total_invoices or 1))
                    }
                else:
                    return {
                        "year": year,
                        "month": month,
                        "total_requests": 0,
                        "total_cost_eur": 0.0,
                        "total_invoices": 0,
                        "total_tokens": 0,
                        "active_users": 0,
                        "avg_duration": 0.0,
                        "cost_per_invoice": 0.0
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get monthly summary: {str(e)}")
            return {}


# Helper function to track processing costs for any provider
async def track_processing_cost(
    provider: str,
    tokens_used: int,
    invoice_count: int = 1,
    user_id: Optional[uuid.UUID] = None,
    invoice_id: Optional[uuid.UUID] = None,
    batch_id: Optional[str] = None,
    processing_successful: bool = True,
    error_message: Optional[str] = None,
    processing_duration: float = 0.0,
    estimated_cost_usd: Optional[float] = None
):
    """
    Convenience function to track any provider costs
    """
    return await CostTracker.track_processing_cost(
        provider=provider,
        processing_type=ProcessingType.BATCH_PROCESSING if batch_id else ProcessingType.SINGLE_INVOICE,
        tokens_used=tokens_used,
        invoice_count=invoice_count,
        user_id=user_id,
        invoice_id=invoice_id,
        batch_id=batch_id,
        processing_successful=processing_successful,
        error_message=error_message,
        processing_duration=processing_duration
    )