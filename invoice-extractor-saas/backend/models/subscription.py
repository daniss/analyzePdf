from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from core.database import Base


class PricingTier(enum.Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Pricing information
    pricing_tier = Column(SQLEnum(PricingTier), nullable=False, default=PricingTier.FREE)
    status = Column(SQLEnum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    
    # Stripe integration
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    stripe_price_id = Column(String, nullable=True)
    
    # Billing information
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    
    # Invoice quotas and usage
    monthly_invoice_limit = Column(Integer, nullable=False, default=10)  # FREE tier default
    monthly_invoices_processed = Column(Integer, nullable=False, default=0)
    quota_reset_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="subscription")


class PricingConfig(Base):
    __tablename__ = "pricing_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tier = Column(SQLEnum(PricingTier), nullable=False, unique=True)
    
    # Pricing details
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price_monthly_eur = Column(Numeric(10, 2), nullable=False)
    invoice_limit_monthly = Column(Integer, nullable=False)
    
    # Features
    unlimited_invoices = Column(Boolean, default=False)
    priority_support = Column(Boolean, default=False)
    api_access = Column(Boolean, default=False)
    custom_export_formats = Column(Boolean, default=False)
    bulk_processing = Column(Boolean, default=False)
    advanced_validation = Column(Boolean, default=False)
    
    # Stripe configuration
    stripe_price_id = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class InvoiceQuotaUsage(Base):
    __tablename__ = "invoice_quota_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False)
    
    # Usage tracking
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    cost_eur = Column(Numeric(10, 4), nullable=False, default=0.0)
    
    # Monthly aggregation
    usage_month = Column(String, nullable=False)  # Format: YYYY-MM
    
    # Relationships
    user = relationship("User")
    subscription = relationship("Subscription")