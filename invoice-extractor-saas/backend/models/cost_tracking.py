"""
Cost tracking models for internal monitoring
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text, ForeignKey, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from enum import Enum

from core.database import Base

class ProcessingProvider(str, Enum):
    CLAUDE_OPUS = "claude_opus"
    CLAUDE_SONNET = "claude_sonnet"
    GROQ_LLAMA = "groq_llama_3.1_8b"

class ProcessingType(str, Enum):
    SINGLE_INVOICE = "single_invoice"
    BATCH_PROCESSING = "batch_processing"
    API_CALL = "api_call"

class CostTracking(Base):
    """
    Internal cost tracking for API usage monitoring
    Hidden from users - for admin analytics only
    """
    __tablename__ = "cost_tracking"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Processing details
    provider = Column(String, nullable=False)  # groq_llama_3.1_8b, claude_opus, etc.
    processing_type = Column(String, nullable=False)  # single_invoice, batch_processing
    
    # Cost information
    tokens_used = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    estimated_cost_eur = Column(Float, default=0.0)
    
    # Processing details
    invoice_count = Column(Integer, default=1)
    pages_processed = Column(Integer, default=1)
    file_size_mb = Column(Float, default=0.0)
    
    # User context (for analytics)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    batch_id = Column(String, nullable=True)  # For batch processing
    
    # Success tracking
    processing_successful = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Timing
    processing_duration_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships (commented out to fix import issues)
    # user = relationship("User", back_populates="cost_entries")
    # invoice = relationship("Invoice", back_populates="cost_entries")

class CostSummary(Base):
    """
    Daily/monthly cost summaries for reporting
    """
    __tablename__ = "cost_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Time period
    period_type = Column(String, nullable=False)  # daily, monthly, yearly
    period_date = Column(DateTime(timezone=True), nullable=False)  # YYYY-MM-DD for daily, YYYY-MM-01 for monthly
    
    # Aggregated costs
    total_invoices_processed = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    total_cost_eur = Column(Float, default=0.0)
    
    # Provider breakdown
    groq_cost_eur = Column(Float, default=0.0)
    claude_cost_eur = Column(Float, default=0.0)
    
    # Processing breakdown
    single_invoice_cost = Column(Float, default=0.0)
    batch_processing_cost = Column(Float, default=0.0)
    
    # User metrics
    active_users_count = Column(Integer, default=0)
    new_users_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Add to existing models
def add_cost_tracking_relationships():
    """
    Add cost tracking relationships to existing models
    Call this after importing User and Invoice models
    """
    try:
        from models.user import User
        from models.invoice import Invoice
        
        # Add back_populates to existing models if not already present
        if not hasattr(User, 'cost_entries'):
            User.cost_entries = relationship("CostTracking", back_populates="user")
            
        if not hasattr(Invoice, 'cost_entries'):
            Invoice.cost_entries = relationship("CostTracking", back_populates="invoice")
            
    except ImportError:
        # Models not available yet, will be added later
        pass