"""
Comprehensive French TVA Validation Engine

This module provides enterprise-grade TVA validation for French invoices,
including product category mapping, automatic rate determination, multi-rate
invoice support, and comprehensive compliance checking.

Features:
- French TVA rates validation (20%, 10%, 5.5%, 2.1%, 0%)
- Product category mapping for automatic rate determination
- Multi-rate invoice validation with cross-references
- TVA calculation verification (HT + TVA = TTC)
- TVA exemption handling and compliance
- Integration with French compliance infrastructure
- Caching and performance optimization
- Comprehensive audit logging
"""

import re
import asyncio
import logging
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from schemas.invoice import InvoiceData, LineItem, FrenchTVABreakdown
from models.french_compliance import (
    FrenchComplianceValidation,
    ComplianceSettings,
    ValidationErrorPattern,
    FRENCH_TVA_RATES,
    FRENCH_ERROR_CODES
)
from core.french_compliance.validation_cache import (
    get_validation_cache,
    cache_tva_validation,
    get_cached_tva_validation
)
from core.gdpr_audit import log_audit_event

logger = logging.getLogger(__name__)

class TVARate(Enum):
    """French TVA rates"""
    STANDARD = 20.0         # Taux normal
    REDUCED_1 = 10.0        # Taux réduit (restauration, transport, hôtellerie)
    REDUCED_2 = 5.5         # Taux réduit (alimentaire, livres, médicaments)
    SUPER_REDUCED = 2.1     # Taux super réduit (presse, médicaments remboursables)
    EXEMPT = 0.0            # Exonéré

class TVAExemptionType(Enum):
    """Types of TVA exemptions"""
    EXPORT = "export"                           # Export hors UE
    INTRA_EU = "intra_eu"                      # Livraisons intracommunautaires
    MEDICAL = "medical"                         # Prestations médicales
    EDUCATION = "education"                     # Enseignement
    FINANCIAL = "financial"                     # Services financiers
    INSURANCE = "insurance"                     # Assurance
    REAL_ESTATE = "real_estate"                # Immobilier
    SMALL_BUSINESS = "small_business"          # Franchise en base (micro-entreprise)

class ProductCategory(Enum):
    """Product categories for TVA rate determination"""
    # Standard rate (20%)
    GENERAL_GOODS = "general_goods"
    SERVICES = "services"
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    COSMETICS = "cosmetics"
    
    # Reduced rate 1 (10%)
    RESTAURANT = "restaurant"
    ACCOMMODATION = "accommodation"
    TRANSPORT = "transport"
    CULTURE = "culture"
    SPORT = "sport"
    
    # Reduced rate 2 (5.5%)
    FOOD = "food"
    BOOKS = "books"
    MEDICINE = "medicine"
    ENERGY = "energy"
    ACCESSIBILITY = "accessibility"
    
    # Super reduced rate (2.1%)
    PRESS = "press"
    REIMBURSABLE_MEDICINE = "reimbursable_medicine"
    
    # Exempt (0%)
    EXPORT_GOODS = "export_goods"
    MEDICAL_SERVICES = "medical_services"
    EDUCATION_SERVICES = "education_services"
    FINANCIAL_SERVICES = "financial_services"

@dataclass
class TVAValidationResult:
    """Result of TVA validation"""
    is_valid: bool
    rate_valid: bool
    calculation_valid: bool
    exemption_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    expected_rate: Optional[float] = None
    expected_amount: Optional[float] = None
    actual_rate: Optional[float] = None
    actual_amount: Optional[float] = None
    product_category: Optional[ProductCategory] = None
    exemption_type: Optional[TVAExemptionType] = None
    compliance_score: float = 0.0

@dataclass
class TVABreakdownValidation:
    """Validation result for TVA breakdown"""
    rate: float
    is_valid_rate: bool
    expected_amount: float
    actual_amount: float
    calculation_valid: bool
    difference: float
    tolerance_exceeded: bool

