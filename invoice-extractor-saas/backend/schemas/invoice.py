from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
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
    """TVA (VAT) breakdown by rate - supports both French and international rates"""
    rate: float = Field(..., description="TVA/VAT rate (any valid percentage)")
    taxable_amount: float = Field(..., description="Amount before TVA (HT)")
    tva_amount: float = Field(..., description="TVA/VAT amount")
    is_french_rate: Optional[bool] = Field(default=None, description="Whether this is a standard French TVA rate")
    
    @validator('rate')
    def validate_tax_rate(cls, v):
        # Allow any reasonable tax rate (0-100%)
        if v < 0 or v > 100:
            raise ValueError(f'Invalid tax rate: {v}%. Must be between 0% and 100%')
        return v
    
    @validator('is_french_rate', always=True)
    def set_french_rate_flag(cls, v, values):
        if 'rate' not in values:
            return v
        
        # Standard French TVA rates
        french_rates = [0.0, 2.1, 5.5, 10.0, 20.0]
        rate = values['rate']
        
        # Auto-detect if this is a French rate
        if v is None:
            return rate in french_rates
        return v


class FrenchBusinessInfo(BaseModel):
    """French business identification information"""
    name: str
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    
    # French mandatory business identifiers
    siren_number: Optional[str] = Field(None, pattern=r'^\d{9}$', description="SIREN number (9 digits)")
    siret_number: Optional[str] = Field(None, pattern=r'^\d{14}$', description="SIRET number (14 digits)")
    tva_number: Optional[str] = Field(None, pattern=r'^FR\d{11}$', description="French TVA number (FR + 11 digits)")
    
    # Additional French business information
    naf_code: Optional[str] = Field(None, pattern=r'^\d{4}[A-Z]$', description="NAF/APE code (4 digits + letter)")
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
    
    # Business context fields (IMPORTANT - Phase 2)
    order_number: Optional[str] = Field(None, description="Numéro de commande")
    project_reference: Optional[str] = Field(None, description="Référence projet")
    contract_number: Optional[str] = Field(None, description="Numéro de contrat")
    
    # Payment and financial details (IMPORTANT - Phase 2)
    payment_method: Optional[str] = Field(None, description="Mode de paiement")
    bank_details: Optional[str] = Field(None, description="RIB/IBAN")
    discount_amount: Optional[float] = Field(None, description="Remise éventuelle")
    deposit_amount: Optional[float] = Field(None, description="Acompte versé")
    shipping_cost: Optional[float] = Field(None, description="Frais de port")
    packaging_cost: Optional[float] = Field(None, description="Frais d'emballage")
    other_charges: Optional[float] = Field(None, description="Autres frais")
    
    # French tax specifics (OPTIONAL - Phase 3)
    auto_entrepreneur_mention: Optional[str] = Field(None, description="Mention micro-entrepreneur")
    vat_exemption_reason: Optional[str] = Field(None, description="Motif d'exonération TVA")
    reverse_charge_mention: Optional[str] = Field(None, description="Autoliquidation TVA")
    
    # Additional French fields
    notes: Optional[str] = None
    delivery_date: Optional[str] = None
    delivery_address: Optional[str] = None
    
    # Compliance and validation
    is_french_compliant: Optional[bool] = Field(False, description="Whether invoice meets French compliance requirements")
    compliance_errors: List[str] = Field(default_factory=list, description="List of compliance violations")
    
    @validator('currency')
    def validate_currency_for_french_market(cls, v):
        # Allow EUR and other currencies, handle common currency symbols
        currency_mapping = {
            '$': 'USD',
            '€': 'EUR', 
            '£': 'GBP',
            'USD': 'USD',
            'EUR': 'EUR',
            'GBP': 'GBP',
            'CHF': 'CHF',
            'CAD': 'CAD'
        }
        
        # Map currency symbols to standard codes
        if v in currency_mapping:
            return currency_mapping[v]
        
        # Allow other common currencies without strict validation
        return v if v else 'EUR'
    
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
    
    def validate_french_compliance(self) -> Dict[str, Any]:
        """
        Validate invoice against French legal requirements with compliance scoring
        
        Returns:
            Dict with validation results, compliance score, and field priorities
        """
        validation_result = {
            "is_valid": True,
            "compliance_score": 100.0,
            "errors": [],
            "warnings": [],
            "field_priorities": {
                "mandatory": [],
                "important": [],
                "optional": []
            }
        }
        
        # 🔴 MANDATORY Fields Validation (French Law)
        mandatory_issues = []
        
        # Invoice identification
        if not self.invoice_number:
            mandatory_issues.append("invoice_number: Numéro de facture obligatoire")
        
        if not self.date:
            mandatory_issues.append("invoice_date: Date de facture obligatoire")
        
        # Supplier information (Critical)
        if not self.vendor or not self.vendor.name:
            mandatory_issues.append("supplier_name: Raison sociale fournisseur obligatoire")
        
        if not self.vendor or not self.vendor.siret_number:
            mandatory_issues.append("supplier_siret: SIRET fournisseur obligatoire (14 chiffres)")
        elif self.vendor.siret_number and len(self.vendor.siret_number) != 14:
            mandatory_issues.append("supplier_siret: SIRET doit contenir exactement 14 chiffres")
        elif self.vendor.siret_number and not self.vendor.siret_number.isdigit():
            mandatory_issues.append("supplier_siret: SIRET doit contenir uniquement des chiffres")
        
        if self.vendor and self.vendor.siret_number and not self.vendor.siren_number:
            # Extract SIREN from SIRET if missing
            if len(self.vendor.siret_number) == 14:
                self.vendor.siren_number = self.vendor.siret_number[:9]
        
        # Customer information (if B2B)
        if not self.customer or not self.customer.name:
            mandatory_issues.append("customer_name: Nom du client obligatoire")
        
        # VAT information validation
        subtotal = self.subtotal_ht or self.subtotal or 0
        total_tax = self.total_tva or self.tax or 0
        total = self.total_ttc or self.total or 0
        
        if subtotal <= 0:
            mandatory_issues.append("amount_ht: Montant HT obligatoire et > 0")
        
        if total <= 0:
            mandatory_issues.append("amount_ttc: Montant TTC obligatoire et > 0")
        
        # VAT calculation validation
        if abs((subtotal + total_tax) - total) > 0.02:  # 2 cents tolerance
            mandatory_issues.append(f"vat_calculation: Calcul TVA incorrect (HT:{subtotal:.2f} + TVA:{total_tax:.2f} ≠ TTC:{total:.2f})")
        
        # VAT rates validation (French standard rates)
        french_vat_rates = [0.0, 2.1, 5.5, 10.0, 20.0]
        for tva_item in self.tva_breakdown or []:
            if tva_item.rate not in french_vat_rates:
                mandatory_issues.append(f"vat_rate: Taux TVA non-standard {tva_item.rate}% (taux français: 0%, 2.1%, 5.5%, 10%, 20%)")
        
        # 🟡 IMPORTANT Fields Validation
        important_issues = []
        
        # Line items validation
        if not self.line_items or len(self.line_items) == 0:
            important_issues.append("line_items: Articles de facture recommandés")
        else:
            for i, item in enumerate(self.line_items):
                if not item.description:
                    important_issues.append(f"line_item_{i+1}_description: Description article obligatoire")
                if not item.quantity or item.quantity <= 0:
                    important_issues.append(f"line_item_{i+1}_quantity: Quantité article > 0 obligatoire")
                if not item.unit_price or item.unit_price <= 0:
                    important_issues.append(f"line_item_{i+1}_unit_price: Prix unitaire > 0 obligatoire")
        
        # Payment terms
        if not self.payment_terms:
            important_issues.append("payment_terms: Conditions de paiement recommandées")
        
        # 🟢 OPTIONAL Fields Validation
        optional_issues = []
        
        # Business context
        if not getattr(self, 'order_number', None):
            optional_issues.append("order_number: Numéro de commande utile pour la traçabilité")
        
        # Calculate compliance score
        base_score = 100.0
        
        # Deduct points for issues
        base_score -= len(mandatory_issues) * 15  # 15 points per mandatory issue
        base_score -= len(important_issues) * 5   # 5 points per important issue
        base_score -= len(optional_issues) * 1    # 1 point per optional issue
        
        # Ensure minimum score of 0
        compliance_score = max(0.0, base_score)
        
        # Determine overall validity
        is_valid = len(mandatory_issues) == 0
        
        # Update validation result
        validation_result.update({
            "is_valid": is_valid,
            "compliance_score": compliance_score,
            "errors": mandatory_issues,
            "warnings": important_issues + optional_issues,
            "field_priorities": {
                "mandatory": [issue.split(":")[0] for issue in mandatory_issues],
                "important": [issue.split(":")[0] for issue in important_issues],
                "optional": [issue.split(":")[0] for issue in optional_issues]
            }
        })
        
        # Update internal compliance status
        self.is_french_compliant = is_valid and compliance_score >= 90.0
        self.compliance_errors = mandatory_issues + important_issues
        
        return validation_result


