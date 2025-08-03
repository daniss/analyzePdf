from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from models.subscription import PricingTier, SubscriptionStatus


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str
    company_name: Optional[str] = None


class SubscriptionInfo(BaseModel):
    pricing_tier: PricingTier
    status: SubscriptionStatus
    monthly_invoice_limit: int
    monthly_invoices_processed: int
    current_period_end: Optional[datetime] = None


class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime
    company_name: Optional[str] = None
    subscription: Optional[SubscriptionInfo] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None