class TVAProductMapper:
    """Maps products/services to appropriate TVA categories and rates"""
    
    def __init__(self):
        # Keywords for automatic product category detection
        self.category_keywords = {
            ProductCategory.FOOD: [
                "alimentaire", "nourriture", "boisson", "légume", "fruit", "viande",
                "poisson", "pain", "pâtisserie", "fromage", "lait", "yaourt",
                "eau", "jus", "café", "thé", "épicerie", "supermarché"
            ],
            ProductCategory.RESTAURANT: [
                "restaurant", "café", "bar", "brasserie", "pizzeria", "repas",
                "menu", "plat", "boisson", "service", "restauration"
            ],
            ProductCategory.ACCOMMODATION: [
                "hôtel", "chambre", "nuitée", "hébergement", "gîte", "camping",
                "location", "séjour", "pension"
            ],
            ProductCategory.TRANSPORT: [
                "transport", "taxi", "bus", "train", "avion", "métro", "tramway",
                "location voiture", "carburant", "péage", "parking"
            ],
            ProductCategory.BOOKS: [
                "livre", "manuel", "guide", "dictionnaire", "encyclopédie",
                "magazine", "revue", "journal", "publication", "édition"
            ],
            ProductCategory.MEDICINE: [
                "médicament", "pharmacie", "médical", "santé", "traitement",
                "ordonnance", "prescription", "thérapie"
            ],
            ProductCategory.PRESS: [
                "presse", "journal", "quotidien", "hebdomadaire", "mensuel",
                "publication périodique", "magazine d'information"
            ],
            ProductCategory.CULTURE: [
                "musée", "théâtre", "cinéma", "concert", "spectacle", "exposition",
                "culture", "art", "monument", "visite"
            ],
            ProductCategory.MEDICAL_SERVICES: [
                "consultation", "médecin", "dentiste", "kinésithérapeute",
                "infirmier", "sage-femme", "ostéopathe", "psychologue"
            ],
            ProductCategory.EDUCATION_SERVICES: [
                "formation", "cours", "enseignement", "école", "université",
                "stage", "éducation", "apprentissage"
            ],
            ProductCategory.FINANCIAL_SERVICES: [
                "banque", "crédit", "prêt", "assurance", "finance", "placement",
                "investissement", "gestion"
            ]
        }
    
    def detect_product_category(self, description: str) -> Optional[ProductCategory]:
        """
        Automatically detect product category from description
        
        Args:
            description: Product/service description
            
        Returns:
            Most likely ProductCategory or None
        """
        if not description:
            return None
        
        description_lower = description.lower()
        
        # Score each category based on keyword matches
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in description_lower)
            if score > 0:
                category_scores[category] = score
        
        if not category_scores:
            return None
        
        # Return category with highest score
        return max(category_scores.items(), key=lambda x: x[1])[0]
    
    def get_expected_tva_rate(self, category: ProductCategory) -> float:
        """Get expected TVA rate for a product category"""
        rate_mapping = {
            # Standard rate (20%)
            ProductCategory.GENERAL_GOODS: TVARate.STANDARD.value,
            ProductCategory.SERVICES: TVARate.STANDARD.value,
            ProductCategory.ELECTRONICS: TVARate.STANDARD.value,
            ProductCategory.CLOTHING: TVARate.STANDARD.value,
            ProductCategory.COSMETICS: TVARate.STANDARD.value,
            
            # Reduced rate 1 (10%)
            ProductCategory.RESTAURANT: TVARate.REDUCED_1.value,
            ProductCategory.ACCOMMODATION: TVARate.REDUCED_1.value,
            ProductCategory.TRANSPORT: TVARate.REDUCED_1.value,
            ProductCategory.CULTURE: TVARate.REDUCED_1.value,
            ProductCategory.SPORT: TVARate.REDUCED_1.value,
            
            # Reduced rate 2 (5.5%)
            ProductCategory.FOOD: TVARate.REDUCED_2.value,
            ProductCategory.BOOKS: TVARate.REDUCED_2.value,
            ProductCategory.MEDICINE: TVARate.REDUCED_2.value,
            ProductCategory.ENERGY: TVARate.REDUCED_2.value,
            ProductCategory.ACCESSIBILITY: TVARate.REDUCED_2.value,
            
            # Super reduced rate (2.1%)
            ProductCategory.PRESS: TVARate.SUPER_REDUCED.value,
            ProductCategory.REIMBURSABLE_MEDICINE: TVARate.SUPER_REDUCED.value,
            
            # Exempt (0%)
            ProductCategory.EXPORT_GOODS: TVARate.EXEMPT.value,
            ProductCategory.MEDICAL_SERVICES: TVARate.EXEMPT.value,
            ProductCategory.EDUCATION_SERVICES: TVARate.EXEMPT.value,
            ProductCategory.FINANCIAL_SERVICES: TVARate.EXEMPT.value,
        }
        
        return rate_mapping.get(category, TVARate.STANDARD.value)

