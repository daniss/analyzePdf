from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total: float


class InvoiceData(BaseModel):
    invoice_number: Optional[str] = None
    date: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    line_items: List[LineItem] = []
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    currency: str = "USD"


class InvoiceCreate(BaseModel):
    filename: str


class InvoiceResponse(BaseModel):
    id: str
    filename: str
    status: str  # "processing", "completed", "failed"
    created_at: datetime
    updated_at: Optional[datetime] = None
    data: Optional[InvoiceData] = None
    error_message: Optional[str] = None