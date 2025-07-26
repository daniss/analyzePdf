from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime
from decimal import Decimal


class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total: float
    # French-specific line item fields
    tva_rate: Optional[float] = None  # TVA rate for this line item
    tva_amount: Optional[float] = None  # TVA amount for this line item
    unit: Optional[str] = None  # Unit of measurement (mandatory in France)


class FrenchTVABreakdown(BaseModel):
    """French TVA (VAT) breakdown by rate"""
    rate: float = Field(..., description="TVA rate (20.0, 10.0, 5.5, 2.1, 0.0)")
    taxable_amount: float = Field(..., description="Amount before TVA (HT)")
    tva_amount: float = Field(..., description="TVA amount")
    
    @validator('rate')
    def validate_french_tva_rate(cls, v):
        valid_rates = [0.0, 2.1, 5.5, 10.0, 20.0]
        if v not in valid_rates:
            raise ValueError(f'Invalid French TVA rate: {v}%. Valid rates: {valid_rates}')
        return v


class FrenchBusinessInfo(BaseModel):
    """French business identification information"""
    name: str
    address: str
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: str = "France"
    
    # French mandatory business identifiers
    siren_number: Optional[str] = Field(None, regex=r'^\d{9}$', description="SIREN number (9 digits)")
    siret_number: Optional[str] = Field(None, regex=r'^\d{14}$', description="SIRET number (14 digits)")
    tva_number: Optional[str] = Field(None, regex=r'^FR\d{11}$', description="French TVA number (FR + 11 digits)")
    
    # Additional French business information
    naf_code: Optional[str] = Field(None, regex=r'^\d{4}[A-Z]$', description="NAF/APE code (4 digits + letter)")
    legal_form: Optional[str] = None  # SARL, SAS, EURL, etc.
    share_capital: Optional[float] = None  # Capital social
    rcs_number: Optional[str] = None  # RCS registration number
    rm_number: Optional[str] = None  # RM number for artisans
    
    phone: Optional[str] = None
    email: Optional[str] = None


class InvoiceData(BaseModel):
    # Basic invoice information
    invoice_number: Optional[str] = None
    date: Optional[str] = None
    due_date: Optional[str] = None
    
    # French-specific invoice sequence validation
    invoice_sequence_number: Optional[int] = Field(None, description="Sequential invoice number for French compliance")
    
    # Business entities (vendor/seller and customer/buyer)
    vendor: Optional[FrenchBusinessInfo] = None
    customer: Optional[FrenchBusinessInfo] = None
    
    # Legacy fields for backward compatibility
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    
    # Line items with French enhancements
    line_items: List[LineItem] = []
    
    # Financial information with French compliance
    subtotal_ht: Optional[float] = Field(None, description="Subtotal Hors Taxes (before TVA)")
    tva_breakdown: List[FrenchTVABreakdown] = Field(default_factory=list, description="TVA breakdown by rate")
    total_tva: Optional[float] = Field(None, description="Total TVA amount")
    total_ttc: Optional[float] = Field(None, description="Total Toutes Taxes Comprises (including TVA)")
    
    # Legacy tax fields for backward compatibility
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    
    currency: str = "EUR"  # Default to EUR for French market
    
    # French mandatory payment information
    payment_terms: Optional[str] = None  # Délai de paiement
    late_payment_penalties: Optional[str] = Field(
        default="En cas de retard de paiement, des pénalités de retard seront appliquées au taux de 3 fois le taux d'intérêt légal.",
        description="Mandatory late payment penalty clause"
    )
    recovery_fees: Optional[str] = Field(
        default="Une indemnité forfaitaire de 40 euros pour frais de recouvrement sera exigible en cas de retard de paiement.",
        description="Mandatory €40 recovery fee clause"
    )
    
    # Additional French fields
    notes: Optional[str] = None
    delivery_date: Optional[str] = None
    delivery_address: Optional[str] = None
    
    # Compliance and validation
    is_french_compliant: Optional[bool] = Field(False, description="Whether invoice meets French compliance requirements")
    compliance_errors: List[str] = Field(default_factory=list, description="List of compliance violations")
    
    @validator('currency')
    def validate_currency_for_french_market(cls, v):
        # Allow EUR and other currencies but warn for non-EUR
        if v not in ['EUR', 'USD', 'GBP']:
            raise ValueError(f'Unsupported currency: {v}')
        return v
    
    def get_vendor_siren(self) -> Optional[str]:
        """Get vendor SIREN number from either new or legacy format"""
        if self.vendor and self.vendor.siren_number:
            return self.vendor.siren_number
        return None
    
    def get_customer_siren(self) -> Optional[str]:
        """Get customer SIREN number for B2B transactions"""
        if self.customer and self.customer.siren_number:
            return self.customer.siren_number
        return None
    
    def calculate_tva_totals(self) -> Dict[str, float]:
        """Calculate total TVA amounts by rate"""
        tva_totals = {}
        for breakdown in self.tva_breakdown:
            rate_key = f"{breakdown.rate}%"
            tva_totals[rate_key] = breakdown.tva_amount
        return tva_totals


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