class TVACalculator:
    """Performs precise TVA calculations with French rounding rules"""
    
    @staticmethod
    def calculate_tva_from_ht(amount_ht: float, rate: float) -> float:
        """
        Calculate TVA amount from HT amount and rate
        
        Args:
            amount_ht: Amount excluding TVA
            rate: TVA rate as percentage (e.g., 20.0 for 20%)
            
        Returns:
            TVA amount rounded to 2 decimal places
        """
        if rate == 0:
            return 0.0
        
        # Use Decimal for precise calculations
        ht_decimal = Decimal(str(amount_ht))
        rate_decimal = Decimal(str(rate)) / Decimal('100')
        
        tva_amount = ht_decimal * rate_decimal
        
        # Round to 2 decimal places using banker's rounding
        return float(tva_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    @staticmethod
    def calculate_ttc_from_ht(amount_ht: float, rate: float) -> float:
        """Calculate TTC amount from HT amount and rate"""
        tva_amount = TVACalculator.calculate_tva_from_ht(amount_ht, rate)
        return round(amount_ht + tva_amount, 2)
    
    @staticmethod
    def calculate_ht_from_ttc(amount_ttc: float, rate: float) -> float:
        """Calculate HT amount from TTC amount and rate"""
        if rate == 0:
            return amount_ttc
        
        ttc_decimal = Decimal(str(amount_ttc))
        rate_decimal = Decimal(str(rate)) / Decimal('100')
        
        ht_amount = ttc_decimal / (Decimal('1') + rate_decimal)
        
        return float(ht_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    @staticmethod
    def validate_tva_calculation(
        amount_ht: float, 
        rate: float, 
        actual_tva: float,
        tolerance: float = 0.01
    ) -> Tuple[bool, float, float]:
        """
        Validate TVA calculation with tolerance
        
        Args:
            amount_ht: HT amount
            rate: TVA rate
            actual_tva: Actual TVA amount from invoice
            tolerance: Acceptable difference in euros
            
        Returns:
            Tuple of (is_valid, expected_tva, difference)
        """
        expected_tva = TVACalculator.calculate_tva_from_ht(amount_ht, rate)
        difference = abs(expected_tva - actual_tva)
        is_valid = difference <= tolerance
        
        return is_valid, expected_tva, difference

class TVAExemptionValidator:
    """Validates TVA exemptions according to French law"""
    
    def __init__(self):
        self.exemption_conditions = {
            TVAExemptionType.EXPORT: {
                "description": "Export de biens hors Union Européenne",
                "required_documents": ["déclaration d'exportation", "preuve de sortie UE"],
                "validation_rules": ["customer_country_non_eu", "goods_physically_exported"]
            },
            TVAExemptionType.INTRA_EU: {
                "description": "Livraisons intracommunautaires",
                "required_documents": ["numéro TVA intracommunautaire client"],
                "validation_rules": ["customer_tva_valid", "customer_country_eu", "goods_transported"]
            },
            TVAExemptionType.MEDICAL: {
                "description": "Prestations médicales",
                "required_documents": ["qualification professionnelle"],
                "validation_rules": ["provider_medical_qualification"]
            },
            TVAExemptionType.EDUCATION: {
                "description": "Enseignement",
                "required_documents": ["agrément enseignement"],
                "validation_rules": ["education_service", "public_interest"]
            },
            TVAExemptionType.FINANCIAL: {
                "description": "Services financiers",
                "required_documents": ["agrément financier"],
                "validation_rules": ["financial_service_nature"]
            }
        }
    
    def validate_exemption(
        self, 
        exemption_type: TVAExemptionType,
        invoice_data: InvoiceData,
        context: Dict[str, Any] = None
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate TVA exemption
        
        Args:
            exemption_type: Type of exemption claimed
            invoice_data: Invoice data
            context: Additional validation context
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        context = context or {}
        
        if exemption_type not in self.exemption_conditions:
            errors.append(f"Type d'exonération non reconnu: {exemption_type}")
            return False, errors, warnings
        
        exemption_info = self.exemption_conditions[exemption_type]
        
        # Validate based on exemption type
        if exemption_type == TVAExemptionType.EXPORT:
            if not self._validate_export_exemption(invoice_data, context):
                errors.append("Conditions d'exonération export non remplies")
        
        elif exemption_type == TVAExemptionType.INTRA_EU:
            if not self._validate_intra_eu_exemption(invoice_data, context):
                errors.append("Conditions d'exonération intracommunautaire non remplies")
        
        elif exemption_type == TVAExemptionType.MEDICAL:
            if not self._validate_medical_exemption(invoice_data, context):
                errors.append("Conditions d'exonération prestations médicales non remplies")
        
        # Add warnings for missing documentation
        for doc in exemption_info["required_documents"]:
            warnings.append(f"Vérifier la présence de: {doc}")
        
        return len(errors) == 0, errors, warnings
    
    def _validate_export_exemption(self, invoice_data: InvoiceData, context: Dict) -> bool:
        """Validate export exemption conditions"""
        # Check if customer is outside EU
        customer = invoice_data.customer
        if customer and customer.country:
            eu_countries = [
                "FR", "DE", "IT", "ES", "NL", "BE", "AT", "PT", "FI", "IE",
                "LU", "GR", "DK", "SE", "CZ", "HU", "PL", "SK", "SI", "EE",
                "LV", "LT", "CY", "MT", "BG", "RO", "HR"
            ]
            return customer.country not in eu_countries
        
        return False
    
    def _validate_intra_eu_exemption(self, invoice_data: InvoiceData, context: Dict) -> bool:
        """Validate intra-EU exemption conditions"""
        customer = invoice_data.customer
        if not customer:
            return False
        
        # Check customer has valid EU TVA number
        if not customer.tva_number:
            return False
        
        # Basic format check for EU TVA numbers
        eu_tva_patterns = {
            "AT": r"^ATU\d{8}$",  # Austria
            "BE": r"^BE\d{10}$",  # Belgium
            "DE": r"^DE\d{9}$",   # Germany
            "ES": r"^ES[A-Z]\d{7}[A-Z]$",  # Spain
            "IT": r"^IT\d{11}$",  # Italy
            "NL": r"^NL\d{9}B\d{2}$",  # Netherlands
            # Add more as needed
        }
        
        country_code = customer.tva_number[:2]
        pattern = eu_tva_patterns.get(country_code)
        
        if pattern:
            return bool(re.match(pattern, customer.tva_number))
        
        return customer.tva_number.startswith(("AT", "BE", "DE", "ES", "IT", "NL"))
    
    def _validate_medical_exemption(self, invoice_data: InvoiceData, context: Dict) -> bool:
        """Validate medical exemption conditions"""
        # Check if vendor provides medical services
        vendor = invoice_data.vendor
        if vendor and vendor.naf_code:
            # NAF codes for medical activities (simplified)
            medical_naf_codes = ["8610", "8621", "8622", "8623", "8690"]
            return any(vendor.naf_code.startswith(code) for code in medical_naf_codes)
        
        # Check line items for medical services
        medical_keywords = ["consultation", "soin", "traitement", "thérapie", "médical"]
        for item in invoice_data.line_items:
            description_lower = item.description.lower()
            if any(keyword in description_lower for keyword in medical_keywords):
                return True
        
        return False

class FrenchTVAValidator:
    """
    Comprehensive French TVA validation engine
    
    Provides enterprise-grade TVA validation with:
    - French rate validation
    - Product category mapping
    - Multi-rate invoice support
    - Calculation verification
    - Exemption handling
    - Caching and performance optimization
    """
    
    def __init__(self):
        self.valid_rates = [rate.value for rate in TVARate]
        self.product_mapper = TVAProductMapper()
        self.calculator = TVACalculator()
        self.exemption_validator = TVAExemptionValidator()
        self.cache = get_validation_cache()
        
        # Validation tolerances
        self.calculation_tolerance = 0.02  # 2 cents tolerance for rounding
        self.rate_tolerance = 0.01  # Allow minor rate variations
    
    async def validate_invoice_tva(
        self, 
        invoice: InvoiceData,
        db_session: AsyncSession,
        validation_id: Optional[str] = None
    ) -> TVAValidationResult:
        """
        Comprehensive TVA validation for an entire invoice
        
        Args:
            invoice: Invoice data to validate
            db_session: Database session for audit logging
            validation_id: Optional validation ID for tracking
            
        Returns:
            Complete TVA validation result
        """
        
        # GDPR audit log
        await log_audit_event(
            db_session,
            user_id=None,
            operation_type="tva_validation",
            data_categories=["financial_data", "tax_data"],
            risk_level="medium",
            details={
                "invoice_number": invoice.invoice_number,
                "validation_id": validation_id,
                "purpose": "french_tva_compliance_validation"
            }
        )
        
        result = TVAValidationResult(
            is_valid=True,
            rate_valid=True,
            calculation_valid=True,
            exemption_valid=True
        )
        
        # Check cache first
        cache_key = f"{invoice.invoice_number}_{hash(str(invoice.tva_breakdown))}"
        cached_result = await get_cached_tva_validation(cache_key)
        if cached_result:
            logger.debug(f"TVA validation cache hit for invoice {invoice.invoice_number}")
            return TVAValidationResult(**cached_result)
        
        try:
            # Validate TVA breakdown
            if invoice.tva_breakdown:
                await self._validate_tva_breakdown(invoice, result, db_session)
            else:
                result.warnings.append("Aucun détail TVA par taux fourni - recommandé pour la conformité")
            
            # Validate line items
            await self._validate_line_items_tva(invoice, result, db_session)
            
            # Validate overall calculations
            await self._validate_overall_calculations(invoice, result)
            
            # Check for exemptions
            await self._validate_exemptions(invoice, result)
            
            # Cross-validate breakdown vs line items
            await self._cross_validate_tva_data(invoice, result)
            
            # Calculate compliance score
            result.compliance_score = self._calculate_tva_compliance_score(result)
            
            # Update final validity
            result.is_valid = (
                result.rate_valid and 
                result.calculation_valid and 
                result.exemption_valid and
                len(result.errors) == 0
            )
            
            # Cache the result
            await cache_tva_validation(cache_key, result.__dict__)
            
            logger.info(
                f"TVA validation completed for invoice {invoice.invoice_number}: "
                f"Valid={result.is_valid}, Score={result.compliance_score:.1f}%"
            )
            
        except Exception as e:
            logger.error(f"TVA validation failed for invoice {invoice.invoice_number}: {e}")
            result.errors.append(f"Erreur lors de la validation TVA: {str(e)}")
            result.is_valid = False
        
        return result
    
    async def _validate_tva_breakdown(
        self, 
        invoice: InvoiceData, 
        result: TVAValidationResult,
        db_session: AsyncSession
    ):
        """Validate TVA breakdown by rate"""
        
        breakdown_validations = []
        
        for i, tva_item in enumerate(invoice.tva_breakdown):
            # Validate rate
            if tva_item.rate not in self.valid_rates:
                result.errors.append(
                    f"Taux TVA invalide: {tva_item.rate}%. "
                    f"Taux français valides: {', '.join(map(str, self.valid_rates))}%"
                )
                result.rate_valid = False
            
            # Validate calculation
            calculation_valid, expected_amount, difference = self.calculator.validate_tva_calculation(
                tva_item.taxable_amount,
                tva_item.rate,
                tva_item.tva_amount,
                self.calculation_tolerance
            )
            
            breakdown_validation = TVABreakdownValidation(
                rate=tva_item.rate,
                is_valid_rate=tva_item.rate in self.valid_rates,
                expected_amount=expected_amount,
                actual_amount=tva_item.tva_amount,
                calculation_valid=calculation_valid,
                difference=difference,
                tolerance_exceeded=difference > self.calculation_tolerance
            )
            
            breakdown_validations.append(breakdown_validation)
            
            if not calculation_valid:
                result.errors.append(
                    f"Calcul TVA incorrect pour le taux {tva_item.rate}%: "
                    f"attendu {expected_amount:.2f}€, trouvé {tva_item.tva_amount:.2f}€ "
                    f"(différence: {difference:.2f}€)"
                )
                result.calculation_valid = False
            elif difference > 0:
                result.warnings.append(
                    f"Différence mineure de calcul TVA pour le taux {tva_item.rate}%: "
                    f"{difference:.2f}€"
                )
    
    async def _validate_line_items_tva(
        self, 
        invoice: InvoiceData, 
        result: TVAValidationResult,
        db_session: AsyncSession
    ):
        """Validate TVA on individual line items"""
        
        for i, item in enumerate(invoice.line_items):
            # Check if TVA rate is provided
            if item.tva_rate is None:
                result.warnings.append(
                    f"Taux TVA manquant pour l'article {i+1}: {item.description}"
                )
                continue
            
            # Validate rate
            if item.tva_rate not in self.valid_rates:
                result.errors.append(
                    f"Taux TVA invalide pour l'article {i+1} ({item.description}): "
                    f"{item.tva_rate}%"
                )
                result.rate_valid = False
            
            # Try to detect product category and suggest appropriate rate
            category = self.product_mapper.detect_product_category(item.description)
            if category:
                expected_rate = self.product_mapper.get_expected_tva_rate(category)
                if abs(item.tva_rate - expected_rate) > self.rate_tolerance:
                    result.warnings.append(
                        f"Taux TVA inhabituel pour l'article {i+1} ({item.description}): "
                        f"trouvé {item.tva_rate}%, attendu {expected_rate}% pour la catégorie {category.value}"
                    )
                    result.product_category = category
                    result.expected_rate = expected_rate
                    result.actual_rate = item.tva_rate
            
            # Validate line item TVA calculation if amount is provided
            if item.tva_amount is not None:
                unit_ht = item.unit_price
                total_ht = unit_ht * item.quantity
                
                calculation_valid, expected_tva, difference = self.calculator.validate_tva_calculation(
                    total_ht,
                    item.tva_rate,
                    item.tva_amount,
                    self.calculation_tolerance
                )
                
                if not calculation_valid:
                    result.errors.append(
                        f"Calcul TVA incorrect pour l'article {i+1}: "
                        f"attendu {expected_tva:.2f}€, trouvé {item.tva_amount:.2f}€"
                    )
                    result.calculation_valid = False
    
    async def _validate_overall_calculations(self, invoice: InvoiceData, result: TVAValidationResult):
        """Validate overall invoice TVA calculations"""
        
        if not invoice.tva_breakdown:
            return
        
        # Calculate totals from breakdown
        total_ht_breakdown = sum(item.taxable_amount for item in invoice.tva_breakdown)
        total_tva_breakdown = sum(item.tva_amount for item in invoice.tva_breakdown)
        total_ttc_calculated = total_ht_breakdown + total_tva_breakdown
        
        # Compare with invoice totals
        if invoice.subtotal_ht is not None:
            ht_difference = abs(total_ht_breakdown - invoice.subtotal_ht)
            if ht_difference > self.calculation_tolerance:
                result.errors.append(
                    f"Incohérence montant HT: détail TVA {total_ht_breakdown:.2f}€, "
                    f"total facture {invoice.subtotal_ht:.2f}€ "
                    f"(différence: {ht_difference:.2f}€)"
                )
                result.calculation_valid = False
        
        if invoice.total_tva is not None:
            tva_difference = abs(total_tva_breakdown - invoice.total_tva)
            if tva_difference > self.calculation_tolerance:
                result.errors.append(
                    f"Incohérence montant TVA: détail TVA {total_tva_breakdown:.2f}€, "
                    f"total facture {invoice.total_tva:.2f}€ "
                    f"(différence: {tva_difference:.2f}€)"
                )
                result.calculation_valid = False
        
        if invoice.total_ttc is not None:
            ttc_difference = abs(total_ttc_calculated - invoice.total_ttc)
            if ttc_difference > self.calculation_tolerance:
                result.errors.append(
                    f"Incohérence montant TTC: calculé {total_ttc_calculated:.2f}€, "
                    f"facture {invoice.total_ttc:.2f}€ "
                    f"(différence: {ttc_difference:.2f}€)"
                )
                result.calculation_valid = False
    
    async def _validate_exemptions(self, invoice: InvoiceData, result: TVAValidationResult):
        """Validate TVA exemptions if present"""
        
        # Check if invoice has 0% TVA items
        zero_rate_items = []
        if invoice.tva_breakdown:
            zero_rate_items = [item for item in invoice.tva_breakdown if item.rate == 0.0]
        
        line_zero_items = [item for item in invoice.line_items if item.tva_rate == 0.0]
        
        if zero_rate_items or line_zero_items:
            # Attempt to determine exemption type
            exemption_type = self._detect_exemption_type(invoice)
            
            if exemption_type:
                is_valid, errors, warnings = self.exemption_validator.validate_exemption(
                    exemption_type, invoice
                )
                
                result.exemption_type = exemption_type
                result.exemption_valid = is_valid
                result.errors.extend(errors)
                result.warnings.extend(warnings)
                
                if is_valid:
                    result.suggestions.append(
                        f"Exonération {exemption_type.value} détectée et validée"
                    )
                else:
                    result.suggestions.append(
                        f"Vérifier les conditions d'exonération {exemption_type.value}"
                    )
            else:
                result.warnings.append(
                    "TVA à 0% détectée sans type d'exonération identifiable - "
                    "vérifier la justification légale"
                )
    
    def _detect_exemption_type(self, invoice: InvoiceData) -> Optional[TVAExemptionType]:
        """Detect likely exemption type from invoice data"""
        
        customer = invoice.customer
        
        # Check for export (non-EU customer)
        if customer and customer.country:
            eu_countries = ["FR", "DE", "IT", "ES", "NL", "BE", "AT", "PT", "FI", "IE"]
            if customer.country not in eu_countries:
                return TVAExemptionType.EXPORT
        
        # Check for intra-EU (EU customer with TVA number)
        if customer and customer.tva_number and not customer.tva_number.startswith("FR"):
            return TVAExemptionType.INTRA_EU
        
        # Check for medical services
        medical_keywords = ["consultation", "soin", "médical", "santé"]
        for item in invoice.line_items:
            if any(keyword in item.description.lower() for keyword in medical_keywords):
                return TVAExemptionType.MEDICAL
        
        # Check for education services
        education_keywords = ["formation", "cours", "enseignement", "éducation"]
        for item in invoice.line_items:
            if any(keyword in item.description.lower() for keyword in education_keywords):
                return TVAExemptionType.EDUCATION
        
        return None
    
    async def _cross_validate_tva_data(self, invoice: InvoiceData, result: TVAValidationResult):
        """Cross-validate TVA data between breakdown and line items"""
        
        if not invoice.tva_breakdown or not invoice.line_items:
            return
        
        # Group line items by TVA rate
        line_items_by_rate = {}
        for item in invoice.line_items:
            if item.tva_rate is not None:
                rate = item.tva_rate
                if rate not in line_items_by_rate:
                    line_items_by_rate[rate] = []
                line_items_by_rate[rate].append(item)
        
        # Check if breakdown rates match line item rates
        breakdown_rates = {item.rate for item in invoice.tva_breakdown}
        line_item_rates = set(line_items_by_rate.keys())
        
        missing_in_breakdown = line_item_rates - breakdown_rates
        missing_in_items = breakdown_rates - line_item_rates
        
        if missing_in_breakdown:
            result.warnings.append(
                f"Taux présents dans les articles mais absents du détail TVA: "
                f"{', '.join(f'{rate}%' for rate in missing_in_breakdown)}"
            )
        
        if missing_in_items:
            result.warnings.append(
                f"Taux présents dans le détail TVA mais absents des articles: "
                f"{', '.join(f'{rate}%' for rate in missing_in_items)}"
            )
        
        # Validate amounts for common rates
        for rate in breakdown_rates & line_item_rates:
            # Find breakdown item for this rate
            breakdown_item = next(
                item for item in invoice.tva_breakdown if item.rate == rate
            )
            
            # Calculate totals from line items
            line_items = line_items_by_rate[rate]
            total_ht_lines = sum(item.unit_price * item.quantity for item in line_items)
            
            # Compare with breakdown
            ht_difference = abs(total_ht_lines - breakdown_item.taxable_amount)
            if ht_difference > self.calculation_tolerance:
                result.warnings.append(
                    f"Incohérence montant HT pour le taux {rate}%: "
                    f"articles {total_ht_lines:.2f}€, détail TVA {breakdown_item.taxable_amount:.2f}€"
                )
    
    def _calculate_tva_compliance_score(self, result: TVAValidationResult) -> float:
        """Calculate TVA compliance score (0-100)"""
        
        score = 100.0
        
        # Deduct for errors (critical)
        score -= len(result.errors) * 15
        
        # Deduct for warnings (minor)
        score -= len(result.warnings) * 3
        
        # Deduct for invalid rates
        if not result.rate_valid:
            score -= 25
        
        # Deduct for calculation errors
        if not result.calculation_valid:
            score -= 20
        
        # Deduct for exemption issues
        if not result.exemption_valid:
            score -= 10
        
        return max(0.0, min(100.0, score))

# Convenience functions for easy integration

async def validate_invoice_tva(
    invoice: InvoiceData,
    db_session: AsyncSession,
    validation_id: Optional[str] = None
) -> TVAValidationResult:
    """
    Convenience function for comprehensive TVA validation
    
    Args:
        invoice: Invoice data to validate
        db_session: Database session
        validation_id: Optional validation ID
        
    Returns:
        TVA validation result
    """
    validator = FrenchTVAValidator()
    return await validator.validate_invoice_tva(invoice, db_session, validation_id)

async def validate_tva_rate(rate: float) -> Tuple[bool, Optional[str]]:
    """
    Quick validation of a TVA rate
    
    Args:
        rate: TVA rate to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_rates = [rate.value for rate in TVARate]
    
    if rate in valid_rates:
        return True, None
    else:
        return False, f"Taux TVA invalide: {rate}%. Taux français valides: {', '.join(map(str, valid_rates))}%"

def get_product_tva_rate(description: str) -> Tuple[float, Optional[ProductCategory]]:
    """
    Get recommended TVA rate for a product/service
    
    Args:
        description: Product/service description
        
    Returns:
        Tuple of (recommended_rate, detected_category)
    """
    mapper = TVAProductMapper()
    category = mapper.detect_product_category(description)
    
    if category:
        rate = mapper.get_expected_tva_rate(category)
        return rate, category
    else:
        return TVARate.STANDARD.value, None

def calculate_tva_amounts(amount_ht: float, rate: float) -> Dict[str, float]:
    """
    Calculate all TVA-related amounts
    
    Args:
        amount_ht: Amount excluding TVA
        rate: TVA rate as percentage
        
    Returns:
        Dictionary with ht, tva, and ttc amounts
    """
    calculator = TVACalculator()
    
    tva_amount = calculator.calculate_tva_from_ht(amount_ht, rate)
    ttc_amount = calculator.calculate_ttc_from_ht(amount_ht, rate)
    
    return {
        "amount_ht": round(amount_ht, 2),
        "tva_amount": tva_amount,
        "amount_ttc": ttc_amount,
        "rate": rate
    }