class InvoiceCreate(BaseModel):
    filename: str


class SIRETValidationSummary(BaseModel):
    """Summary of SIRET validation results for frontend display"""
    vendor_siret_validation: Optional[Dict[str, Any]] = None
    customer_siret_validation: Optional[Dict[str, Any]] = None
    overall_summary: Optional[Dict[str, Any]] = None


class InvoiceResponse(BaseModel):
    id: str
    filename: str
    status: str  # "processing", "completed", "failed"
    created_at: datetime
    updated_at: Optional[datetime] = None
    data: Optional[InvoiceData] = None
    siret_validation_results: Optional[SIRETValidationSummary] = None
    error_message: Optional[str] = None
    # Review workflow fields
    review_status: Optional[str] = None  # "pending_review", "in_review", "reviewed", "approved", "rejected"
    # Batch processing tracking
    processing_source: Optional[str] = None  # "individual", "batch", "api"
    batch_id: Optional[str] = None


# ==========================================
# BULK UPLOAD AND DUPLICATE HANDLING SCHEMAS
# ==========================================

class DuplicateInfo(BaseModel):
    """Information about a detected duplicate"""
    filename: str
    is_duplicate: bool
    duplicate_type: str  # "file_duplicate", "invoice_duplicate", "cross_period_duplicate"
    severity: str  # "error", "warning", "info"
    existing_invoice_id: Optional[str] = None
    existing_filename: Optional[str] = None
    existing_created_at: Optional[datetime] = None
    french_message: str
    recommended_action: str  # "skip", "replace", "allow", "user_choice"
    metadata: Dict[str, Any] = {}


class DuplicateResolution(BaseModel):
    """User's resolution for a duplicate"""
    filename: str
    action: str  # "skip", "replace", "allow"
    reason: Optional[str] = None
    user_notes: Optional[str] = None


class BatchUploadSummary(BaseModel):
    """Summary of batch upload duplicate analysis"""
    total_files: int
    unique_files: int
    duplicate_count: int
    requires_user_action: bool
    french_summary: str
    processing_recommendations: Dict[str, str]  # filename -> action


class BulkUploadResponse(BaseModel):
    """Response from bulk upload endpoint"""
    batch_id: str
    upload_summary: BatchUploadSummary
    duplicates_detected: List[DuplicateInfo]
    successful_uploads: List[InvoiceResponse]
    failed_uploads: List[Dict[str, str]]  # filename -> error message
    requires_duplicate_resolution: bool
    french_status_